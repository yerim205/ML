from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, Callable

# from recommend.hybrid_scheduler import HybridScheduler

# 추천 함수만 임포트
# from recommend.top3_transfer_recommend import recommend as transfer_recommend
from recommend.icu_congestion_recommend import recommend as congestion_recommend
from recommend.icu_discharge_recommend import recommend as discharge_recommend

app = FastAPI()

# transfer_scheduler = HybridScheduler("model/model1.pkl")
# congestion_scheduler = HybridScheduler("model/model2.pkl")
# discharge_scheduler = HybridScheduler("model/model3.pkl")

# ─── 공통 요청/응답 스키마 ─────────────────
class RecommendRequest(BaseModel):
    data: Dict[str, Any] = Field(
        ...,
        description="원시 API 요청 바디 전체를 data 로 받습니다."
    )

class RecommendResponse(BaseModel):
    result: Any

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

# # ─── /transfer/recommend ───────────────────
# @app.post("/transfer/recommend", response_model=RecommendResponse)
# def transfer_endpoint(req: RecommendRequest):
#     body = req.data

#     # 1) 중증질환 코드 추출 & 변환
#     try:
#         raw_diss = body["dissInfo"][0]["dissCd"]
#         icd = extract_icd(raw_diss)
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=f"dissCd 파싱 오류: {e}")

#     # 2) ptrmInfo → ptntDtlsCtrlAllLst → wardLst 평탄화
#     bed_rows: List[Dict[str, Any]] = []
#     for ptrm in body.get("ptrmInfo", []):
#         for ctrl in ptrm.get("ptntDtlsCtrlAllLst", []):
#             for ward in ctrl.get("wardLst", []):
#                 bed_rows.append({
#                     "wardCd":     ward.get("wardCd"),
#                     "embdCct":    ward.get("embdCct", 0),
#                     "dschCct":    ward.get("dschCct", 0),
#                     "useSckbCnt": ward.get("useSckbCnt", 0),
#                     "admsApntCct":ward.get("admsApntCct",0),
#                     "chupCct":    ward.get("chupCct", 0),
#                 })
#     if not bed_rows:
#         raise HTTPException(status_code=400, detail="병상 정보(ptrmInfo) 누락")

#     # 3) topK 옵션
#     topk = body.get("topK", 1)

#     # 4) 모델 호출
#     try:
#         result = transfer_recommend({
#             "dissCd": icd,
#             "bedInfo": bed_rows,
#             "topK": topk
#         })
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Transfer 추천 오류: {e}")

#     return RecommendResponse(result=result)

# --- model2: icu_congestion ---
@app.post("/congestion/recommend", response_model=RecommendResponse)
def model2_recommend(req: RecommendRequest):
    try:
        res = congestion_recommend(req.data)
        # res = congestion_scheduler.recommend(req.data)
    except Exception as e:
        raise HTTPException(500, detail=str(e))
    return RecommendResponse(result=res)

# --- model3: icu_discharge ---
@app.post("/discharge/recommend", response_model=RecommendResponse)
def discharge_endpoint(req: RecommendRequest) -> RecommendResponse:
    return handle_recommendation(discharge_recommend, req)

@app.get("/")
async def root():
    return {"message": "RMPR AI Unified API is running!"}