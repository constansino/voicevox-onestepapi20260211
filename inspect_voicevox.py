import requests
import json

try:
    # Shikoku Metan UUID from previous run
    uuid = "7ffcb7ce-00ec-4bdc-82cd-45a8889e43ff"
    response = requests.get(f"http://127.0.0.1:800/speaker_info?speaker_uuid={uuid}")
    if response.status_code == 200:
        data = response.json()
        # Truncate long fields like base64 images
        if "portrait" in data: data["portrait"] = "TRUNCATED"
        if "style_infos" in data:
            for s in data["style_infos"]:
                if "icon" in s: s["icon"] = "TRUNCATED_ICON"
                if "voice_samples" in s: 
                    # Print first sample start to check format
                    print(f"Sample 1 start: {s['voice_samples'][0][:50]}")
                    s["voice_samples"] = ["TRUNCATED_SAMPLES"]
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(f"Error checking speaker_info: {response.status_code} {response.text}")

except Exception as e:
    print(f"Exception: {e}")
