// The site's terms, defined once. Pages use term() for an inline definition on first use and the
// Methods page lists them all, so a word always means the same thing everywhere.
import { esc } from '../ui/dom';

export interface Term {
  key: string;
  term: string;
  def: string;
}

export const GLOSSARY: Term[] = [
  { key: 'precovery', term: 'Precovery', def: 'A detection of an object in images taken before its first known observation, found after the object was discovered.' },
  { key: 'discovery', term: 'Discovery date', def: 'Date of the discovery observation, from the Minor Planet Center via JPL SBDB.' },
  { key: 'first_obs', term: 'First known observation', def: 'Earliest observation linked to the object in the MPC record. It can be earlier than the discovery date when older observations were linked later.' },
  { key: 'lead', term: 'Lead time', def: 'Days between the earliest SPHEREx detection and the first known observation.' },
  { key: 'stack', term: 'Shift-and-stack', def: 'Image cutouts shifted along the predicted motion and co-added, so a moving source too faint for any single image adds up while noise averages down.' },
  { key: 'snr', term: 'S/N (null-calibrated)', def: 'Stack signal divided by the scatter of identical stacks along offset (null) trajectories. Detection threshold: 5 for the full stack, 2 for a single night.' },
  { key: 'null', term: 'Null trajectory', def: 'A synthetic path offset from the predicted one, stacked the same way. Null stacks measure how often noise alone looks like a detection.' },
  { key: 'injection', term: 'Injection–recovery', def: 'Synthetic point sources planted in the real images at the predicted brightness; the fraction recovered measures completeness at that position.' },
  { key: 'static_sky', term: 'Static-sky subtraction', def: 'Removal of fixed stars and galaxies using other SPHEREx images of the same field taken when the object was elsewhere.' },
  { key: 'sigma3', term: '3σ positional uncertainty', def: 'Largest axis of the 3σ cloud of orbit clones sampled from the fit covariance, propagated to a stated date (gravity only).' },
  { key: 'arc', term: 'Observed arc', def: 'Time span between the first and last observations used in an orbit fit. Short arcs give uncertain orbits.' },
  { key: 'control', term: 'Control object', def: 'A long-known object (e.g. 433 Eros) run through the same pipeline to show what a clear SPHEREx detection looks like. Never counted as a precovery.' },
];

const BY_KEY = new Map(GLOSSARY.map((t) => [t.key, t]));

/** Inline term with its definition as a tooltip (hover or keyboard focus): term('stack') -> shift-and-stack. */
export function term(key: string, text?: string): string {
  const t = BY_KEY.get(key);
  if (!t) return esc(text ?? key);
  return `<dfn class="term" tabindex="0" data-tip="${esc(t.def)}">${esc(text ?? t.term.toLowerCase())}</dfn>`;
}
