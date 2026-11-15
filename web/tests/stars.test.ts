import { describe, expect, it } from 'vitest';
import { lightCurve, niceStep, parseCsv, passSpots, pctFromMag, track } from '../src/views/stars/logic';

const positions = `source,year,pred_east_from_ref,pred_north_from_ref,meas_east_from_ref,meas_north_from_ref,resid_arcsec,note
DSS poss1_red,1950.5,0,0,,,,target too faint for this survey; peak is not the target
DASCH mc1,1915.3,0,0,0.3,0.4,0.5,
DSS poss1_red,1950.4,3,4,3,4.2,0.2,
DSS poss1_blue,1950.6,3,4,3,3.8,0.2,
2MASS J,1998.2,30,40,,,,nearest peak > 5 arcsec from prediction (confused)
SPHEREx pass 0,2025.6,60,80,60,80,0.1,
SPHEREx pass 1,2026.6,66,88,66,88,0.3,
`;

describe('parseCsv', () => {
  it('reads rows by header name and keeps empty cells empty', () => {
    const rows = parseCsv(positions);
    expect(rows).toHaveLength(7);
    expect(rows[0].source).toBe('DSS poss1_red');
    expect(rows[0].meas_east_from_ref).toBe('');
    expect(rows[1].resid_arcsec).toBe('0.5');
  });
});

describe('track', () => {
  const t = track(parseCsv(positions))!;

  it('groups the measured photos by telescope and year, with all SPHEREx passes as one dot', () => {
    expect(t.points.map((p) => [p.family, p.n])).toEqual([['Harvard glass plate', 1], ['Digitized Sky Survey', 2], ['SPHEREx', 2]]);
    expect(t.points[2].spherex).toBe(true);
    expect([t.points[2].first, t.points[2].last]).toEqual([2025.6, 2026.6]);
  });

  it('measures the distance from the predicted spot of the first photo that shows the star', () => {
    expect(t.points[0].moved).toBeCloseTo(0.5);
    expect(t.points[1].moved).toBeCloseTo(Math.hypot(3, 3.8)); // a dot sits where its last photo is
    expect(t.points[2].moved).toBeCloseTo(110);
    expect(t.points[1].miss).toBeCloseTo(0.2);
  });

  it('draws the prediction from the first measured year on, through the photos that were not measured', () => {
    expect(t.line[0]).toEqual([1915.3, 0]);
    expect(t.line.map((p) => p[0])).toContain(1998.2);
    expect(t.line[t.line.length - 1]).toEqual([2026.6, 110]);
  });

  it('counts only the photos left out for being too faint, and needs two measured photos', () => {
    expect(t.tooFaint).toBe(1);
    expect(track(parseCsv(positions).slice(0, 2))).toBeNull();
  });
});

describe('lightCurve', () => {
  it('turns magnitudes into per cent brighter or fainter', () => {
    expect(pctFromMag(0)).toBe(0);
    expect(pctFromMag(-0.75)).toBeCloseTo(99.5, 1); // 0.75 mag brighter is about twice as bright
    expect(pctFromMag(0.75)).toBeCloseTo(-49.9, 1);
  });

  it('gives one median for each pass in each half of the spectrum, in time order', () => {
    const lc = lightCurve(parseCsv(`mjd,detector,saturated,pass,dmag_vs_median_sed
60900,1,True,0,0.0
60901,2,True,0,-0.75
60902,3,False,0,0.75
61080,2,True,1,0.75
60900,5,True,0,
61081,6,False,1,-0.75
`));
    expect(lc.points).toHaveLength(5); // the row without a brightness is dropped
    expect(lc.points.filter((p) => p.saturated)).toHaveLength(3);
    expect(lc.medians.map((m) => [m.band, m.pass, m.n, Math.round(m.pct)])).toEqual([[0, 0, 3, 0], [0, 1, 1, -50], [1, 1, 1, 100]]);
    expect(lc.medians[0].mjd).toBe(60901);
  });
});

describe('passSpots', () => {
  it('averages the predicted spot of the photos near each pass, and is null when there are none', () => {
    const frame = (mjd: number, x: number, y: number) => ({ iso: '', mjd, wavelength_um: 1, png: '', pred_xy: [x, y] as [number, number] });
    const spots = passSpots({
      seasons: [{ iso: '2025-08-27', png: '' }, { iso: '2026-03-17', png: '' }, { iso: '2026-08-21', png: '' }],
      frames: [frame(60910, 240, 270), frame(60920, 244, 274), frame(61270, 248, 218)],
    });
    expect(spots).toEqual([[242, 272], null, [248, 218]]);
  });
});

describe('niceStep', () => {
  it('picks round axis steps', () => {
    expect(niceStep(19.2, 4)).toBe(5);
    expect(niceStep(137, 4)).toBe(50);
    expect(niceStep(111, 7)).toBe(20);
    expect(niceStep(16, 7)).toBe(2);
  });
});
