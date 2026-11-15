"""A9: download all WGSBN Bulletins (IAU, partner - official source of new minor-planet names/citations) and parse citations to a table."""
import requests,re,os,time,hashlib,csv,subprocess,datetime
OUT='data/09-people/names/wgsbn'; os.makedirs(OUT,exist_ok=True)
H={'User-Agent':'Mozilla/5.0 (Rewind SpaceApps research)'}
idx=requests.get('https://www.wgsbn-iau.org/files/Bulletins/',headers=H,timeout=60).text
pdfs=sorted(set(re.findall(r'href="(files/Bulletins/[^"]+\.pdf)"',idx)))
man=[]
for p in pdfs:
    fn=os.path.join(OUT,os.path.basename(p)); u='https://www.wgsbn-iau.org/'+p
    if not os.path.exists(fn):
        for i in range(4):
            try:
                r=requests.get(u,headers=H,timeout=90)
                if r.status_code==200: open(fn,'wb').write(r.content); break
            except Exception: pass
            time.sleep(2**i)
        time.sleep(0.7)
    if os.path.exists(fn):
        b=open(fn,'rb').read(); man.append(dict(filename='names/wgsbn/'+os.path.basename(fn),url=u,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),date=datetime.date.today().isoformat()))
with open('data/09-people/names/wgsbn_manifest.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['filename','url','bytes','sha256','date']); w.writeheader(); w.writerows(man)
# parse: entries look like "(12345) Name = 2001 AB12" followed by citation paragraph
rows=[]
pat=re.compile(r'^\((\d+)\)\s+(.+?)\s+=\s+(\S.*?)\s*$')
for m in man:
    fn='data/09-people/'+m['filename']
    t=subprocess.run(['pdftotext','-layout',fn,'-'],capture_output=True,text=True).stdout
    lines=[l.strip() for l in t.splitlines()]
    cur=None
    for l in lines:
        mm=pat.match(l)
        if mm:
            if cur: rows.append(cur)
            cur=dict(number=mm.group(1),name=mm.group(2).strip(),provisional=mm.group(3).split('  ')[0].strip(),citation='',bulletin=os.path.basename(fn),bulletin_url=m['url'])
        elif cur is not None:
            if not l: 
                if cur['citation']: rows.append(cur); cur=None
                continue
            if re.match(r'^(WGSBN Bulletin|Page \d+|\d+$)',l): continue
            cur['citation']=(cur['citation']+' '+l).strip()
    if cur: rows.append(cur)
with open('data/09-people/names/wgsbn_citations.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['number','name','provisional','citation','bulletin','bulletin_url']); w.writeheader(); w.writerows(rows)
print('bulletins',len(man),'citations',len(rows),'bytes',sum(x['bytes'] for x in man))
