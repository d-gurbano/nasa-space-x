import requests, re, os, time, urllib.parse as up
BASE='https://irsa.ipac.caltech.edu'
seen=set(); out=[]
def links(url,html):
    return [up.urljoin(url,h.split('#')[0]) for h in re.findall(r'href=["\']([^"\']+)["\']',html)]
q=[BASE+'/spherex-archive-documentation/']
while q:
    u=q.pop(0)
    if u in seen: continue
    seen.add(u)
    try: r=requests.get(u,timeout=60)
    except Exception as e: print('ERR',u,e); continue
    print(r.status_code,u,len(r.content),flush=True)
    if r.status_code!=200: continue
    out.append(u)
    for l in links(u,r.text):
        if l.startswith(BASE+'/spherex-archive-documentation/') and not re.search(r'\.(png|jpg|gif|css|js|svg|ico)$',l,re.I) and l not in seen:
            q.append(l)
    time.sleep(0.5)
open('data/03-spherex/tmp/archive_doc_urls.txt','w').write('\n'.join(out))
