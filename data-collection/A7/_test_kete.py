import os, time, gzip, inspect
os.environ['KETE_CACHE_DIR']=os.path.abspath('data/02-orbits/kete-cache')
import kete, numpy as np
print(inspect.signature(kete.CometElements))
print(kete.CometElements.__doc__[:1200])
print([a for a in dir(kete.CometElements) if not a.startswith('_')])
with gzip.open('data/02-orbits/mpc/MPCORB.DAT.gz','rt',errors='replace') as f:
    lines=f.readlines()
i=[k for k,l in enumerate(lines) if l.startswith('-----')][0]
print(i, lines[i+1][:200])
print(len(lines)-i-1)
