import sqlite3
import shutil
import os

def clean_database():
    db_file = 'phrases_library.db'
    backup_file = 'phrases_library_backup.db'
    
    # 1. Backup erstellen
    print(f"Erstelle Backup von {db_file} nach {backup_file}...")
    shutil.copy2(db_file, backup_file)
    print("Backup erfolgreich erstellt.")

    # 2. Verbindung herstellen
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # 3. Sprachspalten ermitteln
    cursor.execute("PRAGMA table_info(phrases)")
    columns = [row[1] for row in cursor.fetchall()]
    lang_columns = [col for col in columns if col.endswith('_original')]

    # 4. Statistiken vor der Bereinigung
    cursor.execute("SELECT COUNT(*) FROM phrases")
    count_before = cursor.fetchone()[0]

    # 5. Duplikate entfernen
    # Wir behalten den Eintrag mit der kleinsten rowid für jede Kombination von Sprach-Strings.
    group_by_clause = ', '.join(lang_columns)
    
    # Um sicherzugehen, dass NULL und leere Strings richtig behandelt werden,
    # nutzen wir ein einfaches GROUP BY. In SQLite sind NULLs beim GROUP BY gleich.
    delete_query = f"""
    DELETE FROM phrases
    WHERE rowid NOT IN (
        SELECT MIN(rowid)
        FROM phrases
        GROUP BY {group_by_clause}
    )
    """
    
    print("Führe Löschvorgang der Duplikate durch...")
    cursor.execute(delete_query)
    deleted_count = cursor.rowcount
    conn.commit()

    # 6. Statistiken nach der Bereinigung
    cursor.execute("SELECT COUNT(*) FROM phrases")
    count_after = cursor.fetchone()[0]

    # 7. Datenbank komprimieren
    print("Optimiere Datenbank (VACUUM)...")
    cursor.execute("VACUUM")
    conn.commit()
    conn.close()

    # 8. Bericht ausgeben
    print("\n=== Bereinigungsbericht ===")
    print(f"Einträge vor Bereinigung: {count_before}")
    print(f"Einträge nach Bereinigung: {count_after}")
    print(f"Tatsächlich gelöschte Zeilen: {deleted_count}")
    
    original_size = os.path.getsize(backup_file) / (1024 * 1024)
    new_size = os.path.getsize(db_file) / (1024 * 1024)
    print(f"Datenbankgröße vor VACUUM: {original_size:.2f} MB")
    print(f"Datenbankgröße nach VACUUM: {new_size:.2f} MB")

if __name__ == '__main__':
    clean_database()
