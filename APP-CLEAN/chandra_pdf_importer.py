import logging
import os
import tempfile
import json
import requests
import hashlib
from typing import Dict, Any, Optional
from sds_parser import NewSDScomParser

logger = logging.getLogger(__name__)

def parse_sds_with_chandra(xml_path: str, pdf_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Liest XML-Daten aus und nutzt die Chandra VLM (Vision-Language Model) Engine
    für fehlerfreie Tabellen-Extraktion aus PDFs.
    """
    print("\n" + "="*50)
    print("💎 CHANDRA (ULTRA-PREMIUM) IMPORTER GESTARTET!")
    print("="*50 + "\n")

    logger.info(f"[Chandra] Lese XML Basisdaten: {xml_path}")
    parser = NewSDScomParser(xml_path)
    sds_data = parser.parse()
    
    if not pdf_path:
        return sds_data
        
    logger.info(f"[Chandra] Verarbeite PDF mit Vision-Language Model: {pdf_path}")
    
    chandra_json_data = _run_chandra_inference(pdf_path)
    
    if chandra_json_data:
        # Chandra nutzt exakt das gleiche Datalab-JSON-Format wie ODL.
        # Daher können wir den hervorragenden Gap-Filler von ODL wiederverwenden!
        from odl_pdf_importer import _fill_gaps_with_odl_data
        sds_data = _fill_gaps_with_odl_data(sds_data, chandra_json_data)
        logger.info("[Chandra] ✓ Gap-Filling mit Chandra-Daten erfolgreich")
    
    return sds_data

def convert_pdf_to_json_with_chandra(input_path: str, output_dir: str) -> str:
    """
    Für den reinen PDF-Import.
    Wandelt PDF mit Chandra in das Datalab-Layout-JSON um.
    """
    print("\n" + "="*50)
    print("💎 CHANDRA VLM: REINER PDF-IMPORT GESTARTET!")
    print("="*50 + "\n")
    
    chandra_json_data = _run_chandra_inference(input_path)
    
    if chandra_json_data:
        output_file = os.path.join(output_dir, "chandra_output.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(chandra_json_data, f, indent=2, ensure_ascii=False)
        return output_file
        
    raise Exception("Chandra VLM API konnte keine JSON-Daten generieren.")

def _run_chandra_inference(pdf_path: str) -> Optional[Dict[str, Any]]:
    # Cache-Ordner erstellen
    cache_dir = "chandra_cache"
    os.makedirs(cache_dir, exist_ok=True)
    
    # Hash der PDF-Datei berechnen, um sie eindeutig zu identifizieren (anhand des Inhalts, nicht des Namens)
    file_hash = hashlib.sha256()
    with open(pdf_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            file_hash.update(chunk)
    pdf_hash = file_hash.hexdigest()
    cache_file = os.path.join(cache_dir, f"{pdf_hash}.json")
    
    # Prüfen, ob wir dieses PDF schon einmal verarbeitet haben
    if os.path.exists(cache_file):
        logger.info("[Chandra] ⚡ Cache-Treffer! Lade gespeicherte JSON-Daten (überspringt API-Call).")
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)

    # Nutze deinen bereitgestellten API-Key als direkten Fallback
    api_key = os.environ.get("DATALAB_API_KEY", "EEll9Ek7OuRRCPqrZyAQLYBVl9JLkIeYpq0P10it7jw")
    
    if api_key:
        logger.info("[Chandra] Nutze Datalab Cloud API...")
        try:
            url = "https://api.datalab.to/api/v1/marker"
            headers = {"X-Api-Key": api_key}
            
            with open(pdf_path, "rb") as f:
                files = {"file": (os.path.basename(pdf_path), f, "application/pdf")}
                data = {"output_format": "json", "extract_tables": "true"}
                
                logger.info("[Chandra] Sende Dokument an Datalab API (dies kann einen Moment dauern)...")
                response = requests.post(url, headers=headers, files=files, data=data, timeout=300)
                
            if response.status_code == 200:
                logger.info("[Chandra] ✓ API-Anfrage erfolgreich abgeschlossen!")
                result_json = response.json()
                # Im Cache speichern für zukünftige Uploads derselben Datei
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(result_json, f, indent=2, ensure_ascii=False)
                return result_json
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            logger.error(f"[Chandra] API-Fehler: {e}")
            raise Exception(f"Fehler bei der Datalab API-Kommunikation: {str(e)}")
    else:
        logger.info("[Chandra] Versuche lokale GPU-Inferenz...")
        try:
            import chandra
        except ImportError:
            raise ImportError("Die Chandra Ultra-Premium-Engine ist noch nicht installiert oder es fehlt ein API-Key.\nLösung:\n1. Lokal: 'pip install chandra' (Benötigt min. 16GB VRAM)\n2. Cloud: 'DATALAB_API_KEY' in die Umgebungsvariablen eintragen.")
        
        return None