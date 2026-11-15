import requests, json
u='https://astroarchive.noirlab.edu/api/adv_search/find/?limit=5&format=json'
body={"outfields":["md5sum","archive_filename","instrument","proc_type","obs_type","caldat","dateobs_center","ra_center","dec_center","exposure","ifilter","url"],
 "search":[["instrument","decam"],["proc_type","instcal"],["caldat","2019-01-01","2019-01-31"],["ra_center",30,40],["dec_center",-10,0]]}
r=requests.post(u,json=body,timeout=300); print(r.status_code); print(r.text[:1500])
