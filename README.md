#  RMRP-AI
Realtime Medical Resources AI

---
## Interpreter Separation
- icu_congestion - .venv_congestion
- icu_discharge - .venv_discharge

## 각 모델별 API 서버 실행
icu_congestion
uvicorn icu_congestion.api.main:app --reload

icu_discharge
uvicorn icu_discharge.api.main:app --reload

top3_transfer
uvicorn runtime_manager:app --reload


curl -X POST http://localhost:8000/recommend \
     -H "Content-Type: application/json" \
     -d '{"dissInfo":[{"dissCd":"01-심근경색의 재관류중재술"}],"bedInfo":[{"ward":"69병동","embdCct":10,"dschCct":2,"useSckbCnt":5,"admsApntCct":1,"chupCct":0}]}'
