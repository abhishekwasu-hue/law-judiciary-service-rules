// pdf.js loaded lazily (large). Worker file is bundled by Vite (?url).
import type { PDFDocumentProxy } from 'pdfjs-dist';

let lib: Promise<typeof import('pdfjs-dist')> | null = null;
export function pdfjs() {
  if (!lib) {
    lib = import.meta.env.VITE_BACKEND === 'artifact'
      ? import('pdfjs-dist').then(async m => {
          // artifact page: one inlined bundle; the worker comes from the pinned CDN copy of the same pdf.js version
          const src = `https://cdn.jsdelivr.net/npm/pdfjs-dist@${m.version}/build/pdf.worker.min.mjs`;
          try {
            const code = await (await fetch(src)).text();
            m.GlobalWorkerOptions.workerPort = new Worker(URL.createObjectURL(new Blob([code], { type: 'text/javascript' })), { type: 'module' });
          } catch {
            m.GlobalWorkerOptions.workerSrc = src;
          }
          return m;
        })
      : Promise.all([import('pdfjs-dist'), import('pdfjs-dist/build/pdf.worker.min.mjs?url')]).then(([m, w]) => {
          m.GlobalWorkerOptions.workerSrc = w.default;
          return m;
        });
    // do not cache a failed import (e.g. old file names after a redeploy) — the next call retries
    lib.catch(() => { lib = null; });
  }
  return lib;
}

// P7: one pdf.js worker for the whole app, started early (warmPdf / preparePdf) so the PDF does not wait for the 1.4 MB worker
// file: pdf.js starts its own download of a URL only after its worker is up, so the file is fetched by us, in parallel.
// Measured (mock, Fast 3G, 4x CPU, 1.1 MB package): URL + Range loading 21.7 s, bytes after worker 17.4 s, bytes in parallel
// with the worker: see docs/AUDIT_2026-11-05.md. A document's destroy() does not end a worker passed in like this.
let worker: Promise<import('pdfjs-dist').PDFWorker | undefined> | null = null;
function sharedWorker() {
  if (!worker) {
    worker = pdfjs().then(m => {
      try {
        return new m.PDFWorker();
      } catch {
        return undefined; // pdf.js then makes its own worker per document, as before
      }
    });
    worker.catch(() => { worker = null; });
  }
  return worker;
}
/** Case page opened: load pdf.js and start its worker when the browser is idle (no visible cost). */
export function warmPdf() {
  const w = window as Window & { requestIdleCallback?: (cb: () => void, o?: { timeout: number }) => number };
  const go = () => void sharedWorker().catch(() => undefined);
  if (w.requestIdleCallback) w.requestIdleCallback(go, { timeout: 5000 });
  else setTimeout(go, 2000);
}

export async function openPdf(data: ArrayBuffer): Promise<PDFDocumentProxy> {
  const [m, w] = await Promise.all([pdfjs(), sharedWorker()]);
  return m.getDocument({ data: new Uint8Array(data), worker: w }).promise;
}

/** P7: start pdf.js + its worker now (the PDF tab calls this before it downloads the file, so both load at the same time). */
export const preparePdf = () => sharedWorker().then(() => undefined);

/** Subject line from page 1's text layer ("विषय :- …"), if the PDF has one. Scanned PDFs return ''. */
export async function guessSubject(file: File): Promise<string> {
  try {
    const doc = await openPdf(await file.arrayBuffer());
    const page = await doc.getPage(1);
    const tc = await page.getTextContent();
    const text = tc.items.map(i => ('str' in i ? i.str : '')).join(' ').replace(/\s+/g, ' ');
    await doc.destroy();
    const m = text.match(/विषय\s*[:：\-–]*\s*[-:]*\s*(.{5,220}?)(?:संदर्भ|महोदय|$)/);
    return m ? m[1].trim() : '';
  } catch {
    return '';
  }
}
