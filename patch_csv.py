import csv

file_path = 'routes/sds_phrases.csv'

mt_translations = {
    "Chem. Unst. Gas A": "Gass Kimikament Instabbli A",
    "Chem. Unst. Gas B": "Gass Kimikament Instabbli B",
    "Aerosols": "Aerosols",
    "Aerosol 1": "Aerosol 1",
    "Aerosol 2": "Aerosol 2",
    "Aerosol 3": "Aerosol 3",
    "Oxidising gases": "Gassijiet ossidanti",
    "Ox. Gas 1": "Gass Oss. 1",
    "Gases under pressure": "Gassijiet taħt pressjoni",
    "Press. Gas.": "Gass taħt pressjoni",
    "Press. Gas (Comp.)": "Gass taħt pressjoni (Komp.)",
    "Press. Gas (Liq.)": "Gass taħt pressjoni (Likw.)",
    "Press. Gas (Ref. Liq.)": "Gass taħt pressjoni (Likw. Iffriż.)",
    "Press. Gas (Diss.)": "Gass taħt pressjoni (Maħlul)",
    "Compr. Gas": "Gass Kompressat",
    "Liquef. Gas": "Gass Likwifikat",
    "Refr. Liquef. Gas": "Gass Likwifikat Iffriżat",
    "Diss. Gas": "Gass Maħlul",
    "flammable liquids": "Likwidi fjammabbli",
    "Flam. Liq. 1": "Likwidu fjammabbli 1"
}

et_translations = {
    "Practical Guide": "Praktiline juhend",
    "Guidance in a nutshell": "Juhend lühidalt",
    "fact sheet": "teabeleht",
    "Practical guide 1: How to report in vitro data": "Praktiline juhend 1: Kuidas esitada in vitro andmeid",
    "Practical guide 2: How to report weight of evidence": "Praktiline juhend 2: Kuidas esitada tõendite kaalukust",
    "Practical guide 3: How to report robust study summaries": "Praktiline juhend 3: Kuidas esitada usaldusväärseid uuringukokkuvõtteid",
    "Practical guide 4: How to report data waiving": "Praktiline juhend 4: Kuidas esitada andmete esitamisest loobumist",
    "Practical guide 5: How to report (Q)SARs": "Praktiline juhend 5: Kuidas esitada (Q)SARe",
    "Practical guide 6: How to report read-across and categories": "Praktiline juhend 6: Kuidas esitada analoogmeetodit ja kategooriaid",
    "Practical guide 7: How to Notify Substances to the Classification & Labelling Inventory": "Praktiline juhend 7: Kuidas teavitada aineid klassifitseerimis- ja märgistusandmikku",
    "Practical guide 8: How to report changes in identity of legal entities": "Praktiline juhend 8: Kuidas teavitada juriidiliste isikute identiteedi muutustest",
    "Practical guide 9: How to do a registration as a member of a joint submission": "Praktiline juhend 9: Kuidas registreerida ühise esitamise liikmena",
    "Practical guide 10: How to avoid unnecessary testing on animals": "Praktiline juhend 10: Kuidas vältida tarbetuid loomkatseid",
    "Practical guide 12: How to communicate with ECHA in dossier evaluation": "Praktiline juhend 12: Kuidas suhelda ECHAga toimiku hindamise käigus",
    "Data Submission Manual Part 2: How to prepare and submit an inquiry dossier using IUCLID 5": "Andmete esitamise käsiraamat, 2. osa: Kuidas koostada ja esitada päringutoimikut IUCLID 5 abil",
    "IUM": "IUM (Tööstuse kasutajajuhend)",
    "Industry User Manual Part 2: Sign-up and account management": "Tööstuse kasutajajuhend, 2. osa: Registreerumine ja konto haldamine",
    "Industry User Manual Part 3: Login and Message Box": "Tööstuse kasutajajuhend, 3. osa: Sisselogimine ja postkast",
    "Industry User Manual Part 5: Pre-SIEF": "Tööstuse kasutajajuhend, 5. osa: Eel-SIEF",
    "Industry User Manual Part 7: Joint submission": "Tööstuse kasutajajuhend, 7. osa: Ühine esitamine"
}

with open(file_path, 'r', encoding='utf-8') as f:
    reader = csv.reader(f, delimiter=';')
    rows = list(reader)
    headers = rows[0]
    et_idx = headers.index('et_original')
    mt_idx = headers.index('mt_original')

updated_count = 0
for row in rows[1:]:
    en_text = row[0]
    
    # Pad row if too short
    while len(row) < len(headers):
        row.append('')
    
    if en_text in mt_translations and not row[mt_idx].strip():
        row[mt_idx] = mt_translations[en_text]
        updated_count += 1
        
    if en_text in et_translations and not row[et_idx].strip():
        row[et_idx] = et_translations[en_text]
        updated_count += 1

with open(file_path, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f, delimiter=';')
    writer.writerows(rows)

print(f"Updated {updated_count} translations in {file_path}.")
