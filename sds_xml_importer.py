#!/usr/bin/env python3
"""
SDS XML Importer v8
Renders an HTML template with data parsed from an SDScom XML file.
Includes validation and gap reporting via sds_validator.py.
"""
import logging
import os
from typing import Optional, Tuple
from jinja2 import Environment, FileSystemLoader
from sds_parser import parse_sds_xml
from sds_validator import validate_and_report

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def import_sds_to_html(
    xml_path: str,
    template_path: str,
    pdf_path: Optional[str] = None,
) -> Tuple[str, Optional[str]]:
    """
    Parses an SDScom XML file and injects its data into a Jinja2 HTML template.
    Optionally accepts a companion PDF path for hybrid gap-filling.
    After parsing, validates completeness and generates a gap report.

    Args:
        xml_path:      The file path of the SDScom XML file.
        template_path: The file path of the Jinja2 HTML template.
        pdf_path:      Optional path to the companion PDF file.
                       When provided, empty XML fields are filled from the PDF.

    Returns:
        A tuple (rendered_html, gap_report_markdown).
        - rendered_html is the rendered HTML string, or "" on error.
        - gap_report_markdown is a Markdown string when gaps exist, else None.

    Note:
        Backward compatible: callers that only pass xml_path and template_path
        continue to work exactly as before (gap_report is simply ignored).
    """
    logger.info(f"Starting import process for {xml_path}")

    # 1. Parse the XML file (with optional PDF gap-filling)
    try:
        if pdf_path:
            logger.info(f"Parsing XML file with PDF fallback: {xml_path} + {pdf_path}")
        else:
            logger.info(f"Parsing XML file: {xml_path}")

        sds_data = parse_sds_xml(xml_path, pdf_path=pdf_path)
        if not sds_data:
            logger.error("XML parsing resulted in empty data.")
            return "", None
        logger.info(f"XML parsed successfully. Keys: {list(sds_data.keys())}")

        # 1b. Inject Section 3.2 table from Datalab JSON if available
        # The Datalab JSON has a complete, richly-formatted S3.2 table with ATE values and GHS images
        if pdf_path and os.path.exists(pdf_path):
            try:
                # We search for the datalab output json. It should be in the same folder as the PDF or project root.
                pdf_dir = os.path.dirname(os.path.abspath(pdf_path))
                pdf_name = os.path.basename(pdf_path)
                
                # Possible locations for the datalab json
                possible_paths = [
                    os.path.join(pdf_dir, f"datalab-output-{pdf_name}.json"),
                    os.path.join(os.getcwd(), f"datalab-output-{pdf_name}.json"),
                    os.path.join(os.getcwd(), 'uploads', f"datalab-output-{pdf_name}.json")
                ]
                
                datalab_json_path = None
                for p in possible_paths:
                    if os.path.exists(p):
                        datalab_json_path = p
                        break
                
                if datalab_json_path:
                    logger.info(f"Loading Datalab JSON: {datalab_json_path}")
                    with open(datalab_json_path, 'r', encoding='utf-8') as f:
                        datalab_j = _json.load(f)

                    def _extract_html(node):
                        if isinstance(node, str): return node
                        if isinstance(node, dict):
                            h = node.get('html', '') or node.get('text', '') or node.get('content', '') or ''
                            for c in node.get('children', []): h += _extract_html(c)
                            return h
                        if isinstance(node, list):
                            return ''.join(_extract_html(n) for n in node)
                        return ''

                    full_html = _extract_html(datalab_j)
                    idx_s3 = full_html.find('3.2. Mixtures')
                    if idx_s3 < 0: idx_s3 = full_html.find('Hazardous ingredients')
                    idx_tbl = full_html.find('<table', idx_s3) if idx_s3 >= 0 else -1
                    idx_tbl_end = full_html.find('</table>', idx_tbl) if idx_tbl >= 0 else -1

                    if idx_tbl >= 0 and idx_tbl_end >= 0:
                        s32_html = full_html[idx_tbl:idx_tbl_end + len('</table>')]
                        # Clean up data-bbox attributes (not needed in final doc)
                        import re as _re
                        s32_html = _re.sub(r'\s*data-bbox="[^"]*"', '', s32_html)
                        if 'section_3' not in sds_data:
                            sds_data['section_3'] = {}
                        sds_data['section_3']['mixture_components_html'] = s32_html
                        logger.info(f"Injected S3.2 table from Datalab JSON ({len(s32_html)} chars)")
                    
                    # 1b-2. Inject Section 2.2 as well if possible (Hazard labelling)
                    idx_s2 = full_html.find('2.2. Label elements')
                    if idx_s2 < 0: idx_s2 = full_html.find('Labelling according to Regulation')
                    idx_s2_content_start = full_html.find('<p', idx_s2) if idx_s2 >= 0 else -1
                    idx_s2_end = full_html.find('<h2>', idx_s2_content_start) if idx_s2_content_start >= 0 else -1
                    if idx_s2_end < 0: idx_s2_end = full_html.find('<h2', idx_s2_content_start)
                    
                    if idx_s2_content_start >= 0 and idx_s2_end >= 0:
                        s2_html = full_html[idx_s2_content_start:idx_s2_end]
                        s2_html = _re.sub(r'\s*data-bbox="[^"]*"', '', s2_html)
                        if 'section_2' not in sds_data:
                            sds_data['section_2'] = {}
                        sds_data['section_2']['hazard_labelling_html'] = s2_html
                        logger.info(f"Injected S2.2 content from Datalab JSON ({len(s2_html)} chars)")
                    else:
                        logger.warning("Datalab JSON found but Section 2.2 content not located within it")
                else:
                    logger.info(f"No Datalab JSON found at {datalab_json_path}, using XML fallback")
            except Exception as e:
                logger.warning(f"Could not load Datalab JSON for S3.2: {e}")

        # 1c. Fill Section 12 and 16 gaps from PDF if available
        if pdf_path and os.path.exists(pdf_path):
            try:
                from pdf_section_extractor import extract_sections_from_pdf, parse_section_16, parse_section_12, parse_section_1, parse_section_2
                pdf_sections = extract_sections_from_pdf(pdf_path)
                
                # Fill Section 1 and 2 gaps from PDF
                if pdf_sections:
                    if pdf_sections.get('section_1') and 'section_1' in sds_data:
                        section_1_data = parse_section_1(pdf_sections.get('section_1', ''))
                        if section_1_data.get('emergency_telephone_name'):
                            sds_data['section_1']['emergency_phone']['description'] = section_1_data['emergency_telephone_name']
                            logger.info("Section 1 emergency name filled from PDF")
                            
                    if pdf_sections.get('section_2') and 'section_2' in sds_data:
                        section_2_data = parse_section_2(pdf_sections.get('section_2', ''))
                        if section_2_data.get('hazard_components'):
                            sds_data['section_2']['labelling']['hazard_components'] = ", ".join(section_2_data['hazard_components'])
                        if section_2_data.get('endocrine_disruptors_human'):
                            if 'other_hazards' not in sds_data['section_2']:
                                sds_data['section_2']['other_hazards'] = {}
                            sds_data['section_2']['other_hazards']['health'] = section_2_data['endocrine_disruptors_human']
                        logger.info("Section 2 gaps filled from PDF")

                # Fill Section 16 gaps from PDF
                if pdf_sections and pdf_sections.get('section_16'):
                    section_16_data = parse_section_16(pdf_sections.get('section_16', ''))
                    
                    # Merge Section 16 data from PDF into sds_data
                    if 'other_information' not in sds_data:
                        sds_data['other_information'] = {}
                    
                    # Fill in missing fields from PDF
                    if not sds_data['other_information'].get('indication_of_changes') and section_16_data.get('indication_of_changes'):
                        sds_data['other_information']['indication_of_changes'] = section_16_data['indication_of_changes']
                    
                    if not sds_data['other_information'].get('abbreviations') and section_16_data.get('abbreviations'):
                        sds_data['other_information']['abbreviations'] = section_16_data['abbreviations']
                    
                    if not sds_data['other_information'].get('literature_references') and section_16_data.get('literature_references'):
                        sds_data['other_information']['literature_references'] = section_16_data['literature_references']
                    
                    if not sds_data['other_information'].get('training_advice') and section_16_data.get('training_advice'):
                        sds_data['other_information']['training_advice'] = section_16_data['training_advice']
                    
                    if not sds_data['other_information'].get('additional_info_lines') and section_16_data.get('additional_info_lines'):
                        sds_data['other_information']['additional_info_lines'] = section_16_data['additional_info_lines']
                    
                    logger.info(f"Section 16 gaps filled from PDF")
                
                # Integrate ATE values from PDF into section 3
                ate_values = pdf_sections.get('ate_values', {})
                if ate_values and 'section_3' in sds_data:
                    ate_list = list(ate_values.values())
                    if 'mixture_components' in sds_data['section_3']:
                        for component in sds_data['section_3']['mixture_components']:
                            component['ate_values'] = ate_list
                    sds_data['section_3']['ate_values'] = ate_list
                    logger.info(f"ATE values filled from PDF: {ate_list}")
                
                
                # Fill Section 12 gaps from PDF
                if pdf_sections and pdf_sections.get('section_12'):
                    section_12_data = parse_section_12(pdf_sections.get('section_12', ''))
                    
                    # Merge Section 12 data from PDF into sds_data
                    if 'section_12' not in sds_data:
                        sds_data['section_12'] = {}
                    
                    # 12.2 Persistence and degradability
                    if section_12_data.get('persistence_and_degradability'):
                        # Add biodegradation data to existing components
                        bio_data = section_12_data['persistence_and_degradability']
                        for comp_name, comp_data in bio_data.items():
                            # Find or create component in ecotox_components
                            found = False
                            for comp in sds_data['section_12'].get('ecotox_components', []):
                                if comp.get('generic_name') and comp_name.lower() in comp.get('generic_name', '').lower():
                                    comp['biodegradation'] = comp_data.get('biodegradation', '')
                                    found = True
                                    break
                            if not found:
                                # Create new component entry
                                if 'ecotox_components' not in sds_data['section_12']:
                                    sds_data['section_12']['ecotox_components'] = []
                                sds_data['section_12']['ecotox_components'].append({
                                    'generic_name': comp_name,
                                    'biodegradation': comp_data.get('biodegradation', '')
                                })
                    
                    # 12.2 Raw Text Fallback
                    if section_12_data.get('persistence_text'):
                        sds_data['section_12']['persistence'] = section_12_data['persistence_text']
                    
                    # 12.3 Bioaccumulative potential - add log_kow and bcf to components
                    if section_12_data.get('bioaccumulative_potential'):
                        bio_data = section_12_data['bioaccumulative_potential']
                        logger.info(f"Bioaccumulative data from PDF: {bio_data}")
                        for comp_name, comp_data in bio_data.items():
                            # Try multiple matching strategies
                            found = False
                            for comp in sds_data['section_12'].get('ecotox_components', []):
                                comp_generic = comp.get('generic_name', '').lower()
                                comp_name_lower = comp_name.lower()
                                
                                # Check for various match patterns
                                if (comp_name_lower in comp_generic or 
                                    comp_generic in comp_name_lower or
                                    (comp_name_lower == 'propan-1-ol' and 'propan' in comp_generic) or
                                    (comp_name_lower == 'ethanol' and 'ethanol' in comp_generic) or
                                    (comp_name_lower == 'dipropylene glycol monomethyl ether' and 'dipropylene' in comp_generic)):
                                    
                                    if comp_data.get('log_kow'):
                                        comp['log_kow'] = comp_data['log_kow']
                                        logger.info(f"Added log_kow {comp_data['log_kow']} to {comp.get('generic_name')}")
                                    if comp_data.get('bcf'):
                                        comp['bcf'] = comp_data['bcf']  # Use 'bcf' not 'bioconcentration_factor'
                                        logger.info(f"Added BCF {comp_data['bcf']} to {comp.get('generic_name')}")
                                    found = True
                                    break
                    
                    # 12.3 Raw Text Fallback
                    if section_12_data.get('bioaccumulation_text'):
                        sds_data['section_12']['bioaccumulation'] = section_12_data['bioaccumulation_text']
                    
                    # 12.4 Mobility in soil
                    if section_12_data.get('mobility_in_soil'):
                        mobility_text = '; '.join([v.get('data', '') for v in section_12_data['mobility_in_soil'].values()])
                        if mobility_text and not sds_data['section_12'].get('mobility_info'):
                            sds_data['section_12']['mobility_info'] = mobility_text
                    
                    # 12.5 Results of PBT and vPvB assessment
                    if section_12_data.get('pbt_vpvb_assessment'):
                        if section_12_data.get('pbt_text'):
                            sds_data['section_12']['pbt_result'] = section_12_data['pbt_text']
                        pbt_text = '; '.join([v.get('assessment', '') for v in section_12_data['pbt_vpvb_assessment'].values()])
                        if pbt_text:
                            sds_data['section_12']['pbt_vpvb_info'] = pbt_text
                        # Also add pbt_result to each ecotox_component
                        pbt_data = section_12_data['pbt_vpvb_assessment']
                        for comp_name, comp_data in pbt_data.items():
                            for comp in sds_data['section_12'].get('ecotox_components', []):
                                comp_generic = comp.get('generic_name', '').lower()
                                if comp_name.lower() in comp_generic or 'propan' in comp_generic:
                                    comp['pbt_result'] = comp_data.get('assessment', '')
                                    break
                    
                    # 12.6 Endocrine disrupting properties
                    if section_12_data.get('endocrine_disruptors') and section_12_data['endocrine_disruptors'].get('text'):
                        if not sds_data['section_12'].get('endocrine_disrupting_info'):
                            sds_data['section_12']['endocrine_disrupting_info'] = section_12_data['endocrine_disruptors']['text']
                    
                    # 12.7 Other adverse effects
                    if section_12_data.get('other_adverse_effects') and section_12_data['other_adverse_effects'].get('text'):
                        if not sds_data['section_12'].get('other_adverse_effects_info'):
                            sds_data['section_12']['other_adverse_effects_info'] = section_12_data['other_adverse_effects']['text']
                    
                    logger.info(f"Section 12 gaps filled from PDF")
                    
            except Exception as e:
                logger.warning(f"Could not fill gaps from PDF: {e}")
                
    except Exception as e:
        logger.error(f"Failed to parse XML file {xml_path}: {e}", exc_info=True)
        return "", None

    # 2. Validate completeness and generate gap report
    gap_report_md: Optional[str] = None
    try:
        validation_result, gap_report_md = validate_and_report(sds_data)
        overall_status = validation_result.get("overall_status", "unknown")
        completeness_pct = round(validation_result.get("overall_completeness", 0) * 100, 1)

        if overall_status == "fail":
            logger.warning(
                f"Validation FAILED for {xml_path}: "
                f"completeness={completeness_pct}%, "
                f"critical_gaps={len(validation_result.get('critical_gaps', []))}. "
                "Proceeding with template rendering (backward-compatible mode)."
            )
        elif overall_status == "warning":
            logger.warning(
                f"Validation WARNING for {xml_path}: "
                f"completeness={completeness_pct}%, "
                f"warnings={len(validation_result.get('warnings', []))}."
            )
        else:
            logger.info(f"Validation PASSED for {xml_path}: completeness={completeness_pct}%.")
            # No gaps – no need to carry the report forward
            gap_report_md = None

    except Exception as e:
        logger.error(f"Validation step failed for {xml_path}: {e}", exc_info=True)
        gap_report_md = None

    # 3. Set up Jinja2 environment
    template_dir = os.path.dirname(template_path)
    template_file = os.path.basename(template_path)
    env = Environment(loader=FileSystemLoader(template_dir), autoescape=True)

    # Register custom filters
    def pad_filter(value, width, fillchar='0', left=True):
        """Zero-pad (or any char) a value to a given width."""
        s = str(value)
        if left:
            return s.zfill(int(width)) if fillchar == '0' else s.rjust(int(width), fillchar)
        return s.ljust(int(width), fillchar)

    env.filters['pad'] = pad_filter

    # 4. Render the template
    try:
        template = env.get_template(template_file)
        rendered_html = template.render(sds_data)
        logger.info("Successfully rendered HTML template.")
        return rendered_html, gap_report_md
    except Exception as e:
        logger.error(f"Failed to render HTML template {template_path}: {e}", exc_info=True)
        return "", gap_report_md


if __name__ == '__main__':
    # Configuration for standalone execution
    XML_FILE = 'Sdb_EU-REACH_MycoplasmaOff™_15-5000,15-1000,15-0050_V5_en_DE.xml'
    TEMPLATE_FILE = 'SDS_PERFEKT_TEMPLATE.html'
    OUTPUT_FILE = 'importer_output.html'
    GAP_REPORT_FILE = 'gap_report.md'
    PDF_FILE = 'SDS_Mycoplasma_Off_15-5xxx_en_DE_Ver.05.pdf'

    # Resolve optional PDF path
    pdf = PDF_FILE if os.path.exists(PDF_FILE) else None
    if pdf:
        print(f"PDF companion found: {pdf}")
    else:
        print("No companion PDF found – running XML-only mode.")

    # Ensure input files exist
    if not os.path.exists(XML_FILE):
        print(f"Error: XML file not found at '{XML_FILE}'")
    elif not os.path.exists(TEMPLATE_FILE):
        print(f"Error: Template file not found at '{TEMPLATE_FILE}'")
    else:
        # Run the import process
        final_html, gap_report = import_sds_to_html(XML_FILE, TEMPLATE_FILE, pdf_path=pdf)

        # Write the HTML output
        if final_html:
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                f.write(final_html)
            print(f"Import successful. Output written to '{OUTPUT_FILE}'")

            # NEW: Copy to uploads folder and create session data for UI integration
            import shutil
            import json
            from datetime import datetime
            
            upload_folder = 'uploads'
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)

            # NEW: Try to fill gaps from PDF for Section 16 if PDF exists
            if pdf and os.path.exists(pdf):
                try:
                    from pdf_section_extractor import extract_sections_from_pdf, parse_section_16
                    print(f"Extracting Section 16 from PDF for gap-filling...")
                    
                    pdf_sections = extract_sections_from_pdf(pdf)
                    if pdf_sections and pdf_sections.get('section_16'):
                        section_16_data = parse_section_16(pdf_sections.get('section_16', ''))
                        print(f"Section 16 data extracted from PDF: {list(section_16_data.keys())}")
                        
                        # Save the PDF section 16 data for later use
                        pdf_gap_data = {
                            'section_16': section_16_data
                        }
                        pdf_gap_file = os.path.join(upload_folder, 'pdf_gap_data.json')
                        with open(pdf_gap_file, 'w', encoding='utf-8') as f:
                            json.dump(pdf_gap_data, f, indent=2, ensure_ascii=False)
                        print(f"PDF gap data saved to '{pdf_gap_file}'")
                except Exception as e:
                    print(f"Warning: Could not extract Section 16 from PDF: {e}")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            uploaded_filename = f"imported_{timestamp}.html"
            uploaded_filepath = os.path.join(upload_folder, uploaded_filename)

            shutil.copy(OUTPUT_FILE, uploaded_filepath)

            session_data = {
                "uploaded_file": uploaded_filepath.replace('\\', '/'),
                "original_filename": uploaded_filename,
                "is_xml_import": True,
                "import_timestamp": timestamp
            }

            session_file = os.path.join(upload_folder, "import_session.json")
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2)

            print(f"Session data saved to '{session_file}'")
            print("The file will be automatically loaded in the UI.")
        else:
            print("Import failed. Check logs for details.")

        # Write the gap report if gaps were found
        if gap_report:
            with open(GAP_REPORT_FILE, 'w', encoding='utf-8') as f:
                f.write(gap_report)
            print(f"Gap report written to '{GAP_REPORT_FILE}'")
        else:
            print("No gaps detected – gap report not generated.")
