import sqlite3
import os
import threading

_db_lock = threading.Lock()
_current_db_path = "phrases_library.db"

DATABASE_OPTIONS = {
    'legacy': {
        'path': 'phrases_library.db',
        'name': 'Legacy Database (Default)',
        'description': 'Bisherige Standard-Datenbank mit allen Phrasen'
    },
    'euphrac_excel': {
        'path': 'euphrac_excel_phrases.db',
        'name': 'EUH Excel Phrases',
        'description': 'EUH-Präfix-Phrasen aus Excel-Importen'
    },
    'sds_only': {
        'path': 'phrases_from_sds_only.db',
        'name': 'SDS-Only Phrases',
        'description': 'Rein aus bestehenden SDS-Dokumenten extrahiert'
    },
    'verified': {
        'path': 'phrases_library_verified.db',
        'name': 'Verified Phrases',
        'description': 'Menschlich verifizierte und freigegebene Phrasen'
    },
    'extracted': {
        'path': 'sds_phrases_extracted.db',
        'name': 'Extracted Raw Phrases',
        'description': 'Automatisch extrahierte Rohphrasen aus SDS-Parsing'
    }
}
DEFAULT_DB_PATH = "phrases_library.db"


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
