import sqlite3

def analyze_translation_quality():
    conn = sqlite3.connect('phrases_library.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Sprachspalten ermitteln
    cursor.execute("PRAGMA table_info(phrases)")
    columns = [row['name'] for row in cursor.fetchall()]
    lang_columns = [col for col in columns if col.endswith('_original')]
    
    # Filtere de und en aus den Zielsprachen für den Vergleich
    target_langs = [col for col in lang_columns if col not in ('de_original', 'en_original')]

    cursor.execute(f"SELECT {', '.join(lang_columns)} FROM phrases")
    rows = cursor.fetchall()

    total_phrases = 0
    total_languages_expected = 0
    total_languages_filled = 0
    
    identical_to_source = 0
    length_anomalies = 0
    total_translations_checked = 0

    for row in rows:
        de = row['de_original']
        en = row['en_original']
        
        de_str = de.strip() if de else ""
        en_str = en.strip() if en else ""
        
        # Bestimme die "Originalsprache" für diese Zeile (bevorzuge EN, dann DE)
        source_text = en_str if en_str else de_str
        
        if not source_text or len(source_text) < 3:
            continue # Überspringe leere oder extrem kurze Quelltexte (z.B. "-", "pH")
            
        total_phrases += 1
        source_len = len(source_text)

        for lang in target_langs:
            total_languages_expected += 1
            target_text = row[lang]
            target_str = target_text.strip() if target_text else ""
            
            if target_str:
                total_languages_filled += 1
                total_translations_checked += 1
                
                # Prüfe auf faulenza-Übersetzung (identisch zum Original)
                # (Ignoriere sehr kurze Begriffe wie IUPAC, die oft in allen Sprachen gleich sind)
                if len(source_text) > 5 and target_str.lower() == source_text.lower():
                    identical_to_source += 1
                    
                # Prüfe auf Längenanomalien (Faktor 4 Unterschied)
                target_len = len(target_str)
                ratio = max(source_len, target_len) / min(source_len, target_len) if min(source_len, target_len) > 0 else 100
                if ratio > 4 and source_len > 10:
                    length_anomalies += 1

    conn.close()

    print("=== Qualitätsanalyse der Übersetzungen (Basis: DE/EN) ===")
    print(f"Ausgewertete Phrasen (mit gültigem DE/EN Text): {total_phrases}")
    
    if total_phrases == 0:
        print("Keine auswertbaren Phrasen gefunden.")
        return

    completeness = (total_languages_filled / total_languages_expected) * 100
    print(f"\n1. Vollständigkeit:")
    print(f"   - Von {total_languages_expected} erwarteten Übersetzungen sind {total_languages_filled} ausgefüllt.")
    print(f"   - Füllstand der Zielsprachen: {completeness:.1f}%")

    if total_translations_checked > 0:
        identical_pct = (identical_to_source / total_translations_checked) * 100
        anomaly_pct = (length_anomalies / total_translations_checked) * 100
        
        print(f"\n2. Sprachliche Auffälligkeiten (geprüfte Übersetzungen: {total_translations_checked}):")
        print(f"   - Einfach kopiert (Zielsprache identisch zu DE/EN): {identical_to_source} mal ({identical_pct:.2f}%)")
        print(f"   - Längen-Anomalien (Verdacht auf abgeschnitten/falsch): {length_anomalies} mal ({anomaly_pct:.2f}%)")
        
        print("\nFazit:")
        if completeness > 90 and identical_pct < 2 and anomaly_pct < 5:
            print("   => Die allgemeine Qualität und Vollständigkeit der Datenbank ist SEHR GUT.")
        elif completeness > 70 and identical_pct < 5 and anomaly_pct < 10:
            print("   => Die allgemeine Qualität ist GUT, es gibt aber Lücken.")
        else:
            print("   => Die Qualität ist DURCHWACHSEN. Viele fehlende oder kopierte Übersetzungen.")
    else:
        print("Keine Übersetzungen in Zielsprachen vorhanden.")

if __name__ == '__main__':
    analyze_translation_quality()
