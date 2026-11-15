"""A9: discovery + name-citation data from NASA/JPL SBDB API (read-only GET, paced)."""
import requests, json, time, csv, sys, datetime
OUT='data/09-people'
API='https://ssd-api.jpl.nasa.gov/sbdb.api'
Q='https://ssd-api.jpl.nasa.gov/sbdb_query.api'
S=requests.Session()
def get(url,params,tries=4):
    for i in range(tries):
        try:
            r=S.get(url,params=params,timeout=60)
            if r.status_code==200: return r.json()
        except Exception as e: pass
        time.sleep(2**i)
    return None
FEATURED=['2024 YR4','99942','3I','101955','65803','2024 PT5','2025 PN7','2025 MN45','C/2025 A6','C/2025 R2','C/2025 K1','2025 FA22','1I','2I','433','162173','25143','2019 OK','2020 CD3','2022 EB5','2023 CX1','2024 BX1','2024 RW1','2024 XA1','2018 LA','2008 TC3']
def one(s):
    d=get(API,{'sstr':s,'discovery':1,'phys-par':1})
    time.sleep(0.4)
    return d
def featured():
    rows=[]
    for s in FEATURED:
        d=one(s)
        if not d or 'object' not in d:
            print('miss',s); continue
        o=d['object']; disc=d.get('discovery') or {}
        orb=d.get('orbit',{})
        rows.append(dict(query=s,fullname=o.get('fullname'),kind=o.get('kind'),neo=o.get('neo'),pha=o.get('pha'),
          orbit_class=(o.get('orbit_class') or {}).get('name'),first_obs=orb.get('first_obs'),last_obs=orb.get('last_obs'),
          n_obs_used=orb.get('n_obs_used'),disc_text=disc.get('discovery'),disc_who=disc.get('who'),disc_location=disc.get('location'),
          disc_site=disc.get('site'),disc_date=disc.get('date'),name=disc.get('name'),citation=disc.get('citation'),
          source_url=f"https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr={s.replace(' ','%20')}"))
    json.dump(rows,open(f'{OUT}/stories/sbdb_featured_raw.json','w'),indent=1)
    print('featured',len(rows))
def recent():
    # all NEOs + comets first observed since 2025-01-01 (VERIFIED from SBDB)
    out={}
    for grp,extra in [('neo',{'sb-group':'neo'}),('comet',{'sb-kind':'c'}),('all_asteroids',{'sb-kind':'a'})]:
        p={'fields':'full_name,pdes,first_obs,last_obs,n_obs_used,H,diameter,class,neo,pha,moid','sb-cdata':json.dumps({'AND':['first_obs|GE|2025-01-01']})}
        p.update(extra)
        d=get(Q,p)
        if d is None: print('fail',grp); continue
        out[grp]=d.get('count')
        if grp!='all_asteroids':
            with open(f'{OUT}/stories/recent_{grp}_since2025_sbdb.csv','w',newline='') as f:
                w=csv.writer(f); w.writerow(d['fields']); w.writerows(d.get('data',[]))
        time.sleep(1)
    json.dump(out,open(f'{OUT}/stories/recent_counts_sbdb.json','w'),indent=1); print(out)
def named_neo_citations():
    d=get(Q,{'fields':'full_name,pdes,name,H,class,pha','sb-group':'neo','sb-ns':'n','sb-cdata':json.dumps({'AND':['name|DF']})})
    lst=d.get('data',[]) if d else []
    print('named NEOs',len(lst))
    rows=[]
    for i,(fn,pdes,name,H,cl,pha) in enumerate(lst):
        dd=get(API,{'sstr':pdes,'discovery':1}); time.sleep(0.35)
        disc=(dd or {}).get('discovery') or {}
        rows.append(dict(number=pdes,name=name,full_name=fn.strip(),H=H,orbit_class=cl,pha=pha,discovery=disc.get('discovery'),
           who=disc.get('who'),location=disc.get('location'),date=disc.get('date'),citation=disc.get('citation'),cite_ref=disc.get('ref'),
           source_url=f'https://ssd-api.jpl.nasa.gov/sbdb.api?sstr={pdes}&discovery=1'))
        if i%100==0: print(i,flush=True)
    with open(f'{OUT}/names/named_neo_citations_sbdb.csv','w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
if __name__=='__main__':
    for step in sys.argv[1:]: globals()[step]()
