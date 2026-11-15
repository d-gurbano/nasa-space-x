"""Download files by HTTPS with retries; append manifest rows (filename,url,bytes,sha256,date). Usage: dl.py urls.tsv  (url<TAB>localpath)"""
import requests, hashlib, os, sys, time, datetime, csv, threading
from concurrent.futures import ThreadPoolExecutor
ROOT='data/03-spherex'; MAN=f'{ROOT}/manifest.csv'; lock=threading.Lock()
def sha(fn):
    h=hashlib.sha256()
    with open(fn,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()
def get(url,dest):
    if os.path.exists(dest) and os.path.getsize(dest)>0: return 'skip'
    os.makedirs(os.path.dirname(dest),exist_ok=True)
    for i in range(6):
        try:
            with requests.get(url,stream=True,timeout=120) as r:
                if r.status_code==404: return 'HTTP404'
                r.raise_for_status()
                tmp=dest+'.part'
                with open(tmp,'wb') as f:
                    for b in r.iter_content(1<<20): f.write(b)
                os.replace(tmp,dest)
            row=[os.path.relpath(dest,ROOT),url,os.path.getsize(dest),sha(dest),datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ')]
            with lock:
                new=not os.path.exists(MAN)
                with open(MAN,'a',newline='') as f:
                    w=csv.writer(f)
                    if new: w.writerow(['filename','url','bytes','sha256','date'])
                    w.writerow(row)
            return 'ok'
        except Exception as e:
            err=str(e); time.sleep(5*(i+1))
    return 'FAIL '+err
if __name__=='__main__':
    jobs=[l.rstrip('\n').split('\t') for l in open(sys.argv[1]) if l.strip() and not l.startswith('#')]
    nt=int(sys.argv[2]) if len(sys.argv)>2 else 4
    with ThreadPoolExecutor(nt) as ex:
        for (u,d),res in zip(jobs,ex.map(lambda j:get(*j),jobs)):
            print(res,u,flush=True)
