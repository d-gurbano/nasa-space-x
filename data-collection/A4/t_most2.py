import requests,time,sys
U="https://irsa.ipac.caltech.edu/cgi-bin/MOST/nph-most"
cat,des,b,e=sys.argv[1:5]
t=time.time()
r=requests.get(U,params=dict(catalog=cat,input_type='name_input',obj_name=des,obs_begin=b,obs_end=e,output_mode='Brief'),timeout=900)
lines=r.text.splitlines()
print(cat,r.status_code,len(r.text),round(time.time()-t,1),len(lines))
print('\n'.join([l for l in lines if l.startswith('\\')][:25])); print('\n'.join([l for l in lines if not l.startswith('\\')][:4]))
