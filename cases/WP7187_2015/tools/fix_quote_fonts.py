"""Put curly quotes / dashes in their own runs with Times New Roman on all four rFonts (DVOT-SurekhMR lacks these glyphs -> boxes when printed)."""
import sys, copy, re, zipfile, shutil, os
from lxml import etree
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
q=lambda t:'{%s}%s'%(W,t)
CH='“”‘’–—…'
RX=re.compile('([%s])'%CH)
def fix_root(root):
    n=0
    for r in list(root.iter(q('r'))):
        kids=[c for c in r if c.tag!=q('rPr')]
        if not any(c.tag==q('t') and c.text and RX.search(c.text) for c in kids): continue
        for c in kids:
            if c.tag==q('lastRenderedPageBreak'): r.remove(c)
        kids=[c for c in r if c.tag!=q('rPr')]
        if any(c.tag not in (q('t'),q('tab'),q('br')) for c in kids): continue
        rpr=r.find(q('rPr'))
        pieces=[]
        for c in kids:
            if c.tag==q('t'):
                pieces+= [('t',p) for p in RX.split(c.text or '') if p]
            else:
                pieces.append(('e',c))
        parent=r.getparent(); idx=parent.index(r)
        for k,(kind,v) in enumerate(pieces):
            nr=etree.Element(q('r'))
            nrpr=copy.deepcopy(rpr) if rpr is not None else etree.Element(q('rPr'))
            nr.append(nrpr)
            if kind=='t':
                t=etree.SubElement(nr,q('t')); t.text=v
                t.set('{http://www.w3.org/XML/1998/namespace}space','preserve')
                if v in CH:
                    f=nrpr.find(q('rFonts'))
                    if f is None:
                        f=etree.Element(q('rFonts')); nrpr.insert(0,f)
                    for a in list(f.attrib): del f.attrib[a]
                    for a in ('ascii','hAnsi','cs','eastAsia'): f.set(q(a),'Times New Roman')
                    n+=1
            else:
                nr.append(copy.deepcopy(v))
            parent.insert(idx+k,nr)
        parent.remove(r)
    return n
def fix(path):
    tmp=path+'.tmp'; zin=zipfile.ZipFile(path); zout=zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED); tot=0
    for it in zin.infolist():
        data=zin.read(it.filename)
        if it.filename.startswith('word/') and it.filename.endswith('.xml') and b'<w:t' in data:
            root=etree.fromstring(data); c=fix_root(root); tot+=c
            if c: data=etree.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
        zout.writestr(it,data)
    zin.close(); zout.close(); shutil.move(tmp,path); return tot
for p in sys.argv[1:]: print(os.path.basename(p), fix(p))
