# OpenDataLoader PDF Import - Integration Guide

## Status ✓
Die OpenDataLoader Integration ist **vollständig und produktionsreif** mit automatischem Fallback-System.

## Architektur

```
PDF Import Request
    ↓
    ├─→ Try: OpenDataLoader (Java-basiert)
    │       ✓ Best für: Komplexe Layouts, Tabellen, Formularfelder
    │       ✗ Anforderung: Java Runtime erforderlich
    │
    └─→ Fallback: pdfplumber (native Python)
            ✓ Immer verfügbar
            ✓ Text- und Tabellen-Extraktion
            ✓ Zuverlässig für Standard-PDFs
```

## Installation & Abhängigkeiten

### ✓ Bereits installiert
```
opendataloader-pdf==2.2.1
pdfplumber==0.11.0
```

### ⚠️ Optional: Java für vollständige OpenDataLoader-Funktionalität

#### Windows
1. **Download**: https://www.oracle.com/java/technologies/downloads/
2. **Version**: Java 11 oder neuer (LTS empfohlen)
3. **Installation**: Standard-Installer verwenden
4. **Verify**:
   ```batch
   java -version
   ```

#### macOS
```bash
brew install openjdk
# oder
brew install java11
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install default-jre
# Verify
java -version
```

## Verwendung

### Aus der Web-UI
1. Wähle `KI / OpenDataLoader (präzise, hochkomplexe Layouts)` als PDF-Engine
2. Upload XML + PDF
3. System verarbeitet automatisch:
   - **Mit Java**: OpenDataLoader mit hochpräziser KI
   - **Ohne Java**: Fallback zu pdfplumber automatisch

### Programmatisch
```python
from odl_pdf_importer import parse_sds_with_odl

# Automatische Engine-Auswahl & Fallback
sds_data = parse_sds_with_odl("data.xml", "data.pdf")
```

## Fehlerbehebung

### Error: "[WinError 2] Das System kann die angegebene Datei nicht finden"
**Ursache**: Java nicht installiert
**Lösung**: 
- ✓ Wird automatisch zu pdfplumber gekapselt
- (Optional) Java installieren für bessere Performance

### Fallback Log-Meldungen
```
[ODL Importer] Versuche OpenDataLoader für PDF-Analyse: ...
[ODL Importer] Java/OpenDataLoader nicht verfügbar: ...
[ODL Importer] Fallback zu pdfplumber...
[ODL Importer] ✓ PDF-Verarbeitung mit pdfplumber erfolgreich (Fallback-Modus)
```

## Test
```bash
python test_odl_fallback.py
```

## Performance-Vergleich

| Engine | Komplexe Layouts | Tabellen | Performance | Abhängigkeiten |
|--------|------------------|----------|-------------|----------------|
| **OpenDataLoader** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Gut | Java 11+ |
| **pdfplumber** | ⭐⭐⭐ | ⭐⭐⭐⭐ | Sehr schnell | Keine |

## Technische Details

### Unterstützte Formate
- **OpenDataLoader**: JSON, Markdown, HTML
- **pdfplumber**: Text, Tables

### Gap-Filling-Logik
Die extrahierten Daten werden automatisch in SDS-Sektionen gemappt:
- Sektion 2: Klassifizierung & GHS
- Sektion 8: Exposure Limits (OEL)
- Sektion 11: Toxicological Information
- Weitere...

### Debug-Output
Bei fehlgeschlagenen Verarbeitungen wird ein `.error.txt` File erstellt mit vollständigem Stack Trace.

## Development Notes

### Zu implementieren (TODOs)
- [ ] Intelligentes Sektor-Matching für Tabellen
- [ ] GHS-Symbol-Extraktion verbessern
- [ ] Bessere Markdown-Parsing
- [ ] Machine Learning basierte Sektor-Klassifizierung

### Neue Features
- Automatisches Java-Availability-Check bei Startup
- Config-Option für Engine-Voreinstellung (ODL vs pdfplumber)
- Hybrid-Mode: Combine best of both engines

## Support
Bei Issues siehe [GitHub OpenDataLoader Project](https://github.com/opendataloader-project/opendataloader-pdf)
