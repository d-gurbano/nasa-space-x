"""Pick DR1 all-sky cube tiles (HEALPix order 5, NESTED, ICRS) for named positions; write url list."""
import astropy_healpix as ah, astropy.units as u, numpy as np, csv, sys
hp=ah.HEALPix(nside=32,order='nested')
def tile(ra,dec): return int(hp.lonlat_to_healpix(ra*u.deg,dec*u.deg))
def url(n): return f'https://nasa-irsa-spherex.s3.amazonaws.com/dr1/hips5_cube/hips_20261026/Norder5/Dir{(n//10000)*10000}/Npix{n}_cube.fits'
P=[('NEP_center',270.0,66.56,1),('SEP_center',90.0,-66.56,1),
   ('barnards_star',269.4482,4.7682,0),('wise0855-0714',133.760,-7.242,0),('eps_indi_b',331.096,-56.8005,0),
   ('rw_aurigae',76.9564,30.4014,0),('r_draconis',248.1674,66.7550,0),('pilot_piazzia_field',284.6883,-31.98799,0)]
rows=[];seen=set()
for name,ra,dec,nb in P:
    n=tile(ra,dec); ids=[(n,'center')]
    if nb: ids+=[(int(x),'neighbour') for x in hp.neighbours(n) if x>=0][::2]   # 4 of 8 neighbours (N,E,S,W style subset)
    for t,role in ids:
        if t in seen: continue
        seen.add(t); rows.append((name,role,ra,dec,t,url(t)))
w=csv.writer(open('data/03-spherex/hips/tiles_selected.csv','w')); w.writerow(['field','role','ra','dec','npix','url']); w.writerows(rows)
open('data/03-spherex/tmp/hips_urls.tsv','w').write('\n'.join(f'{r[5]}\tdata/03-spherex/hips/cubes/Npix{r[4]}_cube.fits' for r in rows)+'\n')
for r in rows: print(r[:5])
print(len(rows),'tiles',len(rows)*0.3209,'GB')
