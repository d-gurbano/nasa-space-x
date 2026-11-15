"""A9: curated discovery stories (hand-checked against cited sources) + auto stories for recent objects from MPC discovery lines."""
import json, csv, os
OUT='data/09-people/stories'
S=[
 dict(object='2024 YR4',type='near-Earth asteroid (Apollo)',discoverer='ATLAS (Asteroid Terrestrial-impact Last Alert System), NASA-funded, University of Hawaii',site='ATLAS Rio Hurtado, Chile (MPC code W68)',discovery_date='2024-12-27',
  story='Found two days after it had already passed Earth on Dec 25, 2024. For a few weeks in early 2025 it had the highest impact chance ever recorded for an object its size (Torino 3). More telescope data ruled out an Earth impact in 2032. Webb then measured it at about 60 m wide, and new Webb positions from Feb 2026 also ruled out a Moon impact: it will pass about 21,200 km from the Moon on Dec 22, 2032.',
  rewind_hook='Every new old photo shrinks the uncertainty cloud - exactly what Rewind does.',
  facts={'size_m':'60 +/- 7 (VERIFIED, JWST, Rivkin et al. 2025 via RNAAS 2026)','peak_torino':'3 (VERIFIED, CNEOS news210)','lunar_impact_prob_before_feb2026':'4.3% (VERIFIED, NASA blog 2026-03-05)','moon_miss_distance_km':'21,200 (VERIFIED, NASA blog 2026-03-05)'},
  sources=['https://cneos.jpl.nasa.gov/news/news210.html','https://science.nasa.gov/solar-system/asteroids/2024-yr4-facts/','https://science.nasa.gov/blogs/planetary-defense/2026/03/05/new-nasa-asteroid-observations-eliminate-chance-of-2032-lunar-impact/','https://iopscience.iop.org/article/10.3847/2515-5172/ae4fb4']),
 dict(object='3I/ATLAS (C/2025 N1)',type='interstellar comet',discoverer='ATLAS survey (NASA-funded)',site='ATLAS Rio Hurtado, Chile (W68)',discovery_date='2025-07-01',
  story='Only the third object ever seen coming from another star system (after Oumuamua in 2017 and Borisov in 2019). ATLAS reported it on July 1, 2025. Within hours, astronomers dug through older images and found it was already there: Zwicky Transient Facility (June 28-29), other ATLAS telescopes (back to June 14), and NASA TESS (May 2025). Its speed and very open path (eccentricity about 6.1) prove it is not bound to the Sun.',
  rewind_hook='The best-known recent case of finding a new object in older archive photos - the core Rewind idea.',
  facts={'eccentricity':'~6.1 (VERIFIED, Seligman/Bolin MNRAS Letters 2025; IfA gives 6.137)','v_infinity_km_s':'57 (VERIFIED, MNRAS Letters 542 L139)','earliest_precovery':'TESS May 2025 (VERIFIED, NASA open-science article 2026-03-20)'},
  sources=['https://science.nasa.gov/solar-system/comets/3i-atlas/3i-atlas-facts-and-faqs','https://science.nasa.gov/solar-system/comets/3i-atlas','https://science.nasa.gov/open-science/interstellar-comet-3i-atlas-data','https://researchimpact.caltech.edu/research-news/zwicky-transient-facility-nabs-an-interstellar-visitor','https://academic.oup.com/mnrasl/article/542/1/L139/8206197']),
 dict(object='99942 Apophis',type='near-Earth asteroid (Aten), potentially hazardous',discoverer='Roy A. Tucker, David J. Tholen, Fabrizio Bernardi',site='Kitt Peak, Arizona',discovery_date='2004-06-19',
  story='Found from Kitt Peak in Arizona in 2004. Early predictions could not rule out a 2029 impact; more observations, including older precovery images, ruled that out, and NASA says it poses no risk for at least 100 years. On April 13, 2029 it will pass about 32,000 km above the surface of Earth, closer than geosynchronous satellites (about 36,000 km). Named after the Egyptian god of chaos.',
  rewind_hook='Old precovery images extended its arc back to March 2004 (SBDB first_obs 2004-03-15) and helped clear the 2029 scare.',
  facts={'first_obs':'2004-03-15 (VERIFIED, SBDB)','flyby_2029_km_above_surface':'32,000 (VERIFIED, NASA Apophis facts page)','no_risk_years':'at least 100 (VERIFIED, NASA Apophis page)'},
  sources=['https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr=99942','https://science.nasa.gov/solar-system/asteroids/apophis/']),
 dict(object='101955 Bennu',type='near-Earth asteroid (Apollo), potentially hazardous',discoverer='LINEAR (Lincoln Laboratory Near-Earth Asteroid Research), MIT Lincoln Lab, USAF/NASA',site='Socorro, New Mexico',discovery_date='1999-09-11',
  story='Found by the LINEAR survey in New Mexico in 1999. NASA OSIRIS-REx visited it, grabbed a sample in 2020 and delivered it to Earth in September 2023. Bennu is named after an Egyptian mythological figure (see the official citation in names/).',
  rewind_hook='A rubble pile we have touched - perfect "what is it made of" anchor.',
  facts={'name_citation':'see names/featured_name_meanings.csv (VERIFIED, SBDB)'},
  sources=['https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr=101955','https://science.nasa.gov/solar-system/asteroids/101955-bennu/']),
 dict(object='65803 Didymos and Dimorphos',type='near-Earth binary asteroid (Amor)',discoverer='Spacewatch (University of Arizona)',site='Kitt Peak, Arizona',discovery_date='1996-04-11',
  story='Didymos was found by the University of Arizona Spacewatch survey in 1996; its small moon, Dimorphos (about 160 m), was found later. On Sept 26, 2022, NASA DART crashed into Dimorphos and measurably shortened its orbit around Didymos - the first time humans moved a celestial body on purpose.',
  rewind_hook='Proof that knowing an orbit early lets us change it.',
  facts={'dimorphos_diameter_m':'160 (VERIFIED, NASA DART page)','didymos_diameter_m':'780 (VERIFIED, NASA DART page)','impact_date':'2022-09-26 (VERIFIED)','orbit_change':'not re-checked in this pass'},
  sources=['https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr=65803','https://science.nasa.gov/mission/dart/']),
 dict(object='2024 PT5',type='near-Earth asteroid, temporary mini-moon',discoverer='ATLAS (NASA-funded, University of Hawaii)',site='ATLAS Sutherland, South Africa (M22)',discovery_date='2024-08-07',
  story='A tiny rock about 5-11 m across found by the ATLAS telescope in South Africa. It was loosely captured by Earth from Sept 29 to Nov 25, 2024, as a short-lived "mini-moon". Its colors look like lunar rock, so it may be a piece knocked off the Moon long ago.',
  rewind_hook='Small, fast, easy to miss - the kind of object old frames can pin down.',
  facts={'capture':'2024-09-29 to 2024-11-25 (VERIFIED, Bolin et al. 2025 ApJL)','diameter_m':'5.4 +/- 1.2 (VERIFIED, Bolin et al.)'},
  sources=['https://iopscience.iop.org/article/10.3847/2041-8213/ada1d0','https://iopscience.iop.org/article/10.3847/2041-8213/ad9ea8','https://www.hawaii.edu/news/2024/09/24/new-companion-asteroid-discovered']),
 dict(object='2025 PN7',type='near-Earth asteroid, Earth quasi-satellite',discoverer='Pan-STARRS 1 (University of Hawaii, NASA-funded)',site='Haleakala, Maui, Hawaii (F51)',discovery_date='2025-08-02',
  story='A small rock (roughly 20 m class) that circles the Sun in step with Earth, so from here it looks like a loop around us - a "quasi-moon". Pan-STARRS caught it in Aug 2025, and older archive detections stretch its record back to 2014 (27 observations over 4,279 days at announcement). It has kept Earth company for decades and will stay roughly 60 more years.',
  rewind_hook='Hidden in old data for over a decade before anyone connected the dots.',
  facts={'arc_days_at_announcement':'4279 (VERIFIED, de la Fuente Marcos 2025 RNAAS)','SBDB_first_obs':'2013-12-11 (VERIFIED, SBDB today)'},
  sources=['https://iopscience.iop.org/article/10.3847/2515-5172/ae028f']),
 dict(object='2025 MN45',type='main-belt asteroid, record fast rotator',discoverer='NSF-DOE Vera C. Rubin Observatory (pre-survey commissioning data)',site='Cerro Pachon, Chile (X05)',discovery_date='2025-05-02 (MPC discovery line, X05)',
  story='Found in Rubin Observatory first-look data in 2025: about 710 m wide yet it spins once every 1.88 minutes, the fastest known for any asteroid over half a kilometer. That means it must be solid, strong rock, not a loose rubble pile.',
  rewind_hook='New surveys find new objects every night - Rewind checks whether older infrared photos already caught them.',
  facts={'diameter_m':'710 (VERIFIED, NOIRLab noirlab2601)','period_min':'1.88 (VERIFIED, NOIRLab)'},
  partner_note='US NSF/DOE facility (not NASA); US-funded, allowed.',
  sources=['https://noirlab.edu/public/news/noirlab2601']),
]
# merge SBDB raw where available
raw={r['query']:r for r in json.load(open(f'{OUT}/sbdb_featured_raw.json'))}
key={'99942 Apophis':'99942','101955 Bennu':'101955','65803 Didymos and Dimorphos':'65803','2024 YR4':'2024 YR4','2024 PT5':'2024 PT5','2025 PN7':'2025 PN7','2025 MN45':'2025 MN45','3I/ATLAS (C/2025 N1)':'3I'}
mpc={}
if os.path.exists(f'{OUT}/mpc_discovery_observations.csv'):
    mpc={r['object']:r for r in csv.DictReader(open(f'{OUT}/mpc_discovery_observations.csv'))}
feat={r['object']:r for r in csv.DictReader(open(f'{OUT}/mpc_discovery_featured.csv'))} if os.path.exists(f'{OUT}/mpc_discovery_featured.csv') else {}
feat['3I']=feat.get('C/2025 N1')
for s in S:
    r=raw.get(key.get(s['object'],''),{})
    s['sbdb']={k:r.get(k) for k in ['fullname','orbit_class','neo','pha','first_obs','last_obs','n_obs_used','disc_text','disc_location','disc_date']}
    m=mpc.get(key.get(s['object'],'')) or feat.get(key.get(s['object'],''))
    if m: s['mpc_discovery_obs']={k:m[k] for k in ['disc_date_utc','station_code','station_name','n_obs_mpc']}
    s['label']='VERIFIED (read in cited sources); story text is our plain-language summary'
json.dump(S,open(f'{OUT}/featured_discovery_stories.json','w'),indent=1,ensure_ascii=False)
with open(f'{OUT}/featured_discovery_stories.csv','w',newline='') as f:
    w=csv.writer(f); w.writerow(['object','type','discoverer_or_survey','site','discovery_date','short_story','source_urls'])
    for s in S: w.writerow([s['object'],s['type'],s['discoverer'],s['site'],s['discovery_date'],s['story'],' '.join(s['sources'])])
# auto stories for recent objects
if mpc:
    rec={}
    for fn in ['recent_neo_since2025_sbdb.csv','recent_comet_since2025_sbdb.csv']:
        for r in csv.DictReader(open(f'{OUT}/{fn}')): rec[r['pdes']]=r
    rows=[]
    for o,m in mpc.items():
        if o not in rec: continue
        r=rec[o]
        stn=m['station_name'] or m['station_code']
        d=m['disc_date_utc'][:10].replace(' ','-')
        kind='comet' if (o.startswith('C/') or o.startswith('P/') or r.get('class','') in ('JFc','HTC','COM','HYP','PAR','ETc','CTc')) else ('potentially hazardous near-Earth asteroid' if r['pha']=='Y' else 'near-Earth asteroid')
        size=f" Its brightness suggests a size of roughly {r['diameter']} km." if r.get('diameter') else ''
        story=f"{r['full_name'].strip()} is a {kind} first reported from {stn} (MPC code {m['station_code']}) on {d} UTC.{size}"
        rows.append(dict(object=r['full_name'].strip(),type=kind,discoverer_or_survey=stn,site_code=m['station_code'],discovery_date_utc=m['disc_date_utc'],H=r['H'],moid_au=r['moid'],pha=r['pha'],n_obs_mpc=m['n_obs_mpc'],short_story=story,source_url=f"https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr={o.replace(' ','%20')}",label='VERIFIED (MPC discovery-flagged observation); story auto-generated'))
    with open(f'{OUT}/recent_discovery_stories_auto.csv','w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print('auto',len(rows))
print('featured',len(S))
