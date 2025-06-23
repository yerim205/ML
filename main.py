from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Any
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

import subprocess
import os
import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager

from recommend.top3_transfer_recommend import auto_transfer_recommend
from recommend.icu_congestion_recommend import auto_congestion_recommend
from recommend.icu_discharge_recommend import auto_recommend

from dotenv import load_dotenv
load_dotenv()

# ─── 로깅 설정 ──────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        scheduler_path = os.path.join(os.path.dirname(__file__), "api", "scheduler.py")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(os.path.dirname(__file__))  # 현재 루트 경로 명시
        subprocess.Popen(["python", scheduler_path], env=env)
        logger.info("스케줄러가 백그라운드에서 실행되었습니다.")
    except Exception as e:
        logger.error(f"스케줄러 실행 실패: {e}")
    yield  # 서버가 실행됨
#     logger.info("FastAPI 서버 종료")


app = FastAPI(lifespan=lifespan)
# app = FastAPI()

@app.get("/health-check")
async def healthCheck():
    return "ok"

# ─── 공통 응답 스키마 ──────────────────────
class RecommendResponse(BaseModel):
    result: Any
    
class ICDRequest(BaseModel):
    icd: str

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
    
# ─── model1: 전실 추천 (POST + JSON) ─────────────
@app.post("/transfer/recommend", response_model=RecommendResponse)
async def recommend_transfer(req: ICDRequest):
    try:
        icd_code = req.icd.strip().upper()
        result = auto_transfer_recommend(icd_code)
        ward_list = [w["ward"] for w in result.get("recommended_wards", [])]

        if not ward_list:
            return JSONResponse(
                status_code=200,
                content={
                    "success": False,
                    "result": {
                        "message": "추천 가능한 병동이 없습니다.",
                        "ward": []
                    }
                }
            )

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "result": {
                    "ward": ward_list
                }
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "result": {
                    "message": f"전실 추천 오류: {e}",
                    "ward": []
                }
            }
        )

from fastapi import Query

# ─── model2: ICU 혼잡도 (POST) ────────────────
@app.post("/congestion/recommend")
async def recommend_congestion():
    try:
        res = auto_congestion_recommend({})

        # 실패한 경우 그대로 반환
        if not res.get("success", False):
            return JSONResponse(status_code=200, content=res)

        # 성공한 경우: prediction이 없으면 에러로 처리
        result = res.get("result", {})
        if "prediction" not in result:
            raise ValueError("예측 결과 'prediction'이 없습니다.")

        prediction = int(result["prediction"])
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "result": {
                    "prediction": prediction
                }
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "result": {
                    "message": f"혼잡도 예측 오류: {str(e)}",
                    "prediction": None
                }
            }
        )
# ─── model3: ICU 퇴실 추천 (POST) ────────────────
@app.post("/discharge/recommend")
async def recommend_discharge():
    try:
        prediction = auto_recommend()

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "result": {
                    "prediction": prediction
                }
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "result": {
                    "message": f"퇴원 예측 오류: {str(e)}",
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


