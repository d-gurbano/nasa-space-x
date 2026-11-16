// Types for the Rewind data contract v1 (docs/DATA-CONTRACT.md).
import type { PlanetRow, Vec3 } from './kepler';

export type Verdict = 'FOUND' | 'HINT' | 'TOO_FAINT' | 'NO_PHOTOS' | 'PENDING';
export type Kind = 'comet' | 'neo' | 'mba' | 'lost' | 'famous';

export interface IndexObject {
  slug: string;
  name: string;
  kind: Kind;
  verdict: Verdict;
  verdict_text: string;
  discovered: { mjd: number; iso: string; by: string; site: string };
  first_spherex_hint: { mjd: number; iso: string; days_before_discovery: number | null } | null;
  /** The first observation anyone reported. An object can be observed before it is announced. */
  first_known_obs_iso?: string | null;
  /** Days from the first SPHEREx photo to the first known observation; null = not earlier than it. */
  days_before_first_known_obs?: number | null;
  claim?: string | null;
  best_snr: number;
  n_frames: number;
  thumb: string;
  page: string;
}

export interface FlashEvent {
  slug: string;
  mjd: number;
  iso: string;
  photo: string;
  spherex_xyz_au: Vec3;
  object_xyz_au: Vec3;
  label: string;
  snr?: number | null;
  /** false = taken after the first known observation: an extra position, not a precovery. */
  before_first_known_obs?: boolean;
}

export interface SiteIndex {
  schema: string;
  generated: string;
  sample: boolean;
  final?: boolean; // true once the engine has finished its last run
  headline_stats: { objects_searched: number; found: number; hints: number; too_faint: number; frames_read: number };
  benchmark: string;
  objects: IndexObject[];
  flash_events: FlashEvent[];
}

export interface OrbitsTable {
  schema: string;
  epoch_mjd: number;
  fields: string[];
  flag_bits: Record<string, string>;
  rows: number[][];
}

export const FLAG = { NEO: 1, PHA: 2, NEW: 4, COMET: 8, IN_REWIND: 16 } as const;

export interface PlanetsFile {
  schema?: string;
  source?: string;
  sample?: boolean;
  planets: PlanetRow[];
}

export interface Frame {
  key: string; mjd: number; iso: string; detector: number | string; wavelength_um: number;
  pred_ra: number; pred_dec: number; sigma_px: number;
  flux_ujy: number | null; flux_err: number | null; snr: number | null; flags: number | string; used: boolean; png: string | null;
}

export interface ObjectPage {
  schema: string; slug: string; name: string; kind: Kind; verdict: Verdict; verdict_text: string; sample: boolean;
  story: { discovered_iso: string; by: string; site: string; plain: string; sources: string[] };
  facts: {
    H: number | null; diameter_km: number | null; albedo: number | null; class: string | null;
    neo: boolean; pha: boolean; sentry: boolean; moid_au: number | null;
    next_close_approach: { iso: string; dist_ld: number } | null;
  };
  // fields can be null when the engine has no orbit (e.g. a comet with only a short arc)
  orbit: { epoch_mjd: number; a: number; e: number; i: number; node: number; peri: number; M: number; q: number | null; Q: number | null; period_yr: number | null } | null;
  cloud: null | {
    dates_mjd: number[];
    before: Vec3[][];
    after: Vec3[][] | null;
    before_sigma_km_at: { iso: string; km: number };
    after_sigma_km_at: { iso: string; km: number } | null;
    note: string;
  };
  spherex: {
    frames: Frame[];
    days: { iso: string; n_frames: number; snr: number | null; png: string }[];
    stack: { png: string; png_median: string; snr: number | null; ab_mag: number | null; n_frames: number };
    spherex_xyz_au_at_frames: Vec3[];
  };
  checks: {
    null_paths: { n: number; snr_mean: number; snr_std: number; n_exceeding: number };
    time_shift: { shifts_days: number[]; snr: number[] };
    per_day_positive: string;
    static_sky_subtracted: { snr: number | null };
    injection: { limit_ab_mag: number | null; recovered_fraction_at_object_mag: number | null };
    orbit_fit: { rms_arcsec_before: number; rms_arcsec_after: number; new_points: number } | null;
    trail_px: number;
    clone_search: { n_clones: number; false_alarm_rate: number; n_null_trials?: number } | null;
    real_or_fake_score: number | null;
    frac_positive?: { target: number; null_mean: number; null_std: number; null_max: number } | null;
    passed?: Partial<Record<CheckKey, boolean>>;
  };
  composition: {
    points: { um: number; value: number; err: number }[];
    templates: { name: string; um: number[]; value: number[] }[];
    best_match: string | null;
    label: string;
    note?: string;
  };
  quiz: { image: string; answer_xy: [number, number]; answer_text: string };
  shape_model: { glb: string; source: string; credit: string } | null;
  credits: string[];
  /** What the SPHEREx positions change. The scenario is computed, and labelled so. */
  impact?: {
    at_discovery_scenario?: { factor?: number; converged?: boolean; label?: string; error?: string; sigma3_km_before?: number; sigma3_km_after?: number } | null;
    one_year_after_last_obs?: { iso: string; sigma3_km_before: number; sigma3_km_after: number; factor: number } | null;
  } | null;
  first_known_obs_iso?: string | null;
  days_before_first_known_obs?: number | null;
}

/** The nine detection checks, in the order the engine defines them (docs/DATA-CONTRACT.md). */
export type CheckKey = 'snr' | 'cleaned' | 'nulls' | 'time_shift' | 'days' | 'detectable' | 'sign_test' | 'not_one_day' | 'orbit';

export interface Benchmark {
  sample?: boolean;
  cases: { name: string; hidden_until_iso: string; truth: string; rewind_verdict: string; snr: number; pos_err_arcsec: number }[];
  summary: { n: number; found: number; missed: number; false_alarms: number; plain: string };
}

export interface StarManifest {
  sample?: boolean;
  slug: string; name: string; ra: number; dec: number; pm: Record<string, number>;
  image?: { arcsec_per_png_px: number; size_px: number; spherex_pixel_arcsec: number };
  seasons: { iso: string; png: string; n_frames?: number }[];
  frames: { iso: string; mjd: number; wavelength_um: number; png: string; pred_xy: [number, number] }[];
  stack: { png: string; snr: number; n_frames?: number };
  n_frames_total?: number;
  motion_caption: string;
  note: string;
}

export interface DetectiveRounds {
  sample?: boolean;
  /** Why no round shows a Rewind find; shown on the page as it is. */
  real_rounds_note?: string;
  rounds: {
    id: string;
    truth: 'planted' | 'known' | 'empty';
    /** Photos of one fixed, north-up patch of sky, in time order. */
    frames: { png: string; iso: string; wavelength_um: number }[];
    /** The mover's place in each photo, in PNG pixels (x right, y down); null when nothing moves. */
    track_xy: [number, number][] | null;
    /** How close a mark must be to the track, in PNG pixels. */
    tolerance_px: number;
    explain: string;
    difficulty: 'easy' | 'medium' | 'hard';
  }[];
}
