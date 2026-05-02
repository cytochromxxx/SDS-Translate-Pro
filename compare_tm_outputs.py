#!/usr/bin/env python3
"""Compare the generated translation memory outputs."""

import pathlib
import re

files = ['translation_memory_md.md', 'translation_memory_json.md']
for fname in files:
    p = pathlib.Path(fname)
    text = p.read_text(encoding='utf-8')
    languages = sorted(set(re.findall(r'^## Language: (\w+)$', text, re.M)))
    counts = {}
    current_lang = None
    for line in text.splitlines():
        if line.startswith('## Language: '):
            current_lang = line.split(':', 1)[1].strip()
            counts[current_lang] = 0
            continue
        if current_lang and line.startswith('| ') and not line.startswith('| Section'):
            counts[current_lang] += 1

    entries = sum(counts.values())
    print(fname)
    print('  size:', p.stat().st_size, 'bytes')
    print('  languages:', len(languages), languages)
    print('  entries:', entries)
    print('  entries by language:')
    for lang in sorted(counts.keys()):
        print('   ', lang, counts[lang])
    print('  first lines:')
    for line in text.splitlines()[:10]:
        print('   ', line)
    print('---')
