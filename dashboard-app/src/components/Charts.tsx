// All Recharts use lives here; pages load this file lazily so the first load does not pull Recharts.
import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { CATEGORIES, TONE_HEX, type Tone } from '../lib/constants';
import { Empty, Section } from './ui';

// Categorical palette for the donut (10 categories); navy-led, saffron used once.
const CAT_COLORS = ['#2b4477', '#ee8a1c', '#3b82f6', '#0d9488', '#7c3aed', '#be185d', '#65a30d', '#0891b2', '#a16207', '#64748b'];
const TICK = { fontSize: 12, fill: '#64748b' };
const chartAxis = { tick: TICK };
const tipStyle = { contentStyle: { borderRadius: 8, fontSize: 14 } };

/** Category-axis width (px) and line length (UTF-16 units) for wrapped Devanagari labels: fits a 360 px phone. */
const LABEL_W = 112;
const LABEL_CHARS = 16;
const LINE_H = 14;

function wrap(text: string, max: number): string[] {
  const out: string[] = [];
  let cur = '';
  for (const w of text.split(/\s+/).filter(Boolean)) {
    if (cur && (cur + ' ' + w).length > max) {
      out.push(cur);
      cur = w;
    } else cur = cur ? `${cur} ${w}` : w;
  }
  if (cur) out.push(cur);
  return out.length ? out : [''];
}

/** Y-axis tick of a horizontal bar chart: the full label, wrapped onto lines (nothing clipped). */
function WrapTick({ x, y, payload }: { x?: number; y?: number; payload?: { value?: unknown } }) {
  const lines = wrap(String(payload?.value ?? ''), LABEL_CHARS);
  const dy0 = -((lines.length - 1) * LINE_H) / 2;
  return (
    <text x={x} y={y} textAnchor="end" fontSize={TICK.fontSize} fill={TICK.fill} dominantBaseline="central">
      {lines.map((l, i) => (
        <tspan key={i} x={x} dy={i === 0 ? dy0 : LINE_H}>{l}</tspan>
      ))}
    </text>
  );
}

/** Height that gives each bar row room for up to 3 wrapped (14 px) label lines. */
const rowsHeight = (n: number) => Math.max(160, n * 54 + 40);

function HBar({ data, dataKey = 'value', nameKey = 'name', fill, cells, unit, onPick }: {
  data: Record<string, unknown>[]; dataKey?: string; nameKey?: string; fill?: string; cells?: string[]; unit: (v: number) => [string | number, string]; onPick?: (name: string) => void;
}) {
  return (
    <div style={{ height: rowsHeight(data.length) }}>
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical" margin={{ left: 0, right: 16, top: 4, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#94a3b833" />
          <XAxis type="number" allowDecimals={false} {...chartAxis} />
          <YAxis type="category" dataKey={nameKey} width={LABEL_W} interval={0} tick={<WrapTick />} />
          <Tooltip {...tipStyle} formatter={(v: number) => unit(v)} />
          <Bar dataKey={dataKey} fill={fill} radius={[0, 4, 4, 0]} className={onPick ? 'cursor-pointer' : undefined} onClick={(d: { name?: string }) => onPick && d.name && onPick(d.name)}>
            {cells && cells.map((c, i) => <Cell key={i} fill={c} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export interface HomeChartsProps {
  catData: { name: string; value: number }[];
  stageData: { name: string; value: number; tone: Tone }[];
  monthly: { name: string; प्राप्त: number; बंद: number }[];
  byOffice: { name: string; value: number }[];
  avgDays: { name: string; value: number }[];
  onCategory: (name: string) => void;
  onStage: (name: string) => void;
  onOffice: (name: string) => void;
}

export function HomeCharts({ catData, stageData, monthly, byOffice, avgDays, onCategory, onStage, onOffice }: HomeChartsProps) {
  return (
    <div className="mt-4 grid gap-4 lg:grid-cols-2">
      <Section title="प्रवर्गनिहाय प्रकरणे">
        <div className="h-72">
          {catData.length === 0 ? <Empty title="माहिती नाही" /> : (
            <ResponsiveContainer>
              <PieChart>
                <Pie data={catData} dataKey="value" nameKey="name" innerRadius="55%" outerRadius="85%" paddingAngle={2} onClick={(d: { name?: string }) => d.name && onCategory(d.name)} className="cursor-pointer">
                  {catData.map(d => <Cell key={d.name} fill={CAT_COLORS[CATEGORIES.indexOf(d.name as (typeof CATEGORIES)[number])]} />)}
                </Pie>
                <Tooltip {...tipStyle} />
                <Legend wrapperStyle={{ fontSize: 13 }} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </Section>
      <Section title="टप्पानिहाय प्रकरणे">
        <HBar data={stageData} cells={stageData.map(d => TONE_HEX[d.tone])} unit={v => [v, 'प्रकरणे']} onPick={onStage} />
      </Section>
      <Section title="मासिक: प्राप्त विरुद्ध बंद">
        <div className="h-64">
          <ResponsiveContainer>
            <LineChart data={monthly} margin={{ left: -16, right: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#94a3b833" />
              <XAxis dataKey="name" {...chartAxis} />
              <YAxis allowDecimals={false} {...chartAxis} />
              <Tooltip {...tipStyle} />
              <Legend wrapperStyle={{ fontSize: 13 }} />
              <Line type="monotone" dataKey="प्राप्त" stroke={TONE_HEX.navy} strokeWidth={2} dot={{ r: 3 }} />
              <Line type="monotone" dataKey="बंद" stroke={TONE_HEX.green} strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Section>
      <Section title="कार्यालयनिहाय प्रलंबित उत्तरे">
        {byOffice.length === 0 ? <Empty icon="✅" title="प्रलंबित उत्तर नाही" /> : (
          <HBar data={byOffice} fill={TONE_HEX.amber} unit={v => [v, 'उत्तरे']} onPick={n => n !== 'नमूद नाही' && onOffice(n)} />
        )}
      </Section>
      <Section title="सरासरी दिवस — टप्पानिहाय" className="lg:col-span-2">
        {avgDays.length === 0 ? <Empty title="टप्पे बदलल्यावर येथे दिसेल" /> : (
          <HBar data={avgDays} fill={TONE_HEX.navy} unit={v => [`${v} दिवस`, 'सरासरी']} onPick={onStage} />
        )}
      </Section>
    </div>
  );
}

/** Days spent in each stage of one case (ब्रीफिंग tab). */
export function StageDaysChart({ days }: { days: { stage: string; days: number }[] }) {
  return <HBar data={days} nameKey="stage" dataKey="days" fill={TONE_HEX.navy} unit={v => [`${v} दिवस`, '']} />;
}
