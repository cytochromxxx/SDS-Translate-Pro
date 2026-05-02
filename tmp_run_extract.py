import os
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(root)
from extract_tm import SDSTranslationMemoryExtractor
extractor = SDSTranslationMemoryExtractor(os.path.join(root, 'SDS', 'downloads'))
extractor.extract_translation_memory('translation_memory.md')
print('EXTRACTION_DONE')
