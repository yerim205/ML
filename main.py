from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, Callable

from recommend.hybrid_scheduler import HybridScheduler

# 추천 함수만 임포트
from recommend.icu_congestion_recommend import recommend as congestion_recommend
from recommend.icu_discharge_recommend import auto_recommend  
from recommend.top3_transfer_recommend import auto_transfer_recommend


app = FastAPI()

transfer_scheduler = HybridScheduler()

# ─── 공통 요청/응답 스키마 ─────────────────
class RecommendRequest(BaseModel):
    data: Dict[str, Any] = Field(
        ...,
        description="원시 API 요청 바디 전체를 data 로 받습니다."
    )

class RecommendResponse(BaseModel):
    result: Any

def extract_icd(raw_diss: str) -> str:
    return raw_diss.strip().upper()

# ─── 공통 처리 함수 ────────────────────────
def handle_recommendation(
    recommender: Callable[[Dict[str, Any]], Any], 
    req: RecommendRequest
) -> RecommendResponse:
    try:
        result = recommender(req.data)
        return RecommendResponse(result=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추천 오류: {e}")
    
# ─── model1: top3_transfer ────────────────────────
@app.get("/transfer/recommend", response_model=RecommendResponse)
def auto_transfer_recommend():
    try:
        from recommend.top3_transfer_recommend import auto_transfer_recommend
        result = auto_transfer_recommend()
        return RecommendResponse(result=result)
    except Exception as e:
        raise HTTPException(500, detail=str(e))

# --- model2: icu_congestion ---

@app.get("/congestion/recommend", response_model=RecommendResponse)
def model2_recommend_auto() -> RecommendResponse:
    try:
        from recommend.icu_congestion_recommend import auto_recommend
        result = auto_recommend()
        return RecommendResponse(result=result)
    except Exception as e:
        raise HTTPException(500, detail=str(e))


# --- model3: icu_discharge ---

@app.get("/discharge/recommend", response_model=RecommendResponse)
def model3_auto_endpoint():
    try:
        res = auto_recommend()
    except Exception as e:
        raise HTTPException(500, detail=str(e))
    return RecommendResponse(result=res)


@app.get("/")
async def root():
    return {
        "message": "RMRP AI Unified API is running!",
        "endpoints": [
            "/transfer/recommend",
            "/congestion/recommend",
            "/discharge/recommend"
        ]
    }
"""
# main.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any
from utils.ncp_client import load_pickle_from_ncp
from recommend.top3_transfer_recommend import recommend as transfer_recommend
from recommend.icu_congestion_recommend import recommend as congestion_recommend
from recommend.icu_discharge_recommend import recommend as discharge_recommend

# ─── 모델 로드 ─────
model1 = load_pickle_from_ncp("model/model1.pkl")
model2 = load_pickle_from_ncp("model/model2.pkl")
model3 = load_pickle_from_ncp("model/model3.pkl")

# FastAPI 앱 생성
app = FastAPI()

class RecommendRequest(BaseModel):
    data: Dict[str, Any]

class RecommendResponse(BaseModel):
    result: Any

@app.post("/transfer/recommend", response_model=RecommendResponse)
def transfer_recommend_endpoint(req: RecommendRequest):
    try:
        return RecommendResponse(result=transfer_recommend(req.data))
    except Exception as e:
        raise HTTPException(500, detail=str(e))

@app.post("/congestion/recommend", response_model=RecommendResponse)
def congestion_recommend_endpoint(req: RecommendRequest):
    try:
        return RecommendResponse(result=congestion_recommend(req.data))
    except Exception as e:
        raise HTTPException(500, detail=str(e))

@app.post("/discharge/recommend", response_model=RecommendResponse)
def discharge_recommend_endpoint(req: RecommendRequest):
    try:
        return RecommendResponse(result=discharge_recommend(req.data))
    except Exception as e:
        raise HTTPException(500, detail=str(e))
"""