#!/usr/bin/env bash
# One-time setup: make the Flogo Design Assistant (FDA) skills and the workshop rules visible to Cline.
#
#   bash ~/FlogoLab/cline/setup-flogo-skills.sh            # workspace = ~/FlogoLab (the folder you open in VS Code)
#   bash ~/FlogoLab/cline/setup-flogo-skills.sh <folder>   # another workspace folder
#
# Copies  cline/flogo-skills/*                 -> <workspace>/.claude/skills/   (fda, fda-mapping, flogobuild, flogo-unit-testing)
#         cline/flogo-skills.clinerules.md      -> <workspace>/.clinerules/flogo-skills.md
# and checks that the fda wrapper (cline/tools/fda) finds flogodesign-cli in your Flogo VS Code extension.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
WS="${1:-$HOME/FlogoLab}"
mkdir -p "$WS/.claude/skills" "$WS/.clinerules"
for s in fda fda-mapping flogobuild flogo-unit-testing; do
  rm -rf "$WS/.claude/skills/$s"
  cp -r "$HERE/flogo-skills/$s" "$WS/.claude/skills/"
done
cp "$HERE/flogo-skills/config.example.md" "$WS/.claude/skills/config.example.md"
cp "$HERE/flogo-skills.clinerules.md" "$WS/.clinerules/flogo-skills.md"
chmod +x "$HERE/tools/fda" "$HERE/tools/fda-link" "$HERE/tools/flogo-encrypt"

echo "Skills : $(ls "$WS/.claude/skills" | tr '\n' ' ')"
echo "Rules  : $WS/.clinerules/flogo-skills.md"
if "$HERE/tools/fda" version >/dev/null 2>&1; then
  echo "fda    : OK ($("$HERE/tools/fda" version 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | tail -1))"
else
  echo "fda    : NOT FOUND - install/enable the TIBCO Flogo VS Code extension, then run this again"; exit 1
fi
command -v python3 >/dev/null && echo "python3: OK" || echo "python3: missing (only needed for the validator)"
if [ -f "$WS/.clinerules/cline-rules-flogo-fda.md" ]; then
  echo
  echo "NOTE: $WS/.clinerules/cline-rules-flogo-fda.md (the FDA *MCP server* rules for Lab 2) is also present."
  echo "      For the skills prompts, switch it OFF in Cline's Rules panel (scale icon under the chat box)."
fi
echo
echo "In Cline: open the Rules & Skills panel (scale icon) -> Skills tab: fda, fda-mapping, flogobuild and"
echo "flogo-unit-testing must be listed and switched on; Rules tab: flogo-skills.md switched on."
