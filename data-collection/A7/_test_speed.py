import sys, time, os; sys.path.insert(0,'code/A7')
from mpcorb import *
t=time.time(); df=load_mpcorb(); print(len(df), 'parsed', round(time.time()-t,1)); print(df.head(3).T)
c=load_comets(); print(len(c), 'comets'); print(c.head(3).T)
t=time.time(); st=to_states(df.iloc[:100000]); print('states', len(st), round(time.time()-t,1))
jd=2461000.5
t=time.time(); p=kete.propagate_n_body(st, jd); print('nbody 100k', round(time.time()-t,1))
obs=kete.spice.get_state('earth', jd)
fov=kete.ConeFOV(kete.Vector.from_ra_dec(30,12), 3.0, obs)
fovs=[kete.ConeFOV(kete.Vector.from_ra_dec(30+i*0.01,12), 3.0, kete.spice.get_state('earth', jd+i*0.01)) for i in range(50)]
t=time.time(); r=kete.fov_state_check(p, fovs); print('fovcheck 100k x50', round(time.time()-t,1), sum(len(x) for x in r))
