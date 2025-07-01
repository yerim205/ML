import os
import boto3
from dotenv import load_dotenv
from pathlib import Path

# ─── 환경 설정 로딩 ─────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=ROOT / ".env")

NCP_ACCESS_KEY = os.getenv("NCP_ACCESS_KEY")
NCP_SECRET_KEY = os.getenv("NCP_SECRET_KEY")
NCP_BUCKET_NAME = os.getenv("NCP_BUCKET_NAME")
NCP_REGION = os.getenv("NCP_REGION", "kr-standard")

# ─── S3 클라이언트 초기화 ──────────────────────
s3 = boto3.client(
    "s3",
    region_name=NCP_REGION,
    endpoint_url=f"http://kr.object.ncloudstorage.com",
    aws_access_key_id=NCP_ACCESS_KEY,
    aws_secret_access_key=NCP_SECRET_KEY
)

# ─── 파일 업로드 ───────────────────────────────
def upload_file_to_ncp(local_path: str, remote_path: str):
    try:
        s3.upload_file(local_path, NCP_BUCKET_NAME, remote_path)
        print(f"업로드 완료: {local_path} → {remote_path}")
    except Exception as e:
        print(f"업로드 실패: {e}")
        raise

# ─── 파일 다운로드 ─────────────────────────────
def download_file_from_ncp(remote_path: str, local_path: str):
    try:
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        s3.download_file(NCP_BUCKET_NAME, remote_path, local_path)
        print(f"다운로드 완료: {remote_path} → {local_path}")
    except Exception as e:
        print(f"다운로드 실패: {e}")
        raise
