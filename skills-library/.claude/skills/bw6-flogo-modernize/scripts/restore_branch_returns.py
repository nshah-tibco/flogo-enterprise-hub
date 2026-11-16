#!/usr/bin/env python3
"""Restore the Return activity after every branch HTTP response in a modernized Flogo app.

Why: each REST operation flow answers non-happy paths (400/404/fallback 200) with its own Configure HTTP
Response activity followed by Return<act>. If the designer drops those Returns (it auto-saves on open and
deletes an activity whose incoming link is stored before its predecessor's), the REST API still works -
httpresponse replies by itself - but every MCP tool that calls the flow as a subflow fails with
"failed to resolve activity attr: 'code' / 'responseBody'". This script finds operation flows (flow outputs
code + responseBody) with an httpresponse activity that has no outgoing link, and adds
Return<act> (code/responseBody from that activity) linked after it - via fda only, nothing else touched.
The new link is stored last, so the designer keeps it.

Close the app in the Flogo designer first (Discard any unsaved changes) - never patch a .flogo that is open.

Usage:  python restore_branch_returns.py <app.flogo> [<app.flogo> ...] [--dry-run]
Needs $FDA (see AGENT.md -> "Resolving the fda CLI").
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fdalib import Fda  # noqa: E402
from designer_load_check import check as designer_drops  # noqa: E402


def dead_end_responses(app):
    """[(flow, act, ret_name, ret_exists)] for httpresponse activities without an outgoing link."""
    d = json.load(open(app, encoding="utf-8"))
    out = []
    for r in d.get("resources", []):
        data = r.get("data", {})
        outputs = {o.get("name") for o in (data.get("metadata") or {}).get("output", [])}
        if not {"code", "responseBody"} <= outputs:
            continue
        flow = r["id"].split(":", 1)[1]
        tasks = {t["id"]: t for t in data.get("tasks", [])}
        sources = {l["from"] for l in data.get("links", [])}
        for tid, t in tasks.items():
            if t["activity"]["ref"] == "#httpresponse" and tid not in sources:
                ret = "Return" + tid
                out.append((flow, tid, ret, ret in tasks))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("apps", nargs="+")
    ap.add_argument("--dry-run", action="store_true", help="only list what would be added")
    a = ap.parse_args()
    rc = 0
    for app in a.apps:
        if not os.path.isfile(app):
            print(f"{app}: not found")
            rc = 1
            continue
        todo = dead_end_responses(app)
        print(f"== {os.path.basename(app)}: {len(todo)} branch response(s) without a Return")
        for flow, act, ret, exists in todo:
            print(f"   {flow}: {act} -> {ret}{' (exists, relink)' if exists else ''}")
        if a.dry_run or not todo:
            continue
        f = Fda(app, history=False, quiet=True)
        for flow, act, ret, exists in todo:
            if not exists:
                f("ca", flow, ret, "act_default_actreturn", "Reply with the branch response", "--doNotLink")
                f("mm", f"{flow}.{ret}.input.mappings.code", f"=$activity[{act}].code")
                f("mm", f"{flow}.{ret}.input.mappings.responseBody", f"=$activity[{act}].response")
            f("cl", flow, act, ret)
        left = dead_end_responses(app)
        fails, _, _ = f.cm()
        print(f"   remaining dead ends: {len(left)}; cm rule failures: {len(fails)}")
        for x in fails:  # filtered @foreach shows up as FOREACH_SCOPE_UNDEFINED, a known cm false positive
            print("     " + " ".join(x.split())[:140])
        lost = designer_drops(app)
        print(f"   designer load check: {'OK' if not lost else 'WOULD DROP ' + json.dumps(lost) + ' - run designer_load_check.py --fix'}")
        rc |= 1 if left or lost else 0
    return rc


if __name__ == "__main__":
    sys.exit(main())
