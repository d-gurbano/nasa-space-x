import re, csv
t=open('data/03-spherex/tmp/expsupp21.txt').read()
s=t.find('Table 16: Image pixel flags'); e=t.find('Table 17',s)
rows=[];cur=None
for line in t[s:e].split('\n'):
    if re.search(r'Caltech/IPAC|SSDC|Explanatory Supplement|continued|Symbolic|^\s*name\s*$|Table 16',line): continue
    m=re.match(r'^\s{0,3}([A-Z][A-Z0-9_]+)\s+(\d{1,2})\s+(.*)$',line)
    if m: cur=[m.group(1),int(m.group(2)),m.group(3)]; rows.append(cur)
    elif cur and line.strip(): cur[2]+=' '+line.strip()
with open('data/03-spherex/flag_definitions_level2.csv','w',newline='') as f:
    w=csv.writer(f); w.writerow(['name','bit','value','description_and_note','source'])
    for n,b,d in rows: w.writerow([n,b,2**b,re.sub(r'\s{2,}',' | ',d.strip()),'SPHEREx Explanatory Supplement v2.1 (2026-11-10) Table 16'])
for r in rows: print(r[0],r[1],r[2][:70])
print(len(rows))
