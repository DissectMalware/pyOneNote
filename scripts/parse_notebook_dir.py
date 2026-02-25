"""
Simple script to parse a directory containing OneNote notebooks (.one files).

Usage:
    python scripts/parse_notebook_dir.py --notebook-dir "C:\\Users\\oz303\\Oz\\MyNotebook" --output-dir "C:\\temp\\onenote_output"

The script will recursively find `.one` files, parse them with `OneNoteParser`, and extract embedded files into
an output subdirectory per notebook.
"""
import argparse
import os
import sys
from pathlib import Path

from pyOneNote import OneNoteParser


def parse_notebook_directory(notebook_dir: str, output_dir: str):
    notebook_path = Path(notebook_dir)
    if not notebook_path.exists() or not notebook_path.is_dir():
        print(f"Notebook directory not found: {notebook_dir}")
        sys.exit(1)

    out_root = Path(output_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    one_files = list(notebook_path.rglob('*.one'))
    if not one_files:
        print(f"No .one files found under: {notebook_dir}")
        return

    for one_file in one_files:
        print(f"Parsing: {one_file}")
        try:
            parser = OneNoteParser(str(one_file))
        except Exception as e:
            print(f"  Failed to open {one_file}: {e}")
            continue

        nb_out = out_root / one_file.stem
        nb_out.mkdir(parents=True, exist_ok=True)
        try:
            count = parser.save_files(str(nb_out))
            print(f"  Extracted {count} file(s) to: {nb_out}")
        except Exception as e:
            print(f"  Failed to save files for {one_file}: {e}")


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--notebook-dir', '-d', required=True, help='Path to directory containing .one files')
    p.add_argument('--output-dir', '-o', default='./onenote_output', help='Output directory for extracted files')
    args = p.parse_args()

    parse_notebook_directory(args.notebook_dir, args.output_dir)
