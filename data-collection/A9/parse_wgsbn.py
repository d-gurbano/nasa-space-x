"""A9: parse downloaded WGSBN Bulletin PDFs into a names + citations table (pdftotext, non-layout)."""
import re,subprocess,csv,glob,os
rows=[]; pat=re.compile(r'^\((\d+)\)\s+(.+?)\s+=\s+(.+)$')
for fn in sorted(glob.glob('data/09-people/names/wgsbn/*.pdf')):
    b=os.path.basename(fn); vol=b.split('_')[1]; u=f'https://www.wgsbn-iau.org/files/Bulletins/{vol}/{b}'
    t=subprocess.run(['pdftotext',fn,'-'],capture_output=True,text=True).stdout
    cur=None
    for l in [x.strip() for x in t.splitlines()]:
        m=pat.match(l)
        if m and '....' not in l:
            if cur and cur['citation']: rows.append(cur)
            cur=dict(number=m.group(1),name=m.group(2).strip(),provisional=m.group(3).strip(),disc_date='',discoverers='',disc_site='',disc_code='',citation='',bulletin=b,bulletin_url=u); continue
        if cur is None: continue
        if l.startswith('Discovery:'):
            p=[x.strip() for x in l[10:].split(' / ')]
            p+=['']*(4-len(p)); cur.update(disc_date=p[0],discoverers=p[1],disc_site=p[2],disc_code=p[3]); continue
        if not l or re.match(r'^(WGSBN Bull\.|\d+$)',l):
            if cur['citation']: rows.append(cur); cur=None
            continue
        cur['citation']=(cur['citation']+' '+l).strip()
    if cur and cur['citation']: rows.append(cur)
with open('data/09-people/names/wgsbn_citations.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print('citations',len(rows),'unique numbers',len({r['number'] for r in rows}))
