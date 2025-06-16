# # recommend/top3_transfer_recommend.py
# from pathlib import Path
# from joblib import load
# from recommend.hybrid_scheduler import HybridScheduler

# MODEL_PATH = Path(__file__).parent.parent / "model/model1.pkl"
# model: HybridScheduler = load(MODEL_PATH)

# def recommend(input_data: dict) -> dict:
#     """
#     입력 형식: {
#         "diagnosis_code": str,
#         "current_bed_info": dict,
#         "top_k": int
#     }
#     출력 형식: {"recommended_wards": [{"ward": str, "score": float}]}
#     """
#     result = model.recommend(
#         input_data["diagnosis_code"],
#         input_data["current_bed_info"],
#         top_k=input_data.get("top_k", 3)
#     )
#     return {"recommended_wards": result}
