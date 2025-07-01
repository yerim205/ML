import numpy as np
import pandas as pd
import pickle
from pathlib import Path

from sklearn.preprocessing import StandardScaler
from imblearn.over_sampling import RandomOverSampler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import (
    roc_auc_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    f1_score
)
from catboost import CatBoostClassifier

# 0) 데이터 로드 & 피처 생성
PATH = Path("/Users/yerim/Desktop/ML_v2/ward_daily_summary.csv")
df_raw = pd.read_csv(PATH, parse_dates=["date"])

def make_features(df):
    df = df.sort_values(["ward_code","date"]).reset_index(drop=True)

    # 기본 수치
    df["free_beds"] = df["total_beds"] - df["occupied_beds"]
    df["occ_rate"]  = df["occupied_beds"] / df["total_beds"]

    # 변화량·추세
    df["prev_occupied"]    = df.groupby("ward_code")["occupied_beds"].shift(1)
    df["occupancy_change"] = df["occupied_beds"] - df["prev_occupied"]
    for lag in (1, 7):
        df[f"occ_rate_lag{lag}"] = df.groupby("ward_code")["occ_rate"].shift(lag)

    # 레이블: 내일 점유율 > 0.90
    df["occ_rate_t+1"] = df.groupby("ward_code")["occ_rate"].shift(-1)
    df["is_full_t+1"]  = (df["occ_rate_t+1"] > 0.90).astype(int)

    cols = [
        "free_beds","occ_rate","occupancy_change",
        "occ_rate_lag1","occ_rate_lag7",
        "is_weekend","is_full_t+1"
    ]
    return df[cols].dropna().reset_index(drop=True)

df = make_features(df_raw)
feature_cols = df.columns.drop("is_full_t+1")
X = df[feature_cols].values
y = df["is_full_t+1"].values
print("샘플:", len(df), "| 양성 비율:", round(y.mean(),3))


# 1) CV용 분할 함수
def split_with_min_pos(X, y, n_splits=6, min_pos=20, expand_ratio=0.7):
    tscv = TimeSeriesSplit(n_splits=n_splits)
    for tr_idx, te_idx in tscv.split(X):
        if y[te_idx].sum() < min_pos:
            extra = int(len(te_idx)*expand_ratio)
            te_idx = np.arange(te_idx[0], te_idx[-1]+extra+1)
        yield tr_idx, te_idx


# 2) CV 평가
cb_params = {
    "loss_function": "Logloss",
    "iterations": 600,
    "depth": 6,
    "learning_rate": 0.05,
    "l2_leaf_reg": 3,
    "auto_class_weights": "Balanced",
    # "verbose": False
}
seeds = list(range(20))
results, fold = [], 0

for tr_idx, te_idx in split_with_min_pos(X, y):
    fold += 1
    X_tr, y_tr = X[tr_idx], y[tr_idx]
    X_te, y_te = X[te_idx], y[te_idx]

    # 스케일 & 오버샘플
    scaler = StandardScaler().fit(X_tr)
    X_tr_s, X_te_s = scaler.transform(X_tr), scaler.transform(X_te)
    X_bal, y_bal = RandomOverSampler(random_state=42).fit_resample(X_tr_s, y_tr)

    # 20개 앙상블
    probas = []
    for s in seeds:
        m = CatBoostClassifier(**cb_params, random_seed=s)
        m.fit(X_bal, y_bal)
        probas.append(m.predict_proba(X_te_s)[:,1])
    proba = np.mean(probas, axis=0)

    # 지표 계산
    auc  = roc_auc_score(y_te, proba)
    p, r, t = precision_recall_curve(y_te, proba)
    p,r   = p[:-1], r[:-1]
    thr   = t[(r>=0.60)&(p>=0.40)].max(initial=0.5)
    pred = (proba>=thr).astype(int)

    results.append({
        "fold": fold,
        "auc": auc,
        "precision": precision_score(y_te, pred, zero_division=0),
        "recall":    recall_score(y_te, pred, zero_division=0),
        "f1":        f1_score(y_te, pred, zero_division=0)
    })
    print(f"Fold{fold}: AUC={auc:.3f} P={results[-1]['precision']:.2f} "
          f"R={results[-1]['recall']:.2f}")

cv = pd.DataFrame(results)
print("\n=== CV 결과 ===")
print(cv)


# 3) 전체 데이터로 재학습해서 모델 저장
# — CV 이후, 전체 X,y로 “스케일링→오버샘플→20개 CatBoost” 앙상블을 한 번 더 학습하고 pickle로 덤프

# 3-1) 스케일 & 오버샘플
scaler_full = StandardScaler().fit(X)
X_s_full   = scaler_full.transform(X)
X_bal_full, y_bal_full = RandomOverSampler(random_state=42).fit_resample(X_s_full, y)

# 3-2) 앙상블 모델 학습
models_full = []
for s in seeds:
    m = CatBoostClassifier(**cb_params, random_seed=s, verbose=False)
    m.fit(X_bal_full, y_bal_full)
    models_full.append(m)

# 3-3) 저장할 객체 묶기
model_bundle = {
    "scaler": scaler_full,
    "models": models_full,
    "threshold_logic": {"r_min":0.60, "p_min":0.40, "default_thr":0.5}
}

with open("model2.pkl", "wb") as f:
    pickle.dump(model_bundle, f)

print("전체 앙상블 모델을 'ward_ensemble_model.pkl'에 저장.")
