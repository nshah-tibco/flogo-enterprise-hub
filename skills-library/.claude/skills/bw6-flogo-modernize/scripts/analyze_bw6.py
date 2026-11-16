#!/usr/bin/env python3
"""Analyze a TIBCO BusinessWorks 6 REST project and write a modernization spec for Flogo.

Reads (never writes) a BW6 module folder -- the one holding META-INF/module.bwm -- and emits:

  <out>/<Module>.bw6spec.json   what the module exposes and does: REST operations, parameters,
                                MCP tool/resource names, HTTP port, shared resources, and per
                                operation the activities and decoded XSLT mappings it runs.
  <out>/<Module>.openapi.json   the module's own OpenAPI descriptor, made Flogo-ready: one merged
                                document, readable operationIds (the MCP tool name when there is
                                one), and the server port moved by --port-offset.
  <out>/<Module>.report.md      a human-readable summary with a modernization checklist.

Usage:
  python analyze_bw6.py <bw6-module-dir> [--out <dir>] [--port-offset 1000]

Standard library only. Exits 2 when the folder is not a BW6 module.
"""
import argparse
import copy
import glob
import html
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

# BW6 activity type id -> (Flogo equivalent, difficulty, note). Unknown types are flagged "review".
ACTIVITY_MAP = {
    "bw.restjson.JsonParser": ("act_general_parsejson", "easy", "Parse JSON"),
    "bw.restjson.JsonRender": ("utility.renderJSON() / mapper", "easy", "Render JSON = serialize in a mapping"),
    "bw.generalactivities.mapper": ("act_general_mapper", "easy", "Mapper"),
    "bw.generalactivities.log": ("act_general_log", "easy", "Log"),
    "bw.generalactivities.parsexml": ("act_general_xmltojson", "medium", "XML parse"),
    "parsexml": ("act_general_xmltojson", "medium", "XML parse"),
    "bw.generalactivities.sleep": ("act_general_sleep", "easy", "Sleep"),
    "bw.jdbc.JDBCQuery": ("act_<db>_query", "medium", "SQL query via the matching Flogo DB connector"),
    "bw.jdbc.update": ("act_<db>_insert/update/delete", "medium", "SQL update via the matching Flogo DB connector"),
    "bw.jdbc.SQLDirect": ("act_<db>_query (SQL direct)", "medium", "Direct SQL"),
    "bw.http.sendHTTPRequest": ("act_http_client / act_general_rest", "easy", "HTTP client"),
    "bw.restjson.Rest": ("act_general_rest", "easy", "Invoke REST API"),
    "bw.java.javamethod": ("mapper functions or a Flogo Go extension", "hard", "Java code: re-express as mapping or write an extension"),
    "javamethod": ("mapper functions or a Flogo Go extension", "hard", "Java code: re-express as mapping or write an extension"),
    "bw.rag.chunk": ("OpenAI vector store file upload (repo extensions/openAI; chunking done by OpenAI) - or Agentic AI "
                     "ChunkAndEmbedDocuments", "hard", "RAG chunking"),
    "bw.rag.ingest": ("OpenAI vector store via repo extensions/openAI (verified) - or ActiveSpaces vector activities / "
                      "REST to the vector DB", "hard", "RAG ingest"),
    "bw.rag.query": ("openAI vectorSearch + Agentic AI LLM Client answer (verified) - or REST to the vector DB + LLM",
                     "hard", "RAG query"),
    "accumulateend": ("iterator / @foreach mapping", "medium", "BW accumulate loop"),
    "bwassign": ("mapper", "easy", "Assign"),
}

NS = {
    "sca": "http://docs.oasis-open.org/ns/opencsa/sca/200912",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
    "bpws": "http://docs.oasis-open.org/wsbpel/2.0/process/executable",
    "tibex": "http://www.tibco.com/bpel/2007/extensions",
}
XSI_TYPE = "{%s}type" % NS["xsi"]


def local(tag):
    return tag.rsplit("}", 1)[-1]


def read(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def slug(text):
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")


def decode_xslt(expr):
    """Turn an HTML-encoded XSLT inputBinding into a compact, readable form."""
    x = html.unescape(expr)
    x = re.sub(r"<\?xml[^>]*\?>", "", x)
    x = re.sub(r'\sxmlns(:\w+)?="[^"]*"', "", x)
    x = re.sub(r"</?xsl:stylesheet[^>]*>", "", x)
    # string literals first: select="'...'" may itself contain double quotes (embedded JSON)
    x = re.sub(r"""<xsl:value-of select="'(.*?)'"\s*/>""", lambda m: "{'" + m.group(1) + "'}", x, flags=re.S)
    x = re.sub(r"\s+", " ", x)
    x = re.sub(r'<xsl:value-of select="([^"]*)"\s*/>', r"{\1}", x)
    x = re.sub(r"<(?:\w+:)?(\w+)>\s*\{([^}]*)\}\s*</(?:\w+:)?\1>", r"\1={\2}; ", x)
    x = re.sub(r"\b[a-z]+\d*:(?=[A-Za-z])(?!xsl:)", "", x)  # drop tns5: style prefixes, keep xsl:
    return x.strip()


def string_literals(xslt):
    """Quoted literals in select="..." expressions = hardcoded data the BW process returns."""
    out = []
    for m in re.finditer(r"\{'((?:[^'\\]|\\.)*)'\}", xslt):
        out.append(m.group(1))
    return out


# ----------------------------------------------------------------------------------------------
# module.bwm: services, REST bindings, operations, MCP tools
# ----------------------------------------------------------------------------------------------
def parse_module(module_dir):
    bwm = os.path.join(module_dir, "META-INF", "module.bwm")
    root = ET.fromstring(read(bwm).encode("utf-8"))
    services, components = [], []
    for el in root.iter():
        tag = local(el.tag)
        if tag == "service" and el.get("promote"):
            services.append(el)
        elif tag == "component":
            components.append(el)

    ops, other_bindings = [], []
    for svc in services:
        for binding in svc:
            if local(binding.tag) != "binding":
                continue
            if "RestServiceBinding" not in (binding.get(XSI_TYPE) or ""):
                # SOAP, JMS ... service bindings: reported in the plan, not built by this skill
                other_bindings.append({"service": svc.get("name"), "type": (binding.get(XSI_TYPE) or "?").split(":")[-1]})
                continue
            raw_path = html.unescape(binding.get("path", ""))
            path, _, query_tpl = raw_path.partition("?")
            for op in binding:
                if local(op.tag) != "operation":
                    continue
                params = []
                for pm in op.iter():
                    if local(pm.tag) == "parameterMapping":
                        params.append({"name": pm.get("parameterName"), "in": (pm.get("parameterType") or "").lower(),
                                       "required": pm.get("required") == "true"})
                # With -Dbw.enable.mcp.server=true BW exposes EVERY REST operation as an MCP tool named
                # after the operation nickname, described by its notes. Operations someone configured on
                # the binding's MCP tab carry tool="true"/resource="true" and may have a nested
                # <restMcpTool>/<restMcpResource> that overrides name/scope/description. "explicit" marks
                # those; the builder exposes only explicit ones unless asked for exact BW parity.
                explicit = op.get("tool") == "true" or op.get("resource") == "true"
                mcp = {"kind": "resource" if op.get("resource") == "true" else "tool", "name": op.get("nickname"),
                       "scope": None, "description": op.get("notes"), "explicit": explicit}
                for child in op:
                    t = local(child.tag)
                    if t in ("restMcpTool", "restMcpResource"):
                        mcp = {"kind": "tool" if t == "restMcpTool" else "resource",
                               "name": child.get("name") or op.get("nickname"), "scope": child.get("scope"),
                               "description": child.get("description") or op.get("notes"), "explicit": True}
                ops.append({
                    "service": svc.get("name"),
                    "component": (svc.get("promote") or "").split("/")[0],
                    "bindingName": binding.get("name"),
                    "path": path or "/",
                    "queryTemplate": query_tpl or None,
                    "basePath": binding.get("basePath", "/"),
                    "method": (op.get("httpMethod") or "").upper(),
                    "operationName": op.get("operationName"),
                    "nickname": op.get("nickname"),
                    "notes": op.get("notes"),
                    "connector": binding.get("connector"),
                    "openapiFile": binding.get("implementation"),
                    "params": params,
                    "mcp": mcp,
                })
    props = [{"name": p.get("name"), "type": p.get("type")} for p in root.iter()
             if local(p.tag) == "property" and not (p.get("name") or "").startswith("BW.")]
    references = []
    for el in root.iter():
        if local(el.tag) == "reference" and el.get("name"):
            kinds = [(b.get(XSI_TYPE) or "?").split(":")[-1] for b in el if local(b.tag) == "binding"]
            references.append({"name": el.get("name"), "promote": el.get("promote"), "bindings": kinds})
    comps = []
    for c in components:
        for impl in c:
            if local(impl.tag) == "implementation":
                comps.append({"name": c.get("name"), "processName": impl.get("processName")})
    return ops, props, comps, other_bindings, references


def parse_substvars(module_dir):
    """Module property values: META-INF/default.substvar (+ any other *.substvar profile). BW.* built-ins skipped."""
    out = {}
    for f in sorted(glob.glob(os.path.join(module_dir, "META-INF", "*.substvar"))):
        prof = os.path.splitext(os.path.basename(f))[0]
        for gv in ET.fromstring(read(f).encode("utf-8")).iter():
            if local(gv.tag) != "globalVariable":
                continue
            val = {local(c.tag): (c.text or "") for c in gv}
            name = val.get("name", "").split("//")[-1]
            if not name or name.startswith("BW."):
                continue
            secret = val.get("type", "").lower() == "password" or bool(SECRETISH.search(name))
            entry = out.setdefault(name, {"type": val.get("type"), "profiles": {}, "secret": secret})
            entry["profiles"][prof] = "<set>" if secret and val.get("value") else val.get("value")
    return out


# XSLT constructs and functions an operation's mappings use -> the "mappings" part of the plan
# decode_xslt() drops namespace prefixes, so decoded text has <if>, <for-each> ... (no "xsl:")
XSLT_FEATURES = re.compile(r"<(?:xsl:)?(if|choose|for-each-group|for-each|variable|copy-of|attribute|sort|call-template|"
                           r"apply-templates|key)\b")
XPATH_FUNCS = re.compile(r"\b((?:tib|fn|xs|bw|exsl|xsd):[A-Za-z][\w-]*|[a-z][a-z-]*[a-z])\(")
XPATH_IGNORE = {"and", "or", "if", "then", "else", "return", "for", "some", "every", "text", "node"}


def xslt_features(xslts):
    feats, funcs = {}, {}
    for x in xslts:
        for m in XSLT_FEATURES.findall(x):
            feats["xsl:" + m] = feats.get("xsl:" + m, 0) + 1
        for m in XPATH_FUNCS.findall(re.sub(r"'[^']*'", "''", x)):
            if m not in XPATH_IGNORE:
                funcs[m] = funcs.get(m, 0) + 1
    return feats, funcs


def jdbc_kind(settings):
    """Database product from a JDBC shared resource's driver / URL (None when unknown)."""
    blob = (settings.get("dbURL", "") + " " + settings.get("jdbcDriver", "")).lower()
    for key, kind in (("sqlserver", "sqlserver"), ("postgres", "postgres"), ("redshift", "postgres"), ("mysql", "mysql"),
                      ("mariadb", "mysql"), ("oracle", "oracle"), ("db2", "db2"), ("snowflake", "snowflake")):
        if key in blob:
            return kind
    return None


# ----------------------------------------------------------------------------------------------
# shared resources: HTTP connector port, HTTP clients, JDBC, RAG ...
# ----------------------------------------------------------------------------------------------
SECRETISH = re.compile(r"(?i)(password|key|token|secret)")


def parse_resources(module_dir):
    res = []
    for f in sorted(glob.glob(os.path.join(module_dir, "Resources", "**", "*.*"), recursive=True)):
        if os.path.isdir(f):
            continue
        t = read(f)
        kind = os.path.splitext(f)[1].lstrip(".")
        attrs = {}
        for k, v in re.findall(r'\s(\w+)="([^"]*)"', t):
            if k in ("id", "version", "encoding", "type", "name") or k.startswith("xmlns"):
                continue
            if SECRETISH.search(k):
                v = "<set>" if v else ""
            attrs.setdefault(k, v)
        # <substitutionBindings template="port" propName="//Module//HTTP_PORT"/>: setting bound to a module property
        bound = {m.group(1): m.group(2).split("//")[-1]
                 for m in re.finditer(r'<substitutionBindings[^>]*template="([^"]+)"[^>]*propName="([^"]+)"', t)}
        res.append({"file": os.path.relpath(f, module_dir).replace("\\", "/"), "kind": kind,
                    "name": os.path.splitext(os.path.basename(f))[0],
                    "settings": {k: v for k, v in attrs.items() if v not in ("", "false", "0")
                                 and k not in ("template", "propName")},
                    "propertyBound": bound})
    return res


# ----------------------------------------------------------------------------------------------
# .bwp processes: per onMessage(operation, partnerLink) -> activities + XSLT
# ----------------------------------------------------------------------------------------------
def sql_of(el):
    """SQL text configured on a JDBC activity (attribute or element named like 'statement')."""
    for sub in el.iter():
        for k, v in sub.attrib.items():
            if local(k).lower() in ("statement", "sqlstatement", "statements") and v.strip():
                return re.sub(r"\s+", " ", html.unescape(v)).strip()
        if local(sub.tag).lower() in ("statement", "sqlstatement") and (sub.text or "").strip():
            return re.sub(r"\s+", " ", html.unescape(sub.text)).strip()
    return None


def element_refs(el):
    """Every '$Name' an activity element mentions: XSLT params/selects AND configuration (e.g. what an
    accumulate end collects), so dependencies hidden in configuration are not mistaken for dead code."""
    text = " ".join(v for d in el.iter() for v in list(d.attrib.values()) + [d.text or ""])
    return sorted(set(re.findall(r"\$([A-Za-z_][\w-]*)", html.unescape(text))))


def parse_process(bwp_path):
    t = read(bwp_path)
    root = ET.fromstring(t.encode("utf-8"))
    parent = {c: p for p in root.iter() for c in p}
    branches = []
    # BW's own dependency summary: <task name="X"><endingVariables><variable>V</variable>... lists what each
    # task (activity or group) reads. Groups (Iterate, accumulate loops) appear here as tasks too.
    ending = {}
    for el in root.iter():
        if local(el.tag) == "task" and el.get("name"):
            ending[el.get("name")] = {(v.text or "").strip() for v in el.iter() if local(v.tag) == "variable" and v.text}

    def links_in(node):
        """bpws links inside node as {name, from, to, condition}. A link's <source>/<target> sit in
        <sources>/<targets> directly under the named activity element."""
        src, dst = {}, {}
        for el in node.iter():
            tag = local(el.tag)
            if tag in ("source", "target") and el.get("linkName"):
                owner = parent.get(parent.get(el))
                name = owner.get("name") if owner is not None else None
                if tag == "source":
                    cond = next((c.text for c in el.iter() if local(c.tag) == "transitionCondition"), None)
                    src[el.get("linkName")] = (name, (cond or "").strip() or None)
                else:
                    dst[el.get("linkName")] = name
        return [{"name": ln, "from": f, "to": dst.get(ln), "condition": c} for ln, (f, c) in src.items()]

    def walk_activities(node):
        acts = []
        for el in node.iter():
            tag = local(el.tag)
            if tag == "activityExtension":
                type_id = None
                for sub in el.iter():
                    if sub.get("activityTypeID"):
                        type_id = sub.get("activityTypeID")
                        break
                xslts = [decode_xslt(b.get("expression", "")) for b in el.iter()
                         if local(b.tag) in ("inputBinding", "partBinding") and b.get("expression")]
                act = {"name": el.get("name"), "type": type_id, "inputXslt": xslts, "refs": element_refs(el)}
                if "jdbc" in (type_id or "").lower():
                    act["sql"] = sql_of(el)
                acts.append(act)
            elif tag in ("reply", "invoke") and el.get("operation"):
                xslts = [decode_xslt(b.get("expression", "")) for b in el.iter()
                         if local(b.tag) in ("inputBinding", "partBinding") and b.get("expression")]
                acts.append({"name": el.get("name"), "type": "bpws:" + tag, "operation": el.get("operation"),
                             "partnerLink": el.get("partnerLink"), "inputXslt": xslts, "refs": element_refs(el)})
        return acts

    def external_refs(node, acts):
        """{activity: True} when '$<activity>' appears in the branch XML outside every activity element."""
        names = {a["name"] for a in acts}
        owners = {}
        for el in node.iter():
            if local(el.tag) in ("activityExtension", "reply", "invoke") and el.get("name") in names:
                owners[el.get("name")] = el
        # Text outside every activity element: group/iterate 'over' expressions, accumulate settings, link
        # conditions. References made INSIDE another activity are handled by mark_used's dependency walk.
        # (Walk the tree; string-replacing serialized sub-elements fails because ElementTree re-prefixes namespaces.)
        inside = {d for el in owners.values() for d in el.iter()}
        chunks = []
        for el in node.iter():
            if el in inside:
                continue
            chunks += [v for v in el.attrib.values()] + [el.text or "", el.tail or ""]
        outside = html.unescape(" ".join(chunks))
        return {n: bool(re.search(r"\$" + re.escape(n) + r"(?![\w-])", outside)) for n in names}

    for om in root.iter():
        if local(om.tag) == "onMessage":
            acts = walk_activities(om)
            refs = external_refs(om, acts)
            names = {a["name"] for a in acts}
            in_branch = {el.get("name") for el in om.iter() if el.get("name")}
            groups = sorted(n for n in in_branch if n in ending and n not in names)
            for a in acts:
                a["referencedElsewhere"] = refs.get(a["name"], False)
                a["endingVariables"] = sorted(ending.get(a["name"], set()))
            branches.append({"operation": om.get("operation"), "partnerLink": om.get("partnerLink"),
                             "activities": acts, "links": links_in(om),
                             "groups": {g: sorted(ending[g]) for g in groups}})
    def constructs(node):
        """BPEL/BW structures that need a decision in Flogo (fault handling, loops, outbound calls, starters)."""
        c = {}
        for el in node.iter():
            t = local(el.tag)
            key = None
            if t in ("catch", "catchAll", "throw", "rethrow", "repeatUntil", "while", "compensate", "eventHandlers",
                     "receiveEvent", "terminate", "exit", "wait"):
                key = t
            elif t == "forEach":
                key = "iterate group" if el.get("group") == "iterate" else "forEach"
            elif t == "scope" and el.get("group") and el.get("group") != "iterate":
                key = "group:" + el.get("group")
            elif t == "invoke" and el.get("partnerLink"):
                key = "invoke (outbound call)"
            elif t == "activityExtension":
                ty = next((x.get("activityTypeID") for x in el.iter() if x.get("activityTypeID")), "") or ""
                if re.search(r"(?i)callprocess|subprocess", ty):
                    key = "call process"
                elif re.search(r"(?i)(timer|receive|subscriber|listener|poller|receiver|starter)", ty):
                    key = "starter:" + ty
            if key:
                c[key] = c.get(key, 0) + 1
        return c

    for b in branches:
        om = next((el for el in root.iter() if local(el.tag) == "onMessage" and el.get("operation") == b["operation"]
                   and el.get("partnerLink") == b["partnerLink"]), None)
        b["constructs"] = constructs(om) if om is not None else {}
    if not branches:  # single receive-style process
        branches.append({"operation": None, "partnerLink": None, "activities": walk_activities(root),
                         "links": links_in(root), "constructs": constructs(root)})
    return branches, constructs(root)


# Activities that change something outside the process (DB writes, outbound calls, sends, files). They run for
# their effect, so they are never "dead" even when the reply ignores their output.
SIDE_EFFECT = re.compile(r"(?i)(jdbc\.update|SQLDirect|JDBCUpdate|jdbc\.call|sendHTTPRequest|\bhttp|restjson\.Rest$|"
                         r"\.rest\.|invoke|file\.(write|create|remove|rename|copy)|jms|ems|kafka|mail|ftp|callprocess|"
                         r"rag\.ingest|\.publish|\.send)")
# Activities whose purity can't be judged from metadata: report them for review instead of calling them dead.
REVIEW = re.compile(r"(?i)(javamethod|java\.|invokejava|custom)")


def mark_used(acts, links=(), groups=None):
    """Flag activities nothing depends on. A BW XSLT declares <xsl:param name="X"/> for every variable it reads;
    starting from the reply AND every side-effecting activity (DB writes, calls, sends), follow those params
    transitively. What is left is pure work whose result is thrown away (e.g. a parse nobody reads) and needs
    no Flogo equivalent. Java invokes are only marked 'review': read the source to confirm they are pure."""
    by_name = {a["name"]: a for a in acts}
    reads = {a["name"]: ({p for x in a["inputXslt"] for p in re.findall(r'<param name="([^"]+)"', x)}
                         | set(a.get("refs", [])) | set(a.get("endingVariables", []))) for a in acts}
    for g, deps in (groups or {}).items():      # group tasks (loops/accumulates) are live control structures
        reads[g] = set(deps)
    todo = [a["name"] for a in acts if (a.get("type") or "").startswith("bpws:") or SIDE_EFFECT.search(a.get("type") or "")
            or a.get("referencedElsewhere")] + list(groups or {})
    # activities read by a transition condition steer the control flow, so they are used too
    for link in links:
        cond = html.unescape(link.get("condition") or "")
        todo += [n for n in re.findall(r"\$([A-Za-z_][\w-]*)", cond) if n in by_name]
    used = set(todo)
    while todo:
        for dep in reads.get(todo.pop(), ()):
            if dep in by_name and dep not in used:
                used.add(dep)
                todo.append(dep)
    for a in acts:
        a["usedByReply"] = a["name"] in used
        a["sideEffect"] = bool(SIDE_EFFECT.search(a.get("type") or ""))
        a["reviewPurity"] = (not a["usedByReply"]) and bool(REVIEW.search(a.get("type") or ""))


# ----------------------------------------------------------------------------------------------
# OpenAPI: merge descriptors, rename operationIds, shift port
# ----------------------------------------------------------------------------------------------
# BW shared resource kind -> (Flogo equivalent, status). Unknown kinds need a decision.
RESOURCE_PLAN = {
    "httpConnResource": ("REST trigger settings (port via the REST_PORT app property)", "verified"),
    "jdbcResource": ("Flogo database connection for that product (host/port/database from the JDBC URL; user/password "
                     "from the user, password as SECRET:)", "verified for SQL Server"),
    "httpClientResource": ("Invoke REST (act_general_rest) settings: base URL as an app property <NAME>_URL built "
                           "from the resource's host/port; timeouts/TLS on the activity", "planned"),
    "ragResource": ("OpenAI vector store via repo extensions/openAI (API key placeholder property + env var at run "
                    "time, store found by name) + Agentic AI LLM Client", "verified"),
    "jmsConnResource": ("Flogo TIBCO EMS / JMS connection", "planned"),
    "kafkaConnResource": ("Flogo Apache Kafka connection", "planned"),
    "sslClientResource": ("TLS settings on the Flogo connection / Invoke REST activity", "planned"),
    "sslServerResource": ("TLS settings on the REST trigger", "planned"),
    "ftlRealmServerResource": ("Flogo TIBCO FTL connection", "planned"),
    "smtpResource": ("Flogo email (SMTP) activity settings", "planned"),
    "keystoreProviderResource": ("certificates as app properties / connection fields", "planned"),
}

# Error responses declared on every operation. The designer's httpresponse "Code" dropdown only offers codes
# declared for the operation, so every code a logic script may answer with must be listed here.
ERROR_CODES = (("400", "Invalid or missing input"), ("403", "Not allowed"), ("404", "Requested item not found"),
               ("409", "Conflict with the current state"), ("422", "Request understood but cannot be processed"),
               ("500", "Unexpected error"))


def flogo_openapi(module_dir, ops, http_port, offset, error_codes=ERROR_CODES, flavours=None):
    files = sorted({o["openapiFile"] for o in ops if o.get("openapiFile")})
    merged = None
    for rel in files:
        p = os.path.join(module_dir, rel)
        if not os.path.exists(p):
            continue
        d = json.loads(read(p))
        if flavours is not None:
            flavours[rel] = "swagger " + str(d["swagger"]) if "swagger" in d else "openapi " + str(d.get("openapi", "?"))
        if merged is None:
            merged = copy.deepcopy(d)
            merged["paths"] = {}
            merged.setdefault("components", {}).setdefault("schemas", {})
        for path, item in d.get("paths", {}).items():
            merged["paths"].setdefault(path, {}).update(item)
        merged["components"]["schemas"].update(d.get("components", {}).get("schemas", {}))
    if merged is None:
        return None, {}
    renames = {}
    used = set()
    for o in ops:
        item = merged["paths"].get(o["path"], {}).get(o["method"].lower())
        if item is None:
            continue
        base = slug(o["mcp"]["name"] if o["mcp"]["explicit"] else f"{o['method'].lower()}_{o['path']}")
        new = base
        i = 2
        while new in used:
            new = f"{base}_{i}"
            i += 1
        used.add(new)
        renames[item.get("operationId")] = new
        item["operationId"] = new
        o["flogoFlow"] = new
        # BW answers bad input / missing data with HTML pages or Java stack traces (HTTP 400/500).
        # The Flogo app answers with JSON instead, so declare the error codes up front: cas turns
        # each declared response into a row of the trigger's response-code table.
        for code, desc in error_codes:
            item.setdefault("responses", {}).setdefault(code, {
                "description": desc,
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}})
    merged["components"]["schemas"].setdefault("ErrorResponse", {
        "type": "object",
        "properties": {"error": {"type": "string"}, "message": {"type": "string"}}})
    if http_port:
        merged["servers"] = [{"url": f"http://localhost:{int(http_port) + offset}/"}]
    return merged, renames


def gap_warnings(spec, openapi):
    """Everything in this module that the skill does NOT build automatically, with the intended workaround.
    status: 'manual' = you write it in the logic script with a documented pattern; 'decide' = needs the user's
    decision before building; 'unsupported' = outside this skill (rebuild by hand / later version)."""
    W = []

    def add(area, item, impact, workaround, status):
        W.append({"area": area, "item": item, "impact": impact, "workaround": workaround, "status": status})

    ops = spec["operations"]
    if not spec["http"]["bwPort"]:
        add("Trigger", "BW HTTP port not found (property-bound without a default?)", "ports cannot be derived",
            "re-run with --bw-port <port>", "decide")
    if len(spec["http"]["connectors"]) > 1:
        add("Trigger", f"{len(spec['http']['connectors'])} HTTP connectors "
            f"({', '.join(str(c['name']) + ':' + str(c['port']) for c in spec['http']['connectors'])})",
            "the scaffold builds ONE Flogo REST trigger on one port", "split the module per connector, or accept one port", "decide")
    for b in spec["otherBindings"]:
        add("Trigger", f"non-REST service binding {b['type']} on service {b['service']}", "not built",
            "rebuild with the matching Flogo trigger (SOAP, JMS/EMS, Kafka ...) by hand", "unsupported")
    for o in ops:
        name = o.get("flogoFlow") or o.get("nickname")
        if not o.get("flogoFlow"):
            add("Operation", f"{o['method']} {o['path']} has no matching path in the OpenAPI descriptor",
                "the scaffold cannot create its flow", "fix/regenerate the BW service descriptor, then re-analyze", "decide")
        if o.get("basePath") not in (None, "", "/"):
            add("Operation", f"{name}: binding basePath {o['basePath']}", "Flogo paths come from the descriptor only",
                "prefix the paths in the Flogo-ready OpenAPI before scaffolding", "manual")
        if any(p["in"] == "header" for p in o["params"]):
            add("Operation", f"{name}: header parameter(s) {', '.join(p['name'] for p in o['params'] if p['in'] == 'header')}",
                "not wired by the scaffold", "map $flow.headers.<name> in the logic script (tr_rest handler headers schema)", "manual")
        impl = o.get("implementation") or {}
        if not impl:
            add("Operation", f"{name}: no BW process branch found", "no logic to translate", "check the component/process wiring", "decide")
        for c, n in (impl.get("constructs") or {}).items():
            how = {
                "catch": ("fault handler", "error branch / flow error handler reading $error", "manual"),
                "catchAll": ("fault handler", "error branch / flow error handler reading $error", "manual"),
                "throw": ("explicit fault", "JSON error reply (400/403/404/409/422) on that branch", "manual"),
                "rethrow": ("re-thrown fault", "JSON 500 error reply", "manual"),
                "invoke (outbound call)": ("calls another service", "act_general_rest / act_http_client to the same URL (property for the base URL)", "manual"),
                "call process": ("sub-process call", "Logic.subflow + Logic.call (act_default_subflow)", "manual"),
                "iterate group": ("loop", "Logic.subflow + Logic.call(iterate=...) or a @foreach mapping", "manual"),
                "forEach": ("loop", "Logic.subflow + Logic.call(iterate=...) or a @foreach mapping", "manual"),
                "repeatUntil": ("loop with exit condition", "doWhile-style subflow loop (references: retry pattern)", "manual"),
                "while": ("loop with exit condition", "doWhile-style subflow loop", "manual"),
                "eventHandlers": ("event handler", "no Flogo equivalent - redesign", "unsupported"),
                "compensate": ("compensation", "no Flogo equivalent - explicit undo steps", "unsupported"),
                "wait": ("wait/sleep", "act_general_sleep", "manual"),
            }.get(c) or (("starter / other construct", "rebuild by hand", "unsupported") if c.startswith("starter:") else
                         ("group " + c, "check the BW group semantics", "decide"))
            add("Logic", f"{name}: {c} x{n}", how[0], how[1], how[2])
    for u in spec["unboundProcesses"]:
        add("Process", f"{u['process']} is not reached by any REST operation", "sub-process or non-REST starter",
            "sub-process: becomes a Flogo subflow when an operation calls it; starter: rebuild with the matching trigger", "decide")
    for p in spec["activityPlan"]:
        if p["difficulty"] in ("hard", "review"):
            add("Activity", p["bw6"], p["note"], p["flogo"], "decide")
    if spec["javaSources"]:
        add("Activity", f"{len(spec['javaSources'])} Java source file(s)", "Java code has no Flogo runtime",
            "if the analyzer marks the step dead: skip it; else re-express with mapping functions or write a Flogo Go extension", "decide")
    for r in spec["sharedResources"]:
        if r["kind"] == "jdbcResource":
            db = r.get("database")
            if db != "sqlserver":
                add("Connection", f"JDBC {r['name']} ({db or 'unknown database'})",
                    "the library's SQL helpers are verified for SQL Server only",
                    f"use the Flogo {db or '<db>'} connector with the same query/insert/update shape (planned - verify with parity)", "decide")
            add("Connection", f"JDBC {r['name']}: credentials", "BW stores the password obfuscated; it cannot be reused",
                "ask the user for the database user/password; stored as SECRET: in the connection", "decide")
        elif r["kind"] in RESOURCE_PLAN and r["kind"] != "httpConnResource":
            flogo, st = RESOURCE_PLAN[r["kind"]]
            add("Connection", f"shared resource {r['name']} ({r['kind']})", "not created by the scaffold",
                flogo, "manual" if st.startswith("verified") else "decide")
        elif r["kind"] not in RESOURCE_PLAN and r["kind"] not in ("xsd", "json", "wsdl", "jsv", "msv", "substvar"):
            add("Connection", f"shared resource {r['name']} ({r['kind']})", "no known Flogo equivalent",
                "find the matching Flogo connector (or a user extension) - decide before building", "decide")
    if spec["moduleProperties"]:
        add("Properties", f"{len(spec['moduleProperties'])} module properties", "become Flogo app properties",
            "Logic.prop(name, type, default) per property; password/secret ones as SECRET: (DB/LLM password fields) or a "
            "placeholder + FLOGO_APP_PROPS_ENV at run time", "manual")
    for rel, flav in spec.get("descriptors", {}).items():
        if flav.startswith("swagger"):
            add("Descriptor", f"{rel} is {flav}", "the scaffold reads OpenAPI 3 (components, requestBody) - bodies would be empty",
                "convert it to OpenAPI 3 first (e.g. swagger2openapi), then re-analyze", "decide")
    for path, item in ((openapi or {}).get("paths") or {}).items():
        for m, op in item.items():
            if not isinstance(op, dict):
                continue
            ok = [c for c in op.get("responses", {}) if str(c).startswith("2")]
            if ok and "200" not in ok:
                add("Operation", f"{m.upper()} {path}: success code(s) {', '.join(ok)}", "the scaffold wires 200",
                    "set the success response code on ConfigureHTTPResponse in the logic script", "manual")
            types = {t for r in op.get("responses", {}).values() if isinstance(r, dict) for t in (r.get("content") or {})}
            types |= set(((op.get("requestBody") or {}).get("content") or {}).keys())
            other = sorted(t for t in types if "json" not in t)
            if other:
                add("Operation", f"{m.upper()} {path}: content type(s) {', '.join(other)}", "the scaffold handles JSON bodies",
                    "XML/text bodies need act_general_xmltojson / string mapping by hand", "manual")
    return W


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("module_dir")
    ap.add_argument("--out", default=None, help="output folder (default: ./<Module>_modernize)")
    ap.add_argument("--port-offset", type=int, default=1000, help="added to the BW HTTP port (default 1000)")
    ap.add_argument("--mcp-port-offset", type=int, default=100, help="Flogo MCP port = Flogo REST port + this (default 100)")
    ap.add_argument("--bw-port", type=int, help="BW HTTP port when the connector's port can't be read (property-bound "
                                                 "without a default, or several connectors)")
    ap.add_argument("--error-codes", default="", metavar="CODE:TEXT,...",
                    help="extra error responses to declare on every operation, e.g. 401:Unauthorized,429:Too many requests "
                         f"(always declared: {', '.join(c for c, _ in ERROR_CODES)})")
    a = ap.parse_args()
    extra = [tuple(x.split(":", 1)) for x in a.error_codes.split(",") if ":" in x]
    error_codes = tuple(ERROR_CODES) + tuple((c.strip(), t.strip()) for c, t in extra if c.strip() not in dict(ERROR_CODES))

    module_dir = os.path.abspath(a.module_dir)
    if not os.path.exists(os.path.join(module_dir, "META-INF", "module.bwm")):
        print(f"error: {module_dir} is not a BW6 module (no META-INF/module.bwm)", file=sys.stderr)
        return 2
    module = os.path.basename(module_dir.rstrip("\\/"))
    out = os.path.abspath(a.out or f"{slug(module)}_modernize")
    os.makedirs(out, exist_ok=True)

    ops, module_props, components, other_bindings, references = parse_module(module_dir)
    substvars = parse_substvars(module_dir)
    for mp in module_props:
        mp.update(substvars.get(mp["name"], {}))
    for name, v in substvars.items():  # properties only declared in the substvar file
        if not any(mp["name"] == name for mp in module_props):
            module_props.append({"name": name, **v})
    resources = parse_resources(module_dir)
    for r in resources:
        if r["kind"] == "jdbcResource":
            r["database"] = jdbc_kind(r["settings"])
    http_conns = [r for r in resources if r["kind"] == "httpConnResource"]

    def conn_port(r):
        """The connector's port: literal, else the default of the module property it is bound to."""
        v = r["settings"].get("port")
        if v and v.isdigit():
            return int(v)
        prop = r.get("propertyBound", {}).get("port")
        if prop:
            mp = next((m for m in module_props if m["name"] == prop), {})
            for val in (mp.get("profiles") or {}).values():
                if str(val).isdigit():
                    return int(val)
        return None

    http_port = a.bw_port or next((conn_port(r) for r in http_conns if conn_port(r)), None)
    if http_port and not 0 < http_port + a.port_offset + a.mcp_port_offset <= 65535:
        print(f"error: BW port {http_port} + offsets is not a valid port; change --port-offset", file=sys.stderr)
        return 2

    processes, process_constructs = {}, {}
    for bwp in sorted(glob.glob(os.path.join(module_dir, "Processes", "**", "*.bwp"), recursive=True)):
        rel = os.path.relpath(bwp, module_dir).replace("\\", "/")
        processes[rel], process_constructs[rel] = parse_process(bwp)

    # attach each operation's process branch (partnerLink = service name, operation = operationName)
    for o in ops:
        o["implementation"] = None
        for rel, branches in processes.items():
            for b in branches:
                if b["partnerLink"] == o["service"] and b["operation"] == o["operationName"]:
                    o["implementation"] = {"process": rel, "activities": b["activities"], "links": b["links"],
                                           "groups": b.get("groups", {}), "constructs": b.get("constructs", {})}
        acts = (o["implementation"] or {}).get("activities", [])
        mark_used(acts, (o["implementation"] or {}).get("links", []), (o["implementation"] or {}).get("groups"))
        o["literals"] = sorted({s for act in acts for x in act["inputXslt"] for s in string_literals(x)})
        o["activityTypes"] = sorted({act["type"] for act in acts if act["type"] and act.get("usedByReply", True)})
        o["unusedActivities"] = [act["name"] for act in acts if not act.get("usedByReply", True)]
        o["xsltFeatures"], o["xpathFunctions"] = xslt_features(
            [x for act in acts if act.get("usedByReply", True) for x in act["inputXslt"]])
    # processes no REST operation reaches (sub-processes, non-REST starters) - listed in the plan
    reached = {(o["implementation"] or {}).get("process") for o in ops}
    unbound = [{"process": rel, "constructs": process_constructs[rel],
                "activityTypes": sorted({a["type"] for b in br for a in b["activities"] if a.get("type")})}
               for rel, br in processes.items() if rel not in reached]

    flavours = {}
    spec_openapi, renames = flogo_openapi(module_dir, ops, http_port, a.port_offset, error_codes, flavours)

    java = [os.path.relpath(p, module_dir).replace("\\", "/")
            for p in glob.glob(os.path.join(module_dir, "src", "**", "*.java"), recursive=True)]
    all_types = sorted({t for o in ops for t in o["activityTypes"]})
    activity_plan = []
    for t in all_types:
        if t.startswith("bpws:"):
            continue
        key = t if t in ACTIVITY_MAP else t.split(".")[-1]
        flogo, level, note = ACTIVITY_MAP.get(key, ("?", "review", "no known Flogo equivalent - review"))
        activity_plan.append({"bw6": t, "flogo": flogo, "difficulty": level, "note": note})

    spec = {
        "module": module,
        "moduleDir": module_dir,
        "http": {"bwPort": http_port, "flogoPort": int(http_port) + a.port_offset if http_port else None,
                 "connectors": [{"name": r["name"], "port": conn_port(r), "boundTo": r.get("propertyBound", {}).get("port")}
                                for r in http_conns]},
        "mcp": {"tools": [o["mcp"]["name"] for o in ops if o["mcp"]["explicit"] and o["mcp"]["kind"] == "tool"],
                "resources": [o["mcp"]["name"] for o in ops if o["mcp"]["explicit"] and o["mcp"]["kind"] == "resource"],
                # Observed BW 6.12 HF4 behaviour: a module with ANY MCP-configured operation exposes only
                # those; a module with none exposes every operation under its nickname.
                "implicitTools": ([] if any(o["mcp"]["explicit"] for o in ops)
                                  else [o["mcp"]["name"] for o in ops]),
                "flogoPort": int(http_port) + a.port_offset + a.mcp_port_offset if http_port else None},
        "operations": ops,
        "operationIdRenames": renames,
        "moduleProperties": module_props,
        "otherBindings": other_bindings,
        "references": references,
        "unboundProcesses": unbound,
        "components": components,
        "sharedResources": resources,
        "javaSources": java,
        "activityPlan": activity_plan,
        "descriptors": flavours,
        "errorCodes": [c for c, _ in error_codes],
    }
    spec["warnings"] = gap_warnings(spec, spec_openapi)
    base = os.path.join(out, slug(module))
    with open(base + ".bw6spec.json", "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=1)
    if spec_openapi:
        with open(base + ".openapi.json", "w", encoding="utf-8") as f:
            json.dump(spec_openapi, f, indent=1)

    # human report
    L = [f"# {module} - modernization analysis", "",
         f"- BW6 HTTP port: {http_port} -> Flogo REST port {spec['http']['flogoPort']}, Flogo MCP port {spec['mcp']['flogoPort']}",
         f"- Operations: {len(ops)}; MCP tools: {', '.join(spec['mcp']['tools']) or 'none'}; "
         f"MCP resources: {', '.join(spec['mcp']['resources']) or 'none'}",
         f"- Implicit MCP tools (BW exposes every operation; Flogo exposes these only with exact parity): "
         f"{', '.join(spec['mcp']['implicitTools']) or 'none'}",
         f"- Java sources: {len(java)}" + (f" ({', '.join(java)})" if java else ""),
         f"- Pure activities nothing reads (skip; Java ones only after checking the source): "
         + (", ".join(f"{o['flogoFlow'] if o.get('flogoFlow') else o['nickname']}: {', '.join(o['unusedActivities'])}"
                      for o in ops if o.get("unusedActivities")) or "none"), "",
         "## Operations", "", "| Method | Path | Flogo flow | MCP | Params | Activities |", "|---|---|---|---|---|---|"]
    for o in ops:
        mcp = (f"{o['mcp']['kind']} `{o['mcp']['name']}` ({o['mcp']['scope'] or '-'})" if o["mcp"]["explicit"]
               else f"implicit `{o['mcp']['name']}`")
        prm = ", ".join(f"{p['name']}:{p['in']}{'*' if p['required'] else ''}" for p in o["params"]) or "-"
        L.append(f"| {o['method']} | `{o['path']}` | `{o.get('flogoFlow', '?')}` | {mcp} | {prm} | "
                 f"{', '.join(t.split('.')[-1] for t in o['activityTypes']) or '-'} |")
    L += ["", "## Activity plan (BW6 -> Flogo)", "", "| BW6 activity | Flogo | Difficulty | Note |", "|---|---|---|---|"]
    for p in activity_plan:
        L.append(f"| `{p['bw6']}` | {p['flogo']} | {p['difficulty']} | {p['note']} |")
    L += ["", "## Shared resources", ""]
    for r in resources:
        L.append(f"- `{r['name']}` ({r['kind']}): " + ", ".join(f"{k}={v}" for k, v in list(r["settings"].items())[:8]))
    L += ["", "## Per-operation logic (decoded XSLT)", ""]
    for o in ops:
        L.append(f"### {o['method']} {o['path']} -> `{o.get('flogoFlow')}`")
        for act in (o["implementation"] or {}).get("activities", []):
            if act.get("usedByReply", True):
                dead = " — side effect (keep)" if act.get("sideEffect") else ""
            elif act.get("reviewPurity"):
                dead = " — **not read by the reply: read its source; skip it only if it has no side effects**"
            else:
                dead = " — **nothing reads its result (no Flogo equivalent needed)**"
            L.append(f"- **{act['name']}** `{act['type']}`{dead}")
            if act.get("sql"):
                L.append(f"  - SQL: `{act['sql'][:500]}`")
            for x in act["inputXslt"]:
                L.append(f"  - `{x[:600]}{'...' if len(x) > 600 else ''}`")
        conds = [lk for lk in (o["implementation"] or {}).get("links", []) if lk.get("condition")]
        if conds:
            L.append("- Conditional links:")
            L += [f"  - {lk['from']} -> {lk['to']}: `{html.unescape(lk['condition'])[:200]}`" for lk in conds]
        L.append("")
    with open(base + ".report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")

    print(f"module     : {module}")
    print(f"operations : {len(ops)}  (MCP tools: {', '.join(spec['mcp']['tools']) or '-'})")
    print(f"ports      : BW {http_port} -> Flogo REST {spec['http']['flogoPort']} / MCP {spec['mcp']['flogoPort']}")
    print(f"difficulty : " + ", ".join(f"{p['bw6'].split('.')[-1]}={p['difficulty']}" for p in activity_plan))
    print(f"wrote      : {base}.bw6spec.json" + (f", {base}.openapi.json" if spec_openapi else "") + f", {base}.report.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
