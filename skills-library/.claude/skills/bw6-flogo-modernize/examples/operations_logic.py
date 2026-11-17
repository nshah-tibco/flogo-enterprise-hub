"""Business logic of Retail.Operations.API rebuilt in Flogo (worked example: SQL Server JDBC reads/writes,
a branching write flow with an authorization check, and static/reference replies).

BW6 source (decoded by analyze_bw6.py; SQL captured from the JDBC activities, conditions from the links):
  POST /api/approve        ValidateApproveRequest -> ResolveUser (users literal, by userId)
                           -> [role = store_manager | admin] GetPendingApproval (SELECT ... WHERE approval_id=? AND status='pending')
                              else Throw (BW 500)
                           -> [tool_name] INSERT reservation | return authorization | promotion application
                           -> ApprovedByJson/ResultJSON (JsonRender) -> CompleteApproval (UPDATE approvals)
                           -> [conversationId given] UPDATE conversations -> INSERT system message -> reply
                           (QueryApproval runs too but nothing reads it - not carried over)
  GET  /api/operations     TOP 20 approvals + TOP 20 reservations -> reshaped lists
  GET  /api/conversations  TOP 25 conversations with message counts
  GET  /api/conversations/{conversationId}   conversation + its messages
  POST /api/demo/reset     DELETE all six tables (BW: one SQLDirect batch) -> counts
  GET  /api/users | /api/demo/scenarios | /api/status | POST /api/evals   literal / count replies

GUID columns are SELECTed as CONVERT(nvarchar(36), x): the Flogo SQL Server connector returns uniqueidentifier in
lower case, BW's JDBC driver in SQL Server's upper case (CONVERT also keeps NULL as NULL).

BW quirks reproduced on purpose (parity): the INSERTs store '1' for sku/order_id/promotion_id and the APPROVER's
name as product_name; result_json.toolName is the tool name only for reserve_inventory, otherwise the status.

Usage: SQL_PASSWORD=<password> [SQL_HOST=<db-host>] python operations_logic.py <work>/plan.json <sql-user>
(the password comes from the environment, not the command line, so it never shows in the process list; it is
stored encrypted as SECRET: in the connection)
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from flogo_logic_lib import Logic, negate  # noqa: E402

L = Logic(sys.argv[1] if len(sys.argv) > 1 else None)   # <work>/plan.json from scaffold_flogo_app.py
SQL_USER = sys.argv[2] if len(sys.argv) > 2 else sys.exit("usage: SQL_PASSWORD=<password> python operations_logic.py "
                                                          "<work>/plan.json <sql-user>  (the database user is required)")
SQL_PASSWORD = os.environ.get("SQL_PASSWORD") or sys.exit("set SQL_PASSWORD (the database password; BW's is obfuscated)")
spec = L.spec or json.load(open(os.path.join(L.work, "analysis", "Retail_Operations_API.bw6spec.json"), encoding="utf-8"))
jdbc = next(r for r in spec["sharedResources"] if r["kind"] == "jdbcResource")["settings"]
# the BW URL says 127.0.0.1; this demo's SQL Server container answers on localhost. SQL_HOST overrides the host
# for a database somewhere else (default: localhost, as in the parity runs)
DB = L.db_connection("RetailOpsDB", jdbc["dbURL"].replace("127.0.0.1", os.environ.get("SQL_HOST", "localhost")),
                     SQL_USER, SQL_PASSWORD)

AP, OP, CV, CD = (L.flow("post_api_approve"), L.flow("get_api_operations"), L.flow("get_api_conversations_GET"),
                  L.flow("get_api_conversations_conversationId"))
RS, US, SC, ST, EV = (L.flow("post_api_demo_reset"), L.flow("get_api_users"), L.flow("get_api_demo_scenarios"),
                      L.flow("get_api_status"), L.flow("post_api_evals"))
GUID = '"^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$"'
is_guid = lambda x: f"string.matchRegEx({GUID}, coerce.toString({x}))"
count = lambda act, out="Output.records": f"array.count($activity[{act}].{out})"
rec = lambda act: f"$activity[{act}].Output.records[0]"
S = "string"


def counts_queries(flow, after, q1="OperationCounts", q2="ConversationCounts"):
    L.sql(flow, q1, "query", "SELECT (SELECT COUNT(*) FROM retail_approvals) AS approvals, (SELECT COUNT(*) FROM retail_reservations) "
          "AS reservations, (SELECT COUNT(*) FROM retail_return_authorizations) AS return_authorizations, (SELECT COUNT(*) FROM "
          "retail_promotion_applications) AS promotion_applications;", DB,
          columns={"approvals": "integer", "reservations": "integer", "return_authorizations": "integer",
                   "promotion_applications": "integer"}, desc="Row counts of the operations tables")
    L.link(flow, after, q1)
    L.sql(flow, q2, "query", "SELECT (SELECT COUNT(*) FROM retail_conversations) AS conversations, (SELECT COUNT(*) FROM "
          "retail_conversation_messages) AS messages;", DB, columns={"conversations": "integer", "messages": "integer"},
          desc="Row counts of the conversation tables")
    L.link(flow, q1, q2)
    return {"operations.approvals": f"={rec(q1)}.approvals", "operations.reservations": f"={rec(q1)}.reservations",
            "operations.returnAuthorizations": f"={rec(q1)}.return_authorizations",
            "operations.promotionApplications": f"={rec(q1)}.promotion_applications",
            "conversations.conversations": f"={rec(q2)}.conversations", "conversations.messages": f"={rec(q2)}.messages"}


# ================================================================ POST /api/approve
b = "$flow.body"
USER = "$activity[FindUser].output.matches[0]"
PEND = rec("GetPendingApproval")
L.unlink_placeholder(AP)
users = L.bw_json(AP, "ParseUsersJSON")
items = L.static_dataset(AP, "UserData", {"users": users}, "Demo users and roles (BW ParseUsersJSON literal)")
L.error(AP, "BadRequest", 400, "invalid_request",
        "approvalId (a GUID) and userId are required; conversationId must be a GUID when given")
bad = (f'coerce.toString({b}.userId) == "" || {negate(is_guid(b + ".approvalId"))} || '
       f'(coerce.toString({b}.conversationId) != "" && {negate(is_guid(b + ".conversationId"))})')
L.link(AP, "Log_API", "BadRequest", bad)
L.link(AP, "Log_API", "UserData", negate(bad))
L.select(AP, "FindUser", "$activity[UserData].output.users", items["users"], f"$loop[u].userId == {b}.userId",
         iterator="u", desc="Approving user (BW ResolveUser)")
L.link(AP, "UserData", "FindUser")
allowed = f'{count("FindUser", "output.matches")} > 0 && ({USER}.role == "store_manager" || {USER}.role == "admin")'
L.error(AP, "Forbidden", 403, "forbidden", "Only a store_manager or admin can approve actions")
L.link(AP, "FindUser", "Forbidden", negate(allowed))
L.sql(AP, "GetPendingApproval", "query",
      "SELECT approval_id, tool_name, arguments_json, summary, status FROM retail_approvals WHERE approval_id = ?approval_id AND status = 'pending';",
      DB, {"approval_id": (S, f"={b}.approvalId")},
      {"approval_id": S, "tool_name": S, "arguments_json": S, "summary": S, "status": S}, "Pending approval by id")
L.link(AP, "FindUser", "GetPendingApproval", allowed)
L.error(AP, "NotFound", 404, "approval_not_found",
        f'=string.concat("No pending approval with id ", {b}.approvalId)')
L.link(AP, "GetPendingApproval", "NotFound", f"{count('GetPendingApproval')} == 0")
TOOL = f"{PEND}.tool_name"
inserts = {
    "reserve_inventory": ("InsertReservation",
        "INSERT INTO retail_reservations ( reservation_id, approval_id, sku, product_name, store_id, customer_id, quantity_reserved, "
        "expires_in_minutes ) VALUES (?reservation_id, ?approval_id, ?sku, ?product_name, ?store_id, ?customer_id, 1, 90);",
        {"reservation_id": (S, '=string.concat("RSV-", datetime.now())'), "approval_id": (S, f"={b}.approvalId"),
         "sku": (S, "1"), "product_name": (S, f"={USER}.name"), "store_id": (S, f"={USER}.storeId"),
         "customer_id": (S, f"={USER}.customerId")}),
    "create_return_authorization": ("InsertReturnAuthorization",
        "INSERT INTO retail_return_authorizations ( return_authorization_id, approval_id, order_id, sku, product_name, status ) "
        "VALUES (?return_authorization_id, ?approval_id, ?order_id, ?sku, ?product_name, 'created');",
        {"return_authorization_id": (S, '=string.concat("RMA-", datetime.now())'), "approval_id": (S, f"={b}.approvalId"),
         "order_id": (S, "1"), "sku": (S, "1"), "product_name": (S, f"={USER}.name")}),
    "apply_promotion": ("InsertPromotionApplication",
        "INSERT INTO retail_promotion_applications ( promotion_application_id, approval_id, customer_id, promotion_id, sku, status ) "
        "VALUES (?promotion_application_id, ?approval_id, ?customer_id, ?promotion_id, ?sku, 'applied');",
        {"promotion_application_id": (S, '=string.concat("PRM-", datetime.now())'), "approval_id": (S, f"={b}.approvalId"),
         "customer_id": (S, f"={USER}.customerId"), "promotion_id": (S, "1"), "sku": (S, "1")}),
}
for tool, (act, stmt, params) in inserts.items():
    L.sql(AP, act, "insert", stmt, DB, params, desc=f"Execute the approved {tool}")
    L.link(AP, "GetPendingApproval", act, f'{count("GetPendingApproval")} > 0 && {TOOL} == "{tool}"')
L.error(AP, "UnsupportedTool", 422, "unsupported_tool", f'=string.concat("Approvals for tool ", {TOOL}, " are not supported")')
L.link(AP, "GetPendingApproval", "UnsupportedTool",
       f'{count("GetPendingApproval")} > 0 && {TOOL} != "reserve_inventory" && {TOOL} != "create_return_authorization" '
       f'&& {TOOL} != "apply_promotion"')
# BW ApprovedByJson / ResultJSON (JsonRender) -> mappers rendered with utility.renderJSON
L.compute(AP, "ApprovedBy", {"userId": (S, f"={USER}.userId"), "name": (S, f"={USER}.name"), "role": (S, f"={USER}.role")},
          desc="BW ApprovedByJson: approver identity")
for act in (a for a, _, _ in inserts.values()):
    L.link(AP, act, "ApprovedBy")
L.compute(AP, "ApprovalResult", {"status": (S, f"={PEND}.status"),
                                 "toolName": (S, f'={TOOL} == "reserve_inventory" ? {TOOL} : {PEND}.status')},
          desc="BW ResultJSON (toolName = status for non-reserve tools, as in BW)")
L.link(AP, "ApprovedBy", "ApprovalResult")
L.sql(AP, "CompleteApproval", "update",
      "UPDATE retail_approvals SET status = 'approved', completed_at = SYSDATETIMEOFFSET(), approved_by_json = ?approved_by_json, "
      "result_json = ?result_json WHERE approval_id = ?approval_id AND status = 'pending';", DB,
      {"approved_by_json": (S, "=utility.renderJSON($activity[ApprovedBy].output, false)"),
       "result_json": (S, "=utility.renderJSON($activity[ApprovalResult].output, false)"),
       "approval_id": (S, f"={b}.approvalId")}, desc="Mark the approval approved")
L.link(AP, "ApprovalResult", "CompleteApproval")
L.sql(AP, "TouchConversation", "update",
      "UPDATE retail_conversations SET updated_at = SYSDATETIMEOFFSET() WHERE conversation_id = ?conversation_id;", DB,
      {"conversation_id": (S, f"={b}.conversationId")}, desc="Bump the conversation")
has_conv = f'coerce.toString({b}.conversationId) != ""'
L.link(AP, "CompleteApproval", "TouchConversation", has_conv)
L.sql(AP, "AppendSystemMessage", "insert",
      "INSERT INTO retail_conversation_messages ( message_id, conversation_id, role, content, user_id, trace_json ) "
      "VALUES (?message_id, ?conversation_id, 'system', ?content, ?user_id, ?trace_json);", DB,
      {"message_id": (S, "=utils.uuid()"), "conversation_id": (S, f"={b}.conversationId"),
       "content": (S, "Approved action completed: "), "user_id": (S, f"={b}.userId"), "trace_json": (S, '="{}"')},
      desc="Record the approval in the conversation")
L.link(AP, "TouchConversation", "AppendSystemMessage")
approved = {"approvalId": f"={b}.approvalId", "toolName": f"={TOOL}", "approvedBy.userId": f"={b}.userId",
            "persistence.provider": "sqlserver", "persistence.approvalId": f"={b}.approvalId",
            "conversation.provider": "sqlserver"}
L.response(AP, "ConfigureHTTPResponse", 200, "ApproveBody", L.op(AP)["ok"], dict(
    approved, **{"conversation.conversationId": f"={b}.conversationId",
                 "conversation.messageCount": "=$activity[AppendSystemMessage].Output.rowsAffected"}))
L.link(AP, "AppendSystemMessage", "ConfigureHTTPResponse")
# BW never replies when conversationId is absent (missing reply after the approval is written) - Flogo replies
L.response(AP, "ApprovedNoConversation", 200, "ApproveBody", L.op(AP)["ok"], approved)
L.link(AP, "CompleteApproval", "ApprovedNoConversation", negate(has_conv))

# ================================================================ GET /api/operations
L.unlink_placeholder(OP)
L.sql(OP, "RecentApprovals", "query",
      "SELECT TOP 20 CONVERT(nvarchar(36), approval_id) AS approval_id, tool_name, arguments_json, summary, status, approved_by_json, result_json "
      "FROM retail_approvals ORDER BY created_at DESC;",
      DB, columns={c: S for c in ("approval_id", "tool_name", "arguments_json", "summary", "status", "approved_by_json", "result_json")},
      desc="Latest approvals")
L.link(OP, "Log_API", "RecentApprovals")
L.sql(OP, "RecentReservations", "query",
      "SELECT TOP 20 reservation_id, CONVERT(nvarchar(36), approval_id) AS approval_id, sku, product_name, store_id, customer_id, quantity_reserved, "
      "expires_in_minutes FROM retail_reservations ORDER BY created_at DESC;",
      DB, columns={"reservation_id": S, "approval_id": S, "sku": S, "product_name": S, "store_id": S, "customer_id": S,
                   "quantity_reserved": "integer", "expires_in_minutes": "integer"}, desc="Latest reservations")
L.link(OP, "RecentApprovals", "RecentReservations")
L.project(OP, "Shape", {
    "approvals": ("$activity[RecentApprovals].Output.records", "a", {
        "approvalId": (S, "=$loop[a].approval_id"), "toolName": (S, "=$loop[a].tool_name"),
        "summary": (S, "=$loop[a].summary"), "status": (S, "=$loop[a].status")}),
    "reservations": ("$activity[RecentReservations].Output.records", "r", {
        "reservationId": (S, "=$loop[r].reservation_id"), "approvalId": (S, "=$loop[r].approval_id"),
        "sku": (S, "=$loop[r].sku"), "productName": (S, "=$loop[r].product_name"), "storeId": (S, "=$loop[r].store_id"),
        "customerId": (S, "=$loop[r].customer_id"), "quantityReserved": ("integer", "=$loop[r].quantity_reserved"),
        "expiresInMinutes": ("integer", "=$loop[r].expires_in_minutes")}),
}, desc="BW reply for-each over Record")
L.link(OP, "RecentReservations", "Shape")
L.response(OP, "ConfigureHTTPResponse", 200, "OperationsBody", L.op(OP)["ok"], {
    "provider": "sqlserver", "approvals": "=$activity[Shape].output.approvals",
    "reservations": "=$activity[Shape].output.reservations"})
L.link(OP, "Shape", "ConfigureHTTPResponse")

# ================================================================ GET /api/conversations
CONV_COLS = {"conversation_id": S, "user_id": S, "customer_id": S, "store_id": S, "title": S, "message_count": "integer"}
conv_item = lambda it: {"conversationId": (S, f"=$loop[{it}].conversation_id"), "userId": (S, f"=$loop[{it}].user_id"),
                        "customerId": (S, f"=$loop[{it}].customer_id"), "storeId": (S, f"=$loop[{it}].store_id"),
                        "title": (S, f"=$loop[{it}].title"), "messageCount": ("integer", f"=$loop[{it}].message_count")}
L.unlink_placeholder(CV)
L.sql(CV, "RecentConversations", "query",
      "SELECT TOP 25 CONVERT(nvarchar(36), c.conversation_id) AS conversation_id, c.user_id, c.customer_id, c.store_id, c.title, COUNT(m.message_id) AS message_count FROM "
      "retail_conversations c LEFT JOIN retail_conversation_messages m ON m.conversation_id = c.conversation_id GROUP BY "
      "c.conversation_id, c.user_id, c.customer_id, c.store_id, c.title, c.created_at, c.updated_at ORDER BY c.updated_at DESC;",
      DB, columns=CONV_COLS, desc="Latest conversations with message counts")
L.link(CV, "Log_API", "RecentConversations")
L.project(CV, "Shape", {"conversations": ("$activity[RecentConversations].Output.records", "c", conv_item("c"))})
L.link(CV, "RecentConversations", "Shape", f"{count('RecentConversations')} > 0")
L.response(CV, "ConfigureHTTPResponse", 200, "ConversationsBody", L.op(CV)["ok"],
           {"provider": "sqlserver", "conversations": "=$activity[Shape].output.conversations"})
L.link(CV, "Shape", "ConfigureHTTPResponse")
# BW <otherwise>: one conversations element whose children are all xsi:nil
L.response(CV, "NoConversations", 200, "ConversationsBody", L.op(CV)["ok"], {"provider": "sqlserver", "conversations": [{}]})
L.link(CV, "RecentConversations", "NoConversations", f"{count('RecentConversations')} == 0")

# ================================================================ GET /api/conversations/{conversationId}
cid = "$flow.pathParams.conversationId"
L.unlink_placeholder(CD)
L.error(CD, "BadRequest", 400, "invalid_request", "conversationId must be a GUID")
L.link(CD, "Log_API", "BadRequest", negate(is_guid(cid)))
L.sql(CD, "Conversation", "query",
      "SELECT CONVERT(nvarchar(36), c.conversation_id) AS conversation_id, c.user_id, c.customer_id, c.store_id, c.title, COUNT(m.message_id) AS message_count FROM "
      "retail_conversations c LEFT JOIN retail_conversation_messages m ON m.conversation_id = c.conversation_id WHERE "
      "c.conversation_id = ?conversation_id GROUP BY c.conversation_id, c.user_id, c.customer_id, c.store_id, c.title, c.created_at, c.updated_at;",
      DB, {"conversation_id": (S, f"={cid}")}, CONV_COLS, "Conversation by id")
L.link(CD, "Log_API", "Conversation", is_guid(cid))
L.sql(CD, "Messages", "query",
      "SELECT CONVERT(nvarchar(36), message_id) AS message_id, CONVERT(nvarchar(36), conversation_id) AS conversation_id, role, content, "
      "user_id, trace_json FROM retail_conversation_messages WHERE "
      "conversation_id = ?conversation_id ORDER BY created_at ASC;", DB, {"conversation_id": (S, f"={cid}")},
      {"message_id": S, "conversation_id": S, "role": S, "content": S, "user_id": S, "trace_json": S}, "Messages of the conversation")
L.link(CD, "Conversation", "Messages")
L.project(CD, "Shape", {"messages": ("$activity[Messages].Output.records", "m", {
    "messageId": (S, "=$loop[m].message_id"), "conversationId": (S, "=$loop[m].conversation_id"),
    "role": (S, "=$loop[m].role"), "content": (S, "=$loop[m].content"), "userId": (S, "=$loop[m].user_id")})})
L.link(CD, "Messages", "Shape")
C0 = rec("Conversation")
L.response(CD, "ConfigureHTTPResponse", 200, "ConversationDetailBody", L.op(CD)["ok"], {
    "provider": "sqlserver", "conversation.conversationId": f"={C0}.conversation_id", "conversation.userId": f"={C0}.user_id",
    "conversation.customerId": f"={C0}.customer_id", "conversation.storeId": f"={C0}.store_id",
    "conversation.title": f"={C0}.title", "conversation.messageCount": f"={C0}.message_count",
    "messages": "=$activity[Shape].output.messages"})
L.link(CD, "Shape", "ConfigureHTTPResponse", f"{count('Conversation')} > 0")
L.response(CD, "UnknownConversation", 200, "ConversationDetailBody", L.op(CD)["ok"], {"provider": "sqlserver"})
L.link(CD, "Shape", "UnknownConversation", f"{count('Conversation')} == 0")

# ================================================================ POST /api/demo/reset
L.unlink_placeholder(RS)
prev = "Log_API"
for table in ("retail_conversation_messages", "retail_conversations", "retail_promotion_applications",
              "retail_return_authorizations", "retail_reservations", "retail_approvals"):
    act = "Delete_" + table
    L.sql(RS, act, "delete", f"DELETE FROM {table};", DB, desc=f"Empty {table} (BW DeleteRecords batch)")
    L.link(RS, prev, act)
    prev = act
reset_counts = counts_queries(RS, prev, "OperationCountsAfter", "ConversationCountsAfter")
L.response(RS, "ConfigureHTTPResponse", 200, "ResetBody", L.op(RS)["ok"], dict(
    **{"reset.uploads.provider": "sqlserver", "reset.operations.provider": "sqlserver",
       "reset.conversations.provider": "sqlserver",
       "status.dataset.products": 10, "status.dataset.inventory": 0, "status.dataset.customers": 4,
       "status.dataset.orders": 5, "status.dataset.policies": 0,
       "status.ingestion.sourceCount": 0, "status.ingestion.chunkCount": 0,
       "status.ingestion.embedding.provider": "stub", "status.ingestion.storage.provider": "weaviate-pending",
       "status.ingestion.uploads": [], "status.ingestion.sampleChunks": [],  # BW renders its nil lists as []
       "status.operations.provider": "sqlserver", "status.conversations.provider": "sqlserver"},
    **{f"status.{k}": v for k, v in reset_counts.items()}))
L.link(RS, "ConversationCountsAfter", "ConfigureHTTPResponse")

# ================================================================ GET /api/status
L.unlink_placeholder(ST)
status_counts = counts_queries(ST, "Log_API")
dataset = {k: len(L.bw_json(ST, a)) for k, a in (("products", "ParseProductsJSON"), ("inventory", "ParseInventoryJSON"),
           ("customers", "ParseCustomerJSON"), ("orders", "ParseOrderJSON"), ("policies", "ParsePolicyJSON"))}
L.response(ST, "ConfigureHTTPResponse", 200, "StatusBody", L.op(ST)["ok"], dict(
    **{f"dataset.{k}": v for k, v in dataset.items()},
    **{"ingestion.sourceCount": 0, "ingestion.chunkCount": 0, "ingestion.embedding.provider": "stub",
       "ingestion.storage.provider": "weaviate-pending", "operations.provider": "sqlserver",
       "conversations.provider": "sqlserver"}, **status_counts))
L.link(ST, "ConversationCounts", "ConfigureHTTPResponse")

# ================================================================ static replies
L.response(US, "ConfigureHTTPResponse", 200, "UsersBody", L.op(US)["ok"], {"users": L.bw_json(US, "ParseUsersJSON2")})
L.response(SC, "ConfigureHTTPResponse", 200, "ScenariosBody", L.op(SC)["ok"],
           {"scenarios": L.bw_json(SC, "ParseScenariosJSON")["scenarios"]})
L.response(EV, "ConfigureHTTPResponse", 200, "EvalsBody", L.op(EV)["ok"], {
    "startedAt": "2026-05-18T10:00:00Z", "completedAt": "2026-05-18T10:00:00Z",
    **{f"summary.{k}": 0 for k in ("cases", "passed", "overallScore", "retrievalQuality", "toolSelectionAccuracy",
                                   "approvalSafety", "citationCorrectness")},
    "summary.scoreKeys": ["retrievalQuality", "toolSelectionAccuracy", "approvalSafety", "citationCorrectness"]})

sys.exit(L.finish())
