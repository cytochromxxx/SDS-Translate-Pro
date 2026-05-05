#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GHS Pictogram Management System
Handles download, caching, and management of GHS pictograms from BGN Symbolbibliothek
"""

import os
import sqlite3
import requests
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from database import get_db_path

# BGN Symbolbibliothek URL patterns
BGN_BASE_URL = "https://bgn-branchenwissen.de/symbolbibliothek/gefahrstoffe-ghs"

# GHS Pictogram definitions with codes and descriptions
GHS_PICTOGRAMS = {
    'GHS01': {'name': 'Explosive', 'description': 'Explosive substances', 'hazard_class': 'Explosive'},
    'GHS02': {'name': 'Flammable', 'description': 'Flammable substances', 'hazard_class': 'Flammable'},
    'GHS03': {'name': 'Oxidizing', 'description': 'Oxidizing substances', 'hazard_class': 'Oxidizing'},
    'GHS04': {'name': 'Compressed Gas', 'description': 'Compressed gases', 'hazard_class': 'Compressed Gas'},
    'GHS05': {'name': 'Corrosive', 'description': 'Corrosive substances', 'hazard_class': 'Corrosive'},
    'GHS06': {'name': 'Toxic', 'description': 'Toxic substances', 'hazard_class': 'Toxic'},
    'GHS07': {'name': 'Harmful', 'description': 'Harmful substances', 'hazard_class': 'Harmful'},
    'GHS08': {'name': 'Health Hazard', 'description': 'Serious health hazards', 'hazard_class': 'Health Hazard'},
    'GHS09': {'name': 'Environmental Hazard', 'description': 'Environmental hazards', 'hazard_class': 'Environmental Hazard'},
}

class GHSPictogramManager:
    def __init__(self, cache_dir='ghs_cache'):
        self.db_path = get_db_path()
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.init_database()
    
    def init_database(self):
        """Initialize database tables for GHS pictograms."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table for available pictograms
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ghs_pictograms (
                code TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                hazard_class TEXT,
                svg_path TEXT,
                png_path TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source_url TEXT
            )
        ''')
        
        # Table for SDS documents with pictogram associations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sds_pictograms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sds_id TEXT NOT NULL,
                ghs_code TEXT NOT NULL,
                position INTEGER DEFAULT 0,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ghs_code) REFERENCES ghs_pictograms(code),
                UNIQUE(sds_id, ghs_code)
            )
        ''')
        
        # Initialize default pictograms
        self._init_default_pictograms(cursor)
        
        conn.commit()
        conn.close()
    
    def _init_default_pictograms(self, cursor):
        """Initialize default GHS pictogram entries and check for local high-quality icons."""
        import shutil
        from pathlib import Path
        
        # Check for local 'symbole' directory to import high-quality icons
        # We'll use this to override the default cached images
        library_path = Path(r"c:\Users\Flo\Coding\agentzero-sdstranslate\backup_sds_translate_latest\FINAL\symbole")
        
        for code, data in GHS_PICTOGRAMS.items():
            # Standard entry
            cursor.execute('''
                INSERT OR IGNORE INTO ghs_pictograms (code, name, description, hazard_class)
                VALUES (?, ?, ?, ?)
            ''', (code, data['name'], data['description'], data['hazard_class']))
            
            # Map GHS01 -> GHS_01_gr.gif
            num = code.replace("GHS0", "")
            if len(num) == 1:
                lib_filename = f"GHS_0{num}_gr.gif"
            else:
                lib_filename = f"GHS_{num}_gr.gif"
                
            lib_file = library_path / lib_filename
            if lib_file.exists():
                cache_file = self.cache_dir / f"{code}.gif"
                # Copy to cache if not already there or to update
                try:
                    shutil.copy2(lib_file, cache_file)
                    cursor.execute('''
                        UPDATE ghs_pictograms 
                        SET png_path = ?, last_updated = CURRENT_TIMESTAMP
                        WHERE code = ?
                    ''', (str(cache_file), code))
                except Exception as e:
                    print(f"Error copying high-quality GHS icon {code}: {e}")

    def download_pictogram(self, code, force_refresh=False):
        """
        Download GHS pictogram from BGN or alternative source.
        Returns True if successful, False otherwise.
        """
        if code not in GHS_PICTOGRAMS:
            return False
        
        # Check if we already have it (either downloaded or copied from library)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT png_path FROM ghs_pictograms WHERE code = ?', (code,))
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0] and os.path.exists(row[0]) and not force_refresh:
            return True
        
        # Standard download/generation logic
        svg_path = self.cache_dir / f"{code}.svg"
        if not force_refresh and svg_path.exists():
            self._update_pictogram_paths(code, str(svg_path), None)
            return True
        
        success = self._generate_placeholder_pictogram(code, svg_path)
        if success:
            self._update_pictogram_paths(code, str(svg_path), None)
        return success
    
    def _generate_placeholder_pictogram(self, code, svg_path):
        """Generate a placeholder SVG pictogram (for development)."""
        colors = {
            'GHS01': '#FF0000', 'GHS02': '#FF6600', 'GHS03': '#FF9900',
            'GHS04': '#0099FF', 'GHS05': '#FF0000', 'GHS06': '#FF0000',
            'GHS07': '#FF9900', 'GHS08': '#FF0000', 'GHS09': '#00CC00',
        }
        
        color = colors.get(code, '#666666')
        name = GHS_PICTOGRAMS[code]['name']
        
        svg_content = f'''<svg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
            <rect width="100" height="100" fill="{color}"/>
            <text x="50" y="50" dominant-baseline="middle" text-anchor="middle" fill="white" font-size="12">{code}</text>
        </svg>'''
        
        try:
            with open(svg_path, 'w', encoding='utf-8') as f:
                f.write(svg_content)
            return True
        except Exception as e:
            print(f"Error generating pictogram {code}: {e}")
            return False
    
    def _update_pictogram_paths(self, code, svg_path, png_path):
        """Update database with pictogram file paths."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE ghs_pictograms 
            SET svg_path = ?, png_path = ?, last_updated = CURRENT_TIMESTAMP
            WHERE code = ?
        ''', (svg_path, png_path, code))
        
        conn.commit()
        conn.close()
    
    def get_all_pictograms(self):
        """Get all available GHS pictograms."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM ghs_pictograms ORDER BY code')
        pictograms = [dict(row) for row in cursor.fetchall()]
        
        for p in pictograms:
            if not p['svg_path'] or not os.path.exists(p['svg_path']):
                self.download_pictogram(p['code'], force_refresh=True)
                # Re-fetch the updated pictogram data
                updated_p = self.get_pictogram_by_code(p['code'])
                p.update(updated_p)

        conn.close()
        return pictograms
    
    def get_pictogram_by_code(self, code):
        """Get specific pictogram by code."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM ghs_pictograms WHERE code = ?', (code,))
        row = cursor.fetchone()
        
        conn.close()
        return dict(row) if row else None
    
    def get_sds_pictograms(self, sds_id):
        """Get all pictograms assigned to an SDS document."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT p.*, s.position FROM ghs_pictograms p
            JOIN sds_pictograms s ON p.code = s.ghs_code
            WHERE s.sds_id = ?
            ORDER BY s.position
        ''', (sds_id,))
        
        pictograms = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return pictograms
    
    def add_pictogram_to_sds(self, sds_id, ghs_code, position=None):
        """
        Add a pictogram to an SDS document.
        Max 3 pictograms allowed.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM sds_pictograms WHERE sds_id = ?', (sds_id,))
        count = cursor.fetchone()[0]
        
        if count >= 3:
            conn.close()
            return False, "Maximum of 3 pictograms allowed"
        
        cursor.execute('SELECT id FROM sds_pictograms WHERE sds_id = ? AND ghs_code = ?', 
                      (sds_id, ghs_code))
        if cursor.fetchone():
            conn.close()
            return False, "Pictogram already added to this SDS"
        
        if position is None:
            position = count
        
        try:
            cursor.execute('''
                INSERT INTO sds_pictograms (sds_id, ghs_code, position)
                VALUES (?, ?, ?)
            ''', (sds_id, ghs_code, position))
            conn.commit()
            conn.close()
            return True, "Pictogram added successfully"
        except Exception as e:
            conn.close()
            return False, f"Database error: {str(e)}"
    
    def remove_pictogram_from_sds(self, sds_id, ghs_code):
        """Remove a pictogram from an SDS document."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM sds_pictograms WHERE sds_id = ? AND ghs_code = ?',
                      (sds_id, ghs_code))
        
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return deleted
    
    def update_pictogram_positions(self, sds_id, ordered_codes):
        """Update positions of pictograms for an SDS."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            for position, code in enumerate(ordered_codes):
                cursor.execute('''
                    UPDATE sds_pictograms 
                    SET position = ?
                    WHERE sds_id = ? AND ghs_code = ?
                ''', (position, sds_id, code))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            conn.close()
            return False
    
    def refresh_cache(self):
        """Refresh all pictogram caches."""
        results = {}
        for code in GHS_PICTOGRAMS.keys():
            success = self.download_pictogram(code, force_refresh=True)
            results[code] = 'success' if success else 'failed'
        return results

if __name__ == '__main__':
    manager = GHSPictogramManager()
    print("Initializing GHS Pictograms...")
    for code in GHS_PICTOGRAMS.keys():
        success = manager.download_pictogram(code)
        status = "OK" if success else "FAIL"
        print(f"  [{status}] {code}: {GHS_PICTOGRAMS[code]['name']}")
    print("\nAll pictograms initialized!")
    print(f"Cache directory: {manager.cache_dir.absolute()}")
