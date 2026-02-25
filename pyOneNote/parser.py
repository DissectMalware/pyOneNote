"""
High-level API for parsing OneNote (.one) files.

Example usage:
    from pyOneNote import OneNoteParser
    
    parser = OneNoteParser('example.one')
    files = parser.get_embedded_files()
    for file_guid, file_data in files.items():
        print(f"File: {file_data['extension']}, Size: {len(file_data['content'])}")
    
    # Save embedded files
    parser.save_files('./output')
    
    # Get metadata
    properties = parser.get_properties()
    headers = parser.get_headers()
"""

import os
import uuid
from typing import Dict, List, Tuple, Optional
from pyOneNote.Header import Header
from pyOneNote.OneDocument import OneDocment
from pyOneNote.exporter import (
    build_pages_from_document,
    build_sections_from_document,
    build_notebook_from_document,
)
from pyOneNote.models import OneNotePage, OneNoteSection, OneNoteNotebook


class OneNoteParser:
    """
    Main API for parsing OneNote files.
    
    Attributes:
        file_path (str): Path to the OneNote file
        document (OneDocment): The parsed OneNote document
    """
    
    def __init__(self, file_path: str):
        """
        Initialize the parser with a OneNote file.
        
        Args:
            file_path (str): Path to the .one file
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file is not a valid OneNote file
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        self.file_path = file_path
        
        with open(file_path, 'rb') as f:
            if not self._validate_file(f):
                raise ValueError("Invalid OneNote file format")
            f.seek(0)
            self.document = OneDocment(f)
    
    @staticmethod
    def _validate_file(file) -> bool:
        """
        Validate that the file is a OneNote file.
        
        Args:
            file: File object to validate
            
        Returns:
            bool: True if valid OneNote file
        """
        signature = file.read(16)
        return signature in (
            b"\xE4\x52\x5C\x7B\x8C\xD8\xA7\x4D\xAE\xB1\x53\x78\xD0\x29\x96\xD3",
            b"\xA1\x2F\xFF\x43\xD9\xEF\x76\x4C\x9E\xE2\x10\xEA\x57\x22\x76\x5F",
        )
    
    def get_headers(self) -> Dict:
        """
        Get the OneNote file headers.
        
        Returns:
            Dict: File headers including GUIDs, versions, and metadata
        """
        return self.document.header.convert_to_dictionary()
    
    def get_properties(self) -> List[Dict]:
        """
        Get all properties from the document.
        
        Returns:
            List[Dict]: List of property sets with type, identity, and values
        """
        return self.document.get_properties()
    
    def get_embedded_files(self) -> Dict[str, Dict]:
        """
        Get all embedded files from the document.
        
        Returns:
            Dict[str, Dict]: Dictionary with file GUIDs as keys and file data as values.
                             Each file data contains:
                             - 'extension': File extension
                             - 'content': File content as bytes
                             - 'identity': Object identity
        """
        files = self.document.get_files()
        # Normalize content: support bytes (returned by parser) or hex string (from JSON path)
        result = {}
        for guid, file_data in files.items():
            content = file_data.get('content')
            if isinstance(content, str):
                try:
                    content_bytes = bytes.fromhex(content)
                except ValueError:
                    # Fall back: encode string as UTF-8
                    content_bytes = content.encode('utf-8')
            elif isinstance(content, (bytes, bytearray)):
                content_bytes = bytes(content)
            else:
                content_bytes = b''

            result[guid] = {
                'extension': file_data.get('extension', ''),
                'content': content_bytes,
                'identity': file_data.get('identity', '')
            }
        return result
    
    def get_json(self) -> Dict:
        """
        Get the entire document as a JSON-serializable dictionary.
        
        Returns:
            Dict: Complete document structure with headers, properties, and files
        """
        return self.document.get_json()
    
    def get_text(self) -> List[OneNotePage]:
        """
        Extract and return OneNotePage objects from the document.
        
        Returns:
            List[OneNotePage]: List of page objects with text content extracted
        """
        try:
            return build_pages_from_document(self.document)
        except Exception:
            return []
    
    def save_files(self, output_dir: str, extension: str = '') -> int:
        """
        Extract and save all embedded files to a directory.
        
        Args:
            output_dir (str): Directory to save files to
            extension (str): Optional extension to append to filenames
            
        Returns:
            int: Number of files extracted
            
        Raises:
            OSError: If unable to create output directory or write files
        """
        os.makedirs(output_dir, exist_ok=True)
        
        if extension and not extension.startswith('.'):
            extension = '.' + extension
        
        files = self.get_embedded_files()
        counter = 0
        
        for file_guid, file_data in files.items():
            filename = f"file_{counter}{file_data['extension']}{extension}"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'wb') as f:
                f.write(file_data['content'])
            counter += 1
        
        return counter
    
    def get_file_count(self) -> int:
        """
        Get the number of embedded files.
        
        Returns:
            int: Number of embedded files
        """
        return len(self.get_embedded_files())
    
    def get_file_extensions(self) -> List[str]:
        """
        Get list of all embedded file extensions.
        
        Returns:
            List[str]: List of file extensions
        """
        files = self.get_embedded_files()
        extensions = [f['extension'] for f in files.values()]
        return list(set(extensions))  # Return unique extensions
    
    def get_pages(self) -> List[OneNotePage]:
        """
        Get all pages from the document as OneNotePage objects.
        
        Returns:
            List[OneNotePage]: List of all pages with content extracted
        """
        return self.get_text()
    
    def get_sections(self) -> List[OneNoteSection]:
        """
        Get all sections from the document as OneNoteSection objects.
        
        Returns:
            List[OneNoteSection]: List of sections (without pages assigned yet)
        """
        try:
            return build_sections_from_document(self.document)
        except Exception:
            return []
    
    def get_notebook(self) -> OneNoteNotebook:
        """
        Get the entire notebook as a OneNoteNotebook object with all sections and pages.
        
        Returns:
            OneNoteNotebook: Complete notebook structure with sections and pages populated
        """
        try:
            return build_notebook_from_document(self.document)
        except Exception:
            return OneNoteNotebook()
