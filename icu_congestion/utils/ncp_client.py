"""
NCP Object Storage 업·다운로드 헬퍼
pip install boto3 python-dotenv
"""
from pathlib import Path
import os, boto3
from dotenv import load_dotenv

load_dotenv()                                      # .env 로드

_s3 = boto3.client(
    "s3",
    region_name=os.getenv("NCP_REGION", "kr-standard"),
    endpoint_url=os.getenv("NCP_ENDPOINT"),
    aws_access_key_id=os.getenv("NCP_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("NCP_SECRET_KEY"),
)
_BUCKET = os.getenv("NCP_BUCKET")

def upload_file(local_path: Path, obj_key: str, bucket: str = _BUCKET):
    _s3.upload_file(str(local_path), bucket, obj_key)
    return f"s3://{bucket}/{obj_key}"

def list_objects(prefix: str = "", bucket: str = _BUCKET):
    for page in _s3.get_paginator("list_objects_v2").paginate(
        Bucket=bucket, Prefix=prefix
    ):
        for obj in page.get("Contents", []):
            yield obj["Key"]
