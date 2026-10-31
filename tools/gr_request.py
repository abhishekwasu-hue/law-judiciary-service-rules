#!/usr/bin/env python3
"""On-demand GR fetch (runs in GitHub Actions). Only the GRs asked for are stored — no bulk copying.
Requests: tools/gr-request.txt, one per line:
  code <sanketank>                                   e.g.  code 201909111829520805
  search <date_from> <date_to> <words...>            e.g.  search 2019-09-11 2019-09-11 ठोक भरपाई
    (searches title/description in the archive.org mirror of gr.maharashtra.gov.in; downloads at most 5 matches)
Output: pdf/gr/<code>.pdf  +  pdf/gr/INDEX.tsv (code, date, department, title, request).
Processed lines are moved to the '# done' section so they are not fetched again."""
import json, os, re, time, urllib.parse, urllib.request
UA = {"User-Agent": "Mozilla/5.0"}
def get(u, t=90):
    for i in range(3):
        try: return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=t).read()
        except Exception:
            if i == 2: raise
            time.sleep(5)
os.makedirs("pdf/gr", exist_ok=True)
IDX = "pdf/gr/INDEX.tsv"
if not os.path.exists(IDX): open(IDX, "w", encoding="utf-8").write("code\tdate\tdepartment\ttitle\trequest\n")
have = {l.split("\t")[0] for l in open(IDX, encoding="utf-8")}
def meta(code):
    u = "https://archive.org/advancedsearch.php?" + urllib.parse.urlencode({"q": f"identifier:in.gov.maharashtra.gr.{code}", "fl[]": ["title", "date", "subject"], "output": "json"}, doseq=True)
    d = json.loads(get(u))["response"]["docs"]; return d[0] if d else {}
def save(code, req, m=None):
    if code in have: return "exists"
    data = None
    for u in (f"https://gr.maharashtra.gov.in/Site/Upload/Government%20Resolutions/Marathi/{code}.pdf",
              f"https://archive.org/download/in.gov.maharashtra.gr.{code}/{code}.pdf",
              f"https://gr.maharashtra.gov.in/Site/Upload/Government%20Resolutions/English/{code}.pdf"):
        try:
            b = get(u, 120)
            if b[:4] == b"%PDF": data = b; break
        except Exception: pass
    if not data: return "not found"
    open(f"pdf/gr/{code}.pdf", "wb").write(data)
    m = m or meta(code); subj = m.get("subject", ""); subj = ", ".join(subj) if isinstance(subj, list) else subj
    open(IDX, "a", encoding="utf-8").write(f"{code}\t{str(m.get('date',''))[:10]}\t{subj}\t{str(m.get('title','')).replace(chr(9),' ')}\t{req}\n")
    have.add(code); return "saved"
lines = open("tools/gr-request.txt", encoding="utf-8").read().split("\n")
todo, done, head = [], [], []
sect = "head"
for l in lines:
    if l.strip() == "# done": sect = "done"; continue
    if sect == "done": done.append(l); continue
    (todo if l.strip() and not l.startswith("#") else head).append(l)
log = []
for req in todo:
    p = req.split()
    try:
        if p[0] == "code":
            log.append(f"{req}  ->  {save(p[1], req)}")
        elif p[0] == "search":
            d1, d2, words = p[1], p[2], " ".join(p[3:])
            q = f'collection:maharashtragr AND date:[{d1} TO {d2}] AND (title:({words}) OR description:({words}))'
            u = "https://archive.org/advancedsearch.php?" + urllib.parse.urlencode({"q": q, "fl[]": ["identifier", "title", "date", "subject"], "rows": 5, "output": "json"}, doseq=True)
            docs = json.loads(get(u))["response"]["docs"]
            if not docs: log.append(f"{req}  ->  no match")
            for d in docs:
                code = d["identifier"].split(".")[-1]
                log.append(f"{req}  ->  {code} {str(d.get('title',''))[:80]}  ->  {save(code, req, d)}")
        else: log.append(f"{req}  ->  unknown request type")
    except Exception as e: log.append(f"{req}  ->  error {e}")
open("tools/gr-request.txt", "w", encoding="utf-8").write("\n".join(head + ["# done"] + [f"{x}" for x in log] + [x for x in done if x.strip()]) + "\n")
print("\n".join(log))
