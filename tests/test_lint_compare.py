"""tools/lint_compare.py — a correction round fails only on lint errors the edit added (DESK_WORKER §4.3)."""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tools", "lint_compare.py")
SAMPLE = os.path.join(ROOT, "samples", "specs", "CR131_2026_special-pay_info-letter.json")
sys.path.insert(0, os.path.join(ROOT, "tools"))
import lint_compare as LC  # noqa: E402


def run(*a):
    return subprocess.run([sys.executable, TOOL, *a], cwd=ROOT, capture_output=True, text=True)


def spec(tmp_path, name, extra_paras=()):
    s = json.load(open(SAMPLE, encoding="utf-8"))
    s["note"]["paras"] = list(s["note"]["paras"]) + list(extra_paras)
    p = tmp_path / name
    json.dump(s, open(p, "w", encoding="utf-8"), ensure_ascii=False)
    return str(p)


BAD1 = "सदर प्रकरणी फाइल z6_0235 पाहावी."       # internal id -> lint error
BAD2 = "सदर प्रकरणी फाइल z7_0274 पाहावी."


def test_new_errors_multiset():
    assert LC.new_errors(["a", "b"], ["b", "a"]) == []
    assert LC.new_errors(["a"], ["a", "a", "c"]) == ["a", "c"]
    assert LC.new_errors(["p[3]: x"], ["p[4]: x"]) == []


def test_old_error_left_passes(tmp_path):
    b = spec(tmp_path, "b.json", [BAD1]); a = spec(tmp_path, "a.json", [BAD1])
    r = run(b, a)
    assert r.returncode == 0, r.stdout
    assert "LINT COMPARE OK" in r.stdout and "OLD-LEFT" in r.stdout


def test_new_error_fails(tmp_path):
    b = spec(tmp_path, "b.json", [BAD1]); a = spec(tmp_path, "a.json", [BAD1, BAD2])
    r = run(b, a)
    assert r.returncode == 1
    new = [l for l in r.stdout.splitlines() if l.startswith("NEW ")]
    assert any("z7_0274" in l for l in new) and not any("z6_0235" in l for l in new)


def test_index_shift_is_not_new(tmp_path):
    b = spec(tmp_path, "b.json", [BAD1])
    s = json.load(open(b, encoding="utf-8"))
    s["note"]["paras"].insert(1, "सदर प्रकरणी पुढील कार्यवाही करण्यात येत आहे.")   # old error moves to a higher index
    a = tmp_path / "a.json"; json.dump(s, open(a, "w", encoding="utf-8"), ensure_ascii=False)
    r = run(b, str(a))
    assert not any("z6_0235" in l for l in r.stdout.splitlines() if l.startswith("NEW ")), r.stdout


def test_clean_and_bad_args(tmp_path):
    b = spec(tmp_path, "b.json")
    assert run(b, b).returncode == 0
    assert run(b).returncode == 2
    assert run(b, str(tmp_path / "missing.json")).returncode == 2
