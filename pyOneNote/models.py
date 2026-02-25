from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from pathlib import Path


@dataclass
class OneNotePage:
    page_id: Optional[str] = None
    title: Optional[str] = None
    content: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Parse and extract data from properties if not explicitly provided."""
        if self.properties and isinstance(self.properties, dict):
            # Auto-extract title from properties if not provided
            if not self.title:
                self.title = self._extract_title_from_properties()
            
            # Auto-extract content from properties if not provided
            if not self.content:
                self.content = self._extract_content_from_properties()
            
            # Clear properties after extraction to keep only text
            self.properties = {}

    def _extract_title_from_properties(self) -> Optional[str]:
        """Try to extract title from common property keys."""
        candidates = ["title", "name", "pageTitle", "PageTitle", "displayName"]
        low_map = {k.lower(): k for k in self.properties.keys()}
        for cand in candidates:
            key = low_map.get(cand.lower())
            if key is not None:
                v = self.properties[key]
                if isinstance(v, (bytes, bytearray)):
                    try:
                        return v.decode("utf-16le").strip()
                    except Exception:
                        pass
                elif isinstance(v, str):
                    return v.strip()
        return None

    def _extract_content_from_properties(self) -> str:
        """Try to extract readable content from properties."""
        found = []
        self._collect_strings(self.properties, found)
        return " ".join(s.strip() for s in found if s and s.strip())

    def _collect_strings(self, value: Any, out: List[str]) -> None:
        """Recursively collect all strings from nested structures."""
        if value is None:
            return
        if isinstance(value, str):
            out.append(value)
        elif isinstance(value, (bytes, bytearray)):
            try:
                decoded = bytes(value).decode("utf-16le")
                if decoded:
                    out.append(decoded)
            except Exception:
                try:
                    decoded = bytes(value).decode("utf-8")
                    if decoded:
                        out.append(decoded)
                except Exception:
                    pass
        elif isinstance(value, dict):
            for v in value.values():
                self._collect_strings(v, out)
        elif isinstance(value, (list, tuple, set)):
            for item in value:
                self._collect_strings(item, out)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_id": self.page_id,
            "title": self.title,
            "content": self.content,
        }


@dataclass
class OneNoteSection:
    section_id: Optional[str] = None
    title: Optional[str] = None
    pages: List[OneNotePage] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Parse and extract data from properties if not explicitly provided."""
        if self.properties and isinstance(self.properties, dict):
            if not self.title:
                self.title = self._extract_title_from_properties()
            # Clear properties after extraction
            self.properties = {}

    def _extract_title_from_properties(self) -> Optional[str]:
        """Try to extract title from common property keys."""
        candidates = ["title", "name", "sectionTitle", "SectionTitle", "displayName"]
        low_map = {k.lower(): k for k in self.properties.keys()}
        for cand in candidates:
            key = low_map.get(cand.lower())
            if key is not None:
                v = self.properties[key]
                if isinstance(v, (bytes, bytearray)):
                    try:
                        return v.decode("utf-16le").strip()
                    except Exception:
                        pass
                elif isinstance(v, str):
                    return v.strip()
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "section_id": self.section_id,
            "title": self.title,
            "pages": [p.to_dict() for p in self.pages],
        }


@dataclass
class OneNoteSectionGroup:
    group_id: Optional[str] = None
    title: Optional[str] = None
    sections: List[OneNoteSection] = field(default_factory=list)
    section_groups: List['OneNoteSectionGroup'] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Parse and extract data from properties if not explicitly provided."""
        if self.properties and isinstance(self.properties, dict):
            if not self.title:
                self.title = self._extract_title_from_properties()
            # Clear properties after extraction
            self.properties = {}

    def _extract_title_from_properties(self) -> Optional[str]:
        """Try to extract title from common property keys."""
        candidates = ["title", "name", "groupTitle", "GroupTitle", "displayName"]
        low_map = {k.lower(): k for k in self.properties.keys()}
        for cand in candidates:
            key = low_map.get(cand.lower())
            if key is not None:
                v = self.properties[key]
                if isinstance(v, (bytes, bytearray)):
                    try:
                        return v.decode("utf-16le").strip()
                    except Exception:
                        pass
                elif isinstance(v, str):
                    return v.strip()
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "group_id": self.group_id,
            "title": self.title,
            "sections": [s.to_dict() for s in self.sections],
            "section_groups": [g.to_dict() for g in self.section_groups],
        }


@dataclass
class OneNoteNotebook:
    notebook_id: Optional[str] = None
    title: Optional[str] = None
    sections: List[OneNoteSection] = field(default_factory=list)
    section_groups: List[OneNoteSectionGroup] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    path: Optional[str] = None  # Path to .one file for auto-parsing

    def __post_init__(self):
        """Parse and extract data from path or properties."""
        # If a path is provided, parse the notebook file
        if self.path:
            self._parse_from_path(self.path)
        elif not self.title:
            self.title = self._extract_title_from_properties()

    def _parse_from_path(self, file_path: str) -> None:
        """
        Parse a OneNote .one file from the given path and populate the notebook structure.
        
        Args:
            file_path: Path to a .one file or directory containing .one files
        """
        try:
            # Import here to avoid circular imports
            from .parser import OneNoteParser
            
            path = Path(file_path)
            
            # If path is a directory, find the first .one file
            if path.is_dir():
                one_files = list(path.rglob("*.one"))
                if not one_files:
                    raise FileNotFoundError(f"No .one files found in {file_path}")
                file_path = str(one_files[0])
            
            # Parse the file
            parser = OneNoteParser(file_path)
            parsed_notebook = parser.get_notebook()
            
            # Copy parsed data to self
            self.notebook_id = parsed_notebook.notebook_id
            self.title = parsed_notebook.title
            self.sections = parsed_notebook.sections
            self.section_groups = parsed_notebook.section_groups
            self.properties = parsed_notebook.properties
            
        except Exception as e:
            raise RuntimeError(f"Failed to parse notebook from {file_path}: {e}")

    def _extract_title_from_properties(self) -> Optional[str]:
        """Try to extract title from common property keys."""
        if not self.properties or not isinstance(self.properties, dict):
            return None
        candidates = ["title", "name", "notebookTitle", "NotebookTitle", "displayName"]
        low_map = {k.lower(): k for k in self.properties.keys()}
        for cand in candidates:
            key = low_map.get(cand.lower())
            if key is not None:
                v = self.properties[key]
                if isinstance(v, (bytes, bytearray)):
                    try:
                        return v.decode("utf-16le").strip()
                    except Exception:
                        pass
                elif isinstance(v, str):
                    return v.strip()
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "notebook_id": self.notebook_id,
            "title": self.title,
            "sections": [s.to_dict() for s in self.sections],
            "section_groups": [g.to_dict() for g in self.section_groups],
        }
