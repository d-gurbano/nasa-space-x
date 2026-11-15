import requests
G='https://irsa.ipac.caltech.edu/cgi-bin/Gator/nph-query'
for name,cat in [('2015 SA','neowiser_p1bs_psd'),('2015 SA','allsky_4band_p1bs_psd'),('C/2025 R3','allsky_4band_p1bs_psd'),('C/2025 R3','neowiser_p1bs_psd'),('3807751:NID','neowiser_p1bs_psd')]:
    p=dict(searchForm='MO',spatial='cone',catalog=cat,outfmt=1,mobj='smo',mobjstr=name,moradius=10,selcols='ra,dec,mjd,w2mpro')
    r=requests.get(G,params=p,timeout=300); print(name,cat, r.status_code, r.text[:150].replace('\n',' '), '| datarows', len([l for l in r.text.splitlines() if l.startswith(' ')]))
