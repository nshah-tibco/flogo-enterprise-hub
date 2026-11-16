#!/usr/bin/env python3
"""Teach fda the activities of a repo-local (user) Flogo extension, without touching the installed VS Code extension.

fda only creates activity types it finds in its catalog, and user extensions (e.g. <repo>/extensions/openAI) are not
in the bundled one. This exports the active catalog to a private file and merges the extension's
activity/trigger/connector/function descriptors into it:

  python extend_fda_catalog.py <extension-dir> [<extension-dir> ...] --out <work>/fda-config.json

Then point every fda call of that app at it:  export FLOGO_DESIGN_CONFIG_FILE=<work>/fda-config.json
(fdalib/Fda pass the environment through). New types appear as act_<group>_<name>, e.g. act_openai_vectorsearch,
with the extension's own import path. Building the app still needs a flogobuild context created with
-u <extensions root> (see SKILL.md).
"""
import argparse
import os
import re
import subprocess
import sys


def run(exe, *args):
    r = subprocess.run([exe, *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = re.sub(r"\x1b\[[0-9;]*m", "", (r.stdout or "") + (r.stderr or ""))
    if r.returncode != 0 or "(ERROR)" in out:
        sys.exit(f"fda {' '.join(args)} failed:\n{out[-1500:]}")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("extensions", nargs="+", help="extension folder(s) holding activity.json/descriptor files")
    ap.add_argument("--out", required=True, help="private fda catalog to write (e.g. <work>/fda-config.json)")
    a = ap.parse_args()
    exe = os.environ.get("FDA")
    if not exe or not os.path.exists(exe):
        sys.exit("Set $FDA to the flogodesign-cli binary of the Flogo 2.x extension (see AGENT.md).")
    out = os.path.abspath(a.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    env_cfg = os.environ.pop("FLOGO_DESIGN_CONFIG_FILE", None)   # export the BUNDLED catalog, not a stale private one
    run(exe, "edc", out)
    added = []
    for ext in a.extensions:
        if not os.path.isdir(ext):
            sys.exit(f"{ext} is not a folder")
        log = run(exe, "ave", os.path.abspath(ext), "--type", "all", "--toConfigFile", out)
        added += re.findall(r"The (?:activity|trigger|connection|function) (\S+) is NOT known", log)
    if env_cfg:
        os.environ["FLOGO_DESIGN_CONFIG_FILE"] = env_cfg
    print(f"catalog : {out}")
    print(f"added   : {', '.join(sorted(set(added))) or 'nothing new (already known)'}")
    print(f"next    : export FLOGO_DESIGN_CONFIG_FILE={out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
