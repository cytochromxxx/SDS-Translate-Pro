# Konzept zur grundlegenden Überarbeitung des Mapping-Editors

Dieses Dokument beschreibt eine vollständige Neugestaltung des Mapping-Editors im Menüpunkt "Mapping". Das Ziel ist es, den Prozess der Zuordnung von Rohdaten (XML/JSON/PDF-Extraktionen) zu den Platzhaltern im HTML-Template intuitiv, visuell und fehlerfrei zu gestalten.

## 1. Aktuelle Schwachstellen

Das derzeitige Mapping-System weist mehrere Einschränkungen auf, die es für den Nutzer schwer bedienbar machen:
*   **Manuelle Eingabe:** Der Nutzer muss sowohl den XML-Pfad (`Woher?`) als auch die Template-Variable (`Wohin?`) händisch als Text eingeben. Das erfordert tiefes technisches Wissen über die Datenstruktur und das Template und ist extrem fehleranfällig (Tippfehler).
*   **Fehlende Übersicht:** Es gibt keine visuelle Rückmeldung darüber, welche Platzhalter im Template überhaupt existieren und welche noch nicht gemappt wurden.
*   **Fehlender Kontext:** Es ist unklar, welche realen Daten sich hinter einem XPath oder JSON-Key verbergen, bis man einen Test-Export durchführt.
*   **Komplexität bei Listen:** Das Mapping von iterierbaren Elementen (z. B. Inhaltsstoffe in Sektion 3, Gefahrenhinweise in Sektion 2) ist als einfaches Text-Mapping oft unzureichend.

## 2. Das neue UX/UI-Konzept: Visuelles Mapping

Der neue Editor sollte sich von einer starren Tabelle zu einem interaktiven, visuellen Tool wandeln. 

### Kern-Ideen:
1.  **Zwei-Spalten-Ansicht (Dual-Pane):** 
    *   **Linke Spalte (Datenquelle):** Zeigt die Struktur der importierten Daten (XML/JSON) als aufklappbaren Baum (Tree-View) an. 
    *   **Rechte Spalte (Template):** Zeigt alle verfügbaren Platzhalter des HTML-Templates, gruppiert nach Sektionen.
2.  **Drag & Drop / Klick-Zuweisung:** Der Nutzer zieht einfach ein Feld von links nach rechts auf den passenden Platzhalter.
3.  **Live-Daten Vorschau:** Neben jedem Feld im Datenbaum wird ein Beispieldatum aus einer realen, hochgeladenen Datei (z. B. "Acetone", "H319") angezeigt.
4.  **Auto-Extraktion der Template-Variablen:** Das System liest die `SDS_PERFEKT_TEMPLATE.html` automatisch aus und listet alle gefundenen Jinja-Variablen (`{{ variable }}`) auf. Der Nutzer muss keine Variablennamen mehr tippen.

### Layout-Skizze (Wireframe)

```text
+-----------------------------------------------------------------------------+
| 💡 Schritt 1: Laden Sie ein XML/JSON als Referenz für die Datenstruktur hoch |
| [ Datei auswählen... ] (Aktuell geladen: SDS_Beispiel_V5.xml)               |
+-----------------------------------------------------------------------------+
|                                      |                                      |
| 🗂️ DATENQUELLE (Woher?)              | 📄 TEMPLATE-PLATZHALTER (Wohin?)     |
| (Beispieldaten aus Referenzdatei)    | (Automatisch aus Template gelesen)   |
|                                      |                                      |
| 🔽 Product                           | 🔽 Sektion 1: Identifikation         |
|   ├── Name          ["Acetone"]  ----|----> {{ section_1.product_name }}    |
|   └── ItemNo        ["123-45"]       |   [ ] {{ section_1.supplier_name }}  |
| 🔽 Hazards                           |                                      |
|   ├── HazardStatement ["H319"]   ----|----> {% for h in section_2.hazards %}|
|   └── Precautionary   ["P280"]       |                                      |
|                                      |                                      |
+-----------------------------------------------------------------------------+
| [🔄 Mappings zurücksetzen]                             [💾 Mappings speichern] |
+-----------------------------------------------------------------------------+
```

## 3. Neue Features und Funktionen

1.  **Referenzdatei-Upload:** Der Nutzer kann ein typisches XML oder JSON hochladen. Das System parst dieses Dokument nicht für eine Übersetzung, sondern generiert daraus das "Schema" für die linke Spalte.
2.  **Visuelles Feedback (Ampelsystem):**
    *   🔴 Rot: Ein Template-Platzhalter hat noch keine Datenquelle zugewiesen.
    *   🟢 Grün: Platzhalter ist erfolgreich gemappt.
    *   🟡 Gelb: Datenquelle im XML hat sich geändert (Pfad existiert im Referenz-XML nicht mehr).
3.  **Intelligentes Auto-Mapping:** Ein Button "Automatisch zuordnen" vergleicht Variablennamen und XML-Keys (z. B. `product_name` mit `Product/Name`) und schlägt Zuordnungen vor.
4.  **Umgang mit Listen/Arrays:** Wenn der Nutzer ein Array (z. B. `Hazards/HazardStatement`) auf einen For-Loop (`{% for h in section_2.hazards %}`) im Template zieht, erkennt das System dies als 1:n Mapping.

## 4. Technische Umsetzungsschritte

Um dieses Konzept zu realisieren, sind folgende technische Anpassungen nötig:

### Backend (`routes/main.py` & neue Module)
1.  **Template Parser (`/api/mappings/scan_template`):** 
    Ein neuer Endpoint, der die Datei `SDS_PERFEKT_TEMPLATE.html` öffnet und mittels regulärer Ausdrücke (Regex) oder einem Jinja2-AST-Parser alle Variablen (`{{ ... }}`) und Schleifen (`{% for ... %}`) extrahiert und als strukturierten JSON-Baum zurückgibt.
2.  **Referenzdaten-Scanner (`/api/mappings/scan_reference`):**
    Ein Endpoint, der eine XML/JSON-Datei entgegennimmt und in einen generischen Pfad-Baum (JSON/XPath) samt Beispielwerten umwandelt.
3.  **Mapping-Speicher:** Die Struktur der `mappings.json` wird erweitert. Anstatt flacher Arrays sollte sie die genaue Relation `Template-Variable <-> Datenpfad` mit Typisierung (String, Array, Object) speichern.

### Frontend (`static/js/main.js` & `templates/index.html`)
1.  **DOM-Struktur:** Das `#mapping-tab` wird komplett umgebaut. Statt einer simplen Tabelle (wie bisher) werden zwei `div`-Container für die Dual-Pane-Ansicht erstellt.
2.  **JavaScript UI-Library:** Zur Umsetzung des Drag & Drop und der Tree-Views empfiehlt sich ein visuelles Tree-View-Plugin oder leichtes Drag-and-Drop (HTML5 Drag/Drop API), um den Entwicklungsaufwand gering zu halten.
3.  **Dynamisches Rendering:** Die Funktion `renderMappings()` wird durch zwei neue Funktionen ersetzt: `renderDataTree(data)` und `renderTemplateTree(templateVars)`. Bei jeder Änderung (Drag & Drop) wird ein Mapping-Objekt aktualisiert und visuell (z.B. durch Farben oder verbundene Linien) dargestellt.

## Fazit

Mit diesem neuen Ansatz transformiert sich der Mapping-Prozess von einer Aufgabe für Entwickler zu einer visuellen "Steckbrett"-Aufgabe für Endanwender. Der Nutzer sieht sofort, wo Daten fehlen, welche Platzhalter das Template bietet und kann Fehler durch Pfad-Änderungen in Lieferanten-XMLs (z. B. neue Formate vom Open DataLoader) in Sekunden diagnostizieren und reparieren.