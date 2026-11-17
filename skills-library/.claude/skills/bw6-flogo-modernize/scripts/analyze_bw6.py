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
  python analyze_bw6.py <bw6-module-dir> --out <work>/analysis [--port-offset 1000] [--mcp-port-offset 100]
                        [--bw-port <port>] [--rename OLD=NEW ...] [--error-codes CODE:TEXT,...]
  python analyze_bw6.py <folder> --list          list the BW6 modules at/below a folder (workspace, .application)

Input (required): ONE BW6 module folder - the folder that holds META-INF/module.bwm (BW Studio: the project
named like the module, e.g. Acme.Orders.API, not Acme.Orders.API.application). Also accepted: the module's
META-INF folder or its module.bwm file, and a <Name>.application folder whose META-INF/TIBCO.xml lists exactly
one application module that sits next to it. A workspace folder holding several modules is rejected with the
list of candidates: analyze them one at a time.

Standard library only. Exits 2 when the input is not (or does not resolve to exactly one) BW6 module.
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
    "bw.generalactivities.timer": ("Timer trigger (process starter)", "medium", "Timer starter"),
    "bw.file.filepoller": ("File poller trigger (process starter)", "medium", "File poller starter"),
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
    "bw.file.write": ("act_file_write (File connector)", "easy", "Write file"),
    "bw.file.read": ("act_file_read (File connector)", "easy", "Read file"),
    "bw.file.list": ("act_file_list (File connector)", "easy", "List files"),
    "bw.file.create": ("act_file_create (File connector)", "easy", "Create file/directory"),
    "bw.file.remove": ("act_file_remove (File connector)", "easy", "Remove file"),
    "bw.file.rename": ("act_file_rename (File connector)", "easy", "Rename/move file"),
    "bw.file.copy": ("act_file_copy (File connector)", "easy", "Copy file"),
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
                key = "invoke (service call)"
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


# Ports Chrome/Edge/Firefox refuse to connect to ("unsafe ports": fetch fails with "Failed to fetch", no request is sent).
# BW 5000 + offset 1000 = 6000 (X11) is the common trap. Chromium net/base/port_util.cc kRestrictedPorts.
BROWSER_UNSAFE_PORTS = {1, 7, 9, 11, 13, 15, 17, 19, 20, 21, 22, 23, 25, 37, 42, 43, 53, 69, 77, 79, 87, 95, 101, 102,
                        103, 104, 109, 110, 111, 113, 115, 117, 119, 123, 135, 137, 139, 143, 161, 179, 389, 427, 465,
                        512, 513, 514, 515, 526, 530, 531, 532, 540, 548, 554, 556, 563, 587, 601, 636, 989, 990, 993,
                        995, 1719, 1720, 1723, 2049, 3659, 4045, 4190, 5060, 5061, 6000, 6566, 6665, 6666, 6667, 6668,
                        6669, 6679, 6697, 10080}


def browser_safe_port(port, label=None):
    """Move a port off the browser-blocked list (next free number up); warn when a label is given."""
    if port is None or port not in BROWSER_UNSAFE_PORTS:
        return port
    new = port
    while new in BROWSER_UNSAFE_PORTS:
        new += 1
    if label:
        print(f"warning: {label} port {port} is blocked by web browsers (unsafe port); using {new} instead", file=sys.stderr)
    return new


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
        base = (o.get("basePath") or "/").rstrip("/")
        if item is None and base and o["path"].startswith(base + "/"):
            # the descriptor lists the path without the binding's basePath: serve the full BW path in Flogo
            short = o["path"][len(base):]
            item = merged["paths"].get(short, {}).get(o["method"].lower())
            if item is not None:
                merged["paths"].setdefault(o["path"], {})[o["method"].lower()] = merged["paths"][short].pop(o["method"].lower())
                if not merged["paths"][short]:
                    del merged["paths"][short]
                o["basePathMerged"] = True
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
        merged["servers"] = [{"url": f"http://localhost:{browser_safe_port(int(http_port) + offset, None)}/"}]
    return merged, renames


PATH_KEYS = {"moduleDir", "file", "openapiFile", "process"}  # real paths into the BW module: never renamed


def apply_renames(value, rules, key=None):
    """Apply --rename rules ('OLD=NEW' literal, 're:PATTERN=REPL' regex) to every string value (not to dict keys,
    not to the PATH_KEYS values that point at real files)."""
    if isinstance(value, dict):
        return {k: (v if k in PATH_KEYS else apply_renames(v, rules, k)) for k, v in value.items()}
    if isinstance(value, list):
        return [apply_renames(v, rules, key) for v in value]
    if isinstance(value, str):
        for r in rules:
            if r.startswith("re:"):
                pat, _, repl = r[3:].rpartition("=")
                value = re.sub(pat, repl, value)
            else:
                old, _, new = r.partition("=")
                value = value.replace(old, new)
    return value


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
            if not o.get("openapiFile"):
                add("Operation", f"{o['method']} {o['path']}: the REST binding has no OpenAPI (JSON) service descriptor",
                    "the scaffold builds flows from an OpenAPI 3 document",
                    "export/generate the OpenAPI (Swagger) JSON for the REST service in BW Studio (or write one from the "
                    "binding's XSD schemas), add it under Service Descriptors, re-analyze", "decide")
            else:
                add("Operation", f"{o['method']} {o['path']} has no matching path in the OpenAPI descriptor",
                    "the scaffold cannot create its flow", "fix/regenerate the BW service descriptor, then re-analyze", "decide")
        if o.get("basePath") not in (None, "", "/") and not o.get("basePathMerged"):
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
                "invoke (service call)": ("calls a service: another process of this module (see 'not reached' processes) "
                                          "or an external REST/SOAP service",
                                          "internal process -> Logic.subflow + Logic.call; external REST -> act_general_rest "
                                          "with the base URL as an app property", "manual"),
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


# ----------------------------------------------------------------------------------------------
# input resolution: which folder is the BW6 module? (fail fast, name the expected file, list candidates)
# ----------------------------------------------------------------------------------------------
SKIP_DIRS = {".git", ".metadata", "node_modules", "target", "bin", ".settings", ".flogodesign", "__pycache__"}


def is_module(path):
    return os.path.isfile(os.path.join(path, "META-INF", "module.bwm"))


def find_modules(root, max_depth=5):
    """Every BW6 module folder (holding META-INF/module.bwm) at or below root, sorted."""
    root = os.path.abspath(root)
    base = root.rstrip("\\/").count(os.sep)
    found = []
    for dirpath, dirnames, _ in os.walk(root):
        if is_module(dirpath):
            found.append(dirpath)
            dirnames[:] = []          # a module does not nest other modules
            continue
        if dirpath.count(os.sep) - base >= max_depth:
            dirnames[:] = []
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
    return sorted(found)


def manifest(module_dir):
    """META-INF/MANIFEST.MF as {header: value}, continuation lines (leading space) unfolded."""
    p = os.path.join(module_dir, "META-INF", "MANIFEST.MF")
    if not os.path.isfile(p):
        return {}
    text = re.sub(r"\r?\n ", "", read(p))
    return {k.strip(): v.strip() for k, _, v in (ln.partition(":") for ln in text.splitlines()) if v}


def module_summary(module_dir):
    """One line for candidate lists: kind, REST operation count, palettes that need extra inputs."""
    mf = manifest(module_dir)
    kind = "shared module" if "TIBCO-BW-SharedModule" in mf else "application module"
    palettes = sorted(set(re.findall(r"name=(bw\.[\w.]+)", mf.get("Require-Capability", ""))))
    try:
        n_ops = len(parse_module(module_dir)[0])
    except (ET.ParseError, OSError):
        n_ops = "?"
    needs = [label for key, label in (("jdbc", "JDBC -> DB details"), ("rag", "AI/RAG -> LLM + vector store"),
                                      ("httpclient", "calls other services -> base URLs"))
             if any(key in p for p in palettes)]
    return f"{kind}, {n_ops} REST operation(s)" + (f"; {', '.join(needs)}" if needs else "")


def application_modules(app_dir):
    """Modules a <Name>.application lists in META-INF/TIBCO.xml -> [(symbolicName, technologyType, folder|None)].
    BW Studio keeps them as sibling projects of the .application folder."""
    p = os.path.join(app_dir, "META-INF", "TIBCO.xml")
    root = ET.fromstring(read(p).encode("utf-8"))
    out = []
    parent = os.path.dirname(os.path.abspath(app_dir).rstrip("\\/"))
    siblings = find_modules(parent, max_depth=1)
    for m in root.iter():
        if local(m.tag) != "module":
            continue
        name = next((c.text or "" for c in m if local(c.tag) == "symbolicName"), "").strip()
        ttype = next((c.text or "" for c in m if local(c.tag) == "technologyType"), "").strip()
        folder = next((s for s in siblings if os.path.basename(s) == name
                       or manifest(s).get("Bundle-SymbolicName", "").split(";")[0].strip() == name), None)
        if name:
            out.append((name, ttype, folder))
    return out


def resolve_module_dir(path):
    """(module_dir, None) when path is - or unambiguously names - one BW6 module; else (None, error text)."""
    p = os.path.abspath(path)
    expect = "expected a BW6 module folder: the folder that holds META-INF/module.bwm"
    if not os.path.exists(p):
        return None, f"{p} does not exist ({expect})"
    if os.path.isfile(p):
        if os.path.basename(p) == "module.bwm" and os.path.basename(os.path.dirname(p)) == "META-INF":
            return os.path.dirname(os.path.dirname(p)), None
        if os.path.basename(p) == "TIBCO.xml":
            p = os.path.dirname(os.path.dirname(p))
        else:
            return None, f"{p} is a file ({expect})"
    if is_module(p):
        return p, None
    if os.path.basename(p) == "META-INF" and os.path.isfile(os.path.join(p, "module.bwm")):
        return os.path.dirname(p), None
    if os.path.isfile(os.path.join(p, "META-INF", "TIBCO.xml")):  # a <Name>.application project
        mods = application_modules(p)
        app_mods = [m for m in mods if m[1] != "bw-sharedmodule"]
        found = [m for m in app_mods if m[2]]
        if len(found) == 1 and len(app_mods) == 1:
            print(f"note: {os.path.basename(p)} is a BW application; analyzing its module {found[0][2]}", file=sys.stderr)
            return found[0][2], None
        lines = [f"  - {n} ({t or '?'}): " + (f"{f}  [{module_summary(f)}]" if f else "folder not found next to the "
                                                 "application - pass its path") for n, t, f in mods]
        return None, (f"{p} is a BW application (META-INF/TIBCO.xml), not a module; {expect}. It lists "
                      f"{len(mods)} module(s):\n" + "\n".join(lines) + "\nRe-run with the module folder to modernize.")
    cands = find_modules(p)
    if not cands:
        return None, (f"no BW6 module found at or below {p}: {expect} (missing {os.path.join(p, 'META-INF', 'module.bwm')}). "
                      "Point at the module project folder of your BW Studio workspace.")
    return None, (f"{p} is not a BW6 module (no META-INF/module.bwm); {len(cands)} module folder(s) found below it:\n"
                  + "\n".join(f"  - {c}  [{module_summary(c)}]" for c in cands)
                  + "\nAnalyze one module per run: re-run with one of these folders (ask the user which ones, and in "
                    "which order, when that is not clear).")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("module_dir", metavar="bw6-module-dir",
                    help="REQUIRED. BW6 module folder (holds META-INF/module.bwm); with --list any folder to search")
    ap.add_argument("--list", action="store_true",
                    help="only list the BW6 modules at/below the folder (kind, REST operations, palettes that need "
                         "extra inputs) and exit - use it to pick the modules and their order")
    ap.add_argument("--out", default=None, help="output folder, e.g. <work>/analysis (default: ./<Module>_modernize)")
    ap.add_argument("--port-offset", type=int, default=1000, help="added to the BW HTTP port (default 1000)")
    ap.add_argument("--mcp-port-offset", type=int, default=100, help="Flogo MCP port = Flogo REST port + this (default 100)")
    ap.add_argument("--bw-port", type=int, help="BW HTTP port when the connector's port can't be read (property-bound "
                                                 "without a default, or several connectors)")
    ap.add_argument("--rename", action="append", default=[], metavar="OLD=NEW",
                    help="replace text in everything the analysis writes (titles, descriptions, tool texts, literals, data, "
                         "module name) - e.g. to drop a customer/brand name; 're:<regex>=<replacement>' for a regular "
                         "expression. Real file paths are never renamed. Repeatable, applied in order")
    ap.add_argument("--error-codes", default="", metavar="CODE:TEXT,...",
                    help="extra error responses to declare on every operation, e.g. 401:Unauthorized,429:Too many requests "
                         f"(always declared: {', '.join(c for c, _ in ERROR_CODES)})")
    a = ap.parse_args()
    extra = [tuple(x.split(":", 1)) for x in a.error_codes.split(",") if ":" in x]
    error_codes = tuple(ERROR_CODES) + tuple((c.strip(), t.strip()) for c, t in extra if c.strip() not in dict(ERROR_CODES))

    if a.list:
        root = os.path.abspath(a.module_dir)
        if not os.path.isdir(root):
            print(f"error: {root} is not a folder", file=sys.stderr)
            return 2
        mods = find_modules(root)
        if os.path.isfile(os.path.join(root, "META-INF", "TIBCO.xml")) and not mods:
            mods = [f for _, _, f in application_modules(root) if f]
        for m in mods:
            print(f"{m}  [{module_summary(m)}]")
        if not mods:
            print(f"error: no BW6 module (META-INF/module.bwm) found at or below {root}", file=sys.stderr)
            return 2
        return 0

    module_dir, problem = resolve_module_dir(a.module_dir)
    if problem:
        print(f"error: {problem}", file=sys.stderr)
        return 2
    module = os.path.basename(module_dir.rstrip("\\/"))
    out = os.path.abspath(a.out or f"{slug(module)}_modernize")
    os.makedirs(out, exist_ok=True)

    ops, module_props, components, other_bindings, references = parse_module(module_dir)
    if not ops:
        print(f"warning: {module} has no REST service binding ({module_summary(module_dir)}) - nothing for the scaffold "
              "to build (shared module, or non-REST starters only: see the report)", file=sys.stderr)
    substvars = parse_substvars(module_dir)
    for mp in module_props:
        mp.update(substvars.get(mp["name"], {}))
    for name, v in substvars.items():  # properties only declared in the substvar file
        if not any(mp["name"] == name for mp in module_props):
            module_props.append({"name": name, **v})
    resources = parse_resources(module_dir)

    def prop_default(name):
        mp = next((m for m in module_props if m["name"] == name or m["name"].split("/")[-1] == name.split("/")[-1]), {})
        vals = mp.get("profiles") or {}
        return vals.get("default", next(iter(vals.values()), None))

    for r in resources:
        if r["kind"] == "jdbcResource":
            resolved = dict(r["settings"])
            for k in ("dbURL", "jdbcDriver"):
                if not resolved.get(k) and r.get("propertyBound", {}).get(k):
                    resolved[k] = prop_default(r["propertyBound"][k]) or ""
            r["database"] = jdbc_kind(resolved)
    http_conns = [r for r in resources if r["kind"] == "httpConnResource"]

    def conn_port(r):
        """The connector's port: literal, else the default of the module property it is bound to."""
        v = r["settings"].get("port")
        if v and v.isdigit():
            return int(v)
        prop = r.get("propertyBound", {}).get("port")
        if prop == "BW.CLOUD.PORT":
            return 8080  # BWCE built-in: the container's HTTP port (default 8080)
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

    # Flogo ports: BW port + offsets, moved off the browser-blocked list (demo pages call these from a browser)
    flogo_rest_port = browser_safe_port(int(http_port) + a.port_offset, "Flogo REST") if http_port else None
    flogo_mcp_port = (browser_safe_port(int(http_port) + a.port_offset + a.mcp_port_offset, "Flogo MCP")
                      if http_port else None)   # from the unmoved REST port, so a moved REST port does not move it
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
        "http": {"bwPort": http_port, "flogoPort": flogo_rest_port,
                 "connectors": [{"name": r["name"], "port": conn_port(r), "boundTo": r.get("propertyBound", {}).get("port")}
                                for r in http_conns]},
        "mcp": {"tools": [o["mcp"]["name"] for o in ops if o["mcp"]["explicit"] and o["mcp"]["kind"] == "tool"],
                "resources": [o["mcp"]["name"] for o in ops if o["mcp"]["explicit"] and o["mcp"]["kind"] == "resource"],
                # Observed BW 6.12 HF4 behaviour: a module with ANY MCP-configured operation exposes only
                # those; a module with none exposes every operation under its nickname.
                "implicitTools": ([] if any(o["mcp"]["explicit"] for o in ops)
                                  else [o["mcp"]["name"] for o in ops]),
                "flogoPort": flogo_mcp_port},
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
    if a.rename:
        spec = apply_renames(spec, a.rename)
        spec_openapi = apply_renames(spec_openapi, a.rename) if spec_openapi else spec_openapi
        spec["renamesApplied"] = len(a.rename)  # the rules themselves may contain the name being removed
        module = spec["module"]
        ops, resources, activity_plan = spec["operations"], spec["sharedResources"], spec["activityPlan"]
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
