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
                'other_hazards': '',
                'toxicity_tables': [],
                'text_blocks': []
            },
            'section_12': {
                'ecotox_components': [], 'persistence_info': '', 'bioaccumulation': '',
                'mobility_info': '', 'pbt_result': '', 'endocrine_disrupting_info': '',
                'other_adverse_effects_info': '',
                'ecotox_tables': [],
                'text_blocks': []
            },
            'section_13': {
                'waste_treatment': '', 'waste_code_product': '', 'waste_code_product_desc': '',
                'waste_code_packaging': '', 'waste_code_packaging_desc': '',
                'appropriate_disposal_product': '', 'appropriate_disposal_package': ''
            },
            'section_14': {
                'land': {}, 'inland': {}, 'sea': {}, 'air': {},
                'special_precautions': '', 'bulk_transport': '',
                'transport_icons': []
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
        # Block-based parsing: each label is a separate block, value follows in next block
        texts = [self._clean_html(b.get('html', '')) for b in blocks]

        def next_val(label):
            """Return the text of the block immediately after the block containing label."""
            for i, t in enumerate(texts):
                if label.lower() in t.lower() and i + 1 < len(texts):
                    return texts[i + 1]
            return ''

        # Product identifier
        self.data['section_1']['product_identifier']['trade_name'] = next_val('Trade name')
        self.data['meta']['product_name'] = self.data['section_1']['product_identifier']['trade_name'] or 'Unknown'
        self.data['section_1']['product_identifier']['item_no'] = next_val('Article No')
        self.data['section_1']['product_identifier']['ufi'] = next_val('UFI')

        # Relevant uses
        self.data['section_1']['relevant_uses']['product_type'] = next_val('Use of the substance')
        lcs = next_val('Life cycle stage')
        self.data['section_1']['relevant_uses']['lcs'] = lcs
        su = next_val('Sector of uses')
        if su:
            m = re.match(r'(SU\s*\d+):\s*(.*)', su)
            self.data['section_1']['relevant_uses']['su'] = m.group(1) if m else su
            self.data['section_1']['relevant_uses']['su_fulltext'] = m.group(2) if m else ''
        pc = next_val('Product Categories')
        if pc:
            m = re.match(r'(PC\s*\d+):\s*(.*)', pc)
            self.data['section_1']['relevant_uses']['pc1'] = m.group(1) if m else pc
            self.data['section_1']['relevant_uses']['pc1_fulltext'] = m.group(2) if m else ''

        # Supplier — collect consecutive blocks after supplier header
        for i, t in enumerate(texts):
            if 'supplier' in t.lower() and 'manufacturer' in t.lower():
                remaining = texts[i+1:]
                # name is first bold-looking block
                if len(remaining) > 0: self.data['section_1']['supplier_details']['name'] = remaining[0]
                addr_parts = []
                for rt in remaining[1:]:
                    if any(kw in rt.lower() for kw in ['telephone', 'e-mail', 'website', 'emergency', '1.4']):
                        break
                    addr_parts.append(rt)
                if addr_parts:
                    self.data['section_1']['supplier_details']['address'] = ', '.join(addr_parts[:-1]) if len(addr_parts) > 1 else addr_parts[0]
                    self.data['section_1']['supplier_details']['country'] = addr_parts[-1] if len(addr_parts) > 1 else ''
                break

        # Phone / Email / Website — may be in same block as label
        for t in texts:
            if t.lower().startswith('telephone:'):
                self.data['section_1']['supplier_details']['phone'] = t.split(':', 1)[1].strip()
            elif t.lower().startswith('e-mail:'):
                self.data['section_1']['supplier_details']['email'] = t.split(':', 1)[1].strip()
            elif t.lower().startswith('website:'):
                self.data['section_1']['supplier_details']['website'] = t.split(':', 1)[1].strip()

        # Emergency phone
        em = next_val('Emergency telephone')
        if not em:
            # fallback: find block with phone number pattern after section 1.4
            for t in texts:
                if re.search(r'\+\d{2,}', t) and any(kw in t.lower() for kw in ['vergiftung', 'poison', 'emergency', '24h', 'notruf']):
                    em = t
                    break
        if em:
            m = re.search(r'(.+?),\s*((?:\+|00)\d[\d\s]+)', em)
            if m:
                self.data['section_1']['emergency_phone']['description'] = m.group(1).strip()
                self.data['section_1']['emergency_phone']['number'] = m.group(2).strip()
            else:
                # Try: "Description 24h: +49..."
                m2 = re.search(r'(.+?)(?:24h:|24 h:)?\s*((?:\+|00)\d[\d\s]{6,})', em)
                if m2:
                    self.data['section_1']['emergency_phone']['description'] = m2.group(1).strip().rstrip(',')
                    self.data['section_1']['emergency_phone']['number'] = m2.group(2).strip()
                else:
                    self.data['section_1']['emergency_phone']['number'] = em

    def _parse_section_2(self, blocks: List[Dict]):
        content = "".join([b.get('html', '') for b in blocks])
        
        # Classifications from Table
        table_matches = re.findall(r'<tr[^>]*>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*</tr>', content, re.S | re.I)
        for cat, stmt, proc in table_matches:
            if "Hazard classes" in cat or "hazard categories" in cat.lower(): continue
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

        # Signal Word - try multiple patterns
        signal_match = re.search(r'Signal word[:\.]?\s*(?:</b>)?\s*(?:<b>)?(Danger|Warning)', content, re.I)
        if signal_match:
            self.data['section_2']['labelling']['signal_word'] = signal_match.group(1)

        # Hazard Statements from tables
        h_stmts = re.findall(r'<td[^>]*>(H\d+(?:\s*\+\s*H\d+)*)</td>\s*<td[^>]*>(.*?)</td>', content, re.S | re.I)
        for code, text in h_stmts:
            if not any(s['code'] == code for s in self.data['section_2']['labelling']['hazard_statements']):
                self.data['section_2']['labelling']['hazard_statements'].append({'code': code, 'text': self._clean_html(text)})

        # Precautionary Statements from tables
        p_stmts = re.findall(r'<td[^>]*>(P\d+(?:\s*\+\s*P\d+)*)</td>\s*<td[^>]*>(.*?)</td>', content, re.S | re.I)
        for code, text in p_stmts:
            clean_text = self._clean_html(text)
            code_clean = code.replace(' ', '')
            if code_clean.startswith('P2'):
                self.data['section_2']['labelling']['precautionary_statements']['prevention'].append({'code': code_clean, 'text': clean_text})
            elif code_clean.startswith('P3') or code_clean.startswith('P4'):
                self.data['section_2']['labelling']['precautionary_statements']['response'].append({'code': code_clean, 'text': clean_text})

    def _parse_section_3(self, blocks: List[Dict]):
        for b in blocks:
            if b.get('block_type') != 'Table':
                continue
            html = b.get('html', '')
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.S | re.I)
            for row in rows:
                cells = re.findall(r'<(?:td|th)[^>]*>(.*?)</(?:td|th)>', row, re.S | re.I)
                if len(cells) < 2:
                    continue
                ids_html, name_html = cells[0], cells[1]
                conc = self._clean_html(cells[2]) if len(cells) > 2 else ''

                # Skip header row
                if 'product identifiers' in ids_html.lower():
                    continue

                cas = re.search(r'CAS(?:\s*No\.?)?:?\s*([\d\-]+)', ids_html, re.I)
                ec  = re.search(r'EC(?:\s*No\.?)?:?\s*([\d\-]+)', ids_html, re.I)
                idx = re.search(r'Index(?:\s*No\.?)?:?\s*([\d\-]+)', ids_html, re.I)
                reach = re.search(r'REACH(?:\s*No\.?)?:?\s*([\d\-/]+)', ids_html, re.I)

                # Name: first <b> or first text
                name_m = re.search(r'<b>([^<]+)</b>', name_html)
                name = self._clean_html(name_m.group(1)) if name_m else self._clean_html(name_html.split('<')[0])

                # Classifications: <div> entries after the name
                classes = [self._clean_html(c) for c in re.findall(r'<div[^>]*>([^<]+)</div>', name_html) if self._clean_html(c)]

                self.data['section_3']['mixture_components'].append({
                    'name': name,
                    'cas': cas.group(1) if cas else '',
                    'ec': ec.group(1) if ec else '',
                    'index_no': idx.group(1) if idx else '',
                    'reach_no': reach.group(1) if reach else '',
                    'concentration': conc,
                    'classification': classes,
                    'pictograms': [],
                    'signal_word': '',
                    'toxicological_info': [],
                    'ate_values': [],
                })

    def _parse_section_5(self, blocks: List[Dict]):
        self.data['section_5'].update(self._parse_labeled_section(blocks, {
            'suitable_media':      ['Suitable extinguishing media', '5.1.'],
            'unsuitable_media':    ['Unsuitable extinguishing media'],
            'special_hazards':     ['Special hazards', '5.2.'],
            'combustion_products': ['Hazardous combustion products', 'combustion'],
            'firefighter_advice':  ['Advice for firefighters', '5.3.'],
            'additional_info':     ['Additional information', '5.4.'],
        }))

    def _parse_section_4(self, blocks: List[Dict]):
        desc = self._parse_labeled_section(blocks, {
            'general':        ['General information', '4.1.'],
            'inhalation':     ['Following inhalation', 'inhalation'],
            'skin':           ['skin contact', 'skin'],
            'eye':            ['eye contact', 'eye'],
            'ingestion':      ['Following ingestion', 'ingestion'],
            'self_protection':['Self-protection of the first aider', 'first aider'],
        })
        self.data['section_4']['description'].update(desc)
        rest = self._parse_labeled_section(blocks, {
            'symptoms':  ['4.2.', 'Most important symptoms', 'symptoms'],
            'treatment': ['4.3.', 'immediate medical attention', 'treatment'],
        })
        self.data['section_4'].update(rest)

    def _parse_section_6(self, blocks: List[Dict]):
        self.data['section_6'].update(self._parse_labeled_section(blocks, {
            'personal_precautions':      ['6.1.1.', 'non-emergency personnel'],
            'protective_equipment':      ['Protective equipment'],
            'emergency_responders':      ['6.1.2.', 'emergency responders'],
            'environmental_precautions': ['6.2.', 'Environmental precautions'],
            'containment':               ['For containment', 'containment and cleaning'],
            'cleaning':                  ['For cleaning up'],
            'other_sections':            ['6.4.', 'Reference to other sections'],
        }))

    def _parse_section_7(self, blocks: List[Dict]):
        self.data['section_7'].update(self._parse_labeled_section(blocks, {
            'safe_handling':        ['safe handling', 'Advices on safe handling', '7.1.'],
            'fire_prevention':      ['Fire prevent', 'fire prevention'],
            'occupational_hygiene': ['occupational hygiene', 'general occupational'],
            'storage_conditions':   ['storage conditions', 'Technical measures', '7.2.'],
            'storage_rooms':        ['storage rooms', 'Requirements for storage'],
            'storage_assembly':     ['storage assembly', 'Hints on storage'],
            'specific_end_use':     ['Specific end use', '7.3.'],
        }))

    def _parse_section_8(self, blocks: List[Dict]):
        self.data['section_8']['occupational_exposure_limits'] = []
        self.data['section_8']['dnel_pnec_values'] = []
        self.data['section_8']['biological_limit_values'] = 'No data available'

        for b in blocks:
            if b.get('block_type') != 'Table':
                continue
            html = b.get('html', '')
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.S | re.I)
            if not rows:
                continue
            header_text = self._clean_html(rows[0]).lower() if rows else ''

            if 'limit value type' in header_text or 'long-term' in header_text or 'parameter' in header_text:
                for row in rows[1:]:
                    cells = re.findall(r'<(?:td|th)[^>]*>(.*?)</(?:td|th)>', row, re.S | re.I)
                    if len(cells) < 2:
                        continue
                    self.data['section_8']['occupational_exposure_limits'].append({
                        'limit_type': self._clean_html(cells[0]),
                        'substance':  self._clean_html(cells[1]),
                        'formatted_values': self._clean_html(cells[2]) if len(cells) > 2 else '',
                    })
            elif 'dnel' in header_text or 'pnec' in header_text:
                for row in rows[1:]:
                    cells = re.findall(r'<(?:td|th)[^>]*>(.*?)</(?:td|th)>', row, re.S | re.I)
                    if len(cells) < 2:
                        continue
                    self.data['section_8']['dnel_pnec_values'].append({
                        'substance': self._clean_html(cells[0]),
                        'value':     self._clean_html(cells[1]),
                        'type':      self._clean_html(cells[2]) if len(cells) > 2 else '',
                    })

        ppe = self._parse_labeled_section(blocks, {
            'engineering_controls':   ['8.2.1.', 'engineering controls', 'engineering'],
            'eye_protection':         ['Eye/face protection', 'eye'],
            'skin_protection':        ['Skin protection', 'skin'],
            'respiratory_protection': ['Respiratory protection', 'respiratory'],
            'body_protection':        ['Other protection measures', 'body'],
            'environmental_exposure': ['8.2.3.', 'Environmental exposure'],
        })
        self.data['section_8'].update(ppe)

    def _parse_section_10(self, blocks: List[Dict]):
        self.data['section_10'].update(self._parse_labeled_section(blocks, {
            'reactivity':              ['Reactivity', '10.1.'],
            'chemical_stability':      ['Chemical stability', '10.2.'],
            'hazardous_reactions':     ['hazardous reactions', '10.3.'],
            'conditions_to_avoid':     ['Conditions to avoid', '10.4.'],
            'incompatible_materials':  ['Incompatible materials', '10.5.'],
            'hazardous_decomposition': ['decomposition products', '10.6.'],
        }))

    def _parse_labeled_section(self, blocks: List[Dict], field_map: dict) -> dict:
        """Generic block-based parser: matches h3/h4 label blocks to field names,
        then takes the text of the next Text block as value."""
        result = {k: '' for k in field_map}
        texts = [(b.get('block_type', ''), self._clean_html(b.get('html', ''))) for b in blocks]

        for i, (btype, text) in enumerate(texts):
            text_lower = text.lower()
            for field, keywords in field_map.items():
                if result[field]:  # already filled
                    continue
                if any(kw.lower() in text_lower for kw in keywords):
                    # Look for next Text block (within next 5 blocks)
                    for j in range(i + 1, min(i + 5, len(texts))):
                        if texts[j][0] == 'Text' and texts[j][1].strip():
                            result[field] = texts[j][1]
                            break
                    # If no Text block found, try to get content from current block if it's long
                    if not result[field] and len(text) > 50:
                        result[field] = text
        return result

    def _parse_section_9(self, blocks: List[Dict]):
        # Appearance: individual Text blocks
        texts = [(b.get('block_type',''), self._clean_html(b.get('html',''))) for b in blocks]
        appearance_parts = []
        for btype, text in texts:
            if btype == 'Text' and any(kw in text.lower() for kw in ['physical state', 'colour', 'color', 'odour', 'odor', 'flammab']):
                appearance_parts.append(text)
        self.data['section_9']['appearance'] = '<br>'.join(appearance_parts)

        # Safety data table
        for b in blocks:
            if b.get('block_type') != 'Table':
                continue
            html = b.get('html', '')
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.S | re.I)
            for row in rows:
                cells = re.findall(r'<(?:td|th)[^>]*>(.*?)</(?:td|th)>', row, re.S | re.I)
                if len(cells) < 2:
                    continue
                param = self._clean_html(cells[0])
                if not param or param.lower() in ('parameter', 'eigenschaft', 'property'):
                    continue
                self.data['section_9']['safety_data'].append({
                    'parameter':   param,
                    'value':       self._clean_html(cells[1]),
                    'temperature': self._clean_html(cells[2]) if len(cells) > 2 else '',
                    'method':      self._clean_html(cells[3]) if len(cells) > 3 else '',
                })

        other = self._parse_labeled_section(blocks, {'other_info': ['9.2.', 'Other information']})
        self.data['section_9']['other_info'] = other.get('other_info', '')

    def _parse_section_11(self, blocks: List[Dict]):
        content = "".join([b.get('html', '') for b in blocks])
        
        # Extrahiere reine Textblöcke (vor, zwischen und nach den Tabellen)
        text_parts = re.split(r'<table[^>]*>.*?</table>', content, flags=re.S | re.I)
        cleaned_texts = [self._clean_html(part) for part in text_parts if self._clean_html(part).strip()]
        self.data['section_11']['text_blocks'] = cleaned_texts

        # Extrahiere alle Tabellen individuell (unterstützt verschiedene Tox-Endpunkte)
        tables = re.findall(r'<table[^>]*>(.*?)</table>', content, re.S | re.I)
        for table_html in tables:
            table_data = []
            table_rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.S | re.I)
            for row_idx, row_content in enumerate(table_rows):
                cell_data = []
                # Finde das Tag (td/th), die Attribute (wo die Breite steht) und den Inhalt
                cells = re.findall(r'<(td|th)([^>]*)>(.*?)</\1>', row_content, re.S | re.I)
                for tag, attrs, inner_html in cells:
                    width = "auto"
                    # Suche nach style="width: 15%;" oder width="15%"
                    w_match = re.search(r'width\s*:\s*([^;"]+)', attrs, re.I)
                    if w_match:
                        width = w_match.group(1).strip()
                    else:
                        w_attr = re.search(r'width\s*=\s*"([^"]+)"', attrs, re.I)
                        if w_attr:
                            width = w_attr.group(1).strip()
                            
                    colspan = "1"
                    c_match = re.search(r'colspan\s*=\s*["\']?(\d+)["\']?', attrs, re.I)
                    if c_match: colspan = c_match.group(1)
                        
                    rowspan = "1"
                    r_match = re.search(r'rowspan\s*=\s*["\']?(\d+)["\']?', attrs, re.I)
                    if r_match: rowspan = r_match.group(1)
                        
                    is_header = (row_idx == 0) or (tag.lower() == 'th')
                    cell_data.append({
                        'text': self._clean_html(inner_html), 'width': width, 
                        'colspan': colspan, 'rowspan': rowspan, 'is_header': is_header
                    })
                if len(cell_data) >= 2:
                    table_data.append(cell_data)
            if table_data:
                self.data['section_11']['toxicity_tables'].append(table_data)
                
        self.data['section_11'].update(self._parse_labeled_section(blocks, {
            'acute_toxicity': ['Acute toxicity'],
            'skin_corrosion': ['Skin corrosion', 'Irritation'],
            'eye_damage': ['Serious eye damage', 'eye irritation'],
            'sensitisation': ['Respiratory or skin sensitisation'],
            'mutagenicity': ['Germ cell mutagenicity'],
            'carcinogenicity': ['Carcinogenicity'],
            'reproductive_toxicity': ['Reproductive toxicity'],
            'stot_single': ['Specific target organ toxicity - single exposure'],
            'stot_repeated': ['Specific target organ toxicity - repeated exposure'],
            'aspiration_hazard': ['Aspiration hazard']
        }))

        # Behalte den gesamten HTML-Text als Fallback für die Fließtexte bei
        self.data['section_11']['raw_html'] = content

    def _parse_section_12(self, blocks: List[Dict]):
        content = "".join([b.get('html', '') for b in blocks])
        
        # Extrahiere reine Textblöcke (vor, zwischen und nach den Tabellen)
        text_parts = re.split(r'<table[^>]*>.*?</table>', content, flags=re.S | re.I)
        cleaned_texts = [self._clean_html(part) for part in text_parts if self._clean_html(part).strip()]
        self.data['section_12']['text_blocks'] = cleaned_texts

        # Extrahiere alle Tabellen individuell
        tables = re.findall(r'<table[^>]*>(.*?)</table>', content, re.S | re.I)
        for table_html in tables:
            table_data = []
            table_rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.S | re.I)
            for row_idx, row_content in enumerate(table_rows):
                cell_data = []
                cells = re.findall(r'<(td|th)([^>]*)>(.*?)</\1>', row_content, re.S | re.I)
                for tag, attrs, inner_html in cells:
                    width = "auto"
                    w_match = re.search(r'width\s*:\s*([^;"]+)', attrs, re.I)
                    if w_match:
                        width = w_match.group(1).strip()
                    else:
                        w_attr = re.search(r'width\s*=\s*"([^"]+)"', attrs, re.I)
                        if w_attr:
                            width = w_attr.group(1).strip()
                            
                    colspan = "1"
                    c_match = re.search(r'colspan\s*=\s*["\']?(\d+)["\']?', attrs, re.I)
                    if c_match: colspan = c_match.group(1)
                        
                    rowspan = "1"
                    r_match = re.search(r'rowspan\s*=\s*["\']?(\d+)["\']?', attrs, re.I)
                    if r_match: rowspan = r_match.group(1)
                        
                    is_header = (row_idx == 0) or (tag.lower() == 'th')
                    cell_data.append({
                        'text': self._clean_html(inner_html), 'width': width, 
                        'colspan': colspan, 'rowspan': rowspan, 'is_header': is_header
                    })
                if len(cell_data) >= 2:
                    table_data.append(cell_data)
            if table_data:
                self.data['section_12']['ecotox_tables'].append(table_data)
                
        self.data['section_12'].update(self._parse_labeled_section(blocks, {
            'persistence_info': ['Persistence and degradability', '12.2.'],
            'bioaccumulation': ['Bioaccumulative potential', '12.3.'],
            'mobility_info': ['Mobility in soil', '12.4.'],
            'pbt_result': ['Results of PBT and vPvB assessment', '12.5.'],
            'endocrine_disrupting_info': ['Endocrine disrupting properties', '12.6.'],
            'other_adverse_effects_info': ['Other adverse effects', '12.7.']
        }))

        # Behalte den gesamten HTML-Text als Fallback für die Fließtexte bei
        self.data['section_12']['raw_html'] = content

    def _parse_section_13(self, blocks: List[Dict]):
        self.data['section_13'].update(self._parse_labeled_section(blocks, {
            'waste_treatment': ['Waste treatment methods', '13.1.'],
            'eu_requirements': ['EU legislation', 'European Waste List'],
        }))
        
        content = "".join([b.get('html', '') for b in blocks])
        
        prod_match = re.search(r'Waste code product\s*([\d\s\*]+)', content, re.I)
        if prod_match:
            self.data['section_13']['waste_code_product'] = prod_match.group(1).strip()
            
        pack_match = re.search(r'Waste code packaging\s*([\d\s\*]+)', content, re.I)
        if pack_match:
            self.data['section_13']['waste_code_packaging'] = pack_match.group(1).strip()
            
        self.data['section_13']['raw_html'] = content

    def _parse_section_14(self, blocks: List[Dict]):
        content = "".join([b.get('html', '') for b in blocks])
        
        un_match = re.search(r'UN\s*(\d{4})', content)
        un_number = un_match.group(0) if un_match else ''
        
        if un_number:
            self.data['section_14']['land']['un_number'] = un_number
            self.data['section_14']['inland']['un_number'] = un_number
            self.data['section_14']['sea']['un_number'] = un_number
            self.data['section_14']['air']['un_number'] = un_number

        land_class = re.search(r'ADR/RID.*?Class(?:es)?:\s*([\d\.]+)', content, re.S|re.I)
        if land_class: self.data['section_14']['land']['transport_class'] = land_class.group(1)
        
        inland_class = re.search(r'ADN.*?Class(?:es)?:\s*([\d\.]+)', content, re.S|re.I)
        if inland_class: self.data['section_14']['inland']['transport_class'] = inland_class.group(1)
        
        sea_class = re.search(r'IMDG.*?Class(?:es)?:\s*([\d\.]+)', content, re.S|re.I)
        if sea_class: self.data['section_14']['sea']['transport_class'] = sea_class.group(1)
        
        air_class = re.search(r'IATA.*?Class(?:es)?:\s*([\d\.]+)', content, re.S|re.I)
        if air_class: self.data['section_14']['air']['transport_class'] = air_class.group(1)

        self.data['section_14'].update(self._parse_labeled_section(blocks, {
            'special_precautions': ['Special precautions for user', '14.6.'],
            'bulk_transport': ['Transport in bulk', '14.7.']
        }))
        
        try:
             from sds_parser import NewSDScomParser
             parser_helper = NewSDScomParser.__new__(NewSDScomParser)
             classes = [
                 self.data['section_14']['land'].get('transport_class'),
                 self.data['section_14']['inland'].get('transport_class'),
                 self.data['section_14']['sea'].get('transport_class'),
                 self.data['section_14']['air'].get('transport_class')
             ]
             self.data['section_14']['transport_icons'] = parser_helper._get_transport_icons_from_classes(classes)
        except Exception as e:
             logger.warning(f"Could not extract transport icons in JSON parser: {e}")
             
        self.data['section_14']['raw_html'] = content

    def _parse_section_15(self, blocks: List[Dict]):
        self.data['section_15'].update(self._parse_labeled_section(blocks, {
            'eu_legislation': ['EU legislation', '15.1.1.'],
            'restrictions_of_occupation': ['Restrictions of occupation', 'employment restrictions'],
            'wgk': ['Water hazard class', 'WGK'],
            'storage_class': ['Storage class'],
            'chemical_safety_assessment': ['Chemical Safety Assessment', '15.2.']
        }))
        
        content = "".join([self._clean_html(b.get('html', '')) for b in blocks])
        wgk_match = re.search(r'WGK:\s*(\d)', content, re.I)
        if not self.data['section_15']['wgk'] and wgk_match:
            self.data['section_15']['wgk'] = wgk_match.group(1)
            
        self.data['section_15']['raw_html'] = "".join([b.get('html', '') for b in blocks])

    def _parse_section_16(self, blocks: List[Dict]):
        info = self._parse_labeled_section(blocks, {
            'indication_of_changes_text': ['Indication of changes', '16.1.'],
            'abbreviations_text': ['Abbreviations and acronyms', '16.2.'],
            'literature_references': ['Key literature references', '16.3.'],
            'training_advice': ['Training advice', '16.6.'],
            'additional_info': ['Additional information', '16.7.']
        })
        
        if 'other_information' not in self.data['section_16']:
            self.data['section_16']['other_information'] = {}
            
        if info['indication_of_changes_text']:
            self.data['section_16']['other_information']['indication_of_changes'] = [{'section': '', 'description': info['indication_of_changes_text']}]
            
        if info['abbreviations_text']:
            self.data['section_16']['other_information']['abbreviations'] = [{'short': '', 'long': info['abbreviations_text']}]
            
        self.data['section_16']['other_information']['literature_references'] = info['literature_references']
        self.data['section_16']['other_information']['training_advice'] = info['training_advice']
        self.data['section_16']['other_information']['additional_info_lines'] = [info['additional_info']] if info['additional_info'] else []
        
        self.data['section_16']['raw_html'] = "".join([b.get('html', '') for b in blocks])

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
             
             # Extract transport classes to generate base64 icons
             land_class = re.search(r'ADR/RID.*?Class(?:es)?:\s*([\d\.]+)', content, re.S|re.I)
             inland_class = re.search(r'ADN.*?Class(?:es)?:\s*([\d\.]+)', content, re.S|re.I)
             sea_class = re.search(r'IMDG.*?Class(?:es)?:\s*([\d\.]+)', content, re.S|re.I)
             air_class = re.search(r'IATA.*?Class(?:es)?:\s*([\d\.]+)', content, re.S|re.I)
             
             if land_class: self.data['section_14']['land']['transport_class'] = land_class.group(1)
             if inland_class: self.data['section_14']['inland']['transport_class'] = inland_class.group(1)
             if sea_class: self.data['section_14']['sea']['transport_class'] = sea_class.group(1)
             if air_class: self.data['section_14']['air']['transport_class'] = air_class.group(1)
             
             try:
                 from sds_parser import NewSDScomParser
                 parser_helper = NewSDScomParser.__new__(NewSDScomParser)
                 classes = [
                     self.data['section_14']['land'].get('transport_class'),
                     self.data['section_14']['inland'].get('transport_class'),
                     self.data['section_14']['sea'].get('transport_class'),
                     self.data['section_14']['air'].get('transport_class')
                 ]
                 self.data['section_14']['transport_icons'] = parser_helper._get_transport_icons_from_classes(classes)
             except Exception as e:
                 logger.warning(f"Could not extract transport icons in JSON parser: {e}")
        
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
