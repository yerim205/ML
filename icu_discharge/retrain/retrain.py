import pandas as pd, pickle, shutil, tempfile
from pathlib import Path
from datetime import datetime
from catboost import CatBoostRegressor
from icu_discharge.retrain.utils import preprocess
from icu_discharge.retrain.utils.ncp_client import upload_file


SELF = Path(__file__).parent
ARCHIVE_DIR = SELF.parent.parent / "data" / "archive"
MODEL_PATH  = SELF.parent / "model" / "best_catboost_model.pkl"

def load_archive():
    files = sorted(ARCHIVE_DIR.glob("*.csv"))
    return pd.concat((pd.read_csv(f) for f in files), ignore_index=True)

def main():
    df = load_archive()
    y  = df.pop("discharge_flag")
    X  = preprocess(df)
    cat_idx = [X.columns.get_loc("ward_code")]

    model = CatBoostRegressor(
        iterations=400, depth=6, learning_rate=0.07,
        cat_features=cat_idx, loss_function="Logloss", random_state=42,
        verbose=False
    ).fit(X,y)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    with tempfile.NamedTemporaryFile(delete=False,suffix=".pkl") as tmp:
        pickle.dump(model,tmp); shutil.move(tmp.name,MODEL_PATH)

    upload_file(MODEL_PATH, f"icu-discharge/{ts}.pkl")
    print(f"re-trained @ {ts}")

if __name__=="__main__": main()
