import re

AVAILABLE_LANGUAGES = {
    'de': 'German (Deutsch)',
    'fr': 'French (Français)',
    'es': 'Spanish (Español)',
    'it': 'Italian (Italiano)',
    'nl': 'Dutch (Nederlands)',
    'pl': 'Polish (Polski)',
    'sv': 'Swedish (Svenska)',
    'da': 'Danish (Dansk)',
    'fi': 'Finnish (Suomi)',
    'el': 'Greek (Ελληνικά)',
    'cs': 'Czech (Čeština)',
    'hu': 'Hungarian (Magyar)',
    'ro': 'Romanian (Română)',
    'bg': 'Bulgarian (Български)',
    'sk': 'Slovak (Slovenčina)',
    'sl': 'Slovenian (Slovenščina)',
    'et': 'Estonian (Eesti)',
    'lv': 'Latvian (Latviešu)',
    'lt': 'Lithuanian (Lietuvių)',
    'hr': 'Croatian (Hrvatski)',
    'pt': 'Portuguese (Português)',
    'no': 'Norwegian (Norsk)',
    'is': 'Icelandic (Íslenska)',
}

LANGUAGE_CODE_MAP = {
    'EN': 'en', 'EN': 'en',
    'DE': 'de', 'DE': 'de',
    'FR': 'fr', 'FR': 'fr',
    'ES': 'es', 'ES': 'es',
    'IT': 'it', 'IT': 'it',
    'NL': 'nl', 'NL': 'nl',
    'PL': 'pl', 'PL': 'pl',
    'SV': 'sv', 'SV': 'sv',
    'DA': 'da', 'DA': 'da',
    'FI': 'fi', 'FI': 'fi',
    'EL': 'el', 'EL': 'el',
    'CS': 'cs', 'CS': 'cs',
    'HU': 'hu', 'HU': 'hu',
    'RO': 'ro', 'RO': 'ro',
    'BG': 'bg', 'BG': 'bg',
    'SK': 'sk', 'SK': 'sk',
    'SL': 'sl', 'SL': 'sl',
    'ET': 'et', 'ET': 'et',
    'LV': 'lv', 'LV': 'lv',
    'LT': 'lt', 'LT': 'lt',
    'HR': 'hr', 'HR': 'hr',
    'PT': 'pt', 'PT': 'pt',
    'NO': 'no', 'NO': 'no',
    'IS': 'is', 'IS': 'is',
}

LANG_TO_COLUMN = {
    'en': 'en_original',
    'de': 'de_original',
    'fr': 'fr_original',
    'es': 'es_original',
    'it': 'it_original',
    'nl': 'nl_original',
    'pl': 'pl_original',
    'sv': 'sv_original',
    'da': 'da_original',
    'fi': 'fi_original',
    'el': 'el_original',
    'cs': 'cs_original',
    'hu': 'hu_original',
    'ro': 'ro_original',
    'bg': 'bg_original',
    'sk': 'sk_original',
    'sl': 'sl_original',
    'et': 'et_original',
    'lv': 'lv_original',
    'lt': 'lt_original',
    'hr': 'hr_original',
    'pt': 'pt_original',
    'no': 'no_original',
    'is': 'is_original',
}


def parse_flag_format(text):
    phrases = []
    current_lang = None
    current_text = []
    source_lang = 'en'
    
    lines = text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or line == '---':
            if line == '---' and current_lang and current_text:
                phrase_text = '\n'.join(current_text).strip()
                if phrase_text:
                    phrases.append((current_lang, phrase_text))
                current_lang = None
                current_text = []
            continue
        
        match = re.match(r'^([A-Z]{2})[\s:\(]*(.*)$', line)
        if match:
            if current_lang and current_text:
                phrase_text = '\n'.join(current_text).strip()
                if phrase_text:
                    phrases.append((current_lang, phrase_text))
            
            lang_code_raw = match.group(1)
            lang_name = match.group(2).strip()
            lang_code = LANGUAGE_CODE_MAP.get(lang_code_raw, lang_code_raw.lower())
            
            if lang_code:
                current_lang = lang_code
                current_text = []

                if 'original' in lang_name.lower():
                    source_lang = lang_code

                # If text follows the language tag on the same line (e.g. "EN: The product..."),
                # treat it as the first line of the phrase, unless it's just a language name
                lang_keywords = {'english','deutsch','german','french','français','español','spanish',
                                 'italiano','italian','nederlands','dutch','polski','polish','svenska',
                                 'swedish','dansk','danish','suomi','finnish','original'}
                if lang_name and lang_name.lower() not in lang_keywords:
                    current_text.append(lang_name)
        else:
            if current_lang:
                current_text.append(line)
    
    if current_lang and current_text:
        phrase_text = '\n'.join(current_text).strip()
        if phrase_text:
            phrases.append((current_lang, phrase_text))
    
    return phrases, source_lang
