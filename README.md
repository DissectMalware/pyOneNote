# pyOneNote
`pyOneNote` is a Python library for parsing Microsoft OneNote `.one` files.

The package supports:
- embedded file extraction
- text extraction (including Hebrew/Unicode)
- notebook object export with hierarchy:
  - `Notebook -> SectionGroup -> Section -> Page`

## Installation

Install from the local repository root:

```bash
pip install .
```

For editable development installs:

```bash
pip install -e .
```

## Python API

### Parse a notebook directory (recommended)

```python
from pyOneNote.models import OneNoteNotebook

notebook = OneNoteNotebook(path=r"C:\Users\you\MyNotebook")

print(notebook.title)
for section in notebook.sections:
    print(section.title, len(section.pages))
for group in notebook.section_groups:
    print(group.title, len(group.sections), len(group.section_groups))
```

### Parse a single `.one` file

```python
from pyOneNote import OneNoteParser

parser = OneNoteParser(r"C:\path\to\section.one")
pages = parser.get_pages()
files = parser.get_embedded_files()
```

## Data Contract

The exported model keeps readable text and important metadata:
- `OneNoteNotebook`: `notebook_id`, `title`, `sections`, `section_groups`, `properties`
- `OneNoteSectionGroup`: `group_id`, `title`, `sections`, `section_groups`, `properties`
- `OneNoteSection`: `section_id`, `title`, `pages`, `properties`
- `OneNotePage`: `page_id`, `title`, `content`, `properties`

Notes:
- Directory nesting maps to nested section groups.
- Ordering is deterministic (stable sort by name/path).
- Page text is cleaned to reduce header/timestamp noise.

## CLI

Extract embedded files:

```bash
pyonenote -f example.one
pyonenote -f example.one -o output_dir
pyonenote -f example.one -o output_dir -e bin
```

Generate JSON only:

```bash
pyonenote -f example.one -j
```

Usage:

```text
pyonenote [-h] -f FILE [-o OUTPUT_DIR] [-e EXTENSION] [-j]
```

## Testing

Run all tests:

```bash
python -m pytest -q tests
```

Integration tests can use a local notebook path:

```bash
set PYONENOTE_NOTEBOOK_DIR=C:\path\to\MyNotebook
python -m pytest -q tests\test_notebook_regression.py
```

Standalone regression script:

```bash
python scripts\regression_check_notebook.py --notebook-dir "C:\path\to\MyNotebook"
```
