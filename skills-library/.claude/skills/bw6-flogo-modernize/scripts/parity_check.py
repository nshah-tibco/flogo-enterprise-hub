#!/usr/bin/env python3
"""Side-by-side parity check: send the same requests to a running BW6 app and its Flogo modernization.

Usage:
  python parity_check.py <cases.json> [--report <out.md>]

cases.json:
{
  "rest": {"bw": "http://<bw-host>:<bw-port>", "flogo": "http://localhost:<flogo-rest-port>",
           "headers": {"Authorization": "Bearer ..."},            optional, sent on every case (both sides)
           "cases": [{"name": "ok", "method": "GET", "path": "/api/x?a=1", "headers": {"X-Tenant": "t1"}},
                     {"name": "post", "method": "POST", "path": "/api/y", "body": {...}},
                     {"name": "extra_field", "method": "POST", "path": "/api/y", "body": {...},
                      "accept": "Flogo ignores unknown request fields; BW rejects them with 400"}]},
  "mcp":  {"bw": "http://<bw-host>:<bw-mcp-port>/rest/mcp", "flogo": "http://localhost:<flogo-mcp-port>/mcp",
           "tools": ["tool_a", "tool_b"],
           "calls": [{"name": "a_ok", "tool": "tool_a", "arguments": {...}}]}
}

Verdicts per case:
  MATCH      same status and identical JSON body (MCP: identical tool result JSON)
  EQUIVALENT identical except keys BW omits and Flogo sends as null (or the reverse)
  IMPROVED   BW failed badly (5xx, or a non-JSON error page) and Flogo answered with a JSON 4xx/5xx.
             A JSON 4xx from BW is a real answer and is compared like any other (status and body).
  ACCEPTED   a MISMATCH on a case that carries "accept": "<why>" - an intentional, documented deviation

Stateful operations (writes): give each side its OWN identical fixture - "flogoBody"/"flogoPath" override what
Flogo receives, and "normalize": {"<flogo fixture id>": "<bw fixture id>"} rewrites the Flogo response before
comparing. Cases run in file order, BW first, so later reads see both sides' writes. "ignore": ["$.items[*].id"]
drops values each side generates on its own (UUIDs, timestamps) before comparing.
  SEMANTIC   (cases with "semantic") same status, same response SHAPE (keys and JSON types, recursively), every
             expected fact found and every expected value present - for operations whose exact output cannot
             match (LLM answers, vector search scores/ids):
               "semantic": {"facts": {"$.answer": ["14 days"]},             # case-insensitive substrings
                            "values": {"$.citations[*].uri": ["policy://policy-electronics-returns"]},
                            "why": "OpenAI vector store + LLM instead of BW RAG/Weaviate"}
  MISMATCH   anything else -> exit code 1

Standard library only; uses urllib (curl may be blocked in agent shells).
"""
import argparse
import json
import re
import sys
import urllib.error
import urllib.request


def http(method, url, body=None, timeout=60, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    h = {"Content-Type": "application/json"} if data else {}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        status, raw, ctype = r.status, r.read(), r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        status, raw, ctype = e.code, e.read(), e.headers.get("Content-Type", "")
    except Exception as e:  # connection refused etc.
        return {"status": None, "json": None, "text": repr(e), "contentType": ""}
    text = raw.decode("utf-8", "replace")
    try:
        js = json.loads(text) if text.strip() else None
    except ValueError:
        js = None
    return {"status": status, "json": js, "text": None if js is not None else text[:300], "contentType": ctype}


def drop_paths(value, paths):
    """Remove generated values (ids, timestamps) before comparing: paths like $.messages[*].messageId or $.id."""
    for path in paths:
        parts = re.findall(r"\.([A-Za-z0-9_]+)|\[(\*|\d+)\]", path)
        def walk(node, i):
            if i == len(parts) or node is None:
                return
            key, idx = parts[i]
            last = i == len(parts) - 1
            if key:
                if isinstance(node, dict) and key in node:
                    if last:
                        node.pop(key)
                    else:
                        walk(node[key], i + 1)
            elif isinstance(node, list):
                for item in (node if idx == "*" else node[int(idx):int(idx) + 1]):
                    walk(item, i + 1)
        walk(value, 0)
    return value


def collect(value, path):
    """Values at a path like $.citations[*].uri (same syntax as drop_paths)."""
    parts = re.findall(r"\.([A-Za-z0-9_]+)|\[(\*|\d+)\]", path)
    nodes = [value]
    for key, idx in parts:
        nxt = []
        for n in nodes:
            if key and isinstance(n, dict) and key in n:
                nxt.append(n[key])
            elif not key and isinstance(n, list):
                nxt += n if idx == "*" else n[int(idx):int(idx) + 1]
        nodes = nxt
    return nodes


def shape(v):
    """Keys and JSON types, recursively; arrays by the union of their items' shapes (empty arrays are 'array')."""
    if isinstance(v, dict):
        return {k: shape(x) for k, x in v.items()}
    if isinstance(v, list):
        merged = {}
        for x in v:
            s = shape(x)
            if isinstance(s, dict):
                merged.update(s)
            else:
                return ["array", s]
        return ["array", merged] if merged else ["array"]
    if isinstance(v, bool):
        return "boolean"
    if isinstance(v, (int, float)):
        return "number"
    return "null" if v is None else "string"


def shape_diff(a, b, path="$"):
    if isinstance(a, dict) and isinstance(b, dict):
        out = [f"{path}.{k}: only in BW" for k in a if k not in b] + [f"{path}.{k}: only in Flogo" for k in b if k not in a]
        for k in a:
            if k in b:
                out += shape_diff(a[k], b[k], f"{path}.{k}")
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) > 1 and len(b) > 1:
            return shape_diff(a[1], b[1], path + "[*]")
        return []                                    # one side empty: nothing to compare
    return [] if a == b or "null" in (a, b) else [f"{path}: BW {a} vs Flogo {b}"]


def semantic(bw, fl, spec):
    notes = []
    if bw["status"] != fl["status"]:
        return False, [f"status BW {bw['status']} != Flogo {fl['status']}"]
    notes += shape_diff(shape(bw["json"]), shape(fl["json"]))
    for path, facts in (spec.get("facts") or {}).items():
        text = " ".join(json.dumps(x) if not isinstance(x, str) else x for x in collect(fl["json"], path)).lower()
        notes += [f"{path}: fact {f!r} missing" for f in facts if f.lower() not in text]
    for path, values in (spec.get("values") or {}).items():
        got = collect(fl["json"], path)
        notes += [f"{path}: value {v!r} missing (got {got[:4]})" for v in values if v not in got]
    return not notes, notes


def strip_nulls(v):
    if isinstance(v, dict):
        return {k: strip_nulls(x) for k, x in v.items() if x is not None}
    if isinstance(v, list):
        return [strip_nulls(x) for x in v]
    return v


def diff(a, b, path="$"):
    """First few differences between two JSON values."""
    out = []
    if type(a) != type(b) and not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
        return [f"{path}: {json.dumps(a)[:80]} != {json.dumps(b)[:80]}"]
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append(f"{path}.{k}: only in Flogo ({json.dumps(b[k])[:60]})")
            elif k not in b:
                out.append(f"{path}.{k}: only in BW ({json.dumps(a[k])[:60]})")
            else:
                out += diff(a[k], b[k], f"{path}.{k}")
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append(f"{path}: list length {len(a)} != {len(b)}")
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff(x, y, f"{path}[{i}]")
    elif a != b:
        out.append(f"{path}: {json.dumps(a)[:80]} != {json.dumps(b)[:80]}")
    return out[:8]


def verdict(bw_status, bw_json, bw_ok, fl_status, fl_json):
    """bw_ok: BW produced a usable answer (a JSON body with a status below 500). Returns (verdict, notes)."""
    if bw_ok:
        if fl_status != bw_status:
            return "MISMATCH", [f"status BW {bw_status} != Flogo {fl_status}"]
        if bw_json == fl_json:
            return "MATCH", []
        if strip_nulls(bw_json) == strip_nulls(fl_json):
            return "EQUIVALENT", ["differs only in null vs absent keys"]
        return "MISMATCH", diff(bw_json, fl_json)
    # BW failed (5xx / HTML error page / connection error)
    if fl_status and fl_status >= 400 and fl_json is not None:
        return "IMPROVED", [f"BW {bw_status} (non-JSON or 5xx) -> Flogo {fl_status} JSON {json.dumps(fl_json)[:90]}"]
    if bw_status == fl_status and bw_json == fl_json:
        return "MATCH", []
    return "MISMATCH", [f"BW {bw_status} -> Flogo {fl_status} {json.dumps(fl_json)[:90] if fl_json else ''}"]


# --------------------------------------------------------------------------------------- MCP
# BW's MCP server wraps a failed REST operation (HTTP 5xx / Java exception) in a tool result whose text starts
# with this prefix instead of setting isError - such a result counts as a BW failure, not an answer.
BW_MCP_FAILURE = "API call failed"

class MCP:
    def __init__(self, url):
        self.url, self.sid, self.n = url, None, 0
        self.rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                                "clientInfo": {"name": "bw6-flogo-parity", "version": "1"}})
        self.rpc("notifications/initialized", notify=True)

    def rpc(self, method, params=None, notify=False):
        body = {"jsonrpc": "2.0", "method": method}
        if not notify:
            self.n += 1
            body["id"] = self.n
        if params is not None:
            body["params"] = params
        h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if self.sid:
            h["Mcp-Session-Id"] = self.sid
        r = urllib.request.urlopen(urllib.request.Request(self.url, json.dumps(body).encode(), h), timeout=60)
        self.sid = r.headers.get("Mcp-Session-Id") or self.sid
        txt = r.read().decode("utf-8", "replace")
        if notify or not txt.strip():
            return None
        if "data:" in txt:
            txt = [l[5:].strip() for l in txt.splitlines() if l.startswith("data:")][-1]
        return json.loads(txt)

    def tools(self):
        return {t["name"]: t for t in self.rpc("tools/list")["result"]["tools"]}

    def call(self, name, args):
        return self.rpc("tools/call", {"name": name, "arguments": args}).get("result", {})


def tool_result_json(res):
    """MCP tool result -> (isError, parsed JSON of the text content or None, raw text)."""
    texts = [c.get("text", "") for c in res.get("content", []) if c.get("type") == "text"]
    raw = "\n".join(texts)
    try:
        js = json.loads(raw)
    except ValueError:
        js = None
    sc = res.get("structuredContent")
    if js is None and isinstance(sc, dict):
        js = sc
    return bool(res.get("isError")), js, raw


def schema_shape(s):
    s = s or {}
    return ({k: (v or {}).get("type") for k, v in (s.get("properties") or {}).items()}, sorted(s.get("required") or []))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cases")
    ap.add_argument("--report", help="write a markdown report here")
    a = ap.parse_args()
    cfg = json.load(open(a.cases, encoding="utf-8"))
    rows, bad = [], 0

    rest = cfg.get("rest")
    if rest:
        for c in rest["cases"]:
            hdr = {**rest.get("headers", {}), **c.get("headers", {})}
            bw = http(c["method"], rest["bw"] + c["path"], c.get("body"), headers=hdr)
            fl = http(c["method"], rest["flogo"] + c.get("flogoPath", c["path"]), c.get("flogoBody", c.get("body")),
                      headers=hdr)
            if c.get("normalize") and fl["json"] is not None:  # Flogo-side fixture ids -> BW-side ids
                s = json.dumps(fl["json"])
                for flogo_value, bw_value in c["normalize"].items():
                    s = s.replace(flogo_value, bw_value)
                fl["json"] = json.loads(s)
            if c.get("ignore"):
                bw["json"], fl["json"] = drop_paths(bw["json"], c["ignore"]), drop_paths(fl["json"], c["ignore"])
            # a JSON answer below 500 (incl. BW's own JSON 4xx errors) is compared as is; only 5xx / non-JSON
            # BW failures can become IMPROVED
            bw_ok = bw["status"] is not None and bw["status"] < 500 and bw["json"] is not None
            v, notes = verdict(bw["status"], bw["json"], bw_ok, fl["status"], fl["json"])
            if v == "MISMATCH" and c.get("semantic"):
                ok, why = semantic(bw, fl, c["semantic"])
                v, notes = ("SEMANTIC", [c["semantic"].get("why", "shape + facts")]) if ok else ("MISMATCH", why[:6])
            if v == "MISMATCH" and c.get("accept"):
                v, notes = "ACCEPTED", [f"intentional deviation: {c['accept']}"] + notes[:2]
            rows.append(("REST", c["name"], f"{c['method']} {c['path']}", bw["status"], fl["status"], v, notes))

    mcp = cfg.get("mcp")
    if mcp:
        bwm, flm = MCP(mcp["bw"]), MCP(mcp["flogo"])
        bwt, flt = bwm.tools(), flm.tools()
        for name in mcp.get("tools", []):
            if name not in flt:
                rows.append(("MCP-def", name, "tools/list", "present", "MISSING", "MISMATCH", ["tool not served by Flogo"]))
                continue
            notes = []
            b, f = bwt.get(name, {}), flt[name]
            if (b.get("description") or "") != (f.get("description") or ""):
                notes.append(f"description BW {b.get('description')!r} != Flogo {f.get('description')!r}")
            bp, br = schema_shape(b.get("inputSchema"))
            fp, fr = schema_shape(f.get("inputSchema"))
            if set(bp) != set(fp):
                notes.append(f"input properties BW {sorted(bp)} != Flogo {sorted(fp)}")
            if br != fr:
                notes.append(f"required BW {br} != Flogo {fr}")
            rows.append(("MCP-def", name, "tools/list", "ok", "ok", "MISMATCH" if notes else "MATCH", notes))
        extra = sorted(set(flt) - set(mcp.get("tools", [])))
        if extra:
            rows.append(("MCP-def", "(extra)", "tools/list", "-", ", ".join(extra), "MISMATCH", ["Flogo serves tools BW parity list lacks"]))
        for c in mcp.get("calls", []):
            be, bj, braw = tool_result_json(bwm.call(c["tool"], c["arguments"]))
            fe, fj, fraw = tool_result_json(flm.call(c["tool"], c["arguments"]))
            bw_ok = not be and bj is not None and not braw.startswith(BW_MCP_FAILURE)
            if bw_ok:
                if fj == bj:
                    v, notes = "MATCH", []
                elif strip_nulls(fj) == strip_nulls(bj):
                    v, notes = "EQUIVALENT", ["differs only in null vs absent keys"]
                else:
                    v, notes = "MISMATCH", diff(bj, fj) or [f"Flogo text: {fraw[:120]}"]
            else:
                v, notes = ("IMPROVED", [f"BW: {braw[:70]}... -> Flogo: {fraw[:90]}"]) if fj is not None else \
                           ("MISMATCH", [f"BW error, Flogo non-JSON: {fraw[:120]}"])
            rows.append(("MCP-call", c["name"], f"{c['tool']}({json.dumps(c['arguments'])[:50]})",
                         "error" if not bw_ok else "ok", "error" if fe else "ok", v, notes))

    lines = ["| Kind | Case | Request | BW | Flogo | Verdict | Notes |", "|---|---|---|---|---|---|---|"]
    for k, n, req, bs, fs, v, notes in rows:
        bad += v == "MISMATCH"
        lines.append(f"| {k} | {n} | `{req}` | {bs} | {fs} | **{v}** | {'; '.join(notes).replace('|', '/')} |")
    counts = {v: sum(1 for r in rows if r[5] == v) for v in ("MATCH", "EQUIVALENT", "IMPROVED", "ACCEPTED", "SEMANTIC", "MISMATCH")}
    summary = f"{len(rows)} checks: " + ", ".join(f"{k} {v}" for k, v in counts.items())
    print(summary)
    for k, n, req, bs, fs, v, notes in rows:
        print(f"  {v:<10} {k:<8} {n:<26} BW={bs} Flogo={fs}  {'; '.join(notes)[:150]}")
    if a.report:
        with open(a.report, "w", encoding="utf-8") as f:
            f.write(f"# Parity report\n\n{summary}\n\n" + "\n".join(lines) + "\n")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
