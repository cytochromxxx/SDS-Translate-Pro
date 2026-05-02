#!/usr/bin/env python3
"""Extract sentence-aligned translation memory from glossary_json JSON files."""

import argparse
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


def strip_html(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r'<[^>]+>', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def item_text(item: dict) -> str:
    if item.get('type') == 'text':
        return str(item.get('text', '') or '')
    if item.get('type') == 'list':
        return ' '.join(str(x) for x in item.get('list_items', []) if x)
    if item.get('type') == 'table':
        parts = []
        if item.get('table_body'):
            parts.append(strip_html(item['table_body']))
        if item.get('table_caption'):
            parts.append(' '.join(item.get('table_caption', [])))
        if item.get('table_footnote'):
            parts.append(' '.join(item.get('table_footnote', [])))
        return ' '.join(parts)
    return ''


class JSONTranslationMemoryExtractor:
    def __init__(self, json_folder: str):
        self.json_folder = json_folder

    def find_parallel_files(self) -> Dict[str, List[Tuple[str, str, str]]]:
        pairs = defaultdict(list)
        for filename in os.listdir(self.json_folder):
            if not filename.lower().endswith('.json'):
                continue
            match = re.match(r'SDB-(.+?)-([A-Z]{2})-([A-Z]{2})\.json$', filename, re.IGNORECASE)
            if not match:
                continue
            product_id, country, lang_code = match.groups()
            lang = LANGUAGE_MAP.get(lang_code.upper(), lang_code.lower())
            pairs[product_id].append((filename, lang, country.upper()))
        return pairs

    def load_json_data(self, path: str) -> List[dict]:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def extract_sections(self, items: List[dict]) -> Dict[int, str]:
        sections = {}
        current_section = None
        current_lines: List[str] = []

        ordered_items = sorted(
            enumerate(items),
            key=lambda x: (x[1].get('page_idx', 0), x[0])
        )
        for _, item in ordered_items:
            text = item_text(item).strip()
            if not text:
                continue
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                heading = SECTION_HEADING_PATTERN.match(line)
                if heading:
                    if current_section is not None and current_section in {4, 5, 6, 7, 8, 10, 11}:
                        sections[current_section] = self._clean_section_text(current_lines)
                    current_section = int(heading.group(1))
                    current_lines = []
                    continue
                if current_section is not None:
                    current_lines.append(line)

        if current_section is not None and current_section in {4, 5, 6, 7, 8, 10, 11}:
            sections[current_section] = self._clean_section_text(current_lines)

        return sections

    def _clean_section_text(self, lines: List[str]) -> str:
        cleaned = []
        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue
            if IGNORE_PATTERNS.search(line):
                continue
            line = re.sub(r'\s+', ' ', line).strip('-–— ')
            if self._is_no_content_line(line):
                continue
            if self._is_table_like(line):
                continue

            if cleaned and self._should_merge_line(cleaned[-1], line):
                previous = cleaned[-1].rstrip()
                if previous.endswith(('-', '–', '—')):
                    cleaned[-1] = previous[:-1].rstrip() + ' ' + line.lstrip()
                else:
                    cleaned[-1] = previous + ' ' + line
            else:
                cleaned.append(line)

        useful = [line for line in cleaned if self._is_useful_line(line)]
        return ' '.join(useful)

    def _is_no_content_line(self, line: str) -> bool:
        return bool(NO_CONTENT_PATTERNS.match(line.strip()))

    def _is_table_like(self, line: str) -> bool:
        if TABLE_LIKE_PATTERNS.search(line):
            return True
        if len(re.findall(r'\d', line)) > 7:
            return True
        if line.count(':') >= 2:
            return True
        uppercase_tokens = sum(1 for token in line.split() if token.isupper() and len(token) > 1)
        return uppercase_tokens >= 3

    def _is_heading_like(self, line: str) -> bool:
        if re.match(r'^[A-ZÄÖÜ][a-zäöüß]+(?: [A-ZÄÖÜ][a-zäöüß]+)*$', line):
            return True
        if len(line.split()) <= 6 and line.endswith(':'):
            return True
        return False

    def _should_merge_line(self, previous: str, current: str) -> bool:
        previous = previous.rstrip()
        if previous.endswith(('-', '–', '—')):
            return True
        if previous.endswith(('.', '!', '?', ':')):
            return False
        if self._is_heading_like(previous) or self._is_heading_like(current):
            return False
        if re.match(r'^[a-zäöüß]', current):
            return True
        if len(current.split()) <= 3:
            return True
        last_word = previous.split()[-1].lower() if previous.split() else ''
        return last_word in MERGE_PREPOSITION

    def _is_useful_line(self, line: str) -> bool:
        if self._is_no_content_line(line):
            return False
        if len(line.split()) < 5:
            return False
        if re.match(r'^[\d\s\W]+$', line):
            return False
        if re.search(r'\b(Version|article number|Artikelnummer|REACH|Seite|Page|n/a|not applicable|ohne|aucun|nessuno|ninguna|ingen|nincs|nema|nenhuma|não)\b', line, re.IGNORECASE):
            return False
        if re.search(r'[®™]', line):
            return False
        return True

    def extract_sentences(self, text: str) -> List[str]:
        text = re.sub(r'\s+', ' ', text)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        result: List[str] = []
        for sent in sentences:
            sent = sent.strip()
            if len(sent) < 15:
                continue
            if len(re.findall(r'[A-Za-zÀ-ÖØ-öø-ÿ]', sent)) < 5:
                continue
            if self._is_table_like(sent):
                continue
            result.append(sent)
        return result

    def extract_translation_memory(self, output_file: str):
        pairs = self.find_parallel_files()
        all_alignments = defaultdict(list)
        total_extracted = 0

        for product_id, files in pairs.items():
            english_files = [fn for fn, lang, country in files if lang == 'en']
            if not english_files:
                continue

            for target_filename, target_lang, _ in files:
                if target_lang == 'en':
                    continue
                for en_filename in english_files:
                    en_path = os.path.join(self.json_folder, en_filename)
                    target_path = os.path.join(self.json_folder, target_filename)
                    en_sections = self.extract_sections(self.load_json_data(en_path))
                    target_sections = self.extract_sections(self.load_json_data(target_path))

                    for section_num in [4, 5, 6, 7, 8, 10, 11]:
                        if section_num not in en_sections or section_num not in target_sections:
                            continue
                        en_sentences = self.extract_sentences(en_sections[section_num])
                        target_sentences = self.extract_sentences(target_sections[section_num])
                        if not en_sentences or not target_sentences:
                            continue
                        if len(en_sentences) != len(target_sentences):
                            mismatch_ratio = abs(len(en_sentences) - len(target_sentences)) / max(len(en_sentences), len(target_sentences))
                            if mismatch_ratio > 0.30:
                                continue
                            align_count = min(len(en_sentences), len(target_sentences))
                        else:
                            align_count = len(en_sentences)

                        for en_sent, target_sent in zip(en_sentences[:align_count], target_sentences[:align_count]):
                            all_alignments[target_lang].append({
                                'section': section_num,
                                'english': en_sent,
                                'target': target_sent,
                            })
                            total_extracted += 1

        self._write_markdown_table(all_alignments, output_file)
        print(f"OK Translation Memory saved: {output_file}")
        print(f"OK Total entries: {total_extracted}")

    def _write_markdown_table(self, alignments: Dict[str, List[Dict]], output_file: str):
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('# SDS Translation Memory from JSON files\n\n')
            f.write('Extracted from glossary_json JSON SDS files (Sections 4-11)\n\n')
            for target_lang in sorted(alignments.keys()):
                entries = alignments[target_lang]
                if not entries:
                    continue
                f.write(f'## Language: {target_lang}\n\n')
                f.write(f'**Total entries: {len(entries)}**\n\n')
                f.write('| Section | English Original | Target Language [' + target_lang + '] |\n')
                f.write('|---------|------------------|-----------------------------|\n')
                for entry in entries:
                    section = entry['section']
                    en_sent = entry['english'].replace('|', '\\|')
                    target_sent = entry['target'].replace('|', '\\|')
                    f.write(f'| {section} | {en_sent} | {target_sent} |\n')


def main():
    parser = argparse.ArgumentParser(description='Extract TM from glossary_json JSON files.')
    parser.add_argument('--input-folder', default='glossary_json', help='Folder containing .json files')
    parser.add_argument('--output-file', default='translation_memory_json.md', help='Output Markdown TM file')
    args = parser.parse_args()

    extractor = JSONTranslationMemoryExtractor(args.input_folder)
    extractor.extract_translation_memory(args.output_file)


if __name__ == '__main__':
    main()
