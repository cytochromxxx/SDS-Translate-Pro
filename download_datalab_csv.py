#!/usr/bin/env python3
"""
Datalab CSV Bulk Downloader
Liest eine CSV-Datei mit Datalab Request-IDs und lädt die fertigen JSON-Ergebnisse herunter.
"""

import os
import csv
import json
import requests
import time

API_KEY = os.environ.get("DATALAB_API_KEY", "EEll9Ek7OuRRCPqrZyAQLYBVl9JLkIeYpq0P10it7jw")

def download_results(csv_filepath, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    headers = {"X-Api-Key": API_KEY}
    
    with open(csv_filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            request_id = row.get("request_id")
            filename = row.get("filename", "unknown")
            status = row.get("status")
            endpoint = row.get("endpoint", "marker")
            
            if status != "success":
                print(f"⏭️ Überspringe {filename} (Status: {status})")
                continue
                
            # Ziel-Dateiname generieren (.pdf -> .json)
            if filename.lower().endswith(".pdf"):
                json_filename = filename[:-4] + ".json"
            else:
                json_filename = filename + ".json"
                
            out_path = os.path.join(output_folder, json_filename)
            if os.path.exists(out_path):
                print(f"✅ {json_filename} existiert bereits. Überspringe...")
                continue
                
            # API Endpoints (Marker ist der Standard-Endpunkt für Dokumenten-Extraktion)
            endpoints_to_try = ["marker", endpoint] if endpoint != "marker" else ["marker"]
            
            for ep in endpoints_to_try:
                url = f"https://api.datalab.to/api/v1/{ep}/{request_id}"
                print(f"⏳ Lade {json_filename} über /{ep} (ID: {request_id})...")
                
                try:
                    resp = requests.get(url, headers=headers, timeout=30)
                    if resp.status_code == 200:
                        data = resp.json()
                        # Falls die API in ein {"status": "complete", "json": {...}} verpackt
                        save_data = data.get("json", data) if isinstance(data, dict) and "json" in data else data
                        
                        with open(out_path, "w", encoding="utf-8") as out_f:
                            json.dump(save_data, out_f, indent=2, ensure_ascii=False)
                        print(f"  -> ✅ Erfolgreich gespeichert!")
                        break
                    else:
                        print(f"  -> ❌ API Fehler {resp.status_code}: {resp.text}")
                except Exception as e:
                    print(f"  -> ❌ Netzwerkfehler: {e}")
                    
            time.sleep(1)  # Kurze Pause für Rate-Limits

if __name__ == "__main__":
    csv_file = "datalab_requests.csv"
    out_dir = "datalab_exports"
    
    if os.path.exists(csv_file):
        print(f"=== Datalab CSV Downloader ===")
        print(f"Lese Requests aus {csv_file} und speichere nach {out_dir}/")
        download_results(csv_file, out_dir)
        print("=== Fertig ===")
    else:
        print(f"❌ Datei '{csv_file}' nicht gefunden.")
        print("Bitte erstelle diese Datei mit den eingefügten CSV-Daten und starte das Skript erneut.")