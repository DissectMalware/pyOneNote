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


def _iter_sections(notebook):
    for section in notebook.sections:
        yield section
    for group in notebook.section_groups:
        yield from _iter_group_sections(group)


def _iter_group_sections(group):
    for section in group.sections:
        yield section
    for child in group.section_groups:
        yield from _iter_group_sections(child)


@pytest.mark.integration
def test_notebook_api_contract_fields_and_types():
    notebook_dir = _get_notebook_dir()
    if not notebook_dir.exists():
        pytest.skip("Notebook dir not found. Set PYONENOTE_NOTEBOOK_DIR to run this test.")

    notebook = OneNoteNotebook(path=str(notebook_dir))

    assert isinstance(notebook.notebook_id, str)
    assert notebook.notebook_id
    assert isinstance(notebook.title, str)
    assert notebook.title
    assert isinstance(notebook.sections, list)
    assert isinstance(notebook.section_groups, list)
    assert isinstance(notebook.properties, dict)
    assert "path" in notebook.properties

    for section in _iter_sections(notebook):
        assert isinstance(section.section_id, str)
        assert section.section_id
        assert isinstance(section.title, str)
        assert section.title
        assert isinstance(section.pages, list)
        assert isinstance(section.properties, dict)
        for key in ("file_name", "file_path", "page_count"):
            assert key in section.properties

        for page in section.pages:
            assert isinstance(page.page_id, str)
            assert page.page_id
            assert isinstance(page.title, str)
            assert page.title
            assert isinstance(page.content, str)
            assert isinstance(page.properties, dict)
            # Keep metadata minimal and relevant.
            assert set(page.properties.keys()).issubset(
                {
                    "CachedTitleString",
                    "CreationTimeStamp",
                    "LastModifiedTimeStamp",
                    "LastModifiedTime",
                    "Author",
                    "AuthorMostRecent",
                    "LanguageID",
                    "PageLevel",
                    "IsConflictPage",
                    "TopologyCreationTimeStamp",
                }
            )

