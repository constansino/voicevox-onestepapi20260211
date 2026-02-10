import csv
import json
import os

csv_path = '/root/voicevox_trilingual.csv'
json_path = '/root/voicevox_translations.json'

translations = {
    "ja": {"params": {}, "styles": {}, "characters": {}},
    "en": {"params": {}, "styles": {}, "characters": {}},
    "zh": {"params": {}, "styles": {}, "characters": {}}
}

if not os.path.exists(csv_path):
    print(f"Error: {csv_path} not found.")
    exit(1)

with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    try:
        header = next(reader)
    except StopIteration:
        print("Empty CSV")
        exit(1)

    for row in reader:
        if not row or len(row) < 9: continue
        lang = row[0].strip()
        section = row[1].strip()
        
        if lang not in translations:
            continue

        if section == 'audio_query_param':
            key = row[7].strip()
            value = row[8].strip()
            if key:
                translations[lang]["params"][key] = value

        elif section == 'style':
            key = row[7].strip()
            value = row[8].strip()
            if key:
                translations[lang]["styles"][key] = value

        elif section == 'character':
            name = row[2].strip()
            uuid = row[3].strip()
            desc = row[5].strip()
            styles_note_raw = row[6].strip()
            
            style_notes = {}
            if styles_note_raw:
                parts = styles_note_raw.split(';')
                for part in parts:
                    part = part.strip()
                    if ':' in part:
                        s_key, s_val = part.split(':', 1)
                        style_notes[s_key.strip()] = s_val.strip()

            if uuid:
                translations[lang]["characters"][uuid] = {
                    "name": name,
                    "description": desc,
                    "style_notes": style_notes
                }

with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(translations, f, ensure_ascii=False, indent=2)

print(f"Successfully generated {json_path}")
