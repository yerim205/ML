# 🏥 RMRP-AI API 테스트 가이드

이 문서는 `RMRP-AI` 프로젝트의 세 가지 추천 모델 API에 대해 Postman을 사용하여 테스트하는 방법을 설명합니다. 각 모델별 endpoint와 JSON 요청 예시를 포함합니다.

---

## 🔗 API 목록 및 설명

| 모델      | Endpoint                | 설명                                    |
| ------- | ----------------------- | ------------------------------------- |
| Model 1 | `/transfer/recommend`   | 질병 코드와 병상 현황을 기반으로 최적의 전실 병동 Top-K 추천 |
| Model 2 | `/congestion/recommend` | 혼잡도(혼잡 여부 및 확률)를 예측하는 ICU 상태 기반 모델    |
| Model 3 | `/discharge/recommend`  | 퇴실 가능 환자에 대한 예측 점수를 반환하는 모델           |

---

## 📦 1. /transfer/recommend (전실 추천)

* **Method:** POST
* **Content-Type:** application/json
* **예시 요청 JSON:**

```json
{
  "data": {
    "dissInfo": [
      { "dissCd": "I60" }
    ],
    "ptrmInfo": [
      {
        "ptntDtlsCtrlAllLst": [
          {
            "wardLst": [
              {
                "wardCd": "71병동",
                "embdCct": 2,
                "dschCct": 3,
                "useSckbCnt": 25,
                "admsApntCct": 1,
                "chupCct": 1
              },
              {
                "wardCd": "외과ICU",
                "embdCct": 1,
                "dschCct": 2,
                "useSckbCnt": 27,
                "admsApntCct": 0,
                "chupCct": 0
              },
              {
                "wardCd": "72병동",
                "embdCct": 2,
                "dschCct": 2,
                "useSckbCnt": 40,
                "admsApntCct": 1,
                "chupCct": 1
              }
            ]
          }
        ]
      }
    ],
    "topK": 3
  }
}
```

* **예시 응답:**

```json
{
  "result": {
    "recommended_wards": [
      { "ward": "외과ICU", "score": -1.65863 },
      { "ward": "71병동", "score": -1.75305 },
      { "ward": "72병동", "score": -2.19472 }
    ]
  }
}
```

---

## 📊 2. /congestion/recommend (혼잡도 예측)

* **Method:** POST
* **예시 요청 JSON:**

```json
{
  "data": {
    "free_beds": 3,
    "occ_rate": 0.87,
    "occupancy_change": 1,
    "occ_rate_lag1": 0.85,
    "occ_rate_lag7": 0.83,
    "is_weekend": 0,
    "is_public_holiday": 1,
    "month": 6,
    "quarter": 2
  }
}
```

* **예시 응답:**

```json
{
  "result": {
    "prediction": 0,
    "probability": 0.1599160012302308,
    "timestamp": "2025-06-16T10:35:05.558955"
  }
}
```

---

## 🏥 3. /discharge/recommend (퇴실 예측)

* **Method:** POST
* **예시 요청 JSON:**

```json
{
  "data": {
    "admissions": 20,
    "occupancy_rate": 0.85,
    "prev_dis": 18,
    "prev_week_dis": 15,
    "morning_ratio": 0.6,
    "afternoon_ratio": 0.4,
    "avg_age": 67.5,
    "male_ratio": 0.55,
    "female_ratio": 0.45,
    "dow": 0,
    "is_weekend": 0,
    "is_public_holiday": 0,
    "mon": 6,
    "ward_code": "ICU1"
  }
}
```

* **예시 응답:**

```json
{
  "result": {
    "prediction": 1.269538920437715,
    "timestamp": "2025-06-16T10:55:46.225368"
  }
}
```

---

## ✅ 참고 사항

* 모든 요청은 `application/json` 형식이며, 반드시 `"data": {...}` 구조로 감싸야 합니다.
* 응답의 `prediction`은 혼잡 여부(0/1), 점수(실수), 또는 병동 추천 리스트일 수 있습니다.
* 오류 발생 시 `"detail"` 필드의 메시지를 통해 JSON 구조 오류를 확인하세요.

---

## 🖼️ 테스트 화면 캡처

* `images/congestion_request.png`
* `images/discharge_request.png`
* `images/transfer_request.png`

---
