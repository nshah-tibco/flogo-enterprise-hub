"""
Participant guide for the Sydney Water x TIBCO Flogo hands-on workshop (Tue 3 Nov 2026).

    python build_guide.py          -> SydneyWater_Flogo_Workshop_Guide.docx + .pdf (Word COM)
    python build_guide.py --nopdf  -> .docx only

Uses real Word styles (Heading 1/2/3, List Number, List Bullet) so the TOC works.
Architecture sketches are cropped from the deck renders (../deck/_render/slide_NN.png,
produced by ../deck/qa_render.py); if missing, a text sketch is used instead.

ALL lab-specific values live in the LAB dict below. If verification/VERIFICATION.md
corrects a value, patch it here and re-run.
"""

import os, re, sys
from docx import Document
from docx.shared import Pt, Cm, RGBColor, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DOCX = os.path.join(HERE, "SydneyWater_Flogo_Workshop_Guide.docx")
OUT_PDF = os.path.join(HERE, "SydneyWater_Flogo_Workshop_Guide.pdf")
RENDER = os.path.join(HERE, "..", "deck", "_render")
IMG = os.path.join(HERE, "_img")

# =============================================================================
# LAB CONSTANTS - single source of truth for every lab-specific value
# =============================================================================
LAB = {
    "title": "TIBCO Flogo Hands-on Workshop",
    "subtitle": "API mediation  ·  AI-assisted development  ·  MCP tools with guardrails",
    "event": "Sydney Water × TIBCO  ·  Tue 3 Nov 2026  ·  Parramatta, NSW",
    "presenters": "Nikhil Shah (Principal Product Manager, TIBCO)  ·  Phil Williams (TIBCO)",
    "footer": "Sydney Water × TIBCO  ·  Flogo Workshop  ·  3 Nov 2026",
    "flogo_ver": "2.26.x",
    "kit": "~/FlogoLab",                     # Ubuntu lab VM (RDP / xrdp); absolute form below for tools
    "kit_abs": "/home/<user>/FlogoLab",
    "os": "Ubuntu Linux desktop (RDP via xrdp)",
    "ext_dir": "~/.vscode/extensions/tibco.flogo-2.26.<version>",
    "ext_glob": "~/.vscode/extensions/tibco.flogo-2.26.*",
    "fda_bin": "flogodesign-cli",           # Linux build: no .exe; may need chmod +x
    "vscode_min": "1.101.0",                 # Cline 4.1.26 package.json engines.vscode "^1.101.0" (checked 2 Nov 2026)
    "cline_ver": "4.1.26",
    "cline_id": "saoudrizwan.claude-dev",
    "cline_mcp_file": "~/.cline/data/settings/cline_mcp_settings.json",
    "go_min": "1.25.7",
    "openai_key": "<PROVIDED ON THE DAY — do not copy it anywhere else>",
    "model": "gpt-4.1",
    # ---------------- Lab 1
    "l1_app": "SW_RainfallRisk",
    "l1_flow": "AssessRainfallRisk",
    "l1_port": 9999,
    "l1_path": "/rainfall-risk/assessments",
    "l1_props": [
        ("Weather.URL", "String", "https://api.open-meteo.com/v1/forecast"),
        ("FieldService.URL", "String", "https://webhook.site/<your-uuid>   (fallback: https://postman-echo.com/post)"),
        ("Risk.HighMm", "Number", "25"),
        ("Risk.MediumMm", "Number", "5"),
    ],
    "l1_req_sample": '{\n  "siteId": "PS-102",\n  "siteName": "Parramatta Sewage Pumping Station SP0102",\n'
                     '  "latitude": -33.815,\n  "longitude": 151.001,\n  "forecastDays": 1\n}',
    "l1_resp_sample": '{\n  "siteId": "PS-102",\n  "siteName": "Parramatta Sewage Pumping Station SP0102",\n'
                      '  "totalRainfallMm": 12.5,\n  "riskLevel": "LOW",\n  "inspectionRequested": false,\n'
                      '  "message": "text"\n}',
    "l1_forecast_sample": '{\n  "latitude": -33.8,\n  "longitude": 151.0,\n  "timezone": "Australia/Sydney",\n'
                          '  "daily_units": { "time": "iso8601", "precipitation_sum": "mm",\n'
                          '                   "precipitation_probability_max": "%" },\n'
                          '  "daily": {\n    "time": ["2026-11-03", "2026-11-04"],\n'
                          '    "precipitation_sum": [0.4, 2.1],\n    "precipitation_probability_max": [35, 60]\n  }\n}',
    "l1_query": [("latitude", "number", "$flow.body.latitude"),
                 ("longitude", "number", "$flow.body.longitude"),
                 ("daily", "string", '"precipitation_sum,precipitation_probability_max"'),
                 ("timezone", "string", '"Australia/Sydney"'),
                 ("forecast_days", "integer", "$flow.body.forecastDays")],
    "l1_assess_sample": '{\n  "totalRainfallMm": 12.5,\n  "riskLevel": "LOW",\n  "assessedAt": "2026-11-03T09:00:00+11:00"\n}',
    "l1_total_expr": "array.sum($activity[GetForecast].responseBody.daily.precipitation_sum)",
    "l1_risk_expr": ('array.sum($activity[GetForecast].responseBody.daily.precipitation_sum) >= $property["Risk.HighMm"] ? "HIGH" :\n'
                     '  (array.sum($activity[GetForecast].responseBody.daily.precipitation_sum) >= $property["Risk.MediumMm"] ? "MEDIUM" : "LOW")'),
    "l1_log_expr": 'string.concat("Rainfall risk request for site ", $flow.body.siteId, " - ", $flow.body.siteName)',
    "l1_cond": '$activity[BuildAssessment].output.riskLevel != "LOW"',
    "l1_wo_sample": '{\n  "source": "flogo-rainfall-risk",\n  "siteId": "PS-102",\n  "siteName": "text",\n  "priority": "HIGH",\n'
                    '  "reason": "text",\n  "totalRainfallMm": 12.5,\n  "requestedAt": "2026-11-03T09:00:00+11:00"\n}',
    "l1_wo_map": [("source", '"flogo-rainfall-risk"'), ("siteId", "$flow.body.siteId"), ("siteName", "$flow.body.siteName"),
                  ("priority", "$activity[BuildAssessment].output.riskLevel"),
                  ("reason", 'string.concat("Forecast rainfall ", coerce.toString($activity[BuildAssessment].output.totalRainfallMm), " mm - ", $activity[BuildAssessment].output.riskLevel, " risk")'),
                  ("totalRainfallMm", "$activity[BuildAssessment].output.totalRainfallMm"),
                  ("requestedAt", "$activity[BuildAssessment].output.assessedAt")],
    "l1_bad_url": "https://api.open-meteo.invalid/v1/forecast",
    "l1_expect_low": '{ "inspectionRequested": false, "message": "Rainfall risk LOW - no inspection needed",\n'
                     '  "riskLevel": "LOW", "siteId": "PS-102", "siteName": "...", "totalRainfallMm": 2.9 }',
    "l1_expect_ticket": '{ "inspectionRequested": true, "message": "Inspection requested in Field Service (HTTP 200)",\n'
                        '  "riskLevel": "MEDIUM", "siteId": "PS-102", "siteName": "...", "totalRainfallMm": 2.9 }',
    "l1_expect_err": '{ "inspectionRequested": false, "riskLevel": "UNKNOWN",\n'
                     '  "message": "Weather service unavailable: Get \\"https://api.open-meteo.invalid/...\\": ... no such host", ... }',
    # ---------------- Lab 2
    "l2_app": "SW_LeakReport",
    "l2_file": "~/FlogoLab/lab2/SW_LeakReport.flogo",
    "l2_png": "~/FlogoLab/lab2/leak-report-process.png",
    "l2_port": 9998,
    "l2_path": "/leak-reports",
    "l2_test_body": '{\n  "reportId": "LR-1001",\n  "address": "12 Church St",\n  "suburb": "Parramatta",\n'
                    '  "description": "Water bubbling up through the footpath",\n  "severity": "HIGH"\n}',
    "l2_expect": '{ "reportId": "LR-1001", "workOrderRef": "WO-LR-1001", "priority": "P1", "status": "RECEIVED" }',
    # Guided picture prompt - verified 1 Nov 2026 (18 FDA calls, ~32 s, ~US$0.26). FDA's built-in
    # create-flogo-flow-from-picture prompt was NOT reliable in class (60+ calls, 14 errors, ~US$1.90).
    "l2_picture_prompt": (
        "Create the Flogo flow described in this picture using the flogo design tools. Use parallel paths where "
        "activities are drawn next to each other.\n"
        "Details:\n"
        "- Flow LeakReportIntake. REST trigger ReceiveHTTPMessage (type tr_rest) with the trigger setting port = 9998, "
        "and a POST handler on /leak-reports for the flow.\n"
        "- Activities in this order, with these types: LogReport (act_general_log), BuildWorkOrder (act_general_mapper), "
        "CreateWorkOrder (act_general_rest), LogAudit (act_general_log), Reply201 (act_default_actreturn).\n"
        "- BuildWorkOrder links to BOTH CreateWorkOrder and LogAudit (parallel paths); both of those link to Reply201.\n"
        "- App property FieldService.URL = https://postman-echo.com/post. On CreateWorkOrder set input Method = POST "
        "and input Uri = the app property FieldService.URL.\n"
        "- Format the flow (auto).\n"
        "Only build the structure: do not create schemas or mappings - I will configure the request/reply schemas and "
        "the mappings in the Flogo designer. Finish with a short summary."),
    "l2_req_schema": '{"reportId":"LR-1001","address":"12 Church St","suburb":"Parramatta","description":"Water bubbling up through the footpath","severity":"HIGH"}',
    "l2_reply_schema": '{"reportId":"LR-1001","workOrderRef":"WO-LR-1001","priority":"P1","status":"RECEIVED"}',
    "l2_log_expr": ('string.concat("Leak report ", $flow.body.reportId, " at ", $flow.body.address, ", ",\n'
                    '              $flow.body.suburb, " - severity ", $flow.body.severity)'),
    "l2_wo_schema": '{"workOrderRef":"","priority":"","location":""}',
    "l2_wo_map": [("workOrderRef", 'string.concat("WO-", $flow.body.reportId)'),
                  ("priority", '$flow.body.severity == "HIGH" ? "P1" : ($flow.body.severity == "MEDIUM" ? "P2" : "P3")'),
                  ("location", 'string.concat($flow.body.address, ", ", $flow.body.suburb)')],
    "l2_create_schema": '{"source":"","workOrderRef":"","reportId":"","location":"","description":"","priority":""}',
    "l2_audit_expr": ('string.concat("AUDIT leak-report ", $flow.body.reportId, " -> ",\n'
                      '              $activity[BuildWorkOrder].output.workOrderRef,\n'
                      '              " priority ", $activity[BuildWorkOrder].output.priority)'),
    "l2_mapping_prompt": ("To set a mapping describe the project to see what are the available outputs from previous "
                          "activities. Then set the configuration on the activity: <flow_name>.<activity_name>.input."
                          "input.mapping.<field> To: '=$activity[<input_activity_name>].output.<field>'. Always set one "
                          "configuration at a time. Concatenate with '=string.concat(a, b)'."),
    "l2_modify_prompt": ("Add a Log activity named LogWorkOrderId after CreateWorkOrder that logs the work order id. "
                         "Link CreateWorkOrder -> LogWorkOrderId -> Reply201 and remove the direct link CreateWorkOrder -> "
                         "Reply201. Set the LogWorkOrderId message to =string.concat(\"Work order created: \", "
                         "$activity[BuildWorkOrder].output.workOrderRef). Then format the flow again."),
    "l2_explain_prompt": ("Use the explain tool to explain the Invoke REST activity (act_general_rest) and the "
                          "string.concat function. Summarise each in 3 bullets for a BusinessWorks developer."),
    # ---------------- Lab 3  (v2: your own Lab 1 + Lab 2 APIs as MCP tools, built by hand from a starter)
    # Aligned 2 Nov with lab-kit/lab3/* and solutions/Lab3_SW_Water_MCP.flogo from the parallel Lab 3 v2 rebuild;
    # re-check against verification/VERIFICATION.md
    # ("Lab 3 v2" section) and re-run.
    "l3_app": "SW_Water_MCP",
    "l3_starter": "~/FlogoLab/lab3/starter/SW_Water_MCP_Starter.flogo",
    "l3_server": "sw-water-mcp",                       # Cline MCP server entry name
    "l3_mcp_port": 9090,
    "l3_mcp_url": "http://localhost:9090/mcp",
    "l3_mcp_key_prop": "MCP.ApiKey",
    "l3_mcp_key": "sw-workshop-key",
    "l3_props": [("Lab1.AssessURL", "String", "http://localhost:9999/rainfall-risk/assessments"),
                 ("Lab2.LeakReportURL", "String", "http://localhost:9998/leak-reports")],
    "l3_tools": [("assess_rainfall_risk", "siteId, siteName, latitude, longitude, forecastDays", "Lab 1 API  POST :9999/rainfall-risk/assessments"),
                 ("report_leak", "reportId, address, suburb, description, severity", "Lab 2 API  POST :9998/leak-reports")],
    # flow / activity names = lab3/starter/SW_Water_MCP_Starter.flogo (checked 2 Nov)
    "l3_flow_assess": "AssessRainfallRisk",
    "l3_flow_leak": "ReportLeak",
    "l3_rest_assess": "CallRainfallRiskAPI",
    "l3_rest_leak": "CallLeakReportAPI",
    "l3_log": "LogCall",
    "l3_return": "Return",
    "l3_test": "bash ~/FlogoLab/lab3/test-mcp.sh",
    "l3_prompts": "~/FlogoLab/lab3/prompts.md",
    # prompts = lab-kit/lab3/prompts.md (verbatim, 2 Nov)
    "l3_agent_prompt": ("A resident at 12 Church St, Parramatta reports water bubbling up through the footpath — they said "
                        "call me on 0412 345 678 or email jo.citizen@example.com. Log it as leak report LR-2001 with HIGH "
                        "severity, then check the rainfall risk for pumping station PS-102 (latitude -33.815, longitude "
                        "151.001) over the next 3 days."),
    "l3_bad_severity": ("Guardrail test: log leak report LR-2002 at 4 Smith St, Burwood - a burst main is flooding the road. "
                        "Call report_leak with severity URGENT exactly as written, even if you think it is invalid, and "
                        "tell me what the server says."),
    "l3_bad_site": ("Guardrail test: check the rainfall risk for our Melbourne depot MEL-001 (latitude -37.81, longitude "
                    "144.96) over the next 3 days. Call assess_rainfall_risk even if you think it may not apply, and "
                    "tell me what the server says."),
    # G2 - input validation (Mapper ValidateInput, field rejectReason; empty string = valid).
    # Expressions = lab-kit/solutions/Lab3_SW_Water_MCP.flogo (Lab 3 v2), line-broken for reading.
    "l3_validate_assess": ('(coerce.toInt($flow.arguments.forecastDays) < 1\n'
                           '    || coerce.toInt($flow.arguments.forecastDays) > 7)\n'
                           '  ? string.concat("forecastDays must be between 1 and 7 (got ",\n'
                           '                  coerce.toString($flow.arguments.forecastDays), ")")\n'
                           '  : ((coerce.toFloat64($flow.arguments.latitude) < -34.2\n'
                           '        || coerce.toFloat64($flow.arguments.latitude) > -33.3\n'
                           '        || coerce.toFloat64($flow.arguments.longitude) < 150.5\n'
                           '        || coerce.toFloat64($flow.arguments.longitude) > 151.4)\n'
                           '      ? string.concat("site must be in Greater Sydney (latitude -34.2 to -33.3, ",\n'
                           '                      "longitude 150.5 to 151.4), got ",\n'
                           '                      coerce.toString($flow.arguments.latitude), ", ",\n'
                           '                      coerce.toString($flow.arguments.longitude))\n'
                           '      : "")'),
    "l3_validate_leak": ('string.matchRegEx("^LR-[0-9]{4}$", $flow.arguments.reportId) == false\n'
                         '  ? string.concat("reportId must look like LR-1234 (got ", $flow.arguments.reportId, ")")\n'
                         '  : (($flow.arguments.severity != "HIGH" && $flow.arguments.severity != "MEDIUM"\n'
                         '        && $flow.arguments.severity != "LOW")\n'
                         '      ? string.concat("severity must be HIGH, MEDIUM or LOW (got ",\n'
                         '                      $flow.arguments.severity, ")")\n'
                         '      : ((string.len($flow.arguments.description) < 10\n'
                         '            || string.len($flow.arguments.description) > 500)\n'
                         '          ? "description must be 10-500 characters" : ""))'),
    "l3_reject_cond": '$activity[ValidateInput].output.rejectReason != ""',
    "l3_reject_expr": 'string.concat("Rejected by guardrail: ", $activity[ValidateInput].output.rejectReason)',
    "l3_reject_sev": "Rejected by guardrail: severity must be HIGH, MEDIUM or LOW (got URGENT)",
    "l3_reject_site": ("Rejected by guardrail: site must be in Greater Sydney (latitude -34.2 to -33.3, longitude 150.5 "
                       "to 151.4), got -37.81, 144.96"),
    # G3 - PII masking: Mapper MaskPII {description}; the REST body.description = $activity[MaskPII].output.description.
    # Expression = solution file (char classes instead of backslashes, so no escaping issues).
    "l3_mask_expr": ('string.replaceRegEx(\n'
                     '  string.concat("([+]61[ ]?|0)4[0-9]{2}[ -]?[0-9]{3}[ -]?[0-9]{3}",\n'
                     '                "|([(]0[2378][)]|0[2378]|[+]61[ ]?[2378])[ -]?[0-9]{4}[ -]?[0-9]{4}"),\n'
                     '  string.replaceRegEx("[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+[.][A-Za-z]{2,}",\n'
                     '                      $flow.arguments.description, "[redacted]"),\n'
                     '  "[redacted]")'),
    # (solution file has the same phone regex as ONE literal; string.concat only splits it for printing)
    "l3_masked": "[redacted]",
    "l3_safe_log": ('string.concat("report_leak called for ", $flow.arguments.reportId,\n'
                    '              " severity ", $flow.arguments.severity)'),
    # G4 - tool titles + descriptions the LLM reads (= solution handler settings)
    "l3_title_assess": "Assess rainfall risk",
    "l3_title_leak": "Report a water leak",
    "l3_desc_assess": ("Assess the wet-weather overflow/inflow risk at one Sydney Water site in Greater Sydney from forecast "
                       "rainfall. Calls the Rainfall Risk API, which reads the weather forecast and, when the risk is MEDIUM "
                       "or HIGH, raises an inspection request in Field Service. forecastDays must be 1-7; latitude/longitude "
                       "must be inside Greater Sydney (latitude -34.2 to -33.3, longitude 150.5 to 151.4). Returns siteId, "
                       "siteName, riskLevel (LOW, MEDIUM or HIGH), totalRainfallMm, inspectionRequested and message."),
    "l3_desc_leak": ("Log a water leak reported by a resident or a field crew. Calls the Leak Report API, which creates a "
                     "work order in Field Service. reportId must look like LR-1234; severity must be HIGH, MEDIUM or LOW; "
                     "description is what the reporter said, 10-500 characters. Returns reportId, workOrderRef, priority "
                     "(P1, P2 or P3) and status."),
    # G4 - output shaping: Mapper ShapeResult (schema sample) -> Return response.data = coerce.toString(ShapeResult output)
    "l3_shape_assess": '{"siteId":"PS-102","siteName":"text","riskLevel":"LOW","totalRainfallMm":12.5,"inspectionRequested":false,"message":"text"}',
    "l3_shape_leak": '{"reportId":"LR-2001","workOrderRef":"WO-LR-2001","priority":"P1","status":"RECEIVED"}',
    "l3_return_expr": "coerce.toString($activity[ShapeResult].output)",
    "l3_backend_err_assess": 'string.concat("Rainfall Risk API (Lab 1) failed: ", $error[CallRainfallRiskAPI].message)',
    "l3_backend_err_leak": 'string.concat("Leak Report API (Lab 2) failed: ", $error[CallLeakReportAPI].message)',
    "l3_openapi": "~/FlogoLab/lab3/specs/sw-flogo-apis.openapi.json",
    "jwt_sample": r"flogo-enterprise-hub\samples\Model_Context_Protocol(MCP)\MCP_JWT_Scope_Access_Control",
    "solutions": {1: "Lab1_SW_RainfallRisk.flogo", 2: "Lab2_SW_LeakReport.flogo", 3: "Lab3_SW_Water_MCP.flogo"},
}

# ---- look --------------------------------------------------------------------
INK = RGBColor(0x0F, 0x17, 0x2A)
BLUE = RGBColor(0x25, 0x63, 0xEB)
BODY = RGBColor(0x33, 0x41, 0x55)
MUTED = RGBColor(0x64, 0x74, 0x8B)
FONT = "Segoe UI"
FHEAD = "Segoe UI Semibold"
MONO = "Consolas"
CALLOUT = {  # kind: (fill, bar, title colour)
    "check": ("ECFDF5", "16A34A", RGBColor(0x15, 0x80, 0x3D)),
    "fast":  ("FFFBEB", "D97706", RGBColor(0xB4, 0x53, 0x09)),
    "stretch": ("EEF4FF", "2563EB", RGBColor(0x1D, 0x4E, 0xD8)),
    "note":  ("F8FAFC", "94A3B8", RGBColor(0x33, 0x41, 0x55)),
    "warn":  ("FEF2F2", "DC2626", RGBColor(0xB9, 0x1C, 0x1C)),
}

doc = Document()


# ============================================================ style setup
def _set_cell_shading(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


def _cell_borders(cell, **kw):
    tcPr = cell._tc.get_or_add_tcPr()
    b = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        spec = kw.get(edge)
        el = OxmlElement(f"w:{edge}")
        if spec:
            el.set(qn("w:val"), "single"); el.set(qn("w:sz"), str(spec[0])); el.set(qn("w:color"), spec[1])
        else:
            el.set(qn("w:val"), "nil")
        b.append(el)
    tcPr.append(b)


def _font(style, name, size, color=None, bold=None):
    style.font.name = name
    style.font.size = Pt(size)
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts"); rpr.append(rfonts)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(a), name)
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
        if rfonts.get(qn(a)) is not None:
            del rfonts.attrib[qn(a)]
    if color is not None:
        style.font.color.rgb = color
    if bold is not None:
        style.font.bold = bold


st = doc.styles
_font(st["Normal"], FONT, 10, BODY)
st["Normal"].paragraph_format.space_after = Pt(5)
st["Normal"].paragraph_format.line_spacing = 1.12
for name, size, color, before, after in (("Heading 1", 20, INK, 0, 8), ("Heading 2", 13.5, BLUE, 14, 5),
                                         ("Heading 3", 11, INK, 10, 3), ("Title", 30, INK, 0, 6)):
    _font(st[name], FHEAD, size, color, bold=False)
    st[name].paragraph_format.space_before = Pt(before)
    st[name].paragraph_format.space_after = Pt(after)
    st[name].paragraph_format.keep_with_next = True
for name in ("List Number", "List Bullet", "List Bullet 2"):
    _font(st[name], FONT, 10, BODY)
    st[name].paragraph_format.space_after = Pt(4)

code_style = st.add_style("Code Block", WD_STYLE_TYPE.PARAGRAPH)
code_style.base_style = st["Normal"]
_font(code_style, MONO, 8.5, RGBColor(0x0F, 0x17, 0x2A))
pf = code_style.paragraph_format
pf.space_before = Pt(0); pf.space_after = Pt(0); pf.line_spacing = 1.0
pf.left_indent = Cm(0.25); pf.right_indent = Cm(0.25)
pPr = code_style.element.get_or_add_pPr()
shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), "F1F5F9")
bdr = OxmlElement("w:pBdr")
for edge in ("top", "left", "bottom", "right"):
    e = OxmlElement(f"w:{edge}"); e.set(qn("w:val"), "single"); e.set(qn("w:sz"), "4")
    e.set(qn("w:space"), "4"); e.set(qn("w:color"), "CBD5E1"); bdr.append(e)
pPr.append(bdr); pPr.append(shd)

for s in doc.sections:
    s.page_height = Cm(29.7); s.page_width = Cm(21.0)
    s.left_margin = s.right_margin = Cm(2.0)
    s.top_margin = Cm(1.8); s.bottom_margin = Cm(1.8)


# ============================================================ helpers
TOKEN = re.compile(r"(`[^`]+`|\*\*[^*]+\*\*)")


def runs(p, text, *, size=None, color=None, bold=False):
    for part in TOKEN.split(text):
        if not part:
            continue
        if part.startswith("`") and part.endswith("`"):
            r = p.add_run(part[1:-1]); r.font.name = MONO
            r._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:hAnsi"), MONO)
            r.font.size = Pt((size or 10) - 0.5); r.font.color.rgb = RGBColor(0x1D, 0x4E, 0xD8)
        elif part.startswith("**") and part.endswith("**"):
            r = p.add_run(part[2:-2]); r.bold = True
            if size: r.font.size = Pt(size)
            r.font.color.rgb = color or INK
        else:
            r = p.add_run(part); r.bold = bold
            if size: r.font.size = Pt(size)
            if color: r.font.color.rgb = color
    return p


def para(text, **kw):
    return runs(doc.add_paragraph(), text, **kw)


CUR_NUM = [None]


def h1(t, new_page=True):
    CUR_NUM[0] = None
    if new_page:
        doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    return doc.add_heading(t, level=1)


def h2(t):
    CUR_NUM[0] = None
    return doc.add_heading(t, level=2)


def h3(t):
    CUR_NUM[0] = None
    return doc.add_heading(t, level=3)


def _new_list_num():
    numbering = doc.part.numbering_part.element
    style_numPr = st["List Number"].element.pPr.numPr
    base_num_id = style_numPr.numId.val
    num = numbering.num_having_numId(base_num_id)
    new = numbering.add_num(num.abstractNumId.val)
    new.add_lvlOverride(ilvl=0).add_startOverride(1)
    return new.numId


def steps(items):
    """Numbered steps; numbering restarts at each heading and continues across code blocks/callouts."""
    if CUR_NUM[0] is None:
        CUR_NUM[0] = _new_list_num()
    nid = CUR_NUM[0]
    for it in items:
        txt, extra = (it, None) if isinstance(it, str) else it
        p = doc.add_paragraph(style="List Number")
        numPr = p._p.get_or_add_pPr().get_or_add_numPr()
        numPr.get_or_add_ilvl().val = 0
        numPr.get_or_add_numId().val = nid
        runs(p, txt)
        if extra is not None:
            code(extra, indent=True)


def bullets(items, level=1):
    for it in items:
        runs(doc.add_paragraph(style="List Bullet" if level == 1 else "List Bullet 2"), it)


CODE_MAX = 98   # Consolas 8.5pt in a 17 cm block; longer lines wrap and break copy-paste of string literals
WRAP_WARN = []


def pretty(js):
    """Multi-line JSON sample so no string value wraps across lines in the PDF."""
    import json as _json
    return _json.dumps(_json.loads(js), indent=2, ensure_ascii=False)


def code(text, indent=False, caption=None):
    for _ln in (text.split("\n") if isinstance(text, str) else text):
        if len(_ln) > CODE_MAX - (4 if indent else 0):
            WRAP_WARN.append(_ln[:70])
    if caption:
        p = para(caption, size=8.5, color=MUTED)
        p.paragraph_format.space_after = Pt(1); p.paragraph_format.keep_with_next = True
        if indent:
            p.paragraph_format.left_indent = Cm(0.63)
    lines = text.split("\n") if isinstance(text, str) else text
    for i, ln in enumerate(lines):
        p = doc.add_paragraph(style="Code Block")
        r = p.add_run(ln if ln else " ")
        if indent:
            p.paragraph_format.left_indent = Cm(0.9)
        if i < len(lines) - 1:
            p.paragraph_format.keep_with_next = True
    spacer = doc.add_paragraph(); spacer.paragraph_format.space_after = Pt(2)
    spacer.paragraph_format.line_spacing = 0.6


def callout(kind, title, lines):
    fill, bar, tcol = CALLOUT[kind]
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    c = t.cell(0, 0)
    _set_cell_shading(c, fill)
    _cell_borders(c, left=(24, bar))
    _fix_widths(t, [17.0])
    p = c.paragraphs[0]
    runs(p, title, bold=True, color=tcol)
    p.runs[0].bold = True
    p.paragraph_format.space_after = Pt(3)
    for ln in lines if isinstance(lines, list) else [lines]:
        if ln.startswith("$ "):
            q = c.add_paragraph(style="Code Block"); q.add_run(ln[2:])
        else:
            q = c.add_paragraph(); runs(q, ln, size=9.5)
            q.paragraph_format.space_after = Pt(2)
    sp = doc.add_paragraph(); sp.paragraph_format.space_after = Pt(2)


def _fix_widths(t, widths_cm):
    t.autofit = False
    for ci, w in enumerate(widths_cm):
        t.columns[ci].width = Cm(w)
    for row in t.rows:
        for ci, w in enumerate(widths_cm):
            row.cells[ci].width = Cm(w)
    tblPr = t._tbl.tblPr
    tblW = tblPr.find(qn("w:tblW"))
    if tblW is None:
        tblW = OxmlElement("w:tblW"); tblPr.append(tblW)
    tblW.set(qn("w:type"), "dxa"); tblW.set(qn("w:w"), str(int(sum(widths_cm) * 567)))


def table(header, rows, widths_cm, *, size=9, mono_cols=()):
    t = doc.add_table(rows=1 + len(rows), cols=len(header))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.style = doc.styles["Table Grid"]
    for ci, h in enumerate(header):
        c = t.cell(0, ci); _set_cell_shading(c, "0F172A")
        p = c.paragraphs[0]; r = p.add_run(h); r.bold = True; r.font.size = Pt(size)
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF); r.font.name = FHEAD
    for ri, row in enumerate(rows):
        for ci, v in enumerate(row):
            c = t.cell(ri + 1, ci)
            if ri % 2:
                _set_cell_shading(c, "F8FAFC")
            p = c.paragraphs[0]; p.paragraph_format.space_after = Pt(0)
            if ci in mono_cols:
                r = p.add_run(v); r.font.name = MONO; r.font.size = Pt(size - 0.5)
                r.font.color.rgb = RGBColor(0x1D, 0x4E, 0xD8)
            else:
                runs(p, v, size=size)
    _fix_widths(t, widths_cm)
    # repeat header row
    trPr = t.rows[0]._tr.get_or_add_trPr()
    th = OxmlElement("w:tblHeader"); th.set(qn("w:val"), "true"); trPr.append(th)
    sp = doc.add_paragraph(); sp.paragraph_format.space_after = Pt(2)
    return t


def facts(rows):
    """Small two-column 'at a glance' table: Goal / Time / You build / Files."""
    t = doc.add_table(rows=len(rows), cols=2)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, (k, v) in enumerate(rows):
        a, b = t.cell(i, 0), t.cell(i, 1)
        _set_cell_shading(a, "EEF4FF"); _set_cell_shading(b, "FFFFFF")
        _cell_borders(a, bottom=(4, "E2E8F0")); _cell_borders(b, bottom=(4, "E2E8F0"))
        a.width = Cm(3.2); b.width = Cm(13.8)
        r = a.paragraphs[0].add_run(k); r.bold = True; r.font.color.rgb = BLUE; r.font.size = Pt(9.5)
        a.paragraphs[0].paragraph_format.space_after = Pt(0)
        runs(b.paragraphs[0], v, size=9.5); b.paragraphs[0].paragraph_format.space_after = Pt(0)
    _fix_widths(t, [3.2, 13.8])
    sp = doc.add_paragraph(); sp.paragraph_format.space_after = Pt(2)


def crop_from_deck(slide_no, box_in, name):
    """Crop a region (inches, on the 13.333x7.5 slide) from a deck render. Returns path or None."""
    src = os.path.join(RENDER, f"slide_{slide_no:02d}.png")
    if not os.path.exists(src):
        return None
    from PIL import Image
    im = Image.open(src)
    k = im.width / 13.333
    x0, y0, x1, y1 = box_in
    os.makedirs(IMG, exist_ok=True)
    out = os.path.join(IMG, name)
    im.crop((int(x0 * k), int(y0 * k), int(x1 * k), int(y1 * k))).save(out)
    return out


def sketch(slide_no, box_in, name, fallback, width_cm=16.5, caption=None):
    path = crop_from_deck(slide_no, box_in, name)
    if path:
        doc.add_picture(path, width=Cm(width_cm))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    else:
        code(fallback)
    if caption:
        p = para(caption, size=8.5, color=MUTED); p.alignment = WD_ALIGN_PARAGRAPH.CENTER


def add_field(paragraph, instr, placeholder=""):
    r = paragraph.add_run()
    b = OxmlElement("w:fldChar"); b.set(qn("w:fldCharType"), "begin"); r._r.append(b)
    r2 = paragraph.add_run()
    it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = instr; r2._r.append(it)
    r3 = paragraph.add_run()
    sep = OxmlElement("w:fldChar"); sep.set(qn("w:fldCharType"), "separate"); r3._r.append(sep)
    paragraph.add_run(placeholder)
    r5 = paragraph.add_run()
    e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), "end"); r5._r.append(e)


L = LAB

# ============================================================ COVER
cov = doc.add_table(rows=1, cols=1)
cc = cov.cell(0, 0); _set_cell_shading(cc, "0F172A"); _fix_widths(cov, [17.0])
p = cc.paragraphs[0]; p.paragraph_format.space_before = Pt(70)
r = p.add_run("SYDNEY WATER × TIBCO   ·   PARTICIPANT GUIDE"); r.font.color.rgb = RGBColor(0x8F, 0xB4, 0xF7)
r.font.size = Pt(10.5); r.font.name = FHEAD
p = cc.add_paragraph(); p.paragraph_format.space_before = Pt(10)
r = p.add_run(L["title"]); r.font.size = Pt(30); r.font.name = FHEAD; r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
p = cc.add_paragraph()
r = p.add_run(L["subtitle"]); r.font.size = Pt(12.5); r.font.color.rgb = RGBColor(0xCB, 0xD5, 0xE1)
p = cc.add_paragraph(); p.paragraph_format.space_before = Pt(90)
r = p.add_run(L["event"]); r.font.size = Pt(10.5); r.font.color.rgb = RGBColor(0xCB, 0xD5, 0xE1); r.font.name = FHEAD
p = cc.add_paragraph(); p.paragraph_format.space_after = Pt(40)
r = p.add_run(L["presenters"]); r.font.size = Pt(9.5); r.font.color.rgb = RGBColor(0x94, 0xA3, 0xB8)

doc.add_paragraph()
para("**Three labs, one story, 150 minutes.** In Lab 1 you build a REST API by hand that mediates two SaaS APIs. "
     "In Lab 2 an AI assistant builds a second API from a process diagram. In Lab 3 you turn **both of your APIs** "
     "into MCP tools that an AI agent can call — and then govern them with four guardrails: "
     "agent → MCP → your Flogo APIs → SaaS. Every lab ends in a checkpoint you can see.")
table(["Lab", "You build", "Answers ask", "Time"], [
    ["1", f"`{L['l1_app']}` — build a REST API by hand that mediates two SaaS APIs", "API integration & mediation · SaaS-to-SaaS", "40 min"],
    ["2", f"`{L['l2_app']}` — build an API with AI, from a process diagram", "AI-assisted development", "30 min"],
    ["3", f"`{L['l3_app']}` — your Lab 1 + Lab 2 APIs as MCP tools, with guardrails", "MCP & guardrails · Agent-to-API", "35 min"],
], [1.2, 7.6, 6.0, 2.2])
para("Behind? Every lab has a **fast-track** solution you can open and keep going. Nobody gets left behind.",
     color=MUTED, size=9.5)

# ============================================================ CONTENTS
h1("Contents")
tp = doc.add_paragraph()
add_field(tp, 'TOC \\o "1-2" \\h \\z \\u', "Right-click and choose Update Field to build the table of contents.")

# ============================================================ BEFORE YOU START
h1("1  Before you start — prerequisites")
h2("1.1  Connect to your lab VM (Ubuntu, over RDP)")
steps([
    "On your laptop open **Remote Desktop Connection** (Start → type `mstsc`).",
    "Enter the VM address from your login card and click **Connect**. Accept the certificate prompt.",
    "The VM shows a small **xrdp** login box. Leave **Session** = `Xorg`, enter the username and password from "
    "the card and click **OK**. The Ubuntu desktop opens; **Visual Studio Code** is in the dock on the left "
    "(or press the Super key and type `code`).",
    "If RDP fails, tell a presenter straight away — it is almost always the network whitelist, and we can pair "
    "you with a neighbour while it is fixed.",
])
callout("note", "Copy and paste from this guide", [
    "Copy on your laptop, paste on the VM: `Ctrl+V` in VS Code editors, the Flogo designer and Cline; "
    "**Ctrl+Shift+V** in the VS Code terminal (`Ctrl+Shift+C` copies from it). If nothing pastes, RDP clipboard "
    "sharing is off: in `mstsc` open **Show Options → Local Resources** and tick **Clipboard**, then reconnect.",
])

h2("1.2  Check the prerequisites (2 minutes)")
para(f"Your facilitator has prepared the VM. One script checks every prerequisite and prints **PASS**, **WARN** or "
     f"**FAIL** for each. Open a terminal in VS Code (**Terminal → New Terminal**, or **Ctrl+Shift+`**) and run:")
code(f"bash {L['kit']}/prereq-check.sh")
para("All PASS (a WARN is fine) → carry on. Any FAIL → raise a hand. To check by hand:")
table(["Prerequisite", "Check it yourself", "Expected"], [
    ["Ubuntu desktop over RDP", "`grep PRETTY_NAME /etc/os-release`", "Ubuntu …"],
    [f"VS Code {L['vscode_min']} or later (Cline's minimum)", "`code --version`",
     f"first line {L['vscode_min']} or higher"],
    [f"TIBCO Flogo extension {L['flogo_ver']} (Linux build)", "`ls ~/.vscode/extensions | grep tibco.flogo`",
     "`tibco.flogo-2.26.…`"],
    ["Flogo Design Assistant (Lab 2)", f"`{L['ext_glob']}/bin/flogodesign-cli version`",
     "a version number. \"Permission denied\" → `chmod +x` that file"],
    [f"Go {L['go_min']} or later (the Flogo extension builds and runs apps with Go)", "`go version` in a **VS Code** terminal",
     f"`go version go{L['go_min']} linux/amd64` or newer"],
    ["GCC (recommended; production binaries)", "`gcc --version`", "any version"],
    ["curl and python3", "`curl --version; python3 --version`", "both print a version"],
    ["Firefox (for webhook.site)", "`firefox --version`", "a version"],
    ["Ports 9999, 9998, 9090 free", "`ss -ltn | grep -E ':(9999|9998|9090) '`", "no output"],
    ["Internet (HTTPS)", "the script tests it", "open-meteo, webhook.site, postman-echo, OpenAI, VS Code Marketplace"],
], [5.2, 6.6, 5.2], size=8.5)
callout("note", "Flogo licence", [
    "You do not need a licence today. Flogo apps started from VS Code without a licence run in **non-production "
    "mode** and stop after 24 hours (the log says so) — plenty for a workshop. Production apps need a licence.",
])

h2("1.3  What you install: Cline")
para("Cline is an open-source AI coding agent for VS Code. In Labs 2 and 3 it is the **MCP client**: it talks to "
     "the LLM and calls MCP tools. Install it now, so a Marketplace problem shows up early.")
steps([
    f"In VS Code open **Extensions** (`Ctrl+Shift+X`), search **Cline**, pick the extension named **Cline** "
    f"(identifier `{L['cline_id']}`) and click **Install**. A robot icon appears in the Activity Bar. "
    f"(Cline {L['cline_ver']} needs VS Code {L['vscode_min']} or later.)",
    "Click the Cline icon. On the welcome screen choose **Bring my own API key** (not \"Login to Cline\").",
    f"**API Provider** = **OpenAI** (not \"OpenAI Compatible\"). Paste the key shown on the day into **OpenAI API Key**. "
    f"Model = **{L['model']}**. Continue.",
    "At the bottom of the chat, set the mode toggle to **Act** (Plan mode cannot change anything).",
    "Generate your MCP settings with your real paths filled in, in a VS Code terminal:",
])
code(f"bash {L['kit']}/cline/print-mcp-settings.sh")
steps([
    "Select the whole JSON it prints and copy it (`Ctrl+Shift+C`).",
    "In Cline click the **MCP Servers** icon (stacked servers, top of the Cline panel) → **Configure** tab → "
    "**Configure MCP Servers** (at the bottom). `cline_mcp_settings.json` opens. Replace everything in it with "
    "the JSON and save (`Ctrl+S`).",
])
callout("check", "✅ Checkpoint — Cline is ready", [
    f"In **MCP Servers**, `flogo-fda-lab2` has a **green** dot and lists tools such as `describe-project` and "
    f"`create-flow`. `{L['l3_server']}` stays red until your Lab 3 app is running — that is expected.",
])

h2("1.4  The lab kit")
para(f"Everything you need is on the VM in `{L['kit']}` (`{L['kit_abs']}`). Open it in VS Code with **File → "
     "Open Folder… → Home → FlogoLab** (it is usually open already).")
table(["Folder / file", "What it is for"], [
    ["lab1/", "Lab 1: you create SW_RainfallRisk.flogo here; parramatta-*.json requests; sample-requests.sh"],
    ["lab2/leak-report-process.png", "The process diagram the AI turns into a flow"],
    ["lab2/prompts.md", "The prompts for Lab 2, ready to copy"],
    ["lab2/SW_LeakReport.flogo", "The app the Flogo Design Assistant edits (created on first use if missing)"],
    ["lab2/test-leak.sh", "Sends a test leak report to your Lab 2 API"],
    ["lab3/starter/SW_Water_MCP_Starter.flogo", "Lab 3 starter: MCP Server with two tools that call your Lab 1 + 2 APIs, no guardrails"],
    ["lab3/test-mcp.sh", "Tests the MCP server without an LLM"],
    ["lab3/prompts.md", "The agent prompts for Lab 3"],
    ["cline/", "Cline rules, MCP settings sample and print-mcp-settings.sh"],
    [".clinerules/", "Rules Cline loads automatically for this folder"],
    ["solutions/", "Fast track: Lab1_SW_RainfallRisk, Lab2_SW_LeakReport, Lab3_SW_Water_MCP"],
    ["prereq-check.sh", "The prerequisite check from 1.2"],
], [6.6, 10.4], mono_cols=(0,))
h2("1.5  VS Code orientation")
bullets([
    "**Explorer** (top icon in the left Activity Bar, `Ctrl+Shift+E`) shows the lab kit folders.",
    "**Flogo** icon in the Activity Bar opens the Flogo app view, where you run apps and see **Flogo App Executions**.",
    "Opening a `.flogo` file opens the **Flogo designer**, with the **FLOWS**, **APP PROPERTIES**, **CONNECTIONS**, "
    "**SCHEMAS** and **SPECS** tabs across the top.",
    "**Cline** (robot icon in the Activity Bar) is the AI coding agent used in Labs 2 and 3.",
    "**Terminal**: **Terminal → New Terminal** or **Ctrl+Shift+`** opens **bash** in the folder you have open. "
    "Paste with `Ctrl+Shift+V`. **Run as Executable** builds a Linux binary of your app and starts it.",
])
h2("1.6  Keys and accounts")
table(["Item", "Value"], [
    ["OpenAI API key (Cline, Labs 2–3)", L["openai_key"]],
    ["Cline provider / model", f"OpenAI / {L['model']}"],
    ["Field-service SaaS (Labs 1–3)", "Your own URL from https://webhook.site (you will get it in Lab 1)"],
    ["MCP API key (Lab 3)", f"{L['l3_mcp_key']} (a lab value, not a secret)"],
    ["VM login", "On your card (provided by the facilitator)"],
], [6.0, 11.0])
callout("warn", "The OpenAI key is for this workshop only",
        ["It is spend-capped and is revoked tonight. Do not paste it into anything except Cline on your lab VM."])
h2("1.7  Conventions in this guide")
table(["You see", "It means"], [
    ["✅ Checkpoint", "Stop and check the expected result. Not seeing it? Raise a hand."],
    ["⚡ Fast track", "Open the solution file and continue from the next step."],
    ["★ Stretch", "Optional extra if you finish early."],
    ["Shaded monospace block", "Copy and paste exactly (terminal: `Ctrl+Shift+V`)."],
    ["Expression in the mapper", "Type it without a leading `=` (the designer adds it). AI tools must include the `=`."],
], [4.5, 12.5])

# ============================================================ LAB 1
h1("2  Lab 1 — API integration & mediation")
facts([
    ("Goal", f"Build `{L['l1_app']}`: a REST API that takes a site and its coordinates, gets the rainfall forecast "
             "from a weather SaaS, works out a risk level and — if the risk is not LOW — raises an inspection "
             "work order in a field-service SaaS."),
    ("Time", "40 minutes (0:15 – 0:55)"),
    ("Use case", "SaaS-to-SaaS integration: Open-Meteo (weather) → Flogo → webhook.site (stand-in field-service SaaS)"),
    ("You learn", "App properties (≈ module properties), JSON Schema (≈ XSD), mapper functions (≈ XPath), "
                  "conditional and error links, App Executions"),
])
sketch(6, (0.75, 1.95, 12.55, 6.72), "lab1_arch.png",
       "curl --POST--> SW_RainfallRisk :9999 --GET--> api.open-meteo.com\n"
       "                                      --POST--> webhook.site (work order)\n"
       "LogRequest -> GetForecast -> BuildAssessment -[riskLevel != LOW]-> CreateInspection -> ReturnTicketed\n"
       "                 |error -> ReturnError 502      -[no match]-> ReturnNoAction",
       caption="Lab 1 architecture and the flow you will build")

h2("2.1  Get your field-service URL")
steps([
    "On the VM, open a browser at **https://webhook.site**. It gives you a unique URL like "
    "`https://webhook.site/1b2c…`. Leave this tab open — your work orders will appear here.",
    "Copy **Your unique URL**. If webhook.site is unavailable, use `https://postman-echo.com/post` instead "
    "(the echo appears in the HTTP response rather than a web page).",
])
h2("2.2  Create the app and its properties")
steps([
    f"In **Explorer**, right-click the `lab1` folder and choose **Create New Flogo App**. Name it `{L['l1_app']}`. "
    f"The file `{L['l1_app']}.flogo` opens in the Flogo designer.",
    "Open the **APP PROPERTIES** tab and add these four properties (**+** / Add property). Use the types shown.",
])
table(["Name", "Type", "Value"], [[n, t, v] for (n, t, v) in L["l1_props"]], [4.2, 2.0, 10.8], mono_cols=(0, 2))
callout("note", "BWCE comparison",
        ["App properties are Flogo's module properties / substitution variables. Flows read them with "
         "`$property[\"Risk.HighMm\"]`. At deploy time they are overridden per environment (environment variables, "
         "a JSON file, a vault, Kubernetes ConfigMaps/Secrets or Control Plane app variables) — the app is not rebuilt."])

h2("2.3  Create the flow and the REST trigger")
steps([
    f"Go to the **FLOWS** tab and create a flow named `{L['l1_flow']}` (**Create** → enter the name → **Create**). "
    "The flow opens on an empty canvas.",
    "In the triggers area on the left of the canvas, add a **ReceiveHTTPMessage** trigger (REST).",
    f"In the trigger configuration set **Method** = `POST` and **Resource path** = `{L['l1_path']}`.",
    "When asked for the request body, paste this sample into **Request Schema** (JSON Schema or a JSON sample "
    "— Flogo infers the schema from a sample):",
])
code(L["l1_req_sample"], caption="Request Schema (sample JSON)")
steps([
    f"Open the trigger's **Trigger Settings** and set **Port** = `{L['l1_port']}` (the default).",
    "Open **Reply Settings** and paste this into **Response Schema** (the reply body):",
])
code(L["l1_resp_sample"], caption="Response Schema (sample JSON)")
steps([
    "Check **Map to Flow Inputs**: `body` and `headers` should be mapped from the trigger output, and **Map from "
    "Flow Outputs**: the reply `data` and `code` from the flow output. If the designer did not do this "
    "automatically, map them by clicking each field and choosing the matching source.",
    "Open the flow's **Flow Inputs & Outputs** tab: the input should contain `body` with your request fields and "
    "the output should contain `code` and `data`. Save (`Ctrl+S`).",
])
callout("note", "JSON Schema vs XSD",
        ["Where BWCE uses XSD/WSDL, Flogo uses JSON Schema. You rarely write one by hand — paste a "
         "realistic sample and let the designer infer it. Use realistic values (e.g. `12.5`, not `0`) so numbers "
         "are typed as numbers."])

h2("2.4  Log the request")
steps([
    "Click **+** after the trigger and add **General → Log Message**. Rename it `LogRequest` (click the name).",
    "In its **Input** tab, set **message** to this expression:",
])
code(L["l1_log_expr"])

h2("2.5  Call the weather SaaS (GetForecast)")
steps([
    "Add **General → Invoke REST Service** after `LogRequest` and rename it `GetForecast`.",
    "**Settings**: **Method** = `GET`. For **URL**, click the field and map it to the app property "
    "`$property[\"Weather.URL\"]`.",
    "**Input Settings** → **Query Params**: add the five parameters below with their types.",
])
table(["Query param", "Type", "Map it to (Input tab)"], [[a, b, c] for (a, b, c) in L["l1_query"]], [3.6, 2.4, 11.0],
      mono_cols=(0, 2))
steps([
    "**Output Settings** → **Response Schema**: paste this sample of the Open-Meteo response.",
])
code(L["l1_forecast_sample"], caption="GetForecast Response Schema (sample JSON)")
steps([
    "**Input** tab: map each query parameter as in the table above. Literal strings go in double quotes.",
])
callout("check", "✅ Checkpoint 1 — the app runs (target 0:30)", [
    f"Save. Open the **Flogo** app view, find `{L['l1_app']}` and choose **Run as Executable**. The terminal shows "
    f"the app starting and listening on port {L['l1_port']}. Stop it again (you will add more first) — or "
    "continue straight to 2.6 and run at the end.",
])

h2("2.6  Build the assessment with the Mapper")
steps([
    "Add **General → Mapper** after `GetForecast` and rename it `BuildAssessment`.",
    "**Input Settings**: paste this sample to define the fields the Mapper produces:",
])
code(L["l1_assess_sample"])
steps([
    "**Input** tab: map the three fields with these expressions.",
])
code(L["l1_total_expr"], caption="totalRainfallMm")
code(L["l1_risk_expr"], caption="riskLevel (one expression — a nested ternary)")
code("datetime.now()", caption="assessedAt")
callout("note", "Mapper functions vs XPath",
        ["`array.sum(...)` replaces `sum(...)` in XPath; `cond ? a : b` replaces `if/then/else` or `xsl:choose`. "
         "Open the function list in the mapper (fx) to browse 90+ functions: string, number, array, datetime, json, "
         "coerce, utils. See Appendix A."])

h2("2.7  Branch: raise a ticket, or not")
steps([
    "Add **Invoke REST Service** after `BuildAssessment` and rename it `CreateInspection`.",
    "**Settings**: **Method** = `POST`, **URL** = `$property[\"FieldService.URL\"]`.",
    "**Output Settings** → **Response Type** = `text/plain`. webhook.site answers in plain text; left at "
    "`application/json` the call fails with HTTP 400 \"unable to deserialize response to json\".",
    "**Input Settings** → **Request Schema**: paste the canonical work-order sample below.",
])
code(L["l1_wo_sample"], caption="Work order Request Schema (sample JSON)")
steps([
    "**Input** tab → `body`: map the fields as follows.",
])
table(["body field", "Expression"], [[a, b] for (a, b) in L["l1_wo_map"]], [3.4, 13.6], mono_cols=(0, 1), size=8.5)
steps([
    "Click the link (arrow) from `BuildAssessment` to `CreateInspection`, change its type to **Success with "
    "condition** and enter the condition:",
])
code(L["l1_cond"])
steps([
    "Add a **Return** activity after `CreateInspection`, rename it `ReturnTicketed`, and map its outputs: `code` = "
    "`200`; `data.siteId`/`data.siteName` from `$flow.body`; `data.totalRainfallMm` and `data.riskLevel` from "
    "`$activity[BuildAssessment].output`; `data.inspectionRequested` = `true`; `data.message` = "
    "`string.concat(\"Inspection requested in Field Service (HTTP \", coerce.toString($activity[CreateInspection].statusCode), \")\")`.",
    "Add a second **Return** from `BuildAssessment`, rename it `ReturnNoAction`, and set that link to **Success with "
    "no matching condition**. Map: `code` = `200`, the same site/rainfall/risk fields, `inspectionRequested` = "
    "`false`, `message` = `\"Rainfall risk LOW - no inspection needed\"`.",
    "Add a third **Return** from `GetForecast`, rename it `ReturnError`, and set that link to **Error**. Map: `code` = "
    "`502`, `riskLevel` = `\"UNKNOWN\"`, `inspectionRequested` = `false`, `message` = "
    "`string.concat(\"Weather service unavailable: \", $error[GetForecast].message)`. In an **error branch** the "
    "designer wants the failing activity's name in brackets; plain `$error.message` is for the flow's **Error "
    "Handler** tab.",
    "Save. Your flow should look like the sketch at the start of this lab: orange (condition), purple (no matching "
    "condition) and red (error) links.",
])

h2("2.8  Run and test")
steps([
    f"In the **Flogo** app view, choose **Run as Executable** for `{L['l1_app']}`. Flogo builds a Linux binary and "
    f"starts it; wait for the log line that it is listening on port {L['l1_port']}.",
    "Open a second terminal (**Terminal → New Terminal**, or the **+** in the terminal panel) and call your API with "
    "one of the ready-made requests (Parramatta, 1-day forecast):",
])
code(f"cd {L['kit']}/lab1\n"
     f"curl -s -X POST http://localhost:{L['l1_port']}{L['l1_path']} \\\n"
     f"  -H \"Content-Type: application/json\" -d @parramatta-1day.json; echo")
para("Or run all three samples (1, 3 and 7 days) in one go: `bash ~/FlogoLab/lab1/sample-requests.sh`. "
     "The request body is the Request Schema sample from 2.3.", size=9.5, color=MUTED)
callout("check", "✅ Checkpoint 2 — you get an assessment (target 0:38)", [
    "HTTP 200 with a body like the one below. The numbers are today's live forecast, so yours will differ — "
    "with `forecastDays` = 1 a dry week usually gives LOW. Add `-i` to curl to see the status line.",
    "$ " + L["l1_expect_low"].replace("\n", " "),
])
h2("2.9  Make it raise a ticket")
para("Risk depends on the live forecast. To force the ticket branch on a dry day, lower the threshold — no flow "
     "change needed:")
steps([
    "Stop the app. In **APP PROPERTIES** set `Risk.MediumMm` = `0`. Save and **Run as Executable** again.",
    "Send the same request.",
])
callout("check", "✅ Checkpoint 3 — a work order lands in the field-service SaaS (target 0:47)", [
    "The response now has `\"inspectionRequested\": true` and a riskLevel of MEDIUM (or HIGH on a wet day). In your "
    "webhook.site tab a new POST appears with the canonical work order JSON (`source`, `siteId`, `priority`, "
    "`reason`, `totalRainfallMm`, `requestedAt`).",
    "$ " + L["l1_expect_ticket"].replace("\n", " "),
    "Want LOW again? Set `Risk.MediumMm` back to `5` (or `500`). Want more rain? Use `parramatta-7day.json`.",
])
h2("2.10  Prove the error branch")
steps([
    f"Stop the app, set `Weather.URL` to `{L['l1_bad_url']}`, run again and send the request.",
    "Afterwards set `Weather.URL` back to `https://api.open-meteo.com/v1/forecast` and run the app again.",
])
callout("check", "✅ Checkpoint 4 — HTTP 502 with a readable message (target 0:52)",
        ["$ " + L["l1_expect_err"].replace("\n", " ")])
h2("2.11  See what happened: Flogo App Executions")
steps([
    "Open the **Flogo** app view and expand **Flogo App Executions** (Runtime Explorer).",
    "Select your latest execution. The path taken is highlighted; click any activity to see its **input** and "
    "**output** — for example the raw Open-Meteo response in `GetForecast` and the computed values in `BuildAssessment`.",
])
callout("note", "Debugging in Flogo",
        ["There are no breakpoints. Instead you get per-activity inputs/outputs in App Executions, unit tests with "
         "mocks, logs, and OpenTelemetry traces in deployed environments."])
callout("warn", "Keep your Lab 1 app",
        [f"Lab 3 calls this API as an MCP tool. Leave `{L['l1_app']}` working (Weather.URL restored, `Risk.MediumMm` "
         "as you like); you will run it again in Lab 3."])
h2("2.12  Troubleshooting")
table(["Symptom", "Fix"], [
    ["curl: `Failed to connect … Connection refused`", f"The app is not running, or still building. Check its terminal for \"listening on {L['l1_port']}\"."],
    ["Port already in use", "A previous run is still alive. Stop it from the Flogo app view, or in a terminal: "
     f"`fuser -k {L['l1_port']}/tcp`."],
    ["Build fails: `go` not found / Go too old", f"VS Code cannot see Go {L['go_min']}+. Run `go version` in a VS Code terminal; tell a presenter."],
    ["curl: `Couldn't read data from file`", "Run it from `~/FlogoLab/lab1` (the `cd` line), or give the full path after `@`."],
    ["400 / JSON error", "The request JSON is invalid or the Content-Type header is missing."],
    ["totalRainfallMm is 0 or empty", "Response Schema for GetForecast is missing `daily.precipitation_sum` as a number array."],
    ["Always LOW / always ticketed", "Expected — it is the live forecast. Adjust `Risk.MediumMm` or `forecastDays` (2.9)."],
    ["Nothing on webhook.site", "Wrong `FieldService.URL` or the condition never matched. Check App Executions."],
    ["Expression shows as text", "Strings need double quotes; property names need `$property[\"...\"]` with quotes."],
], [5.5, 11.5])
callout("fast", "⚡ Fast track", [
    f"In a terminal: `cp {L['kit']}/solutions/{L['solutions'][1]} {L['kit']}/lab1/` and open it from Explorer. In "
    "**APP PROPERTIES** set `FieldService.URL` to your webhook.site URL, then continue from 2.8.",
])
callout("stretch", "★ Stretch — a unit test (BWCE .bwt → Flogo .flogotest)", [
    f"Right-click `{L['l1_app']}.flogo` → **Create Unit Tests for Flogo App**. In the new `.flogotest`, add a test "
    "case for the flow with the request sample as flow input, set `GetForecast` to **Mock Output** with "
    "`precipitation_sum` = `[30, 10]`, and add an assertion that `$.data.riskLevel` equals `HIGH`. Run it with the "
    "play icon. In CI the same file runs with `flogobuild test-app` and produces JUnit XML.",
])

# ============================================================ LAB 2
h1("3  Lab 2 — AI-assisted development")
facts([
    ("Goal", f"Turn a process diagram into a working Flogo flow with Cline and the Flogo Design Assistant (FDA), "
             f"then review and finish it in the designer."),
    ("Time", "30 minutes (0:55 – 1:25)"),
    ("You build", f"`{L['l2_app']}` — POST `:{L['l2_port']}{L['l2_path']}`"),
    ("You learn", "Picture-to-flow, prompting with FDA rules, what AI does well and what you must own"),
])
sketch(9, (0.75, 2.5, 12.55, 4.25), "lab2_arch.png",
       "leak-report-process.png -> Cline (gpt-4.1) --MCP stdio--> flogodesign-cli -f SW_LeakReport.flogo -> designer",
       caption="Cline drives the Flogo Design Assistant, which edits one .flogo file")
callout("warn", "Tech Preview", ["The Flogo Design Assistant is a Tech Preview. Treat everything it creates as a "
                                 "first draft: open it, read it, test it."])
h2("3.1  Check your setup (2 minutes)")
steps([
    "Click the **Cline** icon in the Activity Bar. At the bottom of the chat panel check the provider is **OpenAI** and "
    f"the model is **{L['model']}**. Not installed or not configured yet? Do section 1.3 now (3 minutes).",
    "Make sure the mode toggle shows **Act** (Plan mode cannot change files).",
    "Click the **MCP Servers** icon at the top of the Cline panel. `flogo-fda-lab2` should have a green dot and list "
    "tools such as `describe-project`, `create-flow`, `create-activity` and `set-attribute`.",
    "Open the **Rules** panel (scale icon left of the model picker) and check `cline-rules-flogo-fda.md` is enabled.",
])
h2("3.2  Read the diagram first")
steps([
    f"In Explorer open `{L['l2_png']}` (\"Customer Leak Report Intake\"). Read it left to right:",
])
bullets([
    f"**Receive leak report** — REST POST `{L['l2_path']}` on port {L['l2_port']}.",
    "**Log report**, then **Build work order** — map severity to priority: HIGH → P1, MEDIUM → P2, LOW → P3.",
    "A parallel gateway: **Create work order in Field Service SaaS (POST)** and **Log audit entry** run side by side "
    "(they become **parallel paths**), then join.",
    "**Reply 201 with work-order reference**.",
], level=2)
steps([
    "Think about what you expect the Flogo flow to look like. You will compare it with what the AI builds.",
])
h2("3.3  Part 2a — picture to flow")
steps([
    "Start a new Cline task. Below the chat box click the **+** button (**Add Files & Images**), browse to "
    "**Home → FlogoLab → lab2** and pick `leak-report-process.png`. A thumbnail appears in the message.",
    f"Paste the prompt below (also in `{L['kit']}/lab2/prompts.md`, Prompt 1) into the same message and press Enter.",
])
code(L["l2_picture_prompt"])
para("Why a guided prompt? FDA also has a built-in *create-flogo-flow-from-picture* prompt. In our dry run it made "
     "60+ tool calls and still left the wrong port and bad mappings. Naming the flow, activity types and port, and "
     "asking only for the structure, finished in 18 calls and about 30 seconds.", size=9.5, color=MUTED)
steps([
    "Cline calls FDA tools one by one. Read each request and click **Approve** (you will see `create-flow`, "
    "`create-trigger`, `create-trigger-handler`, `create-activity`, `create-link`, `create-app-property`, "
    "`set-attribute`, `format-flow`). About 30 seconds.",
    "Read Cline's summary. If it offers to run `check-mappings` and reports `TR_REST_NO_SWAGGER` "
    "(\"runtime will panic\"), ignore it: that is a known false positive and the app runs fine. Do **not** let Cline "
    "replace the REST trigger.",
])
callout("check", "✅ Checkpoint 1 — FDA created the flow (target 1:05)", [
    f"Open `{L['l2_file']}` in the designer (if it is already open, close and reopen it to reload). On the **FLOWS** tab you "
    "see a flow whose activities and parallel paths match the diagram, laid out automatically.",
])
h2("3.4  Review and finish it in the designer")
para("The AI built the structure. Schemas and mappings are your job; they use the same skills as Lab 1. Check first: "
     f"trigger on port `{L['l2_port']}`, POST `{L['l2_path']}`, five activities, two parallel paths joining at Reply201.")
steps([
    "**Trigger handler** → **Output Settings** → **Request Schema**: paste the sample below. "
    "**Reply Settings** → reply data schema: paste the reply sample. Map the trigger output `body` to the flow "
    "input, and flow output `code`/`data` to the reply.",
])
code(pretty(L["l2_req_schema"]), caption="Request Schema (sample JSON)")
code(pretty(L["l2_reply_schema"]), caption="Reply data schema (sample JSON)")
steps([
    "**LogReport** → message:",
])
code(L["l2_log_expr"])
steps([
    f"**BuildWorkOrder** (Mapper) → Input Schema `{L['l2_wo_schema']}`, then map:",
])
table(["field", "Expression"], [[a, b] for (a, b) in L["l2_wo_map"]], [3.4, 13.6], mono_cols=(0, 1), size=8.5)
steps([
    f"**CreateWorkOrder** → Request Schema `{L['l2_create_schema']}`. Map `source` = `\"flogo-leak-intake\"`; "
    "`workOrderRef`, `location`, `priority` from `$activity[BuildWorkOrder].output`; `reportId`, `description` from "
    "`$flow.body`. Set **Response Type** = `text/plain` (webhook.site answers in plain text).",
    "**APP PROPERTIES** → set `FieldService.URL` to **your webhook.site URL** from Lab 1, so you can watch the work "
    "orders arrive. (You will need this in Lab 3.)",
    "**LogAudit** → message:",
])
code(L["l2_audit_expr"])
steps([
    "**Reply201** (Return): `code` = `201`; `data`: `reportId` = `$flow.body.reportId`, `workOrderRef` and "
    "`priority` from `$activity[BuildWorkOrder].output`, `status` = `\"RECEIVED\"`.",
    "Optional, for production: add an **Error** link from CreateWorkOrder to a Return with code `502`. The diagram "
    "doesn't show it, and FDA cannot create error links.",
])
para("Stuck on a mapping? Ask Cline with the mapping prompt below, filling in names from `describe-project`.",
     size=9.5, color=MUTED)
code(L["l2_mapping_prompt"])
h2("3.5  Run and test")
steps([
    f"Run the app (**Flogo** app view → **Run as Executable**). Then test it from a terminal:",
])
code(f"curl -s -X POST http://localhost:{L['l2_port']}{L['l2_path']} \\\n"
     "  -H \"Content-Type: application/json\" \\\n"
     "  -d '" + L["l2_req_schema"].replace(',"description"', ',\n       "description"') + "'; echo")
para(f"Or simply `bash {L['kit']}/lab2/test-leak.sh`. Try `\"severity\": \"MEDIUM\"` (P2) and `\"LOW\"` (P3) too.",
     size=9.5, color=MUTED)
callout("check", "✅ Checkpoint 2 — your AI-drafted flow runs (target 1:15)", [
    "HTTP 201 and this reply:",
    "$ " + L["l2_expect"],
    "In **Flogo App Executions** both parallel paths ran, and the field-service request is visible in the call's "
    "input/output.",
])
h2("3.6  Part 2b — change it and explain it")
steps([
    "Stop the app. Ask Cline to modify the flow, for example:",
])
code(L["l2_modify_prompt"])
steps([
    "Reload the flow in the designer and check the change is exactly what you asked for.",
    "Known FDA issue: the **remove-link** step does nothing, so the old link CreateWorkOrder → Reply201 stays. "
    "Delete it by hand in the designer. If you forget, nothing breaks; Reply201 just waits for every branch.",
    "Ask FDA to explain building blocks in BusinessWorks terms:",
])
code(L["l2_explain_prompt"])
callout("check", "✅ Checkpoint 3 — modify + explain (target 1:22)", [
    "LogWorkOrderId sits between CreateWorkOrder and Reply201, and the app log shows "
    "\"Work order created: WO-LR-1001\". The explanation maps Invoke REST and string.concat to what you know from BW.",
])
h2("3.7  What you just learned")
table(["The AI did", "You did"], [
    ["Read the diagram: flow, trigger, port, 5 activities", "Checked it matched the business process"],
    ["Built parallel paths, the app property and the REST call settings", "Defined request/reply schemas and flow I/O"],
    ["Inserted a new activity and re-formatted on request", "Wrote mappings, removed the leftover link, added error handling"],
    ["Explained activities and functions in BW terms", "Ran it, tested it, decided what is fit to commit"],
], [8.5, 8.5])
h2("3.8  Troubleshooting")
table(["Symptom", "Fix"], [
    ["`flogo-fda-lab2` is red", "Wrong `flogodesign-cli` path in the MCP settings (re-run `print-mcp-settings.sh`), or the "
     f"file is not executable: `chmod +x {L['ext_glob']}/bin/flogodesign-cli`, then restart the server."],
    ["Cline says 401 / invalid key", "Re-select **API Provider: OpenAI** (not \"OpenAI Compatible\") and re-paste the key."],
    ["429 / rate limit", "Wait 30 s and retry; the room shares one key."],
    ["Cline edits the .flogo file directly", "Stop it and remind it: \"Use only the flogo design tools.\""],
    ["Designer doesn't show the changes", "Close and reopen the .flogo file."],
    ["Mappings appear as plain text", "Missing leading `=` — fix in the mapper or re-prompt with the mapping prompt."],
    ["`check-mappings` says TR_REST_NO_SWAGGER", "False positive — ignore it; don't let Cline swap the trigger."],
    ["Port clash on 9999", f"The Lab 2 trigger must be on {L['l2_port']}; stop Lab 1 or fix the trigger port."],
    ["CreateWorkOrder returns HTTP 400", "Set its Response Type to `text/plain` (webhook.site replies in text)."],
    ["Image ignored", "Check the model is gpt-4.1 (vision-capable) and the thumbnail is in the message."],
], [5.5, 11.5])
callout("fast", "⚡ Fast track", [
    f"`cp {L['kit']}/solutions/{L['solutions'][2]} {L['kit']}/lab2/SW_LeakReport.flogo` (replaces the AI draft, so FDA "
    "edits the solution in part 2b). Open it, set `FieldService.URL` to your webhook.site URL, run it and continue "
    "from 3.5.",
])
callout("warn", "Keep your Lab 2 app",
        [f"Lab 3 calls this API as an MCP tool. Keep `{L['l2_app']}` working; you will run it again in Lab 3."])
callout("stretch", "★ Stretch — explain a flow you inherited", [
    "Ask Cline: \"Use describe-project and explain the LeakReportIntake flow step by step for a new team member, "
    "in BusinessWorks terms.\" Compare the explanation with what you built.",
])

# ============================================================ LAB 3
h1("4  Lab 3 — Your APIs as MCP tools, with guardrails")
facts([
    ("Goal", "Expose the two APIs you built — Lab 1 rainfall risk and Lab 2 leak report — to an AI agent as MCP "
             "tools, by hand in the designer. Then govern them with four guardrails: authentication, input "
             "validation, PII masking, and least privilege with output shaping."),
    ("Time", "35 minutes (1:35 – 2:10)"),
    ("Use case", "Agent-to-API: AI agent → MCP → your Flogo APIs → SaaS (weather, field service)"),
    ("You learn", "MCP Server trigger, tool handlers and arguments, API Key auth with a Password property, "
                  "guardrail patterns in a flow"),
])
sketch(12, (0.75, 2.12, 12.55, 4.72), "lab3_arch.png",
       f"Cline agent --MCP streamable HTTP :{L['l3_mcp_port']}/mcp--> Flogo {L['l3_app']} (2 tools + guardrails)\n"
       "   assess_rainfall_risk --REST--> Lab 1 API :9999 --> Open-Meteo / field service\n"
       "   report_leak          --REST--> Lab 2 API :9998 --> field service (webhook.site)",
       caption="The agent sees two governed tools; your APIs and the SaaS behind them stay inside Flogo")

h2("4.1  Why: agents need tools — and limits")
para("An AI agent is only as useful as the tools it can call, and only as safe as the limits on those tools. "
     "**MCP** (Model Context Protocol) is the standard way for agents to discover and call tools. Flogo's **MCP "
     "Server** trigger turns flows into MCP tools, so any API you already have — today your Lab 1 and Lab 2 APIs, "
     "tomorrow a BWCE service or an on-premise system — becomes an agent tool **without changing it**.")
table(["Tool", "Arguments the agent sends", "Calls"], [[t, a, c] for (t, a, c) in L["l3_tools"]],
      [4.2, 6.6, 6.2], mono_cols=(0,), size=8.5)

h2("4.2  Start your Lab 1 and Lab 2 APIs")
steps([
    f"Lab 3 calls both APIs, so both must run for the whole lab. Open `lab1/{L['l1_app']}.flogo` and choose **Run as "
    f"Executable**; then open `lab2/{L['l2_app']}.flogo` and **Run as Executable**. Each runs in its own terminal "
    f"(ports {L['l1_port']} and {L['l2_port']}).",
    f"Not finished, or not sure they work? Use the solutions instead: open `{L['kit']}/solutions/{L['solutions'][1]}` "
    f"and `{L['kit']}/solutions/{L['solutions'][2]}`, set `FieldService.URL` in **both** to your webhook.site URL, "
    "and run them.",
    "Check both answer (Lab 2 should be pointed at your webhook.site URL — see 3.4):",
])
code(f"bash {L['kit']}/lab1/sample-requests.sh\nbash {L['kit']}/lab2/test-leak.sh")
callout("check", "✅ Checkpoint 1 — both APIs are up (target 1:40)", [
    f"Lab 1 returns 200 with a `riskLevel`; Lab 2 returns 201 with a `workOrderRef`. Leave both terminals running.",
])

h2("4.3  Open the starter and connect the agent")
steps([
    f"Open `{L['l3_starter']}` in the designer.",
    f"Click the **MCP Server** trigger: **Server Type** `HTTP`, **HTTP Server Port** `{L['l3_mcp_port']}`, "
    f"**HTTP Server Endpoint Path** `/mcp`, **Authentication Type** `None`. It has two handlers with **MCP Primitive "
    f"Type** `Tool`: `{L['l3_tools'][0][0]}` → flow `{L['l3_flow_assess']}` and `{L['l3_tools'][1][0]}` → flow "
    f"`{L['l3_flow_leak']}`. Each tool has a name, a **description** (what the LLM reads to choose a tool) and an "
    "**arguments** schema.",
    "**APP PROPERTIES** has one URL per API:",
])
table(["Name", "Type", "Value"], [[n, t, v] for (n, t, v) in L["l3_props"]], [4.2, 2.0, 10.8], mono_cols=(0, 2))
steps([
    f"Open the flow `{L['l3_flow_leak']}`: `{L['l3_log']}` → `{L['l3_rest_leak']}` (Invoke REST, **Method** POST, "
    f"**URL** bound to `Lab2.LeakReportURL` with the field's app-property toggle, body mapped from "
    f"`$flow.arguments.<field>`) → `{L['l3_return']}` (`response.data`). `{L['l3_flow_assess']}` has the same shape "
    f"and calls `Lab1.AssessURL`.",
    "**Run as Executable** for the starter.",
    f"In Cline → **MCP Servers**, `{L['l3_server']}` turns **green** with two tools (if it stays red, click its "
    f"restart/retry button). Its settings already send `Authorization: Bearer {L['l3_mcp_key']}` — harmless now, "
    "needed after guardrail 1.",
    "Optional, without an LLM — list the tools and call each once:",
])
code(f"{L['l3_test']} --no-key")
callout("note", "Invoke REST URL = one whole app property", [
    "The **URL** field takes a literal or **one** app property, picked with the field's app-property toggle. Do not "
    "type an expression such as `string.concat(...)` — the designer blanks it (\"URL is required\").",
])

h2("4.4  Run the agent — then see the problems")
steps([
    f"Start a new Cline task (**+**) and paste the agent prompt (also Prompt 1 in `{L['l3_prompts']}`):",
])
code(L["l3_agent_prompt"])
steps([
    f"Approve the two tool calls (`{L['l3_tools'][1][0]}` and `{L['l3_tools'][0][0]}`). Cline reports the work order "
    "(`WO-LR-2001`, priority P1) and the rainfall risk for PS-102.",
    "Now open your **webhook.site** tab and look at the new work order from Lab 2: its `description` contains Jo's "
    "**phone number and email** — personal data that went from the chat, through your API, straight into the "
    "field-service SaaS.",
    "New task — a value your business never uses:",
])
code(L["l3_bad_severity"])
steps([
    "Accepted: Lab 2 files a burst main as **P3** — a silent downgrade. (If the agent asks you to confirm, reply "
    "`Yes, send URGENT exactly as written.`) New task — a site outside Sydney Water's area:",
])
code(L["l3_bad_site"])
steps([
    "Accepted too: Lab 1 assesses Melbourne and may even raise an inspection. Finally, from a terminal — no "
    "credentials at all:",
])
code(f"curl -s -o /dev/null -w \"%{{http_code}}\\n\" -X POST {L['l3_mcp_url']} \\\n"
     "  -H \"Content-Type: application/json\" -d '{}'")
para("Anything other than `401` means the MCP server is not checking who is calling.", size=9.5, color=MUTED)
table(["Problem you just saw", "Guardrail you will add"], [
    ["Anyone who can reach :9090 can call every tool", "G1  API Key authentication"],
    ["Any input accepted: severity URGENT, a Melbourne site", "G2  Input validation in the flow"],
    ["The caller's phone and email flow into the field-service SaaS", "G3  PII masking"],
    ["One-line tool descriptions, default hints, the whole backend reply returned", "G4  Least privilege & output shaping"],
], [10.0, 7.0])
callout("check", "✅ Checkpoint 2 — the agent works, and so does a careless agent (target 1:48)", [
    "Both tools worked from the chat, the work order is on webhook.site with contact details, URGENT and "
    "Melbourne were accepted, and the anonymous curl did **not** get 401.",
])

h2("4.5  Guardrail 1 — authenticate the agent")
steps([
    f"Stop the starter. **APP PROPERTIES** → add `{L['l3_mcp_key_prop']}` with type **Password** and value "
    f"`{L['l3_mcp_key']}` (the designer encrypts it). It must be Password: the Secret field is a password field, and "
    "binding it to a String property shows \"Type of field Secret (password) differs from the bound app property\".",
    "Open the **MCP Server** trigger settings and set **Authentication Type** = **API Key**.",
    f"In the **Secret** field that appears, switch on its app-property toggle and pick `{L['l3_mcp_key_prop']}` "
    "(never type the key itself). Save and **Run as Executable**.",
    "Repeat the anonymous `curl` from 4.4 — it now returns `401`. Then send the key:",
])
code(f"curl -s -o /dev/null -w \"%{{http_code}}\\n\" -X POST {L['l3_mcp_url']} \\\n"
     f"  -H \"Content-Type: application/json\" -H \"Authorization: Bearer {L['l3_mcp_key']}\" -d '{{}}'")
steps([
    f"Cline already sends the Bearer key, so `{L['l3_server']}` reconnects. Restart it in **MCP Servers** if needed.",
])
callout("check", "✅ Checkpoint 3 — 401 without the key, connected with it (target 1:53)",
        ["No header → `401` (\"no bearer token\"). With the Bearer key → not 401, and Cline lists the two tools "
         "again. A **wrong** key is also rejected, currently with HTTP `500` \"invalid API key\" rather than 401."])

h2("4.6  Guardrail 2 — validate inputs before anything reaches your APIs")
para(f"Check the agent's arguments first in each tool flow. A rejection goes back to the agent as a tool error "
     f"(`response.error`), and your API is never called. Start with `{L['l3_flow_leak']}`:")
steps([
    f"Delete the link `{L['l3_log']}` → `{L['l3_rest_leak']}`. Add a **Mapper** after `{L['l3_log']}` and rename it "
    "`ValidateInput`.",
    "**Input Settings**: schema `{\"rejectReason\":\"\"}`. **Input** tab: map `rejectReason` to this expression "
    "(empty string = valid):",
])
code(L["l3_validate_leak"], caption=f"rejectReason in {L['l3_flow_leak']}")
steps([
    "Add a **Return** after `ValidateInput` and rename it `ReturnRejected`. Set that link to **Success with "
    "condition**:",
])
code(L["l3_reject_cond"])
steps(["Map `ReturnRejected` → `response.error`:"])
code(L["l3_reject_expr"])
steps([
    f"Link `ValidateInput` → `{L['l3_rest_leak']}` and set that link to **Success with no matching condition**.",
    f"Repeat steps 1–5 in `{L['l3_flow_assess']}` (before `{L['l3_rest_assess']}`) with this rejectReason. The "
    "`coerce.*` calls make the numbers comparable whatever JSON type the agent sends:",
])
code(L["l3_validate_assess"], caption=f"rejectReason in {L['l3_flow_assess']}")
steps([
    "Save, run, and repeat the URGENT and Melbourne prompts from 4.4 in new Cline tasks.",
])
callout("check", "✅ Checkpoint 4 — rejected by guardrail (target 1:59)", [
    f"The tool results are `{L['l3_reject_sev']}` and `{L['l3_reject_site']}`. The Lab 1 and Lab 2 terminals log "
    "**no** new request — the guardrail stopped them before your APIs.",
])

h2("4.7  Guardrail 3 — mask personal data before it leaves")
para(f"In `{L['l3_flow_leak']}` the description is sent to the field-service SaaS. Mask phone numbers and email "
     "addresses on the way out:")
steps([
    f"Delete the link `ValidateInput` → `{L['l3_rest_leak']}`. Add a **Mapper** after `ValidateInput`, rename it "
    f"`MaskPII`, and set that new link to **Success with no matching condition**. Link `MaskPII` → `{L['l3_rest_leak']}`.",
    "`MaskPII` **Input Settings**: schema `{\"description\":\"\"}`. **Input** tab: map `description` to:",
])
code(L["l3_mask_expr"], caption="MaskPII.description — string.replaceRegEx(regex, input, replacement): emails first, then AU mobile / landline numbers")
steps([
    f"Open `{L['l3_rest_leak']}` → **Input** tab → `body.description` and change it from `$flow.arguments.description` "
    "to `$activity[MaskPII].output.description`.",
    f"Logs are a PII sink too: `{L['l3_log']}` writes the raw arguments, phone and email included. Change its message to:",
])
code(L["l3_safe_log"])
para("(The solution goes one step further: it logs the **masked** description in a `LogForward` activity after "
     "`MaskPII`.)", size=9.5, color=MUTED)
steps([
    "Save, run, and send the agent prompt from 4.4 again.",
])
callout("check", "✅ Checkpoint 5 — no personal data reaches the SaaS (target 2:03)", [
    f"On webhook.site the new work order's `description` shows `{L['l3_masked']}` where the phone number and email "
    "were; report id, address and severity are unchanged, and the agent still gets its work order. The Lab 3 log no "
    "longer shows the phone number. (The model decides what goes into `description`; once your tool description "
    "says contact details are masked it may leave them out itself — a soft guardrail. The Flogo mask is the hard "
    "one: it works whatever the model does.)",
])

h2("4.8  Guardrail 4 — least privilege and output shaping")
steps([
    "**Least privilege.** The agent gets exactly two tools that do one business thing each — no generic \"call any "
    "URL\" tool, no admin or delete operations. Every new tool is a decision, not a default.",
    "**Clear descriptions.** The LLM chooses and fills tools from their descriptions. Open each tool handler, set "
    f"the title (`{L['l3_title_assess']}` / `{L['l3_title_leak']}`) and replace the one-line description:",
])
code(L["l3_desc_assess"], caption=L["l3_tools"][0][0])
code(L["l3_desc_leak"], caption=L["l3_tools"][1][0])
steps([
    "**Honest hints.** Check each handler: **ReadOnly Tool** = false (both tools create a ticket or work order), "
    "**Destructive Tool** = false, **Idempotent Tool** = false, **Open World Tool** = true (they reach external SaaS). "
    "Clients use hints to decide what needs human approval; hints are advice, not enforcement (that is G1–G3).",
    f"**Return only what the agent needs.** In each flow delete the link from the REST call to `{L['l3_return']}`, add "
    f"a **Mapper** `ShapeResult` in between, paste the schema sample below, and map each field from "
    "`$activity[<REST call>].responseBody.<field>`:",
])
code(pretty(L["l3_shape_assess"]), caption=f"ShapeResult schema in {L['l3_flow_assess']}")
code(pretty(L["l3_shape_leak"]), caption=f"ShapeResult schema in {L['l3_flow_leak']}")
steps([
    f"Change `{L['l3_return']}` → `response.data` to `{L['l3_return_expr']}`.",
    "**Fail cleanly.** Add a **Return** `ReturnBackendError` with an **Error** link from each REST call, mapping "
    "`response.error`:",
])
code(L["l3_backend_err_leak"], caption=L["l3_flow_leak"])
code(L["l3_backend_err_assess"], caption=L["l3_flow_assess"])

h2("4.9  Prove it: the scenario again, then the test script")
steps([
    "New Cline task: paste the agent prompt from 4.4 once more. Same outcome as Checkpoint 2 — work order and "
    "risk — but the contact details are masked. Guardrails do not get in the way of legitimate work. That is the point.",
    "Run the guardrail tests (no LLM involved):",
])
code(L["l3_test"])
callout("check", "✅ Checkpoint 6 — every guardrail holds (target 2:08)", [
    "No key → 401; wrong key → rejected; the two tools are listed with your descriptions; a valid call to each tool "
    "succeeds; URGENT and Melbourne are rejected by guardrail; the description arrives masked. Every line says PASS.",
])

h2("4.10  Presenter demo — production-grade options")
table(["Capability", "What it adds"], [
    ["JWT auth + per-tool **Required Scope**", "`tools/list` only shows the tools the caller's token scopes allow "
     "(sample `MCP_JWT_Scope_Access_Control` in flogo-enterprise-hub)"],
    ["MCP Elicitation", "Ask the human to approve (or add details) before a write executes"],
    ["OAuth 2.0 / JWKS (2.26.6+)", "Validate tokens issued by your identity provider; tokenInfo claims in the flow"],
    ["TIBCO Platform MCP Hub", "One governed gateway and catalogue for every agent's tools (Preview)"],
    ["FDA `create-mcp-skeleton`", "Generates an MCP server from the OpenAPI spec of your Lab 1 + 2 APIs in seconds "
     "— a scaffold; the guardrails are still yours to add"],
], [6.0, 11.0])

h2("4.11  Troubleshooting")
table(["Symptom", "Fix"], [
    ["Tool result: `connection refused` on `:9999` or `:9998`",
     "Your Lab 1 or Lab 2 app is not running — the MCP server is fine, its backend is down. Start it (or its "
     "solution, 4.2) and retry. `[::1]` in the message is just the first address tried for localhost."],
    [f"`{L['l3_server']}` red in Cline", "MCP app not running; or after G1 the Bearer header is missing; restart the "
     "server entry in **MCP Servers**."],
    ["Cline searches your files and guesses tool names (e.g. `log_leak_report`) instead of calling `report_leak`",
     f"`{L['l3_server']}` is not in **Cline's** MCP settings — Cline has no tools. Add it via Cline → **MCP Servers** → "
     "**Configure MCP Servers** (servers added with VS Code's **MCP: Add Server** are for Copilot Chat only), check "
     "it is green with two tools, start a new task."],
    ["VS Code: \"MCP Server Definition … wants to authenticate to localhost:9090\", then `/authorize` → 404 page not found",
     "The server was added to VS Code's own MCP config without the Bearer header, so VS Code tried OAuth (Flogo has "
     f"none). Click **Cancel**; add it in Cline instead. For Copilot, add `\"headers\": {{\"Authorization\": \"Bearer "
     f"{L['l3_mcp_key']}\"}}` to the VS Code entry and run **Authentication: Remove Dynamic Authentication Providers**."],
    ["Port 9090 already in use", "The starter is still running. Stop it before running your changed app or the "
     "solution (`fuser -k 9090/tcp`)."],
    ["HTTP 500 \"invalid API key\"", f"Wrong key: the header must be exactly `Authorization: Bearer {L['l3_mcp_key']}`."],
    ["Designer: Secret \"(password) differs from the bound app property (string)\"",
     f"`{L['l3_mcp_key_prop']}` was created as String. Recreate it as **Password** and re-bind."],
    ["Designer: \"URL is required\" on Invoke REST", "The URL was set to an expression. Bind it to one whole app "
     "property with the toggle."],
    ["Validation never triggers", "Check the link types: condition on `ReturnRejected`, no-matching-condition to the REST call."],
    ["The LLM \"fixes\" URGENT or refuses Melbourne", "Good model behaviour — use the exact prompts in 4.4; if it "
     "asks, reply `Yes, send URGENT exactly as written.`"],
    ["Phone still visible on webhook.site", f"`{L['l3_rest_leak']}` body.description must map "
     "`$activity[MaskPII].output.description`, not `$flow.arguments.description`. Save and re-run the app."],
    ["Agent never calls a tool", "It may be waiting for your approval — check the chat."],
], [6.0, 11.0])
callout("fast", "⚡ Fast track", [
    f"Open `{L['kit']}/solutions/{L['solutions'][3]}` (all four guardrails applied), stop the starter, run the "
    f"solution with your Lab 1 and Lab 2 apps still running, then `{L['l3_test']}` and the prompts in 4.4.",
])
callout("stretch", "★ Stretch — make the limits configurable", [
    "Move a guardrail limit into an app property (for example `Guardrail.MaxForecastDays` = 7, read with "
    "`$property[\"Guardrail.MaxForecastDays\"]`). Ops can then tighten it per environment without a rebuild — "
    "exactly like `Risk.MediumMm` in Lab 1.",
])

# ============================================================ WRAP-UP
h1("5  What you built today")
table(["Lab", "Pattern", "Where it applies at Sydney Water"], [
    ["1", "REST API mediating two SaaS APIs; properties, transform, route, error branch",
     "New REST/JSON integrations, SaaS-to-SaaS, replacing simple BWCE REST services"],
    ["2", "AI-drafted flow from a process diagram, finished by a developer",
     "Faster first drafts; explaining inherited flows; onboarding"],
    ["3", "Your own APIs as governed MCP tools: auth, validation, masking, least privilege",
     "Letting AI agents use existing APIs, BWCE services and on-prem systems safely — without changing them"],
], [1.2, 7.4, 8.4])
para("**Next:** the closing session maps your BWCE practice (CI/CD, monitoring, containers) to Flogo — what you "
     "reuse, what you adapt and what you replace. Appendix B is the one-page summary.")

# ============================================================ APPENDIX A
h1("Appendix A — Mapper cheat-sheet")
para("Type expressions in the mapper without a leading `=`. AI tools writing to the `.flogo` file must add the `=`.")
table(["Need", "Flogo expression", "BW / XPath equivalent"], [
    ["Read an app property", '$property["Risk.HighMm"]', "%%ModuleProperty%% / module property"],
    ["Flow input (REST body)", "$flow.body.siteId", "$Start/root/siteId"],
    ["Path / query parameter", "$flow.pathParams.id  ·  $flow.queryParams.q", "HTTP Receiver params"],
    ["Previous activity output", "$activity[GetForecast].responseBody.daily", "$GetForecast/..."],
    ["Error details", "error branch: $error[Activity].message  ·  Error Handler: $error.message", "$_error/..."],
    ["MCP tool arguments", "$flow.arguments.reportId", "—"],
    ["If / else", 'cond ? "A" : "B"', "if (...) then ... else ..."],
    ["Join strings", 'string.concat("a", $x, "b")', "concat()"],
    ["String length", "string.len($s)", "string-length()"],
    ["Regex match", 'string.matchRegEx("^LR-[0-9]{4}$", $s)', "matches()"],
    ["Regex replace", 'string.replaceRegEx(regex, $s, "[redacted]")', "replace()"],
    ["Upper / lower case", "string.toUpper($s)  ·  string.toLower($s)", "upper-case() / lower-case()"],
    ["Contains", 'string.contains($s, "x")', "contains()"],
    ["Sum an array", "array.sum($arr)", "sum()"],
    ["Count an array", "array.count($arr)", "count()"],
    ["Item in array", 'array.contains($arr, "x")', "$arr = 'x'"],
    ["Now / format a date", 'datetime.now()  ·  datetime.format($d, "RFC3339")', "current-dateTime() / format-dateTime()"],
    ["Type conversion", "coerce.toString($n)  ·  coerce.toInt($s)", "string() / number()"],
    ["JSONPath query", 'json.path("$.items[0].id", $obj)', "XPath predicate"],
    ["jq query", 'json.jq($obj, ".items[] | select(.ok)")', "for-each + filter"],
    ["Object to JSON text", "coerce.toString($obj)  ·  utility.renderJSON($obj, false)", "render-xml / serialize"],
    ["UUID", "utils.uuid()", "tib:uuid()"],
], [4.0, 7.4, 5.6], mono_cols=(1,), size=8.5)
callout("note", "Link types (evaluated in this order)", [
    "1 **Success with condition** (orange) — runs when its expression is true.  "
    "2 **Success with no matching condition** (purple) — runs when no conditional link matched.  "
    "3 **Success** (green) — always on success.  4 **Error** (red) — when the activity fails; `$error` is available.",
])

# ============================================================ APPENDIX B
h1("Appendix B — BWCE → Flogo at a glance")
table(["Area", "In BWCE", "In Flogo", "Verdict"], [
    ["Project & reuse", "Application module, shared modules", "One .flogo app; subflows (same app) in 2.x; shared libraries in 3.x (preview)", "Replace"],
    ["Starter / process", "Process starter, process", "Trigger, flow", "Adapt"],
    ["Configuration", "Module properties, substvars, ConfigMaps", "App properties; env vars, JSON file, Consul, AWS/Azure vaults, K8s; CP app variables", "Adapt"],
    ["Data model", "XML, XSD, WSDL, XPath, XSLT", "JSON, JSON Schema, mapper expressions (90+ functions, json.path/json.jq)", "Replace"],
    ["Errors", "Catch / throw, error transitions", "Error link per activity, flow Error Handler, Retry on Error, Circuit Breaker", "Adapt"],
    ["Transactions", "XA / JTA, compensation", "Not available — design idempotent services; keep XA workloads on BWCE", "Gap"],
    ["Testing", ".bwt unit tests", ".flogotest (mock output/error, JSONPath assertions); flogobuild test-app", "Adapt"],
    ["CI/CD", "bw6-maven-plugin, Jenkins / GitHub Actions", "Same pipeline; flogobuild (build-exe, build-docker-image, build-tp-deployment) + tibcop CLI for Control Plane", "Reuse"],
    ["Containers", "JVM base image + EAR, JVM tuning", "Static Go binary, tiny image; same registry, Helm, HPA", "Reuse"],
    ["Monitoring", "TEA / collectors, dashboards, alerting", "OpenTelemetry traces & metrics, Prometheus /metrics, JSON logs; CP Observability", "Reuse"],
    ["Debugging", "Studio debugger, breakpoints", "App Executions view, unit tests, logs, traces (no breakpoints)", "Adapt"],
    ["Security", "Policies, WS-Security, mTLS", "mTLS, Basic, JWT, OAuth 2.0/JWKS, vault-backed properties (no WS-Security/NTLM)", "Adapt"],
    ["AI / agents", "Tech-preview plug-ins", "MCP Server (GA), AI Agent, LLM, A2A, Design Assistant (Preview)", "New"],
], [2.7, 3.8, 8.6, 1.9], size=8.5)
para("**Keep on BWCE:** SOAP/WSDL services, SAP and deep adapters, XA transactions, complex stateful orchestration, "
     "stable services that just work. **Build on Flogo:** new REST/JSON APIs, event-driven flows, SaaS-to-SaaS, AI "
     "agents and MCP tools. Both on one TIBCO Control Plane with end-to-end OpenTelemetry.", size=9.5)

# ============================================================ APPENDIX C
h1("Appendix C — Glossary")
table(["Term", "Meaning"], [
    ["Activity", "One step in a flow (Log Message, Invoke REST Service, Mapper, Return…)."],
    ["App / .flogo file", "A Flogo application: triggers, flows, properties, schemas and connections in one JSON file."],
    ["App properties", "Named configuration values read with $property[\"...\"], overridable at runtime."],
    ["App Executions", "VS Code view showing each run's path and every activity's input/output."],
    ["Cline", "Open-source AI coding agent for VS Code; acts as the MCP client in Labs 2 and 3."],
    ["FDA", "Flogo Design Assistant (Tech Preview): flogodesign-cli exposed as MCP tools that edit a .flogo file."],
    ["Flow", "The integration logic started by a trigger (BW: process)."],
    ["flogobuild", "CLI used in CI/CD to test and build Flogo apps into executables, images or Control Plane builds."],
    ["Guardrail", "A control that limits what an agent can do or see: auth, validation, PII masking, least privilege."],
    ["JSON Schema", "Describes the shape of JSON data (BW: XSD)."],
    ["Mapper", "Activity and editor for transforming data with expressions (BW: mapper/XPath)."],
    ["MCP", "Model Context Protocol: standard way for AI agents to discover and call tools."],
    ["MCP Server trigger", "Flogo trigger that exposes flows as MCP tools, prompts or resources."],
    ["Streamable HTTP", "The MCP transport over HTTP used in Lab 3 (http://localhost:9090/mcp)."],
    ["stdio", "MCP transport over a child process's stdin/stdout (FDA in Lab 2)."],
    ["Tool annotations", "ReadOnly / Destructive / Idempotent / OpenWorld hints a client uses to decide on approval."],
    ["Trigger", "What starts a flow: REST, Timer, Kafka, MCP Server… (BW: process starter)."],
    ["TIBCO Control Plane", "TIBCO Platform's management plane that deploys and observes Flogo, BWCE, BW5/6 and more."],
], [4.0, 13.0], size=9)

# ============================================================ APPENDIX D
h2("Appendix D — Links")
table(["Resource", "Where"], [
    ["TIBCO Flogo documentation", "https://docs.tibco.com  (search: TIBCO Flogo)"],
    ["Flogo samples (incl. MCP, AI agents, JWT scopes)", "https://github.com/nshah-tibco/flogo-enterprise-hub"],
    ["Open-Meteo forecast API", "https://open-meteo.com/en/docs"],
    ["Model Context Protocol", "https://modelcontextprotocol.io"],
    ["Cline documentation", "https://docs.cline.bot"],
    ["webhook.site", "https://webhook.site"],
], [6.5, 10.5], mono_cols=(1,))

# ============================================================ footer + save
for s in doc.sections:
    fp = s.footer.paragraphs[0]
    fp.text = ""
    r = fp.add_run(LAB["footer"] + "      "); r.font.size = Pt(8); r.font.color.rgb = MUTED
    add_field(fp, "PAGE", "1")
    for rr in fp.runs:
        rr.font.size = Pt(8); rr.font.color.rgb = MUTED
    fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT

doc.save(OUT_DOCX)
print("OK wrote", OUT_DOCX)
for _w in WRAP_WARN:
    print("WRAP WARNING (code line too long):", _w)

if "--nopdf" not in sys.argv:
    import win32com.client
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    try:
        d = word.Documents.Open(OUT_DOCX)
        if d.TablesOfContents.Count:
            d.TablesOfContents(1).Update()
        d.Fields.Update()
        d.Save()
        pages = d.ComputeStatistics(2)  # wdStatisticPages
        d.ExportAsFixedFormat(OUT_PDF, 17)  # wdExportFormatPDF
        d.Close(False)
        print("OK wrote", OUT_PDF, "pages:", pages)
    finally:
        word.Quit()
