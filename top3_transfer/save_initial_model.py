'''save_initial_model.py'''
import joblib
from collections import defaultdict
import pandas as pd

# --------- 하이퍼파라미터 ---------
ALPHA = 1.0          # 페로몬
BETA = 2.0           # 휴리스틱
PHER_INIT = 1.0      # 초기 페로몬 레벨


OCC_WEIGHT = 0.7     
DIST_WEIGHT = 0.3    # 거리 고려 

# --------- 모델 파라미터 ---------
WARD_TOTALS = {
    '심혈관 일일입원실': 27, '응급센터': 0, '내과ICU': 0, '외과ICU': 30, '응급중환자실': 13,
    '54병동': 32, '71병동': 34, '72병동': 45, '75병동': 32, '76병동': 33,
    '78병동': 29, '83병동': 33, '뇌졸중집중치료실': 4, '69병동': 40, '53병동': 31
}
WARD_FLOORS = {
    '응급센터':1, '내과ICU':4, '외과ICU':4, '심혈관계중환자실':4, '심혈관 일일입원실':4,
    '53병동':5, '54병동':5, '71병동':7, '72병동':7, '75병동':7, '76병동':7, '78병동':7,
    '83병동':8, '69병동':6, '응급중환자실':7, '뇌졸중집중치료실':4
}
BASE_FLOOR = 1
WARD_DISTANCES = {w: abs(f - BASE_FLOOR) * 0.1 for w, f in WARD_FLOORS.items()}

RAW_PRIORITY_WEIGHTS = {
    ('I46','심혈관계중환자실'):0.257, ('I46','83병동'):0.242, ('I46','내과ICU'):0.217,
    ('I46','응급센터'):0.163, ('I46','외과ICU'):0.121,
    ('I60','71병동'):0.3761, ('I60','외과ICU'):0.2778, ('I60','응급센터'):0.0655,
    ('I60','72병동'):0.0621, ('I60','76병동'):0.0586,
    ('I71','83병동'):0.2583, ('I71','외과ICU'):0.2231, ('I71','72병동'):0.2024,
    ('I71','54병동'):0.1954, ('I71','응급센터'):0.1208,
    ('I20','69병동'):0.4504, ('I20','심혈관 일일입원실'):0.2964,
    ('I20','심혈관계중환자실'):0.1768, ('I20','54병동 (OG)'):0.0656, ('I20','외과ICU'):0.0410,
    ('I21','69병동'):0.3459, ('I21','심혈관계중환자실'):0.2238, ('I21','외과ICU'):0.1491,
    ('I21','78병동'):0.0745, ('I21','54병동'):0.0676, ('I21','응급중환자실'):0.0451,
    ('I63','75병동'):0.3317, ('I63','뇌졸중집중치료실'):0.2351, ('I63','76병동'):0.1837,
    ('I63','응급중환자실'):0.1776, ('I63','응급센터'):0.0662, ('I63','외과ICU'):0.0662
}
TRANSFER_RATES = {'I60':0.80, 'I46':0.69, 'I71':0.89, 'I20':0.26, 'I21':0.62, 'I63':0.47}
EDGES_BY_ICD = {
    'I60':['71병동','외과ICU','응급센터','72병동','76병동'],
    'I46':['심혈관계중환자실','83병동','내과ICU','응급센터','외과ICU'],
    'I71':['83병동','외과ICU','72병동','54병동','응급센터'],
    'I20':['69병동','심혈관 일일입원실','심혈관계중환자실','54병동','외과ICU'],
    'I21':['69병동','심혈관계중환자실','외과ICU','78병동','54병동','응급중환자실'],
    'I63':['75병동','뇌졸중집중치료실','76병동','응급중환자실','응급센터','외과ICU']
}


def normalize(raw_pw):
    totals = defaultdict(float)
    for (icd, ward), v in raw_pw.items():
        totals[icd] += v
    return {k: (v / totals[k[0]] if totals[k[0]] > 0 else 0) for k, v in raw_pw.items()}


def make_state_from_df(df: pd.DataFrame) -> dict:
    df = df.copy()
    df['total_beds'] = df.embdCct + df.dschCct + df.useSckbCnt + df.admsApntCct + df.chupCct
    agg = df.groupby('ward').agg(total=('total_beds','first'), occupied=('useSckbCnt','sum')).reset_index()
    return {r.ward: {'total': int(r.total), 'occupied': int(r.occupied)} for r in agg.itertuples()}

# --------- MODEL CLASS ---------
class HybridScheduler:
    def __init__(self):
        self.alpha = ALPHA
        self.beta = BETA
        self.pheromone = {(icd, w): PHER_INIT for icd, wards in EDGES_BY_ICD.items() for w in wards}
        self.raw_pw = RAW_PRIORITY_WEIGHTS.copy()
        self.pw = normalize(self.raw_pw)
        self.transfer_rates = TRANSFER_RATES
        self.distances = WARD_DISTANCES
        self.edges = EDGES_BY_ICD

    def compute_eta(self, icd, ward, state):
        pr = self.pw.get((icd, ward), 0.01)
        tr = self.transfer_rates.get(icd, 0.01)
        s = state.get(ward, {'total': 0, 'occupied': 0})
        avail = max((s['total'] - s['occupied']) / s['total'], 0) if s['total'] > 0 else 0
        return pr * tr * avail

    def compute_cost(self, icd, ward, state):
        pr = self.pw.get((icd, ward), 0.01)
        s = state.get(ward, {'total': 1, 'occupied': 0})
        occ_ratio = s['occupied'] / s['total']
        dist = self.distances.get(ward, 0)
        tr = self.transfer_rates.get(icd, 0.5)
        return (1 - pr) + OCC_WEIGHT * occ_ratio + DIST_WEIGHT * (1 - tr) + dist

    def combined_score(self, icd, ward, state):
        tau = self.pheromone.get((icd, ward), PHER_INIT) ** self.alpha
        eta = self.compute_eta(icd, ward, state) ** self.beta
        cost = self.compute_cost(icd, ward, state)
        return tau * eta - cost

    def recommend(self, icd: str, df_live: pd.DataFrame = None, top_k=1) -> list:
        if df_live is not None:
            state = make_state_from_df(df_live)
        else:
            state = {w: {'total': WARD_TOTALS[w], 'occupied': 0} for w in WARD_TOTALS}
        scores = {}
        for w in self.edges.get(icd, []):
            s = state.get(w)
            if not s or s['occupied'] >= s['total']:
                continue
            scores[w] = self.combined_score(icd, w, state)
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]

if __name__ == '__main__':
    scheduler = HybridScheduler()
    joblib.dump(scheduler, 'hybrid_scheduler_initial.pkl')
    print("Initial HybridScheduler saved to hybrid_scheduler_initial.pkl")