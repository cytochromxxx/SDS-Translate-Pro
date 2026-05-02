import fitz
import os
import sys

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

pdf_path = r"c:\Users\Flo\Downloads\SDS-Translate-Pro-master\SDS\downloads\SDB-0332-GB-EN.pdf"

doc = fitz.open(pdf_path)
print(f"Total pages: {len(doc)}")
print("\n=== First 1500 characters of page 1 ===\n")
text = doc[0].get_text()
print(text[:1500])

print("\n=== Searching for section keywords ===\n")
full_text = ""
for page in doc:
    full_text += page.get_text()

# Look for section markers
import re
sections_found = re.findall(r'(Section\s+\d+|^\d+\.\s+[A-Z][a-z]+)', full_text, re.MULTILINE | re.IGNORECASE)
print(f"Sections found: {sections_found[:20]}")

doc.close()
