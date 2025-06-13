# utils/ncp_client.py
import sys
from pathlib import Path
import os
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# 프로젝트 루트를 시스템 경로에 추가
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent / ".env"
sys.path.append(str(PROJECT_ROOT))

# .env 경로 설정
env_path = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=env_path)

# 2) 환경변수 읽기
NCP_ACCESS_KEY = os.getenv("NCP_ACCESS_KEY")
NCP_SECRET_KEY = os.getenv("NCP_SECRET_KEY")
NCP_REGION     = os.getenv("NCP_REGION", "kr-standard")
NCP_ENDPOINT   = os.getenv("NCP_ENDPOINT", "https://kr.object.ncloudstorage.com")
NCP_BUCKET     = os.getenv("NCP_BUCKET_NAME")

if not all([NCP_ACCESS_KEY, NCP_SECRET_KEY, NCP_BUCKET]):
    raise ValueError("NCP_ACCESS_KEY, NCP_SECRET_KEY, NCP_BUCKET 환경변수가 설정되어 있지 않습니다.")

# 3) boto3 S3 클라이언트 인스턴스 생성
_s3_client = boto3.client(
    service_name="s3",
    region_name=NCP_REGION,
    endpoint_url=NCP_ENDPOINT,
    aws_access_key_id=NCP_ACCESS_KEY,
    aws_secret_access_key=NCP_SECRET_KEY,
)


def upload_file(local_path: Path, object_key: str, bucket: str = NCP_BUCKET) -> str:
    """
    로컬 파일을 NCP Object Storage (S3 호환) 버킷에 업로드.
    - local_path: 로컬 파일 경로 (Path 객체 또는 문자열)
    - object_key: 버킷 내 저장될 객체 키 (예: "models/20250601_model.pkl")
    - bucket: 업로드 대상 버킷 이름 (기본: .env의 NCP_BUCKET)
    
    반환: "s3://<버킷>/<object_key>" 형태의 URI 문자열
    """
    try:
        _s3_client.upload_file(str(local_path), bucket, object_key)
        return f"s3://{bucket}/{object_key}"
    except ClientError as e:
        raise RuntimeError(f"파일 업로드 실패: {e}")


def list_objects(prefix: str = "", bucket: str = NCP_BUCKET) -> list[str]:
    """
    버킷 내에 지정한 prefix 를 가진 객체 키 리스트를 반환.
    - prefix: 탐색할 접두어 (예: "models/" 혹은 빈 문자열)
    - bucket: 조회 대상 버킷 이름
    
    반환: 문자열 리스트 (각 요소는 객체 키)
    """
    keys = []
    paginator = _s3_client.get_paginator("list_objects_v2")
    try:
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                keys.append(obj["Key"])
    except ClientError as e:
        raise RuntimeError(f"객체 목록 조회 실패: {e}")
    return keys


# 4) 간단 테스트/예시 용도
if __name__ == "__main__":
    from pathlib import Path

    # 업로드 테스트
    test_file = Path(__file__).parent.parent / "README.md"
    if not test_file.exists():
        # “README.md”가 없으면 임시 파일 만들어서 테스트
        tmp = Path("/tmp") / "ncp_test.txt"
        tmp.write_text("NCP Object Storage upload 테스트")
        test_file = tmp

    object_key = f"test/{test_file.name}"
    uri = upload_file(test_file, object_key)
    print(f"업로드 완료 → {uri}")

    # 리스트 테스트
    print("버킷 내 'test/' 디렉토리 객체 키:")
    for key in list_objects(prefix="test/"):
        print(f" - {key}")
