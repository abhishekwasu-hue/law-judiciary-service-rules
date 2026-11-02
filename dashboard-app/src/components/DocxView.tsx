import { useEffect, useRef, useState } from 'react';
import { fileBytes, humanError } from '../lib/api';
import { Skeleton } from './ui';
import { isChunkError, reloadOnceForNewBuild } from './ErrorBoundary';

let lib: Promise<typeof import('docx-preview')> | null = null;
// a failed import is not cached (the next attempt may succeed)
export const docxLib = () => (lib ||= import('docx-preview').catch(e => { lib = null; throw e; }));

const NARROW = 768;
const NEW_BUILD_MSG = 'app ची नवीन आवृत्ती आली आहे — पान रीलोड करत आहे';
/** Marathi text for a load/render error; raw library (English) messages are not shown.
 *  An old tab after a redeploy cannot load the library chunk → reload once for the new build. */
function errText(e: unknown): string {
  if (isChunkError(e) && reloadOnceForNewBuild()) return NEW_BUILD_MSG;
  const h = humanError(e);
  return /[ऀ-ॿ]/.test(h) ? h : 'फाइल उघडता आली नाही — पुन्हा लोड करा किंवा डाउनलोड करून पाहा.';
}

const BAD_URL = /^\s*(javascript|data|vbscript):/i;
const URL_ATTRS = ['href', 'xlink:href', 'src', 'action', 'formaction', 'srcdoc'];
/** A crafted DOCX must not run code in the app: drop active elements, on* handlers and javascript:/data: links.
 *  Images keep their data: src (docx-preview embeds pictures as base64 data URLs). */
export function sanitizeDocx(root: HTMLElement) {
  root.querySelectorAll('script, iframe, frame, object, embed, base, meta, link, form, input, button, textarea, select').forEach(el => el.remove());
  root.querySelectorAll('*').forEach(el => {
    for (const a of Array.from(el.attributes)) {
      const name = a.name.toLowerCase();
      if (name.startsWith('on')) el.removeAttribute(a.name);
      else if (URL_ATTRS.includes(name) && BAD_URL.test(a.value)) {
        // pictures: <img src> and VML-as-SVG <image href> carry data:image/… (not executable there)
        const pic = (name === 'src' && el.tagName === 'IMG') || (name !== 'src' && el.tagName.toLowerCase() === 'image');
        const imgData = pic && /^\s*data:image\//i.test(a.value);
        if (!imgData) el.removeAttribute(a.name);
      }
    }
    if (el.tagName === 'A') {
      el.setAttribute('rel', 'noopener noreferrer');
      el.setAttribute('target', '_blank');
    }
  });
}

/** Read-only DOCX preview (docx-preview). The stored file itself is never changed. */
export default function DocxView({ fileId }: { fileId: number }) {
  const host = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<'load' | 'ok' | 'err'>('load');
  const [err, setErr] = useState('');
  const [scaled, setScaled] = useState(false);

  useEffect(() => {
    let alive = true;
    setState('load');
    (async () => {
      try {
        const [{ data }, m] = await Promise.all([fileBytes(fileId), docxLib()]);
        if (!alive || !host.current) return;
        // render off-document, clean, then attach (nothing from the file reaches the page unchecked)
        const tmp = document.createElement('div');
        await m.renderAsync(data, tmp, undefined, { className: 'docx', inWrapper: true, breakPages: true, ignoreLastRenderedPageBreak: true, experimental: false, useBase64URL: true });
        sanitizeDocx(tmp);
        if (!alive || !host.current) return;
        host.current.replaceChildren(...Array.from(tmp.childNodes));
        setState('ok');
      } catch (e) {
        if (alive) {
          setErr(errText(e));
          setState('err');
        }
      }
    })();
    return () => {
      alive = false;
    };
  }, [fileId]);

  // Narrow screens (< 768 px): zoom the A4 pages down to the available width.
  // CSS `zoom` (unlike transform) also shrinks the layout box, so the scroll height stays correct.
  useEffect(() => {
    const el = host.current;
    if (state !== 'ok' || !el) return;
    const wrap = el.querySelector<HTMLElement>('.docx-wrapper');
    if (!wrap) return;
    const fit = () => {
      wrap.style.zoom = '';
      if (window.innerWidth >= NARROW) return setScaled(false);
      const page = wrap.querySelector<HTMLElement>('section.docx');
      const natural = (page?.offsetWidth || wrap.scrollWidth) + 16;
      const z = Math.min(1, (el.clientWidth - 4) / natural);
      if (z < 0.99) wrap.style.zoom = String(z);
      setScaled(z < 0.99);
    };
    fit();
    const ro = new ResizeObserver(fit);
    ro.observe(el);
    return () => {
      ro.disconnect();
      wrap.style.zoom = '';
    };
  }, [state]);

  return (
    <div>
      {state === 'load' && <div className="space-y-2"><Skeleton className="h-6 w-1/3" /><Skeleton className="h-[50vh] w-full" /></div>}
      {state === 'err' && <div className="rounded-lg bg-red-100 p-3 text-red-900 dark:bg-red-900/40 dark:text-red-100" role="alert">{err === NEW_BUILD_MSG ? err : `पूर्वावलोकन होऊ शकले नाही: ${err}`}</div>}
      {state === 'ok' && scaled && <p className="mb-1 text-sm font-semibold text-slate-600 dark:text-slate-300">लहान पडद्यासाठी पान लहान दाखवले आहे — पूर्ण वाचनासाठी डाउनलोड करा.</p>}
      <div ref={host} className="docx-host max-h-[75vh] overflow-auto rounded-lg bg-slate-200 dark:bg-navy-950" hidden={state !== 'ok'} />
      {state === 'ok' && <p className="mt-1 text-xs text-slate-500">पूर्वावलोकनात DVOT-SurekhMR फॉन्ट नसल्यास दुसरा फॉन्ट दिसतो; डाउनलोड फाइल मूळ आहे.</p>}
    </div>
  );
}

/** Paragraph texts of a DOCX (for the version diff). */
export async function docxParagraphs(fileId: number): Promise<string[]> {
  const [{ data }, m] = await Promise.all([fileBytes(fileId), docxLib()]);
  const div = document.createElement('div');
  await m.renderAsync(data, div, undefined, { inWrapper: false, breakPages: false });
  return Array.from(div.querySelectorAll('p'))
    .map(p => (p.textContent || '').replace(/\s+/g, ' ').trim())
    .filter(Boolean);
}
