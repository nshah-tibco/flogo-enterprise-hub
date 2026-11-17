#!/usr/bin/env python3
"""Build an AI orchestrator over modernized Flogo MCP servers (worked example: no BW6 source - an agent that replaces a
browser-side tool loop + Node MCP proxy). Everything is created with the Flogo Design CLI (fda) through fdalib/Logic.

  POST /api/chat   {message, conversationId?} -> {answer, conversationId}
                   Agentic AI LLM Client (conversation memory per conversationId) with MCP connections to the
                   cylinder-operations server (search / status / dispatch) and the document server (RAG question
                   answering with citations). The LLM plans and calls the tools itself.
  GET  /api/health {ok, service, model}

Usage:
  python gas_ops_orchestrator_build.py --apps-dir <FLOGO_APPS_DIR> --work <dir> [--app-name GasOpsAIOrchestrator]
      [--port 18090] --mcp GasCylinderOps=http://localhost:16100/mcp --mcp GasDocs=http://localhost:8412/mcp
Needs $FDA. The LLM API key is a password property (SECRET: placeholder); supply the key at run time:
  FLOGO_APP_PROPS_ENV=auto LLM_API_KEY=sk-... ./GasOpsAIOrchestrator
"""
import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from fdalib import Fda  # noqa: E402
from flogo_logic_lib import Logic  # noqa: E402

SYSTEM_PROMPT = (
    "You are the Industrial Gas Smart Operations AI Assistant, powered by TIBCO Flogo MCP tools. "
    "You have live cylinder-operations tools (search gas stock by gas type and yard location, get a cylinder's "
    "status, dispatch a cylinder) and a document tool (post-ragimgquery) that answers questions from the company's "
    "safety data sheets, SOPs and policies with citations. Always call a tool to get current data or document "
    "facts - never make assumptions about inventory or procedures. For document questions pass the user's question "
    "to post-ragimgquery and keep its citations and Sources section in your answer. Be concise and professional and "
    "reference specific cylinder IDs and figures from tool results. Before dispatching, check the cylinder's status "
    "and certificate expiry; when dispatching, confirm the cylinder ID and destination clearly. "
    "searchGasStock matches EXACT values: gasType is one of Argon, Nitrogen, Oxygen, Hydrogen (no grade words such as "
    "'high-purity' - read purity from the results) and location is one of Houston Yard A, Houston Yard B, Dallas "
    "Distribution Center. To find a gas everywhere, search each location. Compare every certificate expiry date with "
    "today's date: a date before today means the certificate has EXPIRED and the cylinder is NOT ready for use or "
    "dispatch, even when its status is Available - always say so explicitly. A cylinder is ready only when its status "
    "is Available and its certificate has not expired.")
# The LLM has no clock: append today's date on every call (date part of datetime.currentDate(), e.g. 2026-11-16)
assert '"' not in SYSTEM_PROMPT, "the prompt is embedded in a double-quoted Flogo string"
SYSTEM_PROMPT_EXPR = ('=string.concat("' + SYSTEM_PROMPT + " Today's date is " + '", '
                      'string.substring(datetime.currentDate(), 0, 10), ".")')

ERR = {"type": "object", "properties": {"error": {"type": "string"}, "message": {"type": "string"}}}
OPENAPI = {
    "openapi": "3.0.3",
    "info": {"title": "Gas Ops AI Orchestrator API", "version": "1.0.0",
             "description": "AI assistant for gas-cylinder operations and documents, over Flogo MCP tools"},
    "paths": {
        "/api/chat": {"post": {
            "operationId": "chat", "summary": "Ask the AI assistant",
            "requestBody": {"required": True, "content": {"application/json": {"schema": {
                "type": "object", "required": ["message"],
                "properties": {"message": {"type": "string"}, "conversationId": {"type": "string"}}}}}},
            "responses": {
                "200": {"description": "The assistant's answer", "content": {"application/json": {"schema": {
                    "type": "object", "properties": {"answer": {"type": "string"}, "conversationId": {"type": "string"}}}}}},
                "400": {"description": "Invalid or missing input", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "500": {"description": "Unexpected error", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}}}}},
        "/api/health": {"get": {
            "operationId": "health", "summary": "Service check",
            "responses": {"200": {"description": "Service is up", "content": {"application/json": {"schema": {
                "type": "object", "properties": {"ok": {"type": "boolean"}, "service": {"type": "string"},
                                                 "model": {"type": "string"}}}}}}}}}},
    "components": {"schemas": {"ErrorResponse": ERR}},
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apps-dir", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--app-name", default="GasOpsAIOrchestrator")
    ap.add_argument("--port", type=int, default=18090)
    ap.add_argument("--model", default="gpt-5.5")
    ap.add_argument("--mcp", action="append", default=[], metavar="NAME=URL", required=True)
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    os.makedirs(a.apps_dir, exist_ok=True)
    app = os.path.abspath(os.path.join(a.apps_dir, a.app_name + ".flogo"))
    if os.path.exists(app):
        os.remove(app)
        shutil.rmtree(os.path.join(a.apps_dir, ".flogodesign", "history", a.app_name), ignore_errors=True)
    spec_path = os.path.join(os.path.abspath(a.work), "orchestrator.openapi.json")
    json.dump(OPENAPI, open(spec_path, "w", encoding="utf-8"), indent=1)

    # ---------------------------------------------------------------- project + REST operations (cas)
    fda = Fda(app)
    fda("cp", a.app_name, "AI assistant for gas-cylinder operations and documents over Flogo MCP tools")
    fda("csp", "OrchestratorAPI", "--specFile", spec_path)
    fda("cas", "OrchestratorAPI", "logReply")
    d = json.load(open(app, encoding="utf-8"))
    rest = d["triggers"][0]["id"]
    fda("cap", "REST_PORT", "number", str(a.port))
    fda("sa", "trigger", f"{rest}.settings.port", "REST_PORT", "--configType", "app-property")
    flows = {r["id"].split(":", 1)[1] for r in d["resources"]}
    chat, health = next(f for f in flows if f.startswith("chat_")), next(f for f in flows if f.startswith("health_"))
    op = lambda flow, path, method, body, ok: {"flow": flow, "method": method, "path": path, "query": [], "pathParams": [],
                                               "requiredQuery": [], "body": body, "ok": ok, "bwActivities": [],
                                               "mcp": {"exposed": False}}
    paths = OPENAPI["paths"]
    plan = {"app": app, "appName": a.app_name, "module": a.app_name, "restTrigger": rest, "restPort": a.port, "ops": [
        op(chat, "/api/chat", "POST", paths["/api/chat"]["post"]["requestBody"]["content"]["application/json"]["schema"],
           paths["/api/chat"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]),
        op(health, "/api/health", "GET", None, paths["/api/health"]["get"]["responses"]["200"]["content"]["application/json"]["schema"])]}
    plan_path = os.path.join(os.path.abspath(a.work), "plan.json")
    json.dump(plan, open(plan_path, "w", encoding="utf-8"), indent=1)

    L = Logic(plan_path)
    # ---------------------------------------------------------------- app properties
    L.prop("LLM_PROVIDER", "string", "OpenAI")
    L.prop("LLM_MODEL", "string", a.model)
    L.prop("LLM_API_KEY", "string", "YOUR_OPENAI_API_KEY", secret=True)   # the LLM Client's apiKey is a password field

    # ---------------------------------------------------------------- MCP connections (one per server)
    conn_ids = []
    for spec in a.mcp:
        name, url = spec.split("=", 1)
        L.fda("cc", name, "con_mcpserverconfig")
        for k, v in (("name", name), ("serverType", "http"), ("serverUrl", url), ("httpTransportType", "streamable"),
                     ("authType", "None"), ("description", f"Flogo MCP server {name}")):
            L.fda("sa", "connection", f"{name}.settings.{k}", v)
        cur = json.load(open(app, encoding="utf-8"))
        conn_ids.append(next(i for i, c in cur["connections"].items() if c.get("name") == name))

    # ---------------------------------------------------------------- GET /api/health
    L.response(health, "ConfigureHTTPResponse", 200, "HealthBody", plan["ops"][1]["ok"],
               {"ok": True, "service": a.app_name, "model": '=$property["LLM_MODEL"]'})

    # ---------------------------------------------------------------- POST /api/chat
    L.unlink_placeholder(chat)
    L.log(chat, '=string.concat("chat conversationId=", coerce.toString($flow.body.conversationId))')
    L.compute(chat, "Conversation", {"conversationId": (
        "string", '=coerce.toString($flow.body.conversationId) != "" ? $flow.body.conversationId : utils.uuid()')},
        desc="Keep the caller's conversation id, or start a new conversation")
    L.require_params(chat, after="Log_API", next_step="Conversation", body_fields=("message",))
    L.llm(chat, "Agent", SYSTEM_PROMPT_EXPR, "=$flow.body.message", desc="Plan and call the MCP tools, then answer",
          key_prop="LLM_API_KEY", temperature=1)
    L.fda("sa", "activity", f"{chat}.Agent.settings.mcpServers", "--jsonValue", json.dumps([f"conn://{i}" for i in conn_ids]))
    L.fda("sa", "activity", f"{chat}.Agent.settings.conversationStoreType", "Memory")
    L.fda("sa", "activity", f"{chat}.Agent.settings.memoryMaxSize", "20", "-C", "number")
    L.fda("mm", f"{chat}.Agent.input.conversationId", "=$activity[Conversation].output.conversationId")
    L.link(chat, "Conversation", "Agent")
    L.response(chat, "ConfigureHTTPResponse", 200, "ChatBody", plan["ops"][0]["ok"], {
        "answer": "=$activity[Agent].response", "conversationId": "=$activity[Conversation].output.conversationId"})
    L.link(chat, "Agent", "ConfigureHTTPResponse")
    return L.finish()


if __name__ == "__main__":
    sys.exit(main())
