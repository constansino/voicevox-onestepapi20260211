import json

# Load the JSON data
with open('speakers.json', 'r', encoding='utf-8') as f:
    speakers = json.load(f)

# Open the output file
with open('voicevox_characters.txt', 'w', encoding='utf-8') as f:
    f.write(f"{ '角色名 (Character)':<20} | { '音色 (Styles)':<50}\n")
    f.write("-" * 80 + "\n")
    
    for speaker in speakers:
        name = speaker.get('name', 'Unknown')
        styles = speaker.get('styles', [])
        
        style_names = [style.get('name', '') for style in styles]
        style_str = ", ".join(style_names)
        
        f.write(f"{name:<20} | {style_str}\n")
        f.write("-" * 80 + "\n")

print("Export completed to voicevox_characters.txt")
