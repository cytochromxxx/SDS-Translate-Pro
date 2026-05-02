#!/usr/bin/env python3
"""Pivot SDS phrase CSV so that each language becomes its own column."""

import argparse
import csv
from collections import defaultdict
from typing import Dict, List, Tuple

DEFAULT_LANG_ORDER = [
    'EN', 'DE', 'FR', 'IT', 'ES', 'NL', 'PT', 'PL', 'CS', 'SK', 'SL', 'HU',
    'RO', 'BG', 'HR', 'LT', 'LV', 'ET', 'FI', 'SV', 'DA', 'NO', 'EL', 'SR'
]


def read_phrases(path: str) -> Tuple[List[str], List[Tuple[str, str, str, str, str]]]:
    rows = []
    with open(path, encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f, delimiter=';')
        header = next(reader, None)
        if header is None:
            raise ValueError('Input CSV is empty')
        for line in reader:
            if len(line) < 5:
                continue
            language, product_id, country, section, phrase = line[:5]
            rows.append((language.strip(), product_id.strip(), country.strip(), section.strip(), phrase.strip()))
    return header, rows


def build_groups(rows: List[Tuple[str, str, str, str, str]]) -> Tuple[List[str], Dict[Tuple[str, str, str], Dict[str, List[str]]]]:
    groups: Dict[Tuple[str, str, str], Dict[str, List[str]]] = {}
    languages = []
    for language, product_id, country, section, phrase in rows:
        language = language.upper()
        if language not in languages:
            languages.append(language)
        key = (product_id, country, section)
        if key not in groups:
            groups[key] = defaultdict(list)
        groups[key][language].append(phrase)
    return languages, groups


def determine_columns(languages: List[str], explicit_order: List[str]) -> List[str]:
    ordered = []
    for code in explicit_order:
        if code in languages:
            ordered.append(code)
    for code in sorted(languages):
        if code not in ordered:
            ordered.append(code)
    return ordered


def write_pivot_csv(output_path: str, groups: Dict[Tuple[str, str, str], Dict[str, List[str]]], columns: List[str]):
    header = ['product_id', 'country', 'section'] + columns
    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(header)
        for (product_id, country, section), lang_map in sorted(groups.items()):
            max_rows = max((len(lang_map.get(lang, [])) for lang in columns), default=0)
            for index in range(max_rows):
                row = [product_id, country, section]
                for lang in columns:
                    phrases = lang_map.get(lang, [])
                    row.append(phrases[index] if index < len(phrases) else '')
                writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(description='Pivot SDS phrases CSV into a language-column matrix.')
    parser.add_argument('--input-file', default='sds_phrases.csv', help='Source CSV file with one phrase per row')
    parser.add_argument('--output-file', default='sds_phrases_pivot.csv', help='Pivoted CSV output file')
    parser.add_argument('--lang-order', default=','.join(DEFAULT_LANG_ORDER), help='Comma-separated language order for columns')
    args = parser.parse_args()

    _, rows = read_phrases(args.input_file)
    languages, groups = build_groups(rows)
    lang_order = [lang.strip().upper() for lang in args.lang_order.split(',') if lang.strip()]
    cols = determine_columns(languages, lang_order)
    write_pivot_csv(args.output_file, groups, cols)
    print(f'Pivoted {len(rows)} phrase rows into {len(groups)} groups and wrote {args.output_file}')


if __name__ == '__main__':
    main()
