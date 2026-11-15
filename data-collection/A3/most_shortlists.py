"""MOST (IRSA, catalog=spherex) frame lists for A1 shortlists. One request at a time, checkpoint per object.
Stop by creating data/03-spherex/STOP_MOST."""
import sys, os, time, requests, gzip, pandas as pd
OUT='data/03-spherex/frames/most_raw'; STOP='data/03-spherex/STOP_MOST'
URL='https://irsa.ipac.caltech.edu/cgi-bin/MOST/nph-most'
objs=[]
for f,tag in [('a_spherex_precovery_shortlist','precovery'),('b_lost_recovery_shortlist','lost')]:
    d=pd.read_parquet(f'data/01-targets/lists/{f}.parquet')
    objs+= [(tag,x) for x in d.designation]
log=open('data/03-spherex/logs/most_status.csv','a')
for i,(tag,name) in enumerate(objs):
    if os.path.exists(STOP): break
    fn=f"{OUT}/{name.replace('/','_').replace(' ','_')}.tbl.gz"
    if os.path.exists(fn) or os.path.exists(fn+'.err'): continue
    p=dict(catalog='spherex',input_type='name_input',obj_name=name,obs_begin='2025-04-01',obs_end='2026-11-15',output_mode='Brief')
    t0=time.time(); txt=None; err=''
    for k in range(4):
        try:
            r=requests.get(URL,params=p,timeout=900)
            if r.status_code==200: txt=r.text; break
            err=f'HTTP{r.status_code}'
        except Exception as e: err=str(e)[:100]
        time.sleep(15*(k+1))
    dt=time.time()-t0
    if txt is None or '|' not in txt:
        open(fn+'.err','w').write(err+'\n'+(txt or '')[:5000])
        st='ERR '+(err or (txt or '')[:200].replace('\n',' '))
    else:
        with gzip.open(fn,'wt') as g: g.write(txt)
        n=sum(1 for l in txt.splitlines() if l and l[0] not in '\\|')
        st=f'ok {n}'
    log.write(f'{i},{tag},{name},{dt:.1f},{st}\n'); log.flush()
    print(i,tag,name,round(dt,1),st,flush=True)
    time.sleep(2)
