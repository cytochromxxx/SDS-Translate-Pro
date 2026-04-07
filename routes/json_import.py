from flask import Blueprint, jsonify, request, session, current_app, render_template
import os
import uuid
import json
from werkzeug.utils import secure_filename
from pathlib import Path
from sds_json_parser import parse_sds_json
from sds_validator import validate_and_report

json_import_bp = Blueprint('json_import', __name__)

@json_import_bp.route('/api/import/json', methods=['POST'])
def import_json():
    """
    Endpoint to import an SDS from a Layout JSON file.
    """
    upload_folder = current_app.config['UPLOAD_FOLDER']
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Keine Datei hochgeladen.'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Keine Datei ausgewählt.'}), 400
        
    if not file.filename.lower().endswith('.json'):
        return jsonify({'success': False, 'error': 'Bitte eine gültige JSON-Datei hochladen.'}), 400

    # Save uploaded JSON
    filename = secure_filename(file.filename)
    json_path = os.path.join(upload_folder, f"json_{uuid.uuid4().hex}_{filename}")
    file.save(json_path)

    try:
        # 1. Parse JSON
        sds_data = parse_sds_json(json_path)
        if not sds_data:
            return jsonify({'success': False, 'error': 'JSON-Datei konnte nicht verarbeitet werden.'}), 400

        # 2. Render HTML using the standard template
        # Note: We use the same template as XML/PDF imports for consistency
        template_name = 'SDS_PERFEKT_TEMPLATE.html'
        
        # We need to ensure we can render this template. 
        # Flask's render_template looks in the 'templates' folder.
        rendered_html = render_template(template_name, **sds_data)

        # 3. Save the rendered HTML
        rendered_filename = f"imported_json_{Path(filename).stem}.html"
        rendered_filepath = os.path.join(upload_folder, rendered_filename)
        with open(rendered_filepath, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        # 4. Generate Gap Report
        validation_result, gap_report_md = validate_and_report(sds_data)
        
        # 5. Update Session
        session['uploaded_file'] = rendered_filepath.replace('\\', '/')
        session['original_filename'] = filename
        session['is_xml_import'] = False # It's a JSON import, but we can treat it similarly to PDF
        session['is_json_import'] = True
        session['json_source_file'] = json_path

        return jsonify({
            'success': True,
            'filename': filename,
            'product_name': sds_data.get('meta', {}).get('product_name', 'Unbekannt'),
            'preview': rendered_html,
            'gap_report': gap_report_md if validation_result.get('overall_status') != 'pass' else None
        })

    except Exception as e:
        import traceback
        current_app.logger.error(f"Error during JSON import: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500
