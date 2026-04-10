FROM python:3.9-slim

# Cài đặt ffmpeg cho các thư viện xử lý âm thanh (ví dụ: pydub)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Tạo user không phải root (Yêu cầu bắt buộc của Hugging Face Spaces)
RUN useradd -m -u 1000 user

# Thiết lập thư mục làm việc
WORKDIR /app

# Copy và cài đặt thư viện
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn vào container
COPY --chown=user:user . .
RUN mkdir -p /app/audio && chown -R user:user /app/audio

# Đổi sang user vừa tạo
USER user

# Thiết lập biến môi trường PORT thành 7860 (Port mặc định của Hugging Face)
ENV PORT=7860

EXPOSE 7860

# Khởi chạy ứng dụng
CMD ["python", "app.py"]
