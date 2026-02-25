import re
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from .models import OneNotePage, OneNoteSection, OneNoteSectionGroup, OneNoteNotebook


IMPORTANT_PAGE_METADATA_KEYS = {
    "CachedTitleString",
    "CreationTimeStamp",
    "LastModifiedTimeStamp",
    "LastModifiedTime",
    "Author",
    "AuthorMostRecent",
    "LanguageID",
    "PageLevel",
    "IsConflictPage",
}


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
_time_only_re = re.compile(r"^\d{1,2}:\d{2}$")
_iso_datetime_re = re.compile(r"^\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2}:\d{2}(?:\.\d+)?)?$")


def _normalize_join(strings: Iterable[str]) -> str:
    joined = " ".join(s.strip() for s in strings if s is not None and str(s).strip())
    # collapse multiple whitespace
    return _whitespace_re.sub(" ", joined).strip()


def _is_header_like_snippet(text: str, page_title: str) -> bool:
    """
    Filter snippets that are page header artifacts rather than body content.
    """
    t = (text or "").strip()
    if not t:
        return True
    if page_title and t == page_title.strip():
        return True
    if _time_only_re.match(t):
        return True
    if _iso_datetime_re.match(t):
        return True
    if all(_iso_datetime_re.match(part) for part in t.split() if part):
        return True
    # Common OneNote date header line in Hebrew locales.
    if t.startswith("יום ") and any(ch.isdigit() for ch in t):
        return True
    return False


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


def _decode_text_value(value: Any) -> str:
    """Decode a value into text while preserving Unicode (including Hebrew)."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if not isinstance(value, (bytes, bytearray)):
        return str(value)

    raw = bytes(value)
    for encoding in ("utf-16le", "utf-16", "utf-8", "latin-1"):
        try:
            return raw.decode(encoding)
        except Exception:
            continue
    return ""


def _extract_important_page_metadata(props: Dict[str, Any]) -> Dict[str, Any]:
    metadata: Dict[str, Any] = {}
    if not isinstance(props, dict):
        return metadata

    for key in IMPORTANT_PAGE_METADATA_KEYS:
        if key not in props:
            continue
        value = props[key]
        if isinstance(value, (bytes, bytearray, str)):
            metadata[key] = _clean_text_content(_decode_text_value(value))
        else:
            metadata[key] = value

    return metadata


def _parse_datetime(value: Any) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _extract_text_from_richtext_properties(props: Dict[str, Any]) -> str:
    text = ""
    if "RichEditTextUnicode" in props:
        text = _decode_text_value(props.get("RichEditTextUnicode"))
    elif "TextExtendedAscii" in props:
        raw = str(props.get("TextExtendedAscii", ""))
        try:
            text = bytes.fromhex(raw).decode("ascii", errors="ignore")
        except Exception:
            text = raw
    text = _clean_text_content(text)
    # Remove inline ISO datetime artifacts that often come from metadata serialization.
    text = re.sub(r"\b\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2}:\d{2}(?:\.\d+)?)?\b", "", text)
    return _clean_text_content(text)


def _latest_nodes_by_oid(nodes) -> List[Any]:
    """
    Keep only the latest node version for each OID.
    Latest preference:
    1) greater LastModifiedTime (if present)
    2) larger traversal index as fallback
    """
    latest: Dict[str, tuple] = {}
    for idx, node in enumerate(nodes):
        if not hasattr(node, "data") or not hasattr(node.data, "body"):
            continue
        oid = str(node.data.body.oid)
        props = {}
        if hasattr(node, "propertySet") and hasattr(node.propertySet, "body"):
            props = node.propertySet.body.get_properties()
        lm = _parse_datetime(props.get("LastModifiedTime")) if isinstance(props, dict) else None
        current = latest.get(oid)
        if current is None:
            latest[oid] = (lm, idx, node)
            continue
        prev_lm, prev_idx, _ = current
        if lm and (prev_lm is None or lm >= prev_lm):
            latest[oid] = (lm, idx, node)
        elif lm is None and idx >= prev_idx:
            latest[oid] = (lm, idx, node)
    return [v[2] for v in sorted(latest.values(), key=lambda x: x[1])]


def _build_page_metadata_candidates(document) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    try:
        page_meta_nodes = _latest_nodes_by_oid(document.get_nodes_by_jcid(["jcidPageMetaData"]))
    except Exception:
        return candidates

    for idx, node in enumerate(page_meta_nodes):
        if not hasattr(node, "propertySet") or not hasattr(node.propertySet, "body"):
            continue
        props = node.propertySet.body.get_properties()
        title = _clean_text_content(_decode_text_value(props.get("CachedTitleString", ""))).strip("\x00").strip()
        created = _parse_datetime(props.get("TopologyCreationTimeStamp"))
        page_id = str(node.data.body.oid) if hasattr(node, "data") and hasattr(node.data, "body") else f"meta-{idx}"
        metadata = _extract_important_page_metadata(props)
        metadata["TopologyCreationTimeStamp"] = props.get("TopologyCreationTimeStamp")
        candidates.append(
            {
                "page_id": page_id,
                "title": title,
                "created": created,
                "metadata": metadata,
            }
        )

    # deterministic order by creation time then id
    candidates.sort(key=lambda c: ((c["created"] or datetime.min), c["page_id"]))

    # Deduplicate repeated metadata entries across object spaces/revisions.
    deduped: List[Dict[str, Any]] = []
    seen = set()
    for c in candidates:
        title_key = (c["title"] or "").strip().lower()
        created = c["created"]
        created_key = created.replace(microsecond=0) if isinstance(created, datetime) else None
        key = (title_key, created_key)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(c)

    return deduped


def _extract_clean_title(props: Dict[str, Any]) -> Optional[str]:
    """Extract just the title text, filtering out metadata and special formats."""
    candidates = ["title", "name", "pageTitle", "PageTitle", "displayName", "CachedTitleString"]
    low_map = {k.lower(): k for k in props.keys()}
    
    for cand in candidates:
        key = low_map.get(cand.lower())
        if key is not None:
            v = props[key]
            if isinstance(v, (bytes, bytearray)):
                title = _clean_text_content(_decode_text_value(v).strip())
                if title and not title.startswith('<') and len(title) < 200:
                    return title
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
    Build pages from rich-text nodes with clean text and selected metadata.
    """
    pages: List[OneNotePage] = []
    seen_signatures = set()

    # 1) Build page skeletons from page metadata (best source for page boundaries/title)
    meta_pages = _build_page_metadata_candidates(document)

    # 2) Collect latest rich-text snippets
    try:
        richtext_nodes = _latest_nodes_by_oid(document.get_nodes_by_jcid(["jcidRichTextOENode"]))
    except Exception:
        richtext_nodes = []

    snippets: List[Dict[str, Any]] = []
    for node in richtext_nodes:
        if not hasattr(node, "propertySet") or not hasattr(node.propertySet, "body"):
            continue
        props = node.propertySet.body.get_properties()
        text = _extract_text_from_richtext_properties(props)
        if not text:
            continue
        modified = _parse_datetime(props.get("LastModifiedTime"))
        snippets.append(
            {
                "text": text,
                "modified": modified,
                "metadata": _extract_important_page_metadata(props),
            }
        )

    if meta_pages:
        # Assign snippets to nearest page creation timestamp.
        bucketed: List[List[Dict[str, Any]]] = [[] for _ in range(len(meta_pages))]
        for snip in snippets:
            if snip["modified"] is None:
                bucketed[0].append(snip)
                continue

            nearest_index = 0
            nearest_delta = None
            for i, meta in enumerate(meta_pages):
                created = meta["created"]
                if created is None:
                    continue
                delta = abs((snip["modified"] - created).total_seconds())
                if nearest_delta is None or delta < nearest_delta:
                    nearest_delta = delta
                    nearest_index = i
            bucketed[nearest_index].append(snip)

        for i, meta in enumerate(meta_pages):
            title = meta["title"] or f"Page {i + 1}"
            parts: List[str] = []
            for snip in bucketed[i]:
                t = snip["text"].strip()
                if _is_header_like_snippet(t, title):
                    continue
                if t not in parts:
                    parts.append(t)
            if not parts:
                # Fallback: keep at least one meaningful snippet even if it equals title.
                preferred = None
                for snip in bucketed[i]:
                    t = snip["text"].strip()
                    if not t or _time_only_re.match(t) or _iso_datetime_re.match(t):
                        continue
                    if title and (t == title or title in t or t in title):
                        preferred = t
                        break
                    if preferred is None:
                        preferred = t
                if preferred:
                    parts.append(preferred)
            content = _clean_text_content("\n".join(parts))

            # Keep page even if content is empty; title from metadata is still useful.
            signature = (title.strip(), content.strip())
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)

            page_metadata = dict(meta["metadata"])
            # Merge sparse metadata from snippets.
            for snip in bucketed[i]:
                for k, v in snip["metadata"].items():
                    if k not in page_metadata or not page_metadata[k]:
                        page_metadata[k] = v

            pages.append(
                OneNotePage(
                    page_id=meta["page_id"],
                    title=title,
                    content=content,
                    properties=page_metadata,
                )
            )
        return pages

    # Fallback path when page metadata is unavailable.
    for i, snip in enumerate(snippets):
        title = f"Page {i + 1}"
        signature = (title.strip(), snip["text"].strip())
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        pages.append(
            OneNotePage(
                page_id=f"page-{i}",
                title=title,
                content=snip["text"],
                properties=snip["metadata"],
            )
        )
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
        
        # Extract pages once via the reliable rich-text path.
        all_pages = build_pages_from_document(document)
        
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


def build_notebook_from_directory(notebook_dir: str) -> OneNoteNotebook:
    """
    Build a notebook hierarchy from a directory that contains .one files.

    Mapping:
    - directory -> OneNoteSectionGroup
    - .one file -> OneNoteSection
    - extracted text nodes -> OneNotePage
    """
    root = Path(notebook_dir)
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Notebook directory not found: {notebook_dir}")

    from .parser import OneNoteParser

    def _build_group(dir_path: Path) -> OneNoteSectionGroup:
        group = OneNoteSectionGroup(
            group_id=str(dir_path.resolve()),
            title=dir_path.name,
            sections=[],
            section_groups=[],
            properties={
                "path": str(dir_path.resolve()),
            },
        )

        one_files = sorted(dir_path.glob("*.one"), key=lambda p: p.name.lower())
        for one_file in one_files:
            parser = OneNoteParser(str(one_file))
            pages = build_pages_from_document(parser.document)
            section = OneNoteSection(
                section_id=str(one_file.resolve()),
                title=one_file.stem,
                pages=pages,
                properties={
                    "file_name": one_file.name,
                    "file_path": str(one_file.resolve()),
                    "page_count": len(pages),
                },
            )
            group.sections.append(section)

        subdirs = sorted([p for p in dir_path.iterdir() if p.is_dir()], key=lambda p: p.name.lower())
        for subdir in subdirs:
            child_group = _build_group(subdir)
            if child_group.sections or child_group.section_groups:
                group.section_groups.append(child_group)

        group.properties["section_count"] = len(group.sections)
        group.properties["section_group_count"] = len(group.section_groups)
        return group

    root_group = _build_group(root)
    notebook = OneNoteNotebook(
        notebook_id=str(root.resolve()),
        title=root.name,
        sections=root_group.sections,
        section_groups=root_group.section_groups,
        properties={
            "path": str(root.resolve()),
            "section_count": len(root_group.sections),
            "section_group_count": len(root_group.section_groups),
        },
    )
    return notebook
