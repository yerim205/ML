#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Train CatBoost model for next-day discharge count (compatible with sklearn==1.5.1)
"""

import numpy as np
import pandas as pd
import pickle
import optuna
from pathlib import Path
import warnings

from sklearn.model_selection import TimeSeriesSplit
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error
from catboost import CatBoostRegressor, Pool

# ───── 설정 ─────
warnings.filterwarnings("ignore", category=UserWarning)
SEED = 42
np.random.seed(SEED)

DATA_PATH = Path("/Users/yerim/Downloads/rmrp-ai-dev/model_first_train/processed_ward_data_filled2.csv")
MODEL_PATH = Path("/Users/yerim/Downloads/rmrp-ai-dev/model/model3.pkl")
CV_SPLITS = 5
N_TRIALS = 50

# ───── 데이터 로딩 및 피처 생성 ─────
def load_data():
    df = pd.read_csv(DATA_PATH, parse_dates=["date"])
    df = df.sort_values(["ward_code", "date"]).reset_index(drop=True)
    df["ward_code"] = df["ward_code"].fillna("unknown").astype(str)

    # 피처 생성
    df["prev_dis"] = df.groupby("ward_code")["discharges"].shift(1)
    df["prev_week_dis"] = df.groupby("ward_code")["discharges"].shift(7)
    df["dow"] = df["date"].dt.dayofweek
    df["mon"] = df["date"].dt.month
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
CAT_COL = "ward_code"

# ───── 전처리: median impute → StandardScaler (with .values) ─────
num_imputer = SimpleImputer(strategy="median").fit(df[NUM_COLS].values)
X_num_imputed = num_imputer.transform(df[NUM_COLS].values)
scaler = StandardScaler().fit(X_num_imputed)
X_num_scaled = scaler.transform(X_num_imputed)

X_full = pd.DataFrame(X_num_scaled, columns=NUM_COLS)
X_full[CAT_COL] = df[CAT_COL].values
y_full = df["target"].values

# ───── Optuna 최적화 ─────
tscv = TimeSeriesSplit(n_splits=CV_SPLITS)

def objective(trial):
    params = {
        "loss_function": "MAE",
        "iterations": trial.suggest_int("iterations", 400, 1200),
        "depth": trial.suggest_int("depth", 4, 8),
        "learning_rate": trial.suggest_float("learning_rate", 0.02, 0.3, log=True),
        "l2_leaf_reg": trial.suggest_float("l2_leaf_reg", 1, 10, log=True),
        "bagging_temperature": trial.suggest_float("bagging_temperature", 0, 1),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "random_seed": SEED,
        "verbose": False,
    }

    maes = []
    for tr_idx, te_idx in tscv.split(X_full):
        cb = CatBoostRegressor(**params)
        cb.fit(Pool(X_full.iloc[tr_idx], y_full[tr_idx], cat_features=[CAT_COL]))
        preds = cb.predict(X_full.iloc[te_idx])
        maes.append(mean_absolute_error(y_full[te_idx], preds))

    return np.mean(maes)

study = optuna.create_study(direction="minimize",
                            sampler=optuna.samplers.TPESampler(seed=SEED))
study.optimize(objective, n_trials=N_TRIALS, show_progress_bar=True)

best_params = {**study.best_params, "loss_function": "MAE", "random_seed": SEED, "verbose": False}

print(f"\n▶ Optuna best MAE: {study.best_value:.4f}")
print(f"▶ Best params: {best_params}")

# ───── 교차검증 리포트 ─────
maes = []
for fold, (tr, te) in enumerate(tscv.split(X_full), 1):
    model = CatBoostRegressor(**best_params)
    model.fit(Pool(X_full.iloc[tr], y_full[tr], cat_features=[CAT_COL]))
    pred = model.predict(X_full.iloc[te])
    mae = mean_absolute_error(y_full[te], pred)
    maes.append(mae)
    print(f"Fold {fold}: MAE = {mae:.3f}")

print(f"\n=== CatBoost CV MAE: {np.mean(maes):.3f} ± {np.std(maes):.3f} ===")

# ───── 전체 데이터 재학습 및 저장 ─────
cb_final = CatBoostRegressor(**best_params).fit(
    Pool(X_full, y_full, cat_features=[CAT_COL]))

with open(MODEL_PATH, "wb") as f:
    pickle.dump({
        "num_imputer": num_imputer,
        "scaler": scaler,
        "cat_model": cb_final,
        "num_cols": NUM_COLS,
        "cat_col": CAT_COL
    }, f)

print(f"✔ 모델 저장 완료 → {MODEL_PATH}")
