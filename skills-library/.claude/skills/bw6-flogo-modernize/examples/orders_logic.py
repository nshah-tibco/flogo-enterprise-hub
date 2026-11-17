"""Business logic of Retail.Orders.API rebuilt in Flogo (worked example: joins + XSLT variables + dates).

BW6 source (decoded by analyze_bw6.py):
  GET  /api/orders/{orderId}
       ParseOrderJSON / ParseProductsJSON / ParseCustomerJSON (JsonParser over literals)
       -> for-each order[orderId = $param][1]: order fields
            + for-each product[sku = current()/sku]          -> product {sku,name,brand,category,price,description}
            + for-each customer[customerId = current()/...]  -> customer {customerId,loyaltyTier,preferredStoreId}
  GET  /api/orders/returns/eligibility?orderId
       -> xsl:variable ageDays = abs(days-from-duration(date("2026-05-10") - date(purchaseDate)))
          xsl:variable returnWindowDays = product[sku = current()/sku]/attributes/returnWindowDays
          eligible = ageDays <= returnWindowDays; reason = choose/when concat(...)
  POST /api/orders/return-authorizations
       -> {approvalRequired:true, tool:'create_return_authorization', arguments:{orderId?}, message}
  (ParseInventoryJSON is parsed by the BW process but never used in the reply - not carried over.)

Usage: python orders_logic.py <work>/plan.json
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from flogo_logic_lib import Logic  # noqa: E402

L = Logic(sys.argv[1] if len(sys.argv) > 1 else None)   # <work>/plan.json from scaffold_flogo_app.py
F = L.flow("lookup_order")
E = L.flow("check_return_eligibility")
P = L.flow("create_return_authorization")

# Each BW branch parses ITS OWN copy of the data, and the copies differ (JKT-RAIN-210 returnWindowDays is
# 45 in the lookup branch, 15 in the eligibility branch) - so each flow takes its own branch's literals.
data_by_flow = {
    F: {"orders": L.bw_json(F, "ParseOrderJSON"), "products": L.bw_json(F, "ParseProductsJSON"),
        "customers": L.bw_json(F, "ParseCustomerJSON")},
    E: {"orders": L.bw_json(E, "ParseOrderJSON1"), "products": L.bw_json(E, "ParseProductsJSON1"),
        "customers": L.bw_json(E, "ParseCustomerJSON1")},
}
today = re.search(r'date\("(\d{4}-\d{2}-\d{2})"\)', L.bw_activity(E, "getOut1")["inputXslt"][0]).group(1)


def order_with_joins(flow, id_expr):
    """ReferenceData -> FindOrder (404 when missing) -> FindProduct -> FindCustomer."""
    L.unlink_placeholder(flow)
    items = L.static_dataset(flow, "ReferenceData", data_by_flow[flow], "Embedded orders, products and customers (BW JsonParser literals)")
    L.require_params(flow, after="Log_API", next_step="ReferenceData")
    L.select(flow, "FindOrder", "$activity[ReferenceData].output.orders", items["orders"],
             f"$loop[o].orderId == {id_expr}", iterator="o", desc="Order with the requested id (BW for-each[orderId = $param])")
    L.link(flow, "ReferenceData", "FindOrder")
    L.error(flow, "NotFound", 404, "order_not_found", f'=string.concat("No order found with id ", {id_expr})')
    L.link(flow, "FindOrder", "NotFound", "array.count($activity[FindOrder].output.matches) == 0")
    L.select(flow, "FindProduct", "$activity[ReferenceData].output.products", items["products"],
             "$loop[p].sku == $activity[FindOrder].output.matches[0].sku", iterator="p",
             desc="Product of the order (BW for-each[sku = current()/sku])")
    L.link(flow, "FindOrder", "FindProduct", "array.count($activity[FindOrder].output.matches) > 0")
    L.select(flow, "FindCustomer", "$activity[ReferenceData].output.customers", items["customers"],
             "$loop[c].customerId == $activity[FindOrder].output.matches[0].customerId", iterator="c",
             desc="Customer of the order (BW for-each[customerId = current()/customerId])")
    L.link(flow, "FindProduct", "FindCustomer")


ORD, PRD, CUS = ("$activity[FindOrder].output.matches[0]", "$activity[FindProduct].output.matches[0]",
                 "$activity[FindCustomer].output.matches[0]")

# ---------------------------------------------------------------- GET /api/orders/{orderId}
order_with_joins(F, "$flow.pathParams.orderId")
L.response(F, "ConfigureHTTPResponse", 200, "LookupOrderBody", L.op(F)["ok"], dict(
    **{f: f"={ORD}.{f}" for f in ("orderId", "customerId", "sku", "purchaseDate", "channel", "storeId")},
    **{f"product.{f}": f"={PRD}.{f}" for f in ("sku", "name", "brand", "category", "price", "description")},
    **{f"customer.{f}": f"={CUS}.{f}" for f in ("customerId", "loyaltyTier", "preferredStoreId")}))
L.link(F, "FindCustomer", "ConfigureHTTPResponse")

# ---------------------------------------------------------------- GET /api/orders/returns/eligibility
order_with_joins(E, "$flow.queryParams.orderId")
diff = f'datetime.diff(datetime.parse({ORD}.purchaseDate, "UTC"), datetime.parse("{today}", "UTC"), "days")'
L.compute(E, "ReturnWindow", {
    # abs(...): Flogo has no abs(); diff(start, end) = end - start, so flip the sign when negative
    "ageDays": ("integer", f"={diff} < 0 ? coerce.toInt(0 - {diff}) : coerce.toInt({diff})"),
    "returnWindowDays": ("integer", f"={PRD}.attributes.returnWindowDays"),
}, desc=f"BW xsl:variables ageDays (days from purchase to {today}) and returnWindowDays")
L.link(E, "FindCustomer", "ReturnWindow")
AGE, WIN = "$activity[ReturnWindow].output.ageDays", "$activity[ReturnWindow].output.returnWindowDays"
L.response(E, "ConfigureHTTPResponse", 200, "ReturnEligibilityBody", L.op(E)["ok"], {
    "orderId": f"={ORD}.orderId", "sku": f"={ORD}.sku", "productName": f"={PRD}.name",
    "purchaseDate": f"={ORD}.purchaseDate", "ageDays": f"={AGE}", "returnWindowDays": f"={WIN}",
    "eligible": f"={AGE} <= {WIN}", "loyaltyTier": f"={CUS}.loyaltyTier",
    "reason": (f'={AGE} <= {WIN} ? string.concat("The item is within the ", coerce.toString({WIN}), " day return window.")'
               f' : string.concat("The item is ", coerce.toString({AGE} - {WIN}), " days past the ", coerce.toString({WIN}),'
               f' " day return window.")'),
})
L.link(E, "ReturnWindow", "ConfigureHTTPResponse")

# ---------------------------------------------------------------- POST /api/orders/return-authorizations
L.response(P, "ConfigureHTTPResponse", 200, "CreateReturnBody", L.op(P)["ok"], {
    "approvalRequired": True,
    "tool": "create_return_authorization",
    "arguments.orderId": "=$flow.body.orderId",
    "message": "This operation changes retail state and must be approved through the agent approval flow.",
})

sys.exit(L.finish())
