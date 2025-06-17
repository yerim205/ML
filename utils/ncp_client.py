import os
import logging
from pathlib import Path
from dotenv import load_dotenv
import boto3
from botocore.client import Config

# ─── .env 로드 ─────────────────────────────
ROOT = Path(__file__).parent.parent
load_dotenv(dotenv_path=ROOT / ".env")

# ─── 환경 변수 로드 ─────────────────────────
NCP_ACCESS_KEY    = os.getenv("NCP_ACCESS_KEY")
NCP_SECRET_KEY    = os.getenv("NCP_SECRET_KEY")
NCP_BUCKET_NAME   = os.getenv("NCP_BUCKET_NAME")
NCP_ENDPOINT_URL  = os.getenv("NCP_ENDPOINT_URL")
NCP_REGION_NAME   = os.getenv("NCP_REGION_NAME", "kr-standard")

# ─── 필수 항목 체크 ─────────────────────────
if not all([NCP_ACCESS_KEY, NCP_SECRET_KEY, NCP_BUCKET_NAME, NCP_ENDPOINT_URL]):
    raise RuntimeError("NCP 관련 환경변수가 모두 설정되어야 합니다.")

# ─── S3 클라이언트 생성 ─────────────────────
s3 = boto3.client(
    "s3",
    region_name=NCP_REGION_NAME,
    endpoint_url=NCP_ENDPOINT_URL,
    aws_access_key_id=NCP_ACCESS_KEY,
    aws_secret_access_key=NCP_SECRET_KEY,
    config=Config(signature_version="s3v4")
)

# ─── 로깅 설정 ──────────────────────────────
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s: %(message)s")


# ─────────────────────────────────────────────
def upload_file(local_path: str, object_key: str, public: bool = True):
    """로컬 파일을 Object Storage에 업로드"""
    try:
        s3.upload_file(local_path, NCP_BUCKET_NAME, object_key)
        if public:
            s3.put_object_acl(ACL="public-read", Bucket=NCP_BUCKET_NAME, Key=object_key)
        logger.info(f"Uploaded: {local_path} → s3://{NCP_BUCKET_NAME}/{object_key}")
    except Exception as e:
        raise RuntimeError(f"[업로드 실패] {local_path} → {object_key}: {e}")


def download_file(object_key: str, local_path: str):
    """Object Storage에서 파일 다운로드"""
    try:
        os.makedirs(Path(local_path).parent, exist_ok=True)
        s3.download_file(NCP_BUCKET_NAME, object_key, local_path)
        logger.info(f"Downloaded: s3://{NCP_BUCKET_NAME}/{object_key} → {local_path}")
    except Exception as e:
        raise RuntimeError(f"[다운로드 실패] {object_key} → {local_path}: {e}")


def list_objects(prefix: str = "", max_keys: int = 20):
    """지정된 경로 기준으로 오브젝트 목록 조회"""
    try:
        resp = s3.list_objects_v2(Bucket=NCP_BUCKET_NAME, Prefix=prefix, MaxKeys=max_keys)
        if "Contents" in resp:
            for obj in resp["Contents"]:
                print(f"- {obj['Key']} (size: {obj['Size']})")
        else:
            print("ℹ오브젝트가 없습니다.")
    except Exception as e:
        logger.error(f"[오브젝트 조회 실패] {e}")


def delete_object(object_key: str):
    """오브젝트 삭제"""
    try:
        s3.delete_object(Bucket=NCP_BUCKET_NAME, Key=object_key)
        logger.info(f"Deleted: s3://{NCP_BUCKET_NAME}/{object_key}")
    except Exception as e:
        logger.error(f"[삭제 실패] {object_key}: {e}")


# ─── CLI 테스트 용도 ─────────────────────────
if __name__ == "__main__":
    print("NCP 연결 테스트 중...")
    try:
        result = s3.list_objects_v2(Bucket=NCP_BUCKET_NAME, MaxKeys=1)
        count = len(result.get("Contents", []))
        print(f"연결 성공: {count}개의 오브젝트 확인됨")
    except Exception as e:
        print("연결 실패:", e)
