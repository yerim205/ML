# # utils/api_to_feedback_converter.py
# from typing import List, Dict

# # ICD 코드 매핑 (중증질환 API → ICD)
# ICD_CODE_MAP = {
#     "01": "I21",  # 심정지-심근경색
#     "02": "I63",  # 심정지-뇌경색
#     "03": "I60",  # 거미막하출혈
#     "04": "I71",  # 급성대동맥(흉부)
#     "05": "I71",  # 급성대동맥(복부)
# }

# # 병동 추론 함수
# def infer_feedback_from_api(api: Dict) -> List[Dict]:
#     icds = []
#     diss_info = api.get("dissInfo", [])
    
#     for item in diss_info:
#         diss_cd = item.get("dissCd")
#         if diss_cd and diss_cd in ICD_CODE_MAP:
#             icds.append(ICD_CODE_MAP[diss_cd])

#     if not icds:
#         return []

#     inferred_wards = set()

#     sckb = api.get("sckbDtls", {})
#     eqpm = api.get("eqpmDtls", {})
#     oprm = api.get("oprmDtls", {})

#     # 병상 정보 기반 추론
#     if sckb.get("admsPsblYn") == "Y":
#         inferred_wards.update(["72병동", "76병동", "78병동", "75병동", "54병동"])
#     if sckb.get("erPsblYn") == "Y":
#         inferred_wards.add("응급센터")
#     if sckb.get("crptRomAdmsYn") == "Y":
#         inferred_wards.update(["외과ICU", "내과ICU", "응급중환자실"])


#     return [{"icd": icd, "wards": list(inferred_wards)} for icd in icds]
