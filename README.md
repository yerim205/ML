#  RMRP-AI
Realtime Medical Resources AI

---
## Interpreter Separation
- icu_congestion - .venv_congestion
- icu_discharge - .venv_discharge


## API 서버 실행
uvicorn main:app --reload


### 🧠 혼잡도 예측 요청 (`/congestion/recommend`)
![혼잡도 예측 요청](images/congestion_request.png)

---

### 🏥 퇴실 예측 요청 (`/discharge/recommend`)
![퇴실 예측 요청](images/discharge_request.png)