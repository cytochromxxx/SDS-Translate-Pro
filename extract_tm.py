#!/usr/bin/env python3
"""
SDS Translation Memory Extractor
"""

import os
import re
from collections import defaultdict
from typing import Dict, List, Tuple

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

class SDSTranslationMemoryExtractor:
    SECTION_HEADING_PATTERN = re.compile(
        r'(?im)^(?:SECTION|ABSCHNITT|SEZIONE|SECCIÓN|SEÇÃO|SECTIE|AVSNITT|AFSNIT|OSASTO|ODD[IÍ]L|ODJELJAK|ODDELEK|SEKCJA|SZAKASZ|SECȚIUNEA|РАЗДЕЛ|ΤΜΗΜΑ|NODAŁA|SKYRIUS)\s+(\d+)\b(?=\s*[:\n])'
    )

    def __init__(self, pdf_folder: str):
        self.pdf_folder = pdf_folder
        self.language_map = {
            'EN': 'en', 'GB': 'en', 'IE': 'en', 'MT': 'en', 'CH': 'en',
            'DE': 'de', 'AT': 'de', 'FR': 'fr', 'LU': 'fr', 'IT': 'it',
            'ES': 'es', 'NL': 'nl', 'BE': 'nl', 'PL': 'pl', 'SV': 'sv',
            'SE': 'sv', 'DA': 'da', 'DK': 'da', 'FI': 'fi', 'EL': 'el',
            'GR': 'el', 'CY': 'el', 'CS': 'cs', 'CZ': 'cs', 'HU': 'hu',
            'RO': 'ro', 'BG': 'bg', 'SK': 'sk', 'SL': 'sl', 'SI': 'sl',
            'ET': 'et', 'EE': 'et', 'LV': 'lv', 'LT': 'lt', 'HR': 'hr',
            'RS': 'sr', 'PT': 'pt', 'NO': 'no',
        }
        self.ignored_prefixes = re.compile(r'^(Page|Section|Chapter|SECTION|ABSCHNITT)', re.IGNORECASE)
        self.boilerplate_patterns = re.compile(
            r'^(?:Safety data sheet|Sicherheitsdatenblatt|Fiche de données de sécurité|Hoja de datos de seguridad|Scheda di sicurezza|REACH.*|according to Regulation \(EC\) No\. 1907/2006|gemäß Verordnung \(EG\) Nr\. 1907/2006|Seite \d+ / \d+|Page \d+ / \d+|Página \d+ / \d+|Version:|article number|Artikelnummer)$',
            re.IGNORECASE,
        )
        self.no_content_patterns = re.compile(
            r'^(?:none|n/a|not applicable|keine|ohne|aucun|nessuno|ninguna|ingen|nincs|nema|no|nenhuma|não)$',
            re.IGNORECASE,
        )

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        text = ""
        if pdfplumber is None:
            return text

        try:
            with pdfplumber.open(pdf_path) as doc:
                for page in doc.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception:
            return ""

        return text
    
    def extract_sections(self, text: str) -> Dict[int, str]:
        sections = {}
        section_markers = {}

        for match in self.SECTION_HEADING_PATTERN.finditer(text):
            section_num = int(match.group(1))
            if section_num in section_markers:
                continue
            start = match.end()
            next_line = text.find('\n', start)
            if next_line != -1:
                start = next_line + 1
            section_markers[section_num] = start

        for section_num in [4, 5, 6, 7, 8, 10, 11]:
            if section_num in section_markers:
                start = section_markers[section_num]
                next_section = None
                for s in sorted(section_markers.keys()):
                    if s > section_num:
                        next_section = section_markers[s]
                        break
                end = next_section if next_section else len(text)
                sections[section_num] = self._clean_section_text(text[start:end])

        return sections
    
    def _clean_section_text(self, section_text: str) -> str:
        lines = []
        for raw_line in section_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if self.SECTION_HEADING_PATTERN.match(line):
                continue
            if re.match(r'^\d+(?:\.\d+)+\s+[A-ZÀ-ÖØ-Ý]', line):
                continue
            if self.boilerplate_patterns.search(line):
                continue
            line = self._strip_line_prefix(line)
            if self._is_no_content_line(line):
                continue
            if self._is_table_like(line):
                continue

            if lines and self._should_merge_line(lines[-1], line):
                previous = lines[-1].rstrip()
                if previous.endswith(('-', '–', '—')):
                    lines[-1] = previous[:-1].rstrip() + line.lstrip()
                else:
                    lines[-1] = f"{previous} {line}"
            else:
                lines.append(line)

        filtered = [line for line in lines if self._is_useful_line(line)]
        return ' '.join(filtered)

    def _is_heading_like(self, line: str) -> bool:
        if re.match(
            r'^(?:Following|Suitable|Advice on|Other information relating to|Personal protective equipment|Occupational exposure limit values|Hazardous combustion products|Reference to other sections|Advice on how|Suitable extinguishing media|Environmental precautions|Methods and material|Exposure controls|Specific target organ toxicity|If substance has entered|Keep away from drains|Use personal protective equipment|Do not allow firefighting water|Fight fire with|Keep container tightly closed|Store in a dry place|Avoid exposure|Avoid: Aerosol or mist formation|Provide fresh air|Rinse skin with water|In case of contact with eyes|Rinse mouth with water|In case of accident or unwellness|Clean up a spill|Take up mechanically|Ventilate affected area|Symptoms related to|There is no additional information)\b',
            line,
            re.IGNORECASE,
        ):
            return True
        if len(line.split()) <= 6 and re.match(r'^[A-ZÄÖÜ][a-zäöüß]+(?: [A-ZÄÖÜ][a-zäöüß]+)*$', line):
            return True
        return False

    def _should_merge_line(self, previous: str, current: str) -> bool:
        previous = previous.rstrip()
        if previous.endswith(('-', '–', '—')):
            return True
        if self._is_heading_like(previous):
            return False
        if self._is_heading_like(current):
            return False
        if previous.endswith(('.', '!', '?', ':')):
            return False
        if re.match(r'^[a-zäöüß]', current):
            return True
        if len(current.split()) <= 3:
            return True
        if previous.split() and previous.split()[-1].lower() in (
            'to', 'and', 'or', 'for', 'with', 'from', 'in', 'on', 'at', 'of', 'by', 'using', 'when', 'if', 'that', 'which', 'but', 'so'
        ):
            return True
        return False

    def _strip_line_prefix(self, line: str) -> str:
        marker = re.search(
            r'^(?:article number|Artikelnummer|Version:|Version|SDS|Sicherheitsdatenblatt|Safety data sheet|Fiche de données de sécurité|Hoja de datos de seguridad|Scheda di sicurezza|REACH|Switzerland|Page)\b',
            line,
            re.IGNORECASE,
        )
        if marker:
            cleaned = line[marker.end():].strip()
            if cleaned:
                return cleaned
        return line

    def _is_no_content_line(self, line: str) -> bool:
        return bool(self.no_content_patterns.match(line.strip()))

    def _is_table_like(self, line: str) -> bool:
        if re.search(
            r'\b(CAS No|CAS-Nr|EC No|EG-Nummer|PNEC|DNEL|MAK|PEL|TLV|NPK-P|VLA|STEL|TWA|ATEX|ECHA|GHS|H\d{3}|P\d{3}|Occupational exposure limit values|Workplace Exposure Limits|Endpoint Threshold|Protection goal|Exposure time|Relevant DNELs|Relevant PNECs|Hazard category|Target organ|Exposure route|Threshold Organism|Hazard category|Hazard statements?)\b',
            line,
            re.IGNORECASE,
        ):
            return True

        if len(re.findall(r'\d', line)) > 7:
            return True

        uppercase_tokens = sum(1 for token in line.split() if token.isupper() and len(token) > 1)
        if uppercase_tokens >= 3:
            return True

        if line.count(':') >= 2:
            return True

        return False

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
        
        result = []
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            if len(sent) < 15:
                continue
            if len(re.findall(r'[A-Za-zÀ-ÖØ-öø-ÿ]', sent)) < 5:
                continue
            if self.ignored_prefixes.match(sent):
                continue
            if self.boilerplate_patterns.search(sent):
                continue
            if self._is_table_like(sent):
                continue
            if re.match(r'^[HP]\d{3}', sent):
                continue
            result.append(sent)
        
        return result
    
    def find_parallel_pdfs(self) -> Dict[str, List[Tuple[str, str]]]:
        pairs = defaultdict(list)
        files = os.listdir(self.pdf_folder)
        pdf_files = [f for f in files if f.lower().endswith('.pdf')]
        
        by_product = defaultdict(list)
        for pdf in pdf_files:
            match = re.match(r'SDB-(\w+)-(\w+)-(\w+)\.pdf', pdf, re.IGNORECASE)
            if match:
                product_id, country, lang_code = match.groups()
                lang = self.language_map.get(lang_code.upper(), lang_code.lower())
                by_product[product_id].append((pdf, lang, country))
        
        for product_id, variants in by_product.items():
            english_files = [f for f, l, c in variants if l == 'en']
            for target_file, target_lang, target_country in variants:
                if target_lang != 'en' and english_files:
                    for en_file in english_files:
                        pairs[target_lang].append((en_file, target_file))
        
        return pairs
    
    def extract_translation_memory(self, output_file: str = "translation_memory.md"):
        pairs = self.find_parallel_pdfs()
        all_alignments = defaultdict(list)
        total_extracted = 0
        
        for target_lang, pdf_pairs in pairs.items():
            print(f"\nProcessing {target_lang.upper()} ({len(pdf_pairs)} pairs)...")
            
            for en_pdf, target_pdf in pdf_pairs:
                en_path = os.path.join(self.pdf_folder, en_pdf)
                target_path = os.path.join(self.pdf_folder, target_pdf)
                print(f"  {en_pdf} <-> {target_pdf}")
                
                en_text = self.extract_text_from_pdf(en_path)
                target_text = self.extract_text_from_pdf(target_path)
                
                if not en_text or not target_text:
                    print("    skip: missing text")
                    continue
                
                en_sections = self.extract_sections(en_text)
                target_sections = self.extract_sections(target_text)
                
                for section_num in [4, 5, 6, 7, 8, 10, 11]:
                    if section_num not in en_sections or section_num not in target_sections:
                        continue

                    en_sents = self.extract_sentences(en_sections[section_num])
                    target_sents = self.extract_sentences(target_sections[section_num])

                    if not en_sents or not target_sents:
                        continue

                    if len(en_sents) != len(target_sents):
                        mismatch_ratio = abs(len(en_sents) - len(target_sents)) / max(len(en_sents), len(target_sents))
                        if mismatch_ratio > 0.30:
                            print(f"    section {section_num}: sentence count mismatch {len(en_sents)} != {len(target_sents)}, skip because ratio {mismatch_ratio:.2f} > 0.30")
                            continue
                        align_count = min(len(en_sents), len(target_sents))
                        print(f"    section {section_num}: sentence count mismatch {len(en_sents)} != {len(target_sents)}, aligning first {align_count}")
                    else:
                        align_count = len(en_sents)

                    for en_sent, target_sent in zip(en_sents[:align_count], target_sents[:align_count]):
                        all_alignments[target_lang].append({
                            'section': section_num,
                            'english': en_sent,
                            'target': target_sent,
                        })
                        total_extracted += 1

        self._write_markdown_table(all_alignments, output_file)
        print(f"\nOK Translation Memory saved: {output_file}")
        print(f"OK Total entries: {total_extracted}")
    
    def _write_markdown_table(self, alignments: Dict[str, List[Dict]], output_file: str):
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# SDS Translation Memory\n\n")
            f.write("Extracted from parallel Safety Data Sheets (Sections 4-11)\n\n")
            f.write("| Section | English Original | Target Language [code] |\n")
            f.write("|---------|------------------|------------------------|\n")
            
            for target_lang in sorted(alignments.keys()):
                entries = alignments[target_lang]
                if not entries:
                    continue
                f.write(f"\n## Language: {target_lang}\n\n")
                f.write(f"**Total entries: {len(entries)}**\n\n")
                f.write("| Section | English Original | Target Language [" + target_lang + "] |\n")
                f.write("|---------|------------------|-----------------------------|\n")
                for entry in entries:
                    section = entry['section']
                    en_sent = entry['english'].replace('|', '\\|')
                    target_sent = entry['target'].replace('|', '\\|')
                    f.write(f"| {section} | {en_sent} | {target_sent} |\n")

if __name__ == '__main__':
    pdf_folder = r"c:\Users\Flo\Downloads\SDS-Translate-Pro-master\SDS\downloads"
    extractor = SDSTranslationMemoryExtractor(pdf_folder)
    extractor.extract_translation_memory("translation_memory.md")
