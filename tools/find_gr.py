#!/usr/bin/env python3
"""Search the Internet Archive 'maharashtragr' mirror of gr.maharashtra.gov.in.
Input: tools/find-gr.txt lines:  <date_from> <date_to> <department substring> <grep1|grep2|...>
Output: working-notes/gr-search/<line-no>.md (all candidates + matches); matching PDFs saved to pdf/_found/."""
import json, os, re, sys, urllib.parse, urllib.request
UA = {"User-Agent": "Mozilla/5.0"}
def get(u, t=60):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=t).read()
os.makedirs("working-notes/gr-search", exist_ok=True); os.makedirs("pdf/_found", exist_ok=True)
for n, line in enumerate(open("tools/find-gr.txt", encoding="utf-8"), 1):
    line = line.strip()
    if not line or line.startswith("#"): continue
    d1, d2, dept, pat = line.split(" ", 3)
    q = f'collection:maharashtragr AND date:[{d1} TO {d2}]'
    url = "https://archive.org/advancedsearch.php?" + urllib.parse.urlencode(
        {"q": q, "fl[]": ["identifier", "title", "date", "subject"], "rows": 2000, "output": "json"}, doseq=True)
    docs = json.loads(get(url))["response"]["docs"]
    out = [f"# {line}", f"candidates: {len(docs)}", ""]
    rx = re.compile(pat)
    for d in docs:
        subj = " ".join(d.get("subject", [])) if isinstance(d.get("subject"), list) else str(d.get("subject", ""))
        if dept.lower() not in (subj + " " + str(d.get("title", ""))).lower(): continue
        ident = d["identifier"]; code = ident.split(".")[-1]
        try: txt = get(f"https://archive.org/stream/{ident}/{code}_djvu.txt").decode("utf-8", "ignore")
        except Exception as e: txt = ""
        hit = rx.search(txt)
        out.append(f"- {d.get('date','')[:10]} | {code} | {str(d.get('title',''))[:150]} | {'MATCH' if hit else ''}")
        if hit:
            i = hit.start(); out.append("  > " + txt[max(0, i-300):i+500].replace("\n", " "))
            try:
                open(f"pdf/_found/{code}.pdf", "wb").write(get(f"https://archive.org/download/{ident}/{code}.pdf", 120))
            except Exception as e: out.append(f"  pdf download failed: {e}")
    open(f"working-notes/gr-search/{n:02d}.md", "w", encoding="utf-8").write("\n".join(out))
    print(line, len(docs))
