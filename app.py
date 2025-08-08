# app.py (Phiên bản nâng cấp - Chuyển giọng đọc theo đoạn)
import os
import subprocess
import uuid
import requests
from pathlib import Path
from flask import Flask, request, render_template, send_from_directory, jsonify

# Thêm import cho pydub
from pydub import AudioSegment

app = Flask(__name__)

# --- CÁC THIẾT LẬP ---
# Danh sách các giọng đọc chúng ta sẽ hỗ trợ
AVAILABLE_VOICES = {
    "en_US-lessac-medium": "English (US, Male)",
    "en_US-kathleen-low": "English (US, Female)",
    "en_GB-alan-medium": "English (UK, Male)"
}
# Định nghĩa giọng nam và nữ mặc định để chuyển đổi
MALE_VOICE_ID = "en_US-lessac-medium"
FEMALE_VOICE_ID = "en_US-kathleen-low"

VOICES_DIR = "piper_voices"
OUTPUT_DIR = "output_audio"

Path(VOICES_DIR).mkdir(exist_ok=True)
Path(OUTPUT_DIR).mkdir(exist_ok=True)

# --- HÀM HỖ TRỢ (Giữ nguyên) ---
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
    voices_path = Path(VOICES_DIR)
    model_path = voices_path / f"{voice_model_name}.onnx"
    config_path = voices_path / f"{voice_model_name}.onnx.json"
    if not model_path.exists() or not config_path.exists():
        print(f"Voice model '{voice_model_name}' not found. Starting download...")
        try:
            parts = voice_model_name.split('-')
            lang_code = parts[0]
            base_url = f"https://huggingface.co/rhasspy/piper-voices/resolve/main/{lang_code}/{voice_model_name}"
            model_url = f"{base_url}.onnx"
            config_url = f"{base_url}.onnx.json"
            if not model_path.exists(): download_file(model_url, model_path)
            if not config_path.exists(): download_file(config_url, config_path)
        except Exception as e:
             print(f"Could not parse or download voice '{voice_model_name}': {e}")
             return None
    if model_path.exists(): return str(model_path)
    return None

# Tải trước tất cả các giọng đọc khi khởi động server
print("Pre-loading all available voice models...")
for voice_name in AVAILABLE_VOICES.keys():
    setup_piper_voice(voice_name)
print("All models checked and ready.")


# --- CÁC ROUTE CỦA WEB ---
@app.route('/')
def index():
    # Chúng ta sẽ thêm một checkbox vào trang HTML để bật/tắt tính năng này
    return render_template('index.html', voices=AVAILABLE_VOICES)

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    text_to_speak = data.get('text')
    voice_model_name = data.get('voice')
    # Nhận trạng thái của checkbox từ frontend
    alternate_voices = data.get('alternate', False)

    if not text_to_speak:
        return jsonify({"error": "Text not provided."}), 400

    # --- LOGIC MỚI: CHUYỂN ĐỔI GIỌNG ĐỌC ---
    if alternate_voices:
        return generate_alternating_audio(text_to_speak)
    # --- LOGIC CŨ: GIỮ NGUYÊN ---
    else:
        if not voice_model_name or voice_model_name not in AVAILABLE_VOICES:
            return jsonify({"error": "Invalid voice selected."}), 400
        return generate_single_audio(text_to_speak, voice_model_name)

def generate_single_audio(text, voice_model_name):
    """Tạo âm thanh với một giọng đọc duy nhất (logic cũ)."""
    model_path = str(Path(VOICES_DIR) / f"{voice_model_name}.onnx")
    if not Path(model_path).exists():
        return jsonify({"error": f"Voice model for '{voice_model_name}' not found on server."}), 500

    try:
        filename = f"{uuid.uuid4()}.wav"
        output_path = Path(OUTPUT_DIR) / filename
        
        subprocess.run(
            ['piper', '--model', model_path, '--output_file', str(output_path)],
            input=text.strip().encode('utf-8'),
            check=True
        )
        return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)
    except Exception as e:
        print("Error during single audio generation:", e)
        return jsonify({"error": "Failed to generate audio."}), 500


def generate_alternating_audio(text):
    """
    Tạo âm thanh bằng cách chuyển đổi giữa giọng nam và nữ cho mỗi đoạn.
    Đoạn 1: Nam, Đoạn 2: Nữ, Đoạn 3: Nam, v.v.
    """
    # Tách văn bản thành các đoạn, loại bỏ các dòng trống
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    if not paragraphs:
        return jsonify({"error": "Text contains no content."}), 400

    male_model_path = str(Path(VOICES_DIR) / f"{MALE_VOICE_ID}.onnx")
    female_model_path = str(Path(VOICES_DIR) / f"{FEMALE_VOICE_ID}.onnx")

    chunk_files = []
    request_id = uuid.uuid4()

    try:
        # Bước 1: Tạo file âm thanh cho từng đoạn
        for i, paragraph in enumerate(paragraphs):
            # Đoạn 1 (i=0), 3 (i=2),... dùng giọng nam
            # Đoạn 2 (i=1), 4 (i=3),... dùng giọng nữ
            is_male_turn = (i % 2 == 0) # i=0, 2, 4...
            
            # Logic theo yêu cầu: đoạn 1, 3 là nam, đoạn 2 là nữ
            # i = 0 (đoạn 1) -> is_male_turn = True -> Giọng Nam
            # i = 1 (đoạn 2) -> is_male_turn = False -> Giọng Nữ
            # i = 2 (đoạn 3) -> is_male_turn = True -> Giọng Nam
            # ... và cứ thế xen kẽ

            model_path = male_model_path if is_male_turn else female_model_path
            
            chunk_filename = f"{request_id}_chunk_{i}.wav"
            chunk_output_path = Path(OUTPUT_DIR) / chunk_filename
            
            print(f"Generating chunk {i} with {'Male' if is_male_turn else 'Female'} voice...")
            subprocess.run(
                ['piper', '--model', model_path, '--output_file', str(chunk_output_path)],
                input=paragraph.encode('utf-8'),
                check=True
            )
            chunk_files.append(chunk_output_path)

        # Bước 2: Ghép các file âm thanh lại
        if not chunk_files:
            return jsonify({"error": "No audio chunks were generated."}), 500
        
        print("Combining audio chunks...")
        # Lấy file đầu tiên làm gốc
        combined_audio = AudioSegment.from_wav(chunk_files[0])
        
        # Nối các file còn lại
        for chunk_file in chunk_files[1:]:
            next_chunk = AudioSegment.from_wav(chunk_file)
            combined_audio += next_chunk

        # Bước 3: Xuất file cuối cùng
        final_filename = f"{request_id}_final.wav"
        final_output_path = Path(OUTPUT_DIR) / final_filename
        combined_audio.export(final_output_path, format="wav")
        
        return send_from_directory(OUTPUT_DIR, final_filename, as_attachment=True)

    except Exception as e:
        print("Error during alternating audio generation:", e)
        return jsonify({"error": "Failed to generate alternating audio."}), 500
    finally:
        # Bước 4: Dọn dẹp các file tạm
        print("Cleaning up chunk files...")
        for chunk_file in chunk_files:
            try:
                os.remove(chunk_file)
            except OSError as e:
                print(f"Error removing file {chunk_file}: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)