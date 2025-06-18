#utils/db_loader.py >> 병상 API
import os, json
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
from datetime import date, timedelta, time
from sqlalchemy import cast, DateTime

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, future=True)

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

def get_latest_realtime_data_for_days_ago(n: int) -> dict:
    from datetime import datetime, timedelta

    target_date = (datetime.now() - timedelta(days=n)).date()

    print(f"🔍 n일 전 쿼리 호출됨, n={n}, 날짜={target_date}")

    query = text("""
        SELECT ctnt, reg_dtm
          FROM rmrp_portal.tb_api_log
         WHERE req_res = 'REQ'
           AND com_src_cd = 'CMC03'
           AND req_url LIKE '%mdcl-rm-rcpt%'
           AND DATE(reg_dtm) = :target_date
         ORDER BY reg_dtm DESC
         LIMIT 1
    """)

    row = None
    with engine.connect() as conn:
        row = conn.execute(query, {"target_date": str(target_date)}).fetchone()

    if not row or not row[0]:
        raise ValueError(f"❌ {target_date}자 병상 API row 자체가 없습니다.")

    try:
        parsed = json.loads(row[0])
        parsed["_timestamp"] = row[1]  # ✅ row는 conn 닫히기 전에 가져왔기 때문에 OK
        print(f"✅ 쿼리 결과 timestamp: {row[1]}")
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
