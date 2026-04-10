import os
from huggingface_hub import HfApi

def upload_to_huggingface():
    # 0. DIEN TOKEN CUA BAN VAO DAY (Token bat dau bang hf_...)
    HF_TOKEN = "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"
    
    # Khoi tao API voi token truc tiep
    api = HfApi(token=HF_TOKEN)
    
    # 1. Dien thong tin repo cua ban
    repo_id = "HuuDatLego/tts-app"  # Doi thanh ten Space thuc te cua ban
    repo_type = "space"             # Vi ban dang up len Space
    
    # 2. Thu muc hien tai (chua toan bo project)
    folder_path = "."               
    
    print(f"Bat dau upload toan bo thu muc '{os.path.abspath(folder_path)}' len {repo_id}...")
    
    try:
        api.upload_folder(
            folder_path=folder_path,
            repo_id=repo_id,
            repo_type=repo_type,
            ignore_patterns=[
                ".git/*",
                "__pycache__/*", 
                "audio/*",
                ".env*",
                "upload_to_hf.py"
            ] 
        )
        print("Upload thanh cong!")
        print(f"Kiem tra tai: https://huggingface.co/spaces/{repo_id}")
    except Exception as e:
        print(f"Upload that bai: {e}")

if __name__ == "__main__":
    upload_to_huggingface()
