#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Section Extractor
Extrahiert Abschnitt 15 und 16 aus einer PDF-Datei
"""

import re
import sys

def extract_sections_from_pdf(pdf_path):
    """Extrahiert Abschnitt 15 und 16 aus einer PDF-Datei"""
    try:
        import PyPDF2
    except ImportError:
        print("PyPDF2 nicht installiert. Bitte installieren mit: pip install PyPDF2")
        return None
    
    try:
        pdf = open(pdf_path, 'rb')
        reader = PyPDF2.PdfReader(pdf)
        
        full_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
        
        pdf.close()
        
        # Extrahiere Abschnitt 12, 15 und 16
        sections = {
            'section_1': extract_section(full_text, '1'),
            'section_2': extract_section(full_text, '2'),
            'section_8': extract_section(full_text, '8'),
            'section_12': extract_section(full_text, '12'),
            'section_15': extract_section(full_text, '15'),
            'section_16': extract_section(full_text, '16'),
            'section_3': extract_section(full_text, '3'),
            'ate_values': extract_ate_values(full_text)
        }
        
        return sections
        
    except Exception as e:
        print(f"Fehler beim Lesen der PDF: {e}")
        return None

def extract_ate_values(text):
    """Extrahiert ATE-Werte (Acute Toxicity Estimates) aus dem Text"""
    ate_values = {}
    
    # Muster für ATE-Werte
    ate_patterns = [
        r'ATE\s*\(?\s*oral\s*\)?\s*[:\s]*([\d.,>\<]+)\s*mg/kg',
        r'ATE\s*\(?\s*dermal\s*\)?\s*[:\s]*([\d.,>\<]+)\s*mg/kg',
        r'ATE\s*\(?\s*inhalation\s*,\s*vapour\s*\)?\s*[:\s]*([\d.,>\<]+)\s*mg/L',
        r'ATE\s*\(?\s*inhalation\s*,\s*dust/mist\s*\)?\s*[:\s]*([\d.,>\<]+)\s*mg/L'
    ]
    
    # Suche nach "Acute Toxicity Estimate" Abschnitten
    # Das ist normalerweise in Abschnitt 3.2
    
    # Extrahiere alle ATE-Werte
    matches = re.findall(r'ATE\s*\([^)]+\)\s*[:\s]*([\d.,>\<]+)\s*(mg/kg|mg/L)', text)
    
    for match in matches:
        value = match[0].strip()
        unit = match[1].strip()
        
        # Bestimme den Typ basierend auf dem Kontext
        context_match = re.search(rf'ATE\s*\(([^)]+)\).*?{re.escape(value)}\s*{unit}', text[:500], re.IGNORECASE)
        if context_match:
            ate_type = context_match.group(1).lower()
            if 'oral' in ate_type:
                ate_values['oral'] = f"ATE (oral) {value} mg/kg"
            elif 'dermal' in ate_type:
                ate_values['dermal'] = f"ATE (dermal) {value} mg/kg"
            elif 'vapour' in ate_type or 'inhalation' in ate_type:
                ate_values['inhalation_vapour'] = f"ATE (inhalation, vapour) {value} mg/L"
            elif 'dust' in ate_type or 'mist' in ate_type:
                ate_values['inhalation_dust'] = f"ATE (inhalation, dust/mist) {value} mg/L"
    
    return ate_values

def extract_section(text, section_num):
    """Extrahiert einen bestimmten Abschnitt aus dem Text"""
    # Muster für Abschnitt 15 oder 16
    patterns = [
        f'(?i)SECTION\\s*{section_num}[:\\s].*?(?=SECTION\\s*\\d+\\s*:|$)',
        f'(?i){section_num}\\.\\s+.*?(?=\\d+\\.\\s+|$)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            # Nimm den längsten Treffer
            return max(matches, key=len).strip()
    
    return ""

def parse_section_1(text):
    """Parst Abschnitt 1 - Identifikation"""
    result = {}
    
    # Notrufnummer-Name
    emergency_match = re.search(r'1\.4\.\s*Emergency telephone number\s*([^\n,]+)', text, re.IGNORECASE)
    if emergency_match:
        result['emergency_telephone_name'] = emergency_match.group(1).strip()
        
    return result

def parse_section_2(text):
    """Parst Abschnitt 2 - Mögliche Gefahren"""
    result = {
        'hazard_components': [],
        'endocrine_disruptors_human': ''
    }
    
    # Gefahrbestimmende Komponenten
    comp_match = re.search(r'Hazard components for labelling:?\s*([^\n]+)', text, re.IGNORECASE)
    if comp_match:
        result['hazard_components'] = [c.strip() for c in comp_match.group(1).split(',')]
        
    # Endokrine Disruptoren (Gesundheit)
    endo_match = re.search(r'2\.3\.?[^\d]*?Other hazards[\s\S]*?(This product does not contain a substance that has endocrine disrupting properties[^.\n]*\.)', text, re.IGNORECASE)
    if endo_match:
        result['endocrine_disruptors_human'] = endo_match.group(1).strip()
        
    return result

def parse_section_8(text):
    """Parst Abschnitt 8 - Arbeitsplatzgrenzwerte"""
    limits = []
    # This pattern tries to capture a whole block for one limit entry.
    # It starts with a limit type (like TRGS 900) and ends before the next one or the end of the section.
    pattern = re.compile(
        r'(TRGS 900 \(DE\)|IOELV \(EU\))\s+([\s\S]*?)(?=(TRGS 900 \(DE\)|IOELV \(EU\)|8\.2\.|$))',
        re.DOTALL
    )

    for match in pattern.finditer(text):
        limit_type = match.group(1).strip()
        block = match.group(2)
        
        limit_entry = {'limit_type': limit_type}

        # Extract substance name (usually the first line)
        name_match = re.search(r'([^\n]+)', block)
        if name_match:
            limit_entry['substance'] = name_match.group(1).strip()

        # Extract CAS and EC
        cas_match = re.search(r'CAS No\.:\s*([^\s\n]+)', block)
        if cas_match:
            limit_entry['CAS_number'] = cas_match.group(1).strip()
        
        ec_match = re.search(r'EC No\.:\s*([^\s\n]+)', block)
        if ec_match:
            limit_entry['ec'] = ec_match.group(1).strip()

        # Extract values and create a pre-formatted HTML block for the template
        long_term_match = re.search(r'①\s*([^\n]+)', block)
        short_term_match = re.search(r'②\s*([^\n]+)', block)
        remark_match = re.search(r'⑤\s*([^\n]+)', block)
        
        formatted_values = ""
        if long_term_match:
            formatted_values += f"① {long_term_match.group(1).strip()}<br>"
        if short_term_match:
            formatted_values += f"② {short_term_match.group(1).strip()}<br>"
        if remark_match:
            formatted_values += f"⑤ {remark_match.group(1).strip()}"
        
        limit_entry['formatted_values'] = formatted_values
        limits.append(limit_entry)
        
    return {'occupational_exposure_limits': limits}

def parse_section_15(text):
    """Parst Abschnitt 15 - Regulatory information"""
    result = {
        'eu_legislation': '',
        'national_legislation': []
    }
    
    # Suche nach EU legislation
    eu_match = re.search(r'(?i)EU.?legislation[:\s]*(.*?)(?=national|Regulation|$)', text, re.DOTALL)
    if eu_match:
        result['eu_legislation'] = eu_match.group(1).strip()
    
    # Suche nach national legislation
    national_matches = re.findall(r'(?i)(TRGS|Wasser Gefährdungs Klasse|Regulation)\s*[:\s]*([^\n]+)', text)
    for match in national_matches:
        result['national_legislation'].append({
            'label': match[0].strip(),
            'value': match[1].strip()
        })
    
    return result

def parse_section_16(text):
    """Parst Abschnitt 16 - Other information"""
    result = {
        'indication_of_changes': [],
        'abbreviations': [],
        'abbreviations_source_note': '',
        'literature_references': '',
        'training_advice': '',
        'additional_info_lines': []
    }
    
    # Extract the full Section 16 content first
    section_match = re.search(r'SECTION 16:[\s\S]*', text)
    if not section_match:
        return result
    
    section_text = section_match.group(0)
    
    # 16.1 Indication of changes - look for numbered list items or bullet points
    changes_match = re.search(r'16\.1\.?[^\d]*?Indication of changes[:\s]*([\s\S]*?)(?=16\.2|$)', text, re.IGNORECASE)
    if changes_match:
        changes_text = changes_match.group(1)
        # Extract individual changes - look for numbered items like "1.", "2." or bullet points
        changes = re.findall(r'(?:^|\n)\s*[*\-]?\s*(\d+\.\d+\.?)\s*([^\n]+)', changes_text)
        if changes:
            result['indication_of_changes'] = [{'section': c[0].strip(), 'description': c[1].strip()} for c in changes if c[1].strip()]
        else:
            # Alternative: look for any numbered items
            changes = re.findall(r'(?:^|\n)\s*[*\-]?\s*(\d+\.?|\*)\s*([^\n]+)', changes_text)
            result['indication_of_changes'] = [{'section': c[0].strip() if c[0].strip() != '*' else '', 'description': c[1].strip()} for c in changes if c[1].strip()]
    
    # 16.2 Abbreviations and acronyms - look for table format
    abbr_match = re.search(r'16\.2\.?[^\d]*?Abbreviat[^:]*[:\s]*([\s\S]*?)(?=16\.3|$)', text, re.IGNORECASE)
    if abbr_match:
        abbr_text = abbr_match.group(1)
        # Extract abbreviations from table format: abbreviation description
        abbrs = re.findall(r'^\s*([A-Z]{2,})\s+([^.\n]+)', abbr_text, re.MULTILINE)
        for abbr in abbrs:
            result['abbreviations'].append({
                'short': abbr[0].strip(),
                'long': abbr[1].strip()
            })
    
    # 16.3 Key literature references
    lit_match = re.search(r'16\.3\.?[^\d]*?Key literature[:\s]*([\s\S]*?)(?=16\.4|$)', text, re.IGNORECASE)
    if lit_match:
        result['literature_references'] = lit_match.group(1).strip()
    
    # 16.6 Training advice
    training_match = re.search(r'16\.6\.?[^\d]*?Training advice[:\s]*([\s\S]*?)(?=16\.7|$)', text, re.IGNORECASE)
    if training_match:
        result['training_advice'] = training_match.group(1).strip()
    
    # 16.7 Additional information
    additional_match = re.search(r'16\.7\.?[^\d]*?Additional information[:\s]*([\s\S]*)', text, re.IGNORECASE)
    if additional_match:
        result['additional_info_lines'] = [additional_match.group(1).strip()]
    
    return result


def parse_section_12(text):
    """Parst Abschnitt 12 - Ecological information"""
    result = {
        'persistence_and_degradability': {},
        'bioaccumulative_potential': {},
        'mobility_in_soil': {},
        'pbt_vpvb_assessment': {},
        'endocrine_disruptors': {},
        'other_adverse_effects': {}
    }
    
    # Extract the full Section 12 content
    section_match = re.search(r'SECTION 12:[\s\S]*?(?=SECTION|$)', text, re.IGNORECASE)
    if not section_match:
        return result
    
    section_text = section_match.group(0)
    
    # 12.2 Persistence and degradability - look for Biodegradation: lines
    # Better regex to match component name + CAS + Biodegradation
    persist_match = re.search(r'12\.2\.?[^\d]*?Persistence and degradability[:\s]*([\s\S]*?)(?=12\.3|$)', text, re.IGNORECASE)
    if persist_match:
        persist_text = persist_match.group(1)
        result['persistence_text'] = persist_text.strip()
        # Find all component blocks and their biodegradation data
        for match in re.finditer(r'(propan-1-ol|ethanol|dipropylene glycol monomethyl ether)\s+CAS No\.:\s*[^\n]+.*?Biodegradation:\s*([^\n]+)', persist_text, re.IGNORECASE | re.DOTALL):
            comp_name = match.group(1).strip()
            bio_data = match.group(2).strip()
            if comp_name and bio_data:
                result['persistence_and_degradability'][comp_name] = {'biodegradation': bio_data}
    
    # 12.3 Bioaccumulative potential - look for Log KOW: and BCF lines
    bio_match = re.search(r'12\.3\.?[^\d]*?Bioaccumulative potential[:\s]*([\s\S]*?)(?=12\.4|$)', text, re.IGNORECASE)
    if bio_match:
        bio_text = bio_match.group(1)
        result['bioaccumulation_text'] = bio_text.strip()
        # Check for Log KOW
        for match in re.finditer(r'(propan-1-ol|ethanol|dipropylene glycol monomethyl ether)\s+CAS No\.:\s*[^\n]+.*?Log K[OW]:\s*([^\n]+)', bio_text, re.IGNORECASE | re.DOTALL):
            comp_name = match.group(1).strip()
            log_kow = match.group(2).strip()
            if comp_name and log_kow:
                if comp_name not in result['bioaccumulative_potential']:
                    result['bioaccumulative_potential'][comp_name] = {}
                result['bioaccumulative_potential'][comp_name]['log_kow'] = log_kow
        # Check for BCF
        for match in re.finditer(r'(propan-1-ol|ethanol|dipropylene glycol monomethyl ether)\s+CAS No\.:\s*[^\n]+.*?Bioconcentration factor.*?:\s*([^\n]+)', bio_text, re.IGNORECASE | re.DOTALL):
            comp_name = match.group(1).strip()
            bcf = match.group(2).strip()
            if comp_name and bcf:
                if comp_name not in result['bioaccumulative_potential']:
                    result['bioaccumulative_potential'][comp_name] = {}
                result['bioaccumulative_potential'][comp_name]['bcf'] = bcf
    
    # 12.4 Mobility in soil
    mob_match = re.search(r'12\.4\.?[^\d]*?Mobility in soil[:\s]*([\s\S]*?)(?=12\.5|$)', text, re.IGNORECASE)
    if mob_match:
        result['mobility_in_soil']['general'] = {'data': 'No data available'}
    
    # 12.5 Results of PBT and vPvB assessment
    pbt_match = re.search(r'12\.5\.?[^\d]*?Results of PBT and vPvB assessment[:\s]*([\s\S]*?)(?=12\.6|$)', text, re.IGNORECASE)
    if pbt_match:
        pbt_text = pbt_match.group(1)
        result['pbt_text'] = pbt_text.strip()
        for comp in ['propan-1-ol', 'ethanol', 'dipropylene glycol monomethyl ether']:
            if comp.lower() in pbt_text.lower():
                result['pbt_vpvb_assessment'][comp] = {'assessment': 'This substance is not considered to be persistent, bioaccumulative and toxic (PBT).'}
    
    # 12.6 Endocrine disrupting properties
    endo_match = re.search(r'12\.6\.?[^\d]*?Endocrine disrupting properties[:\s]*([\s\S]*?)(?=12\.7|$)', text, re.IGNORECASE)
    if endo_match:
        result['endocrine_disruptors']['text'] = endo_match.group(1).strip()
    
    # 12.7 Other adverse effects
    other_match = re.search(r'12\.7\.?[^\d]*?Other adverse effects[:\s]*([\s\S]*)', text, re.IGNORECASE)
    if other_match:
        result['other_adverse_effects']['text'] = other_match.group(1).strip()
    
    return result

def main():
    if len(sys.argv) < 2:
        print("Verwendung: python pdf_section_extractor.py <pdf_datei>")
        return
    
    pdf_path = sys.argv[1]
    print(f"Lese PDF: {pdf_path}")
    
    sections = extract_sections_from_pdf(pdf_path)
    
    if sections:
        print("\n=== Abschnitt 15 ===")
        print(sections['section_15'][:500] if sections['section_15'] else "Nicht gefunden")
        
        print("\n=== Abschnitt 16 ===")
        print(sections['section_16'][:500] if sections['section_16'] else "Nicht gefunden")
        
        # Speichere als JSON
        import json
        
        parsed_1 = parse_section_1(sections.get('section_1', ''))
        parsed_2 = parse_section_2(sections.get('section_2', ''))
        parsed_15 = parse_section_15(sections['section_15'])
        parsed_16 = parse_section_16(sections['section_16'])
        
        output = {
            'section_1': parsed_1,
            'section_2': parsed_2,
            'section_15': parsed_15,
            'section_16': parsed_16
        }
        
        output_file = 'pdf_extracted_data.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\nDaten gespeichert in: {output_file}")
    else:
        print("Keine Daten gefunden")

if __name__ == '__main__':
    main()
