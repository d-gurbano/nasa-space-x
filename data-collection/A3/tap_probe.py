import pyvo,time,sys
tap=pyvo.dal.TAPService('https://irsa.ipac.caltech.edu/TAP')
for sql in ["select collection, count(*) as n from spherex.observation group by collection",
            "select top 2 * from spherex.observation where collection='spherex_qr3_deep'"]:
    t0=time.time()
    try:
        job=tap.submit_job(sql); job.run(); job.wait(phases=['COMPLETED','ERROR','ABORTED'],timeout=900)
        print(job.phase, time.time()-t0, flush=True)
        if job.phase=='COMPLETED':
            t=job.fetch_result().to_table(); print(t if len(t.colnames)<5 else [(c,t[c][0]) for c in t.colnames],flush=True)
        else: print(job.job.errorsummary,flush=True)
    except Exception as e: print('ERR',sql,e,time.time()-t0,flush=True)
