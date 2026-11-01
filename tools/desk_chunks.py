"""Split an output file into base64 chunk docs for the प्रस्ताव कक्ष page (docs/PROPOSAL_DESK.md).

The page's `assets` store does not accept .docx, so each .docx is stored in the page db as
documents outputs/<case>__<kind>__<i>, each {"i", "n", "data"} with data < 200 KiB (db doc cap 256 KiB).

Usage: python tools/desk_chunks.py <file.docx> <case_id> <kind> <outdir>
  kind: study | note_letter
Writes <outdir>/<case>__<kind>__<i>.json (one per chunk) and prints the output record to put in
cases/<case_id>.outputs[]. Then write the chunk files with ArtifactData batch (op set, collection
"outputs", doc_id = file stem, file_path = the json file).
"""
import base64
import json
import os
import sys

CHUNK = 190_000  # base64 chars per doc

MIME = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pdf": "application/pdf",
}


def main():
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    path, case_id, kind, outdir = sys.argv[1:]
    os.makedirs(outdir, exist_ok=True)
    b64 = base64.b64encode(open(path, "rb").read()).decode("ascii")
    parts = [b64[i:i + CHUNK] for i in range(0, len(b64), CHUNK)] or [""]
    ref = f"{case_id}__{kind}"
    for i, p in enumerate(parts):
        with open(os.path.join(outdir, f"{ref}__{i}.json"), "w", encoding="utf-8") as f:
            json.dump({"i": i, "n": len(parts), "data": p}, f)
    rec = {
        "name": os.path.basename(path),
        "kind": kind,
        "store": "db",
        "ref": ref,
        "chunks": len(parts),
        "mime": MIME.get(os.path.splitext(path)[1].lower(), "application/octet-stream"),
    }
    print(json.dumps(rec, ensure_ascii=False))


if __name__ == "__main__":
    main()
