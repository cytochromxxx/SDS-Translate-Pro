#!/usr/bin/env python3
"""Extract SDS phrases into a sorted CSV, one line per language phrase."""

import argparse
import csv
import html
import json
import os
import re
from collections import defaultdict
from typing import Dict, List, Tuple

LANGUAGE_MAP = {
    'EN': 'en', 'GB': 'en', 'IE': 'en', 'MT': 'en', 'CH': 'en',
    'DE': 'de', 'AT': 'de', 'FR': 'fr', 'LU': 'fr', 'IT': 'it',
    'ES': 'es', 'NL': 'nl', 'BE': 'nl', 'PL': 'pl', 'SV': 'sv',
    'SE': 'sv', 'DA': 'da', 'DK': 'da', 'FI': 'fi', 'EL': 'el',
    'GR': 'el', 'CY': 'el', 'CS': 'cs', 'CZ': 'cs', 'HU': 'hu',
    'RO': 'ro', 'BG': 'bg', 'SK': 'sk', 'SL': 'sl', 'SI': 'sl',
    'ET': 'et', 'EE': 'et', 'LV': 'lv', 'LT': 'lt', 'HR': 'hr',
    'RS': 'sr', 'PT': 'pt', 'NO': 'no',
}

SECTION_HEADING_PATTERN = re.compile(
    r'^(?:SECTION|ABSCHNITT|SEZIONE|SECCIÓN|SEÇÃO|SECTIE|AVSNITT|AFSNIT|OSASTO|ODD[IÍ]L|ODJELJAK|ODDELEK|SEKCJA|SZAKASZ|SECȚIUNEA|РАЗДЕЛ|ΤΜΗΜΑ|NODAŁA|SKYRIUS)\s+(\d+)\b',
    re.IGNORECASE,
)

IGNORE_PATTERNS = re.compile(
    r'^(?:Safety data sheet|Sicherheitsdatenblatt|Fiche de données de sécurité|Hoja de datos de seguridad|Scheda di sicurezza|REACH.*|according to Regulation \(EC\) No\. 1907/2006|gemäß Verordnung \(EG\) Nr\. 1907/2006|Seite \d+ / \d+|Page \d+ / \d+|Página \d+ / \d+|Version:|article number|Artikelnummer|Telefon:|Telephone:|Telefax:|e-mail:|Website:|Webseite:|Page \d+|Seite \d+|Switzerland|Schweiz|Deutschland|France|España|Italy|Italia)$',
    re.IGNORECASE,
)

NO_CONTENT_PATTERNS = re.compile(
    r'^(?:none|n/a|not applicable|keine|ohne|aucun|nessuno|ninguna|ingen|nincs|nema|no|nenhuma|não)$',
    re.IGNORECASE,
)

TABLE_LIKE_PATTERNS = re.compile(
    r'\b(CAS No|CAS-Nr|EC No|EG-Nummer|PNEC|DNEL|MAK|PEL|TLV|NPK-P|VLA|STEL|TWA|ATEX|ECHA|GHS|H\d{3}|P\d{3}|Occupational exposure limit values|Workplace Exposure Limits|Endpoint Threshold|Protection goal|Exposure time|Relevant DNELs|Relevant PNECs|Hazard category|Target organ|Exposure route|Threshold|Hazard statements?)\b',
    re.IGNORECASE,
)

MERGE_PREPOSITION = {
    'to', 'and', 'or', 'for', 'with', 'from', 'in', 'on', 'at', 'of', 'by',
    'using', 'when', 'if', 'that', 'which', 'but', 'so', 'as', 'after', 'before',
}

SECTIONS_TO_EXTRACT = [4, 5, 6, 7, 8, 10, 11]


def normalize_language(code: str) -> str:
    return LANGUAGE_MAP.get(code.upper(), code.lower())


def strip_html(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r'<[^>]+>', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def item_text(item: dict) -> str:
    item_type = item.get('type', '')
    if item_type == 'text':
        return str(item.get('text', '') or '')
    if item_type == 'list':
        return ' '.join(str(x) for x in item.get('list_items', []) if x)
    if item_type == 'table':
        parts = []
        if item.get('table_body'):
            parts.append(strip_html(item['table_body']))
        if item.get('table_caption'):
            parts.append(' '.join(item.get('table_caption', [])))
        if item.get('table_footnote'):
            parts.append(' '.join(item.get('table_footnote', [])))
        return ' '.join(parts)
    return ''


def parse_filename(filename: str) -> Tuple[str, str, str]:
    match = re.match(r'SDB-(.+?)-([A-Z]{2})-([A-Z]{2})\.(?:json|md)$', filename, re.IGNORECASE)
    if match:
        product_id, country, lang_code = match.groups()
        return product_id, country.upper(), normalize_language(lang_code)
    return '', '', ''


def load_markdown(path: str) -> str:
    with open(path, 'r', encoding='utf-8') as f:
        raw = f.read()
    return strip_html(raw)


def extract_sections_from_text(text: str) -> Dict[int, str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    section_positions = {}
    for idx, line in enumerate(lines):
        match = SECTION_HEADING_PATTERN.match(line)
        if match:
            section_positions[int(match.group(1))] = idx

    sections: Dict[int, str] = {}
    keys = sorted(section_positions)
    for i, section_num in enumerate(keys):
        if section_num not in SECTIONS_TO_EXTRACT:
            continue
        start = section_positions[section_num] + 1
        end = section_positions[keys[i + 1]] if i + 1 < len(keys) else len(lines)
        content = ' '.join(lines[start:end])
        sections[section_num] = clean_text(content)
    return sections


def extract_sections_from_json(items: List[dict]) -> Dict[int, str]:
    sections: Dict[int, str] = {}
    current_section = None
    current_lines: List[str] = []

    items_sorted = sorted(
        enumerate(items),
        key=lambda x: (x[1].get('page_idx', 0), x[0])
    )

    for _, item in items_sorted:
        text = item_text(item).strip()
        if not text:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            heading = SECTION_HEADING_PATTERN.match(line)
            if heading:
                if current_section is not None and current_section in SECTIONS_TO_EXTRACT:
                    sections[current_section] = clean_text(' '.join(current_lines))
                current_section = int(heading.group(1))
                current_lines = []
                continue
            if current_section is not None:
                current_lines.append(line)

    if current_section is not None and current_section in SECTIONS_TO_EXTRACT:
        sections[current_section] = clean_text(' '.join(current_lines))

    return sections


def clean_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    text = re.sub(r'\b(article number|Artikelnummer|Version:|Version|SDS|Sicherheitsdatenblatt|Safety data sheet|Fiche de données de sécurité|Hoja de datos de seguridad|Scheda di sicurezza|REACH|Switzerland|Page|Seite)\b', '', text, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', text).strip()


def extract_sentences(text: str) -> List[str]:
    text = re.sub(r'\s+', ' ', text)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    result: List[str] = []
    for sent in sentences:
        sent = sent.strip()
        if len(sent) < 15:
            continue
        if len(re.findall(r'[A-Za-zÀ-ÖØ-öø-ÿ]', sent)) < 5:
            continue
        if NO_CONTENT_PATTERNS.match(sent):
            continue
        if TABLE_LIKE_PATTERNS.search(sent):
            continue
        if re.search(r'^(?:H\d{3}|P\d{3}|EUH\d{3})', sent, re.IGNORECASE):
            continue
        result.append(sent)
    return result


def gather_phrases(input_folder: str, source_format: str) -> List[Tuple[str, str, str, int, str]]:
    phrases = []
    files = [f for f in os.listdir(input_folder) if f.lower().endswith('.' + source_format)]
    for filename in sorted(files):
        product_id, country, lang = parse_filename(filename)
        if not product_id or not lang:
            continue
        path = os.path.join(input_folder, filename)
        if source_format == 'md':
            sections = extract_sections_from_text(load_markdown(path))
        else:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            sections = extract_sections_from_json(data)

        for section_num, section_text in sections.items():
            for sentence in extract_sentences(section_text):
                phrases.append((lang, product_id, country, section_num, sentence))
    return phrases


def write_csv(output_file: str, rows: List[Tuple[str, str, str, int, str]]):
    header = ['language', 'product_id', 'country', 'section', 'phrase']
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(header)
        for row in rows:
            writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(description='Extract SDS phrases from glossary_json files to CSV.')
    parser.add_argument('--input-folder', default='glossary_json', help='Folder containing source files')
    parser.add_argument('--source-format', default='json', choices=['json', 'md'], help='Source file format')
    parser.add_argument('--output-file', default='sds_phrases.csv', help='Output CSV file')
    args = parser.parse_args()

    phrases = gather_phrases(args.input_folder, args.source_format)
    phrases.sort(key=lambda item: (item[0], item[1], item[3], item[4]))
    write_csv(args.output_file, phrases)
    print(f'OK phrases extracted: {len(phrases)} rows to {args.output_file}')


if __name__ == '__main__':
    main()
