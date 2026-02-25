import os
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.regression_check_notebook import validate_notebook
from pyOneNote.models import OneNoteNotebook


def _get_notebook_dir() -> Path:
    env_path = os.environ.get("PYONENOTE_NOTEBOOK_DIR", "").strip()
    if env_path:
        return Path(env_path)
    default_path = Path(r"C:\Users\oz303\Oz\MyNotebook")
    return default_path


@pytest.mark.integration
def test_real_notebook_regression():
    notebook_dir = _get_notebook_dir()
    if not notebook_dir.exists():
        pytest.skip(
            "Notebook dir not found. Set PYONENOTE_NOTEBOOK_DIR to run this test."
        )

    notebook = OneNoteNotebook(path=str(notebook_dir))
    errors = validate_notebook(notebook)
    assert not errors, "Regression mismatches:\n" + "\n".join(f"- {e}" for e in errors)


def test_directory_parsing_keeps_nested_groups_shape():
    notebook_dir = _get_notebook_dir()
    if not notebook_dir.exists():
        pytest.skip(
            "Notebook dir not found. Set PYONENOTE_NOTEBOOK_DIR to run this test."
        )

    notebook = OneNoteNotebook(path=str(notebook_dir))
    # Guard important contract points.
    assert notebook.title == "MyNotebook"
    assert len(notebook.sections) == 2
    assert len(notebook.section_groups) == 1
    assert notebook.section_groups[0].title == "SectionGroup"
