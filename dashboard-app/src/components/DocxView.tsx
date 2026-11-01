import { useEffect, useRef, useState } from 'react';
import { fileBytes } from '../lib/api';
import { Skeleton } from './ui';

let lib: Promise<typeof import('docx-preview')> | null = null;
export const docxLib = () => (lib ||= import('docx-preview'));

/** Read-only DOCX preview (docx-preview). The stored file itself is never changed. */
export default function DocxView({ fileId }: { fileId: number }) {
  const host = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<'load' | 'ok' | 'err'>('load');
  const [err, setErr] = useState('');

  useEffect(() => {
    let alive = true;
    setState('load');
    (async () => {
      try {
        const [{ data }, m] = await Promise.all([fileBytes(fileId), docxLib()]);
        if (!alive || !host.current) return;
        host.current.replaceChildren();
        await m.renderAsync(data, host.current, undefined, { className: 'docx', inWrapper: true, breakPages: true, ignoreLastRenderedPageBreak: true, experimental: false, useBase64URL: true });
        if (alive) setState('ok');
      } catch (e) {
        if (alive) {
          setErr(e instanceof Error ? e.message : String(e));
          setState('err');
        }
      }
    })();
    return () => {
      alive = false;
    };
  }, [fileId]);

  return (
    <div>
      {state === 'load' && <div className="space-y-2"><Skeleton className="h-6 w-1/3" /><Skeleton className="h-[50vh] w-full" /></div>}
      {state === 'err' && <div className="rounded-lg bg-red-100 p-3 text-red-900 dark:bg-red-900/40 dark:text-red-100">पूर्वावलोकन होऊ शकले नाही: {err}</div>}
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
