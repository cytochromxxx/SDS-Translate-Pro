import sqlite3

def clean_sds_extracted():
    conn = sqlite3.connect('phrases_library.db')
    cursor = conn.cursor()

    # Sprachspalten ermitteln
    cursor.execute("PRAGMA table_info(phrases)")
    columns = [row[1] for row in cursor.fetchall()]
    lang_columns = [col for col in columns if col.endswith('_original')]

    # Anzahl aller 'sds_pdf_extracted' Einträge
    cursor.execute("SELECT COUNT(*) FROM phrases WHERE source = 'sds_pdf_extracted'")
    total_extracted = cursor.fetchone()[0]

    # Wir bauen die Bedingung: Ein Eintrag ist unvollständig, wenn EINE der Sprachspalten NULL oder leer ist
    conditions = " OR ".join([f"({col} IS NULL OR TRIM({col}) = '')" for col in lang_columns])
    
    # Zählen, wie viele davon unvollständig sind
    query_incomplete = f"SELECT COUNT(*) FROM phrases WHERE source = 'sds_pdf_extracted' AND ({conditions})"
    cursor.execute(query_incomplete)
    incomplete_count = cursor.fetchone()[0]

    # Löschen der unvollständigen
    if incomplete_count > 0:
        delete_query = f"DELETE FROM phrases WHERE source = 'sds_pdf_extracted' AND ({conditions})"
        cursor.execute(delete_query)
        conn.commit()
        
        # Datenbank optimieren
        cursor.execute("VACUUM")
        conn.commit()

    conn.close()

    print(f"Gesamtzahl 'sds_pdf_extracted' vor Bereinigung: {total_extracted}")
    print(f"Gelöschte unvollständige Einträge: {incomplete_count}")
    print(f"Verbleibende vollständige Einträge: {total_extracted - incomplete_count}")

if __name__ == '__main__':
    clean_sds_extracted()
