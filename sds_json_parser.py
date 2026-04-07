import json
import re
import logging
import os
import base64
from typing import Any, Dict, List, Optional
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SDSJsonParser:
    def __init__(self, json_path: str):
        self.json_path = json_path
        with open(json_path, 'r', encoding='utf-8') as f:
            self.raw_data = json.load(f)
        
        self.data = {
            'meta': {
                'product_name': 'Unknown',
                'version': '1.0',
                'revision_date': '',
                'print_date': '',
                'language': 'en',
                'country': 'DE'
            },
            'section_1': {
                'product_identifier': {'trade_name': '', 'item_no': '', 'ufi': ''},
                'relevant_uses': {'product_type': '', 'su': '', 'su_fulltext': '', 'pc1': '', 'pc2': '', 'lcs': ''},
                'supplier_details': {'name': '', 'address': '', 'country': '', 'phone': '', 'email': '', 'website': ''},
                'emergency_phone': {'number': '', 'description': ''}
            },
            'section_2': {
                'classification': [],
                'labelling': {
                    'pictograms': [],
                    'signal_word': '',
                    'hazard_components': [],
                    'hazard_statements': [],
                    'precautionary_statements': {'prevention': [], 'response': []}
                },
                'other_hazards': {'physicochemical': '', 'health': ''}
            },
            'section_3': {'mixture_components': []},
            'section_4': {
                'description': {'general': '', 'inhalation': '', 'skin': '', 'eye': '', 'ingestion': '', 'self_protection': ''},
                'symptoms': '',
                'treatment': ''
            },
            'section_5': {
                'suitable_media': '', 'unsuitable_media': '', 'special_hazards': '',
                'combustion_products': '', 'firefighter_advice': '', 'additional_info': ''
            },
            'section_6': {
                'personal_precautions': '', 'protective_equipment': '', 'emergency_responders': '',
                'environmental_precautions': '', 'containment': '', 'cleaning': '',
                'other_sections': '', 'additional_info': ''
            },
            'section_7': {
                'safe_handling': '', 'fire_prevention': '', 'occupational_hygiene': '',
                'storage_conditions': '', 'storage_rooms': '', 'storage_assembly': '',
                'specific_end_use': ''
            },
            'section_8': {
                'control_parameters': '',
                'biological_limit_values': '',
                'dnel_pnec': '',
                'engineering_controls': '',
                'eye_protection': '',
                'skin_protection': '',
                'respiratory_protection': '',
                'body_protection': '',
                'environmental_exposure': '',
                'ppe_icons': {}
            },
            'section_9': {
                'physical_state': '', 'colour': '', 'odour': '',
                'safety_data': [], 'other_info': ''
            },
            'section_10': {
                'reactivity': '', 'chemical_stability': '', 'hazardous_reactions': '',
                'conditions_to_avoid': '', 'incompatible_materials': '', 'hazardous_decomposition': ''
            },
            'section_11': {
                'acute_toxicity': '', 'skin_corrosion': '', 'eye_damage': '', 'sensitisation': '',
                'mutagenicity': '', 'carcinogenicity': '', 'reproductive_toxicity': '',
                'stot_single': '', 'stot_repeated': '', 'aspiration_hazard': '',
                'other_hazards': ''
            },
            'section_12': {
                'ecotox_components': [], 'persistence_info': '', 'bioaccumulation': '',
                'mobility_info': '', 'pbt_result': '', 'endocrine_disrupting_info': '',
                'other_adverse_effects_info': ''
            },
            'section_13': {
                'waste_treatment': '', 'waste_code_product': '', 'waste_code_product_desc': '',
                'waste_code_packaging': '', 'waste_code_packaging_desc': '',
                'appropriate_disposal_product': '', 'appropriate_disposal_package': ''
            },
            'section_14': {
                'land': {}, 'inland': {}, 'sea': {}, 'air': {},
                'special_precautions': '', 'bulk_transport': ''
            },
            'section_15': {
                'eu_legislation': '', 'restrictions_of_occupation': '', 'stoerfallverordnung': '',
                'betrsichv': '', 'wgk': '', 'storage_class': ''
            },
            'section_16': {
                'other_information': {
                    'indication_of_changes': [], 'abbreviations': [],
                    'literature_references': '', 'training_advice': '', 'additional_info_lines': []
                }
            }
        }
        
        self.blocks = []
        self._flatten_blocks(self.raw_data.get('children', []))
        self.sections_content = self._group_by_sections()

    def _flatten_blocks(self, children: List[Dict[str, Any]]):
        for child in children:
            if child.get('block_type') == 'Page' or 'children' in child:
                self._flatten_blocks(child.get('children', []))
            else:
                self.blocks.append(child)

    def _group_by_sections(self) -> Dict[int, List[Dict[str, Any]]]:
        sections = {}
        current_sec = 0
        
        # Regex to match "SECTION 1", "SECTION 2", etc.
        sec_pattern = re.compile(r'SECTION\s+(\d+)', re.IGNORECASE)
        
        for block in self.blocks:
            html = block.get('html', '')
            match = sec_pattern.search(html)
            
            if match and block.get('block_type') == 'SectionHeader':
                current_sec = int(match.group(1))
            elif match and 'background-color' in html and ('h1' in html or 'h2' in html):
                 # Fallback if block_type isn't SectionHeader but looks like a header
                 current_sec = int(match.group(1))

            if current_sec > 0:
                if current_sec not in sections:
                    sections[current_sec] = []
                sections[current_sec].append(block)
        
        return sections

    def parse(self) -> Dict[str, Any]:
        self._parse_meta()
        for i in range(1, 17):
            if i in self.sections_content:
                parse_method = getattr(self, f'_parse_section_{i}', None)
                if parse_method:
                    parse_method(self.sections_content[i])
                else:
                    self._parse_generic_section(i, self.sections_content[i])
        
        # Post-processing
        self._extract_ppe_icons()
        return self.data

    def _parse_meta(self):
        # Extract from first page or top of doc
        all_html = "".join([b.get('html', '') for b in self.blocks[:20]])
        
        # Trade Name
        tn_match = re.search(r'Trade name/designation:.*?</b></p><p[^>]*>(.*?)</p>', all_html, re.S)
        if tn_match:
            self.data['meta']['product_name'] = self._clean_html(tn_match.group(1))
            self.data['section_1']['product_identifier']['trade_name'] = self.data['meta']['product_name']
            
        # Version
        v_match = re.search(r'Version:\s*(\d+\.?\d*)', all_html)
        if v_match:
            self.data['meta']['version'] = v_match.group(1)
            
        # Revision Date
        rd_match = re.search(r'Revision date:\s*([\d\.]+)', all_html)
        if rd_match:
            self.data['meta']['revision_date'] = rd_match.group(1)
            
        # Print Date
        pd_match = re.search(r'Print date:\s*([\d\.]+)', all_html)
        if pd_match:
            self.data['meta']['print_date'] = pd_match.group(1)

    def _parse_section_1(self, blocks: List[Dict]):
        content = "".join([b.get('html', '') for b in blocks])
        
        # Article No
        art_match = re.search(r'Article No.:</h4><p[^>]*>(.*?)</p>', content, re.S)
        if art_match:
            self.data['section_1']['product_identifier']['item_no'] = self._clean_html(art_match.group(1))
            
        # UFI
        ufi_match = re.search(r'UFI:</h4><p[^>]*>(.*?)</p>', content, re.S)
        if ufi_match:
            self.data['section_1']['product_identifier']['ufi'] = self._clean_html(ufi_match.group(1))

        # Supplier
        supp_match = re.search(r'supplier of the safety data sheet</h3><p[^>]*><b>.*?</b></p><p[^>]*>(.*?)</p><p[^>]*>(.*?)</p><p[^>]*>(.*?)</p><p[^>]*>(.*?)</p>', content, re.S)
        if supp_match:
            self.data['section_1']['supplier_details']['name'] = self._clean_html(supp_match.group(1))
            self.data['section_1']['supplier_details']['address'] = f"{self._clean_html(supp_match.group(2))}, {self._clean_html(supp_match.group(3))}"
            self.data['section_1']['supplier_details']['country'] = self._clean_html(supp_match.group(4))

        # Phone / Email / Website
        tel_match = re.search(r'Telephone:</b>\s*(.*?)</p>', content)
        if tel_match: self.data['section_1']['supplier_details']['phone'] = self._clean_html(tel_match.group(1))
        
        mail_match = re.search(r'E-mail:</b>\s*(.*?)</p>', content)
        if mail_match: self.data['section_1']['supplier_details']['email'] = self._clean_html(mail_match.group(1))
        
        web_match = re.search(r'Website:</b>\s*(.*?)</p>', content)
        if web_match: self.data['section_1']['supplier_details']['website'] = self._clean_html(web_match.group(1))

        # Emergency
        em_match = re.search(r'Emergency telephone number</h3><p[^>]*>(.*?),\s*([\d\+\s]+)</p>', content)
        if em_match:
            self.data['section_1']['emergency_phone']['description'] = self._clean_html(em_match.group(1))
            self.data['section_1']['emergency_phone']['number'] = self._clean_html(em_match.group(2))

    def _parse_section_2(self, blocks: List[Dict]):
        content = "".join([b.get('html', '') for b in blocks])
        
        # Classifications from Table
        table_matches = re.findall(r'<tr>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*</tr>', content, re.S)
        for cat, stmt, proc in table_matches:
            if "Hazard classes" in cat: continue
            code_match = re.search(r'(H\d+):\s*(.*)', stmt)
            code = code_match.group(1) if code_match else ''
            text = code_match.group(2) if code_match else stmt
            self.data['section_2']['classification'].append({
                'category': self._clean_html(cat),
                'code': code,
                'statement': self._clean_html(text),
                'procedure': self._clean_html(proc)
            })

        # Pictograms from Images
        for block in blocks:
            if block.get('block_type') == 'Picture' or '<img' in block.get('html', ''):
                img_html = block.get('html', '')
                alt_match = re.search(r'alt="(GHS\d+)', img_html)
                if alt_match:
                    code = alt_match.group(1)
                    if code not in self.data['section_2']['labelling']['pictograms']:
                        self.data['section_2']['labelling']['pictograms'].append(code)

        # Signal Word
        signal_match = re.search(r'Signal word:</b>\s*<b>(.*?)</b>', content)
        if signal_word := signal_match.group(1) if signal_match else '':
             self.data['section_2']['labelling']['signal_word'] = signal_word
        else:
             # Try other variant
             signal_match = re.search(r'Signal word:\s*(Danger|Warning)', content, re.I)
             if signal_match:
                 self.data['section_2']['labelling']['signal_word'] = signal_match.group(1)

        # Hazard Statements
        h_stmts = re.findall(r'(H\d+):\s*(.*?)</p>', content)
        for code, text in h_stmts:
            if not any(s['code'] == code for s in self.data['section_2']['labelling']['hazard_statements']):
                self.data['section_2']['labelling']['hazard_statements'].append({'code': code, 'text': self._clean_html(text)})

        # Precautionary Statements
        p_stmts = re.findall(r'(P\d+(?:\s*\+\s*P\d+)*):\s*(.*?)</p>', content)
        for code, text in p_stmts:
            clean_text = self._clean_html(text)
            if code.startswith('P2'):
                self.data['section_2']['labelling']['precautionary_statements']['prevention'].append({'code': code, 'text': clean_text})
            elif code.startswith('P3'):
                self.data['section_2']['labelling']['precautionary_statements']['response'].append({'code': code, 'text': clean_text})

    def _parse_section_3(self, blocks: List[Dict]):
        content = "".join([b.get('html', '') for b in blocks])
        # Mixture components table
        # Structure: Product identifiers | Substance name / Classification | Concentration
        rows = re.findall(r'<tr>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*</tr>', content, re.S)
        for ids, name_class, conc in rows:
            if "Product identifiers" in ids: continue
            
            # Extract name and classification
            name_match = re.search(r'<b>(.*?)</b>', name_class)
            name = name_match.group(1) if name_match else self._clean_html(name_class.split('<')[0])
            
            classes = re.findall(r'<div>(.*?)</div>', name_class)
            
            # Extract IDs (CAS, EC, etc.)
            cas = re.search(r'CAS No.:\s*([\d-]+)', ids)
            ec = re.search(r'EC No.:\s*([\d-]+)', ids)
            
            self.data['section_3']['mixture_components'].append({
                'name': self._clean_html(name),
                'cas': cas.group(1) if cas else '',
                'ec': ec.group(1) if ec else '',
                'concentration': self._clean_html(conc),
                'classification': [self._clean_html(c) for c in classes if c],
                'toxicological_info': [],
                'ate_values': []
            })

    def _parse_section_8(self, blocks: List[Dict]):
        content = "".join([b.get('html', '') for b in blocks])
        
        # OEL Table mapping (simplified)
        self.data['section_8']['control_parameters'] = self._extract_section_text(content, r'Occupational exposure limit values', r'Biological limit values|DNEL-/PNEC-values|8.2.')
        
        # PPE texts
        self.data['section_8']['eye_protection'] = self._extract_section_text(content, r'Eye/face protection:', r'Skin protection:|Respiratory protection:|Other protection')
        self.data['section_8']['skin_protection'] = self._extract_section_text(content, r'Skin protection:', r'Respiratory protection:|Other protection|Environmental')
        self.data['section_8']['respiratory_protection'] = self._extract_section_text(content, r'Respiratory protection:', r'Other protection|Environmental|8.2.3.')
        self.data['section_8']['body_protection'] = self._extract_section_text(content, r'Other protection measures:', r'Environmental|8.2.3.|SECTION 9')

    def _parse_section_9(self, blocks: List[Dict]):
        content = "".join([b.get('html', '') for b in blocks])
        
        # Appearance
        state = re.search(r'Physical state:</b>\s*(.*?)(?:<br|</div>)', content)
        if state: self.data['section_9']['physical_state'] = self._clean_html(state.group(1))
        
        color = re.search(r'Colour:</b>\s*(.*?)(?:<br|</div>)', content)
        if color: self.data['section_9']['colour'] = self._clean_html(color.group(1))
        
        odour = re.search(r'Odour:</b>\s*(.*?)(?:<br|</div>)', content)
        if odour: self.data['section_9']['odour'] = self._clean_html(odour.group(1))

        # Safety data table
        rows = re.findall(r'<tr>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*</tr>', content, re.S)
        for param, val, temp, meth in rows:
            if "Parameter" in param: continue
            self.data['section_9']['safety_data'].append({
                'parameter': self._clean_html(param),
                'value': self._clean_html(val),
                'temperature': self._clean_html(temp),
                'method': self._clean_html(meth)
            })

    def _parse_generic_section(self, num: int, blocks: List[Dict]):
        # Just concatenate HTML for sections we don't have deep parsers for yet
        # This keeps the layout fidelity
        content = "".join([b.get('html', '') for b in blocks])
        section_key = f'section_{num}'
        
        # Try to clean up standard headers from the body
        content = re.sub(r'<h[23][^>]*>SECTION.*?</h[23]>', '', content, flags=re.I|re.S)
        
        if num == 4:
            self.data['section_4']['description']['general'] = content
        elif num == 14:
             # Basic mapping for transport
             self.data['section_14']['land']['un_number'] = re.search(r'UN\s*(\d{4})', content).group(1) if re.search(r'UN\s*(\d{4})', content) else ''
        
        # For simplicity, we can store the whole block in a 'body' or similar if needed, 
        # but the template expects specific fields. 
        # For now, we'll map the raw HTML to appropriate fields if possible.
        self.data[section_key]['raw_html'] = content

    def _extract_section_text(self, content: str, start_pattern: str, end_pattern: str) -> str:
        match = re.search(f'{start_pattern}(.*?)(?:{end_pattern})', content, re.S | re.I)
        if match:
            return self._clean_html(match.group(1)).strip()
        return ''

    def _clean_html(self, html: str) -> str:
        # Remove tags but keep text
        text = re.sub(r'<[^>]*>', ' ', html)
        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _extract_ppe_icons(self):
        # reuse the logic from sds_parser
        eye = self.data['section_8'].get('eye_protection', '')
        skin = self.data['section_8'].get('skin_protection', '')
        resp = self.data['section_8'].get('respiratory_protection', '')
        
        from sds_parser import NewSDScomParser
        parser_helper = NewSDScomParser.__new__(NewSDScomParser)
        # We need a dummy object to call the method
        self.data['section_8']['ppe_icons'] = parser_helper._get_ppe_icons_from_text(eye, skin, resp)

def parse_sds_json(json_path: str) -> Dict[str, Any]:
    try:
        parser = SDSJsonParser(json_path)
        return parser.parse()
    except Exception as e:
        logger.error(f"Error parsing JSON: {e}", exc_info=True)
        return {}

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        res = parse_sds_json(sys.argv[1])
        print(json.dumps(res, indent=2))
