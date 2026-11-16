#!/usr/bin/env python3
"""Will the Flogo designer silently DELETE activities when it opens this app? (gotchas F37)

The VS Code designer (2.26.x, LinkConverter.buildActivityTree in dist/flogo-editor/appEditor.js) rebuilds each
flow's canvas from the `links` array IN STORED ORDER: every link creates a NEW node for its target and overwrites
any node already built for that activity, then the canvas is whatever is reachable from links[0].from. So when
the link out of X is stored before the (last) link into X, X's outgoing branch is cut off, never drawn, and the
save the designer performs on open removes those activities from the file - no warning. fda cm, flogobuild and
the runtime all ignore link order, so only this check sees it.

Safe order: links[0] starts at the flow's root, and every link out of an activity comes after ALL links into it.

Usage:
  python designer_load_check.py <app.flogo> [...]             report activities the designer would drop
  python designer_load_check.py <app.flogo> --fix             re-store links in safe order via fda (keeps
                                                                branch conditions), then re-check
  python designer_load_check.py <app.flogo> --designer-js     also run the installed designer's own code (node)
Close the app in the designer before --fix. Needs $FDA for --fix.
"""
import argparse
import glob
import json
import os
import subprocess
import sys


def dropped_on_open(tasks, links):
    """Python port of the designer's buildActivityTree + convertTreeToItems; returns the task ids it loses."""
    tasks = list(tasks)
    known = set(tasks)
    acc = {}
    for l in links:
        frm, to = l["from"], l["to"]
        if frm not in known:
            continue
        node = acc.get(frm) or {"id": frm, "links": []}
        if to in known:
            child = {"id": to, "links": []}  # always a NEW node: an earlier node for `to` (and its links) is lost
            acc[to] = child
            node["links"].append(child)
        acc[frm] = node
    if links and links[0]["from"] in known:
        root = acc[links[0]["from"]]
    elif tasks:
        root = {"id": tasks[0], "links": []}
    else:
        return []
    kept, queue = {root["id"]}, list(root["links"])
    while queue:
        n = queue.pop(0)
        kept.add(n["id"])
        queue.extend(n["links"])
    return [t for t in tasks if t not in kept]


def safe_order(tasks, links):
    """Same links, re-ordered so the designer keeps everything: start at the root, and emit an activity's
    outgoing links only after all of its incoming links (Kahn order; stable w.r.t. the current order)."""
    incoming = {}
    for l in links:
        incoming[l["to"]] = incoming.get(l["to"], 0) + 1
    seen_in = {}
    roots = [l["from"] for l in links if incoming.get(l["from"], 0) == 0]
    ready = list(dict.fromkeys(roots))
    out, done = [], set()
    while ready:
        a = ready.pop(0)
        for i, l in enumerate(links):
            if l["from"] == a and i not in done:
                done.add(i)
                out.append(l)
                seen_in[l["to"]] = seen_in.get(l["to"], 0) + 1
                if seen_in[l["to"]] == incoming[l["to"]]:
                    ready.append(l["to"])
    out += [l for i, l in enumerate(links) if i not in done]  # cycles (not valid in Flogo): keep as is
    return out


def flows_of(app):
    d = json.load(open(app, encoding="utf-8"))
    for r in d.get("resources", []):
        data = r.get("data", {})
        yield r["id"].split(":", 1)[1], [t["id"] for t in data.get("tasks", [])], data.get("links", [])
        eh = data.get("errorHandler")
        if eh and eh.get("tasks"):
            yield r["id"].split(":", 1)[1] + "#errorHandler", [t["id"] for t in eh["tasks"]], eh.get("links", [])


def empty_literals(app):
    """Empty-object literals ({} or [{}]) inside activity input mappings. The designer REMOVES them when it saves
    the app, which changes the JSON the app returns (gotchas F38). [(flow, activity, path)]"""
    hits = []

    def walk(v, path):
        if isinstance(v, dict):
            if not v and path:
                hits.append(path)
            for k, x in v.items():
                walk(x, f"{path}.{k}" if path else k)
        elif isinstance(v, list):
            for i, x in enumerate(v):
                walk(x, f"{path}[{i}]")

    d = json.load(open(app, encoding="utf-8"))
    for r in d.get("resources", []):
        for t in r.get("data", {}).get("tasks", []):
            ref = t["activity"].get("ref", "")
            if not any(k in ref for k in ("httpresponse", "mapper", "actreturn")):
                continue  # only activities that shape a reply / data (SQL "parameters": {} placeholders are harmless)
            m = ((t["activity"].get("input") or {}).get("input") or {}).get("mapping")
            if isinstance(m, dict):
                found = []
                hits_before = len(hits)
                walk(m, "")
                found = hits[hits_before:]
                del hits[hits_before:]
                hits += [(r["id"].split(":", 1)[1], t["id"], f) for f in found]
    return hits


def check(app):
    return {flow: lost for flow, tasks, links in flows_of(app) if (lost := dropped_on_open(tasks, links))}


def find_app_editor(explicit=None):
    """The designer bundle of the extension the user works with: --designer-js-path, else the extension that
    ships $FDA (<ext>/bin/flogodesign-cli -> <ext>/dist/flogo-editor/appEditor.js), else the only installed 2.x one."""
    if explicit:
        return [explicit] if os.path.exists(explicit) else []
    fda = os.environ.get("FDA")
    if fda:
        cand = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(fda))), "dist", "flogo-editor", "appEditor.js")
        if os.path.exists(cand):
            return [cand]
    home = os.path.expanduser("~")
    return glob.glob(os.path.join(home, ".vscode*", "extensions", "tibco.flogo-2.*", "dist", "flogo-editor", "appEditor.js"))


def designer_js_check(app, explicit=None):
    """Cross-check with the installed designer's own buildActivityTree (needs node)."""
    js = find_app_editor(explicit)
    if len(js) != 1:
        return None, ("no Flogo 2.x extension appEditor.js found" if not js else
                      "several Flogo 2.x extensions installed - export FDA=<their flogodesign-cli> or pass --designer-js-path")
    runner = os.path.join(os.path.dirname(os.path.abspath(__file__)), "designer_tree.js")
    flows = [{"flow": f, "tasks": t, "links": [{"from": l["from"], "to": l["to"], "type": l.get("type", "label")} for l in ls]}
             for f, t, ls in flows_of(app)]
    try:
        r = subprocess.run(["node", runner, js[0]], input=json.dumps(flows), capture_output=True, text=True, encoding="utf-8")
    except FileNotFoundError:
        return None, "node is not installed (the Python check above is the same algorithm)"
    if r.returncode:
        return None, r.stderr.strip()[:300]
    return {x["flow"]: x["dropped"] for x in json.loads(r.stdout) if x["dropped"]}, js[0]


def fix(app):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from fdalib import Fda
    f = Fda(app, history=False, quiet=True)
    for flow, tasks, links in flows_of(app):
        if "#" in flow or not dropped_on_open(tasks, links):
            continue
        target = safe_order(tasks, links)
        k = next((i for i, (a, b) in enumerate(zip(links, target)) if (a["from"], a["to"]) != (b["from"], b["to"])), len(links))
        for l in links[k:]:
            f("rl", flow, l["from"], l["to"])
        for l in target[k:]:
            f("cl", flow, l["from"], l["to"])
        cur = next(ls for fl, _, ls in flows_of(app) if fl == flow)
        for l in target[k:]:  # cl creates a plain link: put the branch condition back
            if l.get("type") == "expression" and l.get("value"):
                idx = next(i for i, c in enumerate(cur) if c["from"] == l["from"] and c["to"] == l["to"])
                f("sa", "flow", f"{flow}.links[{idx}].type", "expression")
                f("sa", "flow", f"{flow}.links[{idx}].value", l["value"], "--force")
        print(f"   {flow}: re-stored {len(target) - k} link(s) in designer-safe order")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("apps", nargs="+")
    ap.add_argument("--fix", action="store_true")
    ap.add_argument("--designer-js", action="store_true", help="also run the installed designer's own code (node)")
    ap.add_argument("--designer-js-path", help="appEditor.js to use (default: the extension that ships $FDA)")
    a = ap.parse_args()
    rc = 0
    for app in a.apps:
        bad = check(app)
        if bad and a.fix:
            fix(app)
            bad = check(app)
        status = "OK - designer keeps every activity" if not bad else "WOULD DROP ACTIVITIES ON OPEN"
        print(f"{os.path.basename(app)}: {status}")
        for flow, lost in bad.items():
            print(f"   {flow}: {', '.join(lost)}")
        empties = empty_literals(app)
        if empties:
            print(f"   WARN {len(empties)} empty-object literal(s) the designer removes on save (the reply changes; gotchas F38):")
            for flow, act, path in empties[:10]:
                print(f"     {flow}.{act}: {path}")
        if a.designer_js:
            js_bad, where = designer_js_check(app, a.designer_js_path)
            if js_bad is None:
                print(f"   designer-js: skipped ({where})")
            else:
                agree = js_bad == bad
                print(f"   designer-js ({os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(where))))}): "
                      f"{'agrees' if agree else 'DISAGREES: ' + json.dumps(js_bad)}")
                rc |= 0 if agree else 2
        rc |= 1 if bad else 0
    return rc


if __name__ == "__main__":
    sys.exit(main())
