"""A4: merge A1 shortlists (precovery A, lost B) into one target table for archive searches."""
import pandas as pd, os
R = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
L = f'{R}/data/01-targets/lists'; O = f'{R}/data/04-other-archives'; os.makedirs(O, exist_ok=True)
a = pd.read_parquet(f'{L}/a_spherex_precovery_shortlist.parquet')
b = pd.read_parquet(f'{L}/b_lost_recovery_shortlist.parquet')
a2 = pd.DataFrame(dict(designation=a.designation, full_name=a.full_name, list='A_precovery', group=a.group, cls=a['class'],
    H=a.H, M1=a.M1, first_obs=a.first_obs, last_obs=a.last_obs, disc_date=a.disc_date_best, rank_score=a.rank_score,
    tier=a.tier, spkid=a.spkid, rank_in_list=range(1, len(a)+1)))
b2 = pd.DataFrame(dict(designation=b.designation, full_name=b.full_name, list='B_lost', group=b.group, cls=b['class'],
    H=b.H, M1=b.M1, first_obs=b.first_obs, last_obs=b.last_obs, disc_date=b.first_obs, rank_score=b.rank_score,
    tier=b.lost_flag, spkid=b.spkid, rank_in_list=range(1, len(b)+1)))
t = pd.concat([a2, b2], ignore_index=True)
t['is_comet'] = t.group.astype(str).str.lower().str.contains('comet') | t.designation.str.match(r'^[PCDI]/|^\d+[PCDI]')
dup = t.designation.duplicated(keep='first'); print('duplicates across lists:', dup.sum())
t['in_both_lists'] = t.designation.isin(a2.designation) & t.designation.isin(b2.designation)
t = t[~dup].reset_index(drop=True)
t.to_csv(f'{O}/targets_A4.csv', index=False); t.to_parquet(f'{O}/targets_A4.parquet', index=False)
print(t.shape, t.list.value_counts().to_dict(), 'comets', t.is_comet.sum())
print(t.disc_date.min(), t.disc_date.max()); print(t.groupby('list').disc_date.describe())
