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
    if not p:
        sys.exit("error: $FDA is not set. Resolve the flogodesign-cli of the Flogo 2.x VS Code extension as described in "
                 "AGENT.md -> 'Resolving the fda CLI' (ask the user to pick when several are installed), then "
                 "export FDA=<path>.")
    if not os.path.isfile(p):
        sys.exit(f"error: $FDA={p} does not exist (extension updated or removed?). Re-run the fda discovery in AGENT.md "
                 "and export FDA=<path>.")
    return p


# skills-library/.claude/skills/config.md: the single source of truth for environment values (AGENT.md)
CONFIG_MD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "config.md"))


def config_value(key, path_relative=False):
    """A value from config.md - a table row '| KEY | `value` | ...' or a 'KEY: value' line - or None when the file,
    the key or a real value is missing (placeholders like <...> count as missing). path_relative=True resolves a
    relative path against the folder of config.md (how FLOGO_APPS_DIR is defined)."""
    if not os.path.isfile(CONFIG_MD):
        return None
    with open(CONFIG_MD, encoding="utf-8", errors="replace") as f:
        text = f.read()
    k = re.escape(key)
    m = (re.search(rf"^\|\s*{k}\s*\|\s*`?([^`|]*?)`?\s*\|", text, re.M | re.I)
         or re.search(rf"^{k}\s*:\s*(.*?)\s*$", text, re.M | re.I))
    v = m.group(1).strip() if m else ""
    if not v or v.startswith("<") or v.startswith("*("):
        return None
    if path_relative and not os.path.isabs(v):
        v = os.path.normpath(os.path.join(os.path.dirname(CONFIG_MD), v))
    return v


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
