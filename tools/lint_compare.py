#!/usr/bin/env python3
"""lint_compare.py <spec_before.json> <spec_after.json> [--pages N]
Lint gate for a correction round (docs/DESK_WORKER.md §4.3): runs tools/lint_spec.py's checks (lint_spec + lint_extras,
the same set its command line runs) on both specs and passes when the after-spec has no error the before-spec did not
have — an old error the edit did not touch never blocks the edit. Errors are compared as their lines with the numeric
JSON-path indices left out ("note.paras[6]" = "note.paras[]"), so a paragraph inserted before an old error does not make
it new; a count per line is kept, so a second copy of an old error is new. Prints "NEW <error line>" for each new error (and, for the
log, "OLD-LEFT n" = old errors still present); "LINT COMPARE OK" and exit 0 when nothing is new, exit 1 otherwise,
exit 2 on bad arguments or an unreadable spec. WARN lines are not compared (they never fail lint either).
Run from the repo root (or anywhere: tools/ is put on sys.path).
"""
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def errors(spec, pages=None):
    import lint_spec as L
    probs = list(L.lint_spec(spec, pages))
    if hasattr(L, "lint_extras"):
        xp, _ = L.lint_extras(spec)
        probs += list(xp)
    return [str(p) for p in probs]


def new_errors(before, after):
    """[error lines of `after` not in `before`] (multiset difference, order of `after`)."""
    key = lambda e: re.sub(r"\[\d+\]", "[]", e)  # noqa: E731
    left = collections.Counter(key(e) for e in before)
    out = []
    for e in after:
        if left[key(e)] > 0:
            left[key(e)] -= 1
        else:
            out.append(e)
    return out


def main(argv):
    args = list(argv[1:]); pages = None
    if "--pages" in args:
        i = args.index("--pages")
        try:
            pages = int(args[i + 1])
        except (IndexError, ValueError):
            print(__doc__); return 2
        del args[i:i + 2]
    if len(args) != 2:
        print(__doc__); return 2
    try:
        b, a = (json.load(open(p, encoding="utf-8-sig")) for p in args)
    except Exception as e:
        print(f"lint_compare: spec not read — {e.__class__.__name__}: {e}"); return 2
    eb, ea = errors(b, pages), errors(a, pages)
    new = new_errors(eb, ea)
    for e in new:
        print("NEW " + e)
    old_left = len(ea) - len(new)
    if old_left:
        print(f"OLD-LEFT {old_left}")
    if new:
        print(f"LINT COMPARE: {len(new)} new error(s)"); return 1
    print("LINT COMPARE OK"); return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main(sys.argv))
