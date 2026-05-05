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
        
    pdf_engine = request.form.get("pdf_engine", "opendataloader")

    temp_pdf_path = os.path.join(upload_folder, f"pdf_{uuid.uuid4().hex}_{secure_filename(file.filename)}")
    
    try:
        file.save(temp_pdf_path)
        debug_json_path = None

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
            try:
                import tempfile
                import shutil
                
                with tempfile.TemporaryDirectory() as temp_output_dir:
                    if pdf_engine == "chandra":
                        from chandra_pdf_importer import convert_pdf_to_json_with_chandra
                        json_path = convert_pdf_to_json_with_chandra(temp_pdf_path, temp_output_dir)
                    else:
                        from opendataloader_pdf import convert
                        convert(
                            input_path=temp_pdf_path,
                            output_dir=temp_output_dir,
                            format="json",
                            quiet=False
                        )
                        output_files = [f for f in os.listdir(temp_output_dir) if f.endswith('.json')]
                        if not output_files:
                            return jsonify({'error': 'Fehler: Engine konnte keine JSON-Struktur aus der PDF generieren.'}), 500
                        json_path = os.path.join(temp_output_dir, output_files[0])
                    
                    # Kopiere die JSON in den Uploads Ordner für Debug-Zwecke
                    debug_json_path = os.path.join(upload_folder, f"odl_debug_{uuid.uuid4().hex}.json")
                    shutil.copy(json_path, debug_json_path)
                    
                    from sds_json_importer import import_sds_json_to_html
                    template_path = os.path.join(current_app.root_path, 'SDS_PERFEKT_TEMPLATE.html')
                    
                    rendered_html, gap_report = import_sds_json_to_html(json_path, template_path)
                    
                    if not rendered_html:
                        return jsonify({'error': 'Fehler beim Erstellen der HTML-Ansicht aus den extrahierten PDF-Daten.'}), 400
                        
                    product_name = 'Extracted directly from PDF (OpenDataLoader)'
            except ImportError:
                return jsonify({
                    'error': 'Das Tool opendataloader-pdf ist nicht installiert. Bitte laden Sie eine PDF mit eingebetteter XML hoch.'
                }), 400
            except Exception as e:
                import traceback
                print(f"Error extracting PDF with ODL: {e}\n{traceback.format_exc()}")
                return jsonify({
                    'error': f'Fehler bei der PDF-Verarbeitung ohne XML. Bitte prüfen Sie das Terminal (Fehlt Java?). Error: {str(e)}'
                }), 500

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
        elif debug_json_path:
            session['json_source_file'] = debug_json_path
            session['is_json_import'] = True

        return jsonify({
            'success': True,
            'filename': file.filename,
            'product_name': product_name,
            'preview': rendered_html,
            'is_embedded_xml': xml_extracted,
            'pdf_url': f'/uploads/{os.path.basename(temp_pdf_path)}'
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
        
        # Inject CSS override to ensure tables use auto sizing (prevents fixed widths from TinyMCE)
        css_override = """
        <style>
          table.sds, table.sds tbody, table.sds tr, table.sds td, table.sds th {
            width: auto !important;
            height: auto !important;
            table-layout: auto !important;
          }
        </style>
        """
        html_content = html_content.replace('</head>', css_override + '\n</head>', 1)
        
        try:
            from weasyprint import HTML
            html_obj = HTML(string=html_content, base_url=upload_folder)
            pdf_bytes = html_obj.write_pdf()
        except Exception as weasy_error:
            try:
                from playwright.sync_api import sync_playwright
                import tempfile
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8') as temp_html:
                    temp_html.write(html_content)
                    temp_html_path = temp_html.name
                    
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.goto(f"file:///{temp_html_path}")
                    page.wait_for_load_state("networkidle")
                    page.evaluate("document.fonts.ready")
                    page.add_style_tag(content="""
                        @media print {
                            table { page-break-inside: auto !important; width: 100% !important; }
                            tr    { page-break-inside: avoid !important; page-break-after: auto !important; }
                            thead { display: table-header-group !important; }
                            h1, h2, h3, h4, h5 { page-break-after: avoid !important; }
                        }
                    """)
                    pdf_bytes = page.pdf(format="A4", print_background=True)
                    browser.close()
            except Exception as playwright_error:
                raise RuntimeError(
                    f"PDF generation failed. WeasyPrint: {weasy_error}; Playwright: {playwright_error}"
                )
            
        return send_file(
            io.BytesIO(pdf_bytes),
            as_attachment=True,
            download_name=f"translated_{session.get('target_language', 'de')}_{session['original_filename'].replace('.html', '.pdf')}",
            mimetype='application/pdf'
        )
            
    except Exception as e:
        import traceback
        return jsonify({'error': f'PDF generation failed: {str(e)}\n{traceback.format_exc()}'}), 500
