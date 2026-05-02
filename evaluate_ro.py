import sqlite3
import random

def evaluate_romanian_translations():
    conn = sqlite3.connect('phrases_library.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Hole alle Phrasen
    cursor.execute("SELECT code, de_original, en_original, ro_original FROM phrases WHERE ro_original IS NOT NULL AND ro_original != ''")
    rows = cursor.fetchall()

    total_ro = len(rows)
    identical_to_en_de = 0
    empty_or_too_short = 0

    sample_pool = []

    for row in rows:
        de = (row['de_original'] or "").strip()
        en = (row['en_original'] or "").strip()
        ro = (row['ro_original'] or "").strip()

        if len(ro) < 3:
            empty_or_too_short += 1
            continue

        if ro.lower() == de.lower() or ro.lower() == en.lower():
            identical_to_en_de += 1
            continue
            
        if len(ro) > 20 and len(de) > 20:
            sample_pool.append(row)

    with open('ro_evaluation.txt', 'w', encoding='utf-8') as f:
        f.write("=== Statistik der rumänischen (RO) Übersetzungen ===\n")
        f.write(f"Gesamtanzahl ausgefüllter RO-Phrasen: {total_ro}\n")
        f.write(f"Zu kurz / Leer: {empty_or_too_short}\n")
        f.write(f"1:1 Kopie von DE oder EN (nicht übersetzt): {identical_to_en_de}\n")
        f.write(f"Potenziell echte Übersetzungen: {total_ro - identical_to_en_de - empty_or_too_short}\n")
        
        f.write("\n=== Stichprobe zur Qualitätsprüfung (15 zufällige, längere Phrasen) ===\n")
        
        if sample_pool:
            random.seed(42)
            samples = random.sample(sample_pool, min(15, len(sample_pool)))
            for i, s in enumerate(samples, 1):
                f.write(f"\n{i}. [Code: {s['code']}]\n")
                f.write(f"   DE: {s['de_original']}\n")
                f.write(f"   EN: {s['en_original']}\n")
                f.write(f"   RO: {s['ro_original']}\n")
        else:
            f.write("Keine ausreichend langen Phrasen für eine Stichprobe gefunden.\n")

    conn.close()

if __name__ == '__main__':
    evaluate_romanian_translations()
