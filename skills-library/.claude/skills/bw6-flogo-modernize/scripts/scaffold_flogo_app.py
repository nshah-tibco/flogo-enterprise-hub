#!/usr/bin/env python3
"""Build the generic part of a Flogo app from analyze_bw6.py output, using fda only.

  project -> Flogo-ready OpenAPI spec -> cas skeleton (one flow per REST operation)
  -> REST/MCP port app properties -> query/path parameters fixed so they reach the flows
  -> MCP Server trigger with one thin flow per MCP tool: subflow call to the REST flow -> {data, error}

Writes <work>/plan.json for the business-logic step (see flogo_logic_lib.py) and stops before any
operation-specific logic: every REST flow still answers with the cas logReply placeholder.

Usage:
  python scaffold_flogo_app.py --analysis <dir> --module <Module_slug> --app-name <AppName>
                               --apps-dir <FLOGO_APPS_DIR> --work <dir> [--mcp all|explicit] [--force]

--module is the analyzer's file prefix (module name with non-alphanumerics as '_', e.g. Acme.Orders.API -> Acme_Orders_API).
--mcp explicit (default) exposes only operations configured as MCP tools in BW; 'all' reproduces BW's
  behaviour for modules without MCP configuration (every operation becomes a tool).
--force deletes an existing <AppName>.flogo and its fda history first (otherwise the script refuses).
"""
import argparse
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fdalib import Fda  # noqa: E402


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
    ap.add_argument("--analysis", required=True)
    ap.add_argument("--module", required=True)
    ap.add_argument("--app-name", required=True)
    ap.add_argument("--apps-dir", required=True)
    ap.add_argument("--work", required=True, help="folder for plan.json and the schema files fda reads")
    ap.add_argument("--mcp", choices=["explicit", "all"], default="explicit")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", a.app_name):
        sys.exit("--app-name: letters, digits and _ only, starting with a letter")
    spec = json.load(open(os.path.join(a.analysis, a.module + ".bw6spec.json"), encoding="utf-8"))
    oas_path = os.path.abspath(os.path.join(a.analysis, a.module + ".openapi.json"))
    if not os.path.exists(oas_path):
        sys.exit(f"{oas_path} not found: the module has no REST operations with an OpenAPI descriptor")
    oas = json.load(open(oas_path, encoding="utf-8"))
    os.makedirs(a.work, exist_ok=True)
    work = os.path.abspath(a.work)

    def tmp(name, obj):
        p = os.path.join(work, name)
        json.dump(obj, open(p, "w", encoding="utf-8"), indent=1)
        return p

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
            "spec": os.path.abspath(os.path.join(a.analysis, a.module + ".bw6spec.json")),
            "restPort": spec["http"]["flogoPort"], "mcpPort": spec["mcp"]["flogoPort"], "ops": []}
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
        # 1) cas leaves query/path params out of the flow inputs
        meta_in = {r["name"] for r in flows[flow]["data"]["metadata"].get("input", [])}
        if (qp and "queryParams" not in meta_in) or (pp and "pathParams" not in meta_in):
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
        fda("sa", "trigger", "mcp_server.settings.serverEndpointPath", "/mcp")
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
        if o["requiredQuery"] + o["pathParams"]:
            args["required"] = o["requiredQuery"] + o["pathParams"]
        fda("sa", "handler", f"mcp_server.{mf}.schemas.output.arguments", "--jsonFile", tmp(f"{mf}_args.json", jschema(args)), "--force")
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
    print(f"ports    : REST {plan['restPort']}, MCP {plan['mcpPort'] if tools else '-'}")
    print(f"cm       : {summary[-1].split(')', 1)[-1].strip() if summary else '?'}")
    for f in fails:
        print("  FAIL", re.sub(r"\s+", " ", f)[:140])
    print(f"plan     : {os.path.join(work, 'plan.json')}  -> next: write the business logic with flogo_logic_lib.py")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
