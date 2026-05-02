from flask import Blueprint, jsonify, request, send_file, send_from_directory
from ghs_pictogram_manager import GHSPictogramManager
import os

ghs_bp = Blueprint('ghs', __name__)

pictogram_manager = GHSPictogramManager()

@ghs_bp.route('/api/ghs/pictograms', methods=['GET'])
def get_ghs_pictograms():
    hazard_class = request.args.get('class', None)
    pictograms = pictogram_manager.get_all_pictograms()
    if hazard_class:
        pictograms = [p for p in pictograms if p.get('hazard_class') == hazard_class]
    return jsonify(pictograms)

@ghs_bp.route('/api/ghs/pictograms/<code>', methods=['GET'])
def get_ghs_pictogram(code):
    pictogram = pictogram_manager.get_pictogram_by_code(code)
    if pictogram:
        return jsonify(pictogram)
    return jsonify({'error': 'Pictogram not found'}), 404

@ghs_bp.route('/api/ghs/pictograms/<code>/svg')
def get_ghs_pictogram_svg(code):
    pictogram = pictogram_manager.get_pictogram_by_code(code)
    if pictogram and pictogram.get('svg_path'):
        svg_path = pictogram['svg_path']
        if os.path.exists(svg_path):
            return send_file(svg_path, mimetype='image/svg+xml')
    
    png_path = os.path.join('ghs', f'{code.lower()}.png')
    if os.path.exists(png_path):
        return send_file(png_path, mimetype='image/png')
    
    return jsonify({'error': 'Pictogram not found'}), 404

@ghs_bp.route('/ghs/<path:filename>')
def serve_ghs_image(filename):
    """Serve GHS pictogram PNG files directly from the ghs folder or aliases from symbole folder."""
    # Intercept literal Jinja/Vue template placeholders that cause 404s
    if '%7B%7B' in filename or '{{' in filename:
        return jsonify({'error': 'Template placeholder, ignoring'}), 404
        
    aliases = {
        'eye_protection.png': 'M004_Augenschutz-benutzen.jpg',
        'skin_protection.png': 'M009_Handschutz_benutzen.jpg',
        'respiratory_protection.png': 'M017_Atemschutz-benutzen.jpg',
        'body_protection.png': 'M010_Schutzkleidung-benutzen.jpg',
        'eye.png': 'M004_Augenschutz-benutzen.jpg',
        
        # GHS standard aliases
        'ghs01.png': 'GHS_01_gr.gif',
        'ghs02.png': 'GHS_02_gr.gif',
        'ghs03.png': 'GHS_03_gr.gif',
        'ghs04.png': 'GHS_04_gr.gif',
        'ghs05.png': 'GHS_05_gr.gif',
        'ghs06.png': 'GHS_06_gr.gif',
        'ghs07.png': 'GHS_07_gr.gif',
        'ghs08.png': 'GHS_08_gr.gif',
        'ghs09.png': 'GHS_09_gr.gif',
    }
    
    if filename.lower() in aliases:
        symbole_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'symbole')
        return send_from_directory(symbole_dir, aliases[filename.lower()])
        
    ghs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ghs')
    
    # Fallback to symbole folder if not found in ghs
    if not os.path.exists(os.path.join(ghs_dir, filename)):
        symbole_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'symbole')
        if os.path.exists(os.path.join(symbole_dir, filename)):
             return send_from_directory(symbole_dir, filename)
             
    return send_from_directory(ghs_dir, filename)

@ghs_bp.route('/transport/<path:filename>')
def serve_transport_image(filename):
    """Serve transport pictograms from the transport folder or aliases from symbole folder."""
    if '%7B%7B' in filename or '{{' in filename:
        return jsonify({'error': 'Template placeholder, ignoring'}), 404
        
    aliases = {
        'class3.png': 'File_UN_transport_pictogram_-_3_(white).svg',
        'class4.png': 'File_UN_transport_pictogram_-_4_(white).svg',
        'class4.1.png': 'File_UN_transport_pictogram_-_4_(stripes).svg',
        'class4.2.png': 'File_UN_transport_pictogram_-_4_(red).svg',
        'class4.3.png': 'File_UN_transport_pictogram_-_4_(white).svg',
        'class5.png': 'File_UN_transport_pictogram_-_5.1.svg',
        'class5.1.png': 'File_UN_transport_pictogram_-_5.1.svg',
        'class5.2.png': 'File_UN_transport_pictogram_-_5.2_(white).svg',
        'class6.png': 'File_UN_transport_pictogram_-_6.svg',
        'class6.1.png': 'File_UN_transport_pictogram_-_6.svg',
        'class6.2.png': 'File_ADR_6.2.svg',
        'class7.png': 'File_ADR_7C.svg',
        'class8.png': 'File_UN_transport_pictogram_-_8.svg',
        'class9.png': 'File_ADR_9.svg',
    }
    
    if filename.lower() in aliases:
        symbole_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'symbole')
        alias_path = os.path.join(symbole_dir, aliases[filename.lower()])
        if os.path.exists(alias_path):
            return send_from_directory(symbole_dir, aliases[filename.lower()])
            
    transport_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'transport')
    if os.path.exists(os.path.join(transport_dir, filename)):
        return send_from_directory(transport_dir, filename)
        
    return jsonify({'error': 'Transport pictogram not found'}), 404
