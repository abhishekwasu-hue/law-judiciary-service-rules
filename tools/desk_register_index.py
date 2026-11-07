#!/usr/bin/env python3
"""desk_register_index.py — register/*.md -> one JSON index for the प्रस्ताव कक्ष page's register search (artifact mode).

Usage: python tools/desk_register_index.py <out.json>
Output: [{"path": "register/<file>.md", "title": first "# " heading or file name, "text": full text}], sorted by path.
The page stores it as an asset (db doc meta/register_index {asset}) and searches it client-side (dashboard-app artifact mode).
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def build(root=ROOT):
    out = []
    reg = os.path.join(root, "register")
    for fn in sorted(os.listdir(reg)):
        if not fn.endswith(".md"):
            continue
        text = open(os.path.join(reg, fn), encoding="utf-8").read()
        title = next((l[2:].strip() for l in text.splitlines() if l.startswith("# ")), fn[:-3])
        out.append({"path": f"register/{fn}", "title": title, "text": text})
    return out


def main(argv):
    if len(argv) != 1:
        sys.exit(__doc__)
    data = build()
    with open(argv[0], "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"{len(data)} files -> {argv[0]} ({os.path.getsize(argv[0])} bytes)")


if __name__ == "__main__":
    main(sys.argv[1:])
