import requests, time
t0=time.time()
r=requests.get('https://irsa.ipac.caltech.edu/TAP/sync',params=dict(QUERY="select top 2 ra,dec,mjd from neowiser_p1bs_psd where cntr=1",FORMAT='csv'),timeout=300); print('tap trivial',r.status_code,time.time()-t0,r.text[:200])
for tb,ra,dec in [('allsky_4band_p1bs_psd',220.162736,-18.913658),('neowiser_p1bs_psd',39.943267,30.097806)]:
    t0=time.time()
    r=requests.get('https://irsa.ipac.caltech.edu/SCS',params=dict(table=tb,RA=ra,DEC=dec,SR=0.01,format='csv'),timeout=300)
    print(tb,r.status_code,time.time()-t0,len(r.text), r.text[:300].replace('\n',' | '))
