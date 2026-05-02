import fitz, re

path = 'SDS/downloads/SDB-0332-CH-EN.pdf'
doc = fitz.open(path)
text = ''
for i in range(min(3, len(doc))):
    page = doc[i]
    text += f'--- PAGE {i+1} ---\n'
    text += page.get_text()
print(text[:5000])
print('--- matches ---')
print(re.findall(r'SECTION\\s+\\d+|section\\s+\\d+|\\d+\\.|\\d+\\s+\\.', text[:5000]))
