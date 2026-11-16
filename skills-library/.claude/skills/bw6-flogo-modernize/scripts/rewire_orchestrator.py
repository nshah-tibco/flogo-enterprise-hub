#!/usr/bin/env python3
"""Make a test copy of a Flogo AI orchestrator that uses modernized Flogo MCP servers next to BW6's.

The source app is never modified. The copy gets:
  - one MCP connection per Flogo app (--flogo-mcp name=url, repeatable),
  - the existing BW MCP connection restricted (selectedTools) to the BW tools that no Flogo app serves yet,
    so every tool name is served exactly once,
  - its listening trigger (REST, WebSocket ...) moved to --port, and optionally the LLM API key set from --api-key
    (encrypted -> password property; the property name is read from the LLM activity's apiKey mapping).
Every LLM Client / AI Agent activity in the app is rewired. Every change goes through fda; nothing is hand-edited.

Usage:
  python rewire_orchestrator.py --source <orchestrator.flogo> --out <copy.flogo> [--port <free port>] \
      --flogo-mcp <Name>=http://localhost:<MCP_PORT>/mcp [--flogo-mcp ...] [--bw-mcp <connection name>] \
      [--flogo-only] [--api-key <key>]

Requires the BW (unless --flogo-only) and Flogo MCP servers to be running (tool lists are read live).
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request

FDA = os.environ.get("FDA")


def run_fda(app, *args):
    r = subprocess.run([FDA, *args, "-f", app], capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = re.sub(r"\x1b\[[0-9;]*m", "", (r.stdout or "") + (r.stderr or ""))
    if r.returncode != 0 or "(ERROR)" in out:
        sys.exit(f"fda {' '.join(args)} failed:\n{out[-1500:]}")
    last = [l for l in out.splitlines() if l.strip()][-1:]
    print(f"fda {' '.join(args)[:100]}\n   -> {last[0][:160] if last else ''}")
    return out


def mcp_tools(url):
    sid, n = None, 0

    def rpc(method, params=None, notify=False):
        nonlocal sid, n
        body = {"jsonrpc": "2.0", "method": method}
        if not notify:
            n += 1
            body["id"] = n
        if params is not None:
            body["params"] = params
        h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if sid:
            h["Mcp-Session-Id"] = sid
        r = urllib.request.urlopen(urllib.request.Request(url, json.dumps(body).encode(), h), timeout=30)
        sid = r.headers.get("Mcp-Session-Id") or sid
        t = r.read().decode("utf-8", "replace")
        if notify or not t.strip():
            return None
        if "data:" in t:
            t = [l[5:].strip() for l in t.splitlines() if l.startswith("data:")][-1]
        return json.loads(t)

    rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "rewire", "version": "1"}})
    rpc("notifications/initialized", notify=True)
    return [t["name"] for t in rpc("tools/list")["result"]["tools"]]


def encrypt(plain):
    """SECRET:<cipher> via flogo-vscode-cli, which ships in the same bin folder as flogodesign-cli."""
    name = "flogo-vscode-cli.exe" if os.name == "nt" else "flogo-vscode-cli"
    cli = os.path.join(os.path.dirname(FDA), name)
    if not os.path.exists(cli):
        sys.exit(f"{cli} not found; cannot store the API key as a password property")
    r = subprocess.run([cli, "secret", "encrypt", "-p", plain], capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r'"cipherText":\s*"(SECRET:[^"]+)"', r.stdout or "")
    if not m:
        sys.exit("flogo-vscode-cli secret encrypt returned no cipherText")
    return m.group(1)


def main():
    global FDA
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--port", type=int, help="listening port of the copy (must differ from the source's when both run)")
    ap.add_argument("--trigger", help="trigger id to move to --port when the app has several listening triggers")
    ap.add_argument("--bw-mcp", help="name of the source's BW MCP connection when it has several MCP connections")
    ap.add_argument("--flogo-mcp", action="append", default=[], metavar="NAME=URL")
    ap.add_argument("--api-key", help="LLM API key; stored encrypted (SECRET:) as a password property. Keep the copy out of git")
    ap.add_argument("--api-key-property", help="app property holding the LLM API key (default: read from the LLM "
                                               "activity's apiKey mapping)")
    ap.add_argument("--flogo-only", action="store_true",
                    help="drop the source's BW MCP connection: the copy uses only the --flogo-mcp servers (runs without BW)")
    ap.add_argument("--fda", help="flogodesign-cli path (default: $FDA)")
    a = ap.parse_args()
    FDA = a.fda or FDA
    if not FDA or not os.path.exists(FDA):
        sys.exit("set --fda or $FDA to the flogodesign-cli binary")
    if os.path.abspath(a.source) == os.path.abspath(a.out):
        sys.exit("--out must differ from --source; the source orchestrator is never modified")

    shutil.copyfile(a.source, a.out)
    app = json.load(open(a.out, encoding="utf-8"))
    mcp_conns = {cid: c for cid, c in app.get("connections", {}).items() if c.get("ref", "").endswith("mcpserverconfig")}
    if a.bw_mcp:
        mcp_conns = {cid: c for cid, c in mcp_conns.items() if c.get("name") == a.bw_mcp}
    if len(mcp_conns) > 1:
        sys.exit("the source has several MCP connections (" + ", ".join(c.get("name") for c in mcp_conns.values())
                 + "); name the BW one with --bw-mcp")
    if not mcp_conns and not a.flogo_only:
        sys.exit("no BW MCP connection found in the source (use --bw-mcp, or --flogo-only)")
    bw_id, bw = next(iter(mcp_conns.items()), (None, None))
    bw_url = (bw or {}).get("settings", {}).get("serverUrl", "")
    m = re.match(r'=\$property\["([^"]+)"\]', str(bw_url))
    if m:  # the URL is bound to an app property: use its value
        bw_url = next((p.get("value") for p in app.get("properties", []) if p["name"] == m.group(1)), bw_url)
    tasks = [(r["id"].split(":", 1)[1], t["id"], t["activity"]) for r in app["resources"] for t in r["data"]["tasks"]
             if t["activity"]["ref"].endswith(("llmclientactivity", "agentactivity"))]
    if not tasks:
        sys.exit("no LLM Client / AI Agent activity found")

    served = {}
    new_ids = []
    for spec in a.flogo_mcp:
        name, url = spec.split("=", 1)
        tools = mcp_tools(url)
        served.update({t: name for t in tools})
        run_fda(a.out, "cc", name, "con_mcpserverconfig")
        for k, v in (("name", name), ("serverType", "http"), ("serverUrl", url), ("httpTransportType", "streamable"),
                     ("authType", "None"), ("description", f"Flogo modernized MCP server ({', '.join(tools)})")):
            run_fda(a.out, "sa", "connection", f"{name}.settings.{k}", v)
        cur = json.load(open(a.out, encoding="utf-8"))
        cid = next(i for i, c in cur["connections"].items() if c.get("name") == name)
        new_ids.append(cid)
        print(f"  {name}: {url} serves {tools}")

    keep = []
    if a.flogo_only:
        # BW is neither needed nor contacted: keep only the Flogo MCP servers, then remove the BW connection
        servers = [f"conn://{i}" for i in new_ids]
    else:
        keep = [t for t in mcp_tools(bw_url) if t not in served]
        run_fda(a.out, "sa", "connection", f"{bw['name']}.settings.selectedTools", "--jsonValue", json.dumps(keep))
        servers = [f"conn://{bw_id}"] + [f"conn://{i}" for i in new_ids]
    for flow, act, _ in tasks:
        run_fda(a.out, "sa", "activity", f"{flow}.{act}.settings.mcpServers", "--jsonValue", json.dumps(servers))
    if a.flogo_only and bw:
        run_fda(a.out, "rc", bw["name"])
    if a.port:
        listening = [t for t in app["triggers"] if "port" in (t.get("settings") or {}) and (not a.trigger or t["id"] == a.trigger)]
        if len(listening) != 1:
            sys.exit(f"{len(listening)} listening triggers ({', '.join(t['id'] for t in listening)}); pick one with --trigger")
        trig = listening[0]
        bound = re.match(r'=\$property\["([^"]+)"\]', str(trig["settings"]["port"]))
        if bound:  # port bound to an app property: change the property, keep the binding
            ptype = next((p.get("type") for p in app.get("properties", []) if p["name"] == bound.group(1)), "float64")
            run_fda(a.out, "rap", bound.group(1))
            run_fda(a.out, "cap", bound.group(1), "string" if ptype == "string" else "number", str(a.port))
        else:
            run_fda(a.out, "sa", "trigger", f"{trig['id']}.settings.port", str(a.port), "-C", "number")
    if a.api_key:
        # A password property is a string property whose value is SECRET:<cipher>; the designer then shows
        # it as type password and the engine decrypts it. Never write type "password" (the engine rejects it).
        prop = a.api_key_property
        if not prop:
            refs = {m for _, _, act in tasks for m in re.findall(r'"apiKey":\s*"=\$property\[\\?"([^"\\]+)\\?"\]', json.dumps(act))}
            if len(refs) != 1:
                sys.exit(f"cannot tell which app property holds the API key ({sorted(refs) or 'none bound'}); "
                         "pass --api-key-property")
            prop = refs.pop()
        secret = a.api_key if a.api_key.startswith("SECRET:") else encrypt(a.api_key)
        run_fda(a.out, "rap", prop)
        run_fda(a.out, "cap", prop, "string", secret)
    mode = "Flogo only (BW connection removed)" if a.flogo_only else f"BW keeps {len(keep)} tools"
    print(f"\n{mode}; Flogo serves {sorted(served)}; {len(tasks)} LLM activit{'y' if len(tasks) == 1 else 'ies'} rewired; "
          f"port {a.port or 'unchanged'}; wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
