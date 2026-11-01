import { Component, type ReactNode } from 'react';

/** Keeps the app usable when one page crashes and shows the error text (so Abhi can send a screenshot). */
export default class ErrorBoundary extends Component<{ children: ReactNode; resetKey?: string }, { err: Error | null }> {
  state = { err: null as Error | null };
  static getDerivedStateFromError(err: Error) {
    return { err };
  }
  componentDidUpdate(prev: { resetKey?: string }) {
    if (prev.resetKey !== this.props.resetKey && this.state.err) this.setState({ err: null });
  }
  render() {
    if (!this.state.err) return this.props.children;
    return (
      <div className="card space-y-3 p-5" role="alert">
        <div className="text-lg font-bold text-red-700 dark:text-red-300">हे पान उघडताना त्रुटी आली</div>
        <p>उरलेले app चालू आहे — डावीकडून दुसरे पान उघडा. या संदेशाचा screenshot पाठवा.</p>
        <pre className="overflow-x-auto whitespace-pre-wrap rounded-lg bg-slate-100 p-3 text-xs dark:bg-navy-800">{String(this.state.err.stack || this.state.err.message).slice(0, 1500)}</pre>
        <button className="btn-ghost" onClick={() => this.setState({ err: null })}>पुन्हा प्रयत्न करा</button>
      </div>
    );
  }
}
