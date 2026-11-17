#!/usr/bin/env python3
"""Build the generic part of a Flogo app from analyze_bw6.py output, using fda only.

  project -> Flogo-ready OpenAPI spec -> cas skeleton (one flow per REST operation)
  -> REST/MCP port app properties -> query/path parameters fixed so they reach the flows
  -> MCP Server trigger with one thin flow per MCP tool: subflow call to the REST flow -> {data, error}

Writes <work>/plan.json for the business-logic step (see flogo_logic_lib.py) and stops before any
operation-specific logic: every REST flow still answers with the cas logReply placeholder.

Usage:
  python scaffold_flogo_app.py --analysis <work>/analysis --work <work> [--module <Module_slug>] [--app-name <AppName>]
                               [--apps-dir <FLOGO_APPS_DIR>] [--mcp all|explicit] [--mcp-path /mcp] [--force]

Required: --analysis (the folder analyze_bw6.py wrote, step 1) and --work; $FDA (see AGENT.md).
--module is the analyzer's file prefix (module name with non-alphanumerics as '_', e.g. Acme.Orders.API -> Acme_Orders_API);
  default: the only *.bw6spec.json in --analysis.
--app-name defaults to the module name without dots (same default as modernization_plan.py).
--apps-dir defaults to FLOGO_APPS_DIR from skills-library/.claude/skills/config.md (relative to config.md).
--mcp explicit (default) exposes only operations configured as MCP tools in BW; 'all' reproduces BW's
  behaviour for modules without MCP configuration (every operation becomes a tool).
--mcp-path is the MCP endpoint path (default /mcp).
--force deletes an existing <AppName>.flogo and its fda history first (otherwise the script refuses).
"""
import argparse
import glob
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fdalib import Fda, config_value, fda_path  # noqa: E402
from modernization_plan import flogo_app_name  # noqa: E402

ANALYZE = "python analyze_bw6.py <bw6-module-dir> --out <work>/analysis"


def jschema(s):
    return {"type": "json", "value": json.dumps(s), "fe_metadata": json.dumps(s)}


def resolve(schema, comps, depth=0):
    """Inline #/components/schemas refs so every schema is self-contained (draft-04 style)."""
    if depth > 12:
        return {"type": "object"}
    if isinstance(schema, dict):
        if "$ref" in schema:
            return resolve(comps[schema["$ref"].split("/")[-1]], comps, depth + 1)
        return {k: resolve(v, comps, depth + 1) for k, v in schema.items() if k not in ("uniqueItems", "exampleSetFlag")}
    if isinstance(schema, list):
        return [resolve(x, comps, depth + 1) for x in schema]
    return schema


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--analysis", required=True, help="REQUIRED. folder analyze_bw6.py wrote (<work>/analysis)")
    ap.add_argument("--module", help="analyzer file prefix, e.g. Acme_Orders_API (default: the only *.bw6spec.json "
                                     "in --analysis)")
    ap.add_argument("--app-name", help="Flogo app name: letters, digits, _ (default: the module name without dots)")
    ap.add_argument("--apps-dir", help="target apps folder (default: FLOGO_APPS_DIR from config.md)")
    ap.add_argument("--work", required=True, help="REQUIRED. folder for plan.json and the schema files fda reads")
    ap.add_argument("--mcp", choices=["explicit", "all"], default="explicit",
                    help="explicit (default): only operations configured as MCP tools in BW; all: every operation")
    ap.add_argument("--mcp-path", default="/mcp", help="MCP endpoint path (default /mcp)")
    ap.add_argument("--force", action="store_true", help="delete an existing <AppName>.flogo and its fda history first")
    a = ap.parse_args()

    # ---- inputs: fail fast, before anything is created or deleted
    if not os.path.isdir(a.analysis):
        sys.exit(f"error: --analysis {a.analysis} does not exist. Run step 1 first: {ANALYZE}")
    specs = sorted(os.path.basename(p)[:-len(".bw6spec.json")] for p in glob.glob(os.path.join(a.analysis, "*.bw6spec.json")))
    if not a.module:
        if len(specs) != 1:
            sys.exit(f"error: --module is needed: {len(specs)} analyzer specs in {a.analysis}"
                     + (f" ({', '.join(specs)})" if specs else f" - run step 1 first: {ANALYZE}"))
        a.module = specs[0]
    spec_path = os.path.abspath(os.path.join(a.analysis, a.module + ".bw6spec.json"))
    if not os.path.isfile(spec_path):
        sys.exit(f"error: {spec_path} not found - run step 1 ({ANALYZE}) for this module"
                 + (f"; specs present: {', '.join(specs)}" if specs else ""))
    spec = json.load(open(spec_path, encoding="utf-8"))
    if not spec.get("operations"):
        sys.exit(f"error: {spec['module']} has no REST operations (shared module or non-REST starters) - nothing to scaffold")
    oas_path = os.path.abspath(os.path.join(a.analysis, a.module + ".openapi.json"))
    if not os.path.exists(oas_path):
        sys.exit(f"{oas_path} not found: the module has no REST operations with an OpenAPI descriptor")
    a.app_name = a.app_name or flogo_app_name(spec["module"])
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", a.app_name):
        sys.exit(f"--app-name {a.app_name!r}: letters, digits and _ only, starting with a letter")
    a.apps_dir = a.apps_dir or config_value("FLOGO_APPS_DIR", path_relative=True)
    if not a.apps_dir:
        sys.exit("error: target apps folder unknown: pass --apps-dir <FLOGO_APPS_DIR> or set FLOGO_APPS_DIR in "
                 "skills-library/.claude/skills/config.md (copy config.example.md)")
    if not a.mcp_path.startswith("/"):
        sys.exit(f"--mcp-path {a.mcp_path!r} must start with '/'")
    fda_path()  # $FDA must be valid BEFORE --force deletes anything
    oas = json.load(open(oas_path, encoding="utf-8"))
    os.makedirs(a.work, exist_ok=True)
    work = os.path.abspath(a.work)

    def tmp(name, obj):
        p = os.path.join(work, name)
        json.dump(obj, open(p, "w", encoding="utf-8"), indent=1)
        return p

    os.makedirs(a.apps_dir, exist_ok=True)  # FLOGO_APPS_DIR may not exist yet on a fresh machine
    app = os.path.abspath(os.path.join(a.apps_dir, a.app_name + ".flogo"))
    hist = os.path.join(os.path.dirname(app), ".flogodesign", "history", a.app_name)
    if os.path.exists(app):
        if not a.force:
            sys.exit(f"{app} exists. Re-run with --force to rebuild it from scratch (deletes it and its fda history).")
        os.remove(app)
        shutil.rmtree(hist, ignore_errors=True)

    fda = Fda(app)
    fda("cp", a.app_name, f"Flogo modernization of BW6 {spec['module']}: REST API + MCP server for the same operations")
    fda("csp", "BW6Spec", "--specFile", oas_path)
    fda("cas", "BW6Spec", "logReply")

    d = json.load(open(app, encoding="utf-8"))
    rest_trigger = d["triggers"][0]["id"]
    flows = {r["id"].split(":", 1)[1]: r for r in d["resources"]}
    fda("cap", "REST_PORT", "number", str(spec["http"]["flogoPort"]))
    fda("sa", "trigger", f"{rest_trigger}.settings.port", "REST_PORT", "--configType", "app-property")

    comps = oas["components"]["schemas"]
    plan = {"app": app, "appName": a.app_name, "module": spec["module"], "restTrigger": rest_trigger,
            "spec": spec_path,
            "restPort": spec["http"]["flogoPort"], "mcpPort": spec["mcp"]["flogoPort"], "mcpPath": a.mcp_path, "ops": []}
    missing = [f"{o['method']} {o['path']}" for o in spec["operations"] if not o.get("flogoFlow")]
    if missing:
        sys.exit("these BW operations have no path in the module's OpenAPI descriptor, so no flow can be generated: "
                 + ", ".join(missing) + " - fix the descriptor (or the binding's basePath) and re-run analyze_bw6.py")
    for op in spec["operations"]:
        flow = next((f for f in flows if f.startswith(op["flogoFlow"] + "_")), None)
        if flow is None:
            sys.exit(f"cas created no flow for {op['method']} {op['path']} ({op['flogoFlow']})")
        item = oas["paths"][op["path"]][op["method"].lower()]
        qp = [p for p in item.get("parameters", []) if p["in"] == "query"]
        pp = [p for p in item.get("parameters", []) if p["in"] == "path"]
        body = resolve(item.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema"), comps)
        ok = resolve(((item.get("responses", {}).get("200") or {}).get("content", {}).get("application/json", {})
                      .get("schema")) or {"type": "object"}, comps)
        # 1) cas leaves query/path params - and, next to a path param, the JSON body - out of the flow inputs. Over REST
        #    the trigger still passes them, but a subflow call (the mcp_<tool> flows) only passes DECLARED inputs.
        meta_in = {r["name"] for r in flows[flow]["data"]["metadata"].get("input", [])}
        if (qp and "queryParams" not in meta_in) or (pp and "pathParams" not in meta_in) or (body and "body" not in meta_in):
            props = {}
            for kind, plist in (("queryParams", qp), ("pathParams", pp)):
                if plist:
                    props[kind] = {"type": "object", "properties": {
                        p["name"]: {"type": p.get("schema", {}).get("type", "string")} for p in plist}}
            if body:
                props["body"] = body
            props.update({"headers": {"type": "object"}, "requestURI": {"type": "string"}, "method": {"type": "string"}})
            fda("sms", f"{flow}.input", "--json-schema", json.dumps({"type": "object", "properties": props}))
        # 2) cas writes the handler's queryParams/pathParams schema as a parameter ARRAY, but the tr_rest
        #    runtime only parses a JSON-schema OBJECT and otherwise delivers queryParams = null. 'required'
        #    stays out: the trigger would reject a missing parameter with a plain-text 400 before the flow
        #    runs, while the flow answers with JSON.
        handler = next(h for h in d["triggers"][0]["handlers"] if h["action"]["settings"]["flowURI"] == f"res://flow:{flow}")
        for kind, plist in (("queryParams", qp), ("pathParams", pp)):
            if plist:
                obj = {"type": "object", "properties": {p["name"]: {"type": p.get("schema", {}).get("type", "string")} for p in plist}}
                fe = handler["schemas"]["output"].get(kind, {}).get("value", "[]")
                fda("sa", "handler", f"{rest_trigger}.{handler['name']}.schemas.output.{kind}", "--jsonFile",
                    tmp(f"{flow}_{kind}.json", {"type": "json", "value": json.dumps(obj), "fe_metadata": fe}), "--force")
        mcp = dict(op["mcp"])
        mcp["exposed"] = mcp["explicit"] or (a.mcp == "all")
        plan["ops"].append({"flow": flow, "method": op["method"], "path": op["path"], "mcp": mcp,
                            "query": [p["name"] for p in qp], "pathParams": [p["name"] for p in pp],
                            "requiredQuery": [p["name"] for p in qp if p.get("required")],
                            "body": body, "ok": ok, "bwActivities": (op.get("implementation") or {}).get("activities", []),
                            "literals": op.get("literals", [])})

    # 3) MCP: one thin flow per tool (one trigger per flow keeps standard wiring and fda cm clean;
    #    the business logic stays in the REST flow, reached through a subflow call)
    tools = [o for o in plan["ops"] if o["mcp"]["exposed"]]
    if tools:
        # the MCP trigger's serverPort field is a STRING (tr_rest's port is a number); a number property
        # bound to it is flagged by the designer: 'Type of field "HTTP Server Port" (string) differs ...'
        fda("cap", "MCP_PORT", "string", str(spec["mcp"]["flogoPort"]))
        fda("ct", "mcp_server", "tr_mcpserver", f"MCP server for {spec['module']}")
        fda("sa", "trigger", "mcp_server.settings.serverName", spec["module"])
        fda("sa", "trigger", "mcp_server.settings.serverPort", "MCP_PORT", "--configType", "app-property")
        fda("sa", "trigger", "mcp_server.settings.serverEndpointPath", a.mcp_path)
    for o in tools:
        m = o["mcp"]
        mf = "mcp_" + re.sub(r"[^A-Za-z0-9_]", "_", m["name"])
        o["mcpFlow"] = mf
        fda("cf", mf, f"MCP {m['kind']} {m['name']}: calls {o['flow']} and returns its body")
        fda("cth", mf, "mcp_server", f"MCP {m['kind']} {m['name']}", "--mcpHandlerType",
            "Tool" if m["kind"] == "tool" else "Resource", "--mcpHandlerName", m["name"],
            "--mcpHandlerDescription", m["description"] or m["name"])
        fda("wth", mf, f"mcp_server.{mf}")
        props = {n: {"type": "string"} for n in o["query"] + o["pathParams"]}
        for n, s in ((o["body"] or {}).get("properties") or {}).items():
            props.setdefault(n, s)
        args = {"$schema": "http://json-schema.org/draft-04/schema#", "type": "object", "properties": props}
        required = o["requiredQuery"] + o["pathParams"] + [f for f in (o["body"] or {}).get("required", []) if f in props]
        if required:
            args["required"] = sorted(set(required), key=required.index)
        fda("sa", "handler", f"mcp_server.{mf}.schemas.output.arguments", "--jsonFile", tmp(f"{mf}_args.json", jschema(args)), "--force")
        # type the tool flow's 'arguments' input too: the designer flags $flow.arguments.<field> on an untyped object
        fda("sms", f"{mf}.input", "--json-schema", json.dumps({"type": "object", "properties": {
            "arguments": {k: v for k, v in args.items() if k != "$schema"}}}))
        # tr_mcpserver reply contract: response.data (string) = tool text content; non-empty response.error = isError
        resp = {"$schema": "http://json-schema.org/draft-04/schema#", "type": "object",
                "properties": {"data": {"type": "string"}, "error": {"type": "string"}}}
        fda("sa", "handler", f"mcp_server.{mf}.schemas.reply.response", "--jsonFile", tmp(f"{mf}_resp.json", jschema(resp)), "--force")
        fda("sa", "handler", f"mcp_server.{mf}.settings.readOnlyToolHint",
            "true" if (m.get("scope") or "").lower() == "read" or o["method"] == "GET" else "false", "-C", "boolean")
        fda("ca", mf, "CallOperation", "act_default_subflow", f"Run {o['flow']} (the REST operation)")
        fda("sa", "activity", f"{mf}.CallOperation.settings.flowURI", f"res://flow:{o['flow']}")
        if o["query"]:
            fda("mm", f"{mf}.CallOperation.input.queryParams", "=$flow.arguments")
        if o["pathParams"]:
            fda("mm", f"{mf}.CallOperation.input.pathParams", "=$flow.arguments")
        if o["body"]:
            fda("mm", f"{mf}.CallOperation.input.body", "=$flow.arguments")
        fda("ca", mf, "Return", "act_default_actreturn", "Return the REST body as the tool result")
        body = "$activity[CallOperation].responseBody.body"
        fda("mm", f"{mf}.Return.input.mappings.response.mapping.data", f"=utility.renderJSON({body}, false)")
        fda("mm", f"{mf}.Return.input.mappings.response.mapping.error",
            f'=$activity[CallOperation].code >= 400 ? utility.renderJSON({body}, false) : ""')

    json.dump(plan, open(os.path.join(work, "plan.json"), "w", encoding="utf-8"), indent=1)
    fails, summary, _ = fda.cm()
    print(f"\napp      : {app}")
    print(f"flows    : {[o['flow'] for o in plan['ops']]} + MCP {[o.get('mcpFlow') for o in tools]}")
    print(f"ports    : REST {plan['restPort']}, MCP {str(plan['mcpPort']) + a.mcp_path if tools else '-'}")
    print(f"cm       : {summary[-1].split(')', 1)[-1].strip() if summary else '?'}")
    for f in fails:
        print("  FAIL", re.sub(r"\s+", " ", f)[:140])
    print(f"plan     : {os.path.join(work, 'plan.json')}  -> next: write the business logic with flogo_logic_lib.py")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
