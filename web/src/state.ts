// Tiny shared app state with change listeners. No framework.
import { mjdFromIso, todayMjd } from './lib/time';

export const TIME_START = mjdFromIso('2024-01-01');
export const TIME_END = mjdFromIso('2031-01-01');
export const SPEEDS = [1, 7, 30, 90]; // days per second
export const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
export const isPhone = window.matchMedia('(max-width: 720px)').matches || /Mobi|Android/i.test(navigator.userAgent);

type Listener = () => void;

class Store {
  mjd = todayMjd();
  today = todayMjd();
  playing = false;
  speedIndex = 1;
  direction = 1;
  selected: string | null = null;
  private listeners = new Set<Listener>();

  setTime(mjd: number) {
    this.mjd = Math.min(TIME_END, Math.max(TIME_START, mjd));
    if (this.mjd === TIME_END || this.mjd === TIME_START) this.playing = false;
    this.emit();
  }
  setPlaying(p: boolean) {
    this.playing = p;
    this.emit();
  }
  get speed() {
    return SPEEDS[this.speedIndex] * this.direction;
  }
  on(fn: Listener) {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }
  emit() {
    for (const fn of this.listeners) fn();
  }
}

export const store = new Store();
