"""A9: curated public NASA media from NASA Image and Video Library API (images-api.nasa.gov). Excludes logos/insignia/people/press events."""
import requests, json, time, csv, hashlib, os, re, datetime
OUT='data/09-people/media'; os.makedirs(f'{OUT}/images',exist_ok=True); os.makedirs(f'{OUT}/videos',exist_ok=True)
S=requests.Session(); API='https://images-api.nasa.gov'
QUERIES=[('SPHEREx',14),('SPHEREx first images',6),('SPHEREx sky map',6),('SPHEREx comet',4),('NEOWISE',12),('NEOWISE asteroid',6),('comet NEOWISE',5),
 ('Bennu',10),('OSIRIS-REx Bennu',6),('DART Dimorphos',8),('Didymos',6),('DART impact',6),('Apophis',3),('interstellar comet',6),('3I ATLAS',6),
 ('near-Earth asteroid',8),('asteroid radar',6),('NEO Surveyor',5),('Itokawa',2),('Eros asteroid',3),('Vesta Dawn',3),('Psyche asteroid',3),('Lucy asteroid Dinkinesh',3),('comet',6),('planetary defense',4)]
BAD=re.compile(r'logo|insignia|emblem|patch|meatball|administrator|press|news conference|briefing|team|employees|conference|poster|award|ceremony|students|visit|crew|speaks|panel|podcast|social media|selfie|signing|interview|worm|staff|engineers? (?:inspect|work)|technicians',re.I)
def get(url,params=None):
    for i in range(4):
        try:
            r=S.get(url,params=params,timeout=90)
            if r.status_code==200: return r
        except Exception: pass
        time.sleep(2**i)
    return None
seen=set(); meta=[]
for q,n in QUERIES:
    r=get(f'{API}/search',{'q':q,'media_type':'image'}); time.sleep(0.5)
    if not r: continue
    items=r.json()['collection']['items']
    # prefer Photojournal science images (PIA ids), then others
    items.sort(key=lambda x: (not x['data'][0]['nasa_id'].startswith('PIA'), x['data'][0].get('date_created','')[::-1]))
    k=0
    for x in items:
        d=x['data'][0]; nid=d['nasa_id']
        if nid in seen: continue
        text=d.get('title','')+' '+' '.join(d.get('keywords',[]) or [])
        if BAD.search(text): continue
        seen.add(nid); k+=1
        meta.append(dict(query=q,nasa_id=nid,title=d.get('title'),center=d.get('center'),date_created=d.get('date_created','')[:10],
           photographer=d.get('photographer',''),secondary_creator=d.get('secondary_creator',''),description=re.sub(r'<[^>]+>','',d.get('description',''))[:1500],keywords=';'.join(d.get('keywords',[]) or []),
           page_url=f'https://images.nasa.gov/details/{nid}',asset_manifest=x['href']))
        if k>=n: break
print('selected',len(meta))
man=[]
for m in meta:
    r=get(m['asset_manifest']); time.sleep(0.4)
    if not r: continue
    files=r.json(); pick=None
    for suf in ['~large.jpg','~medium.jpg','~orig.jpg','~large.png','~orig.png','~orig.tif']:
        c=[f for f in files if f.lower().endswith(suf)]
        if c: pick=c[0].replace('http://','https://'); break
    if not pick: continue
    rr=get(pick)
    if not rr: continue
    fn=re.sub(r'[^A-Za-z0-9_.-]','_',m['nasa_id'])+os.path.splitext(pick)[1].split('?')[0]
    open(f'{OUT}/images/{fn}','wb').write(rr.content)
    m['local_file']=f'images/{fn}'; m['file_url']=pick
    desc=m['description']
    m['non_nasa_credit_flag']='Y' if re.search(r'ESA|JAXA|ASI|Gemini|NOIRLab|Keck|Copyright|©|courtesy',desc+m['secondary_creator']+m['photographer']) else ''
    m['credit_line']=('NASA/'+m['center'] if m['center'] else 'NASA')+(' - '+m['secondary_creator'] if m['secondary_creator'] else '')+(' - '+m['photographer'] if m['photographer'] else '')
    man.append(dict(filename=m['local_file'],url=pick,bytes=len(rr.content),sha256=hashlib.sha256(rr.content).hexdigest(),date=datetime.date.today().isoformat()))
    time.sleep(0.3)
# videos: a few short clips for the 30-second video
VQ=[('SPHEREx',4),('DART impact',2),('Bennu',3),('NEOWISE',2),('asteroid animation',3),('comet',2)]
vmeta=[]
for q,n in VQ:
    r=get(f'{API}/search',{'q':q,'media_type':'video'}); time.sleep(0.5)
    if not r: continue
    k=0
    for x in r.json()['collection']['items']:
        d=x['data'][0]; nid=d['nasa_id']
        if nid in seen or BAD.search(d.get('title','')+' '+' '.join(d.get('keywords',[]) or [])) or re.search(r'live|launch coverage|news|reel',d.get('title',''),re.I) and 'Reel' not in d.get('title',''): continue
        rr=get(x['href']); time.sleep(0.4)
        if not rr: continue
        files=rr.json(); c=[f for f in files if f.endswith('~mobile.mp4')] or [f for f in files if f.endswith('~small.mp4')] or [f for f in files if f.endswith('~preview.mp4')]
        if not c: continue
        u=c[0].replace('http://','https://'); v=get(u)
        if not v or len(v.content)>150e6: continue
        seen.add(nid); k+=1
        fn=re.sub(r'[^A-Za-z0-9_.-]','_',nid)[:90]+'.mp4'; open(f'{OUT}/videos/{fn}','wb').write(v.content)
        caps=[f for f in files if f.endswith('.srt') or f.endswith('.vtt')]
        vmeta.append(dict(query=q,nasa_id=nid,title=d.get('title'),center=d.get('center'),date_created=d.get('date_created','')[:10],photographer=d.get('photographer',''),secondary_creator=d.get('secondary_creator',''),
            description=re.sub(r'<[^>]+>','',d.get('description',''))[:1500],page_url=f'https://images.nasa.gov/details/{nid}',file_url=u,local_file=f'videos/{fn}',captions=';'.join(caps),
            credit_line='NASA/'+(d.get('center') or '')+(' - '+d['secondary_creator'] if d.get('secondary_creator') else ''),
            non_nasa_credit_flag='Y' if re.search(r'ESA|JAXA|Copyright|©|courtesy|music',d.get('description',''),re.I) else ''))
        man.append(dict(filename=f'videos/{fn}',url=u,bytes=len(v.content),sha256=hashlib.sha256(v.content).hexdigest(),date=datetime.date.today().isoformat()))
        if k>=n: break
keys=list(dict.fromkeys(k for m in meta for k in m))
with open(f'{OUT}/images_metadata.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=keys); w.writeheader(); w.writerows([m for m in meta if 'local_file' in m])
if vmeta:
    with open(f'{OUT}/videos_metadata.csv','w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(vmeta[0].keys())); w.writeheader(); w.writerows(vmeta)
with open(f'{OUT}/manifest.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['filename','url','bytes','sha256','date']); w.writeheader(); w.writerows(man)
print('images',sum(1 for m in meta if 'local_file' in m),'videos',len(vmeta),'bytes',sum(x['bytes'] for x in man))
