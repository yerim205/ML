# utils/preprocess.py
import pandas as pd

def preprocess(df: pd.DataFrame) -> pd.DataFrame:

    # 범주형 변수 dtype 지정 (필요시)
    if 'ward_code' in df.columns:
        df['ward_code'] = df['ward_code'].astype('category')
    
    return df
