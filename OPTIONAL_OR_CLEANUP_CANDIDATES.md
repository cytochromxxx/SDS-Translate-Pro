# Optional Or Cleanup Candidates

This list contains files/folders that are not required for core app runtime.

## Generally Optional For Production Runtime

- `README.md` and other `*.md` notes/documentation
- `node_modules/` (current app runtime does not require Node tooling)
- `package.json`, `package-lock.json` (optional for current runtime path)
- `.venv/`, `venv/` (environment folders; should be recreated, not versioned)
- `.ruff_cache/`
- `__pycache__/`
- `tmp_chandra/`

## Debug And Investigation Scripts

- `debug_*.py`
- `inspect_pdf.py`
- `tmp_run_extract.py`
- `debug_out.txt`

## Analysis / Migration / Utility Scripts (Non-runtime)

- `analyze_*.py`
- `check_*.py`
- `clean_*.py`
- `compare_tm_outputs.py`
- `csv_to_db.py`
- `download_datalab_*.py`
- `evaluate_*.py`
- `export_*.py`
- `extract_*.py`
- `import_*_bulk.py`
- `json_tm_extractor.py`
- `md_tm_extractor.py`
- `patch_csv.py`
- `pivot_sds_phrases_csv.py`
- `pdf_section_extractor.py`
- `sds_quality_check.py`
- `sdscom_parser.py` (standalone parser helper; app uses `sds_parser.py` + importers)

## Tests

- `test_*.py`

## Caution Before Deleting

Keep these if you actively use the related feature/workflow:

- `datalab_exports/`, `bibliothek/`, `chandra_cache/` (library/import source pools)
- non-default phrase DB files (`phrases_*.db`, `euphrac_excel_phrases.db`, etc.) if you switch DB via UI
- `ghs_cache/` (rebuildable cache, but may speed up first load)
