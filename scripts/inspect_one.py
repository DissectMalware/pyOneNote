"""
Diagnostic script to inspect one .one file and report embedded file metadata.

Usage:
    python scripts/inspect_one.py --one-file "C:\\Users\\oz303\\Oz\\MyNotebook\\New Section 1.one"

Prints header summary, property count, file entries and sizes.
"""
import argparse
import json
import os
import sys
from pathlib import Path

# Ensure local package can be imported if running from repo root
try:
    from pyOneNote import OneNoteParser
except Exception:
    pass


def inspect_one(one_file_path: str):
    p = Path(one_file_path)
    if not p.exists():
        print(f"File not found: {one_file_path}")
        return 1

    try:
        parser = OneNoteParser(str(p))
    except Exception as e:
        print(f"Failed to parse {one_file_path}: {e}")
        return 2

    print(f"Parsed: {one_file_path}")

    headers = parser.get_headers()
    print("Headers summary:")
    for k, v in headers.items():
        print(f"  {k}: {v}")

    props = parser.get_properties()
    print(f"Properties count: {len(props)}")
    # Search properties for embedded/picture containers
    found = False
    for i, prop in enumerate(props):
        val = prop.get('val', {})
        if 'EmbeddedFileContainer' in val or 'PictureContainer' in val:
            if not found:
                print('\nFound potential embedded/picture containers in properties:')
                found = True
            print(f"  Property #{i}: type={prop.get('type')} identity={prop.get('identity')}")
            for k, v in val.items():
                print(f"    {k}: {v}")
    if not found:
        print('No EmbeddedFileContainer or PictureContainer keys found in properties.')

    files = parser.get_embedded_files()
    print(f"Embedded file entries: {len(files)}")
    if files:
        for guid, f in files.items():
            print(f"  GUID: {guid}  ext: {f['extension']}  size: {len(f['content'])}  identity: {f['identity']}")

    # Enumerate file node types present in the document
    try:
        node_types = {}

        def traverse(node_list):
            for fragment in node_list.fragments:
                for fn in fragment.fileNodes:
                    t = fn.file_node_header.file_node_type
                    node_types[t] = node_types.get(t, 0) + 1
                    # traverse children lists
                    for child in fn.children:
                        traverse(child)

        traverse(parser.document.root_file_node_list)

        print('\nFile node types and counts:')
        for t, c in sorted(node_types.items(), key=lambda x: -x[1]):
            print(f"  {t}: {c}")
    except Exception as e:
        print(f"Failed to enumerate node types: {e}")

    # Print JSON top-level keys (sizes)
    djson = parser.get_json()
    print("JSON sizes:")
    print(f"  headers keys: {len(djson.get('headers', {}))}")
    print(f"  properties items: {len(djson.get('properties', []))}")
    print(f"  files entries: {len(djson.get('files', {}))}")

    return 0


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--one-file', '-f', required=True, help='Path to .one file to inspect')
    args = ap.parse_args()
    sys.exit(inspect_one(args.one_file))
