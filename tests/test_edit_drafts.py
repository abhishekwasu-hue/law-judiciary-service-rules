"""tools/edit_drafts.py (सुधारणा-चॅट, docs/DRAFT_EDIT_DESIGN.md points 4-5 + Addendum A). No network: Supabase
(engine_supabase.http) and the Messages API (edit_drafts.post_json) / GR downloads (edit_drafts.download_url) are faked."""
import copy, json, os, re, sys, urllib.parse

import docx
import pymupdf
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import engine_supabase as E  # noqa: E402
import edit_drafts as ED  # noqa: E402

SPECS = os.path.join(ROOT, "samples", "specs")


def sample(name):
    return json.load(open(os.path.join(SPECS, name), encoding="utf-8"))


# ---------------------------------------------------------------- fake Supabase
class FakeSB:
    def __init__(self, case_id=7, run_id=70):
        self.case = {"id": case_id, "cr_no": "131", "cr_year": 2026, "subject": "विशेष वेतन", "desk": None}
        self.run = {"id": run_id, "case_id": case_id, "kind": "edit", "state": "queued", "warnings": []}
        self.files, self.objects, self.activity, self.patches, self.refused_patches = [], {}, [], [], []
        self.next_id = 100

    def add(self, kind, name, data, bucket="outputs", version=1):
        self.next_id += 1
        path = f"{self.case['id']}/{kind}/v{version}/{name}"
        self.objects[f"{bucket}/{path}"] = data
        row = {"id": self.next_id, "case_id": self.case["id"], "kind": kind, "original_name": name, "version": version,
               "storage_path": f"{bucket}/{path}", "created_at": f"2026-11-04T00:00:{self.next_id % 60:02d}"}
        self.files.append(row)
        return row

    def http(self, method, url, body=None, headers=None, raw=False):
        u = urllib.parse.urlparse(url)
        if "/storage/v1/object/" in u.path:
            key = urllib.parse.unquote(u.path.split("/storage/v1/object/", 1)[1])
            if method == "GET":
                return self.objects[key]
            if method == "POST":
                self.objects[key] = bytes(body); return None
            if method == "DELETE":
                self.objects.pop(key, None); return None
        table = u.path.split("/rest/v1/", 1)[1]
        q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        eq = lambda k: q.get(k, "").replace("eq.", "")
        if table == "runs":
            if method == "GET":
                return [copy.deepcopy(self.run)]
            if method == "PATCH":
                st = q.get("state", "")
                if st.startswith("in.(") and self.run.get("state") not in st[4:-1].split(","):   # L-F8 guard
                    self.refused_patches.append(body)
                    return [] if "return=representation" in str((headers or {}).get("Prefer")) else None
                self.patches.append(body); self.run.update(body)
                return [copy.deepcopy(self.run)] if "return=representation" in str((headers or {}).get("Prefer")) else None
        if table == "cases":
            if method == "GET":
                return [dict(self.case)]
            return None
        if table == "case_files":
            if method == "GET":
                rows = [f for f in self.files if str(f["case_id"]) == eq("case_id")]
                if "kind" in q:
                    rows = [f for f in rows if f["kind"] == eq("kind")]
                if q.get("order") == "version.desc":
                    rows = sorted(rows, key=lambda f: -f["version"])
                if "limit" in q:
                    rows = rows[: int(q["limit"])]
                return copy.deepcopy(rows)
            if method == "POST":
                self.next_id += 1
                self.files.append({**body, "id": self.next_id, "created_at": "2026-11-04T01:00:00"}); return None
        if table == "activity":
            self.activity.append(body); return None
        raise AssertionError(f"unexpected {method} {url}")


@pytest.fixture
def sb(monkeypatch):
    f = FakeSB()
    monkeypatch.setattr(E, "http", f.http)
    monkeypatch.setattr(E, "BASE", "https://sb.test")
    monkeypatch.setattr(E, "KEY", "k")
    monkeypatch.setattr(E, "CASE", str(f.case["id"]))
    monkeypatch.setattr(E, "RUN", str(f.run["id"]))
    monkeypatch.delenv("RUN_TOKEN", raising=False)
    monkeypatch.delenv("WORKER", raising=False)
    monkeypatch.setenv("EDIT_NO_SLEEP", "1")
    return f


def model_reply(ops, summary="बदल केला.", refuse="", usage=None):
    body = {"ops": [{"op": o[0], "path": o[1], "value_json": json.dumps(o[2], ensure_ascii=False) if len(o) > 2 else ""}
                    for o in ops], "summary": summary, "refuse": refuse}
    return {"model": "claude-sonnet-5-5", "stop_reason": "end_turn",
            "content": [{"type": "text", "text": json.dumps(body, ensure_ascii=False)}],
            "usage": usage or {"input_tokens": 10000, "output_tokens": 1000}}


class FakeAPI:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    def __call__(self, url, body, headers, timeout=900):
        self.calls.append({"url": url, "body": copy.deepcopy(body), "headers": dict(headers)})
        return 200, self.replies.pop(0)


def blank_pdf(path, n, text="पृष्ठ"):
    d = pymupdf.open()
    for i in range(n):
        p = d.new_page()
        p.insert_text((72, 100), f"Page {i + 1} sample line", fontsize=12)
    d.save(path)
    return path


def docx_text(path):
    return "\n".join(p.text for p in docx.Document(path).paragraphs) + "\n" + "\n".join(
        c.text for t in docx.Document(path).tables for r in t.rows for c in r.cells)


# ---------------------------------------------------------------- ops + path guard
PART = {"note": {"first": "अ सादर.", "paras": ["एक.", {"table": [["अ", "ब"]]}, "दोन."]}, "related": [{"heading": "h"}]}


def test_apply_replace_remove_insert():
    new, ch = ED.apply_ops(PART, [{"op": "replace", "path": "/note/paras/0", "value_json": '"नवीन."'},
                                  {"op": "insert", "path": "/note/paras/-", "value_json": '"तीन."'},
                                  {"op": "remove", "path": "/related/0"},
                                  {"op": "insert", "path": "/note/closing", "value_json": '"सबब, मान्यतेस्तव सादर."'}])
    assert new["note"]["paras"] == ["नवीन.", {"table": [["अ", "ब"]]}, "दोन.", "तीन."]
    assert new["related"] == [] and new["note"]["closing"].startswith("सबब")
    assert PART["note"]["paras"][0] == "एक."           # the original is never changed
    assert [c["op"] for c in ch] == ["replace", "insert", "remove", "insert"]
    w = ED.readable_changes(ch)
    assert w[0] == {"where": "टिप्पणी परि. 2", "before": "एक.", "after": "नवीन."}
    assert w[1]["where"].startswith("टिप्पणी परि. ") or "नवीन परिच्छेद" in w[1]["where"]
    assert w[2]["where"] == "संबंधित माहिती क्र. 1"


@pytest.mark.parametrize("path", ["/desk", "/", "/note", "/letter/intro", "/note/paras/9", "/note/paras/x",
                                  "note/first", "/note//first"])
def test_path_guard(path):
    with pytest.raises(ValueError):
        ED.apply_ops(PART, [{"op": "replace", "path": path, "value_json": '"x"'}])


def test_insert_existing_key_and_bad_json():
    with pytest.raises(ValueError):
        ED.apply_ops(PART, [{"op": "insert", "path": "/note/first", "value_json": '"x"'}])
    with pytest.raises(ValueError):
        ED.apply_ops(PART, [{"op": "replace", "path": "/note/first", "value_json": "{bad"}])


def test_where_labels_on_samples():
    s = sample("WP35697_2026_parawise_GP-letter.json")
    part = {"parawise": s["parawise"]}
    _, ch = ED.apply_ops(part, [{"op": "replace", "path": "/parawise/paras/3/remarks", "value_json": '"Denied."'}])
    assert ED.where_of(ch[0]).startswith("परिच्छेदनिहाय उत्तर — Para ")
    s = sample("CR131_2026_special-pay_info-letter.json")
    _, ch = ED.apply_ops({"letter": s["letter"]}, [{"op": "replace", "path": "/letter/subject", "value_json": '"x"'}])
    assert ED.where_of(ch[0]) == "पत्र — विषय"


def test_quote_guard():
    part = {"note": {"paras": ["GR मध्ये “मूळ उतारा येथे आहे” असे नमूद आहे."]}}
    _, ch = ED.apply_ops(part, [{"op": "replace", "path": "/note/paras/0",
                                 "value_json": '"GR मध्ये “बदललेला उतारा” असे नमूद आहे."'}])
    assert ED.quote_problems(ch, "परिच्छेद लहान करा")
    assert not ED.quote_problems(ch, "“मूळ उतारा येथे आहे” हा उतारा बदला")


# ---------------------------------------------------------------- target -> keys / outputs on the real samples
@pytest.mark.parametrize("fname,target,keys", [
    ("CR131_2026_special-pay_info-letter.json", "letter", ["letter"]),
    ("CR131_2026_special-pay_info-letter.json", "note", ["note", "related"]),
    ("WP35697_2026_parawise_GP-letter.json", "parawise", ["parawise"]),
    ("HTE_2026_overpayment-waiver_finance-concurrence.json", "order", ["orders"]),
    ("ORDER_gr_example.json", "order", ["order"]),
    ("COURT_affidavit_example.json", "affidavit", ["affidavit"]),
    ("LQ_answer_example.json", "lq", ["lq"])])
def test_target_keys_exist_in_samples(fname, target, keys):
    s = sample(fname)
    got = [k for k in ED.TARGET_KEYS[target] if k in s and s[k] not in (None, "", [], {})]
    assert got == keys


def test_affected_kinds():
    have = {"note_letter": 1, "parawise": 1, "affidavit": 1}
    assert ED.affected_kinds({"parawise"}, have) == ["parawise", "affidavit"]   # affidavit reply = parawise.paras
    assert ED.affected_kinds({"letter"}, have) == ["note_letter"]
    assert ED.affected_kinds({"orders"}, have) == []


def test_new_lint_errors_ignore_old_ones():
    before = ["note.paras[3]: banned word — 'कदाचित'"]
    after = ["note.paras[4]: banned word — 'कदाचित'", "letter.intro: §4.19 — 'करुन'"]
    assert ED.new_lint_errors(before, after) == ["letter.intro: §4.19 — 'करुन'"]


def test_cost_from_usage():
    r = {"model": "claude-sonnet-5-5", "usage": {"input_tokens": 1_000_000, "output_tokens": 100_000}}
    assert abs(ED.cost_of(r, "claude-sonnet-5-5") - 3.0) < 1e-9          # 2 + 1 $
    assert abs(ED.cost_of({"model": "claude-sonnet-5", "usage": r["usage"]}, "x") - 3.0) < 1e-9


# ---------------------------------------------------------------- full dry pipeline (CR131 note + letter)
def seed_cr131(sb, tmp_path, pages=20):
    spec = sample("CR131_2026_special-pay_info-letter.json")
    nl = sb.add("note_letter", "CR131_2026_Note_and_Letter.docx", b"old docx")
    pkg = blank_pdf(str(tmp_path / "pkg.pdf"), pages)
    sb.add("package_pdf", "प्रस्ताव CR131.pdf", open(pkg, "rb").read())
    # a full run stores the spec AFTER its outputs (tools/engine_supabase.py finish; L-F7 compares the row ids)
    sb.add("spec", "spec.json", json.dumps(spec, ensure_ascii=False).encode("utf-8"))
    return spec, nl


def test_full_pipeline_letter_edit(sb, tmp_path, monkeypatch):
    spec, nl = seed_cr131(sb, tmp_path)
    old = spec["letter"]["intro"]
    new = old.replace("सदर प्रकरणी पुढील कार्यवाहीसाठी", "सदर प्रकरणी पुढील आवश्यक कार्यवाहीसाठी")
    assert new != old
    sb.run.update({"edit_target": "letter", "edit_message": "पत्राच्या सुरुवातीत 'आवश्यक' हा शब्द जोडा"})
    api = FakeAPI([model_reply([("replace", "/letter/intro", new)], "पत्राच्या प्रारंभात 'आवश्यक' शब्द जोडला.")])
    monkeypatch.setattr(ED, "post_json", api)
    er = ED.run_edit(str(tmp_path / "w"), api_key="sk-test", model="claude-sonnet-5-5")
    # the model got only the letter (+ context), structured output, no temperature
    body = api.calls[0]["body"]
    sent = body["messages"][0]["content"]
    assert '"letter"' in sent and '"note"' not in sent.split("The part")[1].split("Message")[0]
    assert body["output_config"]["format"]["type"] == "json_schema" and "temperature" not in body
    assert api.calls[0]["headers"]["anthropic-version"] == "2023-06-01"
    # new versions uploaded, old ones kept
    nls = [f for f in sb.files if f["kind"] == "note_letter"]
    assert sorted(f["version"] for f in nls) == [1, 2]
    assert all(f["original_name"] == "CR131_2026_Note_and_Letter.docx" for f in nls)
    v2 = next(f for f in nls if f["version"] == 2)
    out = tmp_path / "v2.docx"
    out.write_bytes(sb.objects[v2["storage_path"]])
    txt = docx_text(str(out))
    assert "पुढील आवश्यक कार्यवाहीसाठी" in txt
    specs = [f for f in sb.files if f["kind"] == "spec" and f["original_name"] == "spec.json"]
    assert sorted(f["version"] for f in specs) == [1, 2]
    s2 = json.loads(sb.objects[next(f for f in specs if f["version"] == 2)["storage_path"]])
    assert s2["letter"]["intro"] == new and s2["note"] == spec["note"]
    # run done with the edit result
    assert sb.run["state"] == "done" and sb.run["summary"].startswith("पत्राच्या")
    r = sb.run["edit_result"]
    assert r["files"] == ["note_letter"] and r["changes"][0]["where"] == "पत्र — प्रारंभ"
    assert r["changes"][0]["before"] == old and r["changes"][0]["after"] == new
    assert abs(r["cost_usd"] - 0.03) < 1e-6 and sb.run["cost_usd"] == r["cost_usd"]
    assert er == r


def test_note_para_edit_shows_in_docx(sb, tmp_path, monkeypatch):
    spec, _ = seed_cr131(sb, tmp_path)
    p0 = spec["note"]["paras"][0]
    new = p0.replace("पुढील कार्यवाहीसाठी व मान्यतेस्तव", "पुढील कार्यवाहीसाठी")
    assert new != p0
    sb.run.update({"edit_target": "note", "edit_message": "परि. 2 मधून 'व मान्यतेस्तव' काढा"})
    monkeypatch.setattr(ED, "post_json", FakeAPI([model_reply([("replace", "/note/paras/0", new)])]))
    ED.run_edit(str(tmp_path / "w"), api_key="sk", model="claude-sonnet-5-5")
    v2 = next(f for f in sb.files if f["kind"] == "note_letter" and f["version"] == 2)
    (tmp_path / "n.docx").write_bytes(sb.objects[v2["storage_path"]])
    t = docx_text(str(tmp_path / "n.docx"))
    assert new.split(" (पृ.")[0][:60] in t and "कार्यवाहीसाठी व मान्यतेस्तव शासनास" not in t
    assert sb.run["edit_result"]["changes"][0]["where"] == "टिप्पणी परि. 2"


def test_refusal_changes_nothing(sb, tmp_path, monkeypatch):
    seed_cr131(sb, tmp_path)
    sb.run.update({"edit_target": "note", "edit_message": "नवीन GR शोधून नोंदीत जोडा"})
    monkeypatch.setattr(ED, "post_json", FakeAPI([model_reply([], "", "नवीन GR साठी 'पुन्हा तयार करा' वापरा.")]))
    with pytest.raises(ED.Refused) as ex:
        ED.run_edit(str(tmp_path / "w"), api_key="sk", model="claude-sonnet-5-5")
    n_files = len(sb.files)
    ED.finish_refused(*ex.value.args)
    assert len(sb.files) == n_files and sb.run["state"] == "done"
    assert sb.run["edit_result"]["refused"].startswith("नवीन GR") and sb.run["edit_result"]["files"] == []
    assert sb.run["edit_result"]["cost_usd"] > 0


def test_partly_out_of_scope_still_edits(sb, tmp_path, monkeypatch):
    """Live 04.11.2026: "remove the letter no. from para 1 … apply this in all future proposals" came back refused and
    the note was not changed. Ops + refuse -> the ops are applied, the reason is kept as a note."""
    spec, _ = seed_cr131(sb, tmp_path)
    p0 = spec["note"]["paras"][0]
    new = p0.replace("पुढील कार्यवाहीसाठी व मान्यतेस्तव", "पुढील कार्यवाहीसाठी")
    sb.run.update({"edit_target": "note", "edit_message": "परि. 2 मधून 'व मान्यतेस्तव' काढावे; पुढील सर्व प्रस्तावांत लागू करावे"})
    monkeypatch.setattr(ED, "post_json", FakeAPI([model_reply([("replace", "/note/paras/0", new)], "बदल करण्यात आला आहे.",
                                                              "पुढील प्रस्तावांसाठीची सूचना या सुविधेच्या कक्षेबाहेर आहे.")]))
    ED.run_edit(str(tmp_path / "w"), api_key="sk", model="claude-sonnet-5-5")
    er = sb.run["edit_result"]
    assert sb.run["state"] == "done" and "refused" not in er and er["changes"]
    assert any("कक्षेबाहेर" in n for n in er["notes"])
    assert any(f["kind"] == "note_letter" and f["version"] == 2 for f in sb.files)


def test_lint_retry_then_ok(sb, tmp_path, monkeypatch):
    spec, _ = seed_cr131(sb, tmp_path)
    old = spec["letter"]["intro"]
    bad = old.replace("उपलब्ध करून", "उपलब्ध करुन")       # §4.19 error
    api = FakeAPI([model_reply([("replace", "/letter/intro", bad)]),
                   model_reply([("replace", "/letter/intro", old.replace("शासनास", "शासनास कृपया"))])])
    monkeypatch.setattr(ED, "post_json", api)
    sb.run.update({"edit_target": "letter", "edit_message": "'कृपया' जोडा"})
    ED.run_edit(str(tmp_path / "w"), api_key="sk", model="claude-sonnet-5-5")
    assert len(api.calls) == 2
    retry = api.calls[1]["body"]["messages"]
    assert retry[1]["role"] == "assistant" and "करुन" in retry[2]["content"]
    assert sb.run["state"] == "done" and abs(sb.run["edit_result"]["cost_usd"] - 0.06) < 1e-6


def test_lint_retry_fails(sb, tmp_path, monkeypatch):
    spec, _ = seed_cr131(sb, tmp_path)
    bad = spec["letter"]["intro"].replace("उपलब्ध करून", "उपलब्ध करुन")
    monkeypatch.setattr(ED, "post_json", FakeAPI([model_reply([("replace", "/letter/intro", bad)])] * 2))
    sb.run.update({"edit_target": "letter", "edit_message": "बदल"})
    n = len(sb.files)
    with pytest.raises(ED.EditFail, match="सुधारणा नियमांत बसली नाही"):
        ED.run_edit(str(tmp_path / "w"), api_key="sk", model="claude-sonnet-5-5")
    assert len(sb.files) == n


def test_no_spec_fails(sb, tmp_path):
    sb.run.update({"edit_target": "note", "edit_message": "x"})
    with pytest.raises(ED.EditFail, match="सुधारणा-फाइल नाही"):
        ED.run_edit(str(tmp_path / "w"), api_key="sk")


# ---------------------------------------------------------------- package (Addendum A)
def seed_package(sb, tmp_path):
    """proposal (3 pages) + one repo GR enclosure (pdf/gr) built with pkg3; a highlight added afterwards (highlight.py)."""
    spec = sample("CR131_2026_special-pay_info-letter.json")
    sb.add("note_letter", "CR131_2026_Note_and_Letter.docx", b"old")
    prop = blank_pdf(str(tmp_path / "prop.pdf"), 3)
    sb.add("proposal", "11ae057d-प्रस्ताव.pdf", open(prop, "rb").read(), bucket="inputs")
    gr = sorted(f for f in os.listdir(os.path.join(ROOT, "pdf", "gr")) if f.endswith(".pdf"))[0]
    encs = [{"path": f"pdf/gr/{gr}", "pages": "1", "label": "वित्त विभाग GR"}]
    ej = tmp_path / "encs.json"; ej.write_text(json.dumps(encs, ensure_ascii=False), encoding="utf-8")
    import subprocess
    old = tmp_path / "प्रस्ताव.pdf"
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "pkg3.py"), prop, str(ej), str(old)], cwd=ROOT,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    d = pymupdf.open(str(old))
    pg3 = d[3]
    h = pg3.add_highlight_annot(pymupdf.Rect(72, 90, 300, 110)); h.update()
    d.saveIncr(); n = len(d); d.close()
    sb.add("package_pdf", "प्रस्ताव.pdf", old.read_bytes())
    sb.add("spec", "spec.json", json.dumps(spec, ensure_ascii=False).encode("utf-8"))
    sb.add("spec", "enclosures.json", json.dumps(encs, ensure_ascii=False).encode("utf-8"))
    return n


def test_package_attach_only(sb, tmp_path, monkeypatch):
    n_old = seed_package(sb, tmp_path)
    img = pymupdf.open(); pg = img.new_page(width=300, height=400); pg.insert_text((50, 50), "attached image")
    png = pg.get_pixmap().tobytes("png")
    a1 = sb.add("extra_doc", "उत्तर-पत्र.png", png, bucket="inputs")
    a2 = sb.add("extra_doc", "टिप्पणी.docx", b"PK\x03\x04 word", bucket="inputs")
    code = "202401011234567890"
    gr_pdf = blank_pdf(str(tmp_path / "g.pdf"), 2)
    monkeypatch.setattr(ED, "download_url", lambda u, timeout=120: open(gr_pdf, "rb").read())
    import prep_pages
    monkeypatch.setattr(ED.shutil, "which", lambda x: None)          # ubuntu-latest: no LibreOffice
    monkeypatch.setattr(prep_pages.shutil, "which", lambda x: None)
    api = FakeAPI([])
    monkeypatch.setattr(ED, "post_json", api)
    sb.run.update({"edit_target": "package", "edit_message": f"हे पत्र व GR {code} जोडा",
                   "edit_attachments": [a1["id"], a2["id"]]})
    er = ED.run_edit(str(tmp_path / "w"), api_key="sk")
    assert api.calls == [] and er["cost_usd"] == 0                       # attach-only: no model call
    assert er["attached"] == [{"title": "उत्तर-पत्र", "pages": f"पृ.{n_old + 1}/प.वि."},
                              {"title": f"शासन निर्णय (सांकेतांक {code})", "pages": f"पृ.{n_old + 2}-{n_old + 3}/प.वि."}]
    assert any("PDF करून जोडावी, ही विनंती" in x for x in er["notes"]) and er["files"] == ["package_pdf"]
    pk = [f for f in sb.files if f["kind"] == "package_pdf"]
    v2 = max(pk, key=lambda f: f["version"])
    assert v2["version"] == 2 and v2["original_name"] == "प्रस्ताव.pdf"
    p = tmp_path / "new.pdf"; p.write_bytes(sb.objects[v2["storage_path"]])
    d = pymupdf.open(str(p))
    assert len(d) == n_old + 3
    assert f"पृ. 1 / {n_old + 3}" in d[0].get_text() and len(list(d[3].annots())) == 1   # old highlight kept
    assert not list(d[0].annots())
    toc = [t[1] for t in d.get_toc()]
    assert "उत्तर-पत्र" in toc and d.metadata.get("producer", "") == ""
    sp = [f for f in sb.files if f["kind"] == "spec"]
    v = max(f["version"] for f in sp)
    newest = {f["original_name"] for f in sp if f["version"] == v}
    assert newest == {"spec.json", "enclosures.json"}                  # one version for both
    enc = json.loads(sb.objects[next(f for f in sp if f["version"] == v and f["original_name"] == "enclosures.json")["storage_path"]])
    assert enc[0]["path"].startswith("pdf/gr/") and enc[1]["case_file_id"] == a1["id"] and enc[2]["gr_code"] == code


def test_package_old_case_refused(sb, tmp_path):
    seed_cr131(sb, tmp_path)
    a = sb.add("extra_doc", "x.pdf", open(blank_pdf(str(tmp_path / "x.pdf"), 1), "rb").read(), bucket="inputs")
    sb.add("proposal", "p.pdf", open(blank_pdf(str(tmp_path / "p.pdf"), 1), "rb").read(), bucket="inputs")
    sb.run.update({"edit_target": "package", "edit_message": "जोडा", "edit_attachments": [a["id"]]})
    with pytest.raises(ED.Refused, match="जुने प्रकरण"):
        ED.run_edit(str(tmp_path / "w"), api_key="sk")


def test_package_with_note_edit_gets_page_ranges(sb, tmp_path, monkeypatch):
    n_old = seed_package(sb, tmp_path)
    a = sb.add("extra_doc", "उत्तर.pdf", open(blank_pdf(str(tmp_path / "u.pdf"), 1), "rb").read(), bucket="inputs")
    spec = sample("CR131_2026_special-pay_info-letter.json")
    paras = spec["note"]["paras"]
    newp = f"त्यानंतर प्राप्त उत्तर पृ.{n_old + 1}/प.वि. वर आहे."
    api = FakeAPI([model_reply([("insert", f"/note/paras/{len(paras) - 1}", newp)], "नवीन परिच्छेद जोडला.")])
    monkeypatch.setattr(ED, "post_json", api)
    sb.run.update({"edit_target": "note", "edit_message": "जोडलेल्या उत्तराचा उल्लेख करा", "edit_attachments": [a["id"]]})
    er = ED.run_edit(str(tmp_path / "w"), api_key="sk", model="claude-sonnet-5-5")
    sent = api.calls[0]["body"]["messages"][0]["content"]
    assert f"उत्तर: पृ.{n_old + 1}/प.वि." in sent and f"1-{n_old + 1}" in sent and "Page 1 sample line" in sent
    assert set(er["files"]) == {"package_pdf", "note_letter"}
    assert er["changes"][0]["after"] == newp and "नवीन परिच्छेद" in er["changes"][0]["where"]


def test_gr_code_regex_only_16_to_18_digits():
    assert ED.GR_CODE_RE.findall("GR 202401011234567890 व 12345 व 2024010112345678901234") == ["202401011234567890"]


# ---------------------------------------------------------------- respectful chat language (Abhi 04.11.2026)
IMPERATIVE = re.compile(r"(?<![ऀ-ॿ])(करा|वापरा|पाठवा|लिहा|जोडा|तपासा|निवडा|द्या|बघा|पहा)(?![ऀ-ॿ])")


def marathi_literals():
    import ast
    src = open(os.path.join(ROOT, "tools", "edit_drafts.py"), encoding="utf-8").read()
    out = []
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and re.search(r"[ऀ-ॿ]", node.value):
            out.append(node.value)
    for line in open(os.path.join(ROOT, ".github", "workflows", "edit-drafts.yml"), encoding="utf-8"):
        out += re.findall(r'R="([^"]+)"', line) + re.findall(r'echo "([^"]*[ऀ-ॿ][^"]*)"', line)
    return out


def test_fixed_strings_are_respectful():
    lits = [s for s in marathi_literals() if s not in (ED.SYSTEM,) and not s.startswith(("edit_drafts.py", "the "))]
    assert len(lits) > 30
    bad = [s for s in lits if IMPERATIVE.search(s.replace("'पुन्हा तयार करा'", ""))]
    assert bad == []
    assert "कृपया" in ED.SYSTEM and "ही विनंती" in ED.SYSTEM and "आपण" in ED.SYSTEM


# ---------------------------------------------------------------- audit 05.11.2026 fixes
def test_stale_spec_refused(sb, tmp_path, monkeypatch):
    """L-F7: the last full run's spec upload failed (its note_letter is newer than the newest spec) -> refused, no model
    call, nothing uploaded."""
    seed_cr131(sb, tmp_path)
    sb.add("note_letter", "CR131_2026_Note_and_Letter.docx", b"newer docx", version=2)
    sb.run.update({"edit_target": "letter", "edit_message": "पत्रात बदल करावा"})
    api = FakeAPI([])
    monkeypatch.setattr(ED, "post_json", api)
    n = len(sb.files)
    with pytest.raises(ED.Refused) as ex:
        ED.run_edit(str(tmp_path / "w"), api_key="sk", model="claude-sonnet-5-5")
    assert ex.value.args[0] == ED.STALE_SPEC and "कृपया" in ED.STALE_SPEC and api.calls == [] and len(sb.files) == n


def test_spec_records_run_and_order(sb, tmp_path, monkeypatch):
    """L-F7: the edit's own spec is stored under …/spec/v<n>/r<run>/ and after its outputs (so the next edit is not stale)."""
    spec, _ = seed_cr131(sb, tmp_path)
    new = spec["letter"]["intro"].replace("सदर प्रकरणी", "सदर प्रकरणी आवश्यक")
    sb.run.update({"edit_target": "letter", "edit_message": "पत्रात 'आवश्यक' शब्द जोडावा"})
    monkeypatch.setattr(ED, "post_json", FakeAPI([model_reply([("replace", "/letter/intro", new)])]))
    ED.run_edit(str(tmp_path / "w"), api_key="sk", model="claude-sonnet-5-5")
    sp = max((f for f in sb.files if f["kind"] == "spec" and f["original_name"] == "spec.json"), key=lambda f: f["version"])
    nl = max((f for f in sb.files if f["kind"] == "note_letter"), key=lambda f: f["version"])
    assert f"/spec/v{sp['version']}/r{sb.run['id']}/spec.json" in sp["storage_path"] and sp["id"] > nl["id"]
    assert ED.spec_run_of(sp) == sb.run["id"] and not ED.stale_spec(sp, nl)


def test_closed_run_not_resurrected(sb, tmp_path, monkeypatch):
    """L-F8: a run already failed (sweep / cancel) is never set running / done; nothing is done."""
    seed_cr131(sb, tmp_path)
    sb.run.update({"state": "failed", "step": "मूळ कारण", "edit_target": "letter", "edit_message": "बदल"})
    api = FakeAPI([])
    monkeypatch.setattr(ED, "post_json", api)
    assert ED.run_edit(str(tmp_path / "w"), api_key="sk", model="claude-sonnet-5-5") is None
    assert sb.run["state"] == "failed" and sb.run["step"] == "मूळ कारण" and api.calls == [] and sb.refused_patches
    ED.finish_refused("कारण")
    assert sb.run["state"] == "failed"
    ED.step("सुधारणा: प्रगती")
    assert sb.run["step"] == "मूळ कारण"


def test_step_direct_to_supabase(sb, monkeypatch):
    """L-F1: with the service key the edit job writes the step itself (the Worker route was blocked by Cloudflare 1010)."""
    monkeypatch.setenv("RUN_TOKEN", "rt"); monkeypatch.setenv("WORKER", "https://worker.test")
    called = []
    monkeypatch.setattr(E, "cmd_step_worker", lambda t: called.append(t))
    sb.run["state"] = "running"
    ED.step("सुधारणा: तपासणी करण्यात येत आहे")
    assert sb.run["step"] == "सुधारणा: तपासणी करण्यात येत आहे" and called == []
    monkeypatch.setattr(E, "KEY", None)
    ED.step("x")
    assert called == ["x"]


def test_user_agent_on_http(monkeypatch):
    """L-F1: Supabase / Worker calls carry User-Agent prastav-kaksha-engine/1 (Python's default UA -> Cloudflare 1010)."""
    seen = []

    class R:
        status = 200
        def read(self): return b"[]"
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake(req, timeout=0):
        seen.append(req.get_header("User-agent")); return R()
    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    monkeypatch.setattr(E, "KEY", "k")
    E.http("GET", "https://sb.test/rest/v1/runs")
    monkeypatch.setenv("RUN_TOKEN", "rt"); monkeypatch.setenv("WORKER", "https://worker.test"); monkeypatch.setenv("RUN_ID", "5")
    E.cmd_step_worker("प्रगती")
    assert seen == [E.USER_AGENT, E.USER_AGENT] and E.USER_AGENT == "prastav-kaksha-engine/1"


def test_note_edit_quote_mismatch_warned(sb, tmp_path, monkeypatch, capsys):
    """Q-F20: a note edit that brings in a quote not on its cited page -> a soft warning (Study / app) and a note; the
    Actions log carries no case text (S-F3)."""
    spec, _ = seed_cr131(sb, tmp_path)
    d = pymupdf.open()   # a package whose page 2 has a usable text layer (>= 50 characters)
    for i in range(20):
        d.new_page().insert_text((72, 100), f"Page {i + 1}: the government resolution text of this page is printed here.", fontsize=10)
    pk = tmp_path / "pk.pdf"; d.save(str(pk)); d.close()
    sb.objects[next(f for f in sb.files if f["kind"] == "package_pdf")["storage_path"]] = pk.read_bytes()
    q = "This sentence of the order is certainly not printed on the cited page"   # Latin: the blank pages' text layer
    p0 = spec["note"]["paras"][0]
    new = p0 + " सदर शासन निर्णयात “" + q + "” अशी तरतूद आहे (पृ.2/प.वि.)."
    sb.run.update({"edit_target": "note", "edit_message": "परि. 2 मध्ये “" + q + "” हा उतारा जोडावा"})
    monkeypatch.setattr(ED, "post_json", FakeAPI([model_reply([("replace", "/note/paras/0", new)], "उतारा जोडण्यात आला आहे.")]))
    ED.run_edit(str(tmp_path / "w"), api_key="sk", model="claude-sonnet-5-5")
    w = [x for x in sb.run["warnings"] if "टिप्पणीतील अवतरणे" in x]
    assert w and w[0].startswith("पडताळणी अपूर्ण — ") and "टिप्पणी परि." in w[0]
    assert ED.QUOTE_NOTE in sb.run["edit_result"]["notes"]
    out = capsys.readouterr()
    assert "उतारा जोडण्यात" not in out.out and q not in out.out + out.err and "edit done:" in out.out


def test_labels_and_system_rule():
    """R-F20: the fallback label is टिप्पणी; the SYSTEM prompt keeps para 1 free of a letter number (§4.29(1))."""
    st = {"note": {"paras": []}}
    assert ED.where_of({"toks": ["note", "other"], "state": st, "op": "replace"}) == "टिप्पणी"
    assert "§4.29(1)" in ED.SYSTEM and "never\n   carries a letter number" in ED.SYSTEM and "authority, date and पृ.N/प.वि. only" in ED.SYSTEM
