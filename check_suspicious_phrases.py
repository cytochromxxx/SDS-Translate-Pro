import sqlite3
import re

def check_suspicious_phrases():
    conn = sqlite3.connect('phrases_library.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT id, code, de_original, en_original FROM phrases")
    rows = cursor.fetchall()

    suspicious_identical = []
    suspicious_length = []
    suspicious_encoding = []
    suspicious_content = []

    def is_mostly_letters(text):
        if not text: return False
        letters = re.sub(r'[^a-zA-ZäöüÄÖÜß]', '', text)
        return len(letters) > 2

    for row in rows:
        de = row['de_original'] or ""
        en = row['en_original'] or ""
        
        de_clean = de.strip()
        en_clean = en.strip()

        # 1. Identisch (und nicht nur Zahlen/Sonderzeichen)
        if de_clean and en_clean and de_clean.lower() == en_clean.lower() and is_mostly_letters(de_clean):
            # Ignoriere kurze Standardabkürzungen wie "pH" oder "OECD"
            if len(de_clean) > 4:
                suspicious_identical.append(row)

        # 2. Längenunterschied (Faktor 4 bei Texten > 10 Zeichen)
        if de_clean and en_clean and (len(de_clean) > 10 or len(en_clean) > 10):
            len_de = len(de_clean)
            len_en = len(en_clean)
            if len_de > 0 and len_en > 0:
                ratio = max(len_de, len_en) / min(len_de, len_en)
                if ratio > 4:
                    suspicious_length.append(row)

        # 3. Encoding-Fehler
        if '' in de_clean or '' in en_clean:
            suspicious_encoding.append(row)
            
        # 4. Ungültiger Inhalt (nur Sonderzeichen, oder "UNDEFINED")
        for text in (de_clean, en_clean):
            if text:
                if text.upper() in ["UNDEFINED", "NULL", "NAN"]:
                    suspicious_content.append(row)
                    break
                # Nur Sonderzeichen/Zahlen ohne Buchstaben (aber mehr als 3 Zeichen lang)
                if len(text) > 3 and not re.search(r'[a-zA-ZäöüÄÖÜß]', text):
                    suspicious_content.append(row)
                    break

    print(f"=== Analyse auf verdächtige Phrasen (DE/EN) ===\n")
    
    print(f"1. Identischer Text in DE und EN (Mögliche fehlende Übersetzung): {len(suspicious_identical)} gefunden")
    for r in suspicious_identical[:5]:
        print(f"   - [Code: {r['code']}] '{r['de_original']}'")
    if len(suspicious_identical) > 5: print("   ...")
    print()

    print(f"2. Extremer Längenunterschied (Möglicherweise abgeschnitten): {len(suspicious_length)} gefunden")
    for r in suspicious_length[:5]:
        print(f"   - [Code: {r['code']}]")
        print(f"     DE: {r['de_original'][:60]}...")
        print(f"     EN: {r['en_original'][:60]}...")
    if len(suspicious_length) > 5: print("   ...")
    print()

    print(f"3. Encoding-Fehler (Enthält ''): {len(suspicious_encoding)} gefunden")
    for r in suspicious_encoding[:5]:
        print(f"   - [Code: {r['code']}] DE: '{r['de_original'][:40]}' | EN: '{r['en_original'][:40]}'")
    if len(suspicious_encoding) > 5: print("   ...")
    print()
    
    print(f"4. Ungültiger/Sinnfreier Inhalt (Nur Sonderzeichen, 'UNDEFINED', etc.): {len(suspicious_content)} gefunden")
    for r in suspicious_content[:5]:
        print(f"   - [Code: {r['code']}] DE: '{r['de_original'][:40]}' | EN: '{r['en_original'][:40]}'")
    if len(suspicious_content) > 5: print("   ...")

if __name__ == '__main__':
    check_suspicious_phrases()
