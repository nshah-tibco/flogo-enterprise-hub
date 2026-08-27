#!/usr/bin/env python3
"""Build RealEstateMCPServer.flogo with fda only. Secrets from env."""
import subprocess, os, sys, json

FDA  = os.environ["FDA"]
DIR  = os.path.dirname(os.path.abspath(__file__))
FILE = os.path.join(DIR, "RealEstateMCPServer.flogo")

PG_HOST = "localhost"; PG_PORT = "5432"; PG_DB = "realestate"; PG_USER = "postgres"
PG_PWD  = os.environ["PG_PWD"]
MCP_PORT = "9592"; ENDPOINT = "/realestate-mls"

def fda(*args, allow_fail=False):
    r = subprocess.run([FDA, *map(str, args), "-f", FILE], capture_output=True, text=True)
    out = (r.stdout or "") + (r.stderr or "")
    tag = " ".join(str(a) for a in args[:3])
    if "(ERROR)" in out and not allow_fail:
        print("FAILED:", " ".join(map(str, args))); print(out[-1500:]); sys.exit(1)
    print("  ok:", tag)
    return out

def conn_uuid(name):
    conns = json.load(open(FILE))["connections"]
    items = list(conns.values()) if isinstance(conns, dict) else conns
    return "conn://" + next(c["id"] for c in items if c["name"] == name)

if os.path.exists(FILE): os.remove(FILE)

print("== project + properties + PostgreSQL connection ==")
fda("cp", "RealEstateMCPServer", "Real Estate MCP Server")
fda("cap", "PostgreSQL.PostgresConn.Host",          "string", PG_HOST)
fda("cap", "PostgreSQL.PostgresConn.Port",          "number", PG_PORT)
fda("cap", "PostgreSQL.PostgresConn.Database_Name", "string", PG_DB)
fda("cap", "PostgreSQL.PostgresConn.User",          "string", PG_USER)
fda("cap", "PostgreSQL.PostgresConn.Password",      "string", PG_PWD)
fda("cap", "MCP_SERVER_PORT",                        "string", MCP_PORT)

fda("cc", "PostgresConn", "con_postgresql")
fda("sa", "connection", "PostgresConn.settings.databaseType", "PostgreSQL")
fda("sa", "connection", "PostgresConn.settings.host",         "PostgreSQL.PostgresConn.Host",          "-C", "app-property")
fda("sa", "connection", "PostgresConn.settings.port",         "PostgreSQL.PostgresConn.Port",          "-C", "app-property")
fda("sa", "connection", "PostgresConn.settings.databaseName", "PostgreSQL.PostgresConn.Database_Name", "-C", "app-property")
fda("sa", "connection", "PostgresConn.settings.user",         "PostgreSQL.PostgresConn.User",          "-C", "app-property")
fda("sa", "connection", "PostgresConn.settings.password",     "PostgreSQL.PostgresConn.Password",      "-C", "app-property")
PG_REF = conn_uuid("PostgresConn")
print("  PG_REF =", PG_REF)

print("== trigger ==")
fda("ct", "RealEstateMCPServer", "tr_mcpserver", "Real Estate MCP server")
fda("sa", "trigger", "RealEstateMCPServer.settings.serverType",         "HTTP")
fda("sa", "trigger", "RealEstateMCPServer.settings.serverPort",         "MCP_SERVER_PORT", "-C", "app-property")
fda("sa", "trigger", "RealEstateMCPServer.settings.serverEndpointPath", ENDPOINT)
fda("sa", "trigger", "RealEstateMCPServer.settings.serverName",         "RealEstateMCPServer")
fda("sa", "trigger", "RealEstateMCPServer.settings.serverVersion",      "1.0.0")

print("== shared tool schemas ==")
fda("cs", "EmptyArgs",    '{"type":"object","properties":{}}')
fda("cs", "ToolResponse", '{"type":"object","properties":{"data":{"type":"string"},"error":{"type":"string"}}}')

TOOLS = [
  ("getLeads", "GetLeadProfile",
   "Look up a real estate lead's full CRM profile by lead id (LEAD-2026-NNNNN), email, or phone: name, contact, lead type (Buyer/Seller/Both), funnel stage, budget range, preferred city/zip/beds/baths, property type, timeline, source, and assigned agent id. Use this to recognize the prospect and recall their saved home-search criteria.",
   "SELECT * FROM public.leads ORDER BY lead_id ASC;"),
  ("getLeadActivity", "GetLeadActivity",
   "Return a lead's engagement history: searches run, listings viewed and saved, emails opened, recommendations sent, and funnel stage changes. Use to understand what a prospect has been looking at.",
   "SELECT * FROM public.lead_activity ORDER BY activity_id ASC;"),
  ("getListings", "SearchListings",
   "Search the property catalog (MLS). Returns listings with address, city, state, zip, price, bedrooms, bathrooms, square footage, property type, status (Active/Pending/Sold), days on market, MLS id, and description. Filter results to the user's city, price range, and bed/bath needs.",
   "SELECT * FROM public.listings ORDER BY listing_id ASC;"),
  ("getAgents", "GetAssignedAgent",
   "Return real estate agent details (name, email, phone, brokerage, service area, specialization). Use with a lead's assigned agent id to tell the prospect who their agent is or to route a follow-up.",
   "SELECT * FROM public.agents ORDER BY agent_id ASC;"),
  ("getAppointments", "GetLeadAppointments",
   "Return a lead's property showings (appointments): the listing, scheduled date/time, and status (Requested/Confirmed/Completed/Cancelled). Use to tell a prospect what tours they have scheduled.",
   "SELECT * FROM public.appointments ORDER BY appointment_id ASC;"),
  ("getMarketStats", "GetAreaMarketInsights",
   "Return residential real-estate market statistics by city and zip: median price, average days on market, active inventory, median price per square foot, and year-over-year price change. Use to answer 'how's the market' questions.",
   "SELECT * FROM public.area_market_stats ORDER BY stat_id ASC;"),
]

for flow, tool, desc, sql in TOOLS:
    print(f"== tool {tool} ({flow}) ==")
    fda("cf", flow, desc)
    fda("ca", flow, "PostgreSQLQuery", "act_postgresql_query", "PostgreSQL Query", "-C", "PostgresConn")
    fda("ca", flow, "Return", "act_default_actreturn", "Simple Return")
    fda("sa", "activity", f"{flow}.PostgreSQLQuery.input.Connection", PG_REF)
    fda("sa", "activity", f"{flow}.PostgreSQLQuery.input.Query", sql)
    fda("sa", "activity", f"{flow}.PostgreSQLQuery.input.Schema", "public")
    fda("cth", flow, "RealEstateMCPServer", desc,
        "--mcpHandlerType", "Tool", "--mcpHandlerName", tool, "--mcpHandlerDescription", desc)
    fda("wth", flow, f"RealEstateMCPServer.{flow}", "--force")
    fda("sa", "handler", f"RealEstateMCPServer.{flow}.schemas.output.arguments", "EmptyArgs",   "-C", "schema", "--force")
    fda("sa", "handler", f"RealEstateMCPServer.{flow}.schemas.reply.response",   "ToolResponse", "-C", "schema", "--force")
    fda("mm", f"{flow}.Return.input.mappings.response.mapping.data",
        "=coerce.toString($activity[PostgreSQLQuery].Output)")

print("\nMCP server build complete:", FILE)
