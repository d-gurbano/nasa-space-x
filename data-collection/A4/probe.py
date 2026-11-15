import requests,sys
ra,dec=76.9564535,30.4013327
def show(name,u,p=None,n=600):
    try:
        r=requests.get(u,params=p,timeout=120); print('##',name,r.status_code,len(r.text),flush=True); print(r.text[:n],flush=True)
    except Exception as e: print('##',name,e,flush=True)
w=sys.argv[1]
if w=='tess': show('tesscut','https://mast.stsci.edu/tesscut/api/v0.1/sector',dict(ra=ra,dec=dec,radius='1m'))
if w=='sha': show('sha','https://irsa.ipac.caltech.edu/applications/Spitzer/SHA/servlet/DataService',dict(RA=ra,DEC=dec,SIZE=0.05,VERB=1,DATASET='ivo://irsa.ipac/spitzer.level1'),1500)
if w=='noir': show('noirlab','https://astroarchive.noirlab.edu/api/sia/voimg',dict(POS=f'{ra},{dec}',SIZE=0.05,format='json',limit=5),1500)
if w=='euclid': show('euclid','https://eas.esac.esa.int/tap-server/tap/sync',dict(REQUEST='doQuery',LANG='ADQL',FORMAT='csv',QUERY="select top 20 table_name from tap_schema.tables"),2000)
