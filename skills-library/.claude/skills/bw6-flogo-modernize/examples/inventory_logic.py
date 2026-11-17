"""Business logic of Retail.Inventory.API rebuilt in Flogo (worked example: dead Java code, synthetic
"not found" records, several outcomes per operation, body-field lookups, a reshaped static list).

BW6 source (decoded by analyze_bw6.py):
  GET  /api/inventory/products/{sku}        product[sku = $param][1] -> product fields + selected attributes
       (JavaInvoke JsonToXmlConverter + ParseXml run too, but the reply never reads them -> not carried over)
  GET  /api/inventory/availability?sku&storeId
       ProductInventoryList (products x inventory join) -> InventoryList (flatten)
       -> InventoryList2: copy + append {sku, storeId, productName?, quantity:0, status:'unknown'} when no match
       -> reply for-each match: fields; aisle = '' when empty; message when status = 'unknown'
  POST /api/inventory/reservations          approval stub {requiresApproval, toolName, arguments{sku?,storeId?,customerId?}, message}
  GET  /api/inventory/tools                 static tool list; the XSLT keeps only properties.sku (as {}) - reproduced
  POST /api/inventory/tools/get_product     = GET products/{sku} with sku from the body
  POST /api/inventory/tools/check_inventory inventory[sku, storeId from body] (no synthetic record) + productName?
  POST /api/inventory/tools/reserve_inventory  approval stub (same shape as reservations)

Usage: python inventory_logic.py <work>/plan.json
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from flogo_logic_lib import Logic  # noqa: E402

L = Logic(sys.argv[1] if len(sys.argv) > 1 else None)   # <work>/plan.json from scaffold_flogo_app.py
G, C, R = L.flow("get_product"), L.flow("check_inventory"), L.flow("reserve_inventory")
T = L.flow("get_api_inventory_tools")
TG = L.flow("post_api_inventory_tools_get_product")
TC = L.flow("post_api_inventory_tools_check_inventory")
TR = L.flow("post_api_inventory_tools_reserve_inventory")

PRODUCT_FIELDS = ("sku", "name", "brand", "category", "price", "description")
ATTRIBUTES = ("color", "gender", "use", "returnWindowDays", "warrantyMonths", "capacityLiters", "batteryDays",
              "thicknessMm", "capacityOz", "batteryHours")          # the attributes the BW reply copies
UNKNOWN_MSG = "No inventory record was found for this store."
APPROVAL_MSG = "This operation changes retail state and must be approved through the agent approval flow."
PRD, STK = "$activity[FindProduct].output.matches[0]", "$activity[FindStock].output.matches[0]"
count = lambda act: f"array.count($activity[{act}].output.matches)"


def product_lookup(flow, products_activity, key, body_fields=()):
    """product[sku = key][1] -> product + attributes; 404 when no product (BW: Java 500)."""
    L.unlink_placeholder(flow)
    items = L.static_dataset(flow, "ProductData", {"products": L.bw_json(flow, products_activity)},
                             f"Embedded product list (BW {products_activity})")
    L.require_params(flow, after="Log_API", next_step="ProductData", body_fields=body_fields)
    L.select(flow, "FindProduct", "$activity[ProductData].output.products", items["products"],
             f"$loop[p].sku == {key}", iterator="p", desc="Product with the requested sku")
    L.link(flow, "ProductData", "FindProduct")
    L.error(flow, "NotFound", 404, "product_not_found", f'=string.concat("No product found with sku ", {key})')
    L.link(flow, "FindProduct", "NotFound", f"{count('FindProduct')} == 0")
    L.response(flow, "ConfigureHTTPResponse", 200, f"{flow}_Body", L.op(flow)["ok"], dict(
        **{f: f"={PRD}.{f}" for f in PRODUCT_FIELDS},
        **{f"attributes.{a}": f"={PRD}.attributes.{a}" for a in ATTRIBUTES}))
    L.link(flow, "FindProduct", "ConfigureHTTPResponse", f"{count('FindProduct')} > 0")


def approval_stub(flow):
    L.response(flow, "ConfigureHTTPResponse", 200, f"{flow}_Body", L.op(flow)["ok"], {
        "requiresApproval": True, "toolName": "reserve_inventory",
        "arguments.sku": "=$flow.body.sku", "arguments.storeId": "=$flow.body.storeId",
        "arguments.customerId": "=$flow.body.customerId", "message": APPROVAL_MSG})


# ---------------------------------------------------------------- products by sku (path and body variants)
product_lookup(G, "ParseProductsJSON", "$flow.pathParams.sku")
product_lookup(TG, "ParseProductsJSON3", "$flow.body.sku", body_fields=("sku",))

# ---------------------------------------------------------------- GET /api/inventory/availability
q = "$flow.queryParams"
L.unlink_placeholder(C)
items = L.static_dataset(C, "ReferenceData", {"products": L.bw_json(C, "ParseProductsJSON1"),
                                              "inventory": L.bw_json(C, "ParseInventoryJSON")},
                         "Embedded products and inventory (BW ParseProductsJSON1 / ParseInventoryJSON)")
L.require_params(C, after="Log_API", next_step="ReferenceData")
L.select(C, "FindStock", "$activity[ReferenceData].output.inventory", items["inventory"],
         f"$loop[i].sku == {q}.sku && $loop[i].storeId == {q}.storeId", iterator="i",
         desc="Inventory record for sku + store")
L.link(C, "ReferenceData", "FindStock")
L.select(C, "AnyStock", "$activity[ReferenceData].output.inventory", items["inventory"],
         f"$loop[a].sku == {q}.sku", iterator="a", desc="Inventory records for the sku at any store")
L.link(C, "FindStock", "AnyStock")
L.select(C, "FindProduct", "$activity[ReferenceData].output.products", items["products"],
         f"$loop[p].sku == {q}.sku", iterator="p", desc="Product of the sku (BW joins products x inventory)")
L.link(C, "AnyStock", "FindProduct")
S, A, P = count("FindStock"), count("AnyStock"), count("FindProduct")
ok = L.op(C)["ok"]
# found: the joined (product x inventory) record exists
L.response(C, "ConfigureHTTPResponse", 200, "AvailabilityBody", ok, {
    "sku": f"={STK}.sku", "storeId": f"={STK}.storeId", "productName": f"={PRD}.name",
    "quantity": f"={STK}.quantity", "aisle": f"=coerce.toString({STK}.aisle)", "status": f"={STK}.status"})
L.link(C, "FindProduct", "ConfigureHTTPResponse", f"{P} > 0 && {S} > 0")
# not found: BW appends a synthetic 'unknown' record; productName only when the sku is stocked elsewhere
unknown = {"sku": f"={q}.sku", "storeId": f"={q}.storeId", "quantity": 0, "aisle": '=""',
           "status": "unknown", "message": UNKNOWN_MSG}
L.response(C, "UnknownStockNamed", 200, "AvailabilityBody", ok, dict(unknown, productName=f"={PRD}.name"))
L.link(C, "FindProduct", "UnknownStockNamed", f"{P} > 0 && {A} > 0 && {S} == 0")
L.response(C, "UnknownStock", 200, "AvailabilityBody", ok, unknown)
L.link(C, "FindProduct", "UnknownStock", f"{P} == 0 || {A} == 0")

# ---------------------------------------------------------------- POST /api/inventory/tools/check_inventory
b = "$flow.body"
L.unlink_placeholder(TC)
items = L.static_dataset(TC, "ReferenceData", {"products": L.bw_json(TC, "ParseProductsJSON4"),
                                               "inventory": L.bw_json(TC, "ParseInventoryJSON4")},
                         "Embedded products and inventory (BW ParseProductsJSON4 / ParseInventoryJSON4)")
L.require_params(TC, after="Log_API", next_step="ReferenceData", body_fields=("sku", "storeId"))
L.select(TC, "FindStock", "$activity[ReferenceData].output.inventory", items["inventory"],
         f"$loop[i].sku == {b}.sku && $loop[i].storeId == {b}.storeId", iterator="i", desc="Inventory record for sku + store")
L.link(TC, "ReferenceData", "FindStock")
L.select(TC, "FindProduct", "$activity[ReferenceData].output.products", items["products"],
         f"$loop[p].sku == {b}.sku", iterator="p", desc="Product name for the sku")
L.link(TC, "FindStock", "FindProduct")
S, P = count("FindStock"), count("FindProduct")
stock = {"sku": f"={STK}.sku", "storeId": f"={STK}.storeId", "quantity": f"={STK}.quantity",
         "aisle": f"={STK}.aisle", "status": f"={STK}.status"}
L.response(TC, "ConfigureHTTPResponse", 200, "ToolAvailabilityBody", L.op(TC)["ok"], dict(stock, productName=f"={PRD}.name"))
L.link(TC, "FindProduct", "ConfigureHTTPResponse", f"{S} > 0 && {P} > 0")
L.response(TC, "StockWithoutProduct", 200, "ToolAvailabilityBody", L.op(TC)["ok"], stock)
L.link(TC, "FindProduct", "StockWithoutProduct", f"{S} > 0 && {P} == 0")
L.error(TC, "NotFound", 404, "inventory_not_found",
        f'=string.concat("No inventory record for sku ", {b}.sku, " at store ", {b}.storeId)')
L.link(TC, "FindProduct", "NotFound", f"{S} == 0")

# ---------------------------------------------------------------- GET /api/inventory/tools (static list)
# The BW XSLT copies name/description/safety/inputSchema.type/required and turns properties into {"sku": {}}
# (only when the tool declares sku) - reproduced exactly from the BW literal.
tools = []
for t in L.bw_json(T, "ParseJSON")["tools"]:
    s = t.get("inputSchema", {})
    out = {k: t[k] for k in ("name", "description", "safety") if k in t}
    out["inputSchema"] = {k: v for k, v in (("type", s.get("type")), ("required", s.get("required"))) if v is not None}
    if "properties" in s:
        out["inputSchema"]["properties"] = {"sku": {}} if "sku" in s["properties"] else {}
    tools.append(out)
L.response(T, "ConfigureHTTPResponse", 200, "InventoryToolsBody", L.op(T)["ok"], {"tools": tools})

# ---------------------------------------------------------------- approval stubs
approval_stub(R)
approval_stub(TR)

sys.exit(L.finish())
