import json, os
from chandra_pdf_importer import convert_pdf_to_json_with_chandra

pdf_path = 'translated_document_20260413.pdf'
output_dir = 'tmp_chandra'
os.makedirs(output_dir, exist_ok=True)

try:
    out_path = convert_pdf_to_json_with_chandra(pdf_path, output_dir)
    print('output json path:', out_path)
    with open(out_path, encoding='utf-8') as f:
        data = json.load(f)
    print('JSON keys:', list(data.keys()))
except Exception as e:
    print('Error during conversion:', e)
