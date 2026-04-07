#!/usr/bin/env python3
"""
PDF Gap Filler for SDS (Safety Data Sheet) parsing.

Extracts data from PDF that is missing or empty in the XML source.
Uses pdfplumber for structured table extraction and regex for text patterns.
XML data always takes precedence - this module only fills empty/None/[] fields.
"""

import re
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _is_empty(value: Any) -> bool:
    """Return True if a value is considered empty/missing."""
    if value is None:
        return True
    if isinstance(value, str):
        v = value.strip().lower()
        if not v or v in ['none', 'none known.', 'none known', 'no data available', 'no data available.', 'keine daten verfügbar', 'keine daten verfügbar.', 'keine bekannt.', 'keine bekannt']:
            return True
        return False
    if isinstance(value, (list, dict)) and not value:
        return True
    return False


class SDSPDFGapFiller:
    """
    Extracts missing SDS data from a PDF file to fill gaps left by XML parsing.

    Only fills fields that are empty/None/[] in the already-parsed XML data.
    """

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self._pdf = None
        self._pages_text: Dict[int, str] = {}  # 0-indexed page -> text cache
        self._open_pdf()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _open_pdf(self):
        try:
            import pdfplumber
            self._pdf = pdfplumber.open(self.pdf_path)
            logger.info(f"Opened PDF: {self.pdf_path} ({len(self._pdf.pages)} pages)")
        except ImportError:
            logger.error("pdfplumber is not installed. Run: pip install pdfplumber")
            self._pdf = None
        except Exception as e:
            logger.error(f"Failed to open PDF {self.pdf_path}: {e}")
            self._pdf = None

    def _page_text(self, page_idx: int) -> str:
        """Return cached text for a 0-indexed page."""
        if self._pdf is None:
            return ""
        if page_idx not in self._pages_text:
            try:
                self._pages_text[page_idx] = self._pdf.pages[page_idx].extract_text() or ""
            except Exception as e:
                logger.warning(f"Could not extract text from page {page_idx + 1}: {e}")
                self._pages_text[page_idx] = ""
        return self._pages_text[page_idx]

    def _page_tables(self, page_idx: int) -> List[List[List[Optional[str]]]]:
        """Return all tables on a 0-indexed page."""
        if self._pdf is None:
            return []
        try:
            return self._pdf.pages[page_idx].extract_tables() or []
        except Exception as e:
            logger.warning(f"Could not extract tables from page {page_idx + 1}: {e}")
            return []

    def _full_text(self) -> str:
        """Return concatenated text of all pages."""
        if self._pdf is None:
            return ""
        parts = []
        for i in range(len(self._pdf.pages)):
            parts.append(self._page_text(i))
        return "\n".join(parts)

    def close(self):
        if self._pdf is not None:
            try:
                self._pdf.close()
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _get_section_2_text(self) -> str:
        """Extracts the full text of Section 2 from the PDF."""
        # Section 2 is usually on pages 1-3.
        full_text = "\n".join(self._page_text(i) for i in range(3))
        match = re.search(r'(SECTION 2: Hazards identification.*?)(?=SECTION 3:)', full_text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1)
        return ""
        
    def extract_hazard_components(self) -> str:
        """Extracts the hazard components for labelling from Section 2."""
        try:
            text = self._get_section_2_text()
            m = re.search(r'Hazard components for labelling:?\s*\n\s*([^\n]+)', text, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        except Exception as e:
            logger.warning(f"Could not extract hazard components: {e}")
        return ""

    def _extract_codes_from_stmt(self, stmt: Dict[str, str]) -> List[str]:
        """Extracts individual P-codes from a statement code string like 'P303+P361+P353'."""
        if not stmt or "code" not in stmt:
            return []
        code_str = stmt.get("code", "")
        # Split by + and clean up each code
        return [c.strip() for c in code_str.split("+") if c.strip()]

    def _extract_precautionary_statements(self, section_text: str) -> Dict[str, List[Dict[str, str]]]:
        """Extracts Prevention and Response precautionary statements from Section 2 text."""
        statements = {"prevention": [], "response": []}
        
        # This regex looks for one or more P-codes (e.g., P264, P305 + P351 + P338)
        # followed by text. The text is captured non-greedily until the next P-code
        # or the end of the string is detected.
        pattern = re.compile(
            r'((?:P\d{3}\s*\+\s*)*P\d{3})\s+(.+?)(?=\s*P\d{3}\s*\+|(?<!\+)\s*$)',
            re.DOTALL
        )

        def parse_block(text_block, category):
            # Clean up text by replacing newlines not followed by a P-code with a space.
            # This joins multi-line statement texts into a single line.
            clean_text = re.sub(r'\s*\n(?!\s*P\d)', ' ', text_block)
            for match in pattern.finditer(clean_text):
                # Combine codes like "P305+P351+P338"
                code = re.sub(r'\s*', '', match.group(1))
                text = ' '.join(match.group(2).strip().split())
                statements[category].append({"code": code, "text": text})

        # Process "Prevention" statements block
        prevention_match = re.search(
            r'Precautionary statements Prevention\s*\n(.*?)(?=\n\s*Precautionary statements Response|\n\s*2\.3\.\s*Other hazards|\Z)',
            section_text, re.DOTALL | re.IGNORECASE
        )
        if prevention_match:
            parse_block(prevention_match.group(1), "prevention")

        # Process "Response" statements block
        response_match = re.search(
            r'Precautionary statements Response\s*\n(.*?)(?=\n\s*Precautionary statements Storage|\n\s*2\.3\.\s*Other hazards|\Z)',
            section_text, re.DOTALL | re.IGNORECASE
        )
        if response_match:
            parse_block(response_match.group(1), "response")
                
        return statements

    def extract_section_3_ate_values(self) -> Dict[str, List[str]]:
        """
        Extract Acute Toxicity Estimate (ATE) values from the Section 3.2 table.

        Returns a dict mapping component name to a list of ATE strings.
        e.g., {'Propan-1-ol': ['ATE (oral): > 2000 mg/kg']}
        """
        results = {}
        try:
            # Section 3 is likely on page 2 or 3 (0-indexed 1 or 2)
            for page_idx in [1, 2]: 
                tables = self._page_tables(page_idx)
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    # Find the table with hazardous ingredients
                    header_str = " ".join(str(c) for c in table[0] if c).lower()
                    if "product identifiers" not in header_str and "substance name" not in header_str:
                        continue
                    
                    logger.debug(f"Found Section 3 table on page {page_idx + 1}")
                    
                    current_component_name = ""
                    for row in table:
                        row_text = "\n".join(str(c) for c in row if c)

                        # A bit fragile: Assume the main component name is in the second cell
                        # and doesn't contain CAS/EC, which signals a new component.
                        if len(row) > 1 and row[1] and "CAS No" not in row_text and "EC No" not in row_text:
                             name_match = re.match(r'^\s*([a-zA-Z0-9\s-]+)', str(row[1]))
                             if name_match:
                                 component_name_candidate = name_match.group(1).strip()
                                 # Avoid picking up classification lines as names
                                 if 'flam.' not in component_name_candidate.lower() and 'eye' not in component_name_candidate.lower():
                                    current_component_name = component_name_candidate
                        
                        # Look for ATE values in the row text
                        if "Acute Toxicity Estimate" in row_text:
                            ate_lines = row_text.splitlines()
                            # Find lines that look like ATE values
                            for line in ate_lines:
                                if line.strip().lower().startswith('ate'):
                                    if current_component_name:
                                        if current_component_name not in results:
                                            results[current_component_name] = []
                                        results[current_component_name].append(line.strip())

        except Exception as e:
            logger.error(f"Error extracting Section 3 ATE values: {e}", exc_info=True)
        
        logger.info(f"Extracted ATE values for {len(results)} components from PDF")
        return results

    # ------------------------------------------------------------------
    # Section 8: Occupational Exposure Limits
    # ------------------------------------------------------------------

    def extract_section_8_oel(self) -> List[Dict[str, str]]:
        """
        Extract the OEL table from Section 8.1.1 (page 4, 0-indexed page 3).

        Returns a list of dicts:
          [{'limit_type': ..., 'substance': ..., 'cas': ..., 'ec': ...,
            'long_term': ..., 'short_term': ..., 'remarks': ...}]
        """
        results = []
        try:
            # The OEL table is on page 4 (0-indexed: 3)
            for page_idx in [3, 4]:
                tables = self._page_tables(page_idx)
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    header = table[0]
                    if header is None:
                        continue
                    header_str = " ".join(str(c) for c in header if c).lower()
                    # Identify the OEL table by its header keywords
                    if "limit value" not in header_str and "substance name" not in header_str:
                        continue
                    logger.debug(f"Found OEL table on page {page_idx + 1}")
                    for row in table[1:]:
                        if not row or all(c is None or str(c).strip() == "" for c in row):
                            continue
                        cells = [str(c).strip() if c else "" for c in row]
                        if len(cells) < 3:
                            continue
                        limit_type_raw = cells[0]
                        substance_raw = cells[1]
                        values_raw = cells[2] if len(cells) > 2 else ""

                        # Parse substance cell: name\nCAS No.:...\nEC No.:...
                        substance_name = ""
                        cas_no = ""
                        ec_no = ""
                        for line in substance_raw.splitlines():
                            line = line.strip()
                            if line.startswith("CAS No.:"):
                                cas_no = line.replace("CAS No.:", "").strip()
                            elif line.startswith("EC No.:"):
                                ec_no = line.replace("EC No.:", "").strip()
                            elif line:
                                substance_name = line

                        # Parse values cell: ① long-term\n② short-term\n⑤ remark
                        long_term = ""
                        short_term = ""
                        remarks = []
                        for line in values_raw.splitlines():
                            line = line.strip()
                            if line.startswith("①"):
                                long_term = line[1:].strip()
                            elif line.startswith("②"):
                                short_term = line[1:].strip()
                            elif line.startswith("⑤"):
                                remarks.append(line[1:].strip())

                        # Parse limit type cell: "TRGS 900 (DE)\nfrom 29 Mar 2019"
                        limit_type_lines = [l.strip() for l in limit_type_raw.splitlines() if l.strip()]
                        limit_type = limit_type_lines[0] if limit_type_lines else limit_type_raw.strip()

                        if substance_name or long_term:
                            results.append({
                                "limit_type": limit_type,
                                "substance": substance_name,
                                "cas": cas_no,
                                "ec": ec_no,
                                "long_term": long_term,
                                "short_term": short_term,
                                "remarks": "; ".join(remarks),
                            })
        except Exception as e:
            logger.error(f"Error extracting Section 8 OEL table: {e}", exc_info=True)
        logger.info(f"Extracted {len(results)} OEL entries from PDF")
        return results

    def _get_symbol_as_base64(self, filename: str) -> str:
        """Helper to load a symbol from the 'symbole' folder and return it as a base64 data URI."""
        import base64
        import os
        from pathlib import Path
        
        # Try to find the 'symbole' directory relative to the current file
        # or in the base project directory
        base_dir = Path(__file__).parent
        symbol_path = base_dir / "symbole" / filename
        
        # Check absolute path fallback if relative fails
        if not symbol_path.exists():
            symbol_path = Path(r"c:\Users\Flo\Coding\agentzero-sdstranslate\backup_sds_translate_latest\FINAL\symbole") / filename
            
        if not symbol_path.exists():
            logger.debug(f"Symbol file not found: {filename} at {symbol_path}")
            return ""
            
        try:
            with open(symbol_path, "rb") as f:
                img_data = f.read()
                b64 = base64.b64encode(img_data).decode("utf-8")
                # Detect mime type by extension
                ext = filename.lower().split('.')[-1]
                mime = f"image/{ext}"
                if ext == 'jpg': mime = 'image/jpeg'
                return f"data:{mime};base64,{b64}"
        except Exception as e:
            logger.error(f"Error encoding symbol {filename}: {e}")
            return ""

    def extract_section_8_ppe(self) -> Dict[str, str]:
        """Extracts PPE icons from section 8. 
        First tries to map keywords to the high-quality 'symbole' folder, falls back to PDF cropping."""
        try:
            import base64
            import fitz
            import os
            
            if not os.path.exists(self.pdf_path):
                return {}
                
            doc = fitz.open(self.pdf_path)
            target_page = None
            page_text = ""
            for i in range(len(doc)):
                text = doc[i].get_text()
                if "8.2" in text and ("protection" in text.lower() or "schutz" in text.lower()):
                    target_page = doc[i]
                    page_text = text
                    break
            
            if not target_page:
                return {}
            
            results = {}
            # Library Mapping (Keyword -> Filename)
            library_mapping = {
                "eye_protection": {
                    "keywords": ["Eye/face protection", "Eye / face protection", "Augen-/Gesichtsschutz", "Augenschutz", "Eye glasses", "Schutzbrille"],
                    "filename": "M004_Augenschutz-benutzen.jpg"
                },
                "skin_protection": {
                    "keywords": ["Skin protection", "Hautschutz", "Handschutz", "Hand protection", "Protective gloves", "Handschuhe"],
                    "filename": "M009_Handschutz_benutzen.jpg"
                },
                "respiratory_protection": {
                    "keywords": ["Respiratory protection", "Atemschutz", "Protective mask", "Atemschutzmaske"],
                    "filename": "M017_Atemschutz-benutzen.jpg"
                },
                "body_protection": {
                    "keywords": ["Body protection", "Körperschutz", "Schutzkleidung", "Protective clothing", "Schutzanzug"],
                    "filename": "M010_Schutzkleidung-benutzen.jpg"
                }
            }
            
            # 1. Try Library Mapping first (Higher Quality)
            for key, config in library_mapping.items():
                for kw in config["keywords"]:
                    if kw.lower() in page_text.lower():
                        b64 = self._get_symbol_as_base64(config["filename"])
                        if b64:
                            results[key] = b64
                            logger.info(f"Matched keyword '{kw}' to library icon {config['filename']}")
                            break
            
            # 2. Fallback to cropping if something wasn't found in library
            # Only crop if the key isn't already filled by the library
            for key, config in library_mapping.items():
                if key not in results:
                    for phrase in config["keywords"]:
                        rects = target_page.search_for(phrase)
                        if rects:
                            r = rects[0]
                            # Look to the left of the text for the icon
                            icon_rect = fitz.Rect(max(0, r.x0 - 50), r.y0 - 5, r.x0 - 5, r.y1 + 15)
                            pix = target_page.get_pixmap(clip=icon_rect, matrix=fitz.Matrix(2, 2))
                            img_data = pix.tobytes("png")
                            b64 = base64.b64encode(img_data).decode("utf-8")
                            results[key] = f"data:image/png;base64,{b64}"
                            logger.info(f"Cropped PDF icon for {key} using phrase '{phrase}'")
                            break
                            
            return results
        except Exception as e:
            logger.warning(f"Could not extract PPE icons: {e}")
            return {}

    # ------------------------------------------------------------------
    # Section 16: Other Information
    # ------------------------------------------------------------------

    def extract_section_16(self) -> Dict[str, Any]:
        """
        Extract all Section 16 data from the PDF (pages 9-11, 0-indexed 8-10).

        Returns a dict matching the structure used in sds_parser._parse_section_16:
          {
            'indication_of_changes': [...],
            'abbreviations': [{'short': ..., 'long': ...}, ...],
            'abbreviations_source_note': '...',
            'literature_references': '...',
            'clp_classifications': [{'hazard_class': ..., 'hazard_statement': ..., 'procedure': ...}],
            'hazard_statements': [{'code': ..., 'text': ...}],
            'training_advice': '...',
            'additional_info': '...',
          }
        """
        result: Dict[str, Any] = {
            "indication_of_changes": [],
            "abbreviations": [],
            "abbreviations_source_note": "",
            "literature_references": "",
            "clp_classifications": [],
            "hazard_statements": [],
            "training_advice": "",
            "additional_info": "",
        }
        try:
            result["indication_of_changes"] = self._extract_indication_of_changes()
            result["abbreviations"], result["abbreviations_source_note"] = self._extract_abbreviations()
            result["literature_references"] = self._extract_literature_references()
            result["literature_references_table"] = self._extract_literature_references_table()
            result["clp_classifications"] = self._extract_clp_classifications()
            result["hazard_statements"] = self._extract_hazard_statements_list()
            result["training_advice"] = self._extract_training_advice()
            result["additional_info"] = self._extract_additional_info()
        except Exception as e:
            logger.error(f"Error extracting Section 16: {e}", exc_info=True)
        return result

    def _extract_indication_of_changes(self) -> List[str]:
        """Extract 16.1 Indication of changes from PDF."""
        changes = []
        try:
            # Search across multiple pages
            text = "\n".join([self._page_text(i) for i in range(8, 11)])
            m = re.search(r'16\.1\.\s*Indication of changes\s*\n(.*?)(?=16\.\d|SECTION|\Z)', text, re.DOTALL | re.IGNORECASE)
            if m:
                # Check for table-like structure first
                for line in m.group(1).splitlines():
                    line = line.strip()
                    if re.match(r'^\d+\.\d+\.?\s+', line):
                        changes.append(line)
                # If no table rows found, treat as plain text
                if not changes:
                    plain_text = " ".join(m.group(1).split())
                    if plain_text: changes.append(plain_text)
        except Exception as e:
            logger.warning(f"Could not extract indication of changes: {e}")
        return changes

    def _extract_abbreviations(self):
        """Extract 16.2 Abbreviations from PDF text."""
        abbreviations = []
        source_note = ""
        try:
            # Search across multiple pages where Section 16 could be
            text = "\n".join([self._page_text(i) for i in range(8, 11)]) # Pages 9, 10, 11
            
            m = re.search(r'16\.2\.\s*Abbreviations and acronyms\s*\n(.*?)(?=16\.\d|For abbreviations|\Z)', text, re.DOTALL | re.IGNORECASE)
            if not m:
                return [], ""
            
            block = m.group(1)
            
            # Process line by line. An abbreviation is typically all-caps.
            for line in block.splitlines():
                line = line.strip()
                if not line:
                    continue
                
                parts = re.split(r'\s{2,}', line, 1) # Split on 2 or more spaces
                if len(parts) == 2:
                    short, long = parts[0].strip(), parts[1].strip()
                    # A basic check: is the abbreviation mostly uppercase/digits?
                    if re.match(r'^[A-Z0-9\s/.-]+$', short):
                         abbreviations.append({"short": short, "long": long})
                # Fallback for single-space separators, being more careful
                elif ' ' in line:
                    parts = line.split(' ', 1)
                    if len(parts) == 2:
                        short, long = parts[0].strip(), parts[1].strip()
                        if re.match(r'^[A-Z0-9/.-]+$', short) and len(short) > 1 and len(short) < 15:
                             abbreviations.append({"short": short, "long": long})

            note_m = re.search(
                r'For abbreviations and acronyms,\s*see:\s*(.+?)(?=\n\n|\n16\.|\Z)',
                text, re.DOTALL | re.IGNORECASE
            )
            if note_m:
                source_note = " ".join(note_m.group(1).split())
        except Exception as e:
            logger.warning(f"Could not extract abbreviations: {e}")
        return abbreviations, source_note

    def _extract_literature_references(self) -> str:
        """Extract 16.3 Key literature references from PDF."""
        try:
            text = "\n".join([self._page_text(i) for i in range(8, 11)])
            m = re.search(
                r'16\.3\.?[^\n]*?(?:Key literature|Literaturhinweise).*?\n(.*?)(?=Substance name|Stoffname|16\.\d|\Z)',
                text, re.DOTALL | re.IGNORECASE
            )
            if m:
                return " ".join(m.group(1).split())
        except Exception as e:
            logger.warning(f"Could not extract literature references: {e}")
        return ""

    def _extract_literature_references_table(self) -> List[Dict[str, str]]:
        """Extract 16.3 Key literature references table from PDF."""
        results = []
        try:
            for page_idx in range(8, 11):
                tables = self._page_tables(page_idx)
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    header = table[0]
                    if not header: continue
                    header_str = " ".join(str(c) for c in header if c).lower()
                    if ("substance name" in header_str and "source" in header_str) or ("stoffname" in header_str and "bezugsquelle" in header_str):
                        for row in table[1:]:
                            if not row or not any(row): continue
                            cells = [str(c).strip() if c else "" for c in row]
                            results.append({
                                "substance": cells[0].replace('\n', '<br>') if len(cells) > 0 else "",
                                "type": cells[1].replace('\n', '<br>') if len(cells) > 1 else "",
                                "source": cells[2].replace('\n', '<br>') if len(cells) > 2 else ""
                            })
                        if results: return results
        except Exception as e:
            logger.warning(f"Could not extract literature references table: {e}")
        return results

    def _extract_clp_classifications(self) -> List[Dict[str, str]]:
        """Extract 16.4 CLP classification table from PDF."""
        results = []
        try:
            # Expand search to pages 9-11
            for page_idx in range(8, 11):
                tables = self._page_tables(page_idx)
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    header = table[0]
                    if header is None: continue
                    header_str = " ".join(str(c) for c in header if c).lower()
                    if "hazard class" not in header_str and "hazard statement" not in header_str:
                        continue
                    # Found the table, process it and return
                    for row in table[1:]:
                        if not row or all(c is None or str(c).strip() == "" for c in row):
                            continue
                        cells = [str(c).strip() if c else "" for c in row]
                        results.append({
                            "hazard_class": cells[0] if len(cells) > 0 else "",
                            "hazard_statement": cells[1] if len(cells) > 1 else "",
                            "procedure": cells[2] if len(cells) > 2 else "",
                        })
                    if results: return results # Stop after finding the first valid table
        except Exception as e:
            logger.warning(f"Could not extract CLP classifications: {e}")
        return results

    def _extract_hazard_statements_list(self) -> List[Dict[str, str]]:
        """Extract 16.5 hazard statements list from PDF."""
        results = []
        try:
            # Expand search to pages 9-11
            for page_idx in range(8, 11):
                tables = self._page_tables(page_idx)
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    header = table[0]
                    if header is None: continue
                    header_str = " ".join(str(c) for c in header if c).lower()
                    if "hazard statement" not in header_str:
                        continue
                    if len(header) >= 3: # Skip the main classification table
                        continue
                    # Found the table, process it
                    for row in table[1:]:
                        if not row or all(c is None or str(c).strip() == "" for c in row):
                            continue
                        cells = [str(c).strip() if c else "" for c in row]
                        if len(cells) >= 2 and re.match(r'^H\d{3}', cells[0]):
                            results.append({"code": cells[0], "text": cells[1]})
                    if results: return results # Stop after finding the first valid table
        except Exception as e:
            logger.warning(f"Could not extract hazard statements list: {e}")
        return results

    def _extract_training_advice(self) -> str:
        """Extract 16.6 Training advice from PDF."""
        try:
            text = "\n".join([self._page_text(i) for i in range(8, 11)])
            m = re.search(
                r'16\.6\.\s*Training advice\s*\n(.*?)(?=16\.\d|\Z)',
                text, re.DOTALL | re.IGNORECASE
            )
            if m:
                val = " ".join(m.group(1).split())
                if val.lower() != "no data available":
                    return val
        except Exception as e:
            logger.warning(f"Could not extract training advice: {e}")
        return ""

    def _extract_additional_info(self) -> str:
        """Extract 16.7 Additional information from PDF."""
        try:
            text = "\n".join([self._page_text(i) for i in range(8, 11)])
            m = re.search(
                r'16\.7\.\s*Additional information\s*\n(.*?)(?=\*\s*Data changed|en\s*/\s*DE|\Z)',
                text, re.DOTALL | re.IGNORECASE
            )
            if m:
                return " ".join(m.group(1).split())
        except Exception as e:
            logger.warning(f"Could not extract additional information: {e}")
        return ""

    # ------------------------------------------------------------------
    # Section 1: Life Cycle Stage
    # ------------------------------------------------------------------

    def extract_section_1_lcs(self) -> str:
        """
        Extract Life Cycle Stage [LCS] from Section 1.2 (page 1, 0-indexed 0).

        Returns a string like 'PW: Widespread use by professional workers'.
        """
        try:
            text = self._page_text(0)
            m = re.search(
                r'Life cycle stage \[LCS\]\s*\n\s*(.+?)(?:\n|Sector)',
                text, re.IGNORECASE
            )
            if m:
                return m.group(1).strip()
        except Exception as e:
            logger.warning(f"Could not extract Section 1 LCS: {e}")
        return ""

    # ------------------------------------------------------------------
    # Section 12: Mobility, Endocrine, Other Adverse Effects
    # ------------------------------------------------------------------

    def extract_section_12_mobility(self) -> str:
        """
        Extract Mobility in soil information from Section 12.4.

        Returns a string with mobility data or empty string if not found.
        """
        try:
            # Search on pages where Section 12 is likely to be (pages 7-9, 0-indexed 6-8)
            text = "\n".join([self._page_text(i) for i in range(6, 9)])
            
            # Look for Section 12.4 Mobility in soil
            m = re.search(
                r'12\.4\.?\s*Mobility in soil\s*\n(.*?)(?=12\.|SECTION 13|\Z)',
                text, re.DOTALL | re.IGNORECASE
            )
            if m:
                result = " ".join(m.group(1).split())
                if result.lower() != "no data available":
                    return result
                return "No data available."
            
            # Fallback: Try to find any mobility mention
            m = re.search(
                r'mobility.*?soil(.*?)(?:12\.|SECTION|\Z)',
                text, re.DOTALL | re.IGNORECASE
            )
            if m:
                return " ".join(m.group(0).split())
                
        except Exception as e:
            logger.warning(f"Could not extract Section 12.4 mobility: {e}")
        return ""

    def extract_section_12_endocrine(self) -> str:
        """
        Extract Endocrine disrupting properties information from Section 12.6.

        Returns a string with endocrine info or empty string if not found.
        """
        try:
            # Search on pages where Section 12 is likely to be (pages 7-9, 0-indexed 6-8)
            text = "\n".join([self._page_text(i) for i in range(6, 9)])
            
            # Look for Section 12.6 Endocrine disrupting properties
            m = re.search(
                r'12\.6\.?\s*Endocrine disrupting properties\s*\n(.*?)(?=12\.|SECTION 13|\Z)',
                text, re.DOTALL | re.IGNORECASE
            )
            if m:
                result = " ".join(m.group(1).split())
                if result.lower() != "no data available":
                    return result
                return "No data available."
            
            # Fallback: Check if there's component-level endocrine info
            # Search for each component
            for page_idx in range(6, 9):
                tables = self._page_tables(page_idx)
                for table in tables:
                    if not table or not table[0]:
                        continue
                    header_str = " ".join(str(c) for c in table[0] if c).lower()
                    if 'cas no' in header_str and 'ec no' in header_str:
                        # This is a component header - check for endocrine info in next rows
                        for row in table[1:]:
                            row_text = " ".join(str(c) for c in row if c).lower()
                            if 'endocrine' in row_text:
                                return " ".join(str(c) for c in row if c)
            
        except Exception as e:
            logger.warning(f"Could not extract Section 12.6 endocrine: {e}")
        return ""

    def extract_section_12_components(self) -> List[Dict[str, Any]]:
        """
        Extracts detailed component data from tables in Section 12.
        This is a complex parser to handle data missing from the XML.
        """
        results = []
        try:
            # Search on pages where Section 12 is likely to be (7-9, 0-indexed 6-8)
            all_tables = []
            for i in range(6, 9):
                all_tables.extend(self._page_tables(i))

            current_component = None

            for table in all_tables:
                if not table or not table[0]:
                    continue
                
                header_str = " ".join(str(c) for c in table[0] if c).strip()

                # Check for a new component header table
                if 'CAS No' in header_str and 'EC No' in header_str and len(table) == 1:
                    if current_component:
                        results.append(current_component)
                    
                    name_match = re.match(r'^(.*?)\s*\(CAS No', header_str)
                    current_component = {
                        'generic_name': name_match.group(1).strip() if name_match else '',
                        'aquatic_toxicity_entries': [],
                        'biodegradation': "", 
                        'bcf': "", 
                        'log_kow': "",
                        'pbt_result': ""
                    }
                    continue

                if not current_component:
                    continue

                # Now, parse the content tables for the current component
                first_cell = str(table[0][0]).lower() if table[0][0] else ""

                if 'aquatic toxicity' in header_str.lower():
                    for row in table[1:]:
                        if len(row) >= 4:
                            entry = {
                                'effect_dose': str(row[0]).split(':')[0].strip() if row[0] else "",
                                'value': str(row[0]).split(':')[1].strip() if row[0] and ':' in row[0] else "",
                                'exposure_time': str(row[1]).strip() if row[1] else "",
                                'species': str(row[2]).strip() if row[2] else "",
                                'method': str(row[3]).strip() if row[3] else ""
                            }
                            if entry['effect_dose'] or entry['value']:
                                current_component['aquatic_toxicity_entries'].append(entry)
                elif 'biodegradation' in first_cell and len(table) > 1 and len(table[1]) > 1:
                    current_component['biodegradation'] = str(table[1][1]).strip()
                elif 'log kow' in first_cell and len(table) > 1 and len(table[1]) > 1:
                     current_component['log_kow'] = str(table[1][1]).strip()
                elif 'bcf' in first_cell and len(table) > 1 and len(table[1]) > 1:
                     current_component['bcf'] = str(table[1][1]).strip()
                elif 'pbt and vpvb' in first_cell and len(table) > 1 and len(table[1]) > 0:
                     current_component['pbt_result'] = str(table[1][0]).strip()

            if current_component:
                results.append(current_component)
                
            # Supplement missing values using text regex (Bio/LogKow/BCF)
            text = "\n".join([self._page_text(i) for i in range(6, 9)])
            parts = re.split(r'(?i)CAS No\.:\s*([\d\-]+)', text)
            for i in range(1, len(parts) - 1, 2):
                cas = parts[i].strip()
                chunk = parts[i+1][:2000]
                comp = next((c for c in results if cas in str(c.get('cas_no',''))), None)
                if not comp:
                    continue
                bio_match = re.search(r'Biodegradation:\s*([^\n]+)', chunk, re.IGNORECASE)
                if bio_match and _is_empty(comp.get('biodegradation')):
                    comp['biodegradation'] = bio_match.group(1).strip()
                log_match = re.search(r'Log KOW:\s*([^\n]+)', chunk, re.IGNORECASE)
                if log_match and _is_empty(comp.get('log_kow')):
                    comp['log_kow'] = log_match.group(1).strip()
                bcf_match = re.search(r'Bioconcentration factor \(BCF\):\s*([^\n]+)', chunk, re.IGNORECASE)
                if bcf_match and _is_empty(comp.get('bcf')):
                    comp['bcf'] = bcf_match.group(1).strip()

        except Exception as e:
            logger.error(f"Error extracting Section 12 component tables: {e}", exc_info=True)
        
        logger.info(f"Extracted Section 12 component details for {len(results)} components from PDF.")
        return results

    def extract_section_12_gaps(self) -> Dict[str, str]:
        """
        Extract mobility, endocrine disrupting properties, and other adverse
        effects text from Section 12 in the PDF.

        Returns dict with keys: mobility_info, endocrine_disrupting_info,
        other_adverse_effects_info.
        """
        result = {
            "mobility_info": "",
            "endocrine_disrupting_info": "",
            "other_adverse_effects_info": "",
        }
        try:
            # Section 12 spans pages 7-8 (0-indexed 6-7)
            full = "\n".join(self._page_text(i) for i in range(6, 9))
            patterns = {
                "mobility_info": r'12\.4\.\s*Mobility in soil\s*\n(.*?)(?=12\.\d|\Z)',
                "endocrine_disrupting_info": r'12\.6\.\s*Endocrine disrupting properties\s*\n(.*?)(?=12\.\d|\Z)',
                "other_adverse_effects_info": r'12\.7\.\s*Other adverse effects\s*\n(.*?)(?=SECTION|\Z)',
            }
            for key, pattern in patterns.items():
                m = re.search(pattern, full, re.DOTALL | re.IGNORECASE)
                if m:
                    val = " ".join(m.group(1).split())
                    if val.lower() not in ("no data available", ""):
                        result[key] = val
        except Exception as e:
            logger.warning(f"Could not extract Section 12 gaps: {e}")
        return result

    # ------------------------------------------------------------------
    # Section 15: EU Legislation + WGK
    # ------------------------------------------------------------------

    def extract_section_15_wgk(self) -> str:
        """
        Extract WGK (Wassergefährdungsklasse) from Section 15 (page 9, 0-indexed 8).

        Returns a string like '1 - slightly hazardous to water'.
        """
        try:
            text = self._page_text(8)
            m = re.search(
                r'WGK\s*:\s*\n?\s*(.+?)(?:\n|$)',
                text, re.IGNORECASE
            )
            if m:
                return m.group(1).strip()
            # Fallback: look for WGK followed by value on same line
            m2 = re.search(r'WGK\s*:\s*(.+)', text, re.IGNORECASE)
            if m2:
                return m2.group(1).strip()
        except Exception as e:
            logger.warning(f"Could not extract Section 15 WGK: {e}")
        return ""

    def extract_section_15_eu_legislation(self) -> str:
        """
        Extract EU legislation text from Section 15.1.1.

        Returns the formatted EU legislation paragraph as a string.
        """
        try:
            text = "\n".join([self._page_text(i) for i in range(8, 11)])
            m = re.search(
                r'15\.1\.1\.\s*EU legislation\s*\n(.*?)(?=15\.1\.2|15\.2|\Z)',
                text, re.DOTALL | re.IGNORECASE
            )
            if m:
                val = m.group(1).strip()
                val = val.replace('\n', ' ')
                val = re.sub(r'\s*•\s*', '<br>• ', val)
                if val.startswith('<br>'):
                    val = val[4:]
                return val
        except Exception as e:
            logger.warning(f"Could not extract Section 15 EU legislation: {e}")
        return ""

    def extract_section_15_chemical_safety_assessment(self) -> str:
        """Extract Chemical Safety Assessment text from Section 15.2."""
        try:
            text = "\n".join([self._page_text(i) for i in range(8, 11)])
            m = re.search(r'15\.2\.?\s*Chemical Safety Assessment\s*\n(.*?)(?=SECTION 16|\Z)', text, re.DOTALL | re.IGNORECASE)
            if m:
                val = " ".join(m.group(1).split())
                if val:
                    return val
        except Exception as e:
            logger.warning(f"Could not extract Section 15.2: {e}")
        return ""

    def extract_section_15_national(self) -> Dict[str, Any]:
        """Extract national regulations like Störfallverordnung, etc."""
        results: Dict[str, Any] = {}
        try:
            text = "\n".join([self._page_text(i) for i in range(8, 11)])
            restr_match = re.search(r'(Restrictions of occupation|Beschäftigungsbeschränkungen)\s*\n\s*([^\n]+)', text, re.IGNORECASE)
            if restr_match:
                results['restrictions'] = restr_match.group(2).strip()
            storf_match = re.search(r'Störfallverordnung[^\n]*\n([\s\S]*?)(?=Betriebssicherheitsverordnung|Water hazard class|15\.2|\Z)', text, re.IGNORECASE)
            if storf_match:
                val = " ".join(storf_match.group(1).split()).replace('• ', '<br>• ')
                results['stoerfallverordnung'] = val
            betr_match = re.search(r'Betriebssicherheitsverordnung\s*\(BetrSichV\)\s*\n\s*([^\n]+)', text, re.IGNORECASE)
            if betr_match:
                results['betriebssicherheitsverordnung'] = betr_match.group(1).strip()
            other_match = re.search(r'Other regulations, restrictions and prohibition regulations\s*\n\s*([^\n]+)', text, re.IGNORECASE)
            if other_match:
                results['additional_info'] = [other_match.group(1).strip()]
        except Exception as e:
            logger.warning(f"Could not extract Section 15 national legislation: {e}")
        return results

    def extract_section_13_waste_codes(self) -> Dict[str, str]:
        """Extract waste codes for product and packaging."""
        result = {}
        try:
            text = "\n".join([self._page_text(i) for i in range(7, 10)])
            prod_match = re.search(r'Waste code product\s*\n\s*([\d\s\*]+)\s*(.*?)(?=\nWaste|\Z)', text, re.IGNORECASE)
            if prod_match:
                result['product'] = f"{prod_match.group(1).strip()} {prod_match.group(2).strip()}".strip()
            pack_match = re.search(r'Waste code packaging\s*\n\s*([\d\s\*]+)\s*(.*?)(?=\nWaste|\Z)', text, re.IGNORECASE)
            if pack_match:
                result['packaging'] = f"{pack_match.group(1).strip()} {pack_match.group(2).strip()}".strip()
        except Exception as e:
            logger.warning(f"Could not extract Section 13 waste codes: {e}")
        return result

    # ------------------------------------------------------------------
    # Main gap-filling entry point
    # ------------------------------------------------------------------

    def fill_gaps(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Takes parsed XML data dict, fills empty/missing fields from PDF,
        and returns the merged data dict.

        XML data always takes precedence - only empty/None/[] fields are filled.
        """
        import copy
        data = copy.deepcopy(parsed_data)

        # Clean text helper (deduplication & fixing HTML artifacts like 'gt')
        def _clean_text(val):
            if not isinstance(val, str):
                return val
            val = re.sub(r'\bgt\s+([\d\.]+)', r'> \1', val)
            if len(val) > 20:
                sentences = [s.strip() for s in val.split('. ') if s.strip()]
                seen = set()
                unique_s = []
                for s in sentences:
                    cmp_s = s.rstrip('.')
                    if cmp_s not in seen:
                        seen.add(cmp_s)
                        unique_s.append(s)
                if len(unique_s) < len(sentences):
                    val = '. '.join(unique_s)
                    if not val.endswith('.') and '.' in val:
                        val += '.'
            # Fix duplicate rat
            val = val.replace('rat (Ratte)', 'Ratte').replace('rabbit (Kaninchen)', 'Kaninchen')
            return val

        # Clean Section 3 ATE Values
        try:
            sec3 = data.get("section_3", {})
            if "mixture_components" in sec3:
                for comp in sec3["mixture_components"]:
                    if comp.get("ate_values"):
                        comp["ate_values"] = [_clean_text(ate) for ate in comp["ate_values"]]
            data["section_3"] = sec3
        except Exception:
            pass

        # Clean Section 11 Text
        try:
            sec11 = data.get("section_11", {})
            for k, v in sec11.items():
                sec11[k] = _clean_text(v)
            data["section_11"] = sec11
        except Exception:
            pass

        # --- Section 2: Precautionary Statements ---
        try:
            sec2 = data.get("section_2", {})
            labelling = sec2.get("labelling", {})
            prec_stmts = labelling.get("precautionary_statements", {})
            
            pdf_haz = self.extract_hazard_components()
            if pdf_haz:
                labelling["hazard_components"] = pdf_haz
            
            # Always try to merge with PDF data (not just when empty)
            # This ensures we get complete codes when XML might have partial data
            sec2_text = self._get_section_2_text()
            if sec2_text:
                pdf_prec_stmts = self._extract_precautionary_statements(sec2_text)
                
                # Merge prevention statements: prefer PDF if it has more codes
                xml_prevention = prec_stmts.get("prevention", [])
                pdf_prevention = pdf_prec_stmts.get("prevention", [])
                if pdf_prevention and (not xml_prevention or len(self._extract_codes_from_stmt(pdf_prevention[0] if pdf_prevention else {})) > len(self._extract_codes_from_stmt(xml_prevention[0] if xml_prevention else {}))):
                    prec_stmts["prevention"] = pdf_prevention
                elif not prec_stmts.get("prevention"):
                    prec_stmts["prevention"] = pdf_prevention
                
                # Merge response statements: prefer PDF if it has more codes
                xml_response = prec_stmts.get("response", [])
                pdf_response = pdf_prec_stmts.get("response", [])
                if pdf_response and (not xml_response or len(self._extract_codes_from_stmt(pdf_response[0] if pdf_response else {})) > len(self._extract_codes_from_stmt(xml_response[0] if xml_response else {}))):
                    prec_stmts["response"] = pdf_response
                elif not prec_stmts.get("response"):
                    prec_stmts["response"] = pdf_response
                
                labelling["precautionary_statements"] = prec_stmts
                sec2["labelling"] = labelling
                data["section_2"] = sec2
                if not _is_empty(pdf_prevention) or not _is_empty(pdf_response):
                    logger.info("Enhanced Section 2 Precautionary Statements by comparing with PDF")
        except Exception as e:
            logger.warning(f"Could not enhance Section 2 Precautionary Statements: {e}", exc_info=True)

        # --- Section 8: Occupational Exposure Limits ---
        try:
            sec8 = data.get("section_8", {})
            
            # Always try to extract from PDF to get clean formatting
            pdf_oel_limits = self.extract_section_8_oel()
            if pdf_oel_limits:
                mapped_oel = []
                for o in pdf_oel_limits:
                    mapped_oel.append({
                        'limit_type': o['limit_type'],
                        'substance': o['substance'],
                        'CAS_number': o['cas'],
                        'ec': o['ec'],
                        'time_weight_average': o['long_term'],
                        'short_term_limit': o['short_term'],
                        'regulatory_reference': o['remarks']
                    })
                sec8["occupational_exposure_limits"] = mapped_oel
                data["section_8"] = sec8
                logger.info(f"Filled Section 8 Occupational Exposure Limits from PDF ({len(pdf_oel_limits)} entries)")
        except Exception as e:
            logger.warning(f"Could not fill Section 8 Occupational Exposure Limits: {e}", exc_info=True)

        # --- Section 3: ATE Values ---
        try:
            sec3 = data.get("section_3", {})
            if "mixture_components" in sec3:
                # Check if any component is missing ATE values
                needs_filling = any(_is_empty(comp.get("ate_values")) for comp in sec3["mixture_components"])
                
                if needs_filling:
                    pdf_ate_values = self.extract_section_3_ate_values()
                    if pdf_ate_values:
                        changed = False
                        for component in sec3["mixture_components"]:
                            # Try to match by component name (case-insensitive and partial match)
                            comp_name = component.get("name", "").lower()
                            if not comp_name:
                                continue
                            
                            for pdf_comp_name, ate_list in pdf_ate_values.items():
                                if pdf_comp_name.lower() in comp_name:
                                    if _is_empty(component.get("ate_values")):
                                        component["ate_values"] = ate_list
                                        changed = True
                                        break # Move to next component once matched
                        if changed:
                            data["section_3"] = sec3
                            logger.info("Filled Section 3 ATE values from PDF")
        except Exception as e:
            logger.warning(f"Could not fill Section 3 ATE values: {e}", exc_info=True)

        # --- Section 1: Life Cycle Stage ---
        try:
            sec1 = data.get("section_1", {})
            relevant_uses = sec1.get("relevant_uses", {})
            if _is_empty(relevant_uses.get("lcs")):
                lcs = self.extract_section_1_lcs()
                if lcs:
                    relevant_uses["lcs"] = lcs
                    sec1["relevant_uses"] = relevant_uses
                    data["section_1"] = sec1
                    logger.info("Filled Section 1 LCS from PDF")
        except Exception as e:
            logger.warning(f"Could not fill Section 1 LCS: {e}")

        # --- Section 8: PPE Icons ---
        try:
            sec8 = data.get("section_8", {})
            ppe_icons = self.extract_section_8_ppe()
            if ppe_icons:
                sec8["ppe_icons"] = ppe_icons
                data["section_8"] = sec8
                logger.info(f"Filled Section 8 PPE icons from PDF")
        except Exception as e:
            logger.warning(f"Could not fill Section 8 PPE icons: {e}")

        # --- Section 9: Water solubility ---
        try:
            sec9 = data.get("section_9", {})
            if "safety_data" in sec9:
                for item in sec9["safety_data"]:
                    if "solubility" in item.get("parameter", "").lower() and _is_empty(item.get("value")):
                        text = "\n".join([self._page_text(i) for i in range(4, 7)])
                        m = re.search(r'Water solubility\s*(completely miscible|vollständig mischbar|[\d\.]+\s*g/l)', text, re.IGNORECASE)
                        if m and not _is_empty(m.group(1)):
                            item["value"] = m.group(1).strip()
                            data["section_9"] = sec9
                            break
        except Exception:
            pass

        # --- Section 12: Ecotoxicological Component Data & Text Gaps ---
        try:
            sec12 = data.get("section_12", {})
            # First, try to fill component data from PDF tables if they exist
            if sec12 and 'ecotox_components' in sec12:
                pdf_components = self.extract_section_12_components()
                if pdf_components:
                    for xml_comp in sec12['ecotox_components']:
                        for pdf_comp in pdf_components:
                            # Match by name (case-insensitive)
                            if xml_comp.get('generic_name', '').lower() == pdf_comp.get('generic_name', '').lower():
                                if _is_empty(xml_comp.get('biodegradation')) and pdf_comp.get('biodegradation'):
                                    xml_comp['biodegradation'] = pdf_comp['biodegradation']
                                if _is_empty(xml_comp.get('log_kow')) and pdf_comp.get('log_kow'):
                                    xml_comp['log_kow'] = pdf_comp['log_kow']
                                if _is_empty(xml_comp.get('bcf')) and pdf_comp.get('bcf'):
                                    xml_comp['bcf'] = pdf_comp['bcf']
                                if _is_empty(xml_comp.get('pbt_result')) and pdf_comp.get('pbt_result'):
                                    xml_comp['pbt_result'] = pdf_comp['pbt_result']
                                # Overwrite aquatic toxicity if XML was empty
                                if _is_empty(xml_comp.get('aquatic_toxicity_entries')) and pdf_comp.get('aquatic_toxicity_entries'):
                                    xml_comp['aquatic_toxicity_entries'] = pdf_comp['aquatic_toxicity_entries']
                    logger.info("Updated Section 12 component data from PDF.")

            # Then, fill the general text gaps for the section
            gaps12 = self.extract_section_12_gaps()
            changed = False
            for key, val in gaps12.items():
                if val and _is_empty(sec12.get(key)):
                    sec12[key] = val
                    changed = True
            if changed:
                logger.info("Filled Section 12 text gaps from PDF")
            
            data["section_12"] = sec12

        except Exception as e:
            logger.warning(f"Could not fill Section 12 gaps: {e}")

        # --- Section 13: Waste Codes ---
        try:
            sec13 = data.get("section_13", {})
            waste_codes = self.extract_section_13_waste_codes()
            if waste_codes:
                changed = False
                if _is_empty(sec13.get("waste_code_product")) and 'product' in waste_codes:
                    sec13["waste_code_product"] = waste_codes['product']
                    changed = True
                if _is_empty(sec13.get("waste_code_packaging")) and 'packaging' in waste_codes:
                    sec13["waste_code_packaging"] = waste_codes['packaging']
                    changed = True
                if changed:
                    data["section_13"] = sec13
                    logger.info("Filled Section 13 Waste Codes from PDF")
        except Exception as e:
            logger.warning(f"Could not fill Section 13 gaps: {e}")

        # --- Section 15: EU Legislation + WGK + National ---
        try:
            sec15 = data.get("section_15", {})
            changed15 = False
            if _is_empty(sec15.get("eu_legislation")):
                eu_leg = self.extract_section_15_eu_legislation()
                if eu_leg:
                    sec15["eu_legislation"] = eu_leg
                    changed15 = True
                    logger.info("Filled Section 15 EU legislation from PDF")
            if _is_empty(sec15.get("wgk")):
                wgk = self.extract_section_15_wgk()
                if wgk:
                    sec15["wgk"] = wgk
                    changed15 = True
                    logger.info(f"Filled Section 15 WGK from PDF: {wgk}")
            
            if _is_empty(sec15.get("chemical_safety_assessment")) or sec15.get("chemical_safety_assessment") == "No data available.":
                csa = self.extract_section_15_chemical_safety_assessment()
                if csa:
                    sec15["chemical_safety_assessment"] = csa
                    changed15 = True
            
            # Other national regulations
            nat_leg_dict = self.extract_section_15_national()
            for key, value in nat_leg_dict.items():
                if _is_empty(sec15.get(key)):
                    sec15[key] = value
                    changed15 = True
            if changed15:
                data["section_15"] = sec15
        except Exception as e:
            logger.warning(f"Could not fill Section 15 gaps: {e}")

        # --- Section 16: Other Information ---
        try:
            other_info = data.get("other_information", {})
            sec16_pdf = self.extract_section_16()
            changed = False

            field_map = {
                "indication_of_changes": "indication_of_changes",
                "abbreviations": "abbreviations",
                "abbreviations_source_note": "abbreviations_source_note",
                "literature_references": "literature_references",
                "literature_references_table": "literature_references_table",
                "training_advice": "training_advice",
                "additional_info_lines": "additional_info",  # XML key -> PDF key
            }
            for xml_key, pdf_key in field_map.items():
                if _is_empty(other_info.get(xml_key)):
                    pdf_val = sec16_pdf.get(pdf_key)
                    if not _is_empty(pdf_val):
                        # Wrap plain string in list for list-type fields
                        if xml_key == "additional_info_lines" and isinstance(pdf_val, str):
                            other_info[xml_key] = [pdf_val] if pdf_val else []
                        else:
                            other_info[xml_key] = pdf_val
                        changed = True

            # clp_classifications lives in hazard_identification, not other_information
            haz_id = data.get("hazard_identification", {})
            if _is_empty(haz_id.get("clp_classifications")):
                clp = sec16_pdf.get("clp_classifications", [])
                if clp:
                    haz_id["clp_classifications"] = clp
                    data["hazard_identification"] = haz_id
                    changed = True

            if changed:
                data["other_information"] = other_info
                logger.info("Filled Section 16 gaps from PDF")
        except Exception as e:
            logger.warning(f"Could not fill Section 16 gaps: {e}")

        return data
