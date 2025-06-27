# import os
# from dotenv import load_dotenv
# import boto3

# # ─── .env 파일 로드 ─────────────────────────────
# load_dotenv()

# NCP_ACCESS_KEY    = os.getenv("NCP_ACCESS_KEY")
# NCP_SECRET_KEY    = os.getenv("NCP_SECRET_KEY")
# NCP_BUCKET_NAME   = os.getenv("NCP_BUCKET_NAME")
# NCP_ENDPOINT_URL  = os.getenv("NCP_ENDPOINT_URL")
# NCP_REGION_NAME   = os.getenv("NCP_REGION_NAME", "kr-standard")

# # ─── 업로드할 파일 경로 및 S3 키 설정 ─────────────
# local_file_path = '/Users/yerim/Downloads/rmrp-ai-dev/model/model1.pkl'
# object_key      = 'sample-folder/model1.pkl'

# # ─── 실행 블록 ───────────────────────────────────
# if __name__ == "__main__":
#     # 1. boto3 클라이언트 생성
#     s3 = boto3.client(
#         "s3",
#         endpoint_url=NCP_ENDPOINT_URL,
#         region_name=NCP_REGION_NAME,
#         aws_access_key_id=NCP_ACCESS_KEY,
#         aws_secret_access_key=NCP_SECRET_KEY
#     )

#     try:
#         # 2. (선택) S3 폴더처럼 보이게 하기 위해 접두 경로 업로드
#         s3.put_object(Bucket=NCP_BUCKET_NAME, Key='sample-folder/')

#         # 3. 파일 업로드
#         s3.upload_file(local_file_path, NCP_BUCKET_NAME, object_key)

#         # 4. 퍼블릭 읽기 권한 부여
#         s3.put_object_acl(ACL="public-read", Bucket=NCP_BUCKET_NAME, Key=object_key)

#         print("업로드 완료!")
#         print(f"퍼블릭 URL: https://{NCP_BUCKET_NAME}.kr.object.ncloudstorage.com/{object_key}")
#     except Exception as e:
#         print("오류 발생:", e)
