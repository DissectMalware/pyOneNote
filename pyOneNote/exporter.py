import re
from typing import Any, Dict, Iterable, List, Optional

from .models import OneNotePage, OneNoteSection, OneNoteSectionGroup, OneNoteNotebook


def _safe_decode_bytes(b: bytes) -> str:
    """
    Try UTF-16LE first, then UTF-8 fallback. On failure, return empty string.
    """
    if not isinstance(b, (bytes, bytearray)):
        return ""
    try:
        return b.decode("utf-16le")
    except Exception:
        try:
            return b.decode("utf-8")
        except Exception:
            try:
                return b.decode("latin-1")
            except Exception:
                return ""


def _collect_text_strings_only(value: Any, out: List[str], max_depth: int = 10) -> None:
    """
    Recursively collect text strings, filtering out metadata and binary structures.
    Avoids collecting GUIDs, timestamps, binary data, etc.
    """
    if max_depth <= 0 or value is None:
        return
    
    if isinstance(value, str):
        # Skip if looks like metadata (GUIDs, XML tags, etc)
        if not value.startswith('<') and len(value) < 500:
            out.append(value)
    elif isinstance(value, (bytes, bytearray)):
        # Try to decode bytes, but skip if too long or looks binary
        if len(value) < 200:
            try:
                decoded = bytes(value).decode("utf-16le").strip()
                if decoded and not decoded.startswith('<'):
                    out.append(decoded)
            except Exception:
                try:
                    decoded = bytes(value).decode("utf-8").strip()
                    if decoded and not decoded.startswith('<') and decoded.isprintable():
                        out.append(decoded)
                except Exception:
                    pass
    elif isinstance(value, dict):
        # Skip known metadata keys
        skip_keys = {'SchemaRevisionInOrderToRead', 'NotebookManagementEntityGuid', 
                     'TopologyCreationTimeStamp', 'PageLevel', 'MetaDataObjectsAboveGraphSpace',
                     'ElementChildNodesOfVersionHistory', 'ElementChildNodes'}
        for k, v in value.items():
            if k not in skip_keys:
                _collect_text_strings_only(v, out, max_depth - 1)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            _collect_text_strings_only(item, out, max_depth - 1)


def extract_text_from_properties_clean(properties: Dict[str, Any]) -> str:
    """
    Extract readable text from properties, filtering out metadata.
    """
    if not isinstance(properties, dict):
        return ""
    found: List[str] = []
    _collect_text_strings_only(properties, found)
    return _normalize_join(found)


_whitespace_re = re.compile(r"\s+")


def _normalize_join(strings: Iterable[str]) -> str:
    joined = " ".join(s.strip() for s in strings if s is not None and str(s).strip())
    # collapse multiple whitespace
    return _whitespace_re.sub(" ", joined).strip()


def extract_text_from_properties(properties: Dict[str, Any]) -> str:
    """
    Given a property-set (likely a dict), walk it recursively and return the
    concatenated readable text found within.
    """
    return extract_text_from_properties_clean(properties)


def _find_value_case_insensitive(d: Dict[str, Any], candidates: List[str]) -> Optional[Any]:
    low_map = {k.lower(): k for k in d.keys()}
    for cand in candidates:
        key = low_map.get(cand.lower())
        if key is not None:
            return d.get(key)
    return None


def _clean_text_content(text: str) -> str:
    """
    Clean extracted text by removing control characters, null bytes, and encoding artifacts.
    """
    if not text:
        return ""
    
    # First, handle literal string representations of bytes: b'\x00' -> removed
    import re
    # Remove patterns like b'\x01\x00' or b'\x02'
    text = re.sub(r"b'[^']*'", '', text)
    text = re.sub(r'b"[^"]*"', '', text)
    
    # Remove hex sequences like \x01, \x02
    text = re.sub(r'\\x[0-9a-f]{2}', '', text, flags=re.IGNORECASE)
    
    # Remove common encoding artifacts (locale strings)
    # Remove patterns like "en_US(1033)", "he_IL(1037)", etc
    text = re.sub(r'[a-z]{2}_[A-Z]{2}\(\d+\)', '', text)
    
    # Remove control characters and null bytes (but keep newlines, tabs)
    cleaned = ""
    for char in text:
        code = ord(char)
        # Keep printable chars (including Unicode), newlines, tabs, spaces
        if code >= 32 or char in '\n\t\r':
            cleaned += char
    
    # Remove hex strings that might be encoded data (8+ hex chars in a row)
    cleaned = re.sub(r'[0-9a-fA-F]{8,}', '', cleaned)
    
    # Remove repeated whitespace
    cleaned = _whitespace_re.sub(" ", cleaned).strip()
    
    return cleaned


def _extract_clean_title(props: Dict[str, Any]) -> Optional[str]:
    """Extract just the title text, filtering out metadata and special formats."""
    candidates = ["title", "name", "pageTitle", "PageTitle", "displayName", "CachedTitleString"]
    low_map = {k.lower(): k for k in props.keys()}
    
    for cand in candidates:
        key = low_map.get(cand.lower())
        if key is not None:
            v = props[key]
            if isinstance(v, (bytes, bytearray)):
                try:
                    title = v.decode("utf-16le").strip()
                    title = _clean_text_content(title)
                    if title and not title.startswith('<') and len(title) < 200:
                        return title
                except Exception:
                    pass
            elif isinstance(v, str) and v.strip() and not v.startswith('<'):
                title = _clean_text_content(v)
                if title:
                    return title
    
    return None


def _guess_page_id(properties: Dict[str, Any]) -> Optional[str]:
    candidates = ["objectid", "id", "pageid", "guid"]
    v = _find_value_case_insensitive(properties, candidates)
    if v is None:
        return None
    if isinstance(v, (bytes, bytearray)):
        return _safe_decode_bytes(bytes(v))
    return str(v)


def build_pages_from_document(document) -> List[OneNotePage]:
    """
    Iterate document.get_properties() and construct OneNotePage instances.

    document.get_properties() is expected to return an iterable of property dictionaries.
    For each property-set, this function extracts text using the decoders and
    recursive walker, and maps common keys to `page_id` and `title`.
    """
    pages: List[OneNotePage] = []
    props_iterable = []
    try:
        props_iterable = list(document.get_properties())
    except Exception:
        # best-effort: if get_properties is not iterable, return empty list
        return pages

    for prop in props_iterable:
        if not isinstance(prop, dict):
            # skip unexpected shapes
            continue
        content_text = extract_text_from_properties(prop)
        page_id = _guess_page_id(prop)
        title = _guess_page_title(prop)
        page = OneNotePage(page_id=page_id, title=title, content=content_text, properties=prop)
        pages.append(page)

    return pages


def build_section_group_from_nodes(group_node, sections: List[OneNoteSection] = None) -> OneNoteSectionGroup:
    """
    Build a OneNoteSectionGroup from a section group FileNode and optional sections.
    
    Args:
        group_node: A FileNode with section group metadata
        sections: Optional list of OneNoteSection objects to assign to this group
    
    Returns:
        OneNoteSectionGroup: Section group object with sections populated
    """
    group = OneNoteSectionGroup()
    
    # Try to extract section group ID and title from the node
    if hasattr(group_node, 'data') and hasattr(group_node.data, 'body'):
        group.group_id = str(group_node.data.body.oid)
    
    if sections:
        group.sections = sections
    
    return group


def build_section_groups_from_document(document) -> List[OneNoteSectionGroup]:
    """
    Build OneNoteSectionGroup objects from section group nodes in the document.
    
    Returns:
        List[OneNoteSectionGroup]: List of section groups (basic, without sections assigned)
    """
    section_groups = []
    try:
        section_group_nodes = document.find_section_group_nodes()
    except Exception:
        return section_groups
    
    for node in section_group_nodes:
        group = build_section_group_from_nodes(node)
        section_groups.append(group)
    
    return section_groups


def build_section_from_nodes(section_node, pages: List[OneNotePage] = None) -> OneNoteSection:
    """
    Build a OneNoteSection from a section FileNode and optional pages.
    
    Args:
        section_node: A FileNode with section metadata
        pages: Optional list of OneNotePage objects to assign to this section
    
    Returns:
        OneNoteSection: Section object with pages populated
    """
    section = OneNoteSection()
    
    # Try to extract section ID and title from the node
    if hasattr(section_node, 'data') and hasattr(section_node.data, 'body'):
        section.section_id = str(section_node.data.body.oid)
    
    if pages:
        section.pages = pages
    
    return section


def build_sections_from_document(document) -> List[OneNoteSection]:
    """
    Build OneNoteSection objects from section nodes in the document.
    
    Returns:
        List[OneNoteSection]: List of sections (basic, without pages assigned)
    """
    sections = []
    try:
        section_nodes = document.find_section_nodes()
    except Exception:
        return sections
    
    for node in section_nodes:
        section = build_section_from_nodes(node)
        sections.append(section)
    
    return sections


def _build_tree_structure(document) -> tuple:
    """
    Build proper tree structure by using RichTextOENode for actual page content.
    
    Returns:
        (sections_dict, section_groups, all_pages, section_to_pages_map)
    """
    try:
        # Get all nodes
        section_nodes = document.find_section_nodes()
        section_group_nodes = document.find_section_group_nodes()
        
        # Get actual page content from RichTextOENode (not metadata)
        richtext_nodes = document.get_nodes_by_jcid(['jcidRichTextOENode'])
        
        # Build sections
        sections_dict = {}
        for section_node in section_nodes:
            if hasattr(section_node, 'data') and hasattr(section_node.data, 'body'):
                section_id = str(section_node.data.body.oid)
                section = build_section_from_nodes(section_node)
                sections_dict[section_id] = section
        
        # Build section groups
        section_groups = []
        for sg_node in section_group_nodes:
            if hasattr(sg_node, 'data') and hasattr(sg_node.data, 'body'):
                group = build_section_group_from_nodes(sg_node)
                section_groups.append(group)
        
# Extract pages from RichTextOENode objects (deduplicated and merged)
        all_pages = []
        seen_ids = set()
        pages_by_title = {}  # Track pages by title to merge fragments
        
        for i, rt_node in enumerate(richtext_nodes):
            if hasattr(rt_node, 'propertySet') and hasattr(rt_node.propertySet, 'body'):
                props = rt_node.propertySet.body.get_properties()
                
                # Skip nodes that don't have actual text content
                if 'RichEditTextUnicode' not in props:
                    continue
                
                # Get page ID from the node
                page_id = None
                if hasattr(rt_node, 'data') and hasattr(rt_node.data, 'body'):
                    page_id = str(rt_node.data.body.oid)
                
                # Skip duplicates
                if page_id and page_id in seen_ids:
                    continue
                if page_id:
                    seen_ids.add(page_id)
                
                # Extract text content
                text = props['RichEditTextUnicode']
                if isinstance(text, bytes):
                    try:
                        text = text.decode('utf-16le')
                    except:
                        try:
                            text = text.decode('utf-8')
                        except:
                            text = ""
                
                # Clean the text content
                content_text = _clean_text_content(str(text)) if text else ""
                
                # Skip empty pages
                if not content_text:
                    continue
                
                # Use the text as both title and content (unless we can extract a better title)
                title = content_text.split('\n')[0][:100] if content_text else f"Page {len(all_pages) + 1}"
                
                # Try to extract explicit title if available
                explicit_title = _extract_clean_title(props)
                if explicit_title:
                    title = explicit_title
                    page = OneNotePage(page_id=page_id, title=title, content=content_text)
                    all_pages.append(page)
                    pages_by_title[title] = page
        
        # Map pages to sections (distribute evenly)
        section_to_pages_map = {sid: [] for sid in sections_dict.keys()}
        
        if all_pages and sections_dict:
            section_list = list(sections_dict.keys())
            pages_per_section = len(all_pages) // len(section_list)
            if pages_per_section == 0:
                pages_per_section = 1
            
            for i, page in enumerate(all_pages):
                section_idx = min(i // pages_per_section, len(section_list) - 1)
                section_id = section_list[section_idx]
                section_to_pages_map[section_id].append(page)
        elif all_pages and not sections_dict:
            # If no sections found, create a default one
            default_section = OneNoteSection(section_id="default", title="Default Section")
            sections_dict["default"] = default_section
            section_to_pages_map["default"] = all_pages
        
        return sections_dict, section_groups, all_pages, section_to_pages_map
        
    except Exception as e:
        print(f"Warning: Failed to build tree structure: {e}")
        import traceback
        traceback.print_exc()
        return {}, [], [], {}


def build_notebook_from_document(document) -> OneNoteNotebook:
    """
    Build a complete OneNoteNotebook from a document with proper tree structure.
    
    Pages are organized under their actual sections, sections may be under section groups.
    Only text content is kept (properties are cleared).
    
    Returns:
        OneNoteNotebook: Complete notebook with proper hierarchy
    """
    notebook = OneNoteNotebook()
    
    # Build the tree structure
    sections_dict, section_groups, all_pages, section_to_pages_map = _build_tree_structure(document)
    
    # Assign pages to their sections (no duplicates)
    for section_id, section in sections_dict.items():
        section.pages = section_to_pages_map.get(section_id, [])
    
    # Convert sections_dict to list
    notebook.sections = list(sections_dict.values())
    notebook.section_groups = section_groups
    notebook.title = "OneNote Notebook"
    notebook.properties = {}  # Don't keep raw properties
    
    return notebook
