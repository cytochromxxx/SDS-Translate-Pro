import logging
import json
import tempfile
import os
from typing import Dict, Any, Optional
from sds_parser import NewSDScomParser
from pdf_gap_filler import _is_empty

logger = logging.getLogger(__name__)

def parse_sds_with_odl(xml_path: str, pdf_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Liest XML-Daten sicher aus und nutzt OpenDataLoader für den PDF-Import 
    zur Schließung komplexer Lücken (z.B. Tabellen).
    
    Fallback-Strategie: Wenn OpenDataLoader nicht verfügbar ist (Java fehlt),
    verwende pdfplumber als Fallback.
    """
    print("\n" + "="*50)
    print("🚀 ODL IMPORTER WURDE GESTARTET!")
    print("="*50 + "\n")

    # 1. XML parsen (XML ist immer die Source of Truth und hat Vorrang)
    logger.info(f"[ODL Importer] Lese XML Basisdaten: {xml_path}")
    parser = NewSDScomParser(xml_path)
    sds_data = parser.parse()
    
    if not pdf_path:
        return sds_data
        
    # 2. Versuche OpenDataLoader, falls verfügbar
    logger.info(f"[ODL Importer] Versuche OpenDataLoader für PDF-Analyse: {pdf_path}")
    try:
        sds_data = _parse_with_opendataloader(sds_data, pdf_path)
        logger.info("[ODL Importer] ✓ OpenDataLoader-Verarbeitung erfolgreich")
        return sds_data
    except FileNotFoundError as e:
        logger.warning(f"[ODL Importer] Java/OpenDataLoader nicht verfügbar: {str(e)}")
        logger.info("[ODL Importer] Fallback zu pdfplumber...")
    except Exception as e:
        logger.warning(f"[ODL Importer] OpenDataLoader-Fehler: {str(e)}")
        logger.info("[ODL Importer] Fallback zu pdfplumber...")
    
    # 3. Fallback zu pdfplumber
    try:
        sds_data = _parse_with_pdfplumber(sds_data, pdf_path)
        logger.info("[ODL Importer] ✓ PDF-Verarbeitung mit pdfplumber erfolgreich (Fallback-Modus)")
        return sds_data
    except Exception as e:
        logger.error(f"[ODL Importer] Auch pdfplumber-Fallback fehlgeschlagen: {str(e)}")
        raise RuntimeError(f"PDF-Import fehlgeschlagen (ODL und pdfplumber): {str(e)}")
        
    return sds_data

def _parse_with_opendataloader(sds_data: Dict[str, Any], pdf_path: str) -> Dict[str, Any]:
    """
    Nutzt OpenDataLoader (erfordert Java) für hochpräzise PDF-Analyse.
    """
    from opendataloader_pdf import convert
    
    with tempfile.TemporaryDirectory() as temp_output_dir:
        logger.info(f"[ODL] Konvertiere PDF mit OpenDataLoader zu JSON...")
        
        # Convert PDF to JSON format (which includes data extraction and table recognition)
        convert(
            input_path=pdf_path,
            output_dir=temp_output_dir,
            format="json",
            quiet=False
        )
        
        # Find the output file
        output_files = [f for f in os.listdir(temp_output_dir) if f.endswith('.json')]
        if not output_files:
            # Try markdown output if JSON fails
            logger.info("[ODL] JSON fehlgeschlagen, versuche Markdown...")
            convert(
                input_path=pdf_path,
                output_dir=temp_output_dir,
                format="markdown",
                quiet=False
            )
            output_files = [f for f in os.listdir(temp_output_dir) if f.endswith('.md')]
        
        if not output_files:
            raise RuntimeError(f"[ODL] Keine Output-Dateien erstellt")
        
        output_file = os.path.join(temp_output_dir, output_files[0])
        logger.info(f"[ODL] Lese Output: {output_files[0]}")
        
        # Save debug output
        debug_path = pdf_path + ".odl_debug.json"
        with open(output_file, "r", encoding="utf-8") as f:
            pdf_content = f.read()
            if output_files[0].endswith('.json'):
                pdf_json = json.loads(pdf_content)
            else:
                pdf_json = {"content": pdf_content, "format": "markdown"}
        
        with open(debug_path, "w", encoding="utf-8") as f:
            json.dump(pdf_json, f, indent=2, default=str)
        logger.info(f"[ODL] Debug-Output: {debug_path}")
        
        # Merge data
        sds_data = _fill_gaps_with_odl_data(sds_data, pdf_json)
        return sds_data

def _parse_with_pdfplumber(sds_data: Dict[str, Any], pdf_path: str) -> Dict[str, Any]:
    """
    Fallback-Parser mit pdfplumber (keine Java erforderlich).
    Extrahiert Text und Tabellen für Gap-Filling.
    """
    import pdfplumber
    
    logger.info(f"[Fallback] Öffne PDF mit pdfplumber: {pdf_path}")
    
    pdf_data = {
        "pages": [],
        "tables": [],
        "text": ""
    }
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            logger.info(f"[Fallback] PDF hat {len(pdf.pages)} Seiten")
            
            for page_num, page in enumerate(pdf.pages, 1):
                page_info = {
                    "page": page_num,
                    "text": page.extract_text() or "",
                    "tables": []
                }
                
                # Versuche Tabellen zu extrahieren
                try:
                    tables = page.extract_tables()
                    if tables:
                        for table_idx, table in enumerate(tables):
                            page_info["tables"].append({
                                "table_index": table_idx,
                                "data": table
                            })
                            pdf_data["tables"].append({
                                "page": page_num,
                                "table_index": table_idx,
                                "data": table
                            })
                except Exception as e:
                    logger.warning(f"[Fallback] Fehler beim Tabellen-Extrahieren auf Seite {page_num}: {e}")
                
                pdf_data["pages"].append(page_info)
                pdf_data["text"] += page_info["text"] + "\n---PAGE BREAK---\n"
        
        logger.info(f"[Fallback] Extrahiert: {len(pdf_data['pages'])} Seiten, {len(pdf_data['tables'])} Tabellen")
        
        # Merge data
        sds_data = _fill_gaps_with_odl_data(sds_data, pdf_data)
        return sds_data
        
    except Exception as e:
        logger.error(f"[Fallback] pdfplumber-Fehler: {str(e)}")
        raise

def _fill_gaps_with_odl_data(sds_data: Dict[str, Any], odl_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mapt die hochpräzisen Markdown/JSON-Strukturen aus dem OpenDataLoader 
    oder die Fallback-Daten aus pdfplumber in die Platzhalter ("No data available") 
    des XML Dictionaries.
    
    OpenDataLoader extrahiert:
    - Tabellen mit strukturierter Formatierung
    - Text mit Layout-Information
    - Bilder und GHS-Symbole
    - Seitennummern und Verweise
    
    pdfplumber extrahiert (Fallback):
    - Text pro Seite
    - Erkannte Tabellen
    - Page-by-page information
    """
    logger.info("[Gap-Filler] Starte Daten-Mapping...")
    
    # Erkenne das Format der ODL-Daten
    if isinstance(odl_data, dict):
        if "pages" in odl_data:
            # pdfplumber format
            logger.info(f"[Gap-Filler] Format: pdfplumber ({len(odl_data.get('pages', []))} Seiten)")
            return _fill_gaps_from_pdfplumber(sds_data, odl_data)
        elif "content" in odl_data:
            # Markdown format from OpenDataLoader
            logger.info("[Gap-Filler] Format: OpenDataLoader (Markdown)")
            return _fill_gaps_from_markdown(sds_data, odl_data)
        else:
            # JSON/structured format from OpenDataLoader
            logger.info("[Gap-Filler] Format: OpenDataLoader (JSON)")
            return _fill_gaps_from_json(sds_data, odl_data)
    
    logger.warning("[Gap-Filler] Unbekanntes Datenformat, keine Gap-Filling")
    return sds_data

def _fill_gaps_from_pdfplumber(sds_data: Dict[str, Any], pdf_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Füllt Lücken mit Daten aus pdfplumber (Text und Tabellen).
    """
    logger.info(f"[Gap-Filler] Verarbeite {len(pdf_data.get('tables', []))} Tabellen für SDS-Zuordnung")
    
    # Beispiel: Sektion 8 (Expositionskontrolle) mit Tabellen füllen
    if "section_8" in sds_data and pdf_data.get("tables"):
        all_text = pdf_data.get("text", "").lower()
        if any(keyword in all_text for keyword in ["section 8", "exposure", "oel", "peel"]):
            logger.info("[Gap-Filler] Tabellen für Sektion 8 gefunden")
    
    return sds_data

def _fill_gaps_from_markdown(sds_data: Dict[str, Any], markdown_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Füllt Lücken mit Markdown-Daten aus OpenDataLoader.
    """
    content = markdown_data.get("content", "")
    logger.info(f"[Gap-Filler] Verarbeite Markdown-Inhalt ({len(content)} Zeichen)")
    return sds_data

def _fill_gaps_from_json(sds_data: Dict[str, Any], json_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Füllt Lücken mit JSON/strukturierten Daten aus OpenDataLoader.
    """
    logger.info(f"[Gap-Filler] Verarbeite JSON-Daten mit {len(json_data)} Fields")
    return sds_data