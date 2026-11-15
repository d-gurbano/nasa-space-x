"""A9: discovery observation (asterisk-flagged line) per object from MPC public get-obs API (read-only GET), plus station names."""
import requests, csv, json, time, re
OUT='data/09-people/stories'
S=requests.Session()
def obscodes():
    r=S.get('https://minorplanetcenter.net/iau/lists/ObsCodes.html',timeout=60); open(f'{OUT}/mpc_ObsCodes.html','w').write(r.text)
    codes={}
    for l in r.text.splitlines():
        if len(l)>30 and re.match(r'^[0-9A-Z]{3} ',l): codes[l[:3]]=l[30:].strip()
    return codes
def disc(desig):
    for i in range(4):
        try:
            r=S.get('https://data.minorplanetcenter.net/api/get-obs',json={'desigs':[desig],'output_format':['OBS80']},timeout=90)
            if r.status_code==200:
                o=r.json()[0]['OBS80'].splitlines()
                d=[l for l in o if len(l)>79 and l[12]=='*']
                return (d[0] if d else None), len(o), (o[0][15:32] if o else None)
        except Exception: pass
        time.sleep(2**i)
    return None,None,None
codes=obscodes(); print('stations',len(codes))
targets=['2024 YR4','2024 PT5','2025 PN7','2025 MN45','C/2025 A6','C/2025 R2','C/2025 K1','2025 FA22','2019 OK','2020 CD3','2022 EB5','2023 CX1','2024 BX1','2024 RW1','2024 XA1','2018 LA','2008 TC3','3I','99942','101955','65803']
for fn in ['recent_neo_since2025_sbdb.csv','recent_comet_since2025_sbdb.csv']:
    rows=list(csv.DictReader(open(f'{OUT}/{fn}')))
    if 'comet' in fn: sel=rows
    else:
        def f(x):
            try: return float(x)
            except: return 99
        sel=[r for r in rows if r['pha']=='Y' or f(r['H'])<20.5 or f(r['moid'])<0.0005]
    targets+= [r['pdes'] for r in sel]
targets=list(dict.fromkeys(targets)); print('targets',len(targets))
res=[]
for t in targets:
    l,n,firstline=disc(t); time.sleep(0.8)
    if l:
        stn=l[77:80]; date=l[15:32].strip()
        res.append(dict(object=t,disc_date_utc=date,station_code=stn,station_name=codes.get(stn,''),mag_band=l[65:71].strip(),n_obs_mpc=n,disc_obs80=l,source_url='https://data.minorplanetcenter.net/api/get-obs'))
    else: res.append(dict(object=t,disc_date_utc='',station_code='',station_name='',mag_band='',n_obs_mpc=n,disc_obs80='',source_url='https://data.minorplanetcenter.net/api/get-obs'))
with open(f'{OUT}/mpc_discovery_observations.csv','w',newline='') as fh:
    w=csv.DictWriter(fh,fieldnames=list(res[0].keys())); w.writeheader(); w.writerows(res)
print('done',len(res),sum(1 for r in res if r['station_code']))
