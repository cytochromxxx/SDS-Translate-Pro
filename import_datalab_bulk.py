#!/usr/bin/env python3
"""
Bulk Importer für Datalab JSON-Dateien
Liest einen Ordner mit rohen Datalab-JSONs ein, parst sie mit dem SDSJsonParser
und speichert die sauberen, strukturierten Dictionaries in der lokalen Bibliothek.
"""

import os
import json
import sqlite3
import glob
from sds_json_parser import parse_sds_json

DB_PATH = 'sds_library.db'

def init_db():
    """Initialisiert die Datenbank und die Tabelle für die SDS-Bibliothek."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sds_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            version TEXT,
            revision_date TEXT,
            language TEXT,
            import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            parsed_data_json TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def import_local_jsons(folder_path):
    if not os.path.exists(folder_path):
        print(f"❌ Fehler: Der Ordner '{folder_path}' existiert nicht.")
        return

    json_files = glob.glob(os.path.join(folder_path, '*.json'))
    if not json_files:
        print(f"⚠️ Keine JSON-Dateien im Ordner '{folder_path}' gefunden.")
        return

    print(f"🔍 Gefunden: {len(json_files)} JSON-Dateien. Starte Import...\n")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    success_count = 0
    error_count = 0

    for file_path in json_files:
        try:
            # 1. JSON durch den bestehenden Parser jagen
            parsed_data = parse_sds_json(file_path)
            if not parsed_data:
                print(f"  [FEHLER] Konnte {os.path.basename(file_path)} nicht parsen (Leeres Ergebnis).")
                error_count += 1
                continue
                
            # 2. Metadaten extrahieren
            meta = parsed_data.get('meta', {})
            product_name = meta.get('product_name')
            if not product_name or product_name == 'Unknown':
                product_name = parsed_data.get('section_1', {}).get('product_identifier', {}).get('trade_name', 'Unbekanntes Produkt')
                
            version = meta.get('version', '')
            revision_date = meta.get('revision_date', '')
            language = meta.get('language', 'en')
            
            # 3. Gepardtes Dictionary als sauberes JSON-String serialisieren
            parsed_data_str = json.dumps(parsed_data, ensure_ascii=False)
            
            # 4. In die Datenbank einfügen
            cursor.execute('''
                INSERT INTO sds_documents (product_name, version, revision_date, language, parsed_data_json)
                VALUES (?, ?, ?, ?, ?)
            ''', (product_name, version, revision_date, language, parsed_data_str))
            
            success_count += 1
            print(f"  [OK] {product_name} (Version: {version})")
            
        except Exception as e:
            print(f"  [FEHLER] bei {os.path.basename(file_path)}: {str(e)}")
            error_count += 1

    conn.commit()
    conn.close()
    
    print("\n" + "="*50)
    print("✅ IMPORT ABGESCHLOSSEN")
    print(f"Erfolgreich: {success_count}")
    print(f"Fehlerhaft:  {error_count}")
    print("="*50)

if __name__ == "__main__":
    init_db()
    print("=== Datalab SDS Bulk Importer ===")
    target_folder = input("Bitte gib den Pfad zum Ordner mit deinen Datalab-JSONs ein (z.B. 'datalab_exports'): ").strip()
    
    if target_folder:
        import_local_jsons(target_folder)
    else:
        print("Kein Ordner angegeben. Abbruch.")