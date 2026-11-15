"""A1 - MPEC indexes: RecentMPECs (last 100 with titles) parsed, and the K25/K26 directory listings (file names + dates)."""
import re, pandas as pd
from common import get, save, D
for y in ("K25", "K26"):
    u = f"https://minorplanetcenter.net/mpec/{y}/"
    r = get(u, pause=3); save(f"mpc/mpec_dir_{y}.html", r.content, u)
    rows = re.findall(r'<a href="(%s\w+)\.html">[^<]*</a></td><td align="right">(\d{4}-\d\d-\d\d \d\d:\d\d)\s*</td><td align="right">([^<]*)</td>' % y, r.text)
    df = pd.DataFrame(rows, columns=["mpec_file", "modified", "size"]); df["url"] = f"https://minorplanetcenter.net/mpec/{y}/" + df.mpec_file + ".html"
    df.to_csv(D / f"clean/mpec_files_{y}.csv", index=False)
    print(y, len(rows))
t = open(D / "raw/mpc/RecentMPECs.html").read()
items = re.findall(r'<li><a href="(/mpec/K\d\d/\w+\.html)"><i>MPEC</i> ([^<]*)</a> \(([^)]*)\)\s*<ul>(.*?)</ul>', t, re.S)
rows = [(u, n, d, "; ".join(x.strip() for x in re.findall(r"<li>([^<\n]*)", body))) for u, n, d, body in items]
pd.DataFrame(rows, columns=["url", "mpec", "date", "objects"]).to_csv(D / "clean/recent_mpecs.csv", index=False)
print("recent", len(rows))
