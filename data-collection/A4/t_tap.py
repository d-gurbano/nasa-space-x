import pyvo, time, numpy as np
from astropy.table import Table
s=pyvo.dal.TAPService('https://irsa.ipac.caltech.edu/TAP')
u=Table(dict(fid=[1,2],scan_id=np.array([b'01477b',b'01477b'],dtype='S6'),frame_num=[157,157],ra=[220.162736,220.0],dec=[-18.913658,-18.5],rad=[0.05,0.01]))
t0=time.time()
q="""select u.fid, p.ra, p.dec, p.mjd, p.w1mpro, p.w2mpro, p.w2snr, p.scan_id, p.frame_num, p.n_allwise, p.r_allwise
from allsky_4band_p1bs_psd p join TAP_UPLOAD.f u on p.scan_id=u.scan_id and p.frame_num=u.frame_num
where CONTAINS(POINT('ICRS',p.ra,p.dec), CIRCLE('ICRS',u.ra,u.dec,u.rad))=1"""
r=s.run_sync(q.replace(', p.n_allwise, p.r_allwise',''),uploads={'f':u}).to_table()
print(time.time()-t0, len(r)); print(r[:5])
