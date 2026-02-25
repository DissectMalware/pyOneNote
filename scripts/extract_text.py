"""
Extract readable text content from a .one file by scanning properties and node values.

Usage:
    python scripts/extract_text.py -f "C:\\Users\\oz303\\Oz\\MyNotebook\\New Section 1.one" -o .\output_text

This script looks for string-like values in properties and writes a plain text file with found snippets.
"""
import argparse
import os
import sys
from pathlib import Path

try:
    from pyOneNote import OneNoteParser
except Exception:
    pass


def extract_strings(obj, min_len=5):
    res = []
    if isinstance(obj, str):
        if len(obj) >= min_len:
            res.append(obj)
    elif isinstance(obj, (bytes, bytearray)):
        try:
            s = obj.decode('utf-8', errors='ignore')
            if len(s) >= min_len:
                res.append(s)
        except Exception:
            pass
    elif isinstance(obj, dict):
        for v in obj.values():
            res.extend(extract_strings(v, min_len))
    elif isinstance(obj, (list, tuple, set)):
        for v in obj:
            res.extend(extract_strings(v, min_len))
    return res


def extract_from_file(one_file: str, out_dir: str):
    p = Path(one_file)
    if not p.exists():
        print(f"File not found: {one_file}")
        return 1

    try:
        parser = OneNoteParser(str(p))
    except Exception as e:
        print(f"Failed to parse {one_file}: {e}")
        return 2

    os.makedirs(out_dir, exist_ok=True)
    out_path = Path(out_dir) / (p.stem + '_text.txt')

    snippets = []

    # Scan properties
    props = parser.get_properties()
    for prop in props:
        snippets.extend(extract_strings(prop.get('val', {}), min_len=4))

    # Also scan headers
    headers = parser.get_headers()
    for v in headers.values():
        snippets.extend(extract_strings(v, min_len=4))

    # Deduplicate and sort by length
    uniq = sorted(set([s.strip() for s in snippets if s and s.strip()]), key=lambda x: -len(x))

    with open(out_path, 'w', encoding='utf-8') as fh:
        if not uniq:
            fh.write('No readable text snippets found.\n')
        else:
            for s in uniq:
                fh.write(s + '\n\n')

    print(f"Wrote {len(uniq)} snippet(s) to: {out_path}")
    return 0


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('-f', '--one-file', required=True, help='Path to .one file to extract')
    ap.add_argument('-o', '--output-dir', default='./text_output', help='Directory to write extracted text')
    args = ap.parse_args()
    sys.exit(extract_from_file(args.one_file, args.output_dir))
