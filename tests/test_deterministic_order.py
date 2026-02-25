import os
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pyOneNote.models import OneNoteNotebook


def _get_notebook_dir() -> Path:
    env_path = os.environ.get("PYONENOTE_NOTEBOOK_DIR", "").strip()
    if env_path:
        return Path(env_path)
    return Path(r"C:\Users\oz303\Oz\MyNotebook")


def _page_snapshot(page):
    return {
        "id": page.page_id,
        "title": page.title,
        "content": page.content,
        "metadata_keys": sorted((page.properties or {}).keys()),
    }


def _section_snapshot(section):
    return {
        "id": section.section_id,
        "title": section.title,
        "properties": dict(section.properties or {}),
        "pages": [_page_snapshot(p) for p in section.pages],
    }


def _group_snapshot(group):
    return {
        "id": group.group_id,
        "title": group.title,
        "properties": dict(group.properties or {}),
        "sections": [_section_snapshot(s) for s in group.sections],
        "groups": [_group_snapshot(g) for g in group.section_groups],
    }


def _notebook_snapshot(notebook):
    return {
        "id": notebook.notebook_id,
        "title": notebook.title,
        "properties": dict(notebook.properties or {}),
        "sections": [_section_snapshot(s) for s in notebook.sections],
        "groups": [_group_snapshot(g) for g in notebook.section_groups],
    }


@pytest.mark.integration
def test_parsing_is_deterministic_for_ordering():
    notebook_dir = _get_notebook_dir()
    if not notebook_dir.exists():
        pytest.skip("Notebook dir not found. Set PYONENOTE_NOTEBOOK_DIR to run this test.")

    first = OneNoteNotebook(path=str(notebook_dir))
    second = OneNoteNotebook(path=str(notebook_dir))

    assert _notebook_snapshot(first) == _notebook_snapshot(second)

