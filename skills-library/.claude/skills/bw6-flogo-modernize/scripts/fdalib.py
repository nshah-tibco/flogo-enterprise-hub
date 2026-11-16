"""Thin, UTF-8 safe wrapper around the Flogo Design CLI (fda / flogodesign-cli) for the build scripts.

The CLI path comes from $FDA (resolve it as described in AGENT.md -> "Resolving the fda CLI").
Every call passes -f <app> explicitly, strips ANSI colour codes and prints one status line.
A non-zero exit code or an "(ERROR)" line stops the build unless check=False.
"""
import os
import re
import subprocess
import sys


def fda_path():
    p = os.environ.get("FDA")
    if not p or not os.path.exists(p):
        sys.exit("Set $FDA to the flogodesign-cli binary of the Flogo 2.x extension (see AGENT.md).")
    return p


class Fda:
    def __init__(self, app, history=True, quiet=False):
        self.app, self.quiet, self.exe = app, quiet, fda_path()
        self.env = dict(os.environ, FLOGO_DESIGN_ENABLE_HISTORY="true" if history else "false")

    def __call__(self, *args, check=True):
        r = subprocess.run([self.exe, *args, "-f", self.app], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env=self.env, cwd=os.path.dirname(os.path.abspath(self.app)))
        out = re.sub(r"\x1b\[[0-9;]*m", "", (r.stdout or "") + (r.stderr or ""))
        lines = [l for l in out.splitlines() if l.strip() and "History Enabled" not in l]
        bad = r.returncode != 0 or any("(ERROR)" in l for l in lines)
        if not self.quiet or bad:
            print(f"$ fda {' '.join(args)[:120]}\n   -> rc={r.returncode} {(lines[-1] if lines else '')[:240]}")
        if bad and check:
            raise SystemExit(f"fda failed: {' '.join(args)}\n{out[-2000:]}")
        return out

    def cm(self):
        """Run check-mappings. Returns (failing rule rows, summary lines, full output)."""
        out = self("cm", check=False)
        fails = [l for l in out.splitlines() if "✗" in l]
        summary = [l for l in out.splitlines() if "passed all" in l or "rule(s)" in l]
        return fails, summary, out
