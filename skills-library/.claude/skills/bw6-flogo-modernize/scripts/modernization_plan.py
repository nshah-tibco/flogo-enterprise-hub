#!/usr/bin/env python3
"""Write the modernization PLAN the user approves before anything is built.

Reads the analyzer's <Module>.bw6spec.json and writes <Module>.plan.md: what the Flogo app will contain
(triggers, flows, activities, connections, app properties) one to one against the BW6 module, how the XSLT
mappings translate, what Flogo has no direct equivalent for and the workaround, and the decisions/inputs
needed from the user. Every row carries a status:
  verified  proven by a side-by-side parity run in an earlier modernization (references/bw6-to-flogo-patterns.md)
  planned   a documented approach not yet proven by parity - verify it in this run
  decide    needs the user's decision or input before building
  manual    a documented pattern the logic script implements by hand
  unsupported  outside this skill - rebuilt by hand or left in BW

Usage:
  python modernization_plan.py <work>/analysis/<Module>.bw6spec.json [--app-name <Name>] [--mcp explicit|all]
                               [--out <plan.md>]
Standard library only.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_bw6 import ACTIVITY_MAP, RESOURCE_PLAN  # noqa: E402  (single source for BW -> Flogo equivalents)

# BW activity type (or its last segment) -> status of the Flogo translation, from the patterns reference
ACTIVITY_STATUS = {
    "JsonParser": "verified", "JsonRender": "verified", "mapper": "verified", "log": "verified",
    "bwassign": "verified", "JDBCQuery": "verified (SQL Server)", "update": "verified (SQL Server)",
    "SQLDirect": "verified (fixed statements, SQL Server)", "accumulateend": "verified (iterator subflow)",
    "chunk": "verified (openAI extension)", "ingest": "verified (openAI extension)", "query": "verified (openAI extension)",
    "javamethod": "decide", "parsexml": "planned", "sendHTTPRequest": "planned", "Rest": "planned", "sleep": "planned",
}
# XSLT constructs -> Flogo mapping approach
XSLT_PLAN = {
    "xsl:if": ("optional field -> plain mapping + FLOGO_MAPPING_OMIT_NULLS=true; as a test -> link condition", "verified"),
    "xsl:choose": ("ternary `cond ? a : b` at the top level of a mapping, or one branch per outcome (conditional links)", "verified"),
    "xsl:for-each": ("@foreach(source, item[, filter]) array mapping (Logic.select for filtered lookups/joins)", "verified"),
    "xsl:variable": ("Logic.compute(): a mapper of typed derived values, chained when one depends on another", "verified"),
    "xsl:copy-of": ("map the whole object/array (`=$activity[X].output.items`)", "verified"),
    "xsl:attribute": ("JSON property of the same name", "planned"),
    "xsl:for-each-group": ("json.jq grouping or a subflow - no direct mapper construct", "decide"),
    "xsl:sort": ("json.jq `sort_by` in a mapping", "planned"),
    "xsl:call-template": ("inline the template's expression, or a subflow when reused", "planned"),
    "xsl:apply-templates": ("inline mapping per matched element", "decide"),
    "xsl:key": ("Logic.select lookup over the keyed array", "planned"),
}
# XPath / BW (tib:) functions -> Flogo mapper functions (names checked against the Flogo 2.26.9 function catalog)
XPATH_PLAN = {
    "concat": ("string.concat", "verified"), "contains": ("string.contains", "verified"),
    "string-length": ("string.len", "planned"), "substring": ("string.substring (0-based, XPath is 1-based)", "planned"),
    "substring-after": ("string.substringAfter", "planned"), "substring-before": ("string.substringBefore", "planned"),
    "starts-with": ("string.startsWith", "planned"), "ends-with": ("string.endsWith", "planned"),
    "upper-case": ("string.toUpper", "planned"), "lower-case": ("string.toLower", "planned"),
    "normalize-space": ("string.trim", "planned"), "trim": ("string.trim", "planned"),
    "replace": ("string.replaceRegEx", "planned"), "matches": ("string.matchRegEx", "verified"),
    "tokenize": ("string.split", "planned"), "string-join": ("string.join", "planned"),
    "pad-front": ("string.padLeft", "planned"), "pad": ("string.padRight", "planned"),
    "count": ("array.count", "verified"), "sum": ("array.sum", "planned"),
    "string": ("coerce.toString", "verified"), "number": ("coerce.toFloat64", "planned"),
    "decimal": ("coerce.toFloat64", "planned"), "boolean": ("coerce.toBool", "planned"),
    "exists": ("data.isDefined(x) / a link condition `x != nil`", "planned"),
    "empty": ("array.count(x) == 0", "planned"), "not": ("(expr) == false  (the designer rejects unary !)", "verified"),
    "true": ("true", "verified"), "false": ("false", "verified"),
    "current-dateTime": ("datetime.now() / datetime.currentDatetime()", "verified"),
    "current-date": ("datetime.currentDate()", "verified"), "date": ("datetime.parse(x, \"UTC\")", "verified"),
    "dateTime": ("datetime.parse(x, \"UTC\")", "planned"),
    "days-from-duration": ("datetime.diff(a, b, \"days\") + coerce.toInt", "verified"),
    "format-dateTime": ("datetime.format / datetime.formatDatetime", "planned"),
    "abs": ("ternary `x < 0 ? 0 - x : x` (no abs())", "verified"), "round": ("math.round", "planned"),
    "floor": ("math.floor", "planned"), "ceiling": ("math.ceil", "planned"),
    "uuid": ("utils.uuid()", "verified"), "current": ("the outer $loop item (join predicate)", "verified"),
    "position": ("$loop index / array position - restructure", "decide"),
    "base64-to-string": ("string.base64ToString", "verified"), "string-to-base64": ("string.stringToBase64", "planned"),
    "render-json": ("utility.renderJSON(obj, false)", "verified"), "parse-json": ("json functions / coerce.toObject", "planned"),
}


def flogo_app_name(module):
    return re.sub(r"[^A-Za-z0-9]", "", module.title() if module.islower() else module)


def table(rows, header):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c).replace("|", "\\|").replace("\n", " ") for c in r) + " |" for r in rows]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("--app-name", help="Flogo app name (default: the module name without dots)")
    ap.add_argument("--mcp", choices=("explicit", "all"), default="explicit",
                    help="explicit: only operations configured as MCP tools in BW; all: every operation (BW's default "
                         "for modules without MCP configuration)")
    ap.add_argument("--out")
    a = ap.parse_args()
    spec = json.load(open(a.spec, encoding="utf-8"))
    module = spec["module"]
    app = a.app_name or flogo_app_name(module)
    ops = spec["operations"]
    tools = spec["mcp"]["tools"] + spec["mcp"]["resources"]
    implicit = spec["mcp"]["implicitTools"]
    if a.mcp == "all":
        tools_note = "every operation (--mcp all, BW's behaviour for a module without MCP configuration)"
        exposed = [o for o in ops if o.get("flogoFlow")]
    else:
        exposed = [o for o in ops if o["mcp"]["explicit"] and o.get("flogoFlow")]
        tools_note = ("only the operations configured as MCP tools/resources in BW" if tools else
                      f"none - this module has no MCP configuration; BW still exposes its {len(implicit)} operation(s) "
                      "implicitly when its MCP server is on. Use --mcp all to expose them too (can include admin/write "
                      "operations)" if implicit else "none")
    warnings = spec.get("warnings", [])
    L = [f"# Modernization plan: {module} -> Flogo app `{app}`", "",
         "Review this plan. Nothing is built until you approve it (reply **approve**, or tell me what to change).", "",
         "## 1. Scope", ""]
    L += table([
        ("BW6 module", f"`{spec['moduleDir']}`"),
        ("Flogo app", f"`<FLOGO_APPS_DIR>/{app}.flogo` (Flogo 2.x), built with the Flogo Design CLI (fda) only"),
        ("REST operations", f"{len(ops)} (same paths, methods, parameters and JSON bodies)"),
        ("MCP", f"{len(exposed)} tool(s): {tools_note}"),
        ("Ports", f"BW {spec['http']['bwPort']} -> Flogo REST {spec['http']['flogoPort']} (`REST_PORT`), "
                  f"Flogo MCP {spec['mcp']['flogoPort']} (`MCP_PORT`); BW keeps running for side-by-side checks"),
        ("Error replies", f"JSON `{{error, message}}` with {', '.join(spec.get('errorCodes', []))} where BW answers with "
                          "HTML pages / stack traces (reported as IMPROVED, never hidden)"),
    ], ["Item", "Plan"])

    L += ["", "## 2. Triggers", ""]
    trig = [("REST service binding" + (f" ({len(spec['http']['connectors'])} HTTP connector(s))" if spec['http'].get('connectors') else ""),
             "REST trigger (`tr_rest`), one handler per operation, port = app property `REST_PORT`", "verified")]
    if exposed:
        trig.append(("BW MCP server (`-Dbw.enable.mcp.server=true`)",
                     "MCP Server trigger (`tr_mcpserver`, endpoint `/mcp`, port = `MCP_PORT`), one handler per tool", "verified"))
    trig += [(f"{b['type']} binding ({b['service']})", "matching Flogo trigger, built by hand", "unsupported")
             for b in spec.get("otherBindings", [])]
    L += table(trig, ["BW6", "Flogo", "Status"])

    L += ["", "## 3. Flows (one per operation)", ""]
    rows = []
    for o in ops:
        acts = (o.get("implementation") or {}).get("activities", [])
        used = [x for x in acts if x.get("usedByReply", True) and not (x.get("type") or "").startswith("bpws:")]
        mcp = (f"`{o['mcp']['name']}` -> flow `mcp_{re.sub(r'[^A-Za-z0-9_]', '_', o['mcp']['name'])}`"
               if o in exposed else "-")
        rows.append((f"{o['method']} `{o['path']}`", f"`{o.get('flogoFlow') or '?'}`", mcp, len(used),
                     ", ".join(o.get("unusedActivities", [])) or "-"))
    L += table(rows, ["BW operation", "Flogo flow", "MCP tool", "BW activities to translate", "Skipped (nothing reads them)"])
    L += ["", "Each MCP tool is a thin flow that calls the REST flow as a subflow and returns its JSON body, so REST and "
              "MCP answers are identical. Tool names, descriptions and input schemas are copied from BW."]

    L += ["", "## 4. Activities (BW6 -> Flogo, one to one)", ""]
    counts = {}
    for o in ops:
        for x in (o.get("implementation") or {}).get("activities", []):
            if x.get("usedByReply", True) and x.get("type"):
                counts[x["type"]] = counts.get(x["type"], 0) + 1
    rows = []
    for t, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        if t == "bpws:reply":
            rows.append((t, n, "`ConfigureHTTPResponse` + `Return` (one pair per outcome/status)", "verified"))
            continue
        if t == "bpws:invoke":
            rows.append((t, n, "`act_general_rest` (Invoke REST) to the same service; base URL as an app property", "planned"))
            continue
        key = t if t in ACTIVITY_MAP else t.split(".")[-1]
        flogo, level, note = ACTIVITY_MAP.get(key, ("?", "review", "no known Flogo equivalent"))
        st = ACTIVITY_STATUS.get(t.split(".")[-1], "decide" if level in ("hard", "review") else "planned")
        rows.append((f"`{t}`", n, f"{flogo} - {note}", st))
    L += table(rows, ["BW6 activity", "Count", "Flogo", "Status"]) if rows else ["(no activities)"]

    L += ["", "## 5. Connections and shared resources", ""]
    rows = []
    for r in spec["sharedResources"]:
        k = r["kind"]
        if k == "httpConnResource":
            rows.append((f"`{r['name']}` (HTTP connector)", "REST trigger settings (port via `REST_PORT`)", "verified"))
        elif k == "jdbcResource":
            db = r.get("database") or "unknown"
            rows.append((f"`{r['name']}` (JDBC, {db})", f"Flogo `{db}` connection; user/password from you, password stored as `SECRET:`",
                         "verified" if db == "sqlserver" else "decide"))
        elif k in ("xsd", "json", "wsdl"):
            continue
        else:
            flogo, st = RESOURCE_PLAN.get(k, ("no known equivalent - matching Flogo connector or user extension", "decide"))
            rows.append((f"`{r['name']}` ({k})", flogo, st))
    L += table(rows, ["BW6", "Flogo", "Status"]) if rows else ["(none)"]

    L += ["", "## 6. App properties", ""]
    rows = [("`REST_PORT`", "number", spec["http"]["flogoPort"], "REST trigger port"),
            ("`MCP_PORT`", "string", spec["mcp"]["flogoPort"], "MCP trigger port (the trigger field is a string)")] if exposed else \
           [("`REST_PORT`", "number", spec["http"]["flogoPort"], "REST trigger port")]
    for mp in spec.get("moduleProperties", []):
        t = (mp.get("type") or "string").lower()
        ft = "string (SECRET:)" if mp.get("secret") or t == "password" else \
             {"integer": "number", "long": "number", "int": "number", "boolean": "boolean"}.get(t, "string")
        vals = mp.get("profiles") or {}
        rows.append((f"`{mp['name']}`", ft, vals.get("default", next(iter(vals.values()), "")), "BW module property"))
    for r in spec["sharedResources"]:
        if r["kind"] == "jdbcResource":
            rows.append((f"connection `{r['name']}` settings", "host, port, database, user, password",
                         "from the BW JDBC URL + you (password as `SECRET:`)", "database connection"))
    L += table(rows, ["Property", "Type", "Value", "Purpose"])
    L += ["", "Override any property at run time with `FLOGO_APP_PROPS_ENV=auto <NAME>=<value>`."]

    L += ["", "## 7. Mappings (BW XSLT -> Flogo mappings)", "",
          "BW maps data with XSLT; Flogo maps with expressions. The analyzer decodes every XSLT the operations run "
          "(`<Module>.report.md`, per operation), and each mapping is rebuilt field by field with the Flogo Design CLI "
          "(`fda mm`) in the logic script - nothing is pasted as a blob. Hardcoded data the BW process returns "
          "(JSON literals) is loaded into typed mappers so both apps serve the same records. Constructs found in this module:", ""]
    feats, funcs = {}, {}
    for o in ops:
        for k, v in (o.get("xsltFeatures") or {}).items():
            feats[k] = feats.get(k, 0) + v
        for k, v in (o.get("xpathFunctions") or {}).items():
            funcs[k] = funcs.get(k, 0) + v
    rows = [("`<xsl:value-of>` paths / literals", "-", "direct mapping `=$flow.queryParams.x`, `=$flow.body.x`, "
             "`=$activity[X].output.y`, or a literal", "verified")]
    rows += [(f"`<{k}>`", n, *XSLT_PLAN.get(k, ("no rule yet", "decide"))) for k, n in sorted(feats.items(), key=lambda kv: -kv[1])]
    L += table(rows, ["XSLT construct", "Uses", "Flogo", "Status"])
    if funcs:
        L += [""]
        rows = [(f"`{k}()`", n, *XPATH_PLAN.get(k.split(":")[-1], ("no known equivalent - mapping function or extension", "decide")))
                for k, n in sorted(funcs.items(), key=lambda kv: -kv[1])]
        L += table(rows, ["XPath / BW function", "Uses", "Flogo function", "Status"])
    lits = sum(len(o.get("literals", [])) for o in ops)
    if lits:
        L += ["", f"{lits} hardcoded literal value(s) in the BW mappings are kept as literals (per operation, from that "
                  "operation's own XSLT)."]

    L += ["", "## 8. Not directly available in Flogo - workaround", ""]
    L += table([(w["area"], w["item"], w["impact"], w["workaround"], w["status"]) for w in warnings],
               ["Area", "Item", "Impact", "Workaround", "Status"]) if warnings else \
        ["Nothing: every construct in this module has a known Flogo equivalent."]

    L += ["", "## 9. Inputs and decisions needed from you", ""]
    asks = [f"Confirm the app name `{app}` and the ports (REST {spec['http']['flogoPort']}, MCP {spec['mcp']['flogoPort']}).",
            f"MCP exposure: {tools_note}. Keep it?" if exposed or implicit else None,
            "Is the BW6 app running (needed for the side-by-side parity check)? Its base URL"
            + (" and its MCP endpoint (BW MCP server host:port)" if exposed else "") + "."]
    for r in spec["sharedResources"]:
        if r["kind"] == "jdbcResource":
            asks.append(f"Database for `{r['name']}`: same database as BW or a copy? User/password for the Flogo app "
                        "(BW's is obfuscated). May the tests write tagged fixture rows (deleted afterwards) and run "
                        "destructive operations (resets)?")
    asks += [f"{w['item']}: {w['workaround']}" for w in warnings if w["status"] == "decide"
             and "credentials" not in w["item"]]
    asks.append("Should I build and run the app (flogobuild) after generating it, or only generate the .flogo?")
    L += [f"{i}. {q}" for i, q in enumerate([q for q in asks if q], 1)]

    L += ["", "## 10. How it will be verified", "",
          "- `fda cm` (mapping rules) and the designer-load gate (no activity lost when you open the app).",
          "- Side-by-side parity: the same requests to BW and Flogo - happy paths, missing/empty parameters, unknown ids, "
          "every MCP tool incl. not-found calls. Done = 0 MISMATCH; IMPROVED/ACCEPTED/SEMANTIC differences are listed.",
          "- If an AI orchestrator uses these tools: its scenarios replayed with the tools served by Flogo.", "",
          "**Reply `approve` to build, or tell me what to change.**"]

    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.spec)), re.sub(r"\.bw6spec\.json$", "", os.path.basename(a.spec)) + ".plan.md")
    open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(f"plan: {out}  ({len(ops)} operations, {len(warnings)} gap(s), "
          f"{sum(1 for w in warnings if w['status'] == 'decide')} decision(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
