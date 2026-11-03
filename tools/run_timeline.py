#!/usr/bin/env python3
"""run_timeline.py — where the time of a headless Claude Code run goes (stdlib only; runner side, never fails the job).
Abhi 03.11.2026 ("हो जोडा"): the last live run's Claude step took 36.5 min and the job log could not show which
subagent / stage took the time.

  stamp <out.tsv> <result.json>
      stdin filter for `claude -p … --output-format stream-json --verbose`: every stdout line is written to <out.tsv>
      as "<runner epoch seconds, ms>\\t<line>" (large base64 image data inside a line is shortened to "<b64 N>", only in
      the .tsv); every {"type":"result",…} line is written UNCHANGED (atomic replace) to <result.json>, so the file
      holds the last result line = what `--output-format json` prints (Claude Code 2.1.300: json prints the last
      result message; its keys equal the stream's result line). <out.tsv>.eof is touched at end of input. Any error
      inside the filter only stops the .tsv writing: stdin is always read to the end (the CLI never gets SIGPIPE).
  report <timeline.json> <label>=<stream.tsv> [<label>=<stream.tsv> …] [--agents <agents.json>] [--line <file>]
      prints, per stream: total time (first..last line, and the result's duration_ms / duration_api_ms, num_turns,
      total_cost_usd); one row per subagent call (Agent/Task tool_use: subagent_type, description, start/end offset,
      duration, model, turns, tool uses, image reads; background agents end at their task_notification / last own
      message); the 10 slowest other tool calls (Bash command first 80 chars, Read path); Read calls of images per
      owner; assistant turns per model (main / subagents); the result's modelUsage per model (tokens, cost).
      Writes everything to <timeline.json>; --line writes ONE short "मॉडेल: वेळ — …" line (first stream) for
      engine_supabase.py note. Missing / garbled lines are skipped; exit 0 always.
  stages <stages.tsv> <job_t0> [<timeline.json>]
      the "वेळ-तक्ता" at the end of the job: one row per runner step from <stages.tsv> lines
      "<name>\\t<start epoch>\\t<end epoch>", the rest of the job since <job_t0> (set-up, install, queue), and the
      subagent rows of <timeline.json>. Exit 0 always.
"""
import json, os, re, sys, time

AGENT_TOOLS = ("Agent", "Task")
IMG_EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif")
B64_RE = re.compile(rb'"(data|base64)":"([A-Za-z0-9+/=]{2000,})"')
SECRET_RE = re.compile(r"(sk-[A-Za-z0-9_-]{8,}|[A-Za-z0-9_\-]{40,})")


# ---------------------------------------------------------------- stamp
def _short_b64(m):
    return b'"' + m.group(1) + b'":"<b64 ' + str(len(m.group(2))).encode() + b'>"'


def cmd_stamp(tsv, result_path):
    src = sys.stdin.buffer
    out = None
    try:
        out = open(tsv, "wb")
    except Exception as e:
        print("run_timeline stamp: cannot write", tsv, e, file=sys.stderr)
    tmp = result_path + ".part"
    for line in src:
        try:
            ts = b"%.3f" % time.time()
            body = line.rstrip(b"\r\n")
            if b'"type":"result"' in body or b'"type": "result"' in body:
                try:
                    o = json.loads(body.decode("utf-8", "replace"))
                except ValueError:
                    o = None
                if isinstance(o, dict) and o.get("type") == "result":
                    with open(tmp, "wb") as f:
                        f.write(body + b"\n")
                    os.replace(tmp, result_path)
            if out is not None:
                if len(body) > 4000:
                    body = B64_RE.sub(_short_b64, body)
                out.write(ts + b"\t" + body + b"\n")
                out.flush()
        except Exception as e:  # disk full, encoding …: keep reading, stop writing the .tsv
            print("run_timeline stamp:", e, file=sys.stderr)
            try:
                if out is not None: out.close()
            except Exception:
                pass
            out = None
    try:
        if out is not None: out.close()
        open(tsv + ".eof", "w").close()
    except Exception:
        pass


# ---------------------------------------------------------------- parse / analyse
def read_events(path):
    ev = []
    try:
        f = open(path, encoding="utf-8", errors="replace")
    except Exception:
        return ev
    with f:
        for line in f:
            ts, sep, body = line.partition("\t")
            if not sep:
                continue
            try:
                t = float(ts)
                o = json.loads(body)
            except ValueError:
                continue
            if isinstance(o, dict):
                ev.append((t, o))
    return ev


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def short_model(m):
    m = str(m or "")
    return re.sub(r"^claude-", "", m) or "?"


def detail(name, inp):
    inp = inp if isinstance(inp, dict) else {}
    if name == "Bash":
        d = str(inp.get("command") or "")
    elif name in ("Read", "Write", "Edit", "NotebookEdit"):
        d = str(inp.get("file_path") or inp.get("notebook_path") or "")
    elif name in ("Glob", "Grep"):
        d = str(inp.get("pattern") or "") + (" @ " + str(inp["path"]) if inp.get("path") else "")
    else:
        d = next((str(v) for v in inp.values() if isinstance(v, str)), "")
    d = " ".join(d.split())
    return SECRET_RE.sub("…", d)[:80]


def analyse(events, agent_models=None):
    agent_models = agent_models or {}
    out = {"lines": len(events)}
    if not events:
        return out
    t0, t1 = events[0][0], events[-1][0]
    tools, order, tasks_by_id = {}, [], {}
    child = {}          # parent_tool_use_id -> {"first", "last", "models": set, "turns": set}
    turns = {}          # (owner "main"/"sub", model) -> set(message ids)
    init = None
    res = None
    for ts, o in events:
        typ = o.get("type")
        pid = o.get("parent_tool_use_id")
        if pid:
            c = child.setdefault(pid, {"first": ts, "last": ts, "models": set(), "turns": set()})
            c["last"] = ts
        if typ == "system":
            st = o.get("subtype")
            if st == "init" and init is None:
                init = {"model": o.get("model"), "version": o.get("claude_code_version")}
            elif st == "task_started":
                tid = o.get("tool_use_id")
                tasks_by_id[o.get("task_id")] = tid
                if tid:
                    t = tools.setdefault(tid, {"name": "Agent", "input": {}, "start": ts, "parent": None})
                    t.update(task_start=ts, bg=o.get("is_backgrounded"))
                    t.setdefault("subagent_type", o.get("subagent_type"))
            elif st == "task_notification":
                tid = o.get("tool_use_id") or tasks_by_id.get(o.get("task_id"))
                if tid in tools:
                    u = o.get("usage") if isinstance(o.get("usage"), dict) else {}
                    tools[tid].update(notified=ts, task_status=o.get("status"), cli_ms=_num(u.get("duration_ms")) or tools[tid].get("cli_ms"),
                                      cli_tokens=_num(u.get("total_tokens")), cli_tool_uses=_num(u.get("tool_uses")))
        elif typ == "assistant":
            m = o.get("message") if isinstance(o.get("message"), dict) else {}
            model = m.get("model") or "?"
            mid = m.get("id") or o.get("uuid") or ts
            if model != "<synthetic>":
                turns.setdefault(("sub" if pid else "main", model), set()).add(mid)
            if pid:
                if model != "<synthetic>":
                    child[pid]["models"].add(model)
                child[pid]["turns"].add(mid)
            for c in m.get("content") or []:
                if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("id") and c["id"] not in tools:
                    tools[c["id"]] = {"name": c.get("name"), "input": c.get("input") if isinstance(c.get("input"), dict) else {},
                                      "start": ts, "parent": pid}
                    order.append(c["id"])
                elif isinstance(c, dict) and c.get("type") == "tool_use" and c.get("id") in tools:
                    t = tools[c["id"]]   # a task_started line came first
                    t.update(name=c.get("name"), input=c.get("input") if isinstance(c.get("input"), dict) else {},
                             start=min(t["start"], ts), parent=pid)
                    if c["id"] not in order: order.append(c["id"])
        elif typ == "user":
            m = o.get("message") if isinstance(o.get("message"), dict) else {}
            cont = m.get("content") if isinstance(m.get("content"), list) else []
            ids = [c.get("tool_use_id") for c in cont if isinstance(c, dict) and c.get("type") == "tool_result"]
            for tid in ids:
                t = tools.get(tid)
                if t is not None and t.get("end") is None:
                    t["end"] = ts
                    t["error"] = any(bool(c.get("is_error")) for c in cont if isinstance(c, dict) and c.get("tool_use_id") == tid)
            tur = o.get("tool_use_result")
            if len(ids) == 1 and isinstance(tur, dict) and ids[0] in tools:
                t = tools[ids[0]]
                for k_out, k_in in (("status", "status"), ("cli_ms", "totalDurationMs"), ("resolved_model", "resolvedModel"),
                                    ("models_used", "modelsUsed"), ("agent_type", "agentType"), ("cli_tool_uses", "totalToolUseCount"),
                                    ("cli_tokens", "totalTokens")):
                    if tur.get(k_in) is not None:
                        t[k_out] = tur[k_in]
        elif typ == "result":
            res = o
    out.update(t0=t0, t1=t1, total_s=round(t1 - t0, 1), init=init)
    if res:
        mu = res.get("modelUsage") if isinstance(res.get("modelUsage"), dict) else {}
        out["result"] = {k: res.get(k) for k in ("subtype", "is_error", "num_turns", "duration_ms", "duration_api_ms", "total_cost_usd",
                                                   "terminal_reason", "stop_reason") if k in res}
        out["model_usage"] = {m: {k: u.get(k) for k in ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens", "costUSD")
                                  if isinstance(u, dict) and k in u} for m, u in mu.items()}
        st = res.get("subagent_stats")
        if isinstance(st, dict):
            out["subagent_stats"] = {k: st.get(k) for k in ("spawned", "completed", "failed", "by_type") if k in st}

    def label(tid):
        t = tools.get(tid) or {}
        inp = t.get("input") or {}
        return str(inp.get("subagent_type") or t.get("agent_type") or t.get("subagent_type") or "agent")

    def owner(t):
        p = t.get("parent")
        return label(p) if p else "main"

    agents, others, img = [], [], {}
    for tid in order + [k for k in tools if k not in order]:
        t = tools[tid]
        if t.get("name") == "Read" and str((t.get("input") or {}).get("file_path") or "").lower().endswith(IMG_EXT):
            img[owner(t)] = img.get(owner(t), 0) + 1
        if t.get("name") in AGENT_TOOLS:
            inp = t.get("input") or {}
            c = child.get(tid) or {}
            bg = t.get("status") == "async_launched" or bool(t.get("bg")) or inp.get("run_in_background") is True
            if t.get("notified"):
                end, how = t["notified"], "notification"
            elif t.get("end") is not None and not (bg and t.get("status") != "completed"):
                end, how = t["end"], "result"
            elif c.get("last"):
                end, how = c["last"], "last message"
            else:
                end, how = t1, "not finished"
            models = [m for m in t.get("models_used") or [] if m] if isinstance(t.get("models_used"), list) else []
            if not models and t.get("resolved_model"):
                models = [t["resolved_model"]]
            if not models and c.get("models"):
                models = sorted(c["models"])
            if not models and (inp.get("model") or agent_models.get(label(tid))):
                models = [inp.get("model") or agent_models.get(label(tid))]
            model = ", ".join(short_model(m) for m in models) or "?"
            n_tools = sum(1 for x in tools.values() if x.get("parent") == tid)
            n_img = sum(1 for x in tools.values() if x.get("parent") == tid and x.get("name") == "Read"
                        and str((x.get("input") or {}).get("file_path") or "").lower().endswith(IMG_EXT))
            agents.append({"id": tid, "type": label(tid), "owner": owner(t), "description": " ".join(str(inp.get("description") or "").split())[:60],
                           "start_s": round(t["start"] - t0, 1), "end_s": round(end - t0, 1), "dur_s": round(end - t["start"], 1),
                           "end_by": how, "background": bg, "model": model, "turns": len(c.get("turns") or ()),
                           "tool_uses": n_tools if n_tools else t.get("cli_tool_uses"), "image_reads": n_img,
                           "cli_s": round(t["cli_ms"] / 1000, 1) if _num(t.get("cli_ms")) else None,
                           "status": t.get("task_status") or t.get("status") or ("error" if t.get("error") else None)})
        else:
            end = t.get("end")
            others.append({"name": t.get("name"), "owner": owner(t), "detail": detail(t.get("name"), t.get("input")),
                           "start_s": round(t["start"] - t0, 1), "dur_s": round((end if end is not None else t1) - t["start"], 1),
                           "finished": end is not None, "error": bool(t.get("error"))})
    others.sort(key=lambda x: -x["dur_s"])
    by_name = {}
    for x in others:
        b = by_name.setdefault(x["name"] or "?", {"calls": 0, "sum_s": 0.0})
        b["calls"] += 1; b["sum_s"] = round(b["sum_s"] + x["dur_s"], 1)
    out.update(agents=agents, slow_tools=others[:10], tool_totals=by_name, image_reads=img,
               turns=[{"owner": o, "model": m, "turns": len(s)} for (o, m), s in sorted(turns.items())])
    return out


# ---------------------------------------------------------------- printing
def mmss(s):
    if s is None:
        return "-"
    s = int(round(s))
    return f"{s // 60}:{s % 60:02d}"


def table(rows, head):
    rows = [[str(c) for c in r] for r in rows]
    w = [max(len(h), *(len(r[i]) for r in rows)) if rows else len(h) for i, h in enumerate(head)]
    print("  " + "  ".join(h.ljust(w[i]) for i, h in enumerate(head)))
    for r in rows:
        print("  " + "  ".join(c.ljust(w[i]) for i, c in enumerate(r)))


def print_stream(label, a):
    print(f"== {label}: वेळ-विभागणी / timeline ({a.get('lines', 0)} lines) ==")
    if not a.get("lines"):
        print("  (stream empty or missing)")
        return
    r = a.get("result") or {}
    dm, da = _num(r.get("duration_ms")), _num(r.get("duration_api_ms"))
    print(f"  एकूण वेळ / total: {mmss(a.get('total_s'))} (first..last line)"
          + (f"; duration_ms {mmss(dm / 1000)}" if dm is not None else "")
          + (f"; duration_api_ms {mmss(da / 1000)}" if da is not None else "")
          + (f"; num_turns {r.get('num_turns')}" if "num_turns" in r else "")
          + (f"; cost ${r['total_cost_usd']:.2f}" if _num(r.get("total_cost_usd")) is not None else "")
          + ("" if r else "; no result line"))
    if a.get("agents"):
        print("  subagents (Agent/Task):")
        table([[x["type"], x["description"], mmss(x["start_s"]), mmss(x["end_s"]), mmss(x["dur_s"]), x["model"], x["turns"],
                 x["tool_uses"] if x["tool_uses"] is not None else "-", x["image_reads"], mmss(x["cli_s"]),
                 ("bg/" if x["background"] else "") + x["end_by"], x["status"] or "-"] for x in a["agents"]],
              ["type", "description", "start", "end", "dur", "model", "turns", "tools", "img", "cli_dur", "end by", "status"])
    if a.get("slow_tools"):
        print("  10 slowest other tool calls:")
        table([[x["name"], x["owner"], mmss(x["start_s"]), mmss(x["dur_s"]) + ("" if x["finished"] else "+"),
                "ERR" if x["error"] else "", x["detail"]] for x in a["slow_tools"]],
              ["tool", "by", "start", "dur", "", "detail"])
    if a.get("tool_totals"):
        print("  tool totals: " + ", ".join(f"{k} {v['calls']}× {mmss(v['sum_s'])}" for k, v in
                                            sorted(a["tool_totals"].items(), key=lambda kv: -kv[1]["sum_s"])))
    if a.get("image_reads"):
        print("  image Reads: " + ", ".join(f"{k} {v}" for k, v in sorted(a["image_reads"].items())))
    if a.get("turns"):
        print("  assistant turns per model: " + ", ".join(f"{x['owner']}/{short_model(x['model'])} {x['turns']}" for x in a["turns"]))
    if a.get("model_usage"):
        print("  modelUsage (result):")
        table([[short_model(m), u.get("inputTokens", "-"), u.get("outputTokens", "-"), u.get("cacheReadInputTokens", "-"),
                u.get("cacheCreationInputTokens", "-"), f"${u['costUSD']:.2f}" if _num(u.get("costUSD")) is not None else "-"]
               for m, u in sorted(a["model_usage"].items(), key=lambda kv: -(_num(kv[1].get("costUSD")) or 0))],
              ["model", "input", "output", "cache_read", "cache_write", "cost"])


def summary_line(a):
    """One short Marathi line for runs.warnings ("मॉडेल:" = the UI's info prefix, not a warning)."""
    if not a.get("lines"):
        return ""
    tot = {}
    for x in a.get("agents") or []:
        tot[x["type"]] = tot.get(x["type"], 0.0) + x["dur_s"]
    parts = [f"{k} {v / 60:.1f}" for k, v in sorted(tot.items(), key=lambda kv: -kv[1])[:5]]
    tt = a.get("tool_totals") or {}
    b = tt.get("Bash")
    line = f"मॉडेल: वेळ — Claude एकूण {a.get('total_s', 0) / 60:.1f} मि"
    if parts:
        line += "; " + ", ".join(parts) + " मि"
    if b:
        line += f"; Bash {b['calls']}× {b['sum_s'] / 60:.1f} मि"
    img = sum((a.get("image_reads") or {}).values())
    if img:
        line += f"; प्रतिमा-वाचन {img}"
    return line[:300]


def cmd_report(args):
    out_json, line_file, agents_path, streams = None, None, None, []
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("--line", "--agents") and i + 1 < len(args):
            if a == "--line": line_file = args[i + 1]
            else: agents_path = args[i + 1]
            i += 2; continue
        if out_json is None:
            out_json = a
        elif "=" in a:
            streams.append(tuple(a.split("=", 1)))
        i += 1
    agent_models = {}
    if agents_path:
        try:
            d = json.load(open(agents_path, encoding="utf-8"))
            agent_models = {k: v.get("model") for k, v in d.items() if isinstance(v, dict) and v.get("model")}
        except Exception:
            agent_models = {}
    res, first_line = {}, None
    for lab, path in streams:
        if not os.path.exists(path):
            continue
        try:
            a = analyse(read_events(path), agent_models)
        except Exception as e:  # never fail the job
            print(f"run_timeline: {lab}: {e}", file=sys.stderr)
            continue
        res[lab] = a
        print_stream(lab, a)
        if first_line is None:
            first_line = summary_line(a)
    if out_json:
        try:
            json.dump(res, open(out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        except Exception as e:
            print("run_timeline: timeline.json not written:", e, file=sys.stderr)
    if line_file:
        try:
            open(line_file, "w", encoding="utf-8").write((first_line or "") + "\n")
        except Exception:
            pass
    if first_line:
        print(first_line)


def cmd_stages(args):
    path = args[0] if args else ""
    try:
        t0 = float(args[1])
    except (IndexError, ValueError):
        t0 = None
    rows = []
    try:
        for line in open(path, encoding="utf-8", errors="replace"):
            p = line.rstrip("\n").split("\t")
            if len(p) >= 3:
                try:
                    rows.append((p[0], float(p[1]), float(p[2])))
                except ValueError:
                    continue
    except Exception:
        pass
    now = time.time()
    print("== वेळ-तक्ता / stage times ==")
    used = sum(e - s for _, s, e in rows)
    tab = [[n, mmss(s - t0) if t0 else "-", mmss(e - s)] for n, s, e in rows]
    if t0:
        tab.append(["इतर (queue, setup, install, checks)", "-", mmss(max(0.0, now - t0 - used))])
        tab.append(["एकूण job (आतापर्यंत)", "0:00", mmss(now - t0)])
    table(tab, ["stage", "start", "dur"])
    if len(args) > 2 and os.path.exists(args[2]):
        try:
            d = json.load(open(args[2], encoding="utf-8"))
        except Exception:
            d = {}
        for lab, a in (d.items() if isinstance(d, dict) else []):
            if isinstance(a, dict) and a.get("agents"):
                print(f"  {lab}: " + "; ".join(f"{x['type']} {mmss(x['dur_s'])}" for x in a["agents"]))


def main(argv):
    try:
        if len(argv) >= 3 and argv[0] == "stamp":
            return cmd_stamp(argv[1], argv[2])
        if len(argv) >= 2 and argv[0] == "report":
            return cmd_report(argv[1:])
        if len(argv) >= 2 and argv[0] == "stages":
            return cmd_stages(argv[1:])
        print(__doc__)
    except Exception as e:
        print("run_timeline:", e, file=sys.stderr)
        if argv and argv[0] == "stamp":  # keep draining stdin
            try:
                for _ in sys.stdin.buffer: pass
            except Exception:
                pass


if __name__ == "__main__":
    main(sys.argv[1:])
    sys.exit(0)
