'''runtime_manager.py

아직 수정 필요
'''
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import joblib
import pandas as pd

from mapping import extract_icd
scheduler = joblib.load('hybrid_scheduler_initial.pkl')

app = FastAPI(title="Hybrid Scheduler API")

# ----- Request/Response Schemas -----
class BedInfo(BaseModel):
    ward: str
    embdCct: int
    dschCct: int
    useSckbCnt: int
    admsApntCct: int
    chupCct: int

class RecommendRequest(BaseModel):
    dissInfo: List[Dict[str, Any]] = Field(..., description="질환 정보 리스트; dissCd 필수")
    bedInfo: List[BedInfo] = Field(..., description="실시간 병상 정보")
    topK: Optional[int] = Field(1, ge=1, description="상위 K개 추천")

class RecommendResponse(BaseModel):
    icd: str
    recommendations: List[Dict[str, Any]]

def make_state_from_df(df: pd.DataFrame) -> Dict[str, Dict[str, int]]:
    df = df.copy()
    df['total_beds'] = df.embdCct + df.dschCct + df.useSckbCnt + df.admsApntCct + df.chupCct
    agg = df.groupby('ward').agg(total=('total_beds','first'), occupied=('useSckbCnt','sum')).reset_index()
    return {r.ward: {'total': int(r.total), 'occupied': int(r.occupied)} for r in agg.itertuples()}

@app.post('/recommend', response_model=RecommendResponse)
def recommend(req: RecommendRequest):
    # Extract ICD from first dissInfo
    try:
        raw = req.dissInfo[0]['dissCd']
        icd = extract_icd(raw)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid dissCd: {e}")
    df_live = pd.DataFrame([b.dict() for b in req.bedInfo])
    state = make_state_from_df(df_live)
    recs = scheduler.recommend(icd, df_live, top_k=req.topK)
    return RecommendResponse(icd=icd,
        recommendations=[{'ward': w, 'score': float(score)} for w, score in recs]
    )

class FeedbackRecord(BaseModel):
    dissCd: str
    assignedWard: str
    acptYn: str

class FeedbackRequest(BaseModel):
    feedback: List[FeedbackRecord]

@app.post('/feedback')
def feedback(req: FeedbackRequest):
    records = []
    for rec in req.feedback:
        try:
            icd = extract_icd(rec.dissCd)
        except:
            continue
        reward = 1.0 if rec.acptYn == 'Y' else 0.0
        records.append({'icd': icd, 'ward': rec.assignedWard, 'reward': reward})
    scheduler.update_feedback(records)
    return {'status': 'ok', 'records_processed': len(records)}
