// After `vite build --config vite.artifact.config.ts`: the artifact publisher refuses raw control bytes and U+FFFD in
// text files. public/nasti/index.html (owner's file, unchanged in the repo) carries SheetJS codepage tables with such
// characters inside JS string literals; the published copy gets them as \xNN / � escapes (same string values).
import { readFileSync, writeFileSync } from 'node:fs';
const p = new URL('../dist-artifact/nasti/index.html', import.meta.url);
let s = readFileSync(p, 'utf8');
s = s.replace(/[\x00-\x08\x0b\x0c\x0e-\x1f]/g, c => '\\x' + c.charCodeAt(0).toString(16).padStart(2, '0')).replace(/�/g, '\\ufffd');
writeFileSync(p, s);
console.log('artifact postbuild: nasti/index.html escaped');
