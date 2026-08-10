#!/usr/bin/env python3
"""
Build the 3 Logistics/Transport Agentic-AI Flogo apps entirely via the Flogo
Design CLI (fda) -- no hand-editing of .flogo JSON.

  * LogisticsMCPServer.flogo     - MCP server, 6 read-only tools
  * LogisticsA2AServers.flogo    - 4 A2A action agents (direct Postgres + email)
  * LogisticsAIOrchestrator.flogo- WebSocket AI orchestrator

SECURITY: this script embeds NO live credentials. All secret / PII / model
fields are set to PLACEHOLDERS (SET_YOUR_...); real values are supplied by the
operator via App Properties at deploy time (see README manual-config section).
Only non-sensitive generics (localhost/5432/postgres, the public OpenAI base
URL, ports) are set to real defaults.

Run:  python build_logistics_apps.py [mcp|a2a|orc|all]
"""
import subprocess, os, sys, json, tempfile

# ---- resolved fda path (tool path, not a secret) -------------------------------
FDA = r"C:\Users\nshah\.vscode\extensions\tibco.flogo-2.26.6-3093\bin\flogodesign-cli.exe"
HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)

MCP_FILE = "LogisticsMCPServer.flogo"
A2A_FILE = "LogisticsA2AServers.flogo"
ORC_FILE = "LogisticsAIOrchestrator.flogo"

# ---- non-sensitive generics ----------------------------------------------------
DBNAME       = "logistics"
PG_HOST      = "localhost"
PG_PORT      = 5432
PG_USER      = "postgres"
LLM_PROVIDER = "OpenAI"
LLM_BASE_URL = "https://api.openai.com/v1"   # gotcha 4c: must be a real endpoint
LLM_MODEL    = "gpt-4o"                       # public default; operator sets their model
USECASE_PATH = "logistics"                    # ws path + mcp endpoint slug

# ---- placeholders for anything sensitive (never real creds in a committed file) -
PH_API_KEY   = "SET_YOUR_LLM_API_KEY"
PH_DB_PWD    = "SET_YOUR_DB_PASSWORD"
PH_MAIL_USER = "sender@example.com"
PH_MAIL_PWD  = "SET_YOUR_EMAIL_APP_PASSWORD"
PH_TO_EMAIL  = "recipient@example.com"

# ---- ports ---------------------------------------------------------------------
MCP_PORT      = 9790
RESCHED_PORT  = 9791
PICKUP_PORT   = 9792
CLAIM_PORT    = 9793
EMAIL_PORT    = 9794
WS_PORT       = 9690

_current_file = None
def use(f):
    global _current_file
    _current_file = f

def fda(*args, allow_fail=False, jsonfile=None):
    cmd = [FDA, *map(str, args)]
    if jsonfile:
        cmd += ["--jsonFile", jsonfile]
    cmd += ["-f", _current_file]
    r = subprocess.run(cmd, capture_output=True, text=True)
    out = (r.stdout or "") + (r.stderr or "")
    tag = " ".join(map(str, args))
    if len(tag) > 90:
        tag = tag[:90] + "..."
    if "(ERROR)" in out and not allow_fail:
        print("FAILED:", tag)
        print(out[-1600:])
        sys.exit(1)
    print("  ok:", tag)
    return out

def sa_jsonfile(kind, selector, obj):
    """sa <kind> <selector> --jsonFile <tmp with json obj>"""
    fd, path = tempfile.mkstemp(suffix=".json")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(obj, fh)
        fda("sa", kind, selector, jsonfile=path)
    finally:
        os.remove(path)

def conn_uuid(name):
    """Read a connection's conn:// ref back from the current .flogo by name.
    PostgreSQL query/insert activities reference the connection via their
    `input.Connection` field as a literal `conn://<uuid>` (the `-C connection`
    name-resolution does NOT populate this field -> empty dropdown in designer)."""
    d = json.load(open(_current_file))
    conns = d.get("connections", {})
    items = list(conns.values()) if isinstance(conns, dict) else conns
    for c in items:
        if c.get("name") == name:
            return "conn://%s" % c["id"]
    raise SystemExit("connection not found in %s: %s" % (_current_file, name))

def pg_connection():
    """Create the standard PostgresConn bound to app properties (MCP + A2A)."""
    fda("cap", "PostgreSQL.PostgresConn.Host", "string", PG_HOST)
    fda("cap", "PostgreSQL.PostgresConn.Port", "number", PG_PORT)
    fda("cap", "PostgreSQL.PostgresConn.Database_Name", "string", DBNAME)
    fda("cap", "PostgreSQL.PostgresConn.User", "string", PG_USER)
    fda("cap", "PostgreSQL.PostgresConn.Password", "string", PH_DB_PWD)
    fda("cc", "PostgresConn", "con_postgresql")
    fda("sa", "connection", "PostgresConn.settings.databaseType", "PostgreSQL")
    fda("sa", "connection", "PostgresConn.settings.host", "PostgreSQL.PostgresConn.Host", "-C", "app-property")
    fda("sa", "connection", "PostgresConn.settings.port", "PostgreSQL.PostgresConn.Port", "-C", "app-property")
    fda("sa", "connection", "PostgresConn.settings.databaseName", "PostgreSQL.PostgresConn.Database_Name", "-C", "app-property")
    fda("sa", "connection", "PostgresConn.settings.user", "PostgreSQL.PostgresConn.User", "-C", "app-property")
    fda("sa", "connection", "PostgresConn.settings.password", "PostgreSQL.PostgresConn.Password", "-C", "app-property")

def llm_connection():
    fda("cap", "AgenticAI.OpenAIConn.LLM_Provider", "string", LLM_PROVIDER)
    fda("cap", "AgenticAI.OpenAIConn.API_Key", "string", PH_API_KEY)
    fda("cap", "AgenticAI.OpenAIConn.LLM_Base_URL", "string", LLM_BASE_URL)
    fda("cap", "LLM_Model", "string", LLM_MODEL)
    fda("cc", "OpenAIConn", "con_llmprovider")
    fda("sa", "connection", "OpenAIConn.settings.llmProvider", "AgenticAI.OpenAIConn.LLM_Provider", "-C", "app-property")
    fda("sa", "connection", "OpenAIConn.settings.apiKey", "AgenticAI.OpenAIConn.API_Key", "-C", "app-property")
    fda("sa", "connection", "OpenAIConn.settings.llmProviderUrl", "AgenticAI.OpenAIConn.LLM_Base_URL", "-C", "app-property")

# ==============================================================================
# MCP SERVER
# ==============================================================================
MCP_TOOLS = [
    ("getCustomers", "GetCustomerProfile", "customers", "customer_id",
     "Get the shipper/customer profile: name, account type (Individual/Business), loyalty tier, email and phone. Use to identify who the customer is."),
    ("getShipments", "GetShipments", "shipments", "tracking_number",
     "List shipments with tracking number, status (Label Created/In Transit/Out for Delivery/Delivered/Delayed/Exception), service level, origin, destination, carrier, weight, declared value and estimated/actual delivery dates. Use to find a shipment or check its status."),
    ("getTrackingEvents", "TrackShipment", "tracking_events", "event_id",
     "Get the scan-by-scan tracking history for shipments: event time, location, status and description. Use to trace where a package is and whether it is delayed."),
    ("getServiceLevels", "GetServiceLevels", "service_levels", "service_code",
     "Get the shipping service-level rate card: Same-Day, Express, Standard, Eco with transit-day ranges, price per kg and max weight. Use to compare shipping options."),
    ("getDeliveryChanges", "GetDeliveryChanges", "delivery_changes", "change_id",
     "List delivery change requests already on file (reschedule/redirect/hold) with new date, new address, reason and status. Use to check pending delivery changes."),
    ("getClaims", "GetClaims", "claims", "claim_id",
     "List claims already filed (Lost/Damaged) with description, amount and status. Use to check existing claims for a shipment or customer."),
]

def build_mcp():
    use(MCP_FILE)
    if os.path.exists(MCP_FILE):
        os.remove(MCP_FILE)
    print("== LogisticsMCPServer.flogo ==")
    fda("cp", "LogisticsMCPServer", "Logistics MCP Server")
    # tr_mcpserver "HTTP Server Port" field is a STRING -> property must be string
    fda("cap", "MCP_SERVER_PORT", "string", MCP_PORT)
    pg_connection()
    pg_ref = conn_uuid("PostgresConn")

    # trigger
    fda("ct", "LogisticsMCPServer", "tr_mcpserver", "Logistics MCP server")
    fda("sa", "trigger", "LogisticsMCPServer.settings.serverType", "HTTP")
    fda("sa", "trigger", "LogisticsMCPServer.settings.serverPort", "MCP_SERVER_PORT", "-C", "app-property")
    fda("sa", "trigger", "LogisticsMCPServer.settings.serverEndpointPath", "/%smcpserver" % USECASE_PATH)
    fda("sa", "trigger", "LogisticsMCPServer.settings.serverName", "Logistics")
    fda("sa", "trigger", "LogisticsMCPServer.settings.serverVersion", "1.0.0")

    # shared schemas (gotcha 1)
    fda("cs", "EmptyArgs", '{"type":"object","properties":{}}')
    fda("cs", "ToolResponse", '{"type":"object","properties":{"data":{"type":"string"},"error":{"type":"string"}}}')

    for flow, tool, table, pk, desc in MCP_TOOLS:
        fda("cf", flow, desc)
        fda("ca", flow, "PostgreSQLQuery", "act_postgresql_query", "PostgreSQL Query", "-C", "PostgresConn")
        fda("ca", flow, "Return", "act_default_actreturn", "Simple Return")
        fda("sa", "activity", "%s.PostgreSQLQuery.input.Connection" % flow, pg_ref)
        fda("sa", "activity", "%s.PostgreSQLQuery.input.Query" % flow,
            "SELECT * FROM public.%s ORDER BY %s ASC;" % (table, pk))
        fda("sa", "activity", "%s.PostgreSQLQuery.input.Schema" % flow, "public")
        fda("cth", flow, "LogisticsMCPServer", desc,
            "--mcpHandlerType", "Tool", "--mcpHandlerName", tool, "--mcpHandlerDescription", desc)
        fda("wth", flow, "LogisticsMCPServer.%s" % flow, "--force")
        fda("sa", "handler", "LogisticsMCPServer.%s.schemas.output.arguments" % flow, "EmptyArgs", "-C", "schema", "--force")
        fda("sa", "handler", "LogisticsMCPServer.%s.schemas.reply.response" % flow, "ToolResponse", "-C", "schema", "--force")
        fda("mm", "%s.Return.input.mappings.response.mapping.data" % flow,
            "=coerce.toString($activity[PostgreSQLQuery].Output)")
    print("== MCP done ==\n")

# ==============================================================================
# A2A SERVERS
# ==============================================================================
def agent_common(agent, desc, port_prop, url_prop, sysprompt):
    fda("ct", agent, "tr_agent", desc)
    fda("sa", "trigger", "%s.settings.llmProviderConnection" % agent, "OpenAIConn", "-C", "connection")
    fda("sa", "trigger", "%s.settings.agentName" % agent, agent)
    fda("sa", "trigger", "%s.settings.agentDescription" % agent, desc)
    fda("sa", "trigger", "%s.settings.agentType" % agent, "A2A Server")
    fda("sa", "trigger", "%s.settings.agentPort" % agent, port_prop, "-C", "app-property")
    fda("sa", "trigger", "%s.settings.agentUrl" % agent, url_prop, "-C", "app-property")
    fda("sa", "trigger", "%s.settings.model" % agent, "LLM_Model", "-C", "app-property")
    fda("sa", "trigger", "%s.settings.temperature" % agent, "--jsonValue", "0.7")
    fda("sa", "trigger", "%s.settings.enableGuardrails" % agent, "--jsonValue", "true")
    fda("sa", "trigger", "%s.settings.redactSensitiveData" % agent, "--jsonValue", "true")
    fda("sa", "trigger", "%s.settings.conversationStoreType" % agent, "Memory")
    fda("sa", "trigger", "%s.settings.memoryMaxSize" % agent, "--jsonValue", "100")
    fda("sa", "trigger", "%s.settings.systemPrompt" % agent, sysprompt)

def agent_flow_start(agent, desc):
    flow = "%s_flow" % agent
    fda("cf", flow, desc)
    fda("ca", flow, "LogMessage", "act_general_log", "Log")
    fda("mm", "%s.LogMessage.input.message" % flow,
        '=string.concat("Agent Invocation started:",$flowctx["FlowName"])')
    return flow

def agent_handler(agent, tool_desc, toolparams_props, required):
    flow = "%s_flow" % agent
    fda("cth", flow, agent, tool_desc)
    fda("sa", "handler", "%s.%s.settings.agentToolName" % (agent, flow), agent)
    fda("sa", "handler", "%s.%s.settings.agentToolDescription" % (agent, flow), tool_desc)
    fda("wth", flow, "%s.%s" % (agent, flow), "--force",
        "--input", "toolParams:object", "--output", "response:object")
    tp_schema = {"type": "object", "properties": toolparams_props, "required": required}
    tp_str = json.dumps(tp_schema)
    fda("cs", "%s_ToolParams" % agent, tp_str)
    fda("sa", "handler", "%s.%s.schemas.output.toolParams" % (agent, flow), "%s_ToolParams" % agent, "-C", "schema", "--force")
    fda("cs", "%s_Resp" % agent, '{"type":"object","properties":{"response":{"type":"string"}}}')
    fda("sa", "handler", "%s.%s.schemas.reply.response" % (agent, flow), "%s_Resp" % agent, "-C", "schema", "--force")
    # gotcha 5: mirror the toolParams schema onto the flow input so mappings resolve
    meta = [{"name": "toolParams", "type": "object",
             "schema": {"type": "json", "value": tp_str}}]
    sa_jsonfile("flow", "%s.metadata.input" % flow, meta)

def build_a2a():
    use(A2A_FILE)
    if os.path.exists(A2A_FILE):
        os.remove(A2A_FILE)
    print("== LogisticsA2AServers.flogo ==")
    fda("cp", "LogisticsA2AServers", "Logistics A2A Servers")
    llm_connection()
    pg_connection()
    pg_ref = conn_uuid("PostgresConn")
    # agent ports/urls + email props
    # tr_agent "A2A Server Port" field is a STRING -> port properties must be string
    fda("cap", "RESCHEDULE_AGENT_PORT", "string", RESCHED_PORT)
    fda("cap", "RESCHEDULE_AGENT_URL", "string", "http://localhost:%d" % RESCHED_PORT)
    fda("cap", "PICKUP_AGENT_PORT", "string", PICKUP_PORT)
    fda("cap", "PICKUP_AGENT_URL", "string", "http://localhost:%d" % PICKUP_PORT)
    fda("cap", "CLAIM_AGENT_PORT", "string", CLAIM_PORT)
    fda("cap", "CLAIM_AGENT_URL", "string", "http://localhost:%d" % CLAIM_PORT)
    fda("cap", "EMAIL_AGENT_PORT", "string", EMAIL_PORT)
    fda("cap", "EMAIL_AGENT_URL", "string", "http://localhost:%d" % EMAIL_PORT)
    fda("cap", "Email_Username", "string", PH_MAIL_USER)
    fda("cap", "Email_App_Password", "string", PH_MAIL_PWD)
    fda("cap", "To_Email", "string", PH_TO_EMAIL)

    # ---- Agent 1: reschedule_delivery_agent -----------------------------------
    a = "reschedule_delivery_agent"
    agent_common(a, "Reschedule or redirect a delivery to a new date or address.",
                 "RESCHEDULE_AGENT_PORT", "RESCHEDULE_AGENT_URL",
                 "You are a delivery-change agent for a logistics company. You reschedule or redirect shipments. "
                 "Given a tracking number and either a new delivery date (YYYY-MM-DD) or a new destination address, "
                 "record the change and update the shipment. Set change_type to Reschedule, Redirect or Hold. "
                 "Always work from the provided tracking number and return a clear confirmation of the change.")
    f = agent_flow_start(a, "Reschedule or redirect a delivery")
    fda("ca", f, "ValidateQuery", "act_postgresql_query", "PostgreSQL Query", "-C", "PostgresConn")
    fda("sa", "activity", "%s.ValidateQuery.input.Connection" % f, pg_ref)
    fda("sa", "activity", "%s.ValidateQuery.input.Query" % f,
        "SELECT tracking_number, status FROM public.shipments WHERE tracking_number = ?tn;")
    fda("sa", "activity", "%s.ValidateQuery.input.Schema" % f, "public")
    fda("mm", "%s.ValidateQuery.input.mapping.parameters.tn" % f, "=$flow.toolParams.tracking_number")
    fda("ca", f, "WriteChange", "act_postgresql_insert", "PostgreSQL Insert", "-C", "PostgresConn")
    fda("sa", "activity", "%s.WriteChange.input.Connection" % f, pg_ref)
    fda("sa", "activity", "%s.WriteChange.input.Query" % f,
        "INSERT INTO public.delivery_changes (tracking_number, customer_id, change_type, new_delivery_date, new_address, reason, status) "
        "VALUES (?p1, ?p2, ?p3, NULLIF(?p4,'')::date, NULLIF(?p5,''), ?p6, 'Requested');")
    fda("sa", "activity", "%s.WriteChange.input.Schema" % f, "public")
    for p, field in [("p1", "tracking_number"), ("p2", "customer_id"), ("p3", "change_type"),
                     ("p4", "new_delivery_date"), ("p5", "new_address"), ("p6", "reason")]:
        fda("mm", "%s.WriteChange.input.mapping.parameters.%s" % (f, p), "=$flow.toolParams.%s" % field)
    fda("ca", f, "UpdateShipment", "act_postgresql_insert", "PostgreSQL Insert", "-C", "PostgresConn")
    fda("sa", "activity", "%s.UpdateShipment.input.Connection" % f, pg_ref)
    fda("sa", "activity", "%s.UpdateShipment.input.Query" % f,
        "UPDATE public.shipments SET estimated_delivery = COALESCE(NULLIF(?d,'')::date, estimated_delivery), "
        "destination_address = COALESCE(NULLIF(?a,''), destination_address) WHERE tracking_number = ?tn;")
    fda("sa", "activity", "%s.UpdateShipment.input.Schema" % f, "public")
    fda("mm", "%s.UpdateShipment.input.mapping.parameters.d" % f, "=$flow.toolParams.new_delivery_date")
    fda("mm", "%s.UpdateShipment.input.mapping.parameters.a" % f, "=$flow.toolParams.new_address")
    fda("mm", "%s.UpdateShipment.input.mapping.parameters.tn" % f, "=$flow.toolParams.tracking_number")
    fda("ca", f, "Return", "act_default_actreturn", "Simple Return")
    fda("mm", "%s.Return.input.mappings.response.mapping.data" % f, "=coerce.toString($activity[WriteChange].Output)")
    agent_handler(a, "Reschedule or redirect a delivery. Provide tracking_number and either new_delivery_date (YYYY-MM-DD) or new_address; set change_type to Reschedule, Redirect or Hold. Records the change and updates the shipment.",
                  {"tracking_number": {"type": "string"}, "customer_id": {"type": "string"},
                   "change_type": {"type": "string"}, "new_delivery_date": {"type": "string"},
                   "new_address": {"type": "string"}, "reason": {"type": "string"}},
                  ["tracking_number"])

    # ---- Agent 2: book_pickup_agent -------------------------------------------
    a = "book_pickup_agent"
    agent_common(a, "Book a carrier pickup for a customer.",
                 "PICKUP_AGENT_PORT", "PICKUP_AGENT_URL",
                 "You are a pickup-booking agent. You schedule carrier pickups for a customer. Given an address, "
                 "pickup date (YYYY-MM-DD), time window and package count, create a pickup request and return a "
                 "confirmation with the pickup details.")
    f = agent_flow_start(a, "Book a carrier pickup")
    fda("ca", f, "WriteRow", "act_postgresql_insert", "PostgreSQL Insert", "-C", "PostgresConn")
    fda("sa", "activity", "%s.WriteRow.input.Connection" % f, pg_ref)
    fda("sa", "activity", "%s.WriteRow.input.Query" % f,
        "INSERT INTO public.pickup_requests (customer_id, address, pickup_date, time_window, package_count, notes, status) "
        "VALUES (?p1, ?p2, NULLIF(?p3,'')::date, ?p4, COALESCE(NULLIF(?p5,'')::int,1), ?p6, 'Scheduled');")
    fda("sa", "activity", "%s.WriteRow.input.Schema" % f, "public")
    for p, field in [("p1", "customer_id"), ("p2", "address"), ("p3", "pickup_date"),
                     ("p4", "time_window"), ("p5", "package_count"), ("p6", "notes")]:
        fda("mm", "%s.WriteRow.input.mapping.parameters.%s" % (f, p), "=$flow.toolParams.%s" % field)
    fda("ca", f, "Return", "act_default_actreturn", "Simple Return")
    fda("mm", "%s.Return.input.mappings.response.mapping.data" % f, "=coerce.toString($activity[WriteRow].Output)")
    agent_handler(a, "Book a carrier pickup. Provide customer_id, address, pickup_date (YYYY-MM-DD), time_window and package_count. Creates a pickup request.",
                  {"customer_id": {"type": "string"}, "address": {"type": "string"},
                   "pickup_date": {"type": "string"}, "time_window": {"type": "string"},
                   "package_count": {"type": "string"}, "notes": {"type": "string"}},
                  ["customer_id", "address", "pickup_date"])

    # ---- Agent 3: file_claim_agent --------------------------------------------
    a = "file_claim_agent"
    agent_common(a, "File a lost or damaged shipment claim.",
                 "CLAIM_AGENT_PORT", "CLAIM_AGENT_URL",
                 "You are a claims agent. You file lost or damaged shipment claims. Validate the shipment exists, "
                 "then record a claim with type (Lost or Damaged), description and amount. Return a confirmation "
                 "including the claim status.")
    f = agent_flow_start(a, "File a lost/damaged claim")
    fda("ca", f, "ValidateQuery", "act_postgresql_query", "PostgreSQL Query", "-C", "PostgresConn")
    fda("sa", "activity", "%s.ValidateQuery.input.Connection" % f, pg_ref)
    fda("sa", "activity", "%s.ValidateQuery.input.Query" % f,
        "SELECT tracking_number, status, declared_value FROM public.shipments WHERE tracking_number = ?tn;")
    fda("sa", "activity", "%s.ValidateQuery.input.Schema" % f, "public")
    fda("mm", "%s.ValidateQuery.input.mapping.parameters.tn" % f, "=$flow.toolParams.tracking_number")
    fda("ca", f, "WriteRow", "act_postgresql_insert", "PostgreSQL Insert", "-C", "PostgresConn")
    fda("sa", "activity", "%s.WriteRow.input.Connection" % f, pg_ref)
    fda("sa", "activity", "%s.WriteRow.input.Query" % f,
        "INSERT INTO public.claims (tracking_number, customer_id, claim_type, description, claim_amount, status) "
        "VALUES (?p1, ?p2, ?p3, ?p4, COALESCE(NULLIF(?p5,'')::numeric,0), 'Submitted');")
    fda("sa", "activity", "%s.WriteRow.input.Schema" % f, "public")
    for p, field in [("p1", "tracking_number"), ("p2", "customer_id"), ("p3", "claim_type"),
                     ("p4", "description"), ("p5", "claim_amount")]:
        fda("mm", "%s.WriteRow.input.mapping.parameters.%s" % (f, p), "=$flow.toolParams.%s" % field)
    fda("ca", f, "Return", "act_default_actreturn", "Simple Return")
    fda("mm", "%s.Return.input.mappings.response.mapping.data" % f, "=coerce.toString($activity[WriteRow].Output)")
    agent_handler(a, "File a lost or damaged shipment claim. Provide tracking_number, customer_id, claim_type (Lost or Damaged), description and claim_amount. Validates the shipment then records the claim.",
                  {"tracking_number": {"type": "string"}, "customer_id": {"type": "string"},
                   "claim_type": {"type": "string"}, "description": {"type": "string"},
                   "claim_amount": {"type": "string"}},
                  ["tracking_number", "claim_type"])

    # ---- Agent 4: send_confirmation_email -------------------------------------
    a = "send_confirmation_email"
    agent_common(a, "Send a confirmation email to the customer.",
                 "EMAIL_AGENT_PORT", "EMAIL_AGENT_URL",
                 "You are a notification agent. You send a confirmation email to the customer. Given a subject and "
                 "body, send the email and confirm it was sent.")
    f = agent_flow_start(a, "Send a confirmation email")
    fda("ca", f, "SendMail", "act_general_sendmail", "Send Mail")
    fda("sa", "activity", "%s.SendMail.input.Server" % f, "smtp.gmail.com")
    fda("sa", "activity", "%s.SendMail.input.Port" % f, "--jsonValue", "465")
    fda("sa", "activity", "%s.SendMail.input.Connection Security" % f, "SSL")
    fda("sa", "activity", "%s.SendMail.input.message_content_type" % f, "text/plain")
    fda("mm", "%s.SendMail.input.Username" % f, '=$property["Email_Username"]')
    fda("mm", "%s.SendMail.input.Password" % f, '=$property["Email_App_Password"]')
    fda("mm", "%s.SendMail.input.sender" % f, '=$property["Email_Username"]')
    fda("mm", "%s.SendMail.input.recipients" % f, '=$property["To_Email"]')
    fda("mm", "%s.SendMail.input.reply_to" % f, '=$property["Email_Username"]')
    fda("mm", "%s.SendMail.input.subject" % f, "=$flow.toolParams.subject")
    fda("mm", "%s.SendMail.input.message" % f, "=$flow.toolParams.body")
    fda("ca", f, "Return", "act_default_actreturn", "Simple Return")
    fda("mm", "%s.Return.input.mappings.response.mapping.data" % f,
        '=string.concat("Confirmation email sent to ",$property["To_Email"])')
    agent_handler(a, "Send a confirmation email to the customer. Provide subject and body. Sends via SMTP to the configured recipient.",
                  {"subject": {"type": "string"}, "body": {"type": "string"}},
                  ["subject", "body"])
    print("== A2A done ==\n")

# ==============================================================================
# ORCHESTRATOR
# ==============================================================================
A2A_CONNS = [
    ("reschedule_delivery_agentA2AServer", RESCHED_PORT),
    ("book_pickup_agentA2AServer", PICKUP_PORT),
    ("file_claim_agentA2AServer", CLAIM_PORT),
    ("send_confirmation_emailA2AServer", EMAIL_PORT),
]

ORC_SYSPROMPT = (
    "You are the Logistics Assistant for a shipping/transport company, helping a shipper (customer) over chat. "
    "Use the MCP tools to look up read-only information and hand off to the A2A agents to perform actions.\n\n"
    "READ (MCP tools): GetCustomerProfile, GetShipments, TrackShipment, GetServiceLevels, GetDeliveryChanges, GetClaims.\n"
    "ACTIONS (A2A agents): reschedule_delivery_agent (reschedule/redirect a delivery), book_pickup_agent (book a pickup), "
    "file_claim_agent (file a lost/damaged claim), send_confirmation_email (email the customer a confirmation).\n\n"
    "Rules:\n"
    "1. Answer status/tracking/rate questions using the MCP tools; never invent tracking numbers, dates or prices.\n"
    "2. Before performing an action, make sure you have the required fields; ask a brief follow-up if something is missing.\n"
    "3. For a multi-step request (e.g. 'track X and if delayed redirect it and email me'), call TrackShipment first, "
    "then reschedule_delivery_agent, then send_confirmation_email, and summarize what you did.\n"
    "4. After a successful action, offer to email a confirmation via send_confirmation_email.\n"
    "5. If a tracking number is unknown or a request is out of scope, say so and ask for clarification."
)

ORC_WS_HEADERS = ('{"type":"object","properties":{"Accept":{"type":"string","visible":false},'
    '"Accept-Charset":{"type":"string","visible":false},"Accept-Encoding":{"type":"string","visible":false},'
    '"Content-Type":{"type":"string","visible":false},"Content-Length":{"type":"string","visible":false},'
    '"Connection":{"type":"string","visible":false},"Cookie":{"type":"string","visible":false},'
    '"Pragma":{"type":"string","visible":false},"Sec-Websocket-Key":{"type":"string","visible":false},'
    '"Sec-Websocket-Version":{"type":"string","visible":false},"Upgrade":{"type":"string","visible":false}},"required":[]}')

def build_orc():
    use(ORC_FILE)
    if os.path.exists(ORC_FILE):
        os.remove(ORC_FILE)
    print("== LogisticsAIOrchestrator.flogo ==")
    fda("cp", "LogisticsAIOrchestrator", "Logistics AI Orchestrator")
    fda("cap", "WS_SERVER_PORT", "number", WS_PORT)
    llm_connection()

    # MCP connection
    fda("cc", "LogisticsMCPServer", "con_mcpserverconfig")
    fda("sa", "connection", "LogisticsMCPServer.settings.serverType", "http")
    fda("sa", "connection", "LogisticsMCPServer.settings.serverUrl",
        "http://localhost:%d/%smcpserver" % (MCP_PORT, USECASE_PATH))
    fda("sa", "connection", "LogisticsMCPServer.settings.httpTransportType", "streamable")

    # A2A connections
    for name, port in A2A_CONNS:
        fda("cc", name, "con_a2aserverconnection")
        fda("sa", "connection", "%s.settings.serverUrl" % name, "http://localhost:%d" % port)

    # read conn:// uuids back (gotcha 3)
    d = json.load(open(ORC_FILE))
    conns = d["connections"]
    items = list(conns.values()) if isinstance(conns, dict) else conns
    cid = {c["name"]: c["id"] for c in items}
    mcp_ref = "conn://%s" % cid["LogisticsMCPServer"]
    a2a_refs = ["conn://%s" % cid[name] for name, _ in A2A_CONNS]

    # trigger + flow + agent activity
    fda("ct", "WebsocketServer", "tr_wsserver", "WebSocket server")
    fda("sa", "trigger", "WebsocketServer.settings.port", "WS_SERVER_PORT", "-C", "app-property")
    fda("cf", "Orchestrator_Flow", "Logistics orchestrator flow")
    fda("ca", "Orchestrator_Flow", "AIAgent", "act_agenticai_agentactivity", "AI Agent")
    fda("ca", "Orchestrator_Flow", "WebsocketWriteData", "act_websocket_wswritedata", "Write to websocket")
    fda("sa", "activity", "Orchestrator_Flow.AIAgent.settings.llmProviderConnection", "OpenAIConn", "-C", "connection")
    fda("sa", "activity", "Orchestrator_Flow.AIAgent.settings.model", "LLM_Model", "-C", "app-property")
    fda("sa", "activity", "Orchestrator_Flow.AIAgent.settings.temperature", "--jsonValue", "0.7")
    fda("sa", "activity", "Orchestrator_Flow.AIAgent.settings.enableGuardrails", "--jsonValue", "true")
    fda("sa", "activity", "Orchestrator_Flow.AIAgent.settings.redactSensitiveData", "--jsonValue", "true")
    fda("sa", "activity", "Orchestrator_Flow.AIAgent.settings.responseType", "Text")
    fda("sa", "activity", "Orchestrator_Flow.AIAgent.settings.conversationStoreType", "Memory")
    fda("sa", "activity", "Orchestrator_Flow.AIAgent.settings.memoryMaxSize", "--jsonValue", "100")
    fda("sa", "activity", "Orchestrator_Flow.AIAgent.settings.systemPrompt", ORC_SYSPROMPT)
    fda("sa", "activity", "Orchestrator_Flow.AIAgent.settings.mcpServers", "--jsonValue", json.dumps([mcp_ref]))
    fda("sa", "activity", "Orchestrator_Flow.AIAgent.settings.remoteAgents", "--jsonValue", json.dumps(a2a_refs))
    fda("mm", "Orchestrator_Flow.AIAgent.input.userPrompt", "=coerce.toString($flow.content)")
    fda("mm", "Orchestrator_Flow.WebsocketWriteData.input.message", "=$activity[AIAgent].response")
    fda("mm", "Orchestrator_Flow.WebsocketWriteData.input.wsconnection", "=$flow.wsconnection")

    # handler + wsserver gotchas (4a/4b)
    fda("cth", "Orchestrator_Flow", "WebsocketServer", "Logistics orchestrator handler")
    fda("sa", "handler", "WebsocketServer.Orchestrator_Flow.settings.path", "/%s" % USECASE_PATH)
    fda("sa", "handler", "WebsocketServer.Orchestrator_Flow.settings.mode", "Data")
    fda("sa", "handler", "WebsocketServer.Orchestrator_Flow.settings.format", "String")
    fda("wth", "Orchestrator_Flow", "WebsocketServer.Orchestrator_Flow", "--force",
        "--input", "content:any,wsconnection:any,pathParams:params,queryParams:params,headers:object", "--inputs-only")
    fda("cs", "OrcWsHeaders", ORC_WS_HEADERS)
    fda("sa", "handler", "WebsocketServer.Orchestrator_Flow.schemas.output.headers", "OrcWsHeaders", "-C", "schema", "--force")
    meta = [{"name": "pathParams", "type": "params"}, {"name": "queryParams", "type": "params"},
            {"name": "headers", "type": "object"}, {"name": "content", "type": "any"},
            {"name": "wsconnection", "type": "any"}]
    sa_jsonfile("flow", "Orchestrator_Flow.metadata.input", meta)
    print("== Orchestrator done ==\n")

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("mcp", "all"):
        build_mcp()
    if which in ("a2a", "all"):
        build_a2a()
    if which in ("orc", "all"):
        build_orc()
    print("BUILD COMPLETE:", which)
