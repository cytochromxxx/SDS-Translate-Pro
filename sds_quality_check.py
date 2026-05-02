# file: sds_quality_check.py
import json, re, pathlib

GLOSSARY = {
    "Slackmedel": "Släckmedel",
    "beredning": "blandning",
    # … weitere Fachbegriffe …
}

ENGLISH_RE = re.compile(r"[A-Za-z]{2,}")

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def replace_terms(text):
    for src, tgt in GLOSSARY.items():
        text = text.replace(src, tgt)
    return text

def check_section(section, txt):
    errors = []
    # 1. Englische Reste
    if ENGLISH_RE.search(txt):
        errors.append("Englische Reste gefunden")
    # 2. Fehlende °C‑Angabe
    if "°C" not in txt and any(k in section.lower() for k in ["flampunkt", "autoignition", "smältpunkt"]):
        errors.append("°C‑Einheit fehlt")
    # 3. Doppelte Wörter
    dup = re.search(r"\b(\w+)\s+\1\b", txt, flags=re.IGNORECASE)
    if dup:
        errors.append(f"Doppelwort: {dup.group(1)}")
    return errors

def main(json_path):
    data = load_json(json_path)
    report = {}
    for sec, content in data.get("sections", {}).items():
        txt = replace_terms(content.get("text", ""))
        report[sec] = check_section(sec, txt)
    # Ausgabe als JSON‑Report
    out_path = pathlib.Path(json_path).with_name("quality_report.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print("Qualitäts‑Report geschrieben nach:", out_path)

if __name__ == "__main__":
    import sys
    main(sys.argv[1])
