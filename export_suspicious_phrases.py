import sqlite3
import csv
import re

def export_suspicious_phrases():
    conn = sqlite3.connect('phrases_library.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT id, code, de_original, en_original FROM phrases")
    rows = cursor.fetchall()

    def is_mostly_letters(text):
        if not text: return False
        letters = re.sub(r'[^a-zA-ZäöüÄÖÜß]', '', text)
        return len(letters) > 2

    csv_filename = 'suspicious_phrases_report.csv'
    
    with open(csv_filename, mode='w', newline='', encoding='utf-8-sig') as csv_file:
        fieldnames = ['Category', 'Code', 'DE_Original', 'EN_Original']
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, delimiter=';')
        
        writer.writeheader()

        for row in rows:
            de = row['de_original'] or ""
            en = row['en_original'] or ""
            
            de_clean = de.strip()
            en_clean = en.strip()
            
            code = row['code']

            # 1. Identisch (und nicht nur Zahlen/Sonderzeichen)
            if de_clean and en_clean and de_clean.lower() == en_clean.lower() and is_mostly_letters(de_clean):
                if len(de_clean) > 4:
                    writer.writerow({
                        'Category': 'Identical DE/EN',
                        'Code': code,
                        'DE_Original': de_clean,
                        'EN_Original': en_clean
                    })
                    continue

            # 2. Längenunterschied (Faktor 4 bei Texten > 10 Zeichen)
            if de_clean and en_clean and (len(de_clean) > 10 or len(en_clean) > 10):
                len_de = len(de_clean)
                len_en = len(en_clean)
                if len_de > 0 and len_en > 0:
                    ratio = max(len_de, len_en) / min(len_de, len_en)
                    if ratio > 4:
                        writer.writerow({
                            'Category': 'Extreme Length Difference',
                            'Code': code,
                            'DE_Original': de_clean,
                            'EN_Original': en_clean
                        })
                        continue

            # 3. Ungültiger Inhalt (nur Sonderzeichen, oder "UNDEFINED")
            invalid_content = False
            for text in (de_clean, en_clean):
                if text:
                    if text.upper() in ["UNDEFINED", "NULL", "NAN"]:
                        invalid_content = True
                        break
                    if len(text) > 3 and not re.search(r'[a-zA-ZäöüÄÖÜß]', text):
                        invalid_content = True
                        break
            
            if invalid_content:
                writer.writerow({
                    'Category': 'Invalid or Nonsense Content',
                    'Code': code,
                    'DE_Original': de_clean,
                    'EN_Original': en_clean
                })

    print(f"Bericht erfolgreich erstellt: {csv_filename}")

if __name__ == '__main__':
    export_suspicious_phrases()
