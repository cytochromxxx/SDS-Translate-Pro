#!/usr/bin/env python3
"""
Datalab Dashboard JSON Downloader
Liest eine CSV-Datei mit request_ids aus dem Datalab Dashboard
und lädt die entsprechenden JSON-Ergebnisse herunter.
"""

import os
import csv
import json
import requests
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Konfiguration
DATALAB_API_KEY = os.environ.get("DATALAB_API_KEY", "EEll9Ek7OuRRCPqrZyAQLYBVl9JLkIeYpq0P10it7jw")
DATALAB_API_BASE = "https://api.datalab.to/api/v1"
OUTPUT_DIR = "datalab_exports"

def ensure_output_dir():
    """Erstelt Ausgabeverzeichnis, falls es nicht existiert."""
    Path(OUTPUT_DIR).mkdir(exist_ok=True)
    logger.info(f"📁 Ausgabeverzeichnis: {OUTPUT_DIR}")

def read_csv(csv_path):
    """Liest die CSV-Datei und gibt eine Liste von Dictionaries zurück."""
    if not os.path.exists(csv_path):
        logger.error(f"❌ CSV-Datei nicht gefunden: {csv_path}")
        return []
    
    rows = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        logger.info(f"✓ CSV gelesen: {len(rows)} Einträge gefunden")
        return rows
    except Exception as e:
        logger.error(f"❌ Fehler beim Lesen der CSV: {e}")
        return []

def download_json_by_request_id(request_id, filename, endpoint_type):
    """
    Versucht, das JSON-Ergebnis vom Datalab Dashboard zu laden.
    
    Mapping der Endpoints:
    - pipeline → /pipeline/{request_id}
    - marker → /marker/{request_id}
    - convert → /convert/{request_id}
    """
    headers = {"X-Api-Key": DATALAB_API_KEY}
    
    # Bestimme den richtigen Endpoint basierend auf endpoint_type
    # Falls endpoint_type unbekannt ist, versuche alle
    if endpoint_type in ["pipeline", "marker", "convert"]:
        endpoints = [f"{DATALAB_API_BASE}/{endpoint_type}/{request_id}"]
    else:
        # Fallback: Versuche alle bekannten Endpoints
        endpoints = [
            f"{DATALAB_API_BASE}/pipeline/{request_id}",
            f"{DATALAB_API_BASE}/marker/{request_id}",
            f"{DATALAB_API_BASE}/convert/{request_id}",
        ]
    
    for endpoint in endpoints:
        try:
            logger.debug(f"  → Versuche: {endpoint}")
            response = requests.get(endpoint, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✓ JSON heruntergeladen: {filename}")
                return result
            elif response.status_code == 404:
                logger.debug(f"  → 404 (nicht gefunden)")
                continue
            elif response.status_code == 401:
                logger.warning(f"  ⚠ 401 Unauthorized - API-Key ungültig?")
                continue
            else:
                logger.debug(f"  → HTTP {response.status_code}")
                continue
        except Exception as e:
            logger.debug(f"  ✗ Fehler: {str(e)[:100]}")
            continue
    
    logger.warning(f"⚠ Konnte JSON für {request_id} ({endpoint_type}) nicht abrufen")
    return None

def save_json(data, filename):
    """Speichert ein JSON-Objekt in einer Datei."""
    if not data:
        return False
    
    output_path = os.path.join(OUTPUT_DIR, f"{filename}.json")
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"  💾 Gespeichert: {output_path}")
        return True
    except Exception as e:
        logger.error(f"  ❌ Speicherfehler: {e}")
        return False

def main(csv_path="usage-all-all.csv"):
    """Hauptfunktion: Liest CSV und lädt alle JSONs herunter."""
    
    logger.info("="*70)
    logger.info("🚀 Datalab Dashboard JSON Downloader")
    logger.info("="*70)
    
    # Verzeichnis vorbereiten
    ensure_output_dir()
    
    # CSV lesen
    if not os.path.exists(csv_path):
        # Versuche im bibliothek-Verzeichnis
        alt_path = f"bibliothek/{csv_path}"
        if os.path.exists(alt_path):
            csv_path = alt_path
            logger.info(f"✓ CSV gefunden unter: {csv_path}")
        else:
            logger.error(f"❌ CSV nicht gefunden. Suche nach: {csv_path}")
            return
    
    rows = read_csv(csv_path)
    if not rows:
        logger.error("❌ Keine Einträge in CSV gefunden.")
        return
    
    # Filtere nur erfolgreiche Requests
    success_rows = [r for r in rows if r.get('status', '').lower() == 'success']
    logger.info(f"📊 {len(success_rows)} erfolgreiche Requests gefunden")
    
    # Lade JSONs herunter
    downloaded = 0
    failed = 0
    
    logger.info("\n" + "="*70)
    logger.info("📥 Starte Download...")
    logger.info("="*70 + "\n")
    
    for i, row in enumerate(success_rows, 1):
        request_id = row.get('request_id', '').strip()
        filename = row.get('filename', 'unknown').replace('.pdf', '').replace('.xml', '')
        endpoint = row.get('endpoint', 'unknown').lower()
        
        if not request_id:
            logger.warning(f"[{i}/{len(success_rows)}] ⚠ Keine request_id vorhanden")
            continue
        
        logger.info(f"[{i}/{len(success_rows)}] 🔍 Request: {request_id}")
        logger.info(f"         Datei: {filename}")
        logger.info(f"         Endpoint: {endpoint}")
        
        # Versuche JSON herunterzuladen
        json_data = download_json_by_request_id(request_id, filename, endpoint)
        
        if json_data:
            if save_json(json_data, f"{request_id}_{filename}"):
                downloaded += 1
        else:
            failed += 1
        
        logger.info("")
    
    # Zusammenfassung
    logger.info("="*70)
    logger.info("✅ DOWNLOAD ABGESCHLOSSEN")
    logger.info(f"   Erfolgreich: {downloaded}/{len(success_rows)}")
    logger.info(f"   Fehlgeschlagen: {failed}/{len(success_rows)}")
    logger.info("="*70)

if __name__ == "__main__":
    import sys
    
    csv_file = sys.argv[1] if len(sys.argv) > 1 else "usage-all-all.csv"
    main(csv_file)
