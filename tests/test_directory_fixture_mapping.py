import sys
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pyOneNote.exporter as exporter
import pyOneNote.parser as parser_mod
from pyOneNote.models import OneNoteNotebook, OneNotePage


FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "notebook_tree"


class _FakeParser:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.document = SimpleNamespace(fake_path=Path(file_path))


def _fake_build_pages_from_document(document):
    stem = document.fake_path.stem
    return [
        OneNotePage(
            page_id=f"{stem}-1",
            title=f"{stem} page",
            content=f"{stem} content",
            properties={},
        )
    ]


def test_build_notebook_from_directory_fixture(monkeypatch):
    monkeypatch.setattr(parser_mod, "OneNoteParser", _FakeParser)
    monkeypatch.setattr(exporter, "build_pages_from_document", _fake_build_pages_from_document)

    notebook = exporter.build_notebook_from_directory(str(FIXTURE_ROOT))

    assert notebook.title == "notebook_tree"
    assert [s.title for s in notebook.sections] == ["a", "B"]
    assert [g.title for g in notebook.section_groups] == ["groupA", "GroupZ"]

    group_a = notebook.section_groups[0]
    assert [s.title for s in group_a.sections] == ["d"]
    assert [g.title for g in group_a.section_groups] == ["sub"]
    assert [s.title for s in group_a.section_groups[0].sections] == ["e"]

    group_z = notebook.section_groups[1]
    assert [s.title for s in group_z.sections] == ["c"]

    assert notebook.sections[0].pages[0].title == "a page"
    assert notebook.sections[1].pages[0].title == "B page"


def test_onenotebook_path_uses_directory_builder(monkeypatch):
    monkeypatch.setattr(parser_mod, "OneNoteParser", _FakeParser)
    monkeypatch.setattr(exporter, "build_pages_from_document", _fake_build_pages_from_document)

    notebook = OneNoteNotebook(path=str(FIXTURE_ROOT))
    assert notebook.title == "notebook_tree"
    assert len(notebook.sections) == 2
    assert len(notebook.section_groups) == 2
