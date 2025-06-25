from datetime import datetime
from io import BytesIO
from joblib import load
import logging
from utils import ncp_client
from typing import List

logger = logging.getLogger(__name__)

def extract_date_from_key(key: str) -> datetime:
    try:
        filename = key.split("/")[-1]  # 예: model3_20250623.pkl
        date_str = filename.replace("model3_", "").replace(".pkl", "")
        return datetime.strptime(date_str, "%Y%m%d")
    except Exception as e:
        logger.warning(f"날짜 파싱 실패: {key} → {e}")
        return datetime.min  # 잘못된 포맷은 최소값 반환

def get_latest_model3_key(keys: List[str]) -> str:
    """NCP 키 리스트 중 가장 최신 model3 키 반환"""
    sorted_keys = sorted(keys, key=extract_date_from_key, reverse=True)
    return sorted_keys[0] if sorted_keys else None

def load_model_from_ncp_direct(ncp_key: str):
    logger.info(f"NCP에서 모델 직접 다운로드 중: {ncp_key}")
    byte_data = ncp_client.get_object_bytes(ncp_key)  # NCP에서 byte로 읽기
    model_data = load(BytesIO(byte_data))
    return model_data

