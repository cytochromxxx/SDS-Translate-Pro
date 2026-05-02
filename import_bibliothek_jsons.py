#!/usr/bin/env python3
"""
Importiert die Datalab JSONs aus dem bibliothek Ordner
und organisiert sie mit ihren request_ids.
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

BIBLIOTHEK_DIR = "bibliothek"
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

def extract_filename_from_json_name(json_filename):
    """
    Extrahiert den Produktnamen aus dem JSON-Dateinamen.
    z.B.: datalab-output-SDS_Mycoplasma_Off_15-5xxx_en_DE_Ver.05.pdf.json 
    → SDS_Mycoplasma_Off_15-5xxx_en_DE_Ver.05
    """
    # Entferne 'datalab-output-' Präfix und '.pdf.json' Suffix
    name = json_filename.replace('datalab-output-', '').replace('.pdf.json', '')
    return name

def find_request_id_for_filename(filename, csv_rows):
    """
    Sucht die request_id für einen gegebenen Dateinamen in der CSV.
    """
    for row in csv_rows:
        csv_filename = row.get('filename', '').strip()
        # Vergleiche die Dateinamen (mit und ohne Erweiterung)
        if csv_filename.endswith('.pdf') or csv_filename.endswith('.xml'):
            csv_base = csv_filename.rsplit('.', 1)[0]
        else:
            csv_base = csv_filename
        
        if csv_base == filename:
            return row.get('request_id', '').strip()
    
    return None

def main():
    """Hauptfunktion: Importiert JSONs aus bibliothek."""
    
    logger.info("="*70)
    logger.info("📥 Datalab JSON Bibliothek Importer")
    logger.info("="*70)
    
    # Verzeichnis vorbereiten
    ensure_output_dir()
    
    # CSV lesen
    rows = read_csv(CSV_FILE)
    if not rows:
        logger.error("❌ Keine Einträge in CSV gefunden.")
        return
    
    # Finde alle datalab-output-*.json Dateien
    json_files = list(Path(BIBLIOTHEK_DIR).glob("datalab-output-*.json"))
    logger.info(f"📦 Gefunden: {len(json_files)} JSON-Dateien im bibliothek Ordner\n")
    
    if not json_files:
        logger.warning("⚠️ Keine JSON-Dateien gefunden!")
        return
    
    copied = 0
    skipped = 0
    
    logger.info("="*70)
    logger.info("📊 Starte Import...")
    logger.info("="*70 + "\n")
    
    for json_file in sorted(json_files):
        json_name = json_file.name
        product_filename = extract_filename_from_json_name(json_name)
        
        # Finde request_id
        request_id = find_request_id_for_filename(product_filename, rows)
        
        if request_id:
            # Zielname mit request_id
            output_filename = f"{request_id}_{product_filename}.json"
            output_path = os.path.join(OUTPUT_DIR, output_filename)
            
            try:
                shutil.copy2(str(json_file), output_path)
                logger.info(f"✓ {json_name}")
                logger.info(f"  → request_id: {request_id[:12]}...")
                logger.info(f"  → Ziel: {output_filename}\n")
                copied += 1
            except Exception as e:
                logger.error(f"❌ Fehler beim Kopieren von {json_name}: {e}\n")
                skipped += 1
        else:
            logger.warning(f"⚠️ Keine request_id gefunden für {product_filename}\n")
            skipped += 1
    
    # Zusammenfassung
    logger.info("="*70)
    logger.info("✅ IMPORT ABGESCHLOSSEN")
    logger.info(f"   Kopiert: {copied}/{len(json_files)}")
    logger.info(f"   Übersprungen: {skipped}/{len(json_files)}")
    logger.info(f"   Zielverzeichnis: {OUTPUT_DIR}/")
    logger.info("="*70)

if __name__ == "__main__":
    main()
