import fitz
import re

pdf_path = r"c:\Users\Flo\Downloads\SDS-Translate-Pro-master\SDS\downloads\SDB-0332-GB-EN.pdf"

doc = fitz.open(pdf_path)
full_text = ""
for page in doc:
    full_text += page.get_text()
doc.close()

# Find section 4
section_markers = {}
for match in re.finditer(r'SECTION\s+(\d+)|section\s+(\d+)', full_text, re.IGNORECASE):
    section_num = int(match.group(1) or match.group(2))
    section_markers[section_num] = match.start()

print(f"Found sections: {sorted(section_markers.keys())}")

if 4 in section_markers:
    start = section_markers[4]
    next_section = section_markers.get(5, len(full_text))
    section_4_text = full_text[start:next_section]
    
    print(f"\n=== Section 4 (first 1000 chars) ===\n")
    print(section_4_text[:1000])
    
    # Try to extract sentences
    text = re.sub(r'\s+', ' ', section_4_text)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    print(f"\n=== Found {len(sentences)} potential sentences ===\n")
    
    valid_sentences = []
    for sent in sentences:
        sent = sent.strip()
        if len(sent) >= 15 and len(re.findall(r'[a-zA-Z]', sent)) >= 5:
            if not re.match(r'^[HP]\d{3}', sent):
                if not re.match(r'^(Page|Section|Chapter|SECTION)', sent, re.IGNORECASE):
                    valid_sentences.append(sent)
    
    print(f"Valid sentences: {len(valid_sentences)}\n")
    for i, sent in enumerate(valid_sentences[:5]):
        print(f"{i+1}. {sent[:100]}")
