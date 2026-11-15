"""Partial reads of DR1 all-sky cube tiles by HTTP Range: for each target, read a band of NR full rows (512 px wide)
around the target in all 102 planes of IMAGE and NHITS, plus SPECTRAL_CHANNELS and WCS-WAVE tables.
Writes a small FITS cube (512 x NR x 102) with a WCS shifted to the band. ~2 x 102 range requests per target."""
import requests, numpy as np, os, sys, csv, time, hashlib, datetime
from astropy.io import fits
from astropy.wcs import WCS
S=requests.Session()
def rng(url,a,n):
    for i in range(6):
        try:
            r=S.get(url,headers={'Range':f'bytes={a}-{a+n-1}'},timeout=300)
            if r.status_code==206 and 0<len(r.content)<=n: return r.content
        except Exception as e: pass
        time.sleep(5*(i+1))
    raise RuntimeError('range failed')
def headers(url):
    """walk HDU headers; return list of (header, data_offset, data_len)"""
    out=[];off=0
    for k in range(6):
        buf=b''
        while True:
            buf+=rng(url,off+len(buf),2880*4)
            i=buf.find(b'END'+b' '*77)
            while i>=0 and i%80: i=buf.find(b'END'+b' '*77,i+1)
            if i>=0: break
        hl=((i+80+2879)//2880)*2880; h=fits.Header.fromstring(buf[:i+80])
        if k==0: nb=0
        else:
            n=abs(h['BITPIX'])//8
            for j in range(1,h['NAXIS']+1): n*=h[f'NAXIS{j}']
            nb=n+h.get('PCOUNT',0)
        out.append((h,off+hl,nb)); off=off+hl+((nb+2879)//2880)*2880
        if k>0 and h.get('EXTNAME')=='WCS-WAVE': break
    return out
def run(name,ra,dec,url,npix,NR=64,outdir='data/03-spherex/hips/cutouts'):
    os.makedirs(outdir,exist_ok=True); fn=f'{outdir}/{name}_Npix{npix}_rows{NR}.fits'
    if os.path.exists(fn): return
    H=headers(url); hd={h.get('EXTNAME','PRIMARY'):(h,o,n) for h,o,n in H}
    h,o,n=hd['IMAGE']; h2=fits.Header(); h2['NAXIS']=2
    for k in ['CTYPE1','CTYPE2','CRPIX1','CRPIX2','CRVAL1','CRVAL2','PC1_1','PC1_2','PC2_1','PC2_2','CDELT1','CDELT2','CUNIT1','CUNIT2','PV2_1','PV2_2','LONPOLE','LATPOLE','RADESYS']:
        h2[k]=h[k]
    w=WCS(h2)
    x,y=w.all_world2pix([[ra,dec]],0)[0]; y0=int(np.clip(round(y)-NR//2,0,512-NR))
    planes={}
    for ext in ['IMAGE','NHITS']:
        h,o,n=hd[ext]; bp=abs(h['BITPIX'])//8; rowb=512*bp
        cube=np.zeros((102,NR,512),dtype=np.dtype('>f4') if h['BITPIX']==-32 else np.dtype(f'>i{bp}'))
        for p in range(102):
            a=o+(p*512+y0)*rowb; cube[p]=np.frombuffer(rng(url,a,NR*rowb),dtype=cube.dtype).reshape(NR,512)
        planes[ext]=(h,cube)
    hl=[fits.PrimaryHDU(header=H[0][0])]
    for ext in ['IMAGE','NHITS']:
        h,cube=planes[ext]; hh=h.copy(); hh['NAXIS2']=NR
        if 'CRPIX2' in hh: hh['CRPIX2']=hh['CRPIX2']-y0
        hh['ROWBAND0']=(y0,'0-based first tile row read'); hh['SRCURL']=url[:68]
        hl.append(fits.ImageHDU(cube,header=hh,name=ext))
    for ext in ['SPECTRAL_CHANNELS','WCS-WAVE']:
        if ext in hd:
            h,o,n=hd[ext]; raw=rng(url,o-((len(h.tostring())+2879)//2880)*2880,((len(h.tostring())+2879)//2880)*2880+((n+2879)//2880)*2880)
            raw=raw+b'\0'*((-len(raw))%2880)
            hl.append(fits.HDUList.fromstring(fits.PrimaryHDU().header.tostring().encode()+raw)[1].copy())
    fits.HDUList(hl).writeto(fn,overwrite=True)
    sha=hashlib.sha256(open(fn,'rb').read()).hexdigest()
    with open('data/03-spherex/manifest.csv','a',newline='') as f:
        csv.writer(f).writerow([os.path.relpath(fn,'data/03-spherex'),url+f' (Range: rows {y0}-{y0+NR-1} of IMAGE,NHITS + tables)',os.path.getsize(fn),sha,datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%dT%H:%MZ')])
    print(name,npix,'rows',y0,'x_target',round(x,1),'ok',flush=True)
if __name__=='__main__':
    for r in csv.DictReader(open('data/03-spherex/hips/tiles_selected.csv')):
        if r['role']!='center' or r['field'] in ('NEP_center','SEP_center'): continue
        try: run(r['field'],float(r['ra']),float(r['dec']),r['url'],r['npix'])
        except Exception as e: print(r['field'],'FAILED',e,flush=True)
