# api/schemas.py
# Pydantic 스키마 정의 (중첩 JSON 구조)
from pydantic import BaseModel
from typing import List, Optional

class WardRow(BaseModel):
    wardCd: str
    wardNm: str
    embdCct: int
    dschCct: int
    useSckbCnt: int
    admsApntCct: int
    chupCct: int
    trasItemLst: Optional[List[dict]] = []

class PtntDtlRow(BaseModel):
    itemCd: str
    itemNm: str
    wardLst: List[WardRow]

class PtrmInfoRow(BaseModel):
    ptrmDvsnCd: str
    sckbNm: str
    ptntDtlsCtrlAllLst: List[PtntDtlRow]

class PredictRequest(BaseModel):
    trasNo: str               # YYYYMMDDHHMMSS
    ptrmInfo: List[PtrmInfoRow]