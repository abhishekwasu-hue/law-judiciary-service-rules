"""Split a Word output into base64 chunk docs for the प्रस्ताव कक्ष page (PROPOSAL_SOP.md Step 0b).

The page's `assets` store does not accept .docx, so each .docx is stored in the page db as documents
outputs/<caseId>__<kind>__<n> = {case, kind, n, total, name, b64}, each b64 < 200 KiB (db doc cap 256 KiB).

Usage: python tools/desk_chunks.py <file.docx> <case_id> <kind> <outdir>
  kind: study | note_letter
Writes <outdir>/<case>__<kind>__<n>.json (one per chunk) and prints the record for cases/<case_id>.outputs[].
Write the chunk files with ArtifactData batch: op set, collection "outputs", doc_id = file stem, file_path = the json file.
"""
import base64
import json
import os
import sys

CHUNK = 190_000  # base64 chars per doc


def main():
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    path, case_id, kind, outdir = sys.argv[1:]
    os.makedirs(outdir, exist_ok=True)
    name = os.path.basename(path)
    b64 = base64.b64encode(open(path, "rb").read()).decode("ascii")
    parts = [b64[i:i + CHUNK] for i in range(0, len(b64), CHUNK)] or [""]
    ref = f"{case_id}__{kind}"
    for n, p in enumerate(parts):
        with open(os.path.join(outdir, f"{ref}__{n}.json"), "w", encoding="utf-8") as f:
            json.dump({"case": case_id, "kind": kind, "n": n, "total": len(parts), "name": name, "b64": p}, f, ensure_ascii=False)
    print(json.dumps({"kind": kind, "name": name, "store": "db", "ref": ref}, ensure_ascii=False))


if __name__ == "__main__":
    main()
