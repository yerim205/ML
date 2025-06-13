# mapping.py

# API의 dissCd 한글명 → 모델이 쓰는 ICD 코드 매핑
DISSCD_TO_ICD = {
    "심근경색의 재관류중재술": "I21",
    "뇌경색의 재관류중재술":   "I63",
    "뇌출혈수술(거미막하출혈)":  "I60",
    "대동맥응급질환(흉부)":     "I71",
    "대동맥응급질환(복부)":     "I71",
}
#아래부분 수정 필요 
def extract_icd(raw_dissCd: str) -> str:
    # "01-심근경색의 재관류중재술" → "심근경색의 재관류중재술"
    name = raw_dissCd.split("-", 1)[1].strip()
    if name not in DISSCD_TO_ICD:
        raise KeyError(f"Unknown disease name: {name}")
    return DISSCD_TO_ICD[name]
