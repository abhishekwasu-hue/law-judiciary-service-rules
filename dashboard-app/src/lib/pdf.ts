// pdf.js loaded lazily (large). Worker file is bundled by Vite (?url).
import type { PDFDocumentProxy } from 'pdfjs-dist';

let lib: Promise<typeof import('pdfjs-dist')> | null = null;
export function pdfjs() {
  if (!lib) {
    lib = Promise.all([import('pdfjs-dist'), import('pdfjs-dist/build/pdf.worker.min.mjs?url')]).then(([m, w]) => {
      m.GlobalWorkerOptions.workerSrc = w.default;
      return m;
    });
  }
  return lib;
}

export async function openPdf(data: ArrayBuffer): Promise<PDFDocumentProxy> {
  const m = await pdfjs();
  return m.getDocument({ data: new Uint8Array(data) }).promise;
}

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
