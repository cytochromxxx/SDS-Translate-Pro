import csv
import re
from collections import defaultdict

file_path = 'routes/sds_phrases.csv'

def evaluate_quality(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=';')
        headers = next(reader)
        
        languages = headers[1:]
        
        stats = {
            lang: {
                'missing': 0,
                'placeholder_mismatch': 0,
                'length_outlier': 0,
                'reach_missing': 0,
                'total_evaluated': 0
            } for lang in languages
        }
        
        total_rows = 0
        
        for row in reader:
            if not row: continue
            total_rows += 1
            en_text = row[0].strip()
            
            # Identify placeholders and REACH keywords in English
            en_placeholders = len(re.findall(r'(\%s|\%d|\{\})', en_text))
            has_reach = 'REACH' in en_text
            has_svhc = 'SVHC' in en_text
            
            for i, lang in enumerate(languages):
                if i + 1 >= len(row):
                    stats[lang]['missing'] += 1
                    continue
                
                translated_text = row[i+1].strip()
                stats[lang]['total_evaluated'] += 1
                
                if not translated_text:
                    stats[lang]['missing'] += 1
                    continue
                
                # Placeholder check
                lang_placeholders = len(re.findall(r'(\%s|\%d|\{\})', translated_text))
                if en_placeholders != lang_placeholders:
                    stats[lang]['placeholder_mismatch'] += 1
                    
                # Length check
                if len(en_text) > 10:
                    ratio = len(translated_text) / len(en_text)
                    if ratio < 0.3 or ratio > 3.0:
                        stats[lang]['length_outlier'] += 1
                        
                # REACH check
                if has_reach and 'REACH' not in translated_text:
                    stats[lang]['reach_missing'] += 1
                if has_svhc and 'SVHC' not in translated_text:
                    stats[lang]['reach_missing'] += 1

    print(f"Total Rows: {total_rows}\n")
    print("Language | Missing | Placeholder Mismatch | Length Outlier | REACH/SVHC Keyword Missing | Quality Score (1-100)")
    print("-" * 115)
    
    for lang, stat in stats.items():
        total = stat['total_evaluated']
        if total == 0: continue
        
        errors = stat['missing'] + stat['placeholder_mismatch'] + stat['length_outlier'] + stat['reach_missing']
        # Simple quality score calculation
        score = max(0, 100 - (errors / total * 100 * 2))  # Penalty multiplier
        
        print(f"{lang:10} | {stat['missing']:7} | {stat['placeholder_mismatch']:20} | {stat['length_outlier']:14} | {stat['reach_missing']:26} | {score:5.1f}")

if __name__ == '__main__':
    evaluate_quality(file_path)
