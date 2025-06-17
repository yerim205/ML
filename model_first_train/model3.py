#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Best-CatBoost (native categorical) for next-day discharge count
  • ward_code → 네이티브 범주형
  • 수치 컬럼 : median 임퓨팅 → StandardScaler
  • Optuna(50 trial) 로 하이퍼파라미터 탐색
  • TimeSeriesSplit(5) 교차검증 MAE 리포트
"""

# ─────────────────────────────── 0) 라이브러리
from pathlib import Path
import warnings, pickle, numpy as np, pandas as pd, optuna

from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing    import StandardScaler
from sklearn.impute           import SimpleImputer
from sklearn.metrics          import mean_absolute_error

from catboost import CatBoostRegressor, Pool

warnings.filterwarnings("ignore", category=UserWarning)

SEED = 42
np.random.seed(SEED)

# ─────────────────────────────── 1) 설정
DATA_PATH  = Path("processed_ward_data_filled2.csv")
MODEL_PATH = Path("best_catboost_discharge.pkl")

CV_SPLITS  = 5
N_TRIALS   = 50                # Optuna trial 수

# ─────────────────────────────── 2) 데이터 로드 & 피처
def load_data() -> tuple[pd.DataFrame, pd.Series]:
    df = pd.read_csv(DATA_PATH, parse_dates=["date"])
    df = df.sort_values(["ward_code", "date"]).reset_index(drop=True)
    df["ward_code"] = df["ward_code"].fillna("unknown").astype(str)

    # 파생 피처
    df["prev_dis"]      = df.groupby("ward_code")["discharges"].shift(1)
    df["prev_week_dis"] = df.groupby("ward_code")["discharges"].shift(7)
    df["dow"]           = df["date"].dt.dayofweek
    df["mon"]           = df["date"].dt.month

    # 타깃
    df["target"] = df.groupby("ward_code")["discharges"].shift(-1)
    df = df.dropna(subset=["target"]).reset_index(drop=True)
    return df

df = load_data()

NUM_COLS = [
    "admissions", "occupancy_rate",
    "prev_dis", "prev_week_dis",
    "morning_ratio", "afternoon_ratio",
    "dow", "is_weekend"
]
CAT_COL  = "ward_code"

# ─────────────────────────────── 3) 수치 전처리 (median → scaler)
num_imputer = SimpleImputer(strategy="median").fit(df[NUM_COLS])
num_vals    = num_imputer.transform(df[NUM_COLS])
scaler      = StandardScaler().fit(num_vals)
X_num       = scaler.transform(num_vals)

# 합쳐서 최종 Feature DataFrame
X_full = pd.DataFrame(X_num, columns=NUM_COLS)
X_full[CAT_COL] = df[CAT_COL].values
y_full  = df["target"].values.astype(float)

# ─────────────────────────────── 4) Optuna 목적 함수
tscv = TimeSeriesSplit(n_splits=CV_SPLITS)

def objective(trial):
    params = {
        "loss_function": "MAE",
        "iterations"   : trial.suggest_int("iterations", 400, 1200),
        "depth"        : trial.suggest_int("depth", 4, 8),
        "learning_rate": trial.suggest_float("learning_rate", 0.02, 0.3, log=True),
        "l2_leaf_reg"  : trial.suggest_float("l2_leaf_reg", 1, 10, log=True),
        "bagging_temperature": trial.suggest_float("bagging_temperature", 0, 1),
        "subsample"    : trial.suggest_float("subsample", 0.6, 1.0),
        "random_seed"  : SEED,
        "verbose"      : False
    }
    maes = []
    for tr_idx, te_idx in tscv.split(X_full):
        cb = CatBoostRegressor(**params).fit(
            Pool(X_full.iloc[tr_idx], y_full[tr_idx], cat_features=[CAT_COL]))
        pred = cb.predict(X_full.iloc[te_idx])
        maes.append(mean_absolute_error(y_full[te_idx], pred))
    return np.mean(maes)

study = optuna.create_study(direction="minimize",
                            sampler=optuna.samplers.TPESampler(seed=SEED))
study.optimize(objective, n_trials=N_TRIALS, show_progress_bar=True)

best_params = {**study.best_params,
               "loss_function":"MAE",
               "random_seed" : SEED,
               "verbose"     : False}

print(f"\n▶ Optuna best MAE  : {study.best_value:.4f}")
print(f"▶ Best params      : {best_params}")

# ─────────────────────────────── 5) 교차검증 성능 리포트
maes = []
for fold, (tr, te) in enumerate(tscv.split(X_full), 1):
    cb = CatBoostRegressor(**best_params).fit(
        Pool(X_full.iloc[tr], y_full[tr], cat_features=[CAT_COL]))
    preds = cb.predict(X_full.iloc[te])
    mae   = mean_absolute_error(y_full[te], preds)
    maes.append(mae)
    print(f"Fold {fold}: MAE={mae:.3f}")

print(f"\n=== CatBoost(native) CV MAE : {np.mean(maes):.3f} ± {np.std(maes):.3f}\n")

# ─────────────────────────────── 6) 전체 데이터 재학습 & 저장
cb_final = CatBoostRegressor(**best_params).fit(
    Pool(X_full, y_full, cat_features=[CAT_COL]))

with open(MODEL_PATH, "wb") as f:
    pickle.dump({
        "num_imputer": num_imputer,
        "scaler"    : scaler,
        "cat_model" : cb_final,
        "num_cols"  : NUM_COLS,
        "cat_col"   : CAT_COL
    }, f)
print(f"✔ Tuned CatBoost model saved → {MODEL_PATH}")

# ─────────────────────────────── 7) 내일 예측 데모
latest_row = df.iloc[-1]                         # 가장 최근 레코드
# 수치 전처리 재적용
x_num = scaler.transform(num_imputer.transform(
        latest_row[NUM_COLS].to_frame().T))
x_df  = pd.DataFrame(x_num, columns=NUM_COLS)
x_df[CAT_COL] = latest_row[CAT_COL]

pred_cnt = cb_final.predict(x_df)[0]
print(f"예상되는 내일 전실(퇴원) 환자 수: {pred_cnt:.1f}명")
