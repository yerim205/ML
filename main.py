# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel, Field
# from typing import Any, Dict, Callable

# from recommend.hybrid_scheduler import HybridScheduler

# # 추천 함수만 임포트
# from recommend.icu_congestion_recommend import recommend as congestion_recommend
# from recommend.icu_discharge_recommend import auto_recommend  
# from recommend.top3_transfer_recommend import auto_transfer_recommend



# app = FastAPI()

# transfer_scheduler = HybridScheduler()

# # ─── 공통 요청/응답 스키마 ─────────────────
# class RecommendRequest(BaseModel):
#     data: Dict[str, Any] = Field(
#         ...,
#         description="원시 API 요청 바디 전체를 data 로 받습니다."
#     )

# class RecommendResponse(BaseModel):
#     result: Any

# def extract_icd(raw_diss: str) -> str:
#     return raw_diss.strip().upper()

# # ─── 공통 처리 함수 ────────────────────────
# def handle_recommendation(
#     recommender: Callable[[Dict[str, Any]], Any], 
#     req: RecommendRequest
# ) -> RecommendResponse:
#     try:
#         result = recommender(req.data)
#         return RecommendResponse(result=result)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"추천 오류: {e}")
    
# # ─── model1: top3_transfer ────────────────────────
# @app.get("/transfer/recommend", response_model=RecommendResponse)
# def auto_transfer_recommend():
#     try:
#         from recommend.top3_transfer_recommend import auto_transfer_recommend
#         result = auto_transfer_recommend()
#         return RecommendResponse(result=result)
#     except Exception as e:
#         raise HTTPException(500, detail=str(e))

# # --- model2: icu_congestion ---

# @app.get("/congestion/recommend", response_model=RecommendResponse)
# def model2_recommend_auto() -> RecommendResponse:
#     try:
#         from recommend.icu_congestion_recommend import auto_recommend
#         result = auto_recommend()
#         return RecommendResponse(result=result)
#     except Exception as e:
#         raise HTTPException(500, detail=str(e))


# # --- model3: icu_discharge ---

# @app.get("/discharge/recommend", response_model=RecommendResponse)
# def model3_auto_endpoint():
#     try:
#         res = auto_recommend()
#     except Exception as e:
#         raise HTTPException(500, detail=str(e))
#     return RecommendResponse(result=res)


# @app.get("/")
# async def root():
#     return {
#         "message": "RMRP AI Unified API is running!",
#         "endpoints": [
#             "/transfer/recommend",
#             "/congestion/recommend",
#             "/discharge/recommend"
#         ]
#     }

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any

from recommend.top3_transfer_recommend import auto_transfer_recommend
from recommend.icu_congestion_recommend import recommend as congestion_recommend
from recommend.icu_discharge_recommend import auto_recommend as discharge_recommend

app = FastAPI()

# ─── 공통 응답 스키마 ──────────────────────
class RecommendResponse(BaseModel):
    result: Any

# ─── model1: 전실 추천 ──────────────────────
@app.get("/transfer/recommend", response_model=RecommendResponse)
def recommend_transfer():
    try:
        result = auto_transfer_recommend()
        return RecommendResponse(result=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"전실 추천 오류: {e}")

# ─── model2: ICU 혼잡도 ─────────────────────
@app.get("/congestion/recommend", response_model=RecommendResponse)
def recommend_congestion():
    try:
        result = congestion_recommend({})
        return RecommendResponse(result=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"혼잡도 예측 오류: {e}")

# ─── model3: ICU 퇴실 추천 ──────────────────
@app.post("/discharge/recommend", response_model=RecommendResponse)
def recommend_discharge():
    try:
        result = discharge_recommend()
        return RecommendResponse(result=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"퇴실 추천 오류: {e}")

# ─── 루트 엔드포인트 ────────────────────────
@app.get("/")
def root():
    return {
        "message": "RMRP AI Unified API is running!",
        "endpoints": [
            "/transfer/recommend",
            "/congestion/recommend",
            "/discharge/recommend"
        ]
    }
