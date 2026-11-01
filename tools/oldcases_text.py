#!/usr/bin/env python3
"""oldcases_text.py <outdir>  — dump every .docx in the repo's 'सन ... प्रकरणे.zip' files to text, for grep.
Writes <outdir>/t/NNN.txt (first line = path inside zip) and <outdir>/index.tsv. Run from the repo root.
Use: grep the index for the subject (वेतननिश्चिती, भत्ता, निवृत्ती, विकल्प, अतिरिक्त कार्यभार ...), read 2-3 old notes of
the same type and copy their LANGUAGE/STRUCTURE (never names/ids). Good models: Finance-approval note with tables
(C R 309-2024), information letter via High Court (C R 6-2026), reply on earlier opinion (C R 21-2024, C R 51-2025)."""
import zipfile, glob, io, os, sys, docx
out = sys.argv[1]; os.makedirs(f"{out}/t", exist_ok=True); idx = []; n = 0
for z in sorted(glob.glob("सन*.zip")):
    zf = zipfile.ZipFile(z)
    for i in zf.infolist():
        nm = i.filename
        try: nm = nm.encode("cp437").decode("utf-8")
        except Exception: pass
        if not nm.lower().endswith(".docx") or "~$" in nm: continue
        try: d = docx.Document(io.BytesIO(zf.read(i)))
        except Exception: continue
        lines = [p.text for p in d.paragraphs]
        for t in d.tables:
            for r in t.rows: lines.append(" | ".join(c.text for c in r.cells))
        n += 1; fn = f"{out}/t/{n:03d}.txt"
        open(fn, "w", encoding="utf-8").write(nm + "\n=====\n" + "\n".join(lines)); idx.append(f"{fn}\t{os.path.basename(z)}\t{nm}")
open(f"{out}/index.tsv", "w", encoding="utf-8").write("\n".join(idx)); print(n, "files")
