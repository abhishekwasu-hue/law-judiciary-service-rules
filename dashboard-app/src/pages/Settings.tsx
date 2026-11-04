import { useEffect, useState, type FormEvent } from 'react';
import { SETTING_LABEL, api, humanError } from '../lib/api';
import { useAuth } from '../lib/auth';
import { sb } from '../lib/supabase';
import type { Member } from '../lib/types';
import { fmtDate } from '../lib/format';
import { Chip, Field, Section, SkeletonRows, Spinner } from '../components/ui';
import { useToast } from '../components/Toast';

// providers reachable through the engine's LiteLLM gateway (Worker AI_PROVIDERS); research 02.11.2026
const PROVIDERS: { k: string; name: string; free: string; privacy: string; tone: 'green' | 'amber' | 'red'; models: string }[] = [
  { k: 'gemini', name: 'Google Gemini', free: 'मोफत स्तर आहे', privacy: 'मोफत: Google माहिती वापरते, माणसे वाचू शकतात — गोपनीय नको. सशुल्क: वापर नाही', tone: 'amber', models: 'gemini-2.5-pro, gemini-2.5-flash' },
  { k: 'openai', name: 'OpenAI (ChatGPT)', free: 'मोफत नाही', privacy: 'API माहिती training ला नाही (default)', tone: 'green', models: 'gpt-6.1-sol, gpt-5.4-mini' },
  { k: 'openrouter', name: 'OpenRouter', free: ':free मॉडेल — दिवसाला 50 (credit $10 नंतर 1000) विनंत्या', privacy: 'मोफत मॉडेलचे host माहिती वापरू शकतात — गोपनीय नको', tone: 'red', models: 'google/gemma-4-31b:free, nvidia/nemotron-3.5-super-vl:free' },
  { k: 'groq', name: 'Groq', free: 'मोफत — पण 8K tokens/मिनिट: अभ्यासाला अपुरे', privacy: 'default: माहिती ठेवत नाही', tone: 'amber', models: 'gpt-oss-120b, qwen3.8-27b' },
  { k: 'mistral', name: 'Mistral', free: 'मोफत स्तर', privacy: 'मोफत: training ला वापरू शकतात (opt-out शक्य)', tone: 'red', models: 'mistral-small-latest' },
  { k: 'cerebras', name: 'Cerebras', free: 'मोफत trial — दिवसाला 10 लाख tokens: अभ्यासाला अपुरे', privacy: 'अटी तपासलेल्या नाहीत', tone: 'amber', models: 'gpt-oss-120b, qwen-3.8-27b' },
  { k: 'cloudflare', name: 'Cloudflare Workers AI', free: 'मोफत — दिवसाला 10,000 Neurons (भाग 1 साठी)', privacy: 'माहिती training ला वापरत नाही', tone: 'green', models: '@cf/meta/llama-4-scout-17b-16e-instruct, @cf/mistralai/mistral-small-3.1-24b-instruct' },
  { k: 'ollama', name: 'Ollama (स्वतःचा सर्व्हर)', free: 'API खर्च नाही — GPU असलेला संगणक हवा', privacy: 'माहिती कार्यालयातच (":cloud" मॉडेल नको)', tone: 'green', models: 'gemma4:31b, gemma4:12b' },
];
function PROVIDER_CHOICES(first: string): [string, string][] {
  return [['', first], ...PROVIDERS.map(p => [p.k, p.name] as [string, string])];
}
const PLAIN: { k: string; label: string; hint?: string; num?: boolean; max?: number; ai?: boolean; alt?: boolean; ph?: string; choices?: [string, string][] }[] = [
  { k: 'owner_email', label: 'मालकाचा ई-मेल', hint: 'या ई-मेलने लॉगिन करणाऱ्याला सेटिंग्ज बदलण्याचा अधिकार' },
  { k: 'supabase_url', label: 'Supabase URL', hint: 'माहिती-साठ्याचा पत्ता — Supabase प्रकल्पाच्या सेटिंग्जमध्ये मिळतो' },
  { k: 'supabase_anon_key', label: 'Supabase anon key', hint: 'त्याच ठिकाणची सार्वजनिक की (anon)' },
  { k: 'github_repo', label: 'GitHub repo', hint: 'नियम व साधने असलेला रेपो — उदा. owner/repo' },
  { k: 'github_branch', label: 'GitHub branch', hint: 'सहसा main' },
  { k: 'model', label: 'मुख्य मॉडेल (model)', hint: 'मसुदा (तथ्ये, टिप्पणी, पत्र, GR) — उदा. claude-sonnet-…', ai: true, ph: 'उदा. claude-sonnet-…' },
  { k: 'model_review', label: 'अंतिम पडताळणी मॉडेल (model_review)', hint: 'टिप्पणी, पत्र व ब्रीफिंगची अंतिम तपासणी व मंजुरी — सर्वात सक्षम मॉडेल ठेवा; रिकामे = डीफॉल्ट', ai: true, ph: 'उदा. claude-opus-…' },
  { k: 'model_light', label: 'स्वस्त मॉडेल (model_light)', hint: 'Study भाग 1–7, संबंधित माहिती व यांत्रिक काम — स्वस्त मॉडेल; रिकामे = डीफॉल्ट', ai: true, ph: 'उदा. claude-haiku-…' },
  { k: 'model_strong', label: 'उच्च-स्तर मॉडेल (model_strong)', hint: 'ऐच्छिक — मुख्य मॉडेलच्या वर एकदिशा उन्नयन (escalation); रिकामे / none = बंद', ai: true, ph: 'रिकामे = बंद' },
  { k: 'effort', label: 'विचार-पातळी (effort)', hint: 'रिकामे = medium', ai: true, choices: [['', 'रिकामे (medium)'], ['low', 'low'], ['medium', 'medium'], ['high', 'high'], ['xhigh', 'xhigh'], ['max', 'max']] },
  { k: 'budget_usd', label: 'कमाल खर्च ($) (budget_usd)', hint: 'प्रत्येक प्रस्तावासाठी अपेक्षित कमाल खर्च ($). ओलांडल्यास फक्त सूचना येते — काम थांबत नाही, दर्जा घटत नाही. रिकामे = 0.75', num: true, max: 20, ai: true, ph: 'उदा. 1.5' },
  // other AI providers (Abhi 02.11.2026: keys for various models incl. free ones — docs/AI_PROVIDERS_RESEARCH.md)
  { k: 'engine_provider', label: 'मुख्य अभ्यास कोणाकडून (engine_provider)', hint: 'रिकामे = Claude (वरील मॉडेल). दुसरा निवडल्यास संपूर्ण अभ्यास त्या AI कडून; सर्व तपासण्या लागू; प्रकरणावर सूचना येते', alt: true, choices: PROVIDER_CHOICES('Claude (डीफॉल्ट)') },
  { k: 'engine_model', label: 'मुख्य — मॉडेल (engine_model)', hint: 'निवडलेल्या AI चे मॉडेल-नाव (खालील तक्ता); रिकामे = त्या AI चे डीफॉल्ट', alt: true },
  { k: 'engine_model_light', label: 'मुख्य — स्वस्त मॉडेल (engine_model_light)', hint: 'यांत्रिक कामासाठी; रिकामे = डीफॉल्ट', alt: true },
  { k: 'fallback_provider', label: 'राखीव AI (fallback_provider)', hint: 'मुख्य AI चे credit/key/सेवा बंद पडल्यास संपूर्ण अभ्यास याच्याकडून', alt: true, choices: PROVIDER_CHOICES('नाही (डीफॉल्ट)') },
  { k: 'fallback_model', label: 'राखीव — मॉडेल (fallback_model)', hint: 'रिकामे = त्या AI चे डीफॉल्ट', alt: true },
  { k: 'fallback_model_light', label: 'राखीव — स्वस्त मॉडेल (fallback_model_light)', hint: 'रिकामे = डीफॉल्ट', alt: true },
  { k: 'part1_provider', label: 'Study भाग 1 कोणाकडून (part1_provider)', hint: 'प्रत्येक आकडा/दिनांक/नाव मुख्य मॉडेलच्या वाचनाशी यंत्राने जुळवला जातो; न जुळलेली पाने मुख्य मॉडेल पुन्हा लिहिते', alt: true, choices: PROVIDER_CHOICES('Claude (डीफॉल्ट)') },
  { k: 'part1_model', label: 'भाग 1 — मॉडेल (part1_model)', hint: 'चित्र (स्कॅन) वाचणारे मॉडेल हवे; रिकामे = डीफॉल्ट', alt: true },
  { k: 'cloudflare_account_id', label: 'Cloudflare account id', hint: 'Cloudflare Workers AI वापरल्यासच (32 अक्षरे)', alt: true },
  { k: 'ollama_base_url', label: 'Ollama पत्ता (ollama_base_url)', hint: 'कार्यालयाचा स्वतःचा मॉडेल-सर्व्हर, उदा. https://host:11434 — इंटरनेटवरून पोहोचणारा हवा', alt: true },
  { k: 'monthly_budget_usd', label: 'मासिक कमाल खर्च ($) (monthly_budget_usd)', hint: 'या महिन्यात (भारतीय वेळ) एकूण कमाल खर्च; ओलांडल्यावर नवीन प्रक्रिया सुरू होत नाही, चालू प्रक्रिया पूर्ण होते. रिकामे = $20', num: true, max: 1000, ai: true, ph: 'रिकामे = $20' },
];
const SECRET: { k: string; label: string; hint: string; alt?: boolean }[] = [
  { k: 'supabase_service_key', label: 'Supabase service_role key', hint: 'माहिती-साठ्याची गुप्त की' },
  { k: 'github_token', label: 'GitHub token', hint: 'प्रक्रिया सुरू करण्यासाठी GitHub ची परवानगी-की' },
  { k: 'anthropic_api_key', label: 'Anthropic API key', hint: 'AI प्रक्रियेसाठीची की' },
  { k: 'gemini_api_key', label: 'Google Gemini API key', hint: 'गोपनीय प्रस्तावांसाठी फक्त सशुल्क (billing चालू) प्रकल्पाची की', alt: true },
  { k: 'openai_api_key', label: 'OpenAI API key', hint: 'OpenAI निवडल्यास', alt: true },
  { k: 'openrouter_api_key', label: 'OpenRouter API key', hint: 'OpenRouter निवडल्यास; account मध्ये "training करणारे providers" बंद ठेवा', alt: true },
  { k: 'groq_api_key', label: 'Groq API key', hint: 'Groq निवडल्यास', alt: true },
  { k: 'mistral_api_key', label: 'Mistral API key', hint: 'Mistral निवडल्यास', alt: true },
  { k: 'cerebras_api_key', label: 'Cerebras API key', hint: 'Cerebras निवडल्यास', alt: true },
  { k: 'cloudflare_api_token', label: 'Cloudflare API token (Workers AI)', hint: 'Workers AI परवानगी असलेला token', alt: true },
  { k: 'ollama_api_key', label: 'Ollama key (ऐच्छिक)', hint: 'सर्व्हरवर key ठेवली असल्यासच', alt: true },
];
// Same rules as the Worker's Settings PUT (cloudflare/worker.js) — checked here first, field named in Marathi
const MODEL_NAME = /^[A-Za-z0-9][A-Za-z0-9._:@/-]{1,99}$/;
const MODEL_KEYS = ['gemini_model', 'part1_model', 'fallback_model', 'fallback_model_light', 'engine_model', 'engine_model_light'];
const REQUIRED = ['supabase_url', 'supabase_anon_key', 'owner_email'];
const CLEAR = '__clear__'; // Worker: deletes the key
const UNCLEARABLE = ['supabase_service_key'];
export function checkSettings(v: Record<string, string>): string | null {
  const t = (k: string) => (v[k] ?? '').trim();
  const L = (k: string) => SETTING_LABEL[k] || k;
  for (const k of REQUIRED) if (k in v && !t(k)) return `${L(k)}: रिकामे ठेवता येत नाही`;
  if (t('budget_usd') && !(Number(t('budget_usd')) > 0 && Number(t('budget_usd')) <= 20)) return `${L('budget_usd')}: 0 पेक्षा जास्त व 20 पर्यंतची संख्या लिहा`;
  if (t('monthly_budget_usd') && !(Number(t('monthly_budget_usd')) > 0 && Number(t('monthly_budget_usd')) <= 1000)) return `${L('monthly_budget_usd')}: 0 पेक्षा जास्त व 1000 पर्यंतची संख्या लिहा (रिकामे = $20)`;
  if (t('cloudflare_account_id') && !/^[0-9a-f]{32}$/.test(t('cloudflare_account_id'))) return `${L('cloudflare_account_id')}: नेमकी 32 अक्षरे (0-9, a-f) लिहा`;
  if (t('ollama_base_url') && !/^https?:\/\/[A-Za-z0-9.-]+(:\d+)?(\/[A-Za-z0-9._~/-]*)?$/.test(t('ollama_base_url'))) return `${L('ollama_base_url')}: http:// किंवा https:// ने सुरू होणारा पत्ता लिहा (उदा. https://host:11434)`;
  for (const k of MODEL_KEYS) if (t(k) && !MODEL_NAME.test(t(k))) return `${L(k)}: योग्य मॉडेल-नाव लिहा (अक्षरे, अंक, . _ : @ / - ; जागा नाही)`;
  const ms = t('model_strong');
  if (ms && ms.toLowerCase() !== 'none' && !MODEL_NAME.test(ms)) return `${L('model_strong')}: योग्य मॉडेल-नाव (अक्षरे, अंक, . _ : @ / - ; जागा नाही) किंवा none लिहा`;
  return null;
}

const ROLE_LABEL: Record<string, string> = { owner: 'मालक', staff: 'कार्यासन कर्मचारी', senior: 'वरिष्ठ (फक्त वाचन)' };

export default function Settings() {
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

  const load = async () => {
    try {
      const s = await api<Record<string, string>>('/api/settings');
      setCur(s);
      setEdit(Object.fromEntries(PLAIN.map(p => [p.k, s[p.k] || ''])));
      setClear(new Set());
    } catch (e) {
      toast(humanError(e), 'err');
    }
    const m = await sb().from('members').select('*').order('created_at');
    if (m.error) toast(humanError(m.error.message), 'err');
    setMembers((m.data as Member[]) || []);
  };
  useEffect(() => {
    if (me?.role === 'owner') void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [me?.role]);

  if (me?.role !== 'owner') return <div className="card p-6 text-center">सेटिंग्ज फक्त मालकासाठी.</div>;

  const plainField = (p: (typeof PLAIN)[number]) => (
    <Field key={p.k} label={p.label} hint={p.hint}>
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
        hint={<>{s.hint} • {marked ? <Chip tone="red">जतन केल्यावर की काढली जाईल</Chip> : cur?.[s.k] ? <>सध्या: <span className="font-mono">{cur[s.k]}</span> — बदलायची असल्यासच टाइप करा</> : <Chip tone="amber">भरलेली नाही</Chip>}</>}
      >
        <div className="flex gap-2">
          <input className="input min-w-0 flex-1 font-mono" type="password" autoComplete="off" disabled={marked} placeholder={cur?.[s.k] || ''} value={edit[s.k] ?? ''} onChange={e => setEdit(x => ({ ...x, [s.k]: e.target.value }))} />
          {cur?.[s.k] && !UNCLEARABLE.includes(s.k) && (
            <button type="button" className={marked ? 'btn-primary shrink-0 px-3' : 'btn-ghost shrink-0 px-3'} aria-pressed={marked} onClick={() => toggleClear(s.k)} title="ही की सेटिंग्जमधून काढा">
              {marked ? '↺ ठेवा' : 'key काढा'}
            </button>
          )}
        </div>
      </Field>
    );
  };

  async function save(e: FormEvent) {
    e.preventDefault();
    setFormErr('');
    setBusy(true);
    try {
      // Plain values are sent as typed; a secret is sent only if a new value was typed (empty = unchanged) or "काढा".
      const body: Record<string, string> = {};
      for (const p of PLAIN) if (cur && edit[p.k] !== (cur[p.k] || '')) body[p.k] = edit[p.k] ?? '';
      for (const s of SECRET) if (clear.has(s.k)) body[s.k] = CLEAR; else if (edit[s.k]) body[s.k] = edit[s.k];
      const bad = checkSettings(body);
      if (bad) {
        setFormErr(bad);
        toast(bad, 'err');
        return;
      }
      if (!Object.keys(body).length) {
        toast('काहीही बदल नाही', 'info');
        return;
      }
      await api('/api/settings', { method: 'PUT', body });
      toast('सेटिंग्ज जतन');
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
    if (!/^\S+@\S+\.\S+$/.test(inv.email.trim())) return toast('योग्य ई-मेल लिहा', 'err');
    setInvBusy(true);
    try {
      const r = await api<{ existing?: boolean }>('/api/members', { body: { email: inv.email.trim(), role: inv.role } });
      toast(r?.existing ? 'सदस्य जोडला (या ई-मेलचे खाते आधीच आहे — थेट लॉगिन करता येईल)' : 'आमंत्रण पाठवले');
      setInv({ email: '', role: inv.role });
      await load();
    } catch (x) {
      toast(humanError(x), 'err');
    } finally {
      setInvBusy(false);
    }
  }

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold">सेटिंग्ज</h1>

      <Section title="की व जोडण्या">
        {!cur ? (
          <SkeletonRows n={5} />
        ) : (
          <form onSubmit={save} className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              {PLAIN.filter(p => !p.ai && !p.alt).map(plainField)}
            </div>
            <fieldset className="space-y-3 rounded-lg border border-slate-200 p-4 dark:border-navy-800">
              <legend className="px-1 text-lg font-bold">AI मॉडेल व खर्च</legend>
              <p className="text-sm text-slate-600 dark:text-slate-300">स्वस्त मॉडेल — Study भाग 1–7, संबंधित माहिती, यांत्रिक काम; मुख्य मॉडेल — मसुदा; पडताळणी मॉडेल — अंतिम तपासणी व मंजुरी</p>
              <div className="grid gap-4 md:grid-cols-3">
                {PLAIN.filter(p => p.ai).map(plainField)}
              </div>
            </fieldset>
            <div className="grid gap-4 md:grid-cols-3">
              {SECRET.filter(s => !s.alt).map(secretField)}
            </div>
            <fieldset className="space-y-3 rounded-lg border border-slate-200 p-4 dark:border-navy-800">
              <legend className="px-1 text-lg font-bold">इतर AI (पर्यायी)</legend>
              <ul className="list-disc space-y-1 pl-5 text-sm text-slate-600 dark:text-slate-300">
                <li>रिकामे ठेवल्यास सर्व काम Claude करते. दुसरा AI निवडल्यास प्रकरणावर सूचना येते व सर्व तपासण्या (lint, उतारा-तपासणी, अंतिम पडताळणी, verify) तशाच लागू.</li>
                <li><b className="text-red-700 dark:text-red-400">मोफत मॉडेल:</b> संपूर्ण अभ्यासासाठी पुरेसा व गोपनीयता पाळणारा मोफत पर्याय (स्वतःचा Ollama सोडून) सध्या नाही — तक्ता पाहा.</li>
              </ul>
              <details className="rounded-lg bg-slate-50 p-3 text-sm dark:bg-navy-800/50">
                <summary className="cursor-pointer font-semibold">AI पर्यायांची तुलना (02.11.2026)</summary>
                <div className="mt-2 overflow-x-auto">
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
              <div className="grid gap-4 md:grid-cols-3">
                {PLAIN.filter(p => p.alt).map(plainField)}
                {SECRET.filter(s => s.alt).map(secretField)}
              </div>
            </fieldset>
            {formErr && <div className="break-words rounded-lg border border-red-300 bg-red-50 px-3 py-2 font-semibold text-red-900 dark:border-red-800 dark:bg-red-900/30 dark:text-red-100" role="alert">{formErr}</div>}
            <button className="btn-primary" disabled={busy}>{busy && <Spinner />} जतन करा</button>
          </form>
        )}
      </Section>

      <Section title="सदस्य">
        {!members ? (
          <SkeletonRows n={2} />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[420px]">
              <thead>
                <tr className="border-b border-slate-200 dark:border-navy-800"><th className="th">ई-मेल</th><th className="th">भूमिका</th><th className="th">दिनांक</th></tr>
              </thead>
              <tbody>
                {members.map(m => (
                  <tr key={m.user_id} className="border-b border-slate-100 dark:border-navy-800/60">
                    <td className="td break-all">{m.email}</td>
                    <td className="td"><Chip tone={m.role === 'owner' ? 'navy' : m.role === 'staff' ? 'blue' : 'slate'}>{ROLE_LABEL[m.role] || m.role}</Chip></td>
                    <td className="td">{fmtDate(m.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <form onSubmit={invite} noValidate className="mt-4 grid gap-3 md:grid-cols-[1fr_220px_auto] md:items-end">
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

      <Section title="टिप्पणीतील सही-साखळी, पत्राचे पत्ते, सूचना">
        <p className="text-slate-600 dark:text-slate-300">या सेटिंग्ज अजून उपलब्ध नाहीत. सध्या सही-साखळी व पत्राचा मजकूर कार्यासनाच्या कायमच्या सूचनांनुसार (§4) आपोआप ठरतो.</p>
      </Section>
    </div>
  );
}
