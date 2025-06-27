# upload_model_to_ncp.py

import os
from pathlib import Path
from utils.ncp_client import upload_file

# ─── 업로드 대상 모델 파일들 ─────────────────
models = {
    "model/model1.pkl": "model/model1.pkl",
    "model/model2.pkl": "model/model2.pkl",
    "model/model3.pkl": "model/model3.pkl"
}

# ─── 업로드 실행 ────────────────────────────────
print("모델 파일 NCP 업로드 시작...")

for local_path, object_key in models.items():
    if not os.path.exists(local_path):
        print(f"로컬 파일 없음: {local_path}")
        continue

    try:
        upload_file(local_path, object_key)
        print(f"업로드 성공: {local_path} → {object_key}")
    except Exception as e:
        print(f"업로드 실패: {local_path} → {object_key}\n   사유: {e}")
