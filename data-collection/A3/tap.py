import pyvo,time
tap=pyvo.dal.TAPService('https://irsa.ipac.caltech.edu/TAP')
def q(sql,tries=5,maxrec=None):
    for i in range(tries):
        try:
            return tap.run_sync(sql,maxrec=maxrec).to_table()
        except Exception as e:
            print('TAP retry',i,str(e)[:120],flush=True); time.sleep(10*(i+1))
    raise RuntimeError('TAP failed: '+sql)
