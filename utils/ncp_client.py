# utils/ncp_client.py

import os
from pathlib import Path
import logging

import boto3
from botocore.client import Config
from dotenv import load_dotenv

# ─── 환경 변수 로드 ─────────────────────────
ROOT = Path(__file__).parent.parent
load_dotenv(dotenv_path=ROOT / ".env")

NCP_ACCESS_KEY   = os.getenv("NCP_ACCESS_KEY")
NCP_SECRET_KEY   = os.getenv("NCP_SECRET_KEY")
NCP_BUCKET_NAME  = os.getenv("NCP_BUCKET_NAME")
NCP_ENDPOINT_URL = os.getenv("NCP_ENDPOINT_URL")

if not all([NCP_ACCESS_KEY, NCP_SECRET_KEY, NCP_BUCKET_NAME, NCP_ENDPOINT_URL]):
    raise RuntimeError("NCP 관련 환경변수가 모두 설정되어야 합니다.")

# ─── S3 호환 클라이언트 생성 ────────────────────
_client = boto3.client(
    "s3",
    aws_access_key_id     = NCP_ACCESS_KEY,
    aws_secret_access_key = NCP_SECRET_KEY,
    endpoint_url          = NCP_ENDPOINT_URL,
    config                = Config(signature_version="s3v4"),
)

logger = logging.getLogger(__name__)


def upload_file(local_path: str, object_key: str) -> None:
    """
    로컬 파일(local_path)을 NCP 오브젝트 스토리지의
    {BUCKET}/{object_key} 로 업로드합니다.
    """
    try:
        _client.upload_file(
            Filename=local_path,
            Bucket=NCP_BUCKET_NAME,
            Key=object_key,
        )
        logger.info(f"Uploaded `{local_path}` to `{NCP_BUCKET_NAME}/{object_key}`")
    except Exception as e:
        logger.error(f"Failed to upload `{local_path}` → `{object_key}`: {e}")
        raise


def download_file(object_key: str, local_path: str) -> None:
    """
    NCP 오브젝트 스토리지의 {BUCKET}/{object_key} 를
    로컬 파일(local_path)로 다운로드합니다.
    """
    try:
        os.makedirs(Path(local_path).parent, exist_ok=True)
        _client.download_file(
            Bucket=NCP_BUCKET_NAME,
            Key=object_key,
            Filename=local_path,
        )
        logger.info(f"Downloaded `{object_key}` to `{local_path}`")
    except Exception as e:
        logger.error(f"Failed to download `{object_key}` → `{local_path}`: {e}")
        raise


# def list_objects(prefix: str = "") -> list[str]:
#     """
#     BUCKET 내 prefix 로 시작하는 오브젝트 키 리스트를 반환합니다.
#     """
#     paginator = _client.get_paginator("list_objects_v2")
#     keys = []
#     for page in paginator.paginate(Bucket=NCP_BUCKET_NAME, Prefix=prefix):
#         keys.extend([o["Key"] for o in page.get("Contents", [])])
#     return keys
