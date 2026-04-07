from flask import Blueprint, jsonify, request, session, render_template, send_file, current_app
import os
import uuid
from werkzeug.utils import secure_filename
from pathlib import Path
import io

pdf_bp = Blueprint('pdf', __name__)

@pdf_bp.route('/api/pdf/process', methods=['POST'])
def process_pdf_dynamic():
    if not current_app.config['SDS_PARSER_V5_AVAILABLE']:
        return jsonify({'error': 'The new SDS parser is not available.'}), 500

    upload_folder = current_app.config['UPLOAD_FOLDER']
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '' or not file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'Please select a valid PDF file.'}), 400

    temp_pdf_path = os.path.join(upload_folder, f"pdf_{uuid.uuid4().hex}_{secure_filename(file.filename)}")
    
    try:
        file.save(temp_pdf_path)

        # Smart Detection: Check for embedded XML files (SDScom standard)
        xml_extracted = False
        temp_xml_path = None
        try:
            import fitz
            doc = fitz.open(temp_pdf_path)
            embfile_names = doc.embfile_names()
            for i in range(doc.embfile_count()):
                file_name = embfile_names[i]
                if file_name.lower().endswith('.xml') or 'sdscom' in file_name.lower():
                    xml_bytes = doc.embfile_get(i)
                    temp_xml_path = os.path.join(upload_folder, f"xml_{uuid.uuid4().hex}_{file_name}")
                    with open(temp_xml_path, 'wb') as f:
                        f.write(xml_bytes)
                    xml_extracted = True
                    break
            doc.close()
        except Exception as e:
            print(f"Error checking PDF attachments: {e}")

        if xml_extracted and temp_xml_path:
            from sds_xml_importer import import_sds_to_html
            template_path = os.path.join(current_app.root_path, 'SDS_PERFEKT_TEMPLATE.html')
            rendered_html, gap_report = import_sds_to_html(temp_xml_path, template_path, pdf_path=temp_pdf_path)
            if not rendered_html:
                return jsonify({'error': 'Failed to parse the embedded SDScom XML file.'}), 400
            product_name = 'Extracted from embedded XML'
        else:
            # Fallback for plain PDFs without embedded XML is currently not implemented
            # as the system relies on SDScom XML for accurate parsing.
            return jsonify({
                'error': 'Die hochgeladene PDF-Datei enthält keine eingebettete XML-Datei. Bitte laden Sie eine PDF mit eingebetteter SDScom XML hoch oder nutzen Sie den kombinierten XML+PDF Import.'
            }), 400

        rendered_filename = f"imported_{Path(file.filename).stem}.html"
        rendered_filepath = os.path.join(upload_folder, rendered_filename)
        with open(rendered_filepath, 'w', encoding='utf-8') as f:
            f.write(rendered_html)
            
        session['uploaded_file'] = rendered_filepath
        session['original_filename'] = rendered_filename
        session['is_pdf_import'] = not xml_extracted
        session['is_xml_import'] = xml_extracted
        session['pdf_source_file'] = temp_pdf_path
        if xml_extracted:
            session['xml_source_file'] = temp_xml_path

        return jsonify({
            'success': True,
            'filename': file.filename,
            'product_name': product_name,
            'preview': rendered_html,
            'is_embedded_xml': xml_extracted
        })

    except Exception as e:
        import traceback
        return jsonify({'error': f'An unexpected error occurred: {str(e)}\n{traceback.format_exc()}'}), 500

@pdf_bp.route('/api/download/pdf', methods=['POST'])
def download_pdf():
    upload_folder = current_app.config['UPLOAD_FOLDER']
    if not current_app.config['WEASYPRINT_AVAILABLE']:
        return jsonify({'error': 'PDF generation not available.'}), 500
        
    if 'translated_file' not in session:
        return jsonify({'error': 'No translation available'}), 400
    
    try:
        # FIRST: Check if there are edited contents from the editor that need to be saved
        # This ensures manual corrections are included in the PDF export
        data = request.get_json() or {}
        edited_content = data.get('edited_content')
        if edited_content:
            # Save the edited content before generating PDF
            with open(session['translated_file'], 'w', encoding='utf-8') as f:
                f.write(edited_content)
            print(f"Saved edited content before PDF export: {len(edited_content)} bytes")
        
        with open(session['translated_file'], 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        from weasyprint import HTML
        
        html_obj = HTML(string=html_content, base_url=upload_folder)
        pdf_bytes = html_obj.write_pdf()
        
        return send_file(
            io.BytesIO(pdf_bytes),
            as_attachment=True,
            download_name=f"translated_{session.get('target_language', 'de')}_{session['original_filename'].replace('.html', '.pdf')}",
            mimetype='application/pdf'
        )
            
    except Exception as e:
        import traceback
        return jsonify({'error': f'PDF generation failed: {str(e)}\n{traceback.format_exc()}'}), 500
