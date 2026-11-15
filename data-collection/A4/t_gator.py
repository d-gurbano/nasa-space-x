import requests, time, sys
G='https://irsa.ipac.caltech.edu/cgi-bin/Gator/nph-query'
p=dict(searchForm='MO',spatial='cone',catalog=sys.argv[2], outfmt=1, mobj='smo', mobjstr=sys.argv[1], moradius=sys.argv[3],
       selcols='ra,dec,mjd,w1mpro,w1sigmpro,w2mpro,w2sigmpro,w1snr,w2snr,scan_id,frame_num,source_id,cc_flags,ph_qual,sso_flg,qual_frame')
t0=time.time()
r=requests.get(G,params=p,timeout=900); print(r.status_code,time.time()-t0,len(r.text)); print('\n'.join([l for l in r.text.splitlines() if not l.startswith('\\')][:15])); print(r.text.count('\n'))
