#!/usr/bin/env python3
"""Build RealEstateA2AServers.flogo with fda only. Secrets from env.
Bakes the full 3-part postgres contract (Fields/State/schemas + input.input.mapping.parameters)
and the flow metadata/fe_metadata, mirroring the proven reference A2A build."""
import subprocess, os, sys, json, uuid, tempfile

FDA  = os.environ["FDA"]
DIR  = os.path.dirname(os.path.abspath(__file__))
FILE = os.path.join(DIR, "RealEstateA2AServers.flogo")

PG_HOST="localhost"; PG_PORT="5432"; PG_DB="realestate"; PG_USER="postgres"
PG_PWD = os.environ["PG_PWD"]
LLM_PROVIDER="OpenAI"; LLM_BASE="https://api.openai.com/v1"; LLM_MODEL="gpt-5.5"
LLM_KEY = os.environ["LLM_API_KEY"]
EMAIL_USER="your-email@gmail.com"; TO_EMAIL="your-email@gmail.com"
EMAIL_PWD = os.environ["SMTP_PWD"]

def fda(*args, allow_fail=False):
    r = subprocess.run([FDA, *map(str, args), "-f", FILE], capture_output=True, text=True)
    out=(r.stdout or "")+(r.stderr or "")
    if "(ERROR)" in out and not allow_fail:
        print("FAILED:"," ".join(map(str,args))); print(out[-1600:]); sys.exit(1)
    print("  ok:", " ".join(str(a) for a in args[:3]))
    return out

def jtmp(obj):
    f=tempfile.NamedTemporaryFile("w",suffix=".json",delete=False,encoding="utf-8")
    json.dump(obj,f); f.close(); return f.name

def conn_uuid(name):
    conns=json.load(open(FILE))["connections"]
    items=list(conns.values()) if isinstance(conns,dict) else conns
    return "conn://"+next(c["id"] for c in items if c["name"]==name)

if os.path.exists(FILE): os.remove(FILE)

# ---- draft-04 schema helpers ----
def in_schema(params, is_insert):
    props={p:{"type":"string"} for p in params}
    d={"$schema":"http://json-schema.org/draft-04/schema#","type":"object","definitions":{},
       "properties":{}}
    if is_insert:
        d["properties"]["values"]={"type":"array","items":{"type":"object","properties":{}}}
    d["properties"]["parameters"]={"type":"object","properties":props}
    return json.dumps(d)
OUT_SCHEMA=json.dumps({"$schema":"http://json-schema.org/draft-04/schema#","type":"object",
    "definitions":{},"properties":{"records":{"type":"array","items":{"type":"object","properties":{}}}}})

def bake_pg(flow, act, ref, query, params, result_cols=None):
    """params: list of (placeholder, expr). result_cols: list of (name,Type) for SELECT."""
    is_insert = (ref=="act_postgresql_insert")
    fields=[{"FieldName":p,"Type":"LONGVARCHAR","Selected":False,"Parameter":True,
             "isEditable":False,"Value":False} for p,_ in params]
    if result_cols:
        for n,ty in result_cols:
            fields.append({"FieldName":n,"Type":ty,"Selected":True,"Parameter":False,"isEditable":False})
    inp={"Connection":PG_REF,"QueryName":"","Schema":"public","Query":query,"manualmode":False,
         "Fields":fields,"RuntimeQuery":"","State":str(uuid.uuid4())+query,
         "input":{"mapping":{"parameters":{p:expr for p,expr in params}}}}
    if not is_insert: inp["fetchMetadata"]=False
    fda("sa","activity",f"{flow}.{act}.input","--jsonFile",jtmp(inp),"--force")
    iv=in_schema([p for p,_ in params], is_insert)
    schemas={"input":{"input":{"type":"json","value":iv,"fe_metadata":iv}},
             "output":{"Output":{"type":"json","value":OUT_SCHEMA,"fe_metadata":OUT_SCHEMA}}}
    fda("sa","activity",f"{flow}.{act}.schemas","--jsonFile",jtmp(schemas),"--force")

# ---- agent specs ----
AGENTS=[
 {"name":"book_property_showing","port":"9593",
  "adesc":"Books a property showing (tour) for a real estate lead at a specific listing and date/time.",
  "sys":"You are a scheduling agent for a residential real estate brokerage. Given a lead id, a listing id, and a preferred date/time, book a property showing. Only book listings that are Active. Never invent ids; the showing agent is derived from the lead's assigned agent.",
  "tooldesc":"Book a property showing for a lead at a listing. Requires lead_id (LEAD-2026-NNNNN), listing_id (LST-NNNNN), and preferred_datetime (e.g. '2026-08-30 14:00'); notes optional. The assigned agent is derived automatically.",
  "tp":[("lead_id","string"),("listing_id","string"),("preferred_datetime","string"),("notes","string")],
  "req":["lead_id","listing_id","preferred_datetime"],
  "acts":[
    {"id":"ValidateQuery","ref":"act_postgresql_query",
     "q":"SELECT l.lead_id, li.listing_id, li.status FROM public.leads l, public.listings li WHERE l.lead_id = ?leadid AND li.listing_id = ?listingid;",
     "p":[("leadid","=$flow.toolParams.lead_id"),("listingid","=$flow.toolParams.listing_id")],
     "cols":[("lead_id","VARCHAR"),("listing_id","VARCHAR"),("status","VARCHAR")]},
    {"id":"WriteRow","ref":"act_postgresql_insert",
     "q":"INSERT INTO public.appointments (lead_id, listing_id, agent_id, scheduled_for, status, notes) SELECT l.lead_id, ?p_listing, l.assigned_agent_id, NULLIF(?p_sched,'')::timestamp, 'Requested', NULLIF(?p_notes,'') FROM public.leads l WHERE l.lead_id = ?p_lead;",
     "p":[("p_listing","=$flow.toolParams.listing_id"),("p_sched","=$flow.toolParams.preferred_datetime"),("p_notes","=$flow.toolParams.notes"),("p_lead","=$flow.toolParams.lead_id")]},
  ],"return":"WriteRow"},

 {"name":"update_lead_stage","port":"9594",
  "adesc":"Advances a lead's funnel stage and logs the change.",
  "sys":"You update a real estate lead's funnel stage (New, Nurturing, Active, Under Contract, Closed, Lost) and log the reason. Use this to advance a lead (e.g. to 'Active' after they book a showing). Never invent lead ids.",
  "tooldesc":"Update a lead's funnel stage. Requires lead_id and new_stage (one of New, Nurturing, Active, Under Contract, Closed, Lost); reason optional but recommended.",
  "tp":[("lead_id","string"),("new_stage","string"),("reason","string")],
  "req":["lead_id","new_stage"],
  "acts":[
    {"id":"UpdateStage","ref":"act_postgresql_insert",
     "q":"UPDATE public.leads SET stage = ?p_stage, last_activity_at = CURRENT_TIMESTAMP WHERE lead_id = ?p_lead;",
     "p":[("p_stage","=$flow.toolParams.new_stage"),("p_lead","=$flow.toolParams.lead_id")]},
    {"id":"LogActivity","ref":"act_postgresql_insert",
     "q":"INSERT INTO public.lead_activity (lead_id, activity_type, detail) VALUES (?p_lead, 'Stage Change', ?p_detail);",
     "p":[("p_lead","=$flow.toolParams.lead_id"),("p_detail","=string.concat(\"Stage changed to \",$flow.toolParams.new_stage,\" \",coerce.toString($flow.toolParams.reason))")]},
  ],"return":"LogActivity"},

 {"name":"send_property_recommendations","port":"9595",
  "adesc":"Records a set of curated listing recommendations sent to a lead.",
  "sys":"You record curated home recommendations for a real estate lead. Given a lead id and the listing ids you recommended, log a 'Recommendation Sent' activity. To actually email the recommendations, the orchestrator calls the email agent separately. Never invent lead ids.",
  "tooldesc":"Log curated listing recommendations for a lead. Requires lead_id and listing_ids (comma-separated LST ids); summary optional.",
  "tp":[("lead_id","string"),("listing_ids","string"),("summary","string")],
  "req":["lead_id","listing_ids"],
  "acts":[
    {"id":"WriteRow","ref":"act_postgresql_insert",
     "q":"INSERT INTO public.lead_activity (lead_id, activity_type, detail) VALUES (?p_lead, 'Recommendation Sent', ?p_detail);",
     "p":[("p_lead","=$flow.toolParams.lead_id"),("p_detail","=string.concat(\"Sent listings: \",$flow.toolParams.listing_ids,\" \",coerce.toString($flow.toolParams.summary))")]},
  ],"return":"WriteRow"},

 {"name":"log_followup_task","port":"9596",
  "adesc":"Creates a follow-up task for the lead's assigned agent.",
  "sys":"You create a follow-up task (Call, Text, or Email) for a real estate lead's assigned agent. Given a lead id, task type and optional due date/notes, log the task. The agent is derived from the lead. Never invent lead ids.",
  "tooldesc":"Create a follow-up task for a lead's agent. Requires lead_id and task_type (Call, Text, or Email); due_date (YYYY-MM-DD) and notes optional.",
  "tp":[("lead_id","string"),("task_type","string"),("due_date","string"),("notes","string")],
  "req":["lead_id","task_type"],
  "acts":[
    {"id":"WriteRow","ref":"act_postgresql_insert",
     "q":"INSERT INTO public.follow_up_tasks (lead_id, agent_id, task_type, due_date, notes) SELECT l.lead_id, l.assigned_agent_id, ?p_type, NULLIF(?p_due,'')::date, NULLIF(?p_notes,'') FROM public.leads l WHERE l.lead_id = ?p_lead;",
     "p":[("p_type","=$flow.toolParams.task_type"),("p_due","=$flow.toolParams.due_date"),("p_notes","=$flow.toolParams.notes"),("p_lead","=$flow.toolParams.lead_id")]},
  ],"return":"WriteRow"},

 {"name":"send_confirmation_email","port":"9597","email":True,
  "adesc":"Sends a confirmation or recommendation email to the prospect.",
  "sys":"You send a single confirmation or recommendation email. Compose a clear subject and body from what the orchestrator gives you and send it. Send only when asked or right after an action is completed.",
  "tooldesc":"Send one email. Requires subject and body. Sends to the preconfigured demo recipient mailbox.",
  "tp":[("subject","string"),("body","string")],
  "req":["subject","body"]},
]

print("== project + properties + connections ==")
fda("cp","RealEstateA2AServers","Real Estate A2A Servers")
fda("cap","AgenticAI.OpenAIConn.LLM_Provider","string",LLM_PROVIDER)
fda("cap","AgenticAI.OpenAIConn.API_Key","string",LLM_KEY)
fda("cap","AgenticAI.OpenAIConn.LLM_Base_URL","string",LLM_BASE)
fda("cap","LLM_Model","string",LLM_MODEL)
fda("cap","PostgreSQL.PostgresConn.Host","string",PG_HOST)
fda("cap","PostgreSQL.PostgresConn.Port","number",PG_PORT)
fda("cap","PostgreSQL.PostgresConn.Database_Name","string",PG_DB)
fda("cap","PostgreSQL.PostgresConn.User","string",PG_USER)
fda("cap","PostgreSQL.PostgresConn.Password","string",PG_PWD)
fda("cap","Email_Username","string",EMAIL_USER)
fda("cap","Email_App_Password","string",EMAIL_PWD)
fda("cap","To_Email","string",TO_EMAIL)
for a in AGENTS:
    fda("cap",f"{a['name']}_PORT","string",a["port"])
    fda("cap",f"{a['name']}_URL","string",f"http://localhost:{a['port']}")

fda("cc","OpenAIConn","con_llmprovider")
fda("sa","connection","OpenAIConn.settings.llmProvider","AgenticAI.OpenAIConn.LLM_Provider","-C","app-property")
fda("sa","connection","OpenAIConn.settings.apiKey","AgenticAI.OpenAIConn.API_Key","-C","app-property")
fda("sa","connection","OpenAIConn.settings.llmProviderUrl","AgenticAI.OpenAIConn.LLM_Base_URL","-C","app-property")

fda("cc","PostgresConn","con_postgresql")
fda("sa","connection","PostgresConn.settings.databaseType","PostgreSQL")
fda("sa","connection","PostgresConn.settings.host","PostgreSQL.PostgresConn.Host","-C","app-property")
fda("sa","connection","PostgresConn.settings.port","PostgreSQL.PostgresConn.Port","-C","app-property")
fda("sa","connection","PostgresConn.settings.databaseName","PostgreSQL.PostgresConn.Database_Name","-C","app-property")
fda("sa","connection","PostgresConn.settings.user","PostgreSQL.PostgresConn.User","-C","app-property")
fda("sa","connection","PostgresConn.settings.password","PostgreSQL.PostgresConn.Password","-C","app-property")
PG_REF=conn_uuid("PostgresConn")
print("  PG_REF =",PG_REF)

for a in AGENTS:
    name=a["name"]; flow=f"{name}_flow"
    print(f"== agent {name} ==")
    fda("ct",name,"tr_agent",a["adesc"])
    fda("sa","trigger",f"{name}.settings.llmProviderConnection","OpenAIConn","-C","connection")
    fda("sa","trigger",f"{name}.settings.agentName",name)
    fda("sa","trigger",f"{name}.settings.agentDescription",a["adesc"])
    fda("sa","trigger",f"{name}.settings.agentType","A2A Server")
    fda("sa","trigger",f"{name}.settings.agentPort",f"{name}_PORT","-C","app-property")
    fda("sa","trigger",f"{name}.settings.agentUrl",f"{name}_URL","-C","app-property")
    fda("sa","trigger",f"{name}.settings.model","LLM_Model","-C","app-property")
    fda("sa","trigger",f"{name}.settings.temperature","0.3","--type","number")
    fda("sa","trigger",f"{name}.settings.enableGuardrails","true","--type","boolean")
    fda("sa","trigger",f"{name}.settings.redactSensitiveData","true","--type","boolean")
    fda("sa","trigger",f"{name}.settings.conversationStoreType","Memory")
    fda("sa","trigger",f"{name}.settings.memoryMaxSize","100","--type","number")
    fda("sa","trigger",f"{name}.settings.systemPrompt",a["sys"])

    # flow
    fda("cf",flow,a["adesc"])
    fda("ca",flow,"LogMessage","act_general_log","Log")
    fda("mm",f"{flow}.LogMessage.input.message",f'=string.concat("Agent invoked: ",$flowctx["FlowName"])')

    if a.get("email"):
        fda("ca",flow,"SendMail","act_general_sendmail","Send Mail")
        mail={"Server":"smtp.gmail.com","Port":465,"authorizationType":"Basic",
              "Username":'=$property["Email_Username"]',"Password":'=$property["Email_App_Password"]',
              "authorizationConn":"","Connection Security":"SSL","serverCertificate":"",
              "message_content_type":"text/plain","sender":'=$property["Email_Username"]',
              "recipients":'=$property["To_Email"]',"cc_recipients":"","bcc_recipients":"",
              "reply_to":'=$property["Email_Username"]',"subject":'=$flow.toolParams.subject',
              "message":'=$flow.toolParams.body',"attachments":{"mapping":[]},"headers":{"mapping":[]}}
        fda("sa","activity",f"{flow}.SendMail.input","--jsonFile",jtmp(mail),"--force")
    else:
        for act in a["acts"]:
            conn=["-C","PostgresConn"]
            label="PostgreSQL Insert" if act["ref"]=="act_postgresql_insert" else "PostgreSQL Query"
            fda("ca",flow,act["id"],act["ref"],label,*conn)
        for act in a["acts"]:
            bake_pg(flow,act["id"],act["ref"],act["q"],act["p"],act.get("cols"))

    fda("ca",flow,"Return","act_default_actreturn","Simple Return")
    if a.get("email"):
        fda("mm",f"{flow}.Return.input.mappings.response.mapping.data",
            '=string.concat("Confirmation email sent: ",$flow.toolParams.subject)')
    else:
        fda("mm",f"{flow}.Return.input.mappings.response.mapping.data",
            f'=coerce.toString($activity[{a["return"]}].Output)')

    # handler = agent tool card
    fda("cth",flow,name,a["tooldesc"])
    fda("sa","handler",f"{name}.{flow}.settings.agentToolName",name)
    fda("sa","handler",f"{name}.{flow}.settings.agentToolDescription",a["tooldesc"])
    fda("wth",flow,f"{name}.{flow}","--force","--input","toolParams:object","--output","response:object")
    tp_props={f:{"type":"string"} for f,_ in a["tp"]}
    tp_schema={"type":"object","properties":tp_props,"required":a["req"]}
    fda("cs",f"{name}_ToolParams",json.dumps(tp_schema))
    fda("sa","handler",f"{name}.{flow}.schemas.output.toolParams",f"{name}_ToolParams","-C","schema","--force")
    fda("cs",f"{name}_Resp",'{"type":"object","properties":{"response":{"type":"string"}}}')
    fda("sa","handler",f"{name}.{flow}.schemas.reply.response",f"{name}_Resp","-C","schema","--force")

    # flow metadata + fe_metadata (durable in designer, no Sync needed)
    compact=json.dumps({f:{"type":"string"} for f,_ in a["tp"]})
    md_in=[{"name":"toolParams","type":"object","schema":{"type":"json","value":compact}}]
    md_out=[{"name":"response","type":"object","schema":{"type":"json","value":'{"response":{"type":"string"}}'}}]
    fda("sa","flow",f"{flow}.metadata.input","--jsonFile",jtmp(md_in),"--force")
    fda("sa","flow",f"{flow}.metadata.output","--jsonFile",jtmp(md_out),"--force")
    fe_in=json.dumps({"type":"object","title":name,"properties":{"toolParams":{"type":"object","properties":tp_props,"required":a["req"]}}})
    fe_out=json.dumps({"type":"object","title":"Inputs","properties":{"response":{"type":"object","properties":{"response":{"type":"string"}}}},"required":[]})
    fda("sa","flow",f"{flow}.metadata.fe_metadata.input",fe_in,"--force")
    fda("sa","flow",f"{flow}.metadata.fe_metadata.output",fe_out,"--force")

print("\nA2A build complete:",FILE)
