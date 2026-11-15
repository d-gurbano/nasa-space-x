// Photo card that slides in with a flash: the real SPHEREx image and a small mono caption.
import type { FlashEvent, IndexObject, ObjectPage } from '../lib/types';
import { plainDate } from '../lib/time';
import { el, esc, fixPlural, plural, provenance } from './dom';
import { beforeWhat, daysBefore, isKnown, knownSince } from '../lib/rank';

export function mountPhotoCard(root: HTMLElement, opts: {
  sample: boolean;
  objectOf: (slug: string) => IndexObject | undefined;
  photoUrl: (f: FlashEvent) => string;
  page: (slug: string) => Promise<ObjectPage>;
  onOpen: (slug: string) => void;
  onHide?: () => void;
}) {
  const card = el('aside', { class: 'photocard', 'aria-live': 'polite', 'aria-label': 'SPHEREx photo' });
  card.hidden = true;
  root.appendChild(card);
  let timer = 0;
  let hover = false;
  card.addEventListener('pointerenter', () => (hover = true));
  card.addEventListener('pointerleave', () => {
    hover = false;
    schedule();
  });
  const hide = () => {
    card.classList.remove('pc-in');
    document.body.classList.remove('card-open');
    opts.onHide?.();
    setTimeout(() => !card.classList.contains('pc-in') && (card.hidden = true), 300);
  };
  const schedule = () => {
    clearTimeout(timer);
    timer = window.setTimeout(() => !hover && hide(), 9000);
  };

  async function show(f: FlashEvent) {
    const o = opts.objectOf(f.slug);
    const name = o?.name ?? f.slug;
    // whole days between this photo and the moment anyone had the object; a photo the engine
    // marks as taken after the first known observation is an extra position, not a find before it
    const days = o && f.before_first_known_obs !== false && knownSince(o) > f.mjd ? Math.floor(knownSince(o) - f.mjd) : null;
    const before = o ? `before ${beforeWhat(o)}` : '';
    // the card shows the photo at the time bar's date; the object's earliest photo can be older
    const earliest = o ? Math.round(daysBefore(o) ?? 0) : 0;
    const guessDay = /\/days\//.test(f.photo);
    card.innerHTML = `
      <div class="pc-head">
        <span class="pc-kicker mono">${o && isKnown(o) ? 'SPHEREx photo' : o?.verdict === 'FOUND' ? 'SPHEREx saw it' : 'SPHEREx may have seen it'}</span>
        <button class="pc-close icon-btn" aria-label="Close photo">&times;</button>
      </div>
      <div class="pc-img"><img alt="SPHEREx photo of ${esc(name)} on ${esc(plainDate(f.iso))}" src="${esc(opts.photoUrl(f))}"><span class="pc-cross" aria-hidden="true"></span></div>
      <h3 class="pc-name">${esc(name)}</h3>
      <dl class="pc-meta mono">
        <div><dt>Date</dt><dd>${esc(plainDate(f.iso))}</dd></div>
        <div><dt>Photo</dt><dd class="pc-kind">${guessDay ? 'One day, stacked' : 'Single photo'}</dd></div>
        <div><dt>Wavelength</dt><dd class="pc-wl">...</dd></div>
        <div><dt>S/N</dt><dd class="pc-snr">${f.snr != null ? f.snr.toFixed(1) : '...'}</dd></div>
        ${o && isKnown(o)
          ? `<div><dt>Note</dt><dd>Known object - shows what SPHEREx sees</dd></div>`
          : days !== null && days >= 0
            ? `<div class="pc-gold"><dt>This photo</dt><dd>${days > 0 ? plural(days, 'day') : 'hours'} ${esc(before)}</dd></div>${earliest > days ? `<div><dt>Earliest</dt><dd>${plural(earliest, 'day')}</dd></div>` : ''}`
            : `<div><dt>Note</dt><dd>${esc(fixPlural(f.label))}</dd></div>`}
      </dl>
      <div class="pc-foot">${provenance(opts.sample, 'NASA SPHEREx')}<button class="pc-open chip chip-gold">Open ${esc(name)}</button></div>`;
    card.hidden = false;
    document.body.classList.add('card-open');
    void card.offsetWidth;
    card.classList.add('pc-in');
    (card.querySelector('.pc-close') as HTMLButtonElement).onclick = hide;
    (card.querySelector('.pc-open') as HTMLButtonElement).onclick = () => {
      hide();
      opts.onOpen(f.slug);
    };
    schedule();
    const set = (sel: string, t: string) => ((card.querySelector(sel) as HTMLElement).textContent = t);
    try {
      const p = await opts.page(f.slug);
      const tail = f.photo.split('/').slice(-2).join('/');
      const frame = p.spherex.frames.find((x) => x.png === tail);
      const day = p.spherex.days.find((x) => x.png === tail);
      const wl = (list: number[]) => (list.length ? (Math.min(...list) === Math.max(...list) ? `${list[0].toFixed(2)} µm` : `${Math.min(...list).toFixed(2)} to ${Math.max(...list).toFixed(2)} µm`) : 'n/a');
      if (frame) {
        set('.pc-kind', 'Single photo');
        set('.pc-wl', wl([frame.wavelength_um]));
        if (f.snr == null) set('.pc-snr', frame.snr != null ? frame.snr.toFixed(1) : 'n/a');
      } else if (day || guessDay) {
        const n = day?.n_frames;
        set('.pc-kind', n ? `${plural(n, 'photo')} from one day, stacked` : 'One day, stacked');
        const sameDay = p.spherex.frames.filter((x) => x.iso.slice(0, 10) === (day?.iso ?? f.iso).slice(0, 10)).map((x) => x.wavelength_um);
        set('.pc-wl', wl(sameDay));
        if (f.snr == null) set('.pc-snr', day?.snr != null ? day.snr.toFixed(1) : 'n/a');
      } else {
        set('.pc-kind', 'All photos, stacked');
        set('.pc-wl', wl(p.spherex.frames.map((x) => x.wavelength_um)));
        if (f.snr == null) set('.pc-snr', p.spherex.stack.snr != null ? p.spherex.stack.snr.toFixed(1) : 'n/a');
      }
    } catch {
      set('.pc-wl', 'n/a');
      if (f.snr == null) set('.pc-snr', 'n/a');
    }
  }
  return { show, hide };
}
