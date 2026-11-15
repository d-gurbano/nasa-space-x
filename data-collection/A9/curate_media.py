"""A9: curation pass over downloaded NASA media (manual decisions after viewing a contact sheet). Moves excluded files to media/excluded/ (kept, not deleted)."""
import csv, os, shutil, re
M='data/09-people/media'; os.makedirs(f'{M}/excluded',exist_ok=True)
EXCL={ 'PIA23866':'off-topic (black hole)','NHQ201812310031':'identifiable people, off-topic','NHQ201812310033':'identifiable people, off-topic',
 'NHQ202308300006':'identifiable person in flight suit with mission patches/insignia','NHQ202308300009':'identifiable people','KSC-20230511-PH-FMX01_0034':'identifiable people at presentation',
 'jsc2023e048789':'portrait of identifiable person','jsc2025e008857':'identifiable person','PIA24788':'identifiable people','PIA25785':'identifiable people, non-NASA credit (AACS)',
 'KSC-99pc':'off-topic 1999 spacecraft processing, possible NASA insignia on hardware','KSC-20211002-PH-DNQ01':'truck/container shots, possible NASA insignia',
 'PIA16675':'ESA copyright (Herschel)','PIA18596':'ESA copyright (Rosetta OSIRIS)','PIA18899':'ESA copyright (Rosetta NAVCAM)','PIA18879':'ESA copyright (Philae CIVA)','PIA17484':'ESA/partner credit',
 'PIA23462':'Canada-France-Hawaii Telescope image (non-NASA)',
 'KSC-20211129-VP_FJM03_KCD_Derrol_Nail':'host-presented NASA show, identifiable people, off-topic','0091_NEA_Scout_Music':'music track - possible third-party audio rights','ksc_092707_dawn_patel':'interview of identifiable person (Dawn)'}
PARTNER={'PIA25434':'ESA/NASA/JPL-Caltech joint credit','PIA21614':'Dawn: UCLA/MPS/DLR/IDA in credit','PIA16116':'Dawn: UCLA/MPS/DLR/IDA in credit','PIA15826':'Dawn: UCLA/MPS/DLR/IDA in credit','PIA15823':'Dawn: UCLA/MPS/DLR/IDA in credit'}
HW=re.compile(r'Spacecraft|Assembly|Testing|Photon Shield|Radiator|Filters|Encapsulation|Instrument Enclosure|Bus|Sunshade|Thruster|Arrival|Uncrating|Launch|Booster|Trays|Sample Arrives|Training',re.I)
VIDEO_USE={'JPL-20250130-SPHERX':'30s video: SPHEREx intro','GSFC_20201008_M13729_BennuTour':'30s video: asteroid close-up','GSFC_20150915_SOHO':'citizen-science segment','GSFC_20130206_SDO':'citizen-science segment','JPL-20240809-NEOWISf':'NEOWISE archive segment','JPL-20240801-NEOWISf':'NEOWISE archive segment','KSC-20211123':'planetary-defense segment (DART launch)'}
def decide(r):
    nid=r['nasa_id']; base=os.path.basename(r['local_file'])
    for k,v in EXCL.items():
        if nid.startswith(k) or base.startswith(k): return 'exclude',v
    notes=[]
    if nid in PARTNER: notes.append('partner credit: '+PARTNER[nid]+' - use full credit line')
    if re.search(r'BAE Systems|Space Dynamics Laboratory|Allison Bills|Steve Gribben|Dan Caselden|Arecibo|GBO|NSF|University',r.get('secondary_creator','')): notes.append('contractor/partner name in credit - copy exact credit line')
    if HW.search(r['title']): notes.append('hardware/event photo - check frame for NASA insignia or logos before use; crop or skip if visible')
    if r.get('non_nasa_credit_flag')=='Y' and nid not in PARTNER: notes.append('description mentions non-NASA credit - check page')
    return ('keep_check' if notes else 'keep'),'; '.join(notes)
for kind in ['images','videos']:
    fn=f'{M}/{kind}_metadata.csv'; rows=list(csv.DictReader(open(fn)))
    for r in rows:
        st,why=decide(r); r['curation']=st; r['curation_note']=why
        sc=r.get('secondary_creator','').strip(); ph=r.get('photographer','').strip()
        r['credit_line']=(sc if sc else 'NASA/'+(r.get('center') or ''))+(f' (photo: {ph})' if ph and ph not in sc else '')
        r['license']='NASA media, generally not copyrighted in the US; credit NASA; no endorsement; no NASA insignia (https://www.nasa.gov/nasa-brand-center/images-and-media/)' if st!='exclude' else 'excluded - see note'
        r['suggested_use']=next((v for k,v in VIDEO_USE.items() if r['nasa_id'].startswith(k)),'')
        if st=='exclude' and os.path.exists(f"{M}/{r['local_file']}"):
            shutil.move(f"{M}/{r['local_file']}",f"{M}/excluded/{os.path.basename(r['local_file'])}"); r['local_file']='excluded/'+os.path.basename(r['local_file'])
    with open(fn,'w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(kind,{s:sum(1 for r in rows if r['curation']==s) for s in ['keep','keep_check','exclude']})
# fix manifest paths
man=list(csv.DictReader(open(f'{M}/manifest.csv')))
for m in man:
    b=os.path.basename(m['filename'])
    if os.path.exists(f'{M}/excluded/{b}'): m['filename']='media/excluded/'+b
    elif not m['filename'].startswith('media/'): m['filename']='media/'+m['filename']
with open(f'{M}/manifest.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['filename','url','bytes','sha256','date']); w.writeheader(); w.writerows(man)
