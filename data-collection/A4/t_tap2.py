import pyvo, time
s=pyvo.dal.TAPService('https://irsa.ipac.caltech.edu/TAP')
for tb,ra,dec,mjd in [('allsky_4band_p1bs_psd',220.162736,-18.913658,55228.4311975),('neowiser_p1bs_psd',39.943267,30.097806,57414.0)]:
    t0=time.time()
    q=f"""select ra,dec,mjd,w1mpro,w2mpro,w2snr,scan_id,frame_num from {tb}
    where CONTAINS(POINT('ICRS',ra,dec), CIRCLE('ICRS',{ra},{dec},0.02))=1 and mjd between {mjd-1} and {mjd+1}"""
    r=s.run_sync(q).to_table(); print(tb,time.time()-t0,len(r)); print(r[:3])
