# Changelog

## 0.1.0 - 2026-02-25

### Added
- Directory-based notebook parsing with nested section group support.
- Export helper `build_notebook_from_directory`.
- Regression tooling:
  - `scripts/regression_check_notebook.py`
  - fixture-based and integration pytest coverage.
- API contract and deterministic-order tests.
- CLI entrypoint tests.

### Changed
- Improved page extraction reliability and metadata handling.
- Improved Unicode/Hebrew text extraction behavior.
- Updated README with object contract, testing, and usage guidance.

### Fixed
- CLI bug: file path is now passed correctly to parser pipeline.
- Object ID stream traversal bug in low-level parser (`ObjectSpaceObjectStreamOfIDs.read`).
