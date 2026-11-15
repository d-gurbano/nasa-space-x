// MPC 80-column optical astrometry lines, for expert review only (never submitted).
// Format: https://minorplanetcenter.net/iau/info/OpticalObs.html

const B62 = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz';

function packCycle(n: number): string {
  if (n < 100) return String(n).padStart(2, '0');
  return B62[Math.floor(n / 10)] + String(n % 10);
}

function packYear(y: number): string {
  return String.fromCharCode('A'.charCodeAt(0) + Math.floor(y / 100) - 10) + String(y % 100).padStart(2, '0');
}

/**
 * Pack a designation into columns 1-12.
 * "2025 OZ" -> "     K25O00Z", "2026 RD39" -> "     K26R39D", "C/2026 S1" -> "    CK26S010", "433" -> "00433       ".
 */
export function packDesignation(name: string): string {
  const s = name.trim();
  const num = s.match(/^\((\d+)\)/) ?? s.match(/^(\d+)$/);
  if (num) {
    const n = +num[1];
    const p = n < 100000 ? String(n).padStart(5, '0') : B62[Math.floor(n / 10000)] + String(n % 10000).padStart(4, '0');
    return p.padEnd(12);
  }
  const comet = s.match(/^([CPDXAI])\/(\d{4}) ([A-Z])(\d+)(?:-([A-Z]))?/);
  if (comet) {
    const [, type, y, half, order, frag] = comet;
    return '    ' + type + packYear(+y) + half + packCycle(+order) + (frag ? frag.toLowerCase() : '0');
  }
  const prov = s.match(/^(\d{4}) ([A-Z])([A-Z])(\d*)/);
  if (prov) {
    const [, y, half, second, cyc] = prov;
    return '     ' + packYear(+y) + half + packCycle(cyc ? +cyc : 0) + second;
  }
  return s.slice(0, 12).padEnd(12);
}

function sexa(v: number, hours: boolean): string {
  // work in integer units (0.001 s of time, or 0.01 arcsec) so rounding never gives 60
  const unit = hours ? 1000 : 100;
  let t = Math.round((Math.abs(v) / (hours ? 15 : 1)) * 3600 * unit);
  const d = Math.floor(t / (3600 * unit));
  t -= d * 3600 * unit;
  const m = Math.floor(t / (60 * unit));
  t -= m * 60 * unit;
  const sec = (t / unit).toFixed(hours ? 3 : 2).padStart(hours ? 6 : 5, '0');
  const head = `${String(d).padStart(2, '0')} ${String(m).padStart(2, '0')} ${sec}`;
  return hours ? head : (v < 0 ? '-' : '+') + head;
}

/** Date "YYYY MM DD.dddddd" (UTC) from MJD. */
export function mpcDate(mjd: number): string {
  const ms = (mjd - 40587) * 86400000;
  const d = new Date(ms);
  const dayFrac = (ms - Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate())) / 86400000;
  return `${d.getUTCFullYear()} ${String(d.getUTCMonth() + 1).padStart(2, '0')} ${(d.getUTCDate() + dayFrac).toFixed(6).padStart(9, '0')}`;
}

export interface MpcObs {
  name: string;
  mjd: number;
  ra: number; // deg
  dec: number; // deg
  mag?: number | null;
  band?: string;
  code?: string; // observatory code
  note2?: string; // 'C' CCD, 'S' space-based
}

/** One 80-character line. */
export function mpcLine(o: MpcObs): string {
  const mag = o.mag != null && Number.isFinite(o.mag) ? o.mag.toFixed(1).padStart(5) : '     ';
  const line =
    packDesignation(o.name) + // 1-12
    ' ' + // 13 discovery asterisk
    ' ' + // 14 note 1
    (o.note2 ?? 'C') + // 15 note 2
    mpcDate(o.mjd) + // 16-32
    sexa(o.ra, true) + // 33-44
    sexa(o.dec, false) + // 45-56
    ' '.repeat(9) + // 57-65
    mag + // 66-70
    (o.band ?? ' ') + // 71
    ' '.repeat(6) + // 72-77
    (o.code ?? 'XXX').padEnd(3).slice(0, 3); // 78-80
  return line;
}
