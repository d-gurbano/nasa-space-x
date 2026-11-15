import boto3, sys
from botocore import UNSIGNED
from botocore.config import Config
s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED), region_name='us-east-1')
B='nasa-irsa-spherex'
def ls(prefix, delim='/', maxk=1000):
    p=s3.get_paginator('list_objects_v2'); pre=[]; obj=[]
    for page in p.paginate(Bucket=B, Prefix=prefix, Delimiter=delim, PaginationConfig={'MaxItems':maxk}):
        pre += [c['Prefix'] for c in page.get('CommonPrefixes',[])]
        obj += [(o['Key'],o['Size'],str(o['LastModified'])) for o in page.get('Contents',[])]
    return pre,obj
if __name__=='__main__':
    pref = sys.argv[1] if len(sys.argv)>1 else ''
    pre,obj = ls(pref)
    for x in pre: print('P',x)
    for o in obj[:200]: print('O',*o)
    print(len(pre),'prefixes',len(obj),'objects')
