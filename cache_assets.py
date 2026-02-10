import requests
import json
import base64
import os

VOICEVOX_URL = "http://127.0.0.1:800"
OUTPUT_DIR = "/data/voicevox/webui"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def save_base64_image(base64_str, filename):
    if not base64_str:
        return False
    try:
        img_data = base64.b64decode(base64_str)
        with open(os.path.join(OUTPUT_DIR, filename), "wb") as f:
            f.write(img_data)
        return True
    except Exception as e:
        print(f"Error saving {filename}: {e}")
        return False

def save_base64_audio(base64_str, filename):
    if not base64_str:
        return False
    try:
        audio_data = base64.b64decode(base64_str)
        with open(os.path.join(OUTPUT_DIR, filename), "wb") as f:
            f.write(audio_data)
        return True
    except Exception as e:
        print(f"Error saving {filename}: {e}")
        return False

def main():
    print("Fetching speakers...")
    try:
        speakers = requests.get(f"{VOICEVOX_URL}/speakers").json()
    except Exception as e:
        print(f"Failed to fetch speakers: {e}")
        return

    print(f"Found {len(speakers)} speakers. Starting download...")

    for speaker in speakers:
        name = speaker["name"]
        uuid = speaker["speaker_uuid"]
        print(f"Processing {name} ({uuid})...")

        try:
            info = requests.get(f"{VOICEVOX_URL}/speaker_info", params={"speaker_uuid": uuid}).json()
            
            # Save Portrait
            if info.get("portrait"):
                save_base64_image(info["portrait"], f"{uuid}_portrait.png")
            
            # Process Styles for Icon and Samples
            if "style_infos" in info:
                # We usually just need one icon per character, but let's see.
                # Usually the first style's icon is used as the character icon.
                if len(info["style_infos"]) > 0:
                    first_style = info["style_infos"][0]
                    if first_style.get("icon"):
                        save_base64_image(first_style["icon"], f"{uuid}_icon.png")
                    
                    # Save samples (limit to 3 per char to save space/time if needed, or all)
                    # Let's save the first 3 samples of the first style for the "preview"
                    if first_style.get("voice_samples"):
                        for i, sample in enumerate(first_style["voice_samples"][:3]):
                            save_base64_audio(sample, f"{uuid}_sample_{i+1}.wav")

        except Exception as e:
            print(f"Error processing {name}: {e}")

    print("Download complete.")

if __name__ == "__main__":
    main()
