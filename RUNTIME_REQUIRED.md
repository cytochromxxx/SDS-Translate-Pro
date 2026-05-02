# Runtime Required Structure

This file documents the minimum project structure required to run all SDS-Translate Pro app features.

## Required Files

- `app.py`
- `database.py`
- `utils.py`
- `sds_translator_v4.py`
- `sds_parser.py`
- `sds_xml_importer.py`
- `sds_json_importer.py`
- `sds_json_parser.py`
- `sds_validator.py`
- `ghs_pictogram_manager.py`
- `odl_pdf_importer.py` (required for OpenDataLoader PDF engine path)
- `chandra_pdf_importer.py` (required for Chandra PDF engine path)
- `pdf_gap_filler.py` (required by PDF import helper path)
- `SDS_PERFEKT_TEMPLATE.html`
- `mb_logo.svg`
- `requirements.txt`

## Required Directories

- `routes/`
  - `main.py`
  - `database.py`
  - `pdf.py`
  - `ghs.py`
  - `json_import.py`
  - `library.py`
- `templates/`
  - `index.html`
  - `library_modal.html`
- `static/`
  - `js/main.js`
  - `css/style.css`
- `uploads/` (runtime workspace for imported/generated files)
- `ghs/` (hazard symbol assets)
- `symbole/` (includes PPE and transport symbols, including `symbole/transport/`)
- `datalab_exports/` (library source; also `bibliothek/` and `chandra_cache/` are read by library routes)

## Required Data Files

- At least one working phrase database in project root.
- Default expected DB: `sds_phrases_new.db`.

## Notes

- If optional PDF engines are disabled, `odl_pdf_importer.py` and/or `chandra_pdf_importer.py` can be treated as feature-optional. They are required for full feature parity.
- Frontend runtime is served by Flask templates/static assets; Node dependencies are not required for the currently active runtime path.
