import { useCallback, useEffect, useRef, useState } from 'react';
import type { PDFDocumentProxy, PDFPageProxy } from 'pdfjs-dist';
import { fileBytes, humanError } from '../lib/api';
import { openPdf } from '../lib/pdf';
import { Skeleton } from './ui';
import { isChunkError, reloadOnceForNewBuild } from './ErrorBoundary';

const NEW_BUILD_MSG = 'app ची नवीन आवृत्ती आली आहे — पान रीलोड करत आहे';

interface OutlineNode { title: string; page: number | null; items: OutlineNode[] }

async function resolveOutline(doc: PDFDocumentProxy): Promise<OutlineNode[]> {
  const raw = (await doc.getOutline()) || [];
  const walk = async (items: typeof raw): Promise<OutlineNode[]> =>
    Promise.all(
      items.map(async it => {
        let page: number | null = null;
        try {
          const dest = typeof it.dest === 'string' ? await doc.getDestination(it.dest) : it.dest;
          if (Array.isArray(dest) && dest[0]) page = typeof dest[0] === 'number' ? dest[0] + 1 : (await doc.getPageIndex(dest[0])) + 1;
        } catch {
          page = null;
        }
        return { title: it.title, page, items: await walk(it.items || []) };
      }),
    );
  return walk(raw);
}

/** Render a page when it is within NEAR px of the scroller view; free its canvas when it is beyond FAR px (long packages on phones). */
const NEAR = '600px';
const FAR = '2400px';

function Page({ doc, n, width, root }: { doc: PDFDocumentProxy; n: number; width: number; root: HTMLElement | null }) {
  const holder = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const pageRef = useRef<PDFPageProxy | null>(null);
  const [visible, setVisible] = useState(false);
  const [ratio, setRatio] = useState(1.414);

  useEffect(() => {
    const el = holder.current;
    if (!el) return;
    const near = new IntersectionObserver(es => es.some(e => e.isIntersecting) && setVisible(true), { root, rootMargin: NEAR });
    const far = new IntersectionObserver(es => es.every(e => !e.isIntersecting) && setVisible(false), { root, rootMargin: FAR });
    near.observe(el);
    far.observe(el);
    return () => {
      near.disconnect();
      far.disconnect();
    };
  }, [root]);

  useEffect(() => {
    if (!visible || !width) return;
    let cancelled = false;
    let task: { cancel: () => void; promise: Promise<unknown> } | null = null;
    (async () => {
      const page = await doc.getPage(n);
      if (cancelled) return;
      pageRef.current = page;
      const base = page.getViewport({ scale: 1 });
      setRatio(base.height / base.width);
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const vp = page.getViewport({ scale: (width / base.width) * dpr });
      const c = canvas.current;
      if (!c || cancelled) return;
      c.width = vp.width;
      c.height = vp.height;
      // Default annotation mode draws existing annotations (the yellow highlights) onto the canvas.
      task = page.render({ canvasContext: c.getContext('2d')!, viewport: vp });
      await task.promise.catch(() => {});
    })().catch(() => undefined);
    return () => {
      cancelled = true;
      task?.cancel();
    };
  }, [visible, width, doc, n]);

  // far off-screen: drop the bitmap (width/height 0 frees canvas memory) and the page's cached data
  useEffect(() => {
    if (visible) return;
    const c = canvas.current;
    if (c && c.width) {
      c.width = 0;
      c.height = 0;
    }
    pageRef.current?.cleanup();
    pageRef.current = null;
  }, [visible]);

  return (
    <div ref={holder} data-page={n} className="relative mx-auto bg-white shadow" style={{ width, height: width * ratio }}>
      <canvas ref={canvas} style={{ width: '100%', height: '100%' }} aria-label={`पृष्ठ ${n}`} />
      <span className="absolute right-1 top-1 rounded bg-black/60 px-1.5 text-xs text-white">{n}</span>
    </div>
  );
}

function Outline({ nodes, go, depth = 0 }: { nodes: OutlineNode[]; go: (p: number) => void; depth?: number }) {
  return (
    <ul className={depth ? 'ml-3 border-l border-slate-200 pl-2 dark:border-navy-700' : ''}>
      {nodes.map((o, i) => (
        <li key={i}>
          <button className="min-h-tap w-full rounded px-2 py-1 text-left text-sm hover:bg-slate-100 disabled:opacity-50 dark:hover:bg-navy-800" disabled={!o.page} onClick={() => o.page && go(o.page)}>
            {o.title} {o.page && <span className="text-slate-500">• पृ. {o.page}</span>}
          </button>
          {o.items.length > 0 && <Outline nodes={o.items} go={go} depth={depth + 1} />}
        </li>
      ))}
    </ul>
  );
}

export default function PdfViewer({ fileId, url, jumpTo }: { fileId?: number; url?: string; jumpTo?: { page: number; at: number } }) {
  const [doc, setDoc] = useState<PDFDocumentProxy | null>(null);
  const [outline, setOutline] = useState<OutlineNode[]>([]);
  const [err, setErr] = useState('');
  const [width, setWidth] = useState(0);
  // bookmarks panel: closed by default on phones (it covers the page there)
  const [showOutline, setShowOutline] = useState(() => typeof window === 'undefined' || window.innerWidth >= 768);
  const [pageInput, setPageInput] = useState('');
  const scroller = useRef<HTMLDivElement | null>(null);
  const [scrollEl, setScrollEl] = useState<HTMLDivElement | null>(null);
  const setScroller = useCallback((el: HTMLDivElement | null) => {
    scroller.current = el;
    setScrollEl(el);
  }, []);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let alive = true;
    let d: PDFDocumentProxy | null = null;
    setDoc(null);
    setErr('');
    (async () => {
      try {
        const data = fileId != null ? (await fileBytes(fileId)).data : await (await fetch(url!)).arrayBuffer();
        d = await openPdf(data);
        if (!alive) return void d.destroy();
        setDoc(d);
        const o = await resolveOutline(d);
        if (alive) {
          setOutline(o);
          if (!o.length) setShowOutline(false);
        }
      } catch (e) {
        if (alive) {
          // an old tab after a redeploy cannot load the pdf.js chunk → reload once for the new build
          if (isChunkError(e) && reloadOnceForNewBuild()) return setErr(NEW_BUILD_MSG);
          const h = humanError(e);
          setErr(/[ऀ-ॿ]/.test(h) ? h : 'फाइल उघडता आली नाही — पुन्हा लोड करा किंवा डाउनलोड करून पाहा.');
        }
      }
    })();
    return () => {
      alive = false;
      void d?.destroy();
    };
  }, [fileId, url]);

  useEffect(() => {
    const el = scroller.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setWidth(Math.min(el.clientWidth - 16, 1000)));
    ro.observe(el);
    return () => ro.disconnect();
  }, [doc]);

  const go = useCallback((p: number) => {
    const el = scroller.current?.querySelector<HTMLElement>(`[data-page="${p}"]`);
    if (el && scroller.current) scroller.current.scrollTo({ top: el.offsetTop - 8, behavior: 'smooth' });
  }, []);
  useEffect(() => {
    if (!jumpTo || !doc) return;
    // on narrow layouts the viewer may be off-screen (list below it): bring it into view first, then jump
    const root = rootRef.current;
    const r = root?.getBoundingClientRect();
    const off = !!r && (r.top < 0 || r.top > window.innerHeight * 0.5);
    if (off) root!.scrollIntoView({ behavior: 'smooth', block: 'start' });
    const t = setTimeout(() => go(jumpTo.page), off ? 350 : 50);
    return () => clearTimeout(t);
  }, [jumpTo, doc, go]);

  if (err) return <div className="rounded-lg bg-red-100 p-3 text-red-900 dark:bg-red-900/40 dark:text-red-100" role="alert">{err === NEW_BUILD_MSG ? err : `PDF उघडता आला नाही: ${err}`}</div>;
  if (!doc) return <div className="space-y-3"><Skeleton className="h-8 w-1/2" /><Skeleton className="h-[60vh] w-full" /></div>;

  return (
    <div ref={rootRef} className="flex scroll-mt-4 flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        {outline.length > 0 && (
          <button className="btn-ghost" onClick={() => setShowOutline(s => !s)} aria-pressed={showOutline}>☰ खूणपट्ट्या</button>
        )}
        <span className="text-sm text-slate-500">एकूण {doc.numPages} पाने</span>
        <form className="ml-auto flex items-center gap-1" onSubmit={e => { e.preventDefault(); const n = Number(pageInput); if (n >= 1 && n <= doc.numPages) go(n); }}>
          <input className="input w-20" inputMode="numeric" placeholder="पृ." value={pageInput} onChange={e => setPageInput(e.target.value.replace(/\D/g, ''))} aria-label="पृष्ठ क्रमांक" />
          <button className="btn-ghost">जा</button>
        </form>
      </div>
      <div className="flex gap-2">
        {showOutline && outline.length > 0 && (
          <nav className="card max-h-[75vh] w-64 shrink-0 overflow-auto p-2 max-md:fixed max-md:inset-x-3 max-md:bottom-20 max-md:z-40 max-md:max-h-[50vh] max-md:w-auto" aria-label="खूणपट्ट्या">
            <Outline nodes={outline} go={p => { go(p); if (window.innerWidth < 768) setShowOutline(false); }} />
          </nav>
        )}
        <div ref={setScroller} className="relative h-[75vh] min-w-0 flex-1 overflow-auto rounded-lg bg-slate-200 p-2 dark:bg-navy-950">
          <div className="flex flex-col gap-3">
            {width > 0 && Array.from({ length: doc.numPages }, (_, i) => <Page key={i} doc={doc} n={i + 1} width={width} root={scrollEl} />)}
          </div>
        </div>
      </div>
    </div>
  );
}
