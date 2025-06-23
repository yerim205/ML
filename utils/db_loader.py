#utils/db_loader.py >> 병상 API
import os, json
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, URL
from datetime import datetime, timedelta
from datetime import date, timedelta, time
from sqlalchemy import cast
import pandas as pd

load_dotenv()
# .env에서 DATABASE_URL 직접 불러오기
from sqlalchemy import create_engine
from dotenv import load_dotenv
from pathlib import Path
import os

# 환경변수 로드
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=ROOT / ".env")

# URL 한 줄로 로딩
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, future=True)

# DB_URL  = os.getenv("DB_URL")
# DB_PORT = os.getenv("DB_PORT")
# DB_USER = os.getenv("DB_USER")
# DB_PW   = os.getenv("DB_PW")

# URL_OBJ = URL.create(
#     drivername="mysql+pymysql",
#     username=DB_USER,
#     password=DB_PW,
#     host=DB_URL,
#     port=DB_PORT,
# )
# engine  = create_engine(URL_OBJ, future=True)

def get_latest_realtime_data() -> dict:
    query = text("""
        SELECT ctnt, reg_dtm
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
            data = json.loads(row[0])
            data["_timestamp"] = row[1]  # reg_dtm 기반 시간 추가
            return data
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 파싱 실패: {e}")

def get_realtime_data_for_today() -> list[dict]:
    today = datetime.now().date()

    query = text("""
        SELECT ctnt, reg_dtm
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
            reg_dtm = row[1]
            if reg_dtm.date() != today:
                continue

            parsed_json = json.loads(row[0])
            parsed_json["_timestamp"] = reg_dtm
            results.append(parsed_json)
        except Exception:
            continue

    return results

def get_realtime_data_for_days_ago(n: int) -> list[dict]:
    target_date = (datetime.now() - timedelta(days=n)).date()

    query = text("""
        SELECT ctnt, reg_dtm
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
            reg_dtm = row[1]
            if reg_dtm.date() != target_date:
                continue

            parsed_json = json.loads(row[0])
            parsed_json["_timestamp"] = reg_dtm
            result.append(parsed_json)
        except Exception:
            continue

    return result

def get_latest_realtime_data_for_days_ago(n: int, base_ts: datetime | None = None) -> dict:
    """
    가장 최근 시각(base_ts)을 기준으로 n일 전 데이터를 가져온다.
    base_ts가 없으면 datetime.now()를 사용(이전 동작과 호환).
    """
    if base_ts is None:
        base_ts = datetime.now()

    target_day = base_ts.date() - timedelta(days=n)
    start_dt   = datetime.combine(target_day, datetime.min.time())
    end_dt     = datetime.combine(target_day, datetime.max.time())

    query = text("""
         SELECT ctnt, reg_dtm
        FROM rmrp_portal.tb_api_log
        WHERE req_res = 'REQ'
        AND com_src_cd = 'CMC03'
        AND req_url LIKE '%mdcl-rm-rcpt%'
        AND ctnt IS NOT NULL
        AND reg_dtm BETWEEN :start_dt AND :end_dt
        ORDER BY reg_dtm DESC
        LIMIT 1
    """)

    with engine.connect() as conn:
        row = conn.execute(query, {"start_dt": start_dt, "end_dt": end_dt}).fetchone()
   # print(f"[DEBUG] DB 연결 정보: {engine.url}")

    if not row:
        raise ValueError(f"{target_day}자 병상 API row 자체가 없습니다.")
    if not row[0]:
        raise ValueError(f"{target_day}자 병상 API ctnt 값이 비어 있습니다.")

    try:
        parsed = json.loads(row[0])
        parsed["_timestamp"] = row[1]
        return parsed 
    except Exception as e:
        raise ValueError(f"JSON 파싱 실패: {e}")



        
def get_realtime_data_for_date(target_date: date) -> list[dict]:
    """
    특정 날짜의 reg_dtm이 해당 날짜로 시작하는 병상 요청 JSON 데이터 추출.
    `_timestamp` 필드를 reg_dtm 기준으로 추가하여 반환.
    """
    query = text("""
        SELECT ctnt, reg_dtm
          FROM rmrp_portal.tb_api_log
         WHERE req_res = 'REQ'
           AND com_src_cd = 'CMC03'
           AND req_url LIKE '%mdcl-rm-rcpt%'
           AND DATE(reg_dtm) = :target_date
         ORDER BY reg_dtm DESC
    """)

    results = []

    with engine.connect() as conn:
        rows = conn.execute(query, {"target_date": target_date}).fetchall()

    for row in rows:
        try:
            raw_ctnt = row[0]
            reg_dtm = row[1]
            parsed_json = json.loads(raw_ctnt)
            parsed_json["_timestamp"] = reg_dtm  # reg_dtm 기준
            results.append(parsed_json)
        except Exception:
            continue

    return results


def safe_get_realtime_data_for_today():
    today = datetime.today().date()

    today_data = get_realtime_data_for_date(today)
    if today_data:
        print("오늘 날짜 기준 DB 데이터가 있습니다.")
        return today_data

    # 없다면 최신 데이터 fallback
    print("오늘 데이터가 없어 최신 데이터를 대신 반환합니다.")
    latest_data = get_latest_realtime_data()

    ts = latest_data.get("_timestamp")
    if ts and isinstance(ts, datetime):
        print("가장 최신 reg_dtm:", ts)
        if ts.date() == today:
            print("reg_dtm 기준으로도 오늘 데이터로 간주합니다.")
            return [latest_data]
        else:
            print("reg_dtm 기준으로도 오늘 데이터가 아닙니다.")
            return [latest_data]
    else:
        print("_timestamp가 누락되어 있음")
        return [latest_data]
    
#retrian에서 사용하는 것 >> n일 전 데이터전체 로그 긁어오기
def get_api_logs_raw(days: int) -> pd.DataFrame:
    query = text("""
        SELECT ctnt, reg_dtm
          FROM rmrp_portal.tb_api_log
         WHERE req_res = 'REQ'
           AND reg_dtm >= NOW() - INTERVAL :d DAY
           AND com_src_cd = 'CMC03'
    """)
    with engine.connect() as conn:
        return pd.read_sql(query, conn, params={"d": days})
    
def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # ward_code 인코딩: 범주형 → 숫자형
    if df["ward_code"].dtype == object or str(df["ward_code"].dtype).startswith("category"):
        df["ward_code"] = df["ward_code"].astype("category").cat.codes

    # occ_rate_7d_ago: 결측치 처리
    if "occ_rate_7d_ago" in df.columns:
        mean_value = df["occ_rate_7d_ago"].mean()
        df["occ_rate_7d_ago"].fillna(mean_value, inplace=True)

    # 그 외 수치형 결측치도 0으로 처리
    df.fillna(0, inplace=True)

    # 컬럼 순서 정리 (선택)
    expected_cols = ["ward_code", "total_beds", "occupied_beds", "occ_rate_7d_ago"]
    df = df[[col for col in expected_cols if col in df.columns]]

    return df