from sds_json_parser import SDSJsonParser
import re

p = SDSJsonParser('datalab_exports/XuB2tyUYYoQVXtyW3pDDDw_SDS_LabClean_15-4100_en_DE_Ver.03.json')

with open('debug_out.txt', 'w', encoding='utf-8') as f:
    f.write('=== SECTION 8 ===\n')
    for i, b in enumerate(p.sections_content[8]):
        html = re.sub(r'<[^>]+>', ' ', b.get('html','')).replace('\n',' ').strip()
        f.write(f"[{i}] {b.get('block_type','?'):15} | {html[:200]}\n")

    f.write('\n=== SECTION 9 ===\n')
    for i, b in enumerate(p.sections_content[9]):
        html = re.sub(r'<[^>]+>', ' ', b.get('html','')).replace('\n',' ').strip()
        f.write(f"[{i}] {b.get('block_type','?'):15} | {html[:200]}\n")

print('Written to debug_out.txt')
