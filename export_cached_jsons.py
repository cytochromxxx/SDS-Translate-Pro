#!/usr/bin/env python3
"""
Exportiert die bereits gecachten Datalab JSONs in das datalab_exports Verzeichnis
und verknüpft sie mit den request_ids aus der CSV.
"""

import os
import json
import csv
import shutil
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CACHE_DIR = "chandra_cache"
OUTPUT_DIR = "datalab_exports"
CSV_FILE = "bibliothek/usage-all-all.csv"

def ensure_output_dir():
    """Erstellt Ausgabeverzeichnis, falls es nicht existiert."""
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

def extract_request_id_from_json(json_path):
    """Extrahiert die request_id aus einer JSON-Datei (aus request_check_url)."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        check_url = data.get('request_check_url', '')
        if check_url and '/' in check_url:
            request_id = check_url.rstrip('/').split('/')[-1]
            return request_id
    except Exception as e:
        logger.debug(f"Fehler beim Parsen von {json_path}: {e}")
    
    return None

def main():
    """Hauptfunktion: Exportiert gecachte JSONs mit request_ids."""
    
    logger.info("="*70)
    logger.info("💾 Datalab Cache JSON Exporter")
    logger.info("="*70)
    
    # Verzeichnis vorbereiten
    ensure_output_dir()
    
    # CSV lesen
    rows = read_csv(CSV_FILE)
    if not rows:
        logger.error("❌ Keine Einträge in CSV gefunden.")
        return
    
    # Erstelle ein Mapping von request_id -> filename
    request_id_map = {}
    for row in rows:
        request_id = row.get('request_id', '').strip()
        filename = row.get('filename', '').strip()
        if request_id and filename:
            request_id_map[request_id] = filename
    
    logger.info(f"🗺️  Erstellt request_id Mapping mit {len(request_id_map)} Einträgen\n")
    
    # Prüfe ob Cache-Verzeichnis existiert
    if not os.path.exists(CACHE_DIR):
        logger.error(f"❌ Cache-Verzeichnis nicht gefunden: {CACHE_DIR}")
        return
    
    # Finde alle JSON-Dateien im Cache
    cache_files = list(Path(CACHE_DIR).glob("*.json"))
    logger.info(f"📦 Gefunden: {len(cache_files)} JSON-Dateien im Cache\n")
    
    exported = 0
    skipped = 0
    
    for cache_file in sorted(cache_files):
        request_id = extract_request_id_from_json(str(cache_file))
        
        if not request_id:
            logger.debug(f"⚠ Konnte request_id nicht extrahieren aus {cache_file.name}")
            skipped += 1
            continue
        
        filename = request_id_map.get(request_id, "unknown")
        
        # Entferne Dateiendung aus filename
        clean_filename = filename.replace('.pdf', '').replace('.xml', '')
        
        # Zielname
        output_filename = f"{request_id}_{clean_filename}"
        output_path = os.path.join(OUTPUT_DIR, f"{output_filename}.json")
        
        try:
            # Kopiere Datei
            shutil.copy2(str(cache_file), output_path)
            
            logger.info(f"✓ Exportiert: {request_id[:12]}... → {output_filename}")
            exported += 1
            
        except Exception as e:
            logger.error(f"❌ Fehler beim Kopieren: {e}")
            skipped += 1
    
    # Zusammenfassung
    logger.info("\n" + "="*70)
    logger.info("✅ EXPORT ABGESCHLOSSEN")
    logger.info(f"   Exportiert: {exported}/{len(cache_files)}")
    logger.info(f"   Übersprungen: {skipped}/{len(cache_files)}")
    logger.info("="*70)

if __name__ == "__main__":
    main()
