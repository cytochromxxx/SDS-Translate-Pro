import sqlite3
import collections

def generate_report():
    conn = sqlite3.connect('phrases_library.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get total records
    cursor.execute("SELECT COUNT(*) as count FROM phrases")
    total_records = cursor.fetchone()['count']

    # Get all columns for translation checking
    cursor.execute("PRAGMA table_info(phrases)")
    columns = [row['name'] for row in cursor.fetchall()]
    lang_columns = [col for col in columns if col.endswith('_original')]

    # Query all phrases
    cursor.execute(f"SELECT id, code, {', '.join(lang_columns)} FROM phrases")
    rows = cursor.fetchall()

    de_counts = collections.Counter()
    en_counts = collections.Counter()
    de_en_counts = collections.Counter()
    all_langs_counts = collections.Counter()

    for row in rows:
        de = row['de_original']
        en = row['en_original']
        
        # Tuple of all language texts
        all_langs = tuple(row[col] for col in lang_columns)

        if de and de.strip():
            de_counts[de.strip()] += 1
        if en and en.strip():
            en_counts[en.strip()] += 1
        if de and en and de.strip() and en.strip():
            de_en_counts[(de.strip(), en.strip())] += 1
            
        # Ignore empty entries for full translation duplicates
        if any(bool(t) for t in all_langs):
            all_langs_counts[all_langs] += 1

    dup_de = sum(count - 1 for count in de_counts.values() if count > 1)
    dup_en = sum(count - 1 for count in en_counts.values() if count > 1)
    dup_de_en = sum(count - 1 for count in de_en_counts.values() if count > 1)
    dup_all = sum(count - 1 for count in all_langs_counts.values() if count > 1)

    print("=== Duplikate in der Datenbank (phrases_library.db) ===")
    print(f"Gesamtzahl der Phrasen: {total_records}")
    print(f"Redundante Einträge (gleicher deutscher Text): {dup_de} (aus {sum(1 for c in de_counts.values() if c > 1)} eindeutigen Phrasen)")
    print(f"Redundante Einträge (gleicher englischer Text): {dup_en} (aus {sum(1 for c in en_counts.values() if c > 1)} eindeutigen Phrasen)")
    print(f"Redundante Einträge (gleiches Paar DE + EN): {dup_de_en} (aus {sum(1 for c in de_en_counts.values() if c > 1)} eindeutigen Paaren)")
    print(f"Exakte Duplikate (alle Sprachen identisch): {dup_all} (aus {sum(1 for c in all_langs_counts.values() if c > 1)} identischen Übersetzungs-Sets)")
    
    # Let's show top 5 duplicated DE/EN pairs
    print("\n--- Top 5 am häufigsten duplizierte Phrasen (DE + EN) ---")
    top_de_en = de_en_counts.most_common(5)
    for (de, en), count in top_de_en:
        if count > 1:
            print(f"- {count}x vorhanden:")
            print(f"  DE: {de[:80]}{'...' if len(de) > 80 else ''}")
            print(f"  EN: {en[:80]}{'...' if len(en) > 80 else ''}")

if __name__ == '__main__':
    generate_report()
