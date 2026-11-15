import requests
G='https://irsa.ipac.caltech.edu/cgi-bin/Gator/nph-query'
base=dict(searchForm='MO',spatial='cone',catalog='neowiser_p1bs_psd',outfmt=1,mobj='smo',mobjstr='2015 SA',moradius=10)
for extra in [dict(btime='2015 09 12 11:27:40',etime='2015 09 13 11:27:40'), dict(btime='2015+09+12+11:27:40',etime='2015+09+13+11:27:40'), dict(btime='2015-09-12 11:27:40',etime='2015-09-13 11:27:40')]:
    p=dict(base,**extra,selcols='ra,dec,mjd,w2mpro')
    u=requests.Request('GET',G,params=p).prepare().url
    if '+' in extra['btime']: u=G+'?'+'&'.join(f'{k}={v}' for k,v in {**base,**extra}.items()).replace(' ','+')+'&selcols=ra,dec,mjd,w2mpro'
    r=requests.get(u,timeout=300); print(extra['btime'], r.status_code, r.text[:200].replace('\n',' '), '| datarows', len([l for l in r.text.splitlines() if l.startswith(' ')]))
