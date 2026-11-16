#!/usr/bin/env python3
"""Write the HAND-OVER summary after a modernization: what was built, how it was verified, what was not
modernized, and the manual steps the user runs to take it end to end.

Reads the built Flogo app (and optionally the analyzer spec and parity reports) - never writes the app.
Secret values (password/key/token/secret properties) are never printed.

Usage:
  python handover_summary.py <app.flogo> [--spec <Module>.bw6spec.json] [--parity <parity_report.md> ...]
                             [--context <flogobuild-context>] [--extensions-dir <repo>/extensions] [--out <handover.md>]
"""
import argparse
import base64
import json
import os
import re
import subprocess
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from designer_load_check import check as designer_drops  # noqa: E402

SECRET_NAME = re.compile(r"(?i)(password|passwd|secret|token|api[_-]?key|apikey|credential)")
PLACEHOLDER = re.compile(r"(?i)^(your[_-]|<|changeme|placeholder|xxx)")


def contribs(app):
    c = app.get("contrib")
    if isinstance(c, list):
        return c
    for dec in (json.loads, lambda s: json.loads(base64.b64decode(s)), lambda s: json.loads(zlib.decompress(base64.b64decode(s)))):
        try:
            return dec(c)
        except Exception:  # noqa: BLE001
            pass
    return []


def prop_state(p):
    v = "" if p.get("value") is None else str(p.get("value"))
    if v.startswith("SECRET:"):
        return "encrypted (SECRET:) - set", "secret"
    if SECRET_NAME.search(p["name"]):
        if not v or PLACEHOLDER.search(v):
            return "PLACEHOLDER - supply at run time", "todo"
        return "plain text value present - do not commit; prefer an env var at run time", "plain-secret"
    if not v:
        return "EMPTY - set it", "todo"
    if PLACEHOLDER.search(v):
        return f"PLACEHOLDER `{v}` - set it", "todo"
    return f"`{v[:60]}`", "ok"


def parity_lines(path):
    t = open(path, encoding="utf-8").read()
    summ = next((l.strip() for l in t.splitlines() if re.match(r"\d+ checks:", l.strip())), "(no summary line)")
    rows = [l for l in t.splitlines() if re.search(r"\*\*(IMPROVED|ACCEPTED|SEMANTIC|MISMATCH)\*\*", l)]
    return summ, rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("app")
    ap.add_argument("--spec")
    ap.add_argument("--parity", action="append", default=[])
    ap.add_argument("--context", help="flogobuild build context name (config.md FLOGOBUILD_CONTEXT_NAME)")
    ap.add_argument("--extensions-dir", help="repo-local user extensions folder, if the app uses one")
    ap.add_argument("--out")
    a = ap.parse_args()
    app_path = os.path.abspath(a.app)
    app = json.load(open(app_path, encoding="utf-8"))
    spec = json.load(open(a.spec, encoding="utf-8")) if a.spec else None
    name = app.get("name") or os.path.splitext(os.path.basename(app_path))[0]
    props = app.get("properties", [])
    pval = {p["name"]: p.get("value") for p in props}
    conts = contribs(app)
    user_ext = [c for c in conts if c.get("isUserExtension")]

    L = [f"# Hand-over: `{name}`", "", "## 1. What was built", ""]
    flows = {r["id"].split(":", 1)[1]: r for r in app.get("resources", [])}
    L += [f"- App: `{app_path}` (Flogo 2.x, app model {app.get('appModel', '?')}, version {app.get('version', '?')})"]
    endpoints, tools = [], []
    for t in app.get("triggers", []):
        port_ref = (t.get("settings") or {}).get("port") or (t.get("settings") or {}).get("serverPort") or ""
        m = re.search(r'\$property\["([^"]+)"\]', str(port_ref))
        port = pval.get(m.group(1)) if m else port_ref
        kind = {"#rest": "REST", "#mcpserver": "MCP server"}.get(t["ref"], t["ref"])
        L.append(f"- Trigger `{t['id']}` ({kind}) on port {port}" + (f" (app property `{m.group(1)}`)" if m else "")
                 + f", {len(t.get('handlers', []))} handler(s)")
        for h in t.get("handlers", []):
            s = h.get("settings") or {}
            if t["ref"] == "#rest":
                endpoints.append((s.get("Method"), s.get("Path"), h["action"]["settings"].get("flowURI", "").split(":")[-1], port))
            elif t["ref"] == "#mcpserver":
                tools.append((s.get("handlerName"), s.get("handlerType"), port, (t.get("settings") or {}).get("serverEndpointPath", "/mcp")))
    sub = [f for f in flows if f not in {e[2] for e in endpoints} and not f.startswith("mcp_")]
    L += [f"- Flows: {len(flows)} ({len(endpoints)} REST operations, {sum(1 for f in flows if f.startswith('mcp_'))} MCP tool "
          f"flows, {len(sub)} subflow(s){': ' + ', '.join(sub) if sub else ''})"]
    if endpoints:
        L += ["", "| Method | Path | Flow |", "|---|---|---|"] + [f"| {m} | `{p}` | `{f}` |" for m, p, f, _ in endpoints]
    if tools:
        L += ["", "MCP " + ", ".join(f"{k.lower()} `{n}`" for n, k, _, _ in tools) + f" at `http://localhost:{tools[0][2]}{tools[0][3]}`"]
    conns = list((app.get("connections") or {}).values())
    if conns:
        L += ["", "Connections: " + ", ".join(f"`{c.get('name')}` ({c.get('ref')})" for c in conns)]
    L += ["", "Contributions: " + ", ".join(c.get("s3location", c.get("ref", "?")).split("/")[-1] for c in conts)
          + (f" - **user extension(s): {', '.join(c.get('s3location', c.get('ref')).split('/')[-1] for c in user_ext)}**" if user_ext else "")]

    L += ["", "## 2. App properties", "", "| Property | Type | State |", "|---|---|---|"]
    todo = []
    for p in props:
        st, kind = prop_state(p)
        L.append(f"| `{p['name']}` | {p.get('type')} | {st} |")
        if kind in ("todo", "plain-secret"):
            todo.append((p["name"], kind))

    L += ["", "## 3. How it was verified", ""]
    lost = designer_drops(app_path)
    L.append(f"- Designer-load gate: {'OK - every activity survives opening in the designer' if not lost else 'FAIL - ' + json.dumps(lost)}")
    for pr in a.parity:
        summ, rows = parity_lines(pr)
        L.append(f"- Parity `{os.path.basename(pr)}`: {summ}")
        L += [f"  - {re.sub(r'  +', ' ', r.strip())[:220]}" for r in rows[:40]]
    if not a.parity:
        L.append("- Parity: not run (pass --parity <report.md>)")

    if spec:
        L += ["", "## 4. Items the plan flagged - confirm each was handled as agreed", ""]
        open_items = [w for w in spec.get("warnings", []) if w["status"] in ("unsupported", "decide")]
        L += [f"- [{w['status']}] {w['area']}: {w['item']} - {w['workaround']}" for w in open_items] or ["- nothing flagged"]
        dead = [(o.get("flogoFlow"), o.get("unusedActivities")) for o in spec["operations"] if o.get("unusedActivities")]
        if dead:
            L += ["- Skipped BW activities (nothing reads their result): " + "; ".join(f"{f}: {', '.join(d)}" for f, d in dead)]

    exe = name + (".exe" if os.name == "nt" else "")
    ctx = a.context or "<FLOGOBUILD_CONTEXT_NAME from config.md>"
    # FLOGO_APP_PROPS_ENV=auto reads env vars named exactly like the property; dotted names (connection properties)
    # are set in the app or in a JSON file passed with FLOGO_APP_PROPS_JSON=<file path>
    env_props = [n for n, _ in todo if "." not in n]
    file_props = [n for n, _ in todo if "." in n]
    steps = ["**Open the app once in the VS Code Flogo designer** and check it shows no errors. Close it before any "
             "further scripted change (the designer saves on open)."]
    if todo:
        steps.append("**Set these properties** (in the designer, or at run time - preferred for secrets): "
                     + ", ".join(f"`{n}`" for n, _ in todo) + "."
                     + (f" Dotted names ({', '.join(f'`{n}`' for n in file_props)}): set them in the app or in a JSON "
                        "file `{\"<name>\": \"<value>\"}` passed with `FLOGO_APP_PROPS_JSON=<file path>`." if file_props else ""))
    if conns:
        steps.append("**Connections**: make sure " + ", ".join(f"`{c.get('name')}`" for c in conns) + " can reach their "
                     "systems (database up, credentials valid). Native driver/client prerequisites: VS Code Flogo sidebar -> "
                     "Help And Feedback -> Install Prerequisites for Flogo Connectors.")
    if user_ext:
        steps.append("**User extension**: build with a flogobuild context created with the extensions folder "
                     f"(`flogobuild create-context -n <name> -v <flogo-vsix> -u {a.extensions_dir or '<repo>/extensions'}`). "
                     "In VS Code, either build with the Build icon, or point `flogo.extensions.local` at the PARENT "
                     "extensions folder before using the shared engine.")
    steps.append(f"**Build**: `flogobuild build-exe -f {app_path} -c {ctx} -o <FLOGO_APPS_DIR>/../bin` (or the Build icon in VS Code).")
    run = ["**Run** (start dependencies first - database, called services; start this app before any AI orchestrator "
           "that uses its MCP tools):",
           "   - bash/Git Bash: `FLOGO_MAPPING_OMIT_NULLS=true FLOGO_APP_PROPS_ENV=auto "
           + "".join(f"{n}=<value> " for n in env_props) + f"<bin>/{exe}`",
           "   - PowerShell: `$env:FLOGO_MAPPING_OMIT_NULLS='true'; $env:FLOGO_APP_PROPS_ENV='auto'; "
           + "".join(f"$env:{n}='<value>'; " for n in env_props) + f"& <bin>{os.sep if os.name == 'nt' else '/'}{exe}`",
           "   - Wait for `Started`" + (" and `MCP HTTP Server ... reachable on`." if tools else ".")]
    steps.append("\n".join(run))
    smoke = ["**Smoke test**:"]
    if endpoints:
        m, p, _, port = next(((m, p, f, port) for m, p, f, port in endpoints if m == "GET"), endpoints[0])
        smoke.append(f"   - REST: `curl -i -X {m} http://localhost:{port}{p}` (fill in path/query parameters)")
    if tools:
        smoke.append(f"   - MCP: connect an MCP client to `http://localhost:{tools[0][2]}{tools[0][3]}` and call `tools/list`")
    steps.append("\n".join(smoke))
    steps.append("**Stop**: Ctrl+C; a background exe on Windows: `netstat -ano | findstr :<port>` then `taskkill /PID <pid> /F`; "
                 "macOS/Linux: `kill <pid>`.")
    steps.append("**Before committing**: replace live secrets with placeholders and keep run-time values in env vars.")
    L += ["", "## 5. Manual steps to run it end to end", ""] + [f"{i}. {x}" for i, x in enumerate(steps, 1)]
    if any(k == "plain-secret" for _, k in todo):
        L += ["", "**Warning:** a secret is stored in plain text in this .flogo (see section 2). Don't commit it."]

    out = a.out or os.path.join(os.path.dirname(app_path), f"{name}.handover.md")
    open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(f"hand-over: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
