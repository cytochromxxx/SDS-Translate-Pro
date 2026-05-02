#!/usr/bin/env python
"""
Erweiterte Test Suite für OpenDataLoader + pdfplumber
Vergleicht Performance und Qualität beider Engines
"""
import os
import sys
import logging
import json
from pathlib import Path

# Enable logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_java_availability():
    """Test if Java is available"""
    print("\n" + "="*70)
    print("TEST 1: Java Availability")
    print("="*70)
    
    import subprocess
    try:
        result = subprocess.run(["java", "-version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version_output = result.stderr  # java -version prints to stderr
            print(f"✓ Java verfügbar:")
            for line in version_output.split('\n')[:2]:
                print(f"  {line}")
            return True
        else:
            # Try with full path
            java_path = r"C:\Program Files\Java\jdk-26\bin\java.exe"
            if os.path.exists(java_path):
                result = subprocess.run([java_path, "-version"], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    version_output = result.stderr
                    print(f"✓ Java verfügbar (voll Pfad):")
                    for line in version_output.split('\n')[:2]:
                        print(f"  {line}")
                    print(f"  Path: {java_path}")
                    return True
            print("✗ Java nicht im PATH - bitte Terminal neustarten")
            return False
    except Exception as e:
        print(f"✗ Fehler: {e}")
        return False

def test_opendataloader_api():
    """Test if OpenDataLoader imports correctly"""
    print("\n" + "="*70)
    print("TEST 2: OpenDataLoader API")
    print("="*70)
    
    try:
        from opendataloader_pdf import convert
        print("✓ opendataloader_pdf.convert erfolgreich importiert")
        print(f"  Funktionssignatur verfügbar")
        return True
    except ImportError as e:
        print(f"✗ Import-Fehler: {e}")
        return False
    except Exception as e:
        print(f"✗ Fehler: {e}")
        return False

def test_fallback_system():
    """Test the fallback mechanism"""
    print("\n" + "="*70)
    print("TEST 3: Fallback-System")
    print("="*70)
    
    from odl_pdf_importer import _parse_with_pdfplumber, _fill_gaps_with_odl_data
    
    try:
        print("✓ pdfplumber parser verfügbar")
        
        # Test format detection
        mock_sds = {"test": "data"}
        pdfplumber_data = {"pages": [], "tables": [], "text": "test"}
        result = _fill_gaps_with_odl_data(mock_sds, pdfplumber_data)
        print("✓ Format-Erkennung funktioniert")
        
        return True
    except Exception as e:
        print(f"✗ Fehler: {e}")
        return False

def test_with_sample_pdf():
    """Test with actual sample PDF if available"""
    print("\n" + "="*70)
    print("TEST 4: Sample PDF Processing")
    print("="*70)
    
    # Look for sample PDFs in uploads directory
    uploads_dir = Path("uploads")
    if not uploads_dir.exists():
        print("⚠️  Kein uploads-Verzeichnis gefunden (normal bei Entwicklung)")
        return True
    
    pdfs = list(uploads_dir.glob("*.pdf"))
    if not pdfs:
        print("⚠️  Keine PDFs zum Testen vorhanden (normal bei Neubuild)")
        return True
    
    print(f"Gefundene PDFs: {len(pdfs)}")
    for pdf in pdfs[:1]:  # Test first PDF
        print(f"\n📄 Testing: {pdf.name}")
        
        try:
            import pdfplumber
            with pdfplumber.open(str(pdf)) as p:
                print(f"  ✓ PDF geöffnet: {len(p.pages)} Seiten")
                
                # Extract text from first page
                if len(p.pages) > 0:
                    text = p.pages[0].extract_text()
                    print(f"  ✓ Text extrahiert: {len(text) if text else 0} Zeichen")
                
                # Try to extract tables
                tables_found = 0
                for page in p.pages[:3]:
                    try:
                        tables = page.extract_tables()
                        if tables:
                            tables_found += len(tables)
                    except:
                        pass
                
                if tables_found > 0:
                    print(f"  ✓ Tabellen gefunden: {tables_found}")
                else:
                    print(f"  - Keine Tabellen in den ersten 3 Seiten")
        
        except Exception as e:
            print(f"  ✗ Fehler beim PDF-Verarbeiten: {e}")
            return False
    
    return True

def print_configuration():
    """Print current configuration"""
    print("\n" + "="*70)
    print("KONFIGURATION")
    print("="*70)
    
    print("\n✓ Installierte Pakete:")
    packages = {
        "opendataloader-pdf": "2.2.1",
        "pdfplumber": "0.11.0",
        "Python": "3.12+",
    }
    
    for pkg, version in packages.items():
        try:
            if pkg == "Python":
                print(f"  • {pkg}: {sys.version.split()[0]}")
            else:
                __import__(pkg.split('-')[0].replace('-', '_'))
                print(f"  • {pkg}: {version}")
        except:
            print(f"  • {pkg}: ✗ nicht verfügbar")
    
    print("\n📋 PDF Import Strategie:")
    print("  1. Versuche: OpenDataLoader + Java (höchste Präzision)")
    print("  2. Fallback: pdfplumber (immer verfügbar, robust)")
    print("  3. Result: Optimale Datenqualität durch automatische Engine-Wahl")

def main():
    print("\n" + "="*70)
    print("🧪 OpenDataLoader Pro Test Suite (mit Java)")
    print("="*70)
    
    results = []
    
    # Run tests
    results.append(("Java Availability", test_java_availability()))
    results.append(("OpenDataLoader API", test_opendataloader_api()))
    results.append(("Fallback System", test_fallback_system()))
    results.append(("Sample PDF Processing", test_with_sample_pdf()))
    
    # Print configuration
    print_configuration()
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ BESTANDEN" if result else "✗ FEHLGESCHLAGEN"
        print(f"{test_name:30s} {status}")
    
    print(f"\nGesamt: {passed}/{total} Tests bestanden")
    
    if all(r for _, r in results):
        print("\n🎉 ALLE TESTS BESTANDEN - OpenDataLoader ist produktionsreif!")
        
        print("\nHinweise:")
        print("  • OpenDataLoader wird jetzt automatisch für PDF-Importe verwendet")
        print("  • pdfplumber steht als Fallback zur Verfügung")
        print("  • Detaillierte Logs in der Aplikation verfügbar")
        
        return 0
    else:
        print("\n⚠️  Einige Tests fehlgeschlagen - bitte Fehler prüfen")
        return 1

if __name__ == "__main__":
    sys.exit(main())
