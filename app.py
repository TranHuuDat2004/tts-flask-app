# app.py (Phiên bản nâng cấp chọn giọng đọc)
import os
import subprocess
import uuid
import requests
from pathlib import Path
from flask import Flask, request, render_template, send_from_directory, jsonify

app = Flask(__name__)

# --- CÁC THIẾT LẬP ---
# Danh sách các giọng đọc chúng ta sẽ hỗ trợ
AVAILABLE_VOICES = {
    "en_US-lessac-medium": "English (US, Male)",
    "en_US-kathleen-low": "English (US, Female)",
    "en_GB-alan-medium": "English (UK, Male)"
}
VOICES_DIR = "piper_voices"
OUTPUT_DIR = "output_audio"

Path(VOICES_DIR).mkdir(exist_ok=True)
Path(OUTPUT_DIR).mkdir(exist_ok=True)

# --- HÀM HỖ TRỢ ---
def download_file(url, local_path):
    print(f"Downloading {url}...")
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(local_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
        print(f"Successfully downloaded to {local_path}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {url}: {e}")
        return False

def setup_piper_voice(voice_model_name):
    """Kiểm tra và tải về MỘT giọng đọc cụ thể nếu cần."""
    voices_path = Path(VOICES_DIR)
    model_path = voices_path / f"{voice_model_name}.onnx"
    config_path = voices_path / f"{voice_model_name}.onnx.json"

    if not model_path.exists() or not config_path.exists():
        print(f"Voice model '{voice_model_name}' not found. Starting download...")
        try:
            parts = voice_model_name.split('-')
            lang_code, voice_name = parts[0].split('_')
            
            # Cấu trúc URL có thể khác nhau giữa các ngôn ngữ
            if lang_code == 'en':
                quality = parts[2]
                base_url = f"https://huggingface.co/rhasspy/piper-voices/resolve/main/{lang_code}/{lang_code}_{voice_name.upper()}/{parts[1]}/{quality}/{voice_model_name}"
            elif lang_code == 'vi':
                 # Cấu trúc cho giọng tiếng Việt
                 base_url = f"https://huggingface.co/rhasspy/piper-voices/resolve/main/{lang_code}/{voice_model_name}"
            else:
                 base_url = f"https://huggingface.co/rhasspy/piper-voices/resolve/main/{lang_code}/{voice_model_name}"


            model_url = f"{base_url}.onnx"
            config_url = f"{base_url}.onnx.json"
            
            if not model_path.exists(): download_file(model_url, model_path)
            if not config_path.exists(): download_file(config_url, config_path)
        except Exception as e:
             print(f"Could not parse or download voice '{voice_model_name}': {e}")
             return None
    
    if model_path.exists():
        return str(model_path)
    return None

# Tải trước tất cả các giọng đọc khi khởi động server
print("Pre-loading all available voice models...")
for voice_name in AVAILABLE_VOICES.keys():
    setup_piper_voice(voice_name)
print("All models checked and ready.")

# --- CÁC ROUTE CỦA WEB ---
@app.route('/')
def index():
    return render_template('index.html', voices=AVAILABLE_VOICES)

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    text_to_speak = data.get('text')
    voice_model_name = data.get('voice')

    if not text_to_speak or not voice_model_name:
        return jsonify({"error": "Text or voice not provided."}), 400

    if voice_model_name not in AVAILABLE_VOICES:
        return jsonify({"error": "Invalid voice selected."}), 400

    model_path = str(Path(VOICES_DIR) / f"{voice_model_name}.onnx")
    if not Path(model_path).exists():
        return jsonify({"error": f"Voice model for '{voice_model_name}' not found on server."}), 500

    try:
        filename = f"{uuid.uuid4()}.wav"
        output_path = Path(OUTPUT_DIR) / filename
        
        subprocess.run(
            ['piper', '--model', model_path, '--output_file', str(output_path)],
            input=text_to_speak.strip().encode('utf-8'),
            check=True
        )
        
        return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)
    except Exception as e:
        print("Error during audio generation:", e)
        return jsonify({"error": "Failed to generate audio."}), 500

if __name__ == '__main__':
    app.run(debug=True)