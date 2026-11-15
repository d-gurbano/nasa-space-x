"""Add position_quality to the answer key from the MPC uncertainty parameter U (A7 cross-check result:
U=0 objects agree with Horizons-from-SPHEREx to <0.12", U>=6 objects disagree by 17" to 170 deg)."""
import os, pandas as pd, numpy as np
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
p = os.path.join(ROOT, 'data/07-answer-keys/answer_key/known_objects_in_frames.parquet')
ak = pd.read_parquet(p)
U = ak.U.astype(str).str.strip()
q = np.where(U.isin(['0', '1', '2']), 'gold', np.where(U.isin(['3', '4', '5']), 'ok', 'uncertain'))
ak['position_quality'] = np.where(ak.kind == 'comet', 'comet_no_nongrav', q)
ak.to_parquet(p)
print(ak[ak.on_detector].position_quality.value_counts())
