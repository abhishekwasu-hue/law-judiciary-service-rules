const pptxgen = require('pptxgenjs');
const SK = '/root/.claude/skills/synced/d7e40bb8-6ce7-4486-9e34-05278f5d2b93_dafb7652-fbbe-43be-ae4f-a15174d81e5c/pptx';
const { applyTheme } = require(SK + '/scripts/apply_theme.js');
const D = require('./data.json');

const THEME = {
  name: 'Nyay BW', headFontFace: 'Nirmala UI', bodyFontFace: 'Nirmala UI',
  colors: { dk1: '000000', lt1: 'FFFFFF', dk2: '000000', lt2: 'F2F2F2',
    accent1: '000000', accent2: '000000', accent3: '000000', accent4: '595959', accent5: '000000', accent6: '595959',
    hlink: '000000', folHlink: '404040' }
};
const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE'; // 13.33 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = 'दुय्यम न्यायालय कर्मचारी वेतनश्रेणी सुधारणा — आर्थिक भार';
const C = pres.SchemeColor;
const NAVY = '000000', SAF = '404040', TEAL = '737373', GOLD = 'BFBFBF', MAR = '262626', TINT = 'F2F2F2';

pres.defineSlideMaster({
  title: 'TITLE', background: { color: 'FFFFFF' },
  objects: [
    { placeholder: { options: { name: 'title', type: 'title', x: 0.8, y: 2.0, w: 11.7, h: 1.8, fontSize: 40, bold: true, color: C.text1, valign: 'bottom' }, text: '' } },
    { placeholder: { options: { name: 'body', type: 'body', x: 0.8, y: 4.0, w: 11.7, h: 1.6, fontSize: 18, color: '404040', valign: 'top' }, text: '' } },
  ],
});
pres.defineSlideMaster({
  title: 'CONTENT', background: { color: 'FFFFFF' }, margin: [0.5, 0.6, 0.7, 0.6],
  objects: [
    { placeholder: { options: { name: 'title', type: 'title', x: 0.6, y: 0.35, w: 12.1, h: 0.9, fontSize: 32, bold: true, color: C.text2, valign: 'middle' }, text: '' } },
    { text: { text: 'विधि व न्याय विभाग • प्र.क्र. 28/2025', options: { x: 0.6, y: 7.0, w: 8, h: 0.35, fontSize: 10, color: C.text2 } } },
  ],
  slideNumber: { x: 12.2, y: 7.0, w: 0.6, h: 0.35, fontSize: 10, color: '404040', align: 'right' },
});

function zebra(rows){rows.forEach((r,i)=>{if(i>0&&i%2===0)r.forEach(c=>{c.options=Object.assign({fill:{color:'F2F2F2'}},c.options)})});return rows}
const T = (s, txt, o) => s.addText(txt, Object.assign({ isTextBox: true, margin: 0, color: C.text1 }, o));
function card(s, x, y, w, h, name, fill) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.1, fill: { color: fill || C.background2 }, line: { color: '7F7F7F', width: 0.75 }, objectName: name });
}
function stat(s, x, y, w, big, label, name, col) {
  card(s, x, y, w, 1.9, name);
  T(s, big, { x: x + 0.25, y: y + 0.25, w: w - 0.5, h: 0.95, fontSize: 36, bold: true, color: col || C.accent1, objectName: name + '-v' });
  T(s, label, { x: x + 0.25, y: y + 1.2, w: w - 0.5, h: 0.55, fontSize: 14, color: C.text2, objectName: name + '-l' });
}
const hdr = (t) => ({ text: t, options: { bold: true, color: 'FFFFFF', fill: { color: '000000' }, fontSize: 14, valign: 'middle' } });
const cell = (t, o = {}) => ({ text: String(t), options: Object.assign({ fontSize: 14, color: '000000', valign: 'middle' }, o) });
const tblOpts = (x, y, w, colW) => ({ x, y, w, colW, border: { type: 'solid', pt: 0.75, color: '7F7F7F' }, margin: [0.04, 0.08, 0.04, 0.08], fontFace: 'Nirmala UI' });
const chartTxt = { catAxisLabelFontFace: '+mn-lt', valAxisLabelFontFace: '+mn-lt', dataLabelFontFace: '+mn-lt', titleFontFace: '+mn-lt',
  catAxisLabelColor: '000000', valAxisLabelColor: '000000', dataLabelColor: '000000', catAxisLabelFontSize: 12, valAxisLabelFontSize: 12, dataLabelFontSize: 11 };

// 1 Title
pres.addSection({ title: 'सुरुवात' });
let s = pres.addSlide({ masterName: 'TITLE', sectionTitle: 'सुरुवात' });
s.addText('दुय्यम न्यायालय कर्मचाऱ्यांना सुधारित वेतनश्रेणी — आर्थिक भार', { placeholder: 'title' });
s.addText([{ text: 'सहावा वेतन आयोग • उच्च न्यायालय कर्मचाऱ्यांप्रमाणे वेतनश्रेणी', options: { breakLine: true } }, { text: 'प्र.क्र. 28/2025 • विधि व न्याय विभाग / कार्यासन-6 • नोव्हेंबर 2026' }], { placeholder: 'body' });

// 2 Demand
pres.addSection({ title: 'प्रस्ताव' });
s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: 'प्रस्ताव' });
s.addText('प्रस्ताव थोडक्यात', { placeholder: 'title' });
stat(s, 0.6, 1.5, 3.8, '197', 'संवर्ग, 8 आस्थापना', 'st-cadre', C.accent1);
stat(s, 4.75, 1.5, 3.8, '26,558', 'मंजूर पदे (24,565 कार्यरत)', 'st-posts', C.accent3);
stat(s, 8.9, 1.5, 3.8, '01.01.2006', 'पासून प्रत्यक्ष लाभ — मा. उच्च न्यायालयाच्या विशेष समितीची शिफारस', 'st-date', C.accent2);
T(s, [
  { text: 'प्रस्ताव: उच्च न्यायालय कर्मचाऱ्यांप्रमाणे (शासन निर्णय 19.04.2022 व 11.01.2023) सुधारित वेतनश्रेणी', options: { bullet: true, breakLine: true } },
  { text: 'उच्च न्यायालय कर्मचाऱ्यांना: 01.01.2006 पासून काल्पनिक, 01.04.2011 पासून प्रत्यक्ष लाभ', options: { bullet: true, breakLine: true } },
  { text: 'वित्त विभाग (सेवा-9, व्यय-10): प्रस्ताव मान्य करता येणार नाही', options: { bullet: true, breakLine: true } },
  { text: 'मा. मुख्यमंत्री: उपमुख्यमंत्री (वित्त), मुख्य सचिव, वित्त सचिव, विधि व न्याय सचिव यांची एकत्रित चर्चा', options: { bullet: true } },
], { x: 0.6, y: 3.75, w: 12.1, h: 3.0, fontSize: 16, paraSpaceAfter: 8, valign: 'top', objectName: 'demand-list' });

// 3 Key figures
pres.addSection({ title: 'आर्थिक भार' });
s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: 'आर्थिक भार' });
s.addText('वार्षिक वेतन खर्च ₹2,081.35 कोटीवरून ₹2,735.43 कोटी', { placeholder: 'title' });
stat(s, 0.6, 1.5, 5.9, '₹654.08 कोटी', 'वार्षिक वेतन खर्चातील फरक (दरमहा ₹54.51 कोटी) • मा. उच्च न्यायालयाचे दि. 23.11.2026 चे पत्र (परिशिष्ट-अ)', 'k1', C.accent2);
stat(s, 6.8, 1.5, 5.9, '24,565', 'कार्यरत पदे (मंजूर पदे 26,558)', 'k2', C.accent3);
s.addChart(pres.charts.BAR, [{ name: 'वार्षिक वेतन खर्च', labels: ['आजचा वार्षिक खर्च', 'सुधारणेनंतर वार्षिक खर्च'], values: [2081.35, 2735.43] }], Object.assign({
  x: 0.6, y: 3.65, w: 12.1, h: 3.2, barDir: 'col', chartColors: ['A6A6A6', '404040'], showValue: true, dataLabelPosition: 'outEnd', dataLabelFormatCode: '₹#,##0.00 "कोटी"',
  valAxisHidden: true, valGridLine: { style: 'none' }, catGridLine: { style: 'none' }, showLegend: false, showTitle: true, title: 'वार्षिक वेतन खर्च (₹ कोटी) — मा. उच्च न्यायालयाच्या दि. 23.11.2026 च्या पत्रानुसार', titleFontSize: 14, titleColor: '000000', catAxisLabelFontSize: 14, valAxisMaxVal: 3300,
}, chartTxt));

// 4 Options
s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: 'आर्थिक भार' });
s.addText('थकबाकी: पर्याय अ विरुद्ध पर्याय ब', { placeholder: 'title' });
card(s, 0.6, 1.45, 5.9, 2.0, 'optA', 'F2F2F2'); card(s, 6.8, 1.45, 5.9, 2.0, 'optB', 'F2F2F2');
T(s, 'पर्याय अ — 01.04.2011 पासून', { x: 0.85, y: 1.6, w: 5.4, h: 0.45, fontSize: 16, bold: true, color: C.accent3, objectName: 'optA-h' });
T(s, '₹5,117.39 कोटी', { x: 0.85, y: 2.1, w: 5.4, h: 0.8, fontSize: 36, bold: true, color: C.accent3, objectName: 'optA-v' });
T(s, 'उच्च न्यायालय कर्मचाऱ्यांप्रमाणे', { x: 0.85, y: 2.9, w: 5.4, h: 0.4, fontSize: 14, color: C.text2, objectName: 'optA-l' });
T(s, 'पर्याय ब — 01.01.2006 पासून (समितीची शिफारस)', { x: 7.05, y: 1.6, w: 5.4, h: 0.45, fontSize: 16, bold: true, color: C.accent2, objectName: 'optB-h' });
T(s, '₹5,448.27 कोटी', { x: 7.05, y: 2.1, w: 5.4, h: 0.8, fontSize: 36, bold: true, color: C.accent2, objectName: 'optB-v' });
T(s, 'मा. उच्च न्यायालयाच्या विशेष समितीची शिफारस', { x: 7.05, y: 2.9, w: 5.4, h: 0.4, fontSize: 14, color: C.text2, objectName: 'optB-l' });
{
  const rows = [[hdr('बाब (₹ कोटी)'), hdr('पर्याय अ'), hdr('पर्याय ब'), hdr('फरक')]];
  const LBL = ['वार्षिक वेतन खर्चातील फरक (दरवर्षी तेवढाच)', 'थकबाकी (31.03.2027 पर्यंत, एकदाच)', 'लाभ लागू करण्याच्या वर्षी एकूण भार (थकबाकी + त्या वर्षाचा फरक)', 'लाभ लागू केल्यापासून 5 वर्षांचा एकूण भार (थकबाकी + 5 वर्षांचा फरक)', 'लाभ लागू केल्यापासून 10 वर्षांचा एकूण भार (थकबाकी + 10 वर्षांचा फरक)'];
  D.opts.filter(r => !r[0].startsWith('दरमहा')).slice(0, 3).forEach((r, i) => rows.push([cell(LBL[i], { bold: i === 2 }), cell(r[1], { align: 'right', bold: i === 2 }), cell(r[2], { align: 'right', bold: i === 2 }), cell(r[3], { align: 'right' })]));
  s.addTable(zebra(rows), Object.assign(tblOpts(0.6, 3.75, 12.1, [6.1, 2.0, 2.0, 2.0]), { rowH: 0.5 }));
}

// 5 Year-wise
s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: 'आर्थिक भार' });
s.addText('वर्षनिहाय थकबाकी, 2006 ते 2027', { placeholder: 'title' });
{
  const yr = D.year.slice(0, -1);
  const labels = yr.map(r => r[0]);
  const vals = yr.map(r => +r[4].replace(/,/g, ''));
  const colors = yr.map(r => r[1] === '6वा' ? '737373' : r[1] === '7वा' ? '404040' : 'BFBFBF');
  s.addChart(pres.charts.BAR, [{ name: 'थकबाकी (₹ कोटी)', labels, values: vals }], Object.assign({
    x: 0.6, y: 1.35, w: 12.1, h: 4.65, barDir: 'col', chartColors: colors, barGapWidthPct: 40, showValue: true, dataLabelPosition: 'outEnd', dataLabelFormatCode: '#,##0',
    valGridLine: { color: 'D9D9D9', size: 0.5 }, catGridLine: { style: 'none' }, showLegend: false, catAxisLabelRotate: -45, catAxisLabelFontSize: 11,
    showValAxisTitle: true, valAxisTitle: '₹ कोटी', valAxisTitleFontSize: 12, valAxisTitleColor: '000000', valAxisTitleFontFace: '+mn-lt',
  }, chartTxt));
  s.addShape(pres.shapes.RECTANGLE, { x: 0.8, y: 6.2, w: 0.25, h: 0.25, fill: { color: '737373' }, line: { color: '737373' }, objectName: 'lg6' });
  T(s, '2006–11 (फक्त पर्याय ब)', { x: 1.15, y: 6.15, w: 2.4, h: 0.35, fontSize: 12, objectName: 'lg6t' });
  s.addShape(pres.shapes.RECTANGLE, { x: 3.6, y: 6.2, w: 0.25, h: 0.25, fill: { color: '404040' }, line: { color: '404040' }, objectName: 'lg7' });
  T(s, '2011–27 (पर्याय अ व ब)', { x: 3.95, y: 6.15, w: 2.4, h: 0.35, fontSize: 12, objectName: 'lg7t' });
  T(s, '2006–11: ₹330.88 कोटी  •  2011–27: ₹5,117.39 कोटी  •  एकूण ₹5,448.27 कोटी', { x: 0.6, y: 6.5, w: 6.2, h: 0.35, fontSize: 12, bold: true, objectName: 'yr-sum' });
  T(s, 'स्रोत: मा. उच्च न्यायालयाचे दि. 23.11.2026 चे पत्र, परिशिष्ट-ब', { x: 6.9, y: 6.45, w: 5.8, h: 0.45, fontSize: 10, color: C.text2, objectName: 'yr-basis' });
}

// 6 Year-wise table
s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: 'आर्थिक भार' });
s.addText('वर्षनिहाय थकबाकी — तक्ता', { placeholder: 'title' });
{
  const yr = D.year.slice(0, -1);
  const mk = (part) => { const rows = [[hdr('आर्थिक वर्ष'), hdr('थकबाकी'), hdr('एकत्रित')]];
    part.forEach(r => rows.push([cell(r[0], { fontSize: 12 }), cell(r[4], { align: 'right', fontSize: 12 }), cell(r[5], { align: 'right', fontSize: 12 })])); return rows; };
  const o = (x) => Object.assign(tblOpts(x, 1.35, 5.95, [2.15, 1.9, 1.9]), { rowH: 0.42 });
  s.addTable(zebra(mk(yr.slice(0, 11))), o(0.6));
  s.addTable(zebra(mk(yr.slice(11))), o(6.75));
  T(s, 'रक्कम ₹ कोटीत • एकूण ₹5,448.27 कोटी • स्रोत: परिशिष्ट-ब', { x: 0.6, y: 6.55, w: 12.1, h: 0.35, fontSize: 12, bold: true, objectName: 'yt-note' });
}

// 7 Establishments
s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: 'आर्थिक भार' });
s.addText('आस्थापनानिहाय वार्षिक वेतन खर्चातील फरक', { placeholder: 'title' });
{
  const e = D.est.slice(0, -1);
  const short = { 'नगर दिवाणी व सत्र न्यायालय, मुंबई': 'नगर दिवाणी व सत्र न्या., मुंबई', 'मुख्य न्यायदंडाधिकारी, मुंबई': 'मुख्य न्यायदंडाधिकारी, मुंबई', 'मुंबई जिल्हा विधी सेवा प्राधिकरण': 'मुंबई जि. विधी सेवा प्राधि.', 'जिल्हा विधी सेवा प्राधिकरण': 'जिल्हा विधी सेवा प्राधि.' };
  const rev = [...e].reverse();
  s.addChart(pres.charts.BAR, [{ name: 'वार्षिक वाढीव भार', labels: rev.map(r => short[r[0]] || r[0]), values: rev.map(r => +r[4].replace(/,/g, '')) }], Object.assign({
    x: 0.6, y: 1.35, w: 5.6, h: 5.4, barDir: 'bar', chartColors: ['000000'], showValue: true, dataLabelPosition: 'outEnd', dataLabelFormatCode: '#,##0.00',
    valAxisHidden: true, valGridLine: { style: 'none' }, catGridLine: { style: 'none' }, showLegend: false, valAxisMaxVal: 640,
    showTitle: true, title: 'वार्षिक वेतन खर्चातील फरक (₹ कोटी)', titleFontSize: 14, titleColor: '000000', catAxisLabelFontSize: 12,
  }, chartTxt));
  const n = v => +v.replace(/,/g, ''); const f2 = v => v.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const rows = [[hdr('आस्थापना'), hdr('आजचा वार्षिक खर्च'), hdr('सुधारणेनंतर वार्षिक खर्च'), hdr('फरक')]];
  e.forEach(r => rows.push([cell(short[r[0]] || r[0], { fontSize: 12 }), cell(r[3], { align: 'right', fontSize: 12 }), cell(f2(n(r[3]) + n(r[4])), { align: 'right', fontSize: 12 }), cell(r[4], { align: 'right', fontSize: 12, bold: true })]));
  rows.push([cell('एकूण', { bold: true, fontSize: 12 }), cell('2,081.35', { align: 'right', bold: true, fontSize: 12 }), cell('2,735.43', { align: 'right', bold: true, fontSize: 12 }), cell('654.08', { align: 'right', bold: true, fontSize: 12 })]);
  s.addTable(zebra(rows), Object.assign(tblOpts(6.4, 1.45, 6.3, [2.4, 1.3, 1.5, 1.1]), { rowH: 0.48 }));
  T(s, 'रक्कम ₹ कोटी', { x: 6.4, y: 6.4, w: 6.3, h: 0.3, fontSize: 11, color: C.text2, objectName: 'est-unit' });
}

// 9 Pay scales
pres.addSection({ title: 'वेतनश्रेणी' });
s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: 'वेतनश्रेणी' });
s.addText('मा. उच्च न्यायालयाने शिफारस केलेली वेतनश्रेणी', { placeholder: 'title' });
{
  const rows = [[hdr('पद'), hdr('सध्याची वेतनश्रेणी'), hdr('शिफारस केलेली वेतनश्रेणी'), hdr('ग्रेड पे वाढ')]];
  [
    ['प्रबंधक', 'PB-2 9300-34800 + 5400', 'PB-3 15600-39100 + 7900', '+2,500'],
    ['अधीक्षक / शिरस्तेदार', 'PB-2 9300-34800 + 4600', 'PB-2 9300-34800 + 5400 (4 वर्षांनंतर PB-3 + 6600)', '+800'],
    ['अतिरिक्त / सहायक अधीक्षक', 'PB-2 9300-34800 + 4400', 'PB-2 9300-34800 + 5000', '+600'],
    ['लघुलेखक (श्रेणी-1)', 'PB-2 9300-34800 + 4800', 'PB-3 15600-39100 + 6600', '+1,800'],
    ['दुभाषी', 'PB-1 5200-20200 + 2800', 'PB-2 9300-34800 + 4200', '+1,400'],
    ['वरिष्ठ लिपिक', 'PB-1 5200-20200 + 2400', 'PB-1 5200-20200 + 3500', '+1,100'],
    ['लिपिक-टंकलेखक / वाहनचालक', 'PB-1 5200-20200 + 1900', 'PB-1 5200-20200 + 2800', '+900'],
    ['हवालदार / मुकादम', 'PB-1S 4440-7440 + 1650', 'PB-1 5200-20200 + 1800', '+150'],
    ['नाईक / लिफ्टमन', 'PB-1S 4440-7440 + 1600', 'PB-1S 4440-7440 + 1700', '+100'],
    ['शिपाई / पहारेकरी / सफाईगार', 'PB-1S 4440-7440 + 1300', 'PB-1S 4440-7440 + 1600', '+300'],
  ].forEach(r => rows.push([cell(r[0]), cell(r[1]), cell(r[2]), cell(r[3], { align: 'right', bold: true, color: '404040' })]));
  s.addTable(zebra(rows), Object.assign(tblOpts(0.6, 1.3, 12.1, [3.3, 3.0, 4.6, 1.2]), { rowH: 0.45 }));
  T(s, 'जिल्हा व सत्र न्यायालये • विशेष समितीचा अहवाल (मा. उच्च न्यायालय रजिस्ट्रीची शिफारस)', { x: 0.6, y: 6.55, w: 12.1, h: 0.35, fontSize: 12, color: C.text2, objectName: 'ps-note' });
}

// 10 Groups
s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: 'वेतनश्रेणी' });
s.addText('72% पदे गट-क मधील', { placeholder: 'title' });
s.addChart(pres.charts.BAR, [{ name: 'मंजूर पदे', labels: ['गट-अ', 'गट-ब', 'गट-क', 'गट-ड'], values: [86, 991, 18521, 6119] }], Object.assign({
  x: 0.6, y: 1.35, w: 12.1, h: 5.3, barDir: 'col', chartColors: ['737373'], showValue: true, dataLabelPosition: 'outEnd', dataLabelFormatCode: '#,##0',
  valAxisHidden: true, valGridLine: { style: 'none' }, catGridLine: { style: 'none' }, showLegend: false, valAxisMaxVal: 21000,
  showTitle: true, title: 'मंजूर पदे 2025-26', titleFontSize: 14, titleColor: '000000', catAxisLabelFontSize: 14,
}, chartTxt));
{
  // per-category average table removed
}

// 11 Points needing attention
pres.addSection({ title: 'निर्णयासाठी' });
// 12 Decisions
s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: 'निर्णयासाठी' });
s.addText('निर्णय आवश्यक असलेले मुद्दे', { placeholder: 'title' });
{
  const items = [
    ['लाभ कोणत्या तारखेपासून?', 'विशेष समितीची शिफारस: 01.01.2006 पासून (थकबाकी ₹5,448.27 कोटी) • उच्च न्यायालय कर्मचाऱ्यांप्रमाणे: 01.04.2011 पासून (₹5,117.39 कोटी)'],
    ['वार्षिक वेतन खर्च', '₹2,081.35 कोटीवरून ₹2,735.43 कोटी (फरक ₹654.08 कोटी)'],
    ['लाभ लागू करण्याच्या वर्षीची तरतूद', 'थकबाकी + त्या वर्षाचा फरक ₹654.08 कोटी = ₹5,771.46 कोटी (अ) किंवा ₹6,102.35 कोटी (ब)'],
    ['वेळ', 'दरमहा उशिरामागे थकबाकी ₹54.51 कोटीने वाढते'],
  ];
  items.forEach((it, i) => {
    const x = 0.6 + (i % 2) * 6.2, y = 1.45 + Math.floor(i / 2) * 2.65;
    const DCF = ['F2F2F2', 'F2F2F2', 'F2F2F2', 'F2F2F2'], DCT = [C.accent3, C.accent2, C.accent1, C.accent5];
    card(s, x, y, 5.9, 2.4, 'dc' + i, DCF[i]);
    T(s, it[0], { x: x + 0.3, y: y + 0.25, w: 5.3, h: 0.6, fontSize: 20, bold: true, color: DCT[i], objectName: 'dch' + i });
    T(s, it[1], { x: x + 0.3, y: y + 0.95, w: 5.3, h: 1.25, fontSize: 16, valign: 'top', objectName: 'dcd' + i });
  });
}

(async () => {
  await pres.writeFile({ fileName: 'presentation_BW.pptx' });
  await applyTheme('presentation_BW.pptx', THEME);
  console.log('ok');
})();
