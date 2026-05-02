import sqlite3
import os
import threading
import csv
import uuid

_db_lock = threading.Lock()
CSV_TRANSLATION_SOURCE = "sds_phrases_PERFEKT.csv"
CSV_TRANSLATION_DB_PATH = "sds_phrases_PERFEKT.db"
_current_db_path = CSV_TRANSLATION_DB_PATH


def _create_db_from_translation_csv(csv_path, db_path):
    """
    Build the runtime phrase SQLite DB from the CSV translation source.
    The generated schema keeps compatibility with existing app queries.
    """
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        fieldnames = [name.strip() for name in (reader.fieldnames or []) if name and name.strip()]

        if "en_original" not in fieldnames:
            raise ValueError("CSV must contain 'en_original' column")

        # Use CSV columns as phrase text columns and keep metadata columns used by legacy tools.
        phrase_columns = fieldnames

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("DROP TABLE IF EXISTS phrases")
            cursor.execute("DROP TABLE IF EXISTS ghs_pictograms")
            cursor.execute("DROP TABLE IF EXISTS sds_pictograms")

            dynamic_cols_sql = ",\n    ".join([f"{col} TEXT" for col in phrase_columns])
            cursor.execute(
                f"""
CREATE TABLE phrases (
    id TEXT PRIMARY KEY,
    code TEXT,
    type TEXT,
    source TEXT,
    status TEXT,
    {dynamic_cols_sql}
)
"""
            )

            # Tables used by GHS manager are expected in the active DB.
            cursor.execute(
                """
CREATE TABLE ghs_pictograms (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    hazard_class TEXT,
    svg_path TEXT,
    png_path TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_url TEXT
)
"""
            )
            cursor.execute(
                """
CREATE TABLE sds_pictograms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sds_id TEXT NOT NULL,
    ghs_code TEXT NOT NULL,
    position INTEGER DEFAULT 0,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ghs_code) REFERENCES ghs_pictograms(code),
    UNIQUE(sds_id, ghs_code)
)
"""
            )

            rows = []
            for row in reader:
                rows.append(
                    [
                        str(uuid.uuid4()),
                        None,  # code
                        "General",
                        "sds_phrases_PERFEKT.csv",
                        "active",
                    ]
                    + [row.get(col, "") for col in phrase_columns]
                )

            value_placeholders = ",".join(["?"] * (5 + len(phrase_columns)))
            column_sql = "id,code,type,source,status," + ",".join(phrase_columns)
            cursor.executemany(
                f"INSERT INTO phrases ({column_sql}) VALUES ({value_placeholders})",
                rows,
            )

            # Core indices
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_phrases_id ON phrases(id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_phrases_en_original ON phrases(en_original)")

            # Create column indices for fast lookup in translation flow.
            for col in phrase_columns:
                cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_phrases_{col} ON phrases({col})")

            conn.commit()
        finally:
            conn.close()


def ensure_translation_database_ready():
    """
    Ensure runtime DB exists and is synchronized with the current CSV source.
    Regenerates DB when CSV is newer than DB or DB is missing.
    """
    csv_path = CSV_TRANSLATION_SOURCE
    db_path = CSV_TRANSLATION_DB_PATH

    if not os.path.exists(csv_path):
        # Keep old behavior possible when CSV is not present.
        return

    rebuild_needed = not os.path.exists(db_path)
    if not rebuild_needed:
        rebuild_needed = os.path.getmtime(csv_path) > os.path.getmtime(db_path)

    if rebuild_needed:
        _create_db_from_translation_csv(csv_path, db_path)

DATABASE_OPTIONS = {
    'sds_phrases_perfekt': {
        'path': CSV_TRANSLATION_DB_PATH,
        'name': 'SDS PERFEKT CSV Database',
        'description': 'Automatisch erzeugt aus sds_phrases_PERFEKT.csv (table phrases)'
    }
}
DEFAULT_DB_PATH = CSV_TRANSLATION_DB_PATH

# Prepare default translation DB on module import so app startup uses latest CSV translations.
ensure_translation_database_ready()


def get_db_path():
    with _db_lock:
        return _current_db_path

def set_db_path(db_key):
    global _current_db_path
    with _db_lock:
        if db_key in DATABASE_OPTIONS:
            new_path = DATABASE_OPTIONS[db_key]['path']
            if os.path.exists(new_path):
                _current_db_path = new_path
                return True, f"Database switched to: {DATABASE_OPTIONS[db_key]['name']}"
            else:
                if os.path.exists(DEFAULT_DB_PATH):
                    _current_db_path = DEFAULT_DB_PATH
                    return False, f"Database '{new_path}' not found, fallback to Legacy Database"
                else:
                    return False, f"Database '{new_path}' not found and no fallback available"
        return False, "Invalid database key"

def get_available_databases():
    available = {}
    for key, config in DATABASE_OPTIONS.items():
        available[key] = {
            **config,
            'exists': os.path.exists(config['path']),
            'active': get_db_path() == config['path']
        }
    return available

def get_db_connection():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def get_current_db_info():
    current_path = get_db_path()
    for key, config in DATABASE_OPTIONS.items():
        if config['path'] == current_path:
            return {
                'key': key,
                'name': config['name'],
                'description': config['description'],
                'path': current_path
            }
    return {
        'key': 'unknown',
        'name': 'Unknown Database',
        'description': 'Custom database path',
        'path': current_path
    }


def ensure_database_indices(db_path=None):
    """
    Create database indices for better query performance.
    This function is safe to call multiple times - indices are only created if they don't exist.
    
    Args:
        db_path: Optional path to database. If None, uses current database.
    
    Returns:
        dict with information about created indices
    """
    if db_path is None:
        db_path = get_db_path()
    
    if not os.path.exists(db_path):
        return {'success': False, 'error': 'Database not found'}
    
    indices_to_create = [
        # Index on en_original for searching
        ('idx_phrases_en_original', 'CREATE INDEX IF NOT EXISTS idx_phrases_en_original ON phrases(en_original)'),
        # Index on id for faster lookups
        ('idx_phrases_id', 'CREATE INDEX IF NOT EXISTS idx_phrases_id ON phrases(id)'),
    ]
    
    # Add indices for each language column
    language_columns = [
        'de_original', 'fr_original', 'es_original', 'it_original', 'nl_original',
        'pl_original', 'sv_original', 'da_original', 'fi_original', 'el_original',
        'cs_original', 'hu_original', 'ro_original', 'bg_original', 'sk_original',
        'sl_original', 'et_original', 'lv_original', 'lt_original', 'hr_original',
        'pt_original', 'no_original', 'is_original'
    ]
    
    for col in language_columns:
        indices_to_create.append((
            f'idx_phrases_{col}',
            f'CREATE INDEX IF NOT EXISTS idx_phrases_{col} ON phrases({col})'
        ))
    
    created_indices = []
    errors = []
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        for index_name, create_sql in indices_to_create:
            try:
                cursor.execute(create_sql)
                created_indices.append(index_name)
            except sqlite3.Error as e:
                errors.append(f"Error creating {index_name}: {e}")
        
        conn.commit()
        
        return {
            'success': True,
            'indices_created': len(created_indices),
            'indices': created_indices,
            'errors': errors
        }
    except sqlite3.Error as e:
        return {'success': False, 'error': str(e)}
    finally:
        conn.close()


def get_database_stats(db_path=None):
    """
    Get statistics about the database including index information.
    
    Args:
        db_path: Optional path to database. If None, uses current database.
    
    Returns:
        dict with database statistics
    """
    if db_path is None:
        db_path = get_db_path()
    
    if not os.path.exists(db_path):
        return {'success': False, 'error': 'Database not found'}
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get table info
        cursor.execute("SELECT COUNT(*) FROM phrases")
        phrase_count = cursor.fetchone()[0]
        
        # Get index info
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
        indices = [row[0] for row in cursor.fetchall()]
        
        # Get database size
        db_size = os.path.getsize(db_path)
        
        return {
            'success': True,
            'phrase_count': phrase_count,
            'indices': indices,
            'index_count': len(indices),
            'db_size_bytes': db_size,
            'db_size_mb': round(db_size / (1024 * 1024), 2)
        }
    except sqlite3.Error as e:
        return {'success': False, 'error': str(e)}
    finally:
        conn.close()
