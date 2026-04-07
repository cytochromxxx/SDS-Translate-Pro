#!/usr/bin/env python3
"""
SDS Translator Web Application
Flask-based web UI for translating Safety Data Sheets
"""

import os
import tempfile
import secrets
from flask import Flask
import logging
from database import set_db_path, get_db_path, DATABASE_OPTIONS, DEFAULT_DB_PATH, ensure_database_indices
from utils import AVAILABLE_LANGUAGES, LANG_TO_COLUMN, parse_flag_format

# Generate secure secret key from environment or random
def get_secret_key():
    """Get secret key from environment or generate a secure random key."""
    env_key = os.environ.get('FLASK_SECRET_KEY')
    if env_key:
        return env_key
    # Generate a new secure key if not in environment (for development only)
    return secrets.token_hex(32)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add msys2 GTK path to system PATH for WeasyPrint
msys2_path = r'C:\msys64\mingw64\bin'
os.environ['PATH'] = msys2_path + os.pathsep + os.environ.get('PATH', '')

# Tell cffi where to find the GTK libraries
os.environ['GI_TYPELIB_PATH'] = r'C:\msys64\mingw64\lib\girepository-1.0'
os.environ['GTK_EXE_PREFIX'] = r'C:\msys64\mingw64'
os.environ['GTK_PATH'] = r'C:\msys64\mingw64'

# --- Flask App Initialization ---
app = Flask(__name__)

def jinja_pad_filter(s, width, fillchar='0', left=True):
    """
    Jinja2 filter to pad a string.
    - s: The string to pad.
    - width: The target width.
    - fillchar: The character to use for padding.
    - left: If True, pad on the left (rjust); otherwise, pad on the right (ljust).
    """
    s = str(s)
    width = int(width)
    fillchar = str(fillchar)
    if left:
        return s.rjust(width, fillchar)
    else:
        return s.ljust(width, fillchar)

# Register the custom filter
app.jinja_env.filters['pad'] = jinja_pad_filter

app.secret_key = get_secret_key()
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')

# Ensure uploads directory exists
uploads_path = app.config['UPLOAD_FOLDER']
if not os.path.exists(uploads_path):
    os.makedirs(uploads_path)

# --- Import checks ---
try:
    from weasyprint import HTML, CSS
    app.config['WEASYPRINT_AVAILABLE'] = True
except (ImportError, OSError) as e:
    print(f"WeasyPrint not available: {e}. PDF export will be disabled.")
    app.config['WEASYPRINT_AVAILABLE'] = False

try:
    from sds_xml_importer import import_sds_to_html
    app.config['SDSCOM_PARSER_AVAILABLE'] = True
except ImportError as e:
    print(f"Could not import the sdscom_parser or sds_xml_importer: {e}")
    app.config['SDSCOM_PARSER_AVAILABLE'] = False

try:
    from pdf_importer import PDFImporter, PDFImportConfig, PDFImportError, check_dependencies
    app.config['PDF_IMPORT_AVAILABLE'] = True
except ImportError:
    app.config['PDF_IMPORT_AVAILABLE'] = False
    print("PDF import module not available")

try:
    from sds_template_importer import SDSTemplateImporter, import_sds_to_template
    app.config['SDS_TEMPLATE_IMPORT_AVAILABLE'] = True
except ImportError:
    app.config['SDS_TEMPLATE_IMPORT_AVAILABLE'] = False
    print("SDS Template import module not available")
    
try:
    from sds_parser import parse_sds_xml
    app.config['SDS_PARSER_V5_AVAILABLE'] = True
except ImportError:
    app.config['SDS_PARSER_V5_AVAILABLE'] = False
    print("SDS Parser v5 not available")


# --- Register Blueprints ---
from routes.main import main_bp
from routes.database import database_bp
from routes.pdf import pdf_bp
from routes.ghs import ghs_bp
from routes.json_import import json_import_bp

app.register_blueprint(main_bp)
app.register_blueprint(database_bp)
app.register_blueprint(pdf_bp)
app.register_blueprint(ghs_bp)
app.register_blueprint(json_import_bp)

# --- Initialize database indices for better performance ---
# This runs automatically on startup to ensure indices exist
try:
    index_result = ensure_database_indices()
    if index_result.get('success'):
        logger.info(f"Database indices initialized: {index_result.get('indices_created')} indices created")
    else:
        logger.warning(f"Could not initialize database indices: {index_result.get('error')}")
except Exception as e:
    logger.warning(f"Error initializing database indices: {e}")

# --- Logo Route ---
@app.route('/mb_logo.svg')
def serve_logo():
    from flask import send_file
    if os.path.exists('mb_logo.svg'):
        return send_file('mb_logo.svg', mimetype='image/svg+xml')
    return "Logo not found", 404

# --- Favicon Route ---
@app.route('/favicon.ico')
def serve_favicon():
    from flask import send_file
    if os.path.exists('mb_logo.svg'):
        return send_file('mb_logo.svg', mimetype='image/svg+xml')
    return "Favicon not found", 404

# --- Uploaded Files Route ---
@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    """Serve files from the uploads directory"""
    from flask import send_from_directory
    upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
    return send_from_directory(upload_folder, filename)


if __name__ == '__main__':
    # Determine debug mode from environment (default: False for security)
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 'yes')
    app.run(debug=debug_mode, host='0.0.0.0', port=5050)
