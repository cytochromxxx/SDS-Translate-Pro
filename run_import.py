import sys
from sds_xml_importer import import_sds_to_html
import os

xml_file = sys.argv[1]
template_file = sys.argv[2]
pdf_file = sys.argv[3] if len(sys.argv) > 3 else None

final_html, gap_report = import_sds_to_html(xml_file, template_file, pdf_path=pdf_file)

if final_html:
    with open('output.html', 'w', encoding='utf-8') as f:
        f.write(final_html)
    print("Success! Wrote to output.html")
else:
    print("Import failed.")
