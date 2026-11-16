"""Business logic of Retail.Promotions.API rebuilt in Flogo (worked example for the skill).

BW6 source (decoded by analyze_bw6.py):
  GET  /api/promotions?customerId&category
       ParseCustomerJSON (JsonParser over an embedded customer list) -> Flogo: typed mapper array
       -> reply: for-each customer[customerId = $param] -> {customerId, category, customerTier,
                 promotions:[Spring Trail 10%], message}           (no match -> Java 500)
  POST /api/promotions/applications
       -> reply: {approvalRequired:true, tool:'apply_promotion', arguments:{customerId?, promotionId, sku?}, message}

Usage: python promotions_logic.py <work>/plan.json
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from flogo_logic_lib import Logic, bw_string_literal  # noqa: E402

L = Logic(sys.argv[1])

# ---------------------------------------------------------------- GET /api/promotions
F = L.flow("find_promotions")
customer = {"type": "object", "properties": {
    "customerId": {"type": "string"}, "name": {"type": "string"}, "loyaltyTier": {"type": "string"},
    "preferredStoreId": {"type": "string"}, "preferences": {"type": "array", "items": {"type": "string"}}}}
customers = json.loads(bw_string_literal(L.bw_activity(F, "ParseCustomerJSON")["inputXslt"][0]))

L.unlink_placeholder(F)
L.log(F, '=string.concat("find_promotions queryParams=", coerce.toString($flow.queryParams))')
L.static_data(F, "CustomerData", "customers", customers, customer,
              "Embedded customer list (BW ParseCustomerJSON literal)")
L.require_params(F, after="Log_API", next_step="CustomerData")
L.select(F, "FindCustomer", "$activity[CustomerData].output.customers", customer,
         "$loop[c].customerId == $flow.queryParams.customerId", iterator="c")
L.link(F, "CustomerData", "FindCustomer")
L.error(F, "NotFound", 404, "customer_not_found",
        '=string.concat("No customer found with id ", $flow.queryParams.customerId)')
L.link(F, "FindCustomer", "NotFound", "array.count($activity[FindCustomer].output.matches) == 0")
L.response(F, "ConfigureHTTPResponse", 200, "FindPromotionsBody", L.op(F)["ok"], {
    "customerId": "=$activity[FindCustomer].output.matches[0].customerId",
    "category": "=$flow.queryParams.category",
    "customerTier": "=$activity[FindCustomer].output.matches[0].loyaltyTier",
    "promotions": [{"id": "promo-spring-trail", "name": "Spring Trail Promotion", "discountPercent": 10,
                    "expiresOn": "2026-05-31", "exclusions": ["Electronics"]}],
    "message": "A loyalty promotion may apply to this category.",
})
L.link(F, "FindCustomer", "ConfigureHTTPResponse", "array.count($activity[FindCustomer].output.matches) > 0")

# ---------------------------------------------------------------- POST /api/promotions/applications
P = L.flow("apply_promotion")
L.response(P, "ConfigureHTTPResponse", 200, "ApplyPromotionBody", L.op(P)["ok"], {
    "approvalRequired": True,
    "tool": "apply_promotion",
    "arguments.customerId": "=$flow.body.customerId",
    "arguments.promotionId": "promo-spring-trail",
    "arguments.sku": "=$flow.body.sku",
    "message": "This operation changes retail state and must be approved through the agent approval flow.",
})

sys.exit(L.finish())
