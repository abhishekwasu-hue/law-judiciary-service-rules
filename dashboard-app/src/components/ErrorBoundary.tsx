import { Component, type ReactNode } from 'react';
import { viewerOwner } from '../lib/format';

// ---- Stale chunks after a redeploy ("link not working"): old index.html asks for page files that no longer exist. ----
// One automatic reload fetches the new build. The guard is keyed by the current build's entry script, so a new
// deploy can reload once again, but the same build can never loop.
const buildKey = () => {
  try {
    const s = document.querySelector<HTMLScriptElement>('script[type="module"][src]');
    return 'chunk-reload:' + (s?.src || location.pathname);
  } catch {
    return 'chunk-reload';
  }
};

export const isChunkError = (e: unknown) =>
  /Failed to fetch dynamically imported module|error loading dynamically imported module|Importing a module script failed|ChunkLoadError|Loading chunk [\w-]+ failed|Unable to preload CSS|text\/html.*MIME|is not a valid JavaScript MIME type/i.test(
    e instanceof Error ? `${e.name} ${e.message}` : String(e),
  );

/** Reloads the page once per build. Returns false if this build already reloaded (then show the error instead). */
export function reloadOnceForNewBuild(): boolean {
  const k = buildKey();
  try {
    if (sessionStorage.getItem(k)) return false;
    sessionStorage.setItem(k, String(Date.now()));
  } catch {
    return false; // no storage → cannot guard against a loop → do not auto-reload
  }
  location.reload();
  return true;
}

/** Keeps the app usable when one page crashes. The technical details (stack) only for the owner (UI audit X2). */
export default class ErrorBoundary extends Component<{ children: ReactNode; resetKey?: string }, { err: Error | null; reloading: boolean }> {
  state = { err: null as Error | null, reloading: false };
  static getDerivedStateFromError(err: Error) {
    return { err };
  }
  componentDidCatch(err: Error) {
    if (isChunkError(err) && reloadOnceForNewBuild()) this.setState({ reloading: true });
  }
  componentDidUpdate(prev: { resetKey?: string }) {
    if (prev.resetKey !== this.props.resetKey && this.state.err) this.setState({ err: null, reloading: false });
  }
  render() {
    if (!this.state.err) return this.props.children;
    if (this.state.reloading || isChunkError(this.state.err))
      return (
        <div className="card space-y-3 p-5" role="status">
          <div className="text-lg font-bold">नवीन आवृत्ती उपलब्ध झाली आहे — पान पुन्हा उघडत आहे.</div>
          <button className="btn-primary min-h-tap" onClick={() => location.reload()}>पान पुन्हा उघडा</button>
        </div>
      );
    return (
      <div className="card space-y-3 p-5" role="alert">
        <div className="text-lg font-bold text-red-700 dark:text-red-300">हे पान उघडताना त्रुटी आली</div>
        <p>इतर पाने नेहमीप्रमाणे उपलब्ध आहेत. कृपया यादीतून दुसरे पान उघडावे किंवा खालील बटणाने हे पान पुन्हा उघडावे. अडचण राहिल्यास कृपया मालकांना कळवावे, ही विनंती.</p>
        {viewerOwner() && (
        <details>
          <summary className="cursor-pointer text-sm text-slate-500">तांत्रिक तपशील</summary>
          <pre className="mt-2 overflow-x-auto whitespace-pre-wrap rounded-lg bg-slate-100 p-3 text-xs dark:bg-navy-800">{String(this.state.err.stack || this.state.err.message).slice(0, 1500)}</pre>
        </details>
        )}
        <button className="btn-primary min-h-tap" onClick={() => location.reload()}>पान पुन्हा उघडा</button>
      </div>
    );
  }
}
