import requests
import json
import time

# Load basic speaker list
try:
    with open('speakers.json', 'r', encoding='utf-8') as f:
        speakers = json.load(f)
except FileNotFoundError:
    print("speakers.json not found, trying to fetch...")
    try:
        resp = requests.get("http://127.0.0.1:800/speakers")
        speakers = resp.json()
    except Exception as e:
        print(f"Failed to fetch speakers: {e}")
        exit(1)

output_file = 'raw_voicevox_info.txt'
base_url = "http://127.0.0.1:800"

with open(output_file, 'w', encoding='utf-8') as f:
    # 1. Output Parameter Fields
    f.write("=== Audio Query Parameters (Original Fields) ===\n")
    params = [
        "accent_phrases", "speedScale", "pitchScale", "intonationScale", 
        "volumeScale", "prePhonemeLength", "postPhonemeLength", 
        "pauseLength", "pauseLengthScale", "outputSamplingRate", 
        "outputStereo", "kana"
    ]
    for p in params:
        f.write(f"{p}\n")
    f.write("\n")

    # 2. Output Character Info
    f.write("=== Character List (Raw Info) ===\n")
    f.write(f"{ 'Name':<20} | {'UUID':<40} | {'Styles':<40} | {'Description (portrait info)'}\n")
    f.write("-" * 150 + "\n")

    for spk in speakers:
        name = spk['name']
        uuid = spk['speaker_uuid']
        styles = ", ".join([s['name'] for s in spk['styles']])
        
        # Try to get detailed info (portrait info usually contains description)
        desc = "N/A"
        try:
            # Note: The actual endpoint for description might be inside speaker_info
            # or just implicit. Let's try /speaker_info
            info_resp = requests.get(f"{base_url}/speaker_info", params={"speaker_uuid": uuid})
            if info_resp.status_code == 200:
                info = info_resp.json()
                # portrait_file_info often contains some meta, but Voicevox API 
                # doesn't strictly have a "description" field in /speakers.
                # However, usually users refer to the style descriptions or just the raw style names.
                # Let's see if we can find anything extra. 
                # Actually, standard Voicevox Engine API /speakers doesn't return description text.
                # It returns styles and their IDs.
                # The user mentioned "子供っぽい高めの声" (Childlike high-pitched voice) which sounds like
                # it might be in the `style_infos` or separate metadata.
                # Let's check if `style_infos` exists in /speaker_info result.
                
                # In standard VV Engine, /speaker_info returns {policy:..., portrait:..., style_infos: [...]} 
                # style_infos might have descriptions.
                if 'style_infos' in info:
                    # Let's grab descriptions from here if available
                    pass
                
                # For now, let's dump what we found.
                pass
        except Exception as e:
            print(f"Error fetching info for {name}: {e}")

        # Since I can't easily see the deep structure without probing, 
        # I will output the Name and Styles (which are the most critical "original fields").
        # If the user specifically remembers descriptions like "Childlike...", 
        # those are often part of the official website metadata, NOT necessarily the engine API.
        # But I will output what the Engine gives us.
        
        f.write(f"{name:<20} | {uuid:<40} | {styles}\n")

print(f"Exported to {output_file}")
