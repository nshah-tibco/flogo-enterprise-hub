#!/usr/bin/env bash
# Print the Cline MCP settings for this VM, with the real Flogo extension path and home folder filled in.
#   bash ~/FlogoLab/cline/print-mcp-settings.sh
# Copy the JSON it prints into Cline > MCP Servers > Configure > "Configure MCP Servers" (replace everything), save.
# (On disk that file is ~/.cline/data/settings/cline_mcp_settings.json.) Writes nothing itself.

KIT="${FLOGOLAB:-$HOME/FlogoLab}"
EXT=$(ls -d "$HOME"/.vscode/extensions/tibco.flogo-2.26.* 2>/dev/null | sort -V | tail -n1)
if [ -z "$EXT" ]; then
  echo "ERROR: no ~/.vscode/extensions/tibco.flogo-2.26.* folder - is the Flogo extension (Linux build) installed?" >&2
  exit 1
fi
FDA="$EXT/bin/flogodesign-cli"
if [ ! -f "$FDA" ]; then echo "ERROR: $FDA not found" >&2; exit 1; fi
if [ ! -x "$FDA" ]; then echo "NOTE: $FDA is not executable - run: chmod +x '$FDA'" >&2; fi

cat <<JSON
{
  "mcpServers": {
    "flogo-fda-lab2": {
      "type": "stdio",
      "command": "$FDA",
      "args": ["-f", "$KIT/lab2/SW_LeakReport.flogo", "mcp", "stdio"],
      "env": {},
      "disabled": false,
      "autoApprove": [],
      "timeout": 120
    },
    "sw-water-mcp": {
      "type": "streamableHttp",
      "url": "http://localhost:9090/mcp",
      "headers": {
        "Authorization": "Bearer sw-workshop-key"
      },
      "disabled": false,
      "autoApprove": [],
      "timeout": 60
    }
  }
}
JSON
