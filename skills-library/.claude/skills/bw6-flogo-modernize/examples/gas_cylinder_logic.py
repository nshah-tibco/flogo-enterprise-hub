#!/usr/bin/env python3
"""Business logic of an industrial-gas cylinder operations API rebuilt in Flogo (worked example: hardcoded XML data,
path-parameter lookup, two-field search, a top-level JSON array reply, an update-style reply).

BW6 source (decoded by analyze_bw6.py):
  GET  /api/v1/cylinders/{id}            ParseXml over an XML literal of 4 cylinders
                                         -> reply for-each Cylinder[cylinderId = $id]: all fields, certExpiryDate = date(..)
  POST /api/v1/cylinders/{id}/dispatch   ParseXml -> Mapper Cylinder[cylinderId = $id]
                                         -> reply {cylinderId, status: "In Transit", destination (body), updatedAt: current-date()}
  GET  /api/v1/cylinders/search?gasType&location
                                         ParseXml -> Mapper1 Cylinder[gasType = $gasType and location = $location]
                                         -> reply CylinderArray (top-level JSON array of cylinders)

Flogo design: the XML literal becomes a typed Mapper of records (Logic.bw_xml), lookups are filtered @foreach selects,
the search reply is a top-level array (Logic.response_array). Unknown ids answer the 404 {code, message} the API
declares (ErrorResponse); a dispatch without "destination" (required in the API) answers 400.

Usage: python gas_cylinder_logic.py <work>/plan.json
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from flogo_logic_lib import Logic  # noqa: E402

L = Logic(sys.argv[1] if len(sys.argv) > 1 else None)   # <work>/plan.json from scaffold_flogo_app.py
GET, DSP, SRC = L.flow("getCylinderStatus"), L.flow("dispatchCylinder"), L.flow("searchGasStock")
cylinder = json.loads(json.dumps(L.op(GET)["ok"]))          # the API's Cylinder schema (types the XML values)
cylinder.pop("required", None)
FIELDS = list(cylinder["properties"])
count = lambda act: f"array.count($activity[{act}].output.matches)"


def data_and_select(flow, xml_activity, predicate, iterator):
    """Typed copy of the BW XML literal used by THIS operation, then the filtered lookup."""
    rows = L.bw_xml(flow, xml_activity, cylinder)
    L.static_data(flow, "CylinderData", "cylinders", rows, cylinder, f"Embedded cylinder list (BW {xml_activity} literal)")
    L.select(flow, "FindCylinder", "$activity[CylinderData].output.cylinders", cylinder, predicate, iterator=iterator)
    L.link(flow, "CylinderData", "FindCylinder")


# ---------------------------------------------------------------- GET /api/v1/cylinders/{id}
L.unlink_placeholder(GET)
L.log(GET, '=string.concat("getCylinderStatus id=", coerce.toString($flow.pathParams.id))')
data_and_select(GET, "ParseXml2", "$loop[c].cylinderId == $flow.pathParams.id", "c")
L.require_params(GET, after="Log_API", next_step="CylinderData")
L.error(GET, "NotFound", 404, "cylinder_not_found",
        '=string.concat("No cylinder found with id ", $flow.pathParams.id)')
L.link(GET, "FindCylinder", "NotFound", f"{count('FindCylinder')} == 0")
L.response(GET, "ConfigureHTTPResponse", 200, "CylinderBody", L.op(GET)["ok"],
           {f: f"=$activity[FindCylinder].output.matches[0].{f}" for f in FIELDS})
L.link(GET, "FindCylinder", "ConfigureHTTPResponse", f"{count('FindCylinder')} > 0")

# ---------------------------------------------------------------- POST /api/v1/cylinders/{id}/dispatch
L.unlink_placeholder(DSP)
L.log(DSP, '=string.concat("dispatchCylinder id=", coerce.toString($flow.pathParams.id))')
data_and_select(DSP, "Copy_1_ParseXml", "$loop[c].cylinderId == $flow.pathParams.id", "c")
L.require_params(DSP, after="Log_API", next_step="CylinderData", body_fields=("destination",))
L.error(DSP, "NotFound", 404, "cylinder_not_found",
        '=string.concat("No cylinder found with id ", $flow.pathParams.id)')
L.link(DSP, "FindCylinder", "NotFound", f"{count('FindCylinder')} == 0")
L.response(DSP, "ConfigureHTTPResponse", 200, "DispatchBody", L.op(DSP)["ok"], {
    "cylinderId": "=$activity[FindCylinder].output.matches[0].cylinderId",
    "status": "In Transit",                                  # BW literal (note: not the enum value "In-Transit")
    "destination": "=$flow.body.destination",
    "updatedAt": "=datetime.currentDate()",                 # BW current-date()
})
L.link(DSP, "FindCylinder", "ConfigureHTTPResponse", f"{count('FindCylinder')} > 0")

# ---------------------------------------------------------------- GET /api/v1/cylinders/search
L.unlink_placeholder(SRC)
L.log(SRC, '=string.concat("searchGasStock ", coerce.toString($flow.queryParams))')
data_and_select(SRC, "ParseXml", "$loop[c].gasType == $flow.queryParams.gasType && "
                                 "$loop[c].location == $flow.queryParams.location", "c")
L.link(SRC, "Log_API", "CylinderData")
L.response_array(SRC, "ConfigureHTTPResponse", 200, "CylinderList", L.op(SRC)["ok"],
                 "$activity[FindCylinder].output.matches")      # select() already yields the Cylinder shape
L.link(SRC, "FindCylinder", "ConfigureHTTPResponse")

sys.exit(L.finish())
