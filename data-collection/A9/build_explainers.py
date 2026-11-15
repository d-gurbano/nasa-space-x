"""A9: plain-language explainers + citizen-science facts (text written by A9 from cited NASA/CNEOS pages)."""
import json
D='data/09-people/'
LD_KM=384400; AU_KM=149597870.7
torino=[(0,'White','No hazard','Chance of hitting is zero or effectively zero.'),
 (1,'Green','Normal','Routine find; a near pass with no unusual danger. More data almost always drops it to 0.'),
 (2,'Yellow','Meriting attention by astronomers','Somewhat close pass; collision very unlikely; no public concern.'),
 (3,'Yellow','Meriting attention by astronomers','1% or more chance of a hit causing local damage. Usually drops to 0 with more data. (2024 YR4 reached this level.)'),
 (4,'Yellow','Meriting attention by astronomers','1% or more chance of a hit causing regional damage. Usually drops to 0 with more data.'),
 (5,'Orange','Threatening','Serious but uncertain threat of regional damage.'),
 (6,'Orange','Threatening','Large object, serious but uncertain threat of global catastrophe.'),
 (7,'Orange','Threatening','Very close pass of a large object; unprecedented, uncertain global threat.'),
 (8,'Red','Certain collision','Certain hit causing local damage (happens about once per 50 to several 1000 years).'),
 (9,'Red','Certain collision','Certain hit causing regional damage (about once per 10,000 to 100,000 years).'),
 (10,'Red','Certain collision','Certain hit causing global climate catastrophe (about once per 100,000 years or less often).')]
E={
 'torino_scale':{'one_liner':'A 0-10 public "danger meter" for a possible future impact, combining the chance of a hit and how much damage it could do. It ignores how far away in time the event is.',
   'adopted':'IAU, 1999 (VERIFIED)','levels':[dict(level=l,color=c,zone=z,plain=p) for l,c,z,p in torino],
   'source':'https://cneos.jpl.nasa.gov/sentry/torino_scale.html','label':'VERIFIED (level text paraphrased)'},
 'palermo_scale':{'one_liner':'A specialist number that compares one possible impact with the normal background risk from all space rocks of that size until that date. Below -2: nothing to worry about. -2 to 0: keep watching. Above 0: some concern.',
   'formula':'PS = log10( P_impact / (f_B * years_until) ), f_B = 0.03 * E^(-4/5) per year, E in megatons (VERIFIED, CNEOS)',
   'examples':{'-2':'1% as likely as background (VERIFIED)','0':'as threatening as background (VERIFIED)','+2':'100 times background (VERIFIED)'},
   'source':'https://cneos.jpl.nasa.gov/sentry/palermo_scale.html'},
 'lunar_distance':{'one_liner':'1 lunar distance (LD) = the average Earth-Moon distance = 384,400 km (238,855 miles). About 30 Earths would fit in that gap.',
   'LD_km':LD_KM,'LD_miles':238855,'source':'https://science.nasa.gov/moon/facts/','label':'VERIFIED',
   'conversions_COMPUTED':{'1 au in LD':round(AU_KM/LD_KM,1),'1 LD in au':round(LD_KM/AU_KM,6),'geosynchronous ring (~36,000 km) in LD':round(36000/LD_KM,3),'Apophis 2029 (~32,000 km above surface) in LD':round((32000+6371)/LD_KM,3),'2024 YR4 miss of Moon 2032 (21,200 km) in LD':round(21200/LD_KM,3)},
   'code_snippet':'ld = km / 384400; km = ld * 384400; au = km / 149597870.7'},
 'close_approach_plain':{'one_liner':'A close approach is just the moment an object passes nearest to Earth. NASA/CNEOS computes these for all near-Earth objects from 1900 to 2200.',
   'pha_definition':'A Potentially Hazardous Asteroid comes within 0.05 au (about 19.5 LD, COMPUTED) of Earth orbit and is roughly 140 m or bigger (H 22.0 or brighter). This "potential" does not mean it will hit (VERIFIED, CNEOS FAQ).',
   'live_snapshot':'close_approaches_next60d_under5LD_cad.json (NASA/JPL CAD API, pulled today)','sources':['https://cneos.jpl.nasa.gov/ca/intro.html','https://cneos.jpl.nasa.gov/faq/','https://ssd-api.jpl.nasa.gov/doc/cad.html']},
 'sentry_snapshot':{'one_liner':'NASA Sentry keeps the list of objects with any non-zero impact chance in the next ~100 years. Nearly all are Torino 0.',
   'file':'sentry_summary.json','source':'https://ssd-api.jpl.nasa.gov/sentry.api'},
 'spherex':{'name':'SPHEREx = Spectro-Photometer for the History of the Universe, Epoch of Reionization, and Ices Explorer',
   'facts':[ 'Launched March 11, 2025 (VERIFIED, science.nasa.gov/mission/spherex)',
     'Sees the sky in 102 infrared colors (wavelengths), invisible to our eyes (VERIFIED, JPL news 2025-12-18)',
     'Circles Earth about 14.5 times a day over the poles and takes about 3,600 images a day (VERIFIED, JPL news 2025-12-18)',
     'Covers the whole sky every six months; began mapping in May 2025, finished the first all-sky map in December 2025; three more all-sky scans planned in the 2-year prime mission (VERIFIED, JPL news 2025-12-18)',
     'Will collect data on 450+ million galaxies and 100+ million Milky Way stars (VERIFIED, science.nasa.gov/mission/spherex)',
     'All data are free to the public (VERIFIED, JPL news 2025-12-18)',
     'Managed by NASA JPL; data archived at IPAC/IRSA (Caltech)'],
   'why_rewind':'Because it photographs every part of the sky every 6 months in 102 colors, any new asteroid was probably already caught in old SPHEREx photos - and the colors hint at what it is made of.',
   'sources':['https://science.nasa.gov/mission/spherex/','https://www.jpl.nasa.gov/news/nasas-spherex-observatory-completes-first-cosmic-map-like-no-other','https://www.nasa.gov/missions/spherex/nasas-spherex-observatory-completes-first-cosmic-map-like-no-other/']},
 'neowise':{'facts':['WISE launched Dec 14, 2009 on a Delta II from Vandenberg (VERIFIED)','Surveyed the full sky in 4 infrared bands: 3.4, 4.6, 12, 22 microns (VERIFIED)','Prime WISE mission Dec 2009 - Feb 2011; reactivated in 2013 as NEOWISE to hunt near-Earth asteroids and comets (VERIFIED)',
     'NEOWISE ended July 31, 2024, was decommissioned Aug 8, 2024 and reentered Earth atmosphere Nov 1, 2024 (VERIFIED)','Successor: NEO Surveyor, scheduled to launch in 2028 (VERIFIED, per page)','Famous find: Comet C/2020 F3 (NEOWISE), the bright comet of July 2020'],
   'why_rewind':'Fifteen years of infrared sky photos (2010-2024) - a deep "rewind" archive for checking where an object was before.',
   'source':'https://science.nasa.gov/mission/neowise/'},
 'media_rules':{'plain':'NASA images and video are generally not copyrighted in the US and can be used for education and information if NASA is credited and nothing implies NASA endorses us. The NASA logo (meatball), worm logotype and seal are NOT public domain and must not be used. Images marked with a third-party copyright (e.g. ESA, a university, a photographer) need that owner\'s permission. Identifiable people need permission for commercial/promotional use. No NFT or crypto use.',
   'ai_note':'The same NASA page (read today) says AI products must not attribute outputs to NASA ("according to NASA" is not allowed in AI-generated output), must not show NASA insignia with AI imagery, and should be marked as AI-generated. Relevant if Rewind shows AI-written text.',
   'credit_format':'"Image: NASA/JPL-Caltech" (or the exact credit given on the image page)',
   'source':'https://www.nasa.gov/nasa-brand-center/images-and-media/','label':'VERIFIED (paraphrased)'}
}
json.dump(E,open(D+'explainers/explainers.json','w'),indent=1,ensure_ascii=False)
C=[
 dict(project='Daily Minor Planet (Zooniverse, NASA citizen science)',launched='2023',what='Volunteers mark moving dots in Catalina Sky Survey (Mt Lemmon) and Bok 2.3 m (Kitt Peak) images as real or not.',numbers='Over 200 main-belt asteroids and 16 near-Earth asteroids discovered (as of Sept 2023); volunteers were credited by the Minor Planet Center two months after launch',label='VERIFIED',urls=['https://science.nasa.gov/citizen-science/daily-minor-planet','https://science.nasa.gov/get-involved/citizen-science/daily-minor-planet-volunteers-earn-nod-from-the-minor-planet-center'],rewind_parallel='Same task as Rewind Detectives: is this dot real?'),
 dict(project='International Astronomical Search Collaboration (IASC), Pan-STARRS images',launched='2006',what='Students and volunteers search Pan-STARRS images for asteroids; real finds go to the Minor Planet Center.',numbers='70,000+ citizen scientists in 100+ countries; 19,000+ previously unreported asteroids spotted (as of Nov 2025)',label='VERIFIED',urls=['https://science.nasa.gov/get-involved/citizen-science/new-way-you-can-discover-asteroids/'],rewind_parallel='Shows the scale a classroom-friendly asteroid hunt can reach.'),
 dict(project='Active Asteroids (Zooniverse, NASA partner)',launched='2021-08-31',what='Volunteers look at DECam (Blanco 4 m, Chile) cutouts of known asteroids for comet-like tails.',numbers='About 8,300 volunteers checked about 430,000 images; activity found on 15 asteroids plus 1 Centaur (2024 paper); 20 discoveries listed on project results page',label='VERIFIED',urls=['https://www.zooniverse.org/projects/orionnau/active-asteroids/about/results','https://iopscience.iop.org/article/10.3847/1538-3881/ad1de2','https://science.nasa.gov/citizen-science/active-asteroids/'],rewind_parallel='AI + people together: an AI filter flagged 2016 UU121 and 2008 GB140, volunteers confirmed.'),
 dict(project='Sungrazer Project (NASA-funded, US Naval Research Laboratory)',launched='2003 (approx; not verified here)',what='Anyone can search ESA/NASA SOHO and NASA STEREO images for new comets near the Sun.',numbers='SOHO 5,000th comet found Mar 25, 2024 by a citizen scientist; Sungrazer site shows 5,204 comets discovered so far (as read 2026)',label='VERIFIED (launch year ESTIMATED)',urls=['https://science.nasa.gov/science-research/heliophysics/esa-nasa-solar-observatory-discovers-its-5000th-comet','https://sungrazer.nrl.navy.mil/home'],rewind_parallel='Old spacecraft images, never designed for comet hunting, became the biggest comet discoverer in history.'),
 dict(project='Backyard Worlds: Planet 9 (NASA, Zooniverse)',launched='2017',what='Volunteers flip through WISE/NEOWISE infrared images to find faint moving objects.',numbers='Over 3,000 new brown dwarfs over ~10 years, roughly doubling the known population (May 2026)',label='VERIFIED (launch year ESTIMATED)',urls=['https://science.nasa.gov/get-involved/citizen-science/nasa-volunteers-double-known-population-of-brown-dwarfs'],rewind_parallel='Same data (WISE/NEOWISE) and same "blink old images" method as Rewind.'),
 dict(project='NASA citizen science on Zooniverse (all projects)',launched='-',what='Platform total.',numbers='31 NASA-sponsored projects, 120 million classifications by 324 thousand volunteers since 2020; 96 papers, 56 with citizen co-authors (July 2026); Zooniverse reached 1 billion classifications',label='VERIFIED',urls=['https://science.nasa.gov/get-involved/citizen-science/nasa-volunteers-help-zooniverse-reach-1-billion-classifications'],rewind_parallel='Pitch line: people-powered checking is proven at huge scale.'),
 dict(project='Comet Hunters (Zooniverse)',launched='-',what='Main-belt comet search in Subaru images.',numbers='Not verified in this pass',label='NOT VERIFIED',urls=[],rewind_parallel='Partner (Japan Subaru data); listed only for completeness.'),
]
json.dump(C,open(D+'citizen-science/citizen_science_facts.json','w'),indent=1,ensure_ascii=False)
print('ok')
