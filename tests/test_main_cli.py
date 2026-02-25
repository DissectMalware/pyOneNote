import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pyOneNote.Main as main_mod


def test_main_passes_file_path_to_processor(monkeypatch, tmp_path):
    sample_file = tmp_path / "sample.one"
    sample_file.write_bytes(b"fixture")

    called = {}

    def _fake_process(file_path, output_dir, extension, json_output):
        called["file_path"] = file_path
        called["output_dir"] = output_dir
        called["extension"] = extension
        called["json_output"] = json_output
        return "{}"

    monkeypatch.setattr(main_mod, "process_onenote_file", _fake_process)
    monkeypatch.setattr(
        sys, "argv", ["pyonenote", "-f", str(sample_file), "-o", "out", "-e", "bin", "-j"]
    )

    main_mod.main()

    assert called["file_path"] == str(sample_file)
    assert isinstance(called["file_path"], str)
    assert called["output_dir"] == "out"
    assert called["extension"] == "bin"
    assert called["json_output"] is True


def test_main_exits_on_missing_file(monkeypatch):
    missing_path = r"C:\definitely_missing\nope.one"
    monkeypatch.setattr(sys, "argv", ["pyonenote", "-f", missing_path])

    with pytest.raises(SystemExit) as exc:
        main_mod.main()

    assert "File doesn't exist" in str(exc.value)
    assert missing_path in str(exc.value)
