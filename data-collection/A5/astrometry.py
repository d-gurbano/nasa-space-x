"""Adopted astrometry for the 5 challenge targets (+ Eps Indi A).
Values VERIFIED from the catalog files in data/05-test-targets/catalogs (Gaia DR3 via
IRSA gaia_dr3_source, CatWISE2020 via IRSA) or from the cited paper.
ep = reference epoch (Julian year, TCB-ish; the difference is negligible here)."""
ASTRO = {
    # Gaia DR3 4472832130942575872
    "barnard": dict(ra=269.4485030, dec=4.7394200, pmra=-801.551, pmdec=10362.394, plx=546.9759, ep=2016.0, rv=-110.47,
                    src="Gaia DR3 4472832130942575872 (IRSA gaia_dr3_source)"),
    # Gaia DR3 6412596012146801152 (RUWE 4.3: Ba+Bb photocentre)
    "eps_indi_b": dict(ra=331.0764530, dec=-56.7938120, pmra=3981.977, pmdec=-2466.832, plx=270.6580, ep=2016.0,
                       src="Gaia DR3 6412596012146801152 (IRSA gaia_dr3_source)"),
    # Position: CatWISE2020 J085506.91-071437.5 ra_pm/dec_pm at MJD 57170 (2015.4);
    # PM + parallax: Kirkpatrick et al. 2021 ApJS 253 7 (-8123.7, +673.2 mas/yr; 439.0 mas), VERIFIED
    # in SIMBAD (Harvard mirror) Nov 15 2026. Luhman & Esplin 2016 give -8118, +680. Not in Gaia (G >> 21).
    "wise0855": dict(ra=133.783556, dec=-7.244052, pmra=-8123.7, pmdec=673.2, plx=439.0, ep=2015.3929,
                     src="CatWISE2020 position @MJD57170 + Kirkpatrick2021 PM/plx (via SIMBAD)"),
    # Gaia DR3 156430822114424576 (RW Aur A; B is 1.5" away, blended in SPHEREx/WISE)
    "rw_aur": dict(ra=76.9560810, dec=30.4012050, pmra=2.641, pmdec=-27.398, plx=6.4062, ep=2016.0,
                   src="Gaia DR3 156430822114424576 (IRSA gaia_dr3_source)"),
    # Gaia DR3 1648328016354496384
    "r_dra": dict(ra=248.1673780, dec=66.7550070, pmra=-20.643, pmdec=6.149, plx=1.2509, ep=2016.0,
                  src="Gaia DR3 1648328016354496384 (IRSA gaia_dr3_source)"),
}
EPS_INDI_A = dict(ra=330.8724080, dec=-56.7972550, pmra=3966.661, pmdec=-2536.192, plx=274.8431, ep=2016.0,
                  src="Gaia DR3 6412595290592307840 (IRSA gaia_dr3_source)")
