# # ─── model1: top3_transfer ────────────────────────
# @app.get("/transfer/recommend", response_model=RecommendResponse)
# def auto_transfer_recommend():
#     try:
#         from recommend.top3_transfer_recommend import auto_transfer_recommend
#         result = auto_transfer_recommend()
#         return RecommendResponse(result=result)
#     except Exception as e:
#         raise HTTPException(500, detail=str(e))

from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel
from typing import Any
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from typing import Optional

from recommend.top3_transfer_recommend import auto_transfer_recommend
from recommend.icu_congestion_recommend import recommend as congestion_recommend
from recommend.icu_discharge_recommend import auto_recommend as discharge_recommend

app = FastAPI()

# ─── 공통 응답 스키마 ──────────────────────
class RecommendResponse(BaseModel):
    result: Any
    
@app.get("/health-check")
async def healthCheck():
    return "ok"

# ─── ValidationError 핸들러: success=false 로 반환 ───────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=200,
        content={
            "success": False,
            "result": {
                "message": "요청 형식이 잘못되었거나 'icd'가 누락되었습니다.",
                "ward": []
            }
        }
    )

class ICDRequest(BaseModel):
    icd: str
    
# ─── model1: 전실 추천 (POST + JSON) ─────────────
@app.post("/transfer/recommend")
async def recommend_transfer(req: ICDRequest):
    try:
        icd_code = req.icd.strip().upper()

        if not icd_code:
            return JSONResponse(
                status_code=200,
                content={
                    "success": False,
                    "result": {
                        "message": "ICD 코드가 비어 있습니다.",
                        "ward": []
                    }
                }
            )

        result = auto_transfer_recommend(icd_code)
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "result": {
                    "ward": [w["ward"] for w in result.get("recommended_wards", [])]
                }
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=200,
            content={
                "success": False,
                "result": {
                    "message": f"전실 추천 오류: {e}",
                    "ward": []
                }
            }
        )
    
# ─── model2: ICU 혼잡도 (POST) ────────────────
@app.post("/congestion/recommend")
async def recommend_congestion():
    try:
        result = congestion_recommend({})
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "result": {
                    "prediction": int(result["prediction"])
                }
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=200,
            content={
                "success": False,
                "result": {
                    "message": f"혼잡도 예측 오류: {e}",
                    "prediction": None
                }
            }
        )


# ─── model3: ICU 퇴실 추천 (POST) ────────────────
@app.post("/discharge/recommend")
async def recommend_discharge():
    try:
        result = discharge_recommend()
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "result": {
                    "prediction": result 
                }
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=200,
            content={
                "success": False,
                "result": {
                    "message": f"퇴실 추천 오류: {e}",
                    "prediction": None
                }
            }
        )

    
# ─── 루트 엔드포인트 ────────────────────────
@app.get("/")
def root():
    return {
        "message": "RMRP AI Unified API is running!",
        "endpoints": [
            "/health-check",
            "/transfer/recommend",
            "/congestion/recommend",
            "/discharge/recommend"
        ]
    }
