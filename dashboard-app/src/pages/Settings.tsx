import { useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { SETTING_LABEL, api, fmtUsd, getSpend, humanError, type Spend } from '../lib/api';
import { useAuth, useCanWrite } from '../lib/auth';
import ProfileForm from '../components/ProfileForm';
import { sb } from '../lib/supabase';
import type { Member } from '../lib/types';
import { fmtDate } from '../lib/format';
import { Chip, Field, Section, SkeletonRows, Spinner } from '../components/ui';
import { useToast } from '../components/Toast';

// providers reachable through the engine's LiteLLM gateway (Worker AI_PROVIDERS); research 02.11.2026
const PROVIDERS: { k: string; name: string; free: string; privacy: string; tone: 'green' | 'amber' | 'red'; models: string }[] = [
  { k: 'gemini', name: 'Google Gemini', free: 'मोफत स्तर आहे', privacy: 'मोफत: Google माहिती वापरते, माणसे वाचू शकतात — गोपनीय नको. सशुल्क: वापर नाही', tone: 'amber', models: 'gemini-3.8-flash, gemini-3.5-flash-lite (2.5 मॉडेल बंद होत आहेत)' },
  { k: 'openai', name: 'OpenAI (ChatGPT)', free: 'मोफत नाही', privacy: 'API माहिती training ला नाही (default)', tone: 'green', models: 'gpt-6.1-sol, gpt-5.4-mini' },
  { k: 'openrouter', name: 'OpenRouter', free: ':free मॉडेल — दिवसाला 50 (credit $10 नंतर 1000) विनंत्या', privacy: 'मोफत मॉडेलचे host माहिती वापरू शकतात — गोपनीय नको', tone: 'red', models: 'google/gemma-4-31b:free, nvidia/nemotron-3.5-super-vl:free' },
  { k: 'groq', name: 'Groq', free: 'मोफत — पण 8K tokens/मिनिट: प्रक्रियेला अपुरे', privacy: 'default: माहिती ठेवत नाही', tone: 'amber', models: 'gpt-oss-120b, qwen3.8-27b' },
  { k: 'mistral', name: 'Mistral', free: 'मोफत स्तर', privacy: 'मोफत: training ला वापरू शकतात (opt-out शक्य)', tone: 'red', models: 'mistral-small-latest' },
  { k: 'cerebras', name: 'Cerebras', free: 'मोफत trial — दिवसाला 10 लाख tokens: प्रक्रियेला अपुरे', privacy: 'अटी तपासलेल्या नाहीत', tone: 'amber', models: 'gpt-oss-120b, qwen-3.8-27b' },
  { k: 'cloudflare', name: 'Cloudflare Workers AI', free: 'मोफत — दिवसाला 10,000 Neurons (भाग 1 साठी)', privacy: 'माहिती training ला वापरत नाही', tone: 'green', models: '@cf/meta/llama-4-scout-17b-16e-instruct, @cf/mistralai/mistral-small-3.1-24b-instruct' },
  { k: 'ollama', name: 'Ollama (स्वतःचा सर्व्हर)', free: 'API खर्च नाही — GPU असलेला संगणक हवा', privacy: 'माहिती कार्यालयातच (":cloud" मॉडेल नको)', tone: 'green', models: 'gemma4:31b, gemma4:12b' },
];
function PROVIDER_CHOICES(first: string): [string, string][] {
  return [['', first], ...PROVIDERS.map(p => [p.k, p.name] as [string, string])];
}
// sec: which Settings section the field sits in (S2). label = Marathi first; the raw key is shown as small grey text (S3).
type Sec = 'cost' | 'tech' | 'ai' | 'alt';
const PLAIN: { k: string; label: string; hint?: string; num?: boolean; max?: number; sec: Sec; ph?: string; choices?: [string, string][] }[] = [
  { k: 'budget_usd', label: 'प्रत्येक प्रस्तावाचा कमाल खर्च ($)', hint: 'ओलांडल्यास फक्त सूचना येते; प्रक्रिया थांबत नाही व दर्जा घटत नाही. रिकामे = 0.75', num: true, max: 20, sec: 'cost', ph: 'उदा. 1.5' },
  { k: 'monthly_budget_usd', label: 'मासिक कमाल खर्च ($)', hint: 'या महिन्याचा (भारतीय वेळ) एकूण कमाल खर्च. ओलांडल्यावर नवीन प्रक्रिया सुरू होत नाही; चालू प्रक्रिया पूर्ण होते. रिकामे = $20', num: true, max: 1000, sec: 'cost', ph: 'रिकामे = $20' },
  { k: 'max_parallel_runs', label: 'एकाच वेळी चालणारे run (1–3)', hint: 'एकाच वेळी जास्तीत जास्त किती प्रस्तावांची प्रक्रिया चालू राहील (वेगवेगळी प्रकरणे; एका प्रकरणाची एकच). इतर प्रस्ताव प्रतीक्षा-यादीत क्रमाने थांबतात. रिकामे = 2', sec: 'cost', choices: [['', 'रिकामे (2)'], ['1', '1 — एकामागून एक'], ['2', '2'], ['3', '3']] },
  { k: 'owner_email', label: 'मालकाचा ई-मेल', hint: 'या ई-मेलने लॉगिन करणाऱ्यास सेटिंग्ज बदलण्याचा अधिकार असतो.', sec: 'tech' },
  { k: 'supabase_url', label: 'माहिती-साठ्याचा पत्ता (Supabase)', hint: 'Supabase प्रकल्पाच्या सेटिंग्जमध्ये मिळतो.', sec: 'tech' },
  { k: 'supabase_anon_key', label: 'माहिती-साठ्याची सार्वजनिक की (Supabase)', hint: 'त्याच ठिकाणची सार्वजनिक (anon) की.', sec: 'tech' },
  { k: 'github_repo', label: 'नियम व साधनांचे भांडार (GitHub)', hint: 'उदा. owner/repo', sec: 'tech' },
  { k: 'github_branch', label: 'भांडाराची शाखा (GitHub)', hint: 'सहसा main', sec: 'tech' },
  { k: 'model', label: 'मुख्य मॉडेल', hint: 'तथ्ये, टिप्पणी व मसुदे (पत्र, शासन निर्णय-प्रारूप).', sec: 'ai', ph: 'उदा. claude-sonnet-…' },
  { k: 'model_review', label: 'अंतिम पडताळणी मॉडेल', hint: 'टिप्पणी, पत्र व ब्रीफिंगची अंतिम तपासणी व मंजुरी. सर्वात सक्षम मॉडेल ठेवावे; रिकामे = डीफॉल्ट', sec: 'ai', ph: 'उदा. claude-opus-…' },
  { k: 'model_light', label: 'स्वस्त मॉडेल', hint: 'अभ्यास-फाइल भाग 1–7, संबंधित माहिती व यांत्रिक काम; रिकामे = डीफॉल्ट', sec: 'ai', ph: 'उदा. claude-haiku-…' },
  { k: 'model_strong', label: 'उच्च-स्तर मॉडेल', hint: 'ऐच्छिक. मुख्य मॉडेलच्या वर एकदिशा उन्नयन (escalation); रिकामे / none = बंद', sec: 'ai', ph: 'रिकामे = बंद' },
  { k: 'model_edit', label: 'सुधारणा-चॅटचे मॉडेल', hint: 'प्रकरणावरील सुधारणा-चॅटसाठी (फक्त claude-… मॉडेल). रिकामे = claude-sonnet-5-5', sec: 'ai', ph: 'claude-sonnet-5-5' },
  { k: 'effort', label: 'विचार-पातळी', hint: 'रिकामे = medium', sec: 'ai', choices: [['', 'रिकामे (medium)'], ['low', 'low'], ['medium', 'medium'], ['high', 'high'], ['xhigh', 'xhigh'], ['max', 'max']] },
  // other AI providers (Abhi 02.11.2026: keys for various models incl. free ones — docs/AI_PROVIDERS_RESEARCH.md)
  { k: 'engine_provider', label: 'मुख्य प्रक्रिया कोणाकडून', hint: 'रिकामे = Claude (वरील मॉडेल). दुसरा AI निवडल्यास संपूर्ण प्रक्रिया त्या AI कडून होते; सर्व तपासण्या लागू; प्रकरणावर सूचना येते.', sec: 'alt', choices: PROVIDER_CHOICES('Claude (डीफॉल्ट)') },
  { k: 'engine_model', label: 'मुख्य — मॉडेल', hint: 'निवडलेल्या AI चे मॉडेल-नाव (तक्ता पाहावा); रिकामे = त्या AI चे डीफॉल्ट', sec: 'alt' },
  { k: 'engine_model_light', label: 'मुख्य — स्वस्त मॉडेल', hint: 'यांत्रिक कामासाठी; रिकामे = डीफॉल्ट', sec: 'alt' },
  { k: 'fallback_provider', label: 'राखीव AI', hint: 'मुख्य AI चे credit / की / सेवा बंद पडल्यास संपूर्ण प्रक्रिया याच्याकडून होते.', sec: 'alt', choices: PROVIDER_CHOICES('नाही (डीफॉल्ट)') },
  { k: 'fallback_model', label: 'राखीव — मॉडेल', hint: 'रिकामे = त्या AI चे डीफॉल्ट', sec: 'alt' },
  { k: 'fallback_model_light', label: 'राखीव — स्वस्त मॉडेल', hint: 'रिकामे = डीफॉल्ट', sec: 'alt' },
  { k: 'part1_provider', label: 'अभ्यास-फाइल भाग 1 कोणाकडून', hint: 'प्रत्येक आकडा / दिनांक / नाव मुख्य मॉडेलच्या वाचनाशी जुळवला जातो; न जुळलेली पाने मुख्य मॉडेल पुन्हा लिहिते.', sec: 'alt', choices: PROVIDER_CHOICES('Claude (डीफॉल्ट)') },
  { k: 'part1_model', label: 'भाग 1 — मॉडेल', hint: 'स्कॅन (चित्र) वाचणारे मॉडेल हवे; रिकामे = डीफॉल्ट', sec: 'alt' },
  { k: 'cloudflare_account_id', label: 'Cloudflare खाते-क्रमांक', hint: 'Cloudflare Workers AI वापरल्यासच (32 अक्षरे).', sec: 'alt' },
  { k: 'ollama_base_url', label: 'Ollama सर्व्हरचा पत्ता', hint: 'कार्यालयाचा स्वतःचा मॉडेल-सर्व्हर, उदा. https://host:11434 (इंटरनेटवरून पोहोचणारा हवा).', sec: 'alt' },
];
const SECRET: { k: string; label: string; hint: string; alt?: boolean }[] = [
  { k: 'supabase_service_key', label: 'माहिती-साठ्याची गुप्त की (Supabase)', hint: 'service_role की' },
  { k: 'github_token', label: 'प्रक्रिया सुरू करण्याची परवानगी-की (GitHub)', hint: 'GitHub token' },
  { k: 'anthropic_api_key', label: 'AI प्रक्रियेची की (Anthropic)', hint: 'Anthropic API की' },
  { k: 'gemini_api_key', label: 'Google Gemini की', hint: 'गोपनीय प्रस्तावांसाठी फक्त सशुल्क (billing चालू) प्रकल्पाची की', alt: true },
  { k: 'openai_api_key', label: 'OpenAI की', hint: 'OpenAI निवडल्यास', alt: true },
  { k: 'openrouter_api_key', label: 'OpenRouter की', hint: 'OpenRouter निवडल्यास; खात्यामध्ये "training करणारे providers" बंद ठेवावेत', alt: true },
  { k: 'groq_api_key', label: 'Groq की', hint: 'Groq निवडल्यास', alt: true },
  { k: 'mistral_api_key', label: 'Mistral की', hint: 'Mistral निवडल्यास', alt: true },
  { k: 'cerebras_api_key', label: 'Cerebras की', hint: 'Cerebras निवडल्यास', alt: true },
  { k: 'cloudflare_api_token', label: 'Cloudflare Workers AI की', hint: 'Workers AI परवानगी असलेला token', alt: true },
  { k: 'ollama_api_key', label: 'Ollama की (ऐच्छिक)', hint: 'सर्व्हरवर की ठेवली असल्यासच', alt: true },
];
const LOCAL_LABEL: Record<string, string> = Object.fromEntries([...PLAIN, ...SECRET].map(f => [f.k, f.label]));
// Same rules as the Worker's Settings PUT (cloudflare/worker.js) — checked here first, field named in Marathi
const MODEL_NAME = /^[A-Za-z0-9][A-Za-z0-9._:@/-]{1,99}$/;
// model_edit: the edit job calls the Anthropic API directly → Claude model ids only (Worker CLAUDE_MODEL)
const CLAUDE_MODEL = /^claude-[A-Za-z0-9][A-Za-z0-9._:@-]{0,92}$/;
const MODEL_KEYS = ['gemini_model', 'part1_model', 'fallback_model', 'fallback_model_light', 'engine_model', 'engine_model_light', 'model_edit'];
const REQUIRED = ['supabase_url', 'supabase_anon_key', 'owner_email'];
const CLEAR = '__clear__'; // Worker: deletes the key
const UNCLEARABLE = ['supabase_service_key'];
export function checkSettings(v: Record<string, string>): string | null {
  const t = (k: string) => (v[k] ?? '').trim();
  const L = (k: string) => LOCAL_LABEL[k] || SETTING_LABEL[k] || k;
  for (const k of REQUIRED) if (k in v && !t(k)) return `${L(k)}: रिकामे ठेवता येत नाही.`;
  if (t('budget_usd') && !(Number(t('budget_usd')) > 0 && Number(t('budget_usd')) <= 20)) return `${L('budget_usd')}: कृपया 0 पेक्षा जास्त व 20 पर्यंतची संख्या नमूद करावी.`;
  if (t('monthly_budget_usd') && !(Number(t('monthly_budget_usd')) > 0 && Number(t('monthly_budget_usd')) <= 1000)) return `${L('monthly_budget_usd')}: कृपया 0 पेक्षा जास्त व 1000 पर्यंतची संख्या नमूद करावी (रिकामे = $20).`;
  if (t('max_parallel_runs') && !/^[1-3]$/.test(t('max_parallel_runs'))) return `${L('max_parallel_runs')}: कृपया 1, 2 किंवा 3 निवडावे (रिकामे = 2).`;
  if (t('cloudflare_account_id') && !/^[0-9a-f]{32}$/.test(t('cloudflare_account_id'))) return `${L('cloudflare_account_id')}: कृपया नेमकी 32 अक्षरे (0-9, a-f) नमूद करावीत.`;
  if (t('ollama_base_url') && !/^https?:\/\/[A-Za-z0-9.-]+(:\d+)?(\/[A-Za-z0-9._~/-]*)?$/.test(t('ollama_base_url'))) return `${L('ollama_base_url')}: कृपया http:// किंवा https:// ने सुरू होणारा पत्ता नमूद करावा (उदा. https://host:11434).`;
  for (const k of MODEL_KEYS) if (t(k) && !MODEL_NAME.test(t(k))) return `${L(k)}: कृपया योग्य मॉडेल-नाव नमूद करावे (अक्षरे, अंक, . _ : @ / - ; जागा नाही).`;
  if (t('model_edit') && !CLAUDE_MODEL.test(t('model_edit'))) return `${L('model_edit')}: कृपया claude- ने सुरू होणारे मॉडेल-नाव नमूद करावे (उदा. claude-sonnet-5-5).`;
  const ms = t('model_strong');
  if (ms && ms.toLowerCase() !== 'none' && !MODEL_NAME.test(ms)) return `${L('model_strong')}: कृपया योग्य मॉडेल-नाव (अक्षरे, अंक, . _ : @ / - ; जागा नाही) किंवा none नमूद करावे.`;
  return null;
}

const ROLE_LABEL: Record<string, string> = { owner: 'मालक', staff: 'कार्यासन कर्मचारी', senior: 'वरिष्ठ (फक्त वाचन)' };

/** Raw setting key as small grey text after the Marathi hint (S3). */
const KeyTag = ({ k }: { k: string }) => <span className="mt-0.5 block break-all font-mono text-xs text-slate-500 dark:text-slate-400">{k}</span>;

/** Collapsible section (S2): summary is a full-width tap target (S7). */
function Fold({ title, sub, children }: { title: string; sub?: string; children: ReactNode }) {
  return (
    <details className="card group min-w-0">
      <summary className="flex min-h-tap cursor-pointer list-none items-center justify-between gap-2 px-4 py-3">
        <span className="min-w-0">
          <span className="block text-base font-bold">{title}</span>
          {sub && <span className="block text-sm text-slate-500 dark:text-slate-400">{sub}</span>}
        </span>
        <span className="shrink-0 text-slate-500 transition group-open:rotate-180" aria-hidden="true">▾</span>
      </summary>
      <div className="min-w-0 space-y-4 border-t border-slate-200 p-4 dark:border-navy-800">{children}</div>
    </details>
  );
}

/** claude.ai artifact build (E-F4): nothing here is set on the page — a short honest card instead of the Worker settings. */
const ARTIFACT = import.meta.env.VITE_BACKEND === 'artifact';

function ArtifactSettings() {
  const canWrite = useCanWrite();
  return (
    <div className="max-w-2xl space-y-5">
      <h1 className="text-2xl font-bold">सेटिंग्ज</h1>
      <Section title="हे पान">
        <ul className="list-disc space-y-1.5 pl-5">
          <li>हे पान क्लॉडच्या संकेतस्थळावर चालते.</li>
          <li>प्रस्तावांचे काम मालकांच्या खात्यातील नियोजित कार्य <b>“प्रस्ताव कक्ष — काम”</b> करते.</li>
          <li>AI की, मॉडेल, मासिक खर्च-मर्यादा, भांडार व माहिती-साठ्याची सेटिंग्ज येथे लागू नाहीत.</li>
          <li>सदस्य पानाच्या <b>“शेअर”</b> पर्यायातून जोडावेत.</li>
        </ul>
      </Section>
      {canWrite && (
        <Section title="माझी माहिती">
          <ProfileForm />
        </Section>
      )}
    </div>
  );
}

export default ARTIFACT ? ArtifactSettings : WorkerSettings;

function WorkerSettings() {
  const { me } = useAuth();
  const toast = useToast();
  const [cur, setCur] = useState<Record<string, string> | null>(null);
  const [edit, setEdit] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [members, setMembers] = useState<Member[] | null>(null);
  const [inv, setInv] = useState({ email: '', role: 'staff' });
  const [invBusy, setInvBusy] = useState(false);
  const [clear, setClear] = useState<Set<string>>(new Set()); // secret keys marked "काढा"
  const [formErr, setFormErr] = useState('');
  const [spend, setSpend] = useState<Spend | null>(null);

  const load = async () => {
    try {
      const s = await api<Record<string, string>>('/api/settings');
      setCur(s);
      setEdit(Object.fromEntries(PLAIN.map(p => [p.k, s[p.k] || ''])));
      setClear(new Set());
    } catch (e) {
      toast(humanError(e), 'err');
    }
    getSpend().then(setSpend, () => setSpend(null));
    const m = await sb().from('members').select('*').order('created_at');
    if (m.error) toast(humanError(m.error.message), 'err');
    setMembers((m.data as Member[]) || []);
  };
  useEffect(() => {
    if (me?.role === 'owner') void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [me?.role]);

  if (me?.role !== 'owner') {
    return (
      <div className="card space-y-3 p-6 text-center">
        <p>ही सेटिंग्ज फक्त मालकासाठी आहेत.</p>
        <Link to="/" className="btn-ghost">मुख्य पृष्ठ</Link>
      </div>
    );
  }

  const plainField = (p: (typeof PLAIN)[number]) => (
    <Field key={p.k} label={p.label} hint={<>{p.hint}<KeyTag k={p.k} /></>}>
      {p.choices ? (
        <select className="input" value={edit[p.k] ?? ''} onChange={e => setEdit(s => ({ ...s, [p.k]: e.target.value }))}>
          {p.choices.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
      ) : <input className="input font-mono" {...(p.num ? { type: 'number', inputMode: 'decimal' as const, min: 0.01, max: p.max, step: 0.01 } : {})} placeholder={p.ph} value={edit[p.k] ?? ''} onChange={e => setEdit(s => ({ ...s, [p.k]: e.target.value }))} />}
    </Field>
  );
  const toggleClear = (k: string) => setClear(x => { const n = new Set(x); if (n.has(k)) n.delete(k); else n.add(k); return n; });
  const secretField = (s: (typeof SECRET)[number]) => {
    const marked = clear.has(s.k);
    return (
      <Field
        key={s.k}
        label={s.label}
        hint={<span className="break-words">{s.hint} • {marked ? <Chip tone="red">जतन केल्यावर की काढली जाईल</Chip> : cur?.[s.k] ? <>सध्या: <span className="break-all font-mono">{cur[s.k]}</span> — बदलायची असल्यासच नवीन की नमूद करावी</> : <Chip tone="amber">भरलेली नाही</Chip>}<KeyTag k={s.k} /></span>}
      >
        <div className="flex min-w-0 gap-2">
          <input className="input min-w-0 flex-1 font-mono" type="password" autoComplete="off" disabled={marked} placeholder={cur?.[s.k] || ''} value={edit[s.k] ?? ''} onChange={e => setEdit(x => ({ ...x, [s.k]: e.target.value }))} />
          {cur?.[s.k] && !UNCLEARABLE.includes(s.k) && (
            <button type="button" className={marked ? 'btn-primary shrink-0 px-3' : 'btn-ghost shrink-0 px-3'} aria-pressed={marked} onClick={() => toggleClear(s.k)} title="ही की सेटिंग्जमधून काढली जाईल">
              {marked ? '↺ ठेवा' : 'की काढा'}
            </button>
          )}
        </div>
      </Field>
    );
  };

  // Plain values are sent as typed; a secret is sent only if a new value was typed (empty = unchanged) or "काढा".
  const changes = (): Record<string, string> => {
    const body: Record<string, string> = {};
    for (const p of PLAIN) if (cur && edit[p.k] !== (cur[p.k] || '')) body[p.k] = edit[p.k] ?? '';
    for (const s of SECRET) if (clear.has(s.k)) body[s.k] = CLEAR; else if (edit[s.k]) body[s.k] = edit[s.k];
    return body;
  };
  const nChanged = cur ? Object.keys(changes()).length : 0;

  async function save() {
    setFormErr('');
    setBusy(true);
    try {
      const body = changes();
      const bad = checkSettings(body);
      if (bad) {
        setFormErr(bad);
        toast(bad, 'err');
        return;
      }
      if (!Object.keys(body).length) {
        toast('कोणताही बदल केलेला नाही.', 'info');
        return;
      }
      await api('/api/settings', { method: 'PUT', body });
      toast('सेटिंग्ज जतन झाली.');
      await load();
    } catch (x) {
      setFormErr(humanError(x));
      toast(humanError(x), 'err');
    } finally {
      setBusy(false);
    }
  }

  async function invite(e: FormEvent) {
    e.preventDefault();
    if (!/^\S+@\S+\.\S+$/.test(inv.email.trim())) return toast('कृपया योग्य ई-मेल नमूद करावा.', 'err');
    setInvBusy(true);
    try {
      const r = await api<{ existing?: boolean }>('/api/members', { body: { email: inv.email.trim(), role: inv.role } });
      toast(r?.existing ? 'सदस्य जोडला आहे. या ई-मेलचे खाते आधीच असल्याने थेट लॉगिन करता येईल.' : 'आमंत्रण पाठविले आहे.');
      setInv({ email: '', role: inv.role });
      await load();
    } catch (x) {
      toast(humanError(x), 'err');
    } finally {
      setInvBusy(false);
    }
  }

  const grid = 'grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3';
  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold">सेटिंग्ज</h1>

      <Section title="खर्च-मर्यादा">
        {!cur ? <SkeletonRows n={2} /> : (
          <div className="space-y-4">
            {spend && (
              <div className="grid grid-cols-3 gap-2 sm:gap-3">
                <div className="rounded-lg bg-slate-50 p-2 dark:bg-navy-800/50 sm:p-3">
                  <div className="text-sm text-slate-500 dark:text-slate-400">या महिन्याचा खर्च</div>
                  <div className={`text-xl font-bold tabular-nums sm:text-2xl ${spend.spent_usd >= spend.limit_usd ? 'text-red-700 dark:text-red-400' : 'text-green-700 dark:text-green-400'}`}>{fmtUsd(spend.spent_usd)}</div>
                </div>
                <div className="rounded-lg bg-slate-50 p-2 dark:bg-navy-800/50 sm:p-3">
                  <div className="text-sm text-slate-500 dark:text-slate-400">मासिक मर्यादा</div>
                  <div className="text-xl font-bold tabular-nums sm:text-2xl">{fmtUsd(spend.limit_usd)}</div>
                </div>
                <div className="rounded-lg bg-slate-50 p-2 dark:bg-navy-800/50 sm:p-3">
                  <div className="text-sm text-slate-500 dark:text-slate-400">प्रक्रिया (या महिन्यात)</div>
                  <div className="text-xl font-bold tabular-nums sm:text-2xl">{spend.runs}</div>
                </div>
              </div>
            )}
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">{PLAIN.filter(p => p.sec === 'cost').map(plainField)}</div>
          </div>
        )}
      </Section>

      <Section title="सदस्य">
        {!members ? (
          <SkeletonRows n={2} />
        ) : (
          <table className="w-full table-fixed">
            <thead>
              <tr className="border-b border-slate-200 dark:border-navy-800"><th className="th">ई-मेल</th><th className="th w-32 sm:w-44">भूमिका</th><th className="th hidden w-32 sm:table-cell">दिनांक</th></tr>
            </thead>
            <tbody>
              {members.map(m => (
                <tr key={m.user_id} className="border-b border-slate-100 align-top dark:border-navy-800/60">
                  <td className="td break-all">{m.email}<span className="block text-sm text-slate-500 dark:text-slate-400 sm:hidden">{fmtDate(m.created_at)}</span></td>
                  <td className="td"><Chip tone={m.role === 'owner' ? 'navy' : m.role === 'staff' ? 'blue' : 'slate'}>{ROLE_LABEL[m.role] || m.role}</Chip></td>
                  <td className="td hidden sm:table-cell">{fmtDate(m.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <form onSubmit={invite} noValidate className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-[1fr_220px_auto] md:items-end">
          <Field label="नवीन सदस्याचा ई-मेल">
            <input className="input" type="email" required value={inv.email} onChange={e => setInv(s => ({ ...s, email: e.target.value }))} />
          </Field>
          <Field label="भूमिका">
            <select className="input" value={inv.role} onChange={e => setInv(s => ({ ...s, role: e.target.value }))}>
              <option value="staff">{ROLE_LABEL.staff}</option>
              <option value="senior">{ROLE_LABEL.senior}</option>
            </select>
          </Field>
          <button className="btn-primary" disabled={invBusy}>{invBusy && <Spinner />} आमंत्रण पाठवा</button>
        </form>
      </Section>

      {!cur ? <div className="card"><SkeletonRows n={3} /></div> : (
        <>
          <Fold title="तांत्रिक जोडण्या" sub="माहिती-साठा, भांडार, की व AI मॉडेल">
            <div className={grid}>{PLAIN.filter(p => p.sec === 'tech').map(plainField)}</div>
            <div className={grid}>{SECRET.filter(s => !s.alt).map(secretField)}</div>
            <h3 className="pt-2 font-bold">AI मॉडेल</h3>
            <p className="text-sm text-slate-600 dark:text-slate-300">स्वस्त मॉडेल: अभ्यास-फाइल भाग 1–7, संबंधित माहिती व यांत्रिक काम. मुख्य मॉडेल: टिप्पणी व मसुदे. पडताळणी मॉडेल: अंतिम तपासणी व मंजुरी. सुधारणा-चॅटचे मॉडेल: प्रकरणावरील सुधारणा (फक्त claude-… मॉडेल).</p>
            <div className={grid}>{PLAIN.filter(p => p.sec === 'ai').map(plainField)}</div>
          </Fold>

          <Fold title="इतर AI" sub="पर्यायी; रिकामे ठेवल्यास सर्व काम Claude करते">
            <ul className="list-disc space-y-1 pl-5 text-sm text-slate-600 dark:text-slate-300">
              <li>दुसरा AI निवडल्यास प्रकरणावर सूचना येते व सर्व तपासण्या (lint, उतारा-तपासणी, अंतिम पडताळणी, verify) तशाच लागू राहतात.</li>
              <li><b className="text-red-700 dark:text-red-400">मोफत मॉडेल:</b> संपूर्ण प्रक्रियेसाठी पुरेसा व गोपनीयता पाळणारा मोफत पर्याय (स्वतःचा Ollama सोडून) सध्या नाही. कृपया तक्ता पाहावा.</li>
            </ul>
            <details className="rounded-lg bg-slate-50 text-sm dark:bg-navy-800/50">
              <summary className="flex min-h-tap cursor-pointer items-center px-3 font-semibold">AI पर्यायांची तुलना (02.11.2026)</summary>
              <div className="overflow-x-auto px-3 pb-3">
                <table className="w-full min-w-[640px]">
                  <thead><tr className="border-b border-slate-200 dark:border-navy-700"><th className="th">AI</th><th className="th">मोफत?</th><th className="th">गोपनीयता</th><th className="th">मॉडेल-नावे (उदा.)</th></tr></thead>
                  <tbody>
                    {PROVIDERS.map(p => (
                      <tr key={p.k} className="border-b border-slate-100 align-top dark:border-navy-800/60">
                        <td className="td font-semibold">{p.name}</td>
                        <td className="td">{p.free}</td>
                        <td className="td"><Chip tone={p.tone}>{p.tone === 'green' ? '✓' : p.tone === 'amber' ? '!' : '✗'}</Chip> {p.privacy}</td>
                        <td className="td break-all font-mono text-xs">{p.models}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
            <div className={grid}>
              {PLAIN.filter(p => p.sec === 'alt').map(plainField)}
              {SECRET.filter(s => s.alt).map(secretField)}
            </div>
          </Fold>

          {/* save bar stays on screen while there are unsaved changes (S2); above the phone bottom nav (57px + safe area) */}
          <div className={nChanged || formErr ? 'sticky bottom-[calc(57px+env(safe-area-inset-bottom))] z-20 md:bottom-0' : ''}>
            <div className="card flex flex-wrap items-center gap-3 px-4 py-3 shadow-lg">
              <button type="button" className="btn-primary" disabled={busy} onClick={() => void save()}>{busy && <Spinner />} जतन करा</button>
              <span className={`text-sm ${nChanged ? 'font-semibold text-amber-800 dark:text-amber-300' : 'text-slate-500 dark:text-slate-400'}`}>
                {nChanged ? `${nChanged} बदल जतन करायचे आहेत` : 'कोणताही बदल नाही'}
              </span>
              {formErr && <div className="w-full break-words rounded-lg border border-red-300 bg-red-50 px-3 py-2 font-semibold text-red-900 dark:border-red-800 dark:bg-red-900/30 dark:text-red-100" role="alert">{formErr}</div>}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
