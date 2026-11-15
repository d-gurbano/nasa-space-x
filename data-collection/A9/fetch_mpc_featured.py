"""A9: quick MPC discovery-line pass for featured objects only (same method as fetch_mpc_discovery.py)."""
import requests,re,csv,time
codes={}
for l in open('data/09-people/stories/mpc_ObsCodes.html').read().splitlines():
    if len(l)>30 and re.match(r'^[0-9A-Z]{3} ',l): codes[l[:3]]=l[30:].strip()
T=['2024 YR4','2024 PT5','2025 PN7','2025 MN45','C/2025 A6','C/2025 R2','2025 FA22','2019 OK','2020 CD3','2022 EB5','2023 CX1','2024 BX1','2024 RW1','2024 XA1','2018 LA','2008 TC3','C/2025 N1','99942','101955','65803']
res=[]
for t in T:
    try:
        o=requests.get('https://data.minorplanetcenter.net/api/get-obs',json={'desigs':[t],'output_format':['OBS80']},timeout=60).json()[0]['OBS80'].splitlines()
        d=[l for l in o if len(l)>79 and l[12]=='*']
        l=d[0] if d else ''
        res.append(dict(object=t,disc_date_utc=l[15:32].strip(),station_code=l[77:80] if l else '',station_name=codes.get(l[77:80],'') if l else '',n_obs_mpc=len(o),disc_obs80=l,source_url='https://data.minorplanetcenter.net/api/get-obs'))
    except Exception as e: res.append(dict(object=t,disc_date_utc='',station_code='',station_name='ERR '+str(e)[:40],n_obs_mpc='',disc_obs80='',source_url=''))
    time.sleep(0.8)
with open('data/09-people/stories/mpc_discovery_featured.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(res[0].keys())); w.writeheader(); w.writerows(res)
for r in res: print(r['object'],'|',r['disc_date_utc'],'|',r['station_code'],r['station_name'],'|',r['n_obs_mpc'])
