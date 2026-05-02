import sqlite3
import csv
import uuid
import os

db_path = 'sds_phrases_new.db'
csv_path = 'routes/sds_phrases.csv'

if os.path.exists(db_path):
    os.remove(db_path)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create table
cursor.execute("""
CREATE TABLE phrases (
    id TEXT PRIMARY KEY,
    code TEXT,
    type TEXT,
    source TEXT,
    status TEXT,
    bg_original TEXT,
    cs_original TEXT,
    da_original TEXT,
    de_original TEXT,
    el_original TEXT,
    en_original TEXT,
    es_original TEXT,
    et_original TEXT,
    fi_original TEXT,
    fr_original TEXT,
    hr_original TEXT,
    hu_original TEXT,
    it_original TEXT,
    lt_original TEXT,
    lv_original TEXT,
    mt_original TEXT,
    nl_original TEXT,
    pl_original TEXT,
    pt_original TEXT,
    ro_original TEXT,
    sk_original TEXT,
    sl_original TEXT,
    sv_original TEXT,
    no_original TEXT,
    is_original TEXT
)
""")

# Create standard tables that might be queried
cursor.execute("""
CREATE TABLE ghs_pictograms (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    hazard_class TEXT,
    svg_path TEXT,
    png_path TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_url TEXT
);
""")

cursor.execute("""
CREATE TABLE sds_pictograms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sds_id TEXT NOT NULL,
    ghs_code TEXT NOT NULL,
    position INTEGER DEFAULT 0,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ghs_code) REFERENCES ghs_pictograms(code),
    UNIQUE(sds_id, ghs_code)
);
""")

with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.reader(f, delimiter=';')
    headers = next(reader)
    
    # We map csv columns to table columns
    # csv columns: en_original;bg_original;...
    # DB columns want matching names
    col_names = headers
    
    # prepare insert statement
    placeholders = ','.join(['?'] * (len(col_names) + 5))
    columns_str = 'id,code,type,source,status,' + ','.join(col_names)
    
    sql = f"INSERT INTO phrases ({columns_str}) VALUES ({placeholders})"
    
    batch = []
    for row in reader:
        # pad row if necessary
        while len(row) < len(col_names):
            row.append('')
            
        # extract data
        id_val = str(uuid.uuid4())
        code_val = None
        type_val = 'General'
        source_val = 'csv_import'
        status_val = 'active'
        
        batch.append([id_val, code_val, type_val, source_val, status_val] + row)
        
    cursor.executemany(sql, batch)

# Create indices
cursor.execute("CREATE INDEX idx_phrases_code ON phrases(code);")
cursor.execute("CREATE INDEX idx_phrases_type ON phrases(type);")
cursor.execute("CREATE INDEX idx_phrases_en ON phrases(en_original);")
cursor.execute("CREATE INDEX idx_phrases_status ON phrases(status);")

for lang in col_names:
    cursor.execute(f"CREATE INDEX idx_phrases_{lang} ON phrases({lang});")

conn.commit()
conn.close()

print(f"Successfully converted {csv_path} to {db_path} with {len(batch)} records.")
