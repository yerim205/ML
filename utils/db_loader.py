#utils/db_loader.py >> 병상 API
import pandas as pd
import os, json, re
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, future=True)

def get_latest_realtime_data() -> dict: #병상 API 받아와 필터링하는 작업 -> 모델 1에 해당함. 
    """
    병상 요청 로그 중 가장 최신 ctnt JSON 반환
    - 요청(REQ)
    - 출처 시스템 CMC03
    - URL이 mdcl-rm-rcpt 포함
    """
    query = text("""
        SELECT ctnt
          FROM rmrp_portal.tb_api_log
         WHERE req_res = 'REQ'
           AND com_src_cd = 'CMC03'
           AND req_url LIKE '%mdcl-rm-rcpt%'
         ORDER BY reg_dtm DESC
         LIMIT 1
    """)

    with engine.connect() as conn:
        row = conn.execute(query).fetchone()
        if not row or not row[0]:
            raise ValueError("DB에 유효한 ctnt 데이터가 없습니다.")
        try:
            return json.loads(row[0])  # 문자열을 JSON으로 파싱
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 파싱 실패: {e}")
        
def get_realtime_data_for_today() -> list[dict]: #모델 2와 모델 3에서 사용 
    """
    병상 요청 로그(ctnt) 중 trasSno가 오늘 날짜인 JSON만 추출
    각 JSON에 trasSno 기반 timestamp 필드도 함께 부여
    """
    today_str = datetime.now().strftime("%Y%m%d")

    query = text("""
        SELECT ctnt
          FROM rmrp_portal.tb_api_log
         WHERE req_res = 'REQ'
           AND com_src_cd = 'CMC03'
           AND req_url LIKE '%mdcl-rm-rcpt%'
         ORDER BY reg_dtm DESC
    """)

    results = []

    with engine.connect() as conn:
        rows = conn.execute(query).fetchall()

    for row in rows:
        try:
            raw_ctnt = row[0]
            match = re.search(r'"trasSno"\s*:\s*"(\d{14})"', raw_ctnt)
            if not match:
                continue

            tras_sno_str = match.group(1)  # e.g., '20250429112235'
            if not tras_sno_str.startswith(today_str):
                continue

            timestamp = datetime.strptime(tras_sno_str, "%Y%m%d%H%M%S")

            parsed_json = json.loads(raw_ctnt)
            parsed_json["_timestamp"] = timestamp  # 추가된 필드

            results.append(parsed_json)
        except Exception:
            continue

    return results

def get_realtime_data_for_days_ago(n: int) -> list[dict]: # 모델 2와 모델 3에서 사용 >> 7일전 데이터 추출
    """
    병상 요청 로그(ctnt) 중 trasSno가 N일 전 날짜인 JSON만 반환
    각 JSON에 _timestamp 필드도 함께 부여
    """
    target_date = (datetime.now() - timedelta(days=n)).strftime("%Y%m%d")

    query = text("""
        SELECT ctnt
          FROM rmrp_portal.tb_api_log
         WHERE req_res = 'REQ'
           AND com_src_cd = 'CMC03'
           AND req_url LIKE '%mdcl-rm-rcpt%'
         ORDER BY reg_dtm DESC
    """)

    result = []

    with engine.connect() as conn:
        rows = conn.execute(query).fetchall()

    for row in rows:
        try:
            raw_ctnt = row[0]
            match = re.search(r'"trasSno"\s*:\s*"(\d{14})"', raw_ctnt)
            if not match:
                continue

            tras_sno = match.group(1)  # e.g., '20250610103000'
            if not tras_sno.startswith(target_date):
                continue

            parsed_json = json.loads(raw_ctnt)
            parsed_json["_timestamp"] = datetime.strptime(tras_sno, "%Y%m%d%H%M%S")
            result.append(parsed_json)
        except Exception:
            continue

    return result
