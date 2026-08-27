#!/usr/bin/env python3
"""Build RealEstateAIOrchestrator.flogo with fda only. Secrets from env.
WebSocket trigger -> agentactivity (MCP + 5 A2A) -> wswritedata."""
import subprocess, os, sys, json, tempfile

FDA  = os.environ["FDA"]
DIR  = os.path.dirname(os.path.abspath(__file__))
FILE = os.path.join(DIR, "RealEstateAIOrchestrator.flogo")

LLM_PROVIDER="OpenAI"; LLM_BASE="https://api.openai.com/v1"; LLM_MODEL="gpt-5.5"
LLM_KEY = os.environ["LLM_API_KEY"]
WS_PORT="9590"; WS_PATH="/realestate"
MCP_URL="http://localhost:9592/realestate-mls"
A2A=[("book_property_showing","9593"),("update_lead_stage","9594"),
     ("send_property_recommendations","9595"),("log_followup_task","9596"),
     ("send_confirmation_email","9597")]

def fda(*args, allow_fail=False):
    r=subprocess.run([FDA,*map(str,args),"-f",FILE],capture_output=True,text=True)
    out=(r.stdout or "")+(r.stderr or "")
    if "(ERROR)" in out and not allow_fail:
        print("FAILED:"," ".join(map(str,args))); print(out[-1600:]); sys.exit(1)
    print("  ok:"," ".join(str(a) for a in args[:3])); return out

def jtmp(obj):
    f=tempfile.NamedTemporaryFile("w",suffix=".json",delete=False,encoding="utf-8")
    json.dump(obj,f); f.close(); return f.name

def cid():
    conns=json.load(open(FILE))["connections"]
    items=list(conns.values()) if isinstance(conns,dict) else conns
    return {c["name"]:c["id"] for c in items}

if os.path.exists(FILE): os.remove(FILE)

SYS_PROMPT = (
"You are a friendly, professional AI home-search assistant for a residential real estate brokerage, "
"chatting directly with a home buyer or seller (a lead) in a chat window. Your job is to help them "
"explore their profile and saved criteria, search active listings, understand the local market, book "
"property showings, get curated home recommendations by email, and request an agent follow-up — all "
"in natural language.\n\n"
"IDENTIFY THE LEAD FIRST. Ask for or accept a lead id (format LEAD-2026-NNNNN), email, or phone, then "
"call GetLeadProfile to load their record. Never guess a lead id. Only act on the identified lead's own "
"data — never another person's.\n\n"
"READ TOOLS (MCP, read-only — use these to answer questions; each returns rows you must filter/summarize):\n"
"• GetLeadProfile — the lead's CRM record: name, contact, buyer/seller type, funnel stage, budget, "
"preferred city/zip/beds/baths, timeline, source, assigned agent id.\n"
"• GetLeadActivity — their engagement history (searches, listings viewed/saved, emails opened, recommendations, stage changes).\n"
"• SearchListings — the property catalog (MLS). Filter the returned rows to the lead's city, budget, and bed/bath needs; only offer Active listings for tours.\n"
"• GetAssignedAgent — the lead's human agent (name, email, phone, brokerage, service area). Use with the lead's assigned_agent_id.\n"
"• GetLeadAppointments — the lead's scheduled showings and their status.\n"
"• GetAreaMarketInsights — market stats by city/zip (median price, avg days on market, inventory, $/sqft, YoY change).\n\n"
"ACTION AGENTS (A2A, these WRITE — always confirm the details with the lead before calling):\n"
"• book_property_showing(lead_id, listing_id, preferred_datetime, notes?) — books a tour. Only book Active listings; "
"if the listing is Pending or Sold, say so and suggest alternatives. The assigned agent is derived automatically.\n"
"• update_lead_stage(lead_id, new_stage, reason?) — moves the lead through the funnel "
"(New, Nurturing, Active, Under Contract, Closed, Lost). After a lead successfully books their first showing, "
"advance them to 'Active' with a short reason. Only move stages forward for sensible reasons; never to 'Under Contract', "
"'Closed', or 'Lost' on your own.\n"
"• send_property_recommendations(lead_id, listing_ids, summary?) — records the curated listings you recommended "
"(comma-separated LST ids). To actually email them, also call the email agent.\n"
"• log_followup_task(lead_id, task_type, due_date?, notes?) — creates a follow-up task for the lead's agent. "
"task_type must be exactly Call, Text, or Email.\n"
"• send_confirmation_email(subject, body) — sends ONE email to the demo mailbox. Send it once, last, and only when "
"the lead asks or right after you complete a booking/recommendation. Compose a clear subject and a friendly, specific body.\n\n"
"RULES:\n"
"1. Confirm before every write (booking, stage change, recommendation, follow-up, email). Echo back what you will do.\n"
"2. Never invent ids, addresses, prices, or dates — use only values returned by tools or given by the lead. "
"Pass datetimes as 'YYYY-MM-DD HH:MM' and dates as 'YYYY-MM-DD'.\n"
"3. Typical full flow: identify lead → search/insight → confirm & book_property_showing → update_lead_stage to Active "
"→ offer a confirmation email.\n"
"4. Respect lead state: a lead 'Under Contract' or 'Closed' should not book new tours without an explicit request; "
"re-engage a 'Lost' lead only gently and briefly.\n"
"5. OUT OF SCOPE — politely decline and, if useful, offer an agent follow-up: making or negotiating prices/offers, "
"legal, mortgage, or financial/investment advice, editing MLS/listing data, accessing anyone else's lead record, or "
"promising anything on the human agent's behalf beyond scheduling and follow-up.\n"
"6. Be concise, warm, and specific. Summarize listings as short bullets (address — price — beds/baths — city). "
"After a write, briefly confirm what was done and any id returned."
)

print("== project + properties ==")
fda("cp","RealEstateAIOrchestrator","Real Estate AI Orchestrator")
fda("cap","AgenticAI.OpenAIConn.LLM_Provider","string",LLM_PROVIDER)
fda("cap","AgenticAI.OpenAIConn.API_Key","string",LLM_KEY)
fda("cap","AgenticAI.OpenAIConn.LLM_Base_URL","string",LLM_BASE)
fda("cap","LLM_Model","string",LLM_MODEL)
fda("cap","WebSocket_PORT","number",WS_PORT)

print("== connections ==")
fda("cc","OpenAIConn","con_llmprovider")
fda("sa","connection","OpenAIConn.settings.llmProvider","AgenticAI.OpenAIConn.LLM_Provider","-C","app-property")
fda("sa","connection","OpenAIConn.settings.apiKey","AgenticAI.OpenAIConn.API_Key","-C","app-property")
fda("sa","connection","OpenAIConn.settings.llmProviderUrl","AgenticAI.OpenAIConn.LLM_Base_URL","-C","app-property")

fda("cc","RealEstateMCPServer","con_mcpserverconfig")
fda("sa","connection","RealEstateMCPServer.settings.serverType","http")
fda("sa","connection","RealEstateMCPServer.settings.serverUrl",MCP_URL)
fda("sa","connection","RealEstateMCPServer.settings.httpTransportType","streamable")

for name,port in A2A:
    cn=f"{name}A2AServer"
    fda("cc",cn,"con_a2aserverconnection")
    fda("sa","connection",f"{cn}.settings.serverUrl",f"http://localhost:{port}")

ids=cid()
OPENAI_REF="conn://"+ids["OpenAIConn"]
MCP_REF="conn://"+ids["RealEstateMCPServer"]
A2A_REFS=["conn://"+ids[f"{n}A2AServer"] for n,_ in A2A]
print("  MCP_REF =",MCP_REF)
print("  A2A_REFS =",A2A_REFS)

print("== trigger + flow ==")
fda("ct","WebsocketServer","tr_wsserver","WebSocket server")
fda("sa","trigger","WebsocketServer.settings.port","WebSocket_PORT","-C","app-property")

fda("cf","Orchestrator_Flow","Real Estate orchestrator flow")
fda("ca","Orchestrator_Flow","AIAgent","act_agenticai_agentactivity","AI Agent")
fda("ca","Orchestrator_Flow","WebsocketWriteData","act_websocket_wswritedata","Write to websocket")

print("== AIAgent settings ==")
fda("sa","activity","Orchestrator_Flow.AIAgent.settings.llmProviderConnection",OPENAI_REF)
fda("sa","activity","Orchestrator_Flow.AIAgent.settings.model","LLM_Model","-C","app-property")
fda("sa","activity","Orchestrator_Flow.AIAgent.settings.temperature","0.4","--type","number")
fda("sa","activity","Orchestrator_Flow.AIAgent.settings.enableGuardrails","true","--type","boolean")
fda("sa","activity","Orchestrator_Flow.AIAgent.settings.redactSensitiveData","true","--type","boolean")
fda("sa","activity","Orchestrator_Flow.AIAgent.settings.responseType","Text")
fda("sa","activity","Orchestrator_Flow.AIAgent.settings.conversationStoreType","Memory")
fda("sa","activity","Orchestrator_Flow.AIAgent.settings.memoryMaxSize","100","--type","number")
fda("sa","activity","Orchestrator_Flow.AIAgent.settings.systemPrompt",SYS_PROMPT)
fda("sa","activity","Orchestrator_Flow.AIAgent.settings.mcpServers","--jsonValue",json.dumps([MCP_REF]))
fda("sa","activity","Orchestrator_Flow.AIAgent.settings.remoteAgents","--jsonValue",json.dumps(A2A_REFS))

print("== mappings ==")
fda("mm","Orchestrator_Flow.AIAgent.input.userPrompt","=coerce.toString($flow.content)")
fda("mm","Orchestrator_Flow.WebsocketWriteData.input.message","=$activity[AIAgent].response")
fda("mm","Orchestrator_Flow.WebsocketWriteData.input.wsconnection","=$flow.wsconnection")

print("== handler + wsserver fixes ==")
fda("cth","Orchestrator_Flow","WebsocketServer","Real Estate orchestrator handler")
fda("sa","handler","WebsocketServer.Orchestrator_Flow.settings.path",WS_PATH)
fda("sa","handler","WebsocketServer.Orchestrator_Flow.settings.mode","Data")
fda("sa","handler","WebsocketServer.Orchestrator_Flow.settings.format","String")
fda("wth","Orchestrator_Flow","WebsocketServer.Orchestrator_Flow","--force",
    "--input","content:any,wsconnection:any,pathParams:params,queryParams:params,headers:object","--inputs-only")

hdr={"type":"object","properties":{k:{"type":"string","visible":False} for k in
     ["Accept","Accept-Charset","Accept-Encoding","Content-Type","Content-Length","Connection",
      "Cookie","Pragma","Sec-Websocket-Key","Sec-Websocket-Version","Upgrade"]},"required":[]}
fda("cs","OrcWsHeaders",json.dumps(hdr))
fda("sa","handler","WebsocketServer.Orchestrator_Flow.schemas.output.headers","OrcWsHeaders","-C","schema","--force")

meta_input=[{"name":"pathParams","type":"params"},{"name":"queryParams","type":"params"},
            {"name":"headers","type":"object"},{"name":"content","type":"any"},
            {"name":"wsconnection","type":"any"}]
fda("sa","flow","Orchestrator_Flow.metadata.input","--jsonFile",jtmp(meta_input),"--force")

print("\nOrchestrator build complete:",FILE)
