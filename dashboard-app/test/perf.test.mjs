// Unit tests of the speed / UI fix helpers (audit 05.11.2026 P2–P5, U2, U6).
// Run: node --test --experimental-strip-types dashboard-app/test/perf.test.mjs   (Node 22.6+)
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  parseInlineConfig, isMissingColumn, latestRunPerCase, pageRows, PAGE_STEP, TODO_TOP, pointsToCheck, studyPointsText,
  routeChunk, barPercents, RUN_LIST_COLUMNS, ACTIVITY_COLUMNS,
} from '../src/lib/perf.ts';

test('P2 inline config: valid, not configured, bad / missing → null (falls back to /api/public-config)', () => {
  assert.deepEqual(parseInlineConfig('{"configured":true,"supabase_url":"https://x.supabase.co","supabase_anon_key":"k"}'),
    { configured: true, supabase_url: 'https://x.supabase.co', supabase_anon_key: 'k' });
  assert.deepEqual(parseInlineConfig('{"configured":false,"supabase_url":"","supabase_anon_key":""}'),
    { configured: false, supabase_url: '', supabase_anon_key: '' });
  for (const t of [null, undefined, '', '  ', '{', 'null', '[]', '{"configured":true}', '{"configured":true,"supabase_url":"x","supabase_anon_key":"k"}',
    '{"configured":true,"supabase_url":"https://x","supabase_anon_key":""}', '{"supabase_url":"https://x","supabase_anon_key":"k"}'])
    assert.equal(parseInlineConfig(t), null, String(t));
  // the Worker escapes "<" as < — JSON.parse restores it
  assert.equal(parseInlineConfig('{"configured":true,"supabase_url":"https://x.co/\\u003c","supabase_anon_key":"k"}').supabase_url, 'https://x.co/<');
});

test('P4 slim columns + missing-column fallback test', () => {
  for (const c of ['id', 'case_id', 'state', 'kind', 'created_at', 'finished_at', 'dispatched_at', 'summary', 'warnings'])
    assert.ok(RUN_LIST_COLUMNS.split(',').includes(c), c);
  assert.ok(!RUN_LIST_COLUMNS.includes('instructions') && !RUN_LIST_COLUMNS.includes('edit_result'));
  assert.equal(ACTIVITY_COLUMNS, 'id,case_id,action,detail,at');
  assert.ok(isMissingColumn({ code: '42703', message: 'column runs.kind does not exist' }));
  assert.ok(isMissingColumn({ code: 'PGRST204', message: '' }));
  assert.ok(isMissingColumn({ message: 'column runs.dispatched_at does not exist' }));
  assert.ok(!isMissingColumn({ code: '42501', message: 'permission denied' }));
  assert.ok(!isMissingColumn(null));
});

test('P4 latest run per case unchanged: newest first wins, edit runs never count', () => {
  const rows = [
    { id: 9, case_id: 1, kind: 'edit' }, { id: 8, case_id: 1, kind: 'full' }, { id: 7, case_id: 2 }, { id: 6, case_id: 1, kind: null }, { id: 5, case_id: 3, kind: 'edit' },
  ];
  const m = latestRunPerCase(rows);
  assert.equal(m.get(1).id, 8);
  assert.equal(m.get(2).id, 7);
  assert.equal(m.has(3), false);
});

test('P5 paging: first 50, "अधिक दाखवा (N)", never beyond the list', () => {
  const rows = Array.from({ length: 120 }, (_, i) => i);
  assert.equal(PAGE_STEP, 50);
  assert.deepEqual([pageRows(rows, 50).visible.length, pageRows(rows, 50).more], [50, 70]);
  assert.deepEqual([pageRows(rows, 100).visible.length, pageRows(rows, 100).more], [100, 20]);
  assert.deepEqual([pageRows(rows, 150).visible.length, pageRows(rows, 150).more], [120, 0]);
  assert.equal(pageRows(rows, 500).visible, rows); // same array when everything is shown
  assert.deepEqual(pageRows([], 50), { visible: [], more: 0 });
});

test('U2 / U6 texts', () => {
  assert.equal(TODO_TOP, 5);
  assert.equal(pointsToCheck(1), '1 मुद्दा तपासावा');
  assert.equal(pointsToCheck(3), '3 मुद्दे तपासावेत');
  assert.match(studyPointsText(1), /^तपासणीचा 1 मुद्दा .* आहे — कृपया वापरण्यापूर्वी पाहावा\.$/);
  assert.match(studyPointsText(2), /^तपासणीचे 2 मुद्दे .* आहेत — कृपया वापरण्यापूर्वी पाहावेत\.$/);
});

test('P2 route → first page file', () => {
  assert.equal(routeChunk('/'), 'home');
  assert.equal(routeChunk('/cases'), 'cases');
  assert.equal(routeChunk('/cases/'), 'cases');
  assert.equal(routeChunk('/cases/60'), 'case');
  assert.equal(routeChunk('/new'), null);
  assert.equal(routeChunk('/cases/abc'), null);
});

test('P3 bar widths', () => {
  assert.deepEqual(barPercents([10, 5, 0, 0.1]), [100, 50, 0, 2]);
  assert.deepEqual(barPercents([0, 0]), [0, 0]);
  assert.deepEqual(barPercents([]), []);
});
