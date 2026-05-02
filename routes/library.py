from flask import Blueprint, jsonify, current_app, request, session, send_file
import os
import glob
import uuid
import json
import re

library_bp = Blueprint('library', __name__)

def _extract_sds_meta(filepath):
    """Extracts product name, article number, version and language from a Datalab JSON.
    Returns None if the file is not a valid parsed SDS (e.g. a failed job)."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            d = json.load(f)

        # Skip failed Datalab jobs (they have 'status' key but no 'children')
        if 'children' not in d:
            return None

        # Collect first-page blocks
        pages = d.get('children', [])
        blocks = pages[0].get('children', []) if pages else []
        first_html = ' '.join(b.get('html', '') for b in blocks[:15])

        # Product name: text after "Safety Data Sheet..." header line
        # Pattern 1: <p>SDS header<br/>\n<b>ProductName</b></p>
        name_match = re.search(r'Safety Data Sheet[^<]*<br/>\s*<b>([^<]{3,80})</b>', first_html)
        if not name_match:
            # Pattern 2: <p>SDS header<br/>\nProductName</p>
            name_match = re.search(r'Safety Data Sheet[^<]*<br/>\s*([^<]{4,80})</p>', first_html)
        if not name_match:
            # Pattern 3: first <b> tag
            name_match = re.search(r'<b>([^<]{4,80})</b>', first_html)
        product = re.sub(r'<[^>]+>', '', name_match.group(1)).strip() if name_match else ''

        # Fallback: derive from filename
        fname = os.path.basename(filepath)
        if not product:
            # Strip request_id prefix and clean up
            clean = re.sub(r'^[A-Za-z0-9_\-]{10,30}_', '', fname)
            clean = re.sub(r'_(en|de|fr|fi|sv|cs|sl|ro|es)_.*$', '', clean, flags=re.IGNORECASE)
            clean = clean.replace('SDS_', '').replace('Sdb_EU-REACH_', '').replace('_', ' ').replace('.json', '')
            product = clean.strip()[:80]

        # Article number from filename
        art = re.search(r'[_-](\d{2,3}-\d{3,4}[x\d]*)', fname)
        article = art.group(1) if art else ''

        # Version from filename
        ver = re.search(r'[Vv](?:er\.?|ersion)?[_.]?(\d+)', fname)
        version = 'V' + ver.group(1) if ver else ''

        # Language from filename
        lang = re.search(r'_(en|de|fr|fi|sv|cs|sl|ro|es)_(DE|FI|US|EN|FR|SE|CZ|SI|RO|ES)', fname, re.IGNORECASE)
        language = lang.group(1).upper() if lang else ''
        country  = lang.group(2).upper() if lang else ''

        return {
            'product': product,
            'article': article,
            'version': version,
            'language': language,
            'country': country,
        }
    except Exception:
        return None


@library_bp.route('/api/library/list', methods=['GET'])
def list_library_files():
    """Lists available SDS JSON files with extracted metadata."""
    # Only datalab_exports is the canonical source; bibliothek/chandra_cache are legacy
    library_dirs = ['datalab_exports', 'bibliothek', 'chandra_cache']
    files = []
    seen_products = {}  # deduplicate by (product, article, version)

    for dir_name in library_dirs:
        dir_path = os.path.join(current_app.root_path, dir_name)
        if not os.path.exists(dir_path):
            continue
        for filepath in sorted(glob.glob(os.path.join(dir_path, '*.json'))):
            filename = os.path.basename(filepath)
            meta = _extract_sds_meta(filepath)

            # Skip invalid/failed files
            if meta is None:
                continue
            dedup_key = (meta['product'].lower(), meta['article'], meta['version'])
            if dedup_key in seen_products and dedup_key != ('', '', ''):
                continue
            seen_products[dedup_key] = True

            files.append({
                'id': filepath,
                'filename': filename,
                'product': meta['product'],
                'article': meta['article'],
                'version': meta['version'],
                'language': meta['language'],
                'country': meta['country'],
                'source': dir_name,
            })

    # Sort by product name
    files.sort(key=lambda x: x['product'].lower())
    return jsonify({'files': files})

@library_bp.route('/api/library/load', methods=['POST'])
def load_library_file():
    """Loads a specific JSON file from the library and sets it as the current active SDS."""
    data = request.get_json()
    filepath = data.get('filepath')
    
    if not filepath or not os.path.exists(filepath):
        return jsonify({'error': 'Datei nicht gefunden'}), 404
        
    # Sicherheitscheck: Verhindere Path Traversal
    abs_filepath = os.path.abspath(filepath)
    allowed_dirs = [
        os.path.abspath(os.path.join(current_app.root_path, d)) 
        for d in ['datalab_exports', 'bibliothek', 'chandra_cache']
    ]
    if not any(abs_filepath.startswith(d) for d in allowed_dirs):
        return jsonify({'error': 'Ungültiger Dateipfad'}), 403
        
    try:
        from sds_json_importer import import_sds_json_to_html
        
        template_path = os.path.join(current_app.root_path, 'SDS_PERFEKT_TEMPLATE.html')
        rendered_html, gap_report = import_sds_json_to_html(filepath, template_path)
        
        if not rendered_html:
            return jsonify({'error': 'Fehler beim Rendern der HTML aus der JSON.'}), 500
            
        upload_folder = current_app.config['UPLOAD_FOLDER']
        filename = os.path.basename(filepath)
        rendered_filename = f"imported_lib_{uuid.uuid4().hex}_{filename}.html"
        rendered_filepath = os.path.join(upload_folder, rendered_filename)
        
        with open(rendered_filepath, 'w', encoding='utf-8') as f:
            f.write(rendered_html)
            
        session['uploaded_file'] = rendered_filepath
        session['original_filename'] = rendered_filename
        session['is_json_import'] = True
        session['json_source_file'] = filepath
        
        return jsonify({
            'success': True,
            'filename': filename,
            'preview': rendered_html
        })
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

@library_bp.route('/api/library/delete', methods=['DELETE'])
def delete_library_file():
    """Löscht eine JSON Datei dauerhaft aus der Bibliothek."""
    data = request.get_json()
    filepath = data.get('filepath')
    
    if not filepath or not os.path.exists(filepath):
        return jsonify({'error': 'Dokument nicht gefunden'}), 404
        
    abs_filepath = os.path.abspath(filepath)
    allowed_dirs = [
        os.path.abspath(os.path.join(current_app.root_path, d)) 
        for d in ['datalab_exports', 'bibliothek', 'chandra_cache']
    ]
    if not any(abs_filepath.startswith(d) for d in allowed_dirs):
        return jsonify({'error': 'Ungültiger Dateipfad'}), 403
        
    try:
        os.remove(filepath)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@library_bp.route('/api/library/export', methods=['GET'])
def export_library_file():
    """Ermöglicht den direkten Download der JSON-Datei."""
    filepath = request.args.get('filepath')
    
    if not filepath or not os.path.exists(filepath):
        return jsonify({'error': 'Dokument nicht gefunden'}), 404
        
    abs_filepath = os.path.abspath(filepath)
    allowed_dirs = [
        os.path.abspath(os.path.join(current_app.root_path, d)) 
        for d in ['datalab_exports', 'bibliothek', 'chandra_cache']
    ]
    if not any(abs_filepath.startswith(d) for d in allowed_dirs):
        return jsonify({'error': 'Ungültiger Dateipfad'}), 403
        
    try:
        filename = os.path.basename(filepath)
        return send_file(filepath, as_attachment=True, download_name=filename, mimetype='application/json')
    except Exception as e:
        return jsonify({'error': str(e)}), 500