// Star speedometer logic, kept apart from the page so it can be tested: turning a drag on the
// image into a shift on the sky, a rate per year, a compass direction and a score.

export interface SpeedEnd {
  date: string;
  mjd: number;
  season: string;
  n_frames: number;
  /** Our measured star position in the 488 px season PNG. */
  xy: [number, number];
}

export interface SpeedRound {
  slug: string;
  name: string;
  a: SpeedEnd;
  b: SpeedEnd;
  /** Our measured shift between the two passes, arcsec (east and north positive). */
  meas_east: number;
  meas_north: number;
  meas_err: number;
  gaia_mas_yr: number;
  gaia_source: string;
  year_pred_arcsec: number;
  year_meas_arcsec: number;
}

export interface SpeedData {
  scale_arcsec_per_px: number;
  size_px: number;
  source: string;
  rounds: SpeedRound[];
}

export const DAYS_PER_YEAR = 365.25;

/** A PNG pixel step to a sky shift. The images are north up, east left. */
export function pxToSky(dx: number, dy: number, scale: number): { east: number; north: number; total: number } {
  const east = -dx * scale, north = -dy * scale;
  return { east, north, total: Math.hypot(east, north) };
}

/** Arcsec over some days to arcsec per year. */
export function perYear(arcsec: number, days: number): number {
  return days > 0 ? (arcsec * DAYS_PER_YEAR) / days : 0;
}

/** Eight-point compass name for a shift, or null if it is too small to have a direction. */
export function compass(east: number, north: number, min = 0.5): string | null {
  if (Math.hypot(east, north) < min) return null;
  const names = ['north', 'north-east', 'east', 'south-east', 'south', 'south-west', 'west', 'north-west'];
  const ang = (Math.atan2(east, north) * 180) / Math.PI; // 0 = north, 90 = east
  return names[Math.round(((ang + 360) % 360) / 45) % 8];
}

/** Points for a guess that lands `miss` arcsec from where we measured the star. */
export function score(miss: number): number {
  if (miss <= 1) return 10;
  if (miss <= 2) return 7;
  if (miss <= 4) return 4;
  return 0;
}

/** Keep a marker inside the image. */
export function clamp(v: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, v));
}
