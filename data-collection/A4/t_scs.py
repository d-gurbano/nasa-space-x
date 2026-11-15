import requests, time
for tb,ra,dec in [('neowiser_p1bs_psd',39.943267,30.097806)]:
    t0=time.time()
    r=requests.get('https://irsa.ipac.caltech.edu/SCS',params=dict(table=tb,RA=ra,DEC=dec,SR=0.01,format='csv'),timeout=200)
    print(tb,r.status_code,time.time()-t0,len(r.text), r.text[:300].replace('\n',' | '))
