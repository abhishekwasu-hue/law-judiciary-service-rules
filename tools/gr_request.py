#!/usr/bin/env python3
"""On-demand GR fetch (runs in GitHub Actions). Only the GRs asked for are stored — no bulk copying.
Requests: tools/gr-request.txt, one per line:
  code <sanketank>                                   e.g.  code 201909111829520805
  search <date_from> <date_to> <words...>            e.g.  search 2019-09-11 2019-09-11 ठोक भरपाई
  dept <date_from> <date_to> <department words>      e.g.  dept 2022-04-19 2022-04-19 Law Judiciary   (all GRs of that dept on those dates, max 15)
    (searches title/description in the archive.org mirror of gr.maharashtra.gov.in; downloads at most 5 matches)
Output: pdf/gr/<code>.pdf  +  pdf/gr/INDEX.tsv (code, date, department, title, request).
Processed lines are moved to the '# done' section so they are not fetched again. A request that found nothing or hit an
error ("not found" / "no match" / "error") stays in the to-do list with a counter (`  #retry=N`) and is tried again on the
next run; after 3 tries it moves to '# done' as "gave up after 3 tries". The INDEX row is written together with the PDF
(metadata is looked up afterwards and filled in; a metadata error never leaves a PDF without its INDEX row)."""
import json, os, re, time, urllib.parse, urllib.request
MAX_TRIES = 3
RETRY = "  #retry="
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
def row(code, m, req):
    subj = m.get("subject", ""); subj = ", ".join(subj) if isinstance(subj, list) else subj
    date = str(m.get("date", ""))[:10] or (f"{code[:4]}-{code[4:6]}-{code[6:8]}" if re.fullmatch(r"\d{16,20}", code) else "")
    clean = lambda v: str(v).replace("\t", " ").replace("\n", " ")
    return f"{code}\t{date}\t{clean(subj)}\t{clean(m.get('title', ''))}\t{clean(req)}\n"
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
    first = row(code, m or {}, req)
    open(IDX, "a", encoding="utf-8").write(first)   # INDEX row first: never a PDF without its row
    have.add(code)
    if m is None:
        try:
            full = row(code, meta(code), req)
            if full != first:
                t = open(IDX, encoding="utf-8").read()
                if t.endswith(first): open(IDX, "w", encoding="utf-8").write(t[: -len(first)] + full)
        except Exception as e:
            return f"saved (metadata not found: {str(e)[:60]})"
    return "saved"
lines = open("tools/gr-request.txt", encoding="utf-8").read().split("\n")
todo, done, head = [], [], []
sect = "head"
for l in lines:
    if l.strip() == "# done": sect = "done"; continue
    if sect == "done": done.append(l); continue
    (todo if l.strip() and not l.startswith("#") else head).append(l)
log, retry = [], []
FAILED = re.compile(r"->\s+(not found|no match|error)")
for line in todo:
    req, _, n = line.partition(RETRY)
    req = req.strip(); tries = int(n) if n.strip().isdigit() else 0
    start = len(log)
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
        elif p[0] == "dept":
            # dept <date_from> <date_to> <department words>  -> all GRs of that department in the date range (max 15)
            d1, d2, words = p[1], p[2], " AND ".join(f"subject:({w})" for w in p[3:])
            q = f'collection:maharashtragr AND date:[{d1} TO {d2}] AND {words}'
            u = "https://archive.org/advancedsearch.php?" + urllib.parse.urlencode({"q": q, "fl[]": ["identifier", "title", "date", "subject", "description"], "rows": 15, "output": "json"}, doseq=True)
            docs = json.loads(get(u))["response"]["docs"]
            if not docs: log.append(f"{req}  ->  no match")
            for d in docs:
                code = d["identifier"].split(".")[-1]
                d["title"] = str(d.get("description") or d.get("title", ""))[:200]
                log.append(f"{req}  ->  {code} {d['title'][:90]}  ->  {save(code, req, d)}")
        else: log.append(f"{req}  ->  unknown request type")
    except Exception as e: log.append(f"{req}  ->  error {e}")
    mine = log[start:]
    if any(FAILED.search(x) for x in mine):
        tries += 1
        if tries < MAX_TRIES:
            retry.append(f"{req}{RETRY}{tries}")
            del log[start:]
            print("\n".join(mine), f"  (try {tries}/{MAX_TRIES}; kept for retry)", sep="\n")
        else:
            log[start:] = [f"{x}  (gave up after {MAX_TRIES} tries)" for x in mine]
open("tools/gr-request.txt", "w", encoding="utf-8").write("\n".join(head + retry + ["# done"] + [f"{x}" for x in log] + [x for x in done if x.strip()]) + "\n")
print("\n".join(log))
