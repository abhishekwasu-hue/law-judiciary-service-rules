// Cloudflare Worker: serves dashboard (assets) + /api/* proxy to GitHub. Browser never talks to github.com.
// Secrets: GH_TOKEN (fine-grained: Contents R/W, Metadata R), DASH_PASSWORD. Vars: GH_REPO, GH_BRANCH.
const FILES = ['Study.docx', 'Note_and_Letter.docx', 'Proposal_with_GRs.pdf'];
const json = (o, s = 200) => new Response(JSON.stringify(o), { status: s, headers: { 'content-type': 'application/json' } });

async function gh(env, path, opt = {}) {
  return fetch(`https://api.github.com/repos/${env.GH_REPO}${path}`, {
    ...opt,
    headers: { Authorization: `Bearer ${env.GH_TOKEN}`, Accept: 'application/vnd.github+json', 'User-Agent': 'proposal-dashboard', ...(opt.headers || {}) },
  });
}
async function put(env, path, b64, msg) {
  const br = env.GH_BRANCH || 'main';
  let sha;
  const ex = await gh(env, `/contents/${path}?ref=${br}`);
  if (ex.ok) sha = (await ex.json()).sha;
  const r = await gh(env, `/contents/${path}`, { method: 'PUT', body: JSON.stringify({ message: msg, content: b64, branch: br, sha }) });
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    if (!url.pathname.startsWith('/api/')) return env.ASSETS.fetch(req);
    if (!env.DASH_PASSWORD || req.headers.get('x-pass') !== env.DASH_PASSWORD) return json({ error: 'auth' }, 401);
    const br = env.GH_BRANCH || 'main';
    try {
      if (url.pathname === '/api/upload' && req.method === 'POST') {
        const { cr, year, file_no, name, pdf } = await req.json();
        if (!/^\d+$/.test(cr) || !/^\d{4}$/.test(year) || !pdf) return json({ error: 'bad input' }, 400);
        const P = `CR${cr}_${year}`;
        const meta = btoa(unescape(encodeURIComponent(JSON.stringify({ cr, year, file_no: file_no || '', name: name || '' }))));
        await put(env, `inbox/${P}.json`, meta, `meta ${P}`);
        await put(env, `cases/${P}/status.json`, btoa(JSON.stringify({ state: 'queued', queued: new Date().toISOString() })), `queued ${P}`);
        await put(env, `inbox/${P}.pdf`, pdf, `proposal ${P}`);
        return json({ ok: true, prefix: P });
      }
      if (url.pathname === '/api/cases') {
        const r = await gh(env, `/contents/cases?ref=${br}`);
        if (!r.ok) return json([]);
        const dirs = (await r.json()).filter(x => x.type === 'dir').map(x => x.name).sort().reverse();
        const out = [];
        for (const p of dirs) {
          let st = { state: 'queued' };
          const s = await gh(env, `/contents/cases/${p}/status.json?ref=${br}`, { headers: { Accept: 'application/vnd.github.raw+json' } });
          if (s.ok) try { st = await s.json(); } catch (e) {}
          out.push({ p, ...st });
        }
        return json(out);
      }
      if (url.pathname === '/api/file') {
        const p = url.searchParams.get('p'), f = url.searchParams.get('f');
        if (!/^CR\d+_\d{4}$/.test(p || '') || !FILES.includes(f)) return json({ error: 'bad input' }, 400);
        const r = await gh(env, `/contents/cases/${p}/${p}_${f}?ref=${br}`, { headers: { Accept: 'application/vnd.github.raw+json' } });
        if (!r.ok) return json({ error: 'not found' }, 404);
        return new Response(r.body, { headers: { 'content-type': 'application/octet-stream', 'content-disposition': `attachment; filename="${p}_${f}"` } });
      }
      if (url.pathname === '/api/search') {
        const q = (url.searchParams.get('q') || '').slice(0, 100);
        if (!q) return json([]);
        const r = await fetch(`https://api.github.com/search/code?q=${encodeURIComponent(`${q} repo:${env.GH_REPO} path:register`)}&per_page=15`, {
          headers: { Authorization: `Bearer ${env.GH_TOKEN}`, Accept: 'application/vnd.github.text-match+json', 'User-Agent': 'proposal-dashboard' },
        });
        if (!r.ok) return json({ error: r.status }, 502);
        const j = await r.json();
        return json(j.items.map(i => ({ path: i.path, url: i.html_url, frags: (i.text_matches || []).slice(0, 2).map(m => m.fragment) })));
      }
      return json({ error: 'not found' }, 404);
    } catch (e) { return json({ error: String(e.message || e) }, 500); }
  },
};
