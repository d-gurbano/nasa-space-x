"""Verify downloaded calibration files against the S3 listing: size, and MD5 vs ETag (single-part uploads).
Writes calibration/verify.csv; bad files are listed (and renamed *.bad) for re-download."""
import csv, hashlib, os, sys
rows=list(csv.DictReader(open('data/03-spherex/s3_calibration_listing.csv')))
out=[]
for r in rows:
    k=r['key']
    if k.startswith('qr3/'): continue
    fn='data/03-spherex/calibration/'+k
    if not os.path.exists(fn): out.append((k,'missing','')); continue
    sz=os.path.getsize(fn)
    if sz<100 and open(fn,'rb').read().startswith(b'placeholder'): out.append((k,'skipped_by_choice','')); continue
    if sz!=int(r['bytes']): st='size_mismatch'
    elif '-' in r['etag']: st='ok_size(multipart etag)'
    else:
        h=hashlib.md5(open(fn,'rb').read()).hexdigest(); st='ok_md5' if h==r['etag'] else 'md5_mismatch'
    if 'mismatch' in st and '--fix' in sys.argv: os.rename(fn,fn+'.bad')
    out.append((k,st,sz))
w=csv.writer(open('data/03-spherex/calibration/verify.csv','w')); w.writerow(['key','status','bytes']); w.writerows(out)
import collections; print(collections.Counter(s for _,s,_ in out))
