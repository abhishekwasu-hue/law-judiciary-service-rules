import copy, re, sys
import docx
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

SRC, OUT = sys.argv[1], sys.argv[2]
d = docx.Document(SRC)
body = d.element.body
els = list(body)
T_NUM = els[int(sys.argv[4])]
T_SUB = els[int(sys.argv[5])]
T_TBL = els[int(sys.argv[6])]
OLD_LAST = els[int(sys.argv[7])]
LAST_TPL = copy.deepcopy(T_NUM)

ENG = re.compile(r"[A-Za-z][A-Za-z0-9\s.,;:'’\"“”()/\-–&@%]*[A-Za-z0-9.)”\"’]|[A-Za-z]")

def run(text, bold=False, size=24):
    r = OxmlElement('w:r')
    rpr = OxmlElement('w:rPr')
    if ENG.fullmatch(text.strip() or 'x') and re.search('[A-Za-z]', text):
        f = OxmlElement('w:rFonts'); f.set(qn('w:ascii'), 'Times New Roman'); f.set(qn('w:hAnsi'), 'Times New Roman')
        rpr.append(f)
    if bold:
        rpr.append(OxmlElement('w:b')); rpr.append(OxmlElement('w:bCs'))
    for tag in ('w:sz', 'w:szCs'):
        e = OxmlElement(tag); e.set(qn('w:val'), str(size)); rpr.append(e)
    r.append(rpr)
    t = OxmlElement('w:t'); t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    parts = text.split('\t')
    for i, ptxt in enumerate(parts):
        if i:
            r.append(OxmlElement('w:tab'))
        tt = copy.deepcopy(t); tt.text = ptxt; r.append(tt)
    return r

def fill(p, text, bold=False, size=24):
    for ch in list(p):
        if ch.tag != qn('w:pPr'):
            p.remove(ch)
    pos = 0
    for m in ENG.finditer(text):
        if m.start() > pos:
            p.append(run(text[pos:m.start()], bold, size))
        p.append(run(m.group(0), bold, size))
        pos = m.end()
    if pos < len(text):
        p.append(run(text[pos:], bold, size))
    return p

def strip_keep(p):
    ppr = p.find(qn('w:pPr'))
    if ppr is not None:
        for tag in ('w:keepNext', 'w:keepLines'):
            e = ppr.find(qn(tag))
            if e is not None: ppr.remove(e)
    return p

new = []
n = [int(sys.argv[8])]
def NUM(text):
    p = strip_keep(copy.deepcopy(T_NUM)); fill(p, f"{n[0]}.\t{text}"); new.append(p); n[0] += 1
def SUB(k, text):
    p = strip_keep(copy.deepcopy(T_SUB)); fill(p, f"({k})\t{text}"); new.append(p)

def TABLE(rows, widths, bold_last=False):
    tbl = OxmlElement('w:tbl')
    tblpr = copy.deepcopy(T_TBL.find(qn('w:tblPr'))); tbl.append(tblpr)
    grid = OxmlElement('w:tblGrid')
    for w in widths:
        g = OxmlElement('w:gridCol'); g.set(qn('w:w'), str(w)); grid.append(g)
    tbl.append(grid)
    for ri, row in enumerate(rows):
        tr = OxmlElement('w:tr')
        for ci, cell in enumerate(row):
            tc = OxmlElement('w:tc'); tcpr = OxmlElement('w:tcPr')
            tw = OxmlElement('w:tcW'); tw.set(qn('w:w'), str(widths[ci])); tw.set(qn('w:type'), 'dxa'); tcpr.append(tw); tc.append(tcpr)
            p = OxmlElement('w:p'); ppr = OxmlElement('w:pPr')
            sp = OxmlElement('w:spacing'); sp.set(qn('w:after'), '0'); sp.set(qn('w:line'), '240'); sp.set(qn('w:lineRule'), 'auto'); ppr.append(sp)
            if ri == 0 or (ci > 0 and re.fullmatch(r'[\d,.\s]+', cell)):
                jc = OxmlElement('w:jc'); jc.set(qn('w:val'), 'center' if ri == 0 else 'right'); ppr.append(jc)
            p.append(ppr)
            fill(p, cell, bold=(ri == 0 or (bold_last and ri == len(rows) - 1)), size=22)
            tc.append(p); tr.append(tc)
        tbl.append(tr)
    new.append(tbl)
    # spacer
    sp = strip_keep(copy.deepcopy(T_NUM)); fill(sp, ''); new.append(sp)

exec(open(sys.argv[3], encoding='utf-8').read())

idx = list(body).index(OLD_LAST)
for i, el in enumerate(new):
    body.insert(idx + i, el)
if sys.argv[9] == 'remove':
    body.remove(OLD_LAST)
else:
    ts = OLD_LAST.findall('.//'+qn('w:t'))
    old = sys.argv[9]
    for t in ts:
        if t.text and t.text.startswith(old):
            t.text = str(n[0]) + t.text[len(old):]; break
    else:
        raise SystemExit('renumber failed')
cp = d.core_properties; cp.last_modified_by = ''
d.save(OUT)
print('paras added', len(new))
