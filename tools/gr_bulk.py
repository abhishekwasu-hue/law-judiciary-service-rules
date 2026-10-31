#!/usr/bin/env python3
"""Bulk GR library builder (runs in GitHub Actions; the Claude sandbox cannot reach these hosts).
Source: Internet Archive mirror of gr.maharashtra.gov.in (collection 'maharashtragr'; subject = department).
1) gr-index/<dept-slug>.tsv  : code, date, title, official url — ALL GRs of the listed departments.
2) gr-library/<dept-slug>/<year>/<code>.pdf : only GRs whose title matches the service-matter keywords
   (config tools/gr-bulk.cfg), skipping files already present. Stops after MAX_MIN minutes; the workflow
   re-runs on schedule until everything is downloaded.
"""
import json, os, re, sys, time, urllib.parse, urllib.request
UA = {"User-Agent": "Mozilla/5.0 (law-judiciary-service-rules GR library)"}
START = time.time(); MAX_MIN = float(os.environ.get("MAX_MIN", "45"))
def get(u, t=90):
    for i in range(3):
        try: return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=t).read()
        except Exception as e:
            if i == 2: raise
            time.sleep(5)
cfg = {}
for line in open("tools/gr-bulk.cfg", encoding="utf-8"):
    line = line.strip()
    if line and not line.startswith("#"):
        k, v = line.split("=", 1); cfg.setdefault(k.strip(), []).append(v.strip())
depts = cfg["dept"]; kw = re.compile("|".join(cfg["keyword"]), re.I)
index_all = cfg.get("index_all", ["no"])[0] == "yes"
os.makedirs("gr-index", exist_ok=True)
def slug(s): return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
def search(q):
    out, page = [], 1
    while True:
        u = "https://archive.org/advancedsearch.php?" + urllib.parse.urlencode(
            {"q": q, "fl[]": ["identifier", "title", "date", "subject"], "rows": 5000, "page": page, "output": "json"}, doseq=True)
        r = json.loads(get(u))["response"]; out += r["docs"]
        if len(out) >= r["numFound"] or not r["docs"]: return out
        page += 1
def dept_of(d):
    s = d.get("subject", []); s = s if isinstance(s, list) else [s]
    for x in s:
        if "department" in str(x).lower() or "विभाग" in str(x): return str(x)
    return "unknown"
queue = []
targets = ["*"] if index_all else depts
for dep in targets:
    q = "collection:maharashtragr" + ("" if dep == "*" else f' AND subject:"{dep}"')
    docs = search(q)
    groups = {}
    for d in docs: groups.setdefault(dept_of(d) if dep == "*" else dep, []).append(d)
    for g, items in groups.items():
        rows = []
        for d in sorted(items, key=lambda x: str(x.get("date", ""))):
            code = d["identifier"].split(".")[-1]; date = str(d.get("date", ""))[:10]; title = str(d.get("title", "")).replace("\t", " ").replace("\n", " ")
            rows.append(f"{code}\t{date}\t{title}\thttps://gr.maharashtra.gov.in/Site/Upload/Government%20Resolutions/Marathi/{code}.pdf")
            if g in depts and kw.search(title): queue.append((g, code, date, d["identifier"]))
        open(f"gr-index/{slug(g)}.tsv", "w", encoding="utf-8").write("code\tdate\ttitle\turl\n" + "\n".join(rows) + "\n")
        print("index", g, len(rows), flush=True)
print("to download (keyword match):", len(queue), flush=True)
done = skip = fail = 0
MAX_BYTES = float(cfg.get("max_gb", ["2.5"])[0]) * 1e9
used = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk("gr-library") for f in fs) if os.path.isdir("gr-library") else 0
for g, code, date, ident in queue:
    if (time.time() - START) / 60 > MAX_MIN: print("time limit reached", flush=True); break
    path = f"gr-library/{slug(g)}/{date[:4] or 'unknown'}/{code}.pdf"
    if os.path.exists(path): skip += 1; continue
    if used > MAX_BYTES: print("size limit reached (max_gb)", flush=True); break
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        data = get(f"https://archive.org/download/{ident}/{code}.pdf", 120)
        if data[:4] != b"%PDF": raise ValueError("not pdf")
        open(path, "wb").write(data); done += 1; used += len(data)
    except Exception as e:
        fail += 1; open("gr-index/_failed.txt", "a").write(f"{code}\t{e}\n")
remaining = sum(1 for g, c, d, i in queue if not os.path.exists(f"gr-library/{slug(g)}/{d[:4] or 'unknown'}/{c}.pdf"))
open("gr-index/_status.txt", "w").write(f"queue={len(queue)} downloaded_this_run={done} existing={skip} failed={fail} remaining={remaining}\n")
print(open("gr-index/_status.txt").read())
