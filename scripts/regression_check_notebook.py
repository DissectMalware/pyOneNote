"""
Regression check for notebook object extraction.

Usage:
    python scripts/regression_check_notebook.py --notebook-dir "C:\\Users\\oz303\\Oz\\MyNotebook"

This script validates the parsed notebook hierarchy and page outputs against
an expected baseline. It exits with code 0 on success, 1 on mismatch.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


EXPECTED = {
    "title": "MyNotebook",
    "sections": [
        {
            "title": "New Section 1",
            "pages": [
                {"title": "\u05d3\u05d5\u05d2\u05de\u05d0", "contains": "\u05d6\u05d0\u05ea \u05d7\u05d5\u05d1\u05e8\u05ea \u05dc\u05d3\u05d5\u05d2\u05de\u05d0"},
                {"title": "\u05e2\u05d5\u05d3 \u05d3\u05d5\u05d2\u05de\u05d4", "contains": "\u05d4\u05e0\u05d4 - \u05db\u05ea\u05d5\u05d1 \u05e4\u05d4 \u05d8\u05e7\u05e1\u05d8. \u05d0\u05d9\u05d6\u05d4 \u05d9\u05d5\u05e4\u05d9!"},
            ],
        },
        {
            "title": "New Section 2",
            "pages": [
                {"title": "\u05de\u05e9\u05d4\u05d5 \u05de\u05e2\u05e0\u05d9\u05d9\u05df?", "contains": "\u05de\u05e9\u05d4\u05d5 \u05de\u05e2\u05e0\u05d9\u05d9\u05df?"},
            ],
        },
    ],
    "section_groups": [
        {
            "title": "SectionGroup",
            "sections": [
                {
                    "title": "New Section 1",
                    "pages": [
                        {"title": "\u05de\u05de\u05de\u05de\u05de\u05de\u05de", "contains": "\u05de\u05de\u05de\u05de\u05de\u05de\u05de"},
                    ],
                }
            ],
            "section_groups": [],
        }
    ],
}


def _normalize_text(text: str) -> str:
    return " ".join((text or "").split())


def _page_to_view(page) -> Dict[str, str]:
    return {
        "title": page.title or "",
        "content": _normalize_text(page.content or ""),
    }


def _section_to_view(section) -> Dict[str, Any]:
    return {
        "title": section.title or "",
        "pages": [_page_to_view(p) for p in section.pages],
    }


def _group_to_view(group) -> Dict[str, Any]:
    return {
        "title": group.title or "",
        "sections": [_section_to_view(s) for s in group.sections],
        "section_groups": [_group_to_view(g) for g in group.section_groups],
    }


def _actual_snapshot(notebook) -> Dict[str, Any]:
    return {
        "title": notebook.title or "",
        "sections": [_section_to_view(s) for s in notebook.sections],
        "section_groups": [_group_to_view(g) for g in notebook.section_groups],
    }


def _compare_sections(actual_sections: List[Dict[str, Any]], expected_sections: List[Dict[str, Any]], prefix: str, errors: List[str]) -> None:
    if len(actual_sections) != len(expected_sections):
        errors.append(f"{prefix}: expected {len(expected_sections)} sections, got {len(actual_sections)}")
        return

    for idx, exp_sec in enumerate(expected_sections):
        act_sec = actual_sections[idx]
        if act_sec["title"] != exp_sec["title"]:
            errors.append(f"{prefix}[{idx}].title: expected '{exp_sec['title']}', got '{act_sec['title']}'")

        exp_pages = exp_sec.get("pages", [])
        act_pages = act_sec.get("pages", [])
        if len(act_pages) != len(exp_pages):
            errors.append(f"{prefix}[{idx}] '{exp_sec['title']}': expected {len(exp_pages)} pages, got {len(act_pages)}")
            continue

        for pidx, exp_page in enumerate(exp_pages):
            act_page = act_pages[pidx]
            if act_page["title"] != exp_page["title"]:
                errors.append(
                    f"{prefix}[{idx}].pages[{pidx}].title: expected '{exp_page['title']}', got '{act_page['title']}'"
                )
            contains = _normalize_text(exp_page.get("contains", ""))
            if contains and contains not in act_page["content"]:
                errors.append(
                    f"{prefix}[{idx}].pages[{pidx}] content does not contain expected snippet '{contains}'"
                )


def _compare_groups(actual_groups: List[Dict[str, Any]], expected_groups: List[Dict[str, Any]], prefix: str, errors: List[str]) -> None:
    if len(actual_groups) != len(expected_groups):
        errors.append(f"{prefix}: expected {len(expected_groups)} groups, got {len(actual_groups)}")
        return

    for idx, exp_group in enumerate(expected_groups):
        act_group = actual_groups[idx]
        if act_group["title"] != exp_group["title"]:
            errors.append(f"{prefix}[{idx}].title: expected '{exp_group['title']}', got '{act_group['title']}'")
        _compare_sections(act_group.get("sections", []), exp_group.get("sections", []), f"{prefix}[{idx}].sections", errors)
        _compare_groups(
            act_group.get("section_groups", []),
            exp_group.get("section_groups", []),
            f"{prefix}[{idx}].section_groups",
            errors,
        )


def validate_notebook(notebook) -> List[str]:
    actual = _actual_snapshot(notebook)
    errors: List[str] = []

    if actual["title"] != EXPECTED["title"]:
        errors.append(f"title: expected '{EXPECTED['title']}', got '{actual['title']}'")

    _compare_sections(actual["sections"], EXPECTED["sections"], "sections", errors)
    _compare_groups(actual["section_groups"], EXPECTED["section_groups"], "section_groups", errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--notebook-dir", required=True, help="Path to notebook directory")
    parser.add_argument("--print-actual", action="store_true", help="Print parsed snapshot JSON")
    args = parser.parse_args()

    notebook_dir = Path(args.notebook_dir)
    if not notebook_dir.exists():
        print(f"Notebook directory not found: {notebook_dir}")
        return 1

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from pyOneNote.models import OneNoteNotebook

    notebook = OneNoteNotebook(path=str(notebook_dir))
    actual = _actual_snapshot(notebook)

    if args.print_actual:
        print(json.dumps(actual, ensure_ascii=False, indent=2))

    errors = validate_notebook(notebook)
    if errors:
        print("FAIL: notebook regression check found mismatches:")
        for err in errors:
            print(f"- {err}")
        return 1

    print("PASS: notebook regression check matched expected hierarchy/titles/content snippets.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
