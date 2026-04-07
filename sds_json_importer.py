import logging
import os
import json
from typing import Optional, Tuple
from jinja2 import Environment, FileSystemLoader
from sds_json_parser import parse_sds_json
from sds_validator import validate_and_report

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def import_sds_json_to_html(
    json_path: str,
    template_path: str
) -> Tuple[str, Optional[str]]:
    """
    Parses a Datalab Layout JSON file and injects its data into a Jinja2 HTML template.
    
    Args:
        json_path:      The file path of the SDS JSON file.
        template_path:  The file path of the Jinja2 HTML template.
        
    Returns:
        A tuple (rendered_html, gap_report_markdown).
    """
    logger.info(f"Starting JSON import process for {json_path}")

    # 1. Parse the JSON file
    try:
        sds_data = parse_sds_json(json_path)
        if not sds_data:
            logger.error("JSON parsing resulted in empty data.")
            return "", None
        logger.info(f"JSON parsed successfully. Keys: {list(sds_data.keys())}")
    except Exception as e:
        logger.error(f"Failed to parse JSON file {json_path}: {e}", exc_info=True)
        return "", None

    # 2. Validate completeness and generate gap report
    gap_report_md: Optional[str] = None
    try:
        validation_result, gap_report_md = validate_and_report(sds_data)
        if validation_result.get("overall_status") == "pass":
            gap_report_md = None
    except Exception as e:
        logger.error(f"Validation step failed for {json_path}: {e}", exc_info=True)
        gap_report_md = None

    # 3. Set up Jinja2 environment
    template_dir = os.path.dirname(os.path.abspath(template_path))
    template_file = os.path.basename(template_path)
    env = Environment(loader=FileSystemLoader(template_dir), autoescape=True)

    # Register custom filters (consistent with app.py and xml_importer)
    def pad_filter(value, width, fillchar='0', left=True):
        s = str(value)
        if left:
            return s.zfill(int(width)) if fillchar == '0' else s.rjust(int(width), fillchar)
        return s.ljust(int(width), fillchar)

    env.filters['pad'] = pad_filter

    # 4. Render the template
    try:
        template = env.get_template(template_file)
        rendered_html = template.render(**sds_data)
        logger.info("Successfully rendered HTML template from JSON data.")
        return rendered_html, gap_report_md
    except Exception as e:
        logger.error(f"Failed to render HTML template {template_path}: {e}", exc_info=True)
        return "", gap_report_md

if __name__ == '__main__':
    # Test script
    JSON_FILE = 'jsons/datalab-output-QcRzGVOl1uqGQP6dtpWv2g_SDS_Mycoplasma_Off_1.pdf.json'
    TEMPLATE_FILE = 'layout-placeholders-fixed-v2.html'
    
    if os.path.exists(JSON_FILE) and os.path.exists(TEMPLATE_FILE):
        html, report = import_sds_json_to_html(JSON_FILE, TEMPLATE_FILE)
        with open('json_import_test.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("JSON Import Test successful. Output: json_import_test.html")
    else:
        print("Test files not found.")
