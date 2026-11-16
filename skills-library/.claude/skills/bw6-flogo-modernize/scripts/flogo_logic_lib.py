"""Helpers for writing the business logic of a modernized flow with fda (step 3 of the skill).

Use from a small per-app script:

    from flogo_logic_lib import Logic
    L = Logic(r"<work>/plan.json")
    F = L.flow("find_promotions")              # REST flow created by scaffold_flogo_app.py
    L.unlink_placeholder(F)                     # detach the cas logReply response so you can insert steps
    L.static_data(F, "CustomerData", "customers", items, item_schema)
    ...
    L.response(F, "ConfigureHTTPResponse", 200, "FindPromotionsBody", L.op(F)["ok"], {...})
    L.link(F, "FindCustomer", "ConfigureHTTPResponse", "array.count($activity[FindCustomer].output.matches) > 0")
    L.finish()                                  # reply link last, format, check-mappings

Every helper encodes a verified rule (see references/gotchas.md):
- mapper output is $activity[<Mapper>].output.<field>
- link conditions: type=expression + value (created with --force, no leading '=')
- the cas Return's incoming link must be stored last or the designer drops Return
- httpresponse bodies need a typed {body:{...}} wrapper schema and field-by-field mappings
- literal data goes into a typed mapper array (static_data), never as a JSON string literal
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fdalib import Fda  # noqa: E402
from designer_load_check import check as designer_drops, safe_order  # noqa: E402

ERROR_SCHEMA = {"type": "object", "properties": {"error": {"type": "string"}, "message": {"type": "string"}}}


def jschema(s):
    return {"type": "json", "value": json.dumps(s), "fe_metadata": json.dumps(s)}


def negate(expr):
    """Logical NOT for link conditions and mappings. The designer's expression parser rejects the unary '!'
    (the runtime accepts it, so parity tests pass while the designer shows a red condition):
    write '(expr) == false' instead."""
    return f"({expr}) == false"


UNARY_NOT = re.compile(r"!(?!=)")
STRING_LITERAL = re.compile(r'"(?:[^"\\]|\\.)*"')   # "..." with escapes; '!' inside literals is not a NOT


def bw_string_literal(xslt):
    """The single-quoted literal of a decoded BW XSLT ({'...'}), e.g. an embedded JSON document."""
    m = re.search(r"\{'(.*)'\}", xslt, re.S)
    return m.group(1) if m else None


def infer_schema(sample):
    """Draft-04 style JSON schema from sample data (merges the keys of every object in an array)."""
    if isinstance(sample, bool):
        return {"type": "boolean"}
    if isinstance(sample, int):
        return {"type": "integer"}
    if isinstance(sample, float):
        return {"type": "number"}
    if isinstance(sample, str) or sample is None:
        return {"type": "string"}
    if isinstance(sample, list):
        objs = [x for x in sample if isinstance(x, dict)]
        if objs:
            merged = {}
            for o in objs:
                merged = _deep_merge(merged, o)
            return {"type": "array", "items": infer_schema(merged)}
        return {"type": "array", "items": infer_schema(sample[0] if sample else "")}
    return {"type": "object", "properties": {k: infer_schema(v) for k, v in sample.items()}}


def _deep_merge(a, b):
    """Union of two sample objects, recursing into nested objects, so keys that only some items have
    (e.g. attributes.capacityLiters on one product) still end up in the schema."""
    out = dict(a)
    for k, v in b.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        elif k not in out or out[k] is None:
            out[k] = v
    return out


class Logic:
    def __init__(self, plan_path):
        self.plan = json.load(open(plan_path, encoding="utf-8"))
        self.work = os.path.dirname(os.path.abspath(plan_path))
        self.app = self.plan["app"]
        self.rest = self.plan["restTrigger"]
        self.fda = Fda(self.app)
        self._ops = {o["flow"]: o for o in self.plan["ops"]}
        self._branches = {}       # flow -> list of (from, to, expr)
        self._placeholder = set()
        self._subflows = []       # flows created with subflow(): formatted in finish()
        self._schemas = set(json.load(open(self.app, encoding="utf-8")).get("schemas", {}))
        # the analyzer spec (shared resources, decoded XSLT, literals); older plan.json files lack the path
        sp = self.plan.get("spec")
        self.spec = json.load(open(sp, encoding="utf-8")) if sp and os.path.exists(sp) else None

    # ------------------------------------------------------------------ lookup
    def flow(self, prefix):
        """REST flow name for an operation (flow names are '<operationId>_<METHOD>')."""
        hits = [f for f in self._ops if f == prefix or f.startswith(prefix + "_")]
        if len(hits) != 1:
            sys.exit(f"flow '{prefix}': expected 1 match, got {hits}")
        return hits[0]

    def op(self, flow):
        return self._ops[flow]

    def bw_activity(self, flow, name):
        return next(a for a in self._ops[flow]["bwActivities"] if a["name"] == name)

    def bw_json(self, flow, name):
        """Parsed JSON literal that the BW activity <name> (e.g. a JsonParser) receives in its XSLT."""
        lit = bw_string_literal(self.bw_activity(flow, name)["inputXslt"][0])
        if lit is None:
            sys.exit(f"{flow}/{name}: no string literal in its input mapping")
        return json.loads(lit)

    def tmp(self, name, obj):
        p = os.path.join(self.work, name)
        json.dump(obj, open(p, "w", encoding="utf-8"), indent=1)
        return p

    def response_codes(self, flow):
        """HTTP codes declared for the flow's REST handler (the designer's response 'Code' dropdown)."""
        d = json.load(open(self.app, encoding="utf-8"))
        for t in d.get("triggers", []):
            for h in t.get("handlers", []):
                if h["action"]["settings"].get("flowURI") == f"res://flow:{flow}":
                    rc = (h.get("schemas", {}).get("reply", {}).get("responseCodesSchema") or {}).get("fe_metadata")
                    try:
                        return {int(r["code"]) for r in json.loads(rc)} if rc else set()
                    except (ValueError, TypeError, KeyError):
                        return set()
        return set()

    def links(self, flow):
        d = json.load(open(self.app, encoding="utf-8"))
        r = next(x for x in d["resources"] if x["id"] == f"flow:{flow}")
        return r["data"].get("links", [])

    # ------------------------------------------------------------------ structure
    def unlink_placeholder(self, flow):
        """Detach Log_API -> ConfigureHTTPResponse so steps can be inserted in between."""
        self.fda("rl", flow, "Log_API", "ConfigureHTTPResponse")
        self._placeholder.add(flow)

    def log(self, flow, message_expr):
        self.fda("mm", f"{flow}.Log_API.input.message", message_expr)

    def link(self, flow, frm, to, condition=None):
        """Create a link; with condition, it only fires when the expression is true. Conditions are
        applied in finish() because link indexes shift while links are added and removed."""
        if condition and UNARY_NOT.search(STRING_LITERAL.sub('""', condition)):
            sys.exit(f"{flow} {frm}->{to}: unary '!' in a condition is rejected by the designer - use negate(expr)")
        self.fda("cl", flow, frm, to)
        if condition:
            self._branches.setdefault(flow, []).append((frm, to, condition))

    def activity(self, flow, name, type_, desc):
        self.fda("ca", flow, name, type_, desc, "--doNotLink")

    # ------------------------------------------------------------------ building blocks
    def static_data(self, flow, name, field, items, item_schema, desc="Embedded reference data (from the BW6 process)"):
        """Data the BW6 process hardcodes (e.g. a JsonParser over a literal) -> a Mapper whose array field is
        seeded with typed JSON. Read it as $activity[<name>].output.<field>.
        Don't put a JSON literal into a string field (e.g. parsejson.jsonString): the designer reads a value
        starting with '{' as an object and flags the field."""
        self.activity(flow, name, "act_general_mapper", desc)
        self.fda("sms", f"{flow}.{name}.input", "--json-schema-file",
                 self.tmp(f"{flow}_{name}_in.json", {"type": "object", "properties": {field: {"type": "array", "items": item_schema}}}))
        self.fda("mm", f"{flow}.{name}.input.input.mapping.{field}", "--jsonValue", json.dumps(items))

    def static_dataset(self, flow, name, datasets, desc="Embedded reference data (from the BW6 process)"):
        """Several hardcoded arrays in one mapper: datasets = {field: list_of_items}; schemas are inferred.
        Read them as $activity[<name>].output.<field>."""
        self.activity(flow, name, "act_general_mapper", desc)
        props = {f: infer_schema(items) for f, items in datasets.items()}
        self.fda("sms", f"{flow}.{name}.input", "--json-schema-file",
                 self.tmp(f"{flow}_{name}_in.json", {"type": "object", "properties": props}))
        for f, items in datasets.items():
            self.fda("mm", f"{flow}.{name}.input.input.mapping.{f}", "--jsonValue", json.dumps(items))
        return {f: s["items"] for f, s in props.items()}

    def compute(self, flow, name, fields, desc="Derived values (BW xsl:variable)"):
        """BW <xsl:variable>s -> a mapper of named, typed expressions: fields = {name: (json_type | schema, "=expr")}.
        A mapper cannot read its own outputs; chain two compute() steps when one value depends on another.
        Read them as $activity[<name>].output.<field>."""
        self.activity(flow, name, "act_general_mapper", desc)
        self.fda("sms", f"{flow}.{name}.input", "--json-schema",
                 json.dumps({"type": "object", "properties": {k: (t if isinstance(t, dict) else {"type": t})
                                                               for k, (t, _) in fields.items()}}))
        for k, (_, expr) in fields.items():
            self.fda("mm", f"{flow}.{name}.input.input.mapping.{k}", expr)

    def select(self, flow, name, source_array, item_schema, predicate, field="matches", iterator="it",
               desc="Select matching items (BW for-each with predicate)"):
        """BW <xsl:for-each select="...[predicate]"> -> mapper with a filtered @foreach.
        predicate uses $loop[<iterator>].<field>. Read the result as $activity[<name>].output.<field>.
        Note: fda cm flags FOREACH_SCOPE_UNDEFINED for the 3-argument form; the runtime filters correctly."""
        self.activity(flow, name, "act_general_mapper", desc)
        self.fda("sms", f"{flow}.{name}.input", "--json-schema-file",
                 self.tmp(f"{flow}_{name}_in.json", {"type": "object", "properties": {field: {"type": "array", "items": item_schema}}}))
        self.fda("mm", f"{flow}.{name}.input.input.mapping.{field}", "--foreach", source_array, "--as", f"{iterator}, {predicate}")
        for p in item_schema.get("properties", {}):
            self.fda("mm", f"{flow}.{name}.input.input.mapping.{field}.{p}", f"=$loop[{iterator}].{p}")

    def response(self, flow, act, code, wrapper_name, body_schema, mappings, desc=""):
        """HTTP response with a typed body. act == 'ConfigureHTTPResponse' reuses the cas activity
        (and its Return); any other name creates <act> + Return<act>, linked to each other.
        mappings: {"field" or "a.b": literal | "=expr" | bool | list/dict (stored as typed JSON)}"""
        f = self.fda
        declared = self.response_codes(flow)
        if declared and int(code) not in declared:
            sys.exit(f"{flow}/{act}: HTTP {code} is not in the operation's response-code table {sorted(declared)}; the designer "
                     f"would show 'Code is required'. Declare it in the Flogo-ready OpenAPI (analyze_bw6.py ERROR_CODES).")
        if act != "ConfigureHTTPResponse":
            self.activity(flow, act, "act_general_httpresponse", desc or f"HTTP {code} response")
            f("sa", "activity", f"{flow}.{act}.input.responsecode", str(code))
        if wrapper_name not in self._schemas:  # fda cs is not idempotent: a second cs adds <name>_2, _3 ... copies
            f("cs", wrapper_name, json.dumps({"type": "object", "properties": {"body": body_schema}}))
            self._schemas.add(wrapper_name)
        f("sa", "activity", f"{flow}.{act}.schemas.input.input", wrapper_name, "-C", "schema", "--force")
        f("sa", "activity", f"{flow}.{act}.input.trigger", self.rest)
        for field, val in mappings.items():
            path = f"{flow}.{act}.input.input.mapping.body.{field}"
            if isinstance(val, bool):
                f("mm", path, "true" if val else "false", "--type", "boolean")
            elif isinstance(val, (int, float)):
                f("mm", path, str(val), "--type", "number")
            elif isinstance(val, (list, dict)):
                f("mm", path, "--jsonValue", json.dumps(val))
            else:
                f("mm", path, val)
        if act != "ConfigureHTTPResponse":
            ret = "Return" + act
            self.activity(flow, ret, "act_default_actreturn", f"Reply {code}")
            f("mm", f"{flow}.{ret}.input.mappings.code", f"=$activity[{act}].code")
            f("mm", f"{flow}.{ret}.input.mappings.responseBody", f"=$activity[{act}].response")
            f("cl", flow, act, ret)

    def error(self, flow, act, code, error, message_expr, wrapper_name="ErrorBody"):
        self.response(flow, act, code, wrapper_name, ERROR_SCHEMA, {"error": error, "message": message_expr})

    def require_params(self, flow, after="Log_API", next_step=None, act="BadRequest", body_fields=()):
        """400 JSON branch when a required query/path parameter (or a listed body field) is empty; the happy
        path goes to next_step. body_fields: request-body fields the BW logic needs (its XSLT selects on them)."""
        o = self._ops[flow]
        req = ([("queryParams", p) for p in o["requiredQuery"]] + [("pathParams", p) for p in o["pathParams"]]
               + [("body", f) for f in body_fields])
        if not req:
            return
        names = ", ".join(p for _, p in req)
        self.error(flow, act, 400, "invalid_request", f"{names} {'is' if len(req) == 1 else 'are'} required")
        missing = " || ".join(f'coerce.toString($flow.{k}.{p}) == ""' for k, p in req)
        present = " && ".join(f'coerce.toString($flow.{k}.{p}) != ""' for k, p in req)
        self.link(flow, after, act, missing)
        if next_step:
            self.link(flow, after, next_step, present)

    # ------------------------------------------------------------------ databases (BW JDBC palette)
    def secret(self, plain):
        """SECRET:<cipher> via flogo-vscode-cli (same bin folder as fda); the engine decrypts it at runtime."""
        name = "flogo-vscode-cli.exe" if os.name == "nt" else "flogo-vscode-cli"
        cli = os.path.join(os.path.dirname(self.fda.exe), name)
        r = subprocess.run([cli, "secret", "encrypt", "-p", plain], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        m = re.search(r'"cipherText":\s*"(SECRET:[^"]+)"', r.stdout or "")
        if not m:
            sys.exit(f"{cli} secret encrypt returned no cipherText")
        return m.group(1)

    def db_connection(self, name, jdbc_url, user, password, extra=None):
        """BW jdbcResource -> Flogo DB connection (SQL Server: con_sqlserver). The password is stored encrypted.
        jdbc_url: the BW dbURL, e.g. jdbc:sqlserver://host:port;databaseName=DB;encrypt=true;..."""
        m = re.match(r"jdbc:sqlserver://([^:;/]+)(?::(\d+))?;?(.*)$", jdbc_url, re.I)
        if not m:
            sys.exit(f"db_connection: only jdbc:sqlserver URLs are supported so far, got {jdbc_url}")
        props = {k.lower(): v for k, v in (kv.split("=", 1) for kv in m.group(3).split(";") if "=" in kv)}
        settings = {"name": name, "host": m.group(1), "port": int(m.group(2) or 1433),
                    "databaseName": props.get("databasename") or props.get("database"),
                    "user": user, "password": self.secret(password)}
        settings.update(extra or {})
        self.fda("cc", name, "con_sqlserver")
        for k, v in settings.items():
            if isinstance(v, bool):
                self.fda("sa", "connection", f"{name}.settings.{k}", "true" if v else "false", "-C", "boolean")
            elif isinstance(v, int):
                self.fda("sa", "connection", f"{name}.settings.{k}", str(v), "-C", "number")
            else:
                self.fda("sa", "connection", f"{name}.settings.{k}", v)
        return name

    SQL_TYPES = {"string": "VARCHAR", "integer": "INT", "number": "FLOAT", "boolean": "BOOLEAN"}
    _STARTERS, _TERMINATORS = " =,(<>+-*%/", " ;),<>+-*%/"

    @classmethod
    def lint_sql(cls, statement, params):
        """The connector only binds ?name when the char before '?' is one of ' =,(<>+-*%/' and the char after
        the name is one of ' ;),<>+-*%/'; otherwise the text stays literal (silently). Unnamed '?' is rejected."""
        problems = []
        for m in re.finditer(r"\?([A-Za-z0-9_.]*)", statement):
            before = statement[m.start() - 1] if m.start() else " "
            after = statement[m.end()] if m.end() < len(statement) else ""
            if not m.group(1):
                problems.append(f"unnamed '?' at {m.start()}")
            elif before not in cls._STARTERS or after == "" or after not in cls._TERMINATORS:
                problems.append(f"?{m.group(1)} not bindable (before={before!r}, after={after!r})")
            elif m.group(1) not in params:
                problems.append(f"?{m.group(1)} has no mapping")
        missing = [p for p in params if f"?{p}" not in statement]
        if missing:
            problems.append(f"mapped but unused: {missing}")
        if problems:
            sys.exit("SQL lint failed: " + "; ".join(problems) + f"\n  {statement}")

    def sql(self, flow, name, kind, statement, connection, params=None, columns=None, desc=""):
        """BW JDBC Query/Update -> act_sqlserver_<kind> (query|insert|update|delete).
        statement: SQL with NAMED parameters (?name) - rewrite BW's positional '?' in the order of the BW input.
        params:  {name: (json_type, "=expr" | literal)} -> input.parameters.<name>
        columns: {column: json_type} for queries -> read rows as $activity[<name>].Output.records
        insert/update/delete return $activity[<name>].Output.rowsAffected."""
        params, columns = params or {}, columns or {}
        self.lint_sql(statement, params)
        stmt_field = {"query": "Query", "insert": "InsertStatement", "update": "UpdateStatement",
                      "delete": "DeleteStatement"}[kind]
        self.fda("ca", flow, name, f"act_sqlserver_{kind}", desc or f"SQL {kind}", "--doNotLink", "-C", connection)
        self.fda("sa", "activity", f"{flow}.{name}.input.{stmt_field}", statement)
        fields = [{"FieldName": p, "Type": self.SQL_TYPES.get(t, "VARCHAR"), "Selected": False, "Parameter": True,
                   "isEditable": False, "Ordinal": i + 1} for i, (p, (t, _)) in enumerate(params.items())]
        fields += [{"FieldName": c, "Type": self.SQL_TYPES.get(t, "VARCHAR"), "Selected": True, "Parameter": False,
                    "isEditable": False, "Ordinal": i + 1} for i, (c, t) in enumerate(columns.items())]
        self.fda("sa", "activity", f"{flow}.{name}.input.Fields", "--jsonValue", json.dumps(fields))
        in_schema = {"$schema": "http://json-schema.org/draft-04/schema#", "type": "object", "definitions": {},
                     "properties": {"parameters": {"type": "object",
                                                   "properties": {p: {"type": t} for p, (t, _) in params.items()}}}}
        self.fda("sa", "activity", f"{flow}.{name}.schemas.input.input", "--jsonFile",
                 self.tmp(f"{flow}_{name}_in.json", jschema(in_schema)), "--force")
        if kind == "query":
            out = {"records": {"type": "array", "items": {"type": "object",
                                                          "properties": {c: {"type": t} for c, t in columns.items()}}}}
        else:
            out = {"rowsAffected": {"type": "integer"}, "lastInsertId": {"type": "integer"}}
        out_schema = {"$schema": "http://json-schema.org/draft-04/schema#", "type": "object", "definitions": {},
                      "properties": out}
        self.fda("sa", "activity", f"{flow}.{name}.schemas.output.Output", "--jsonFile",
                 self.tmp(f"{flow}_{name}_out.json", jschema(out_schema)), "--force")
        if params:
            for p, (_, expr) in params.items():
                self.fda("mm", f"{flow}.{name}.input.input.mapping.parameters.{p}", expr)
        else:  # the connector rejects a missing input ("No input arguments for query specified")
            self.fda("sa", "activity", f"{flow}.{name}.input.input", "--jsonValue", '{"mapping": {"parameters": {}}}', "--force")

    def project(self, flow, name, arrays, desc="Reshape records (BW for-each over Record)"):
        """Mapper building arrays from other arrays with renamed/converted fields:
        arrays = {field: (source_array_expr, iterator, {out_field: (json_type, "=expr using $loop[iterator]")})}.
        Read them as $activity[<name>].output.<field>."""
        self.activity(flow, name, "act_general_mapper", desc)
        props = {f: {"type": "array", "items": {"type": "object", "properties": {k: {"type": t} for k, (t, _) in spec.items()}}}
                 for f, (_, _, spec) in arrays.items()}
        self.fda("sms", f"{flow}.{name}.input", "--json-schema-file",
                 self.tmp(f"{flow}_{name}_in.json", {"type": "object", "properties": props}))
        for f, (src, it, spec) in arrays.items():
            self.fda("mm", f"{flow}.{name}.input.input.mapping.{f}", "--foreach", src, "--as", it)
            for k, (_, expr) in spec.items():
                self.fda("mm", f"{flow}.{name}.input.input.mapping.{f}.{k}", expr)

    # ------------------------------------------------------------------ app properties
    def prop(self, name, type_, value, secret=False):
        """App property (re-created if it exists). secret=True stores SECRET:<cipher> (shown as a password)."""
        d = json.load(open(self.app, encoding="utf-8"))
        if any(x["name"] == name for x in d.get("properties", [])):
            self.fda("rap", name)
        self.fda("cap", name, type_, self.secret(value) if secret else str(value))

    def _set_input(self, flow, act, field, value):
        """Non-mapper activity input: literal (typed) or =expression."""
        path = f"{flow}.{act}.input.{field}"
        if isinstance(value, bool):
            self.fda("mm", path, "true" if value else "false", "--type", "boolean")
        elif isinstance(value, (int, float)):
            self.fda("mm", path, str(value), "--type", "number")
        elif isinstance(value, (list, dict)) and "\"=" in json.dumps(value):
            # A literal list/object holding =expressions: the runtime evaluates it only under a {"mapping": ...}
            # wrapper, and the designer cannot render that on an untyped field (red editor). Build the value in a
            # typed mapper (compute) and pass ONE expression instead, e.g. a jq to_entries over the mapper output.
            sys.exit(f"{flow}/{act}.{field}: literal list/object with =expressions is rejected by the designer; build it "
                     f"in a compute() mapper and map one expression (see examples/policy_logic.py DocAttributes)")
        elif isinstance(value, (list, dict)):
            self.fda("mm", path, "--jsonValue", json.dumps(value))
        else:
            self.fda("mm", path, value)

    # ------------------------------------------------------------------ subflows
    def subflow(self, name, desc, inputs, outputs):
        """A flow without a trigger (BW subprocess / shared logic), run with call().
        inputs/outputs: JSON-schema properties {field: {"type": ...}}; read them as $flow.<field>."""
        self.fda("cf", name, desc)
        self.fda("sms", f"{name}.input", "--json-schema", json.dumps({"type": "object", "properties": inputs}))
        self.fda("sms", f"{name}.output", "--json-schema", json.dumps({"type": "object", "properties": outputs}))
        self._subflows.append(name)

    def sub_return(self, flow, act, mappings, desc="Return the subflow outputs"):
        """actreturn for a subflow: mappings = {output: "=expr" | literal}."""
        self.activity(flow, act, "act_default_actreturn", desc)
        for k, v in mappings.items():
            self.fda("mm", f"{flow}.{act}.input.mappings.{k}", v)

    def call(self, flow, act, subflow, inputs, iterate=None, desc=""):
        """Run a subflow. inputs = {subflow input: "=expr"}. iterate="=<array expr>" runs it once per item
        (read the item as $iteration[value]); outputs are $activity[<act>].<output> (an array when iterating).
        fda has no iterator flag: the task's type/settings are set with 'sa any ... --force' (designer format)."""
        self.activity(flow, act, "act_default_subflow", desc or f"Run {subflow}")
        self.fda("sa", "activity", f"{flow}.{act}.settings.flowURI", f"res://flow:{subflow}")
        for k, v in inputs.items():
            self.fda("mm", f"{flow}.{act}.input.{k}", v)
        if iterate:
            d = json.load(open(self.app, encoding="utf-8"))
            ri = next(i for i, r in enumerate(d["resources"]) if r["id"] == f"flow:{flow}")
            ti = next(i for i, x in enumerate(d["resources"][ri]["data"]["tasks"]) if x["id"] == act)
            base = f"resources.{ri}.data.tasks.{ti}"
            self.fda("sa", "any", f"{base}.type", "iterator", "--force")
            self.fda("sa", "any", f"{base}.settings.iterate", iterate, "--force")
            self.fda("sa", "any", f"{base}.settings.accumulate", "--jsonValue", "true", "--force")

    # ------------------------------------------------------------------ AI / RAG building blocks
    LLM_CONFIG_SCHEMA = {
        "type": "object", "additionalProperties": False, "title": "LLM Config Schema", "required": ["model", "provider"],
        "properties": {
            "provider": {"type": "string", "enum": ["OpenAI", "Gemini", "Anthropic", "Ollama", "vLLM", "AzureOpenAI"]},
            "anthropicProviderType": {"type": "string", "enum": ["Default", "Amazon Bedrock"]},
            "apiKey": {"type": "string"}, "model": {"type": "string"}, "providerBaseUrl": {"type": "string"},
            "temparature": {"type": "number", "enum": [round(x * 0.1, 1) for x in range(21)]},
            "reasoningEffort": {"type": "string"}, "azureDeployment": {"type": "string"},
            "azureApiVersion": {"type": "string"}, "azureRegion": {"type": "string"}, "azureResourceName": {"type": "string"}}}

    def openai(self, flow, act, kind, inputs, desc="", settings=None, outputs=None,
               url_prop="OPENAI_API_ENDPOINT_URL", key_prop="OPENAI_API_KEY"):
        """Activity of the repo-local openAI extension (act_openai_<kind>: vectorstorelist/create/delete, fileupload,
        vectorsearch, ...). fda must know the extension: run extend_fda_catalog.py and export FLOGO_DESIGN_CONFIG_FILE.
        Settings endPointURL/apiKey are bound to app properties; outputs = {field: json-schema} binds output schemas."""
        # These activities take a timeoutSeconds INPUT; fda writes its catalog default 0, and e.g. vectorStoreList
        # turns an explicit 0 into a 0-second deadline ("request timeout ... exceeded 0 seconds"). Default to 60.
        if kind in ("vectorstorelist", "vectorstoredelete", "vectorstorefilelist", "vectorstorecreate", "filelist",
                    "filedelete") and "timeoutSeconds" not in inputs:
            inputs = dict(inputs, timeoutSeconds=60)
        self.activity(flow, act, f"act_openai_{kind}", desc or f"OpenAI {kind}")
        self.fda("sa", "activity", f"{flow}.{act}.settings.endPointURL", url_prop, "--configType", "app-property")
        self.fda("sa", "activity", f"{flow}.{act}.settings.apiKey", key_prop, "--configType", "app-property")
        for k, v in (settings or {}).items():
            if isinstance(v, bool):
                self.fda("sa", "activity", f"{flow}.{act}.settings.{k}", "true" if v else "false", "-C", "boolean")
            elif isinstance(v, (int, float)):
                self.fda("sa", "activity", f"{flow}.{act}.settings.{k}", str(v), "-C", "number")
            else:
                self.fda("sa", "activity", f"{flow}.{act}.settings.{k}", v)
        for k, s in (outputs or {}).items():
            out = dict({"$schema": "http://json-schema.org/draft-04/schema#"}, **s)
            self.fda("sa", "activity", f"{flow}.{act}.schemas.output.{k}", "--jsonFile",
                     self.tmp(f"{flow}_{act}_{k}_out.json", jschema(out)), "--force")
        for k, v in inputs.items():
            self._set_input(flow, act, k, v)

    def llm(self, flow, act, system_prompt, user_prompt, desc="Ask the LLM",
            provider_prop="LLM_PROVIDER", key_prop="LLM_API_KEY", model_prop="LLM_MODEL", temperature=0.3):
        """Agentic AI LLM Client (no tools): answer = $activity[<act>].response."""
        self.activity(flow, act, "act_agenticai_llmclientactivity", desc)
        # fda seeds the optional dynamic-server lists as EMPTY mappings; the runtime skips them (len == 0), but the
        # designer then shows their required item fields (name, serverUrl) as blank warnings. Designer-made LLM
        # Client activities leave both unmapped, so remove them.
        for optional in ("mcpServerConfigs", "a2aServerConfigs"):
            self.fda("rmm", f"{flow}.{act}.input.{optional}")
        self.fda("sa", "activity", f"{flow}.{act}.schemas.input.llmConfiguration", "--jsonFile",
                 self.tmp(f"{flow}_{act}_llmcfg.json", jschema(self.LLM_CONFIG_SCHEMA)), "--force")
        for k, v in (("provider", f'=$property["{provider_prop}"]'), ("apiKey", f'=$property["{key_prop}"]'),
                     ("model", f'=$property["{model_prop}"]')):
            self.fda("mm", f"{flow}.{act}.input.llmConfiguration.mapping.{k}", v)
        self.fda("mm", f"{flow}.{act}.input.llmConfiguration.mapping.temparature", str(temperature), "--type", "number")
        self.fda("mm", f"{flow}.{act}.input.systemPrompt", system_prompt)
        self.fda("mm", f"{flow}.{act}.input.userPrompt", user_prompt)

    # ------------------------------------------------------------------ finish
    def finish(self):
        f = self.fda
        # Designer-safe link order (gotchas F37). The designer rebuilds each flow from `links` in stored order and
        # auto-saves on open, permanently DELETING every activity behind a link that was stored before the link
        # into its source (e.g. BadRequest -> ReturnBadRequest created before Log_API -> BadRequest). fda cm,
        # flogobuild and the runtime ignore link order, and over REST a lost branch Return is invisible - but every
        # MCP tool calling that flow as a subflow then fails. So re-store the links of EVERY flow in safe order
        # (root first; an activity's outgoing links after all its incoming links) BEFORE branch conditions are
        # applied below, then gate on the designer's own load algorithm.
        all_flows = list(self._ops) + [o["mcpFlow"] for o in self._ops.values() if o.get("mcpFlow")] + self._subflows
        for flow in all_flows:
            links = self.links(flow)
            tasks = [t["id"] for r in json.load(open(self.app, encoding="utf-8"))["resources"]
                     if r["id"] == f"flow:{flow}" for t in r["data"]["tasks"]]
            target = safe_order(tasks, links)
            k = next((i for i, (a, b) in enumerate(zip(links, target)) if (a["from"], a["to"]) != (b["from"], b["to"])), len(links))
            for l in links[k:]:
                f("rl", flow, l["from"], l["to"])
            for l in target[k:]:
                f("cl", flow, l["from"], l["to"])
        for flow, branches in self._branches.items():
            for frm, to, expr in branches:
                idx = next(i for i, l in enumerate(self.links(flow)) if l["from"] == frm and l["to"] == to)
                f("sa", "flow", f"{flow}.links[{idx}].type", "expression")
                f("sa", "flow", f"{flow}.links[{idx}].value", expr, "--force")
        for flow in list(self._ops) + [o["mcpFlow"] for o in self._ops.values() if o.get("mcpFlow")] + self._subflows:
            f("ff", flow, "auto")
        fails, summary, _ = f.cm()
        print(f"\ncm: {summary[-1].split(')', 1)[-1].strip() if summary else '?'}")
        # documented fda cm false positives: filtered @foreach, $iteration (RESOLVER_UNKNOWN), subflow outputs
        # (ACTIVITY_OUTPUT_LEAF_UNKNOWN) - all valid at runtime (see references/gotchas.md)
        known = ("FOREACH_SCOPE_UNDEFINED",) + (("RESOLVER_UNKNOWN", "ACTIVITY_OUTPUT_LEAF_UNKNOWN") if self._subflows else ())
        real = [x for x in fails if not any(k in x for k in known)]
        for x in fails:
            print(("  known false positive: " if x not in real else "  FAIL ") + re.sub(r"\s+", " ", x)[:120])
        for flow in self._ops:
            print(f"  {flow}: " + ", ".join(f"{l['from']}->{l['to']}" + (f" [{l.get('value')}]" if l.get("type") == "expression" else "")
                                         for l in self.links(flow)))
        lost = designer_drops(self.app)  # gate: would the designer delete anything when the user opens the app?
        print(f"designer load check: {'OK - every activity survives opening in the designer' if not lost else 'FAIL'}")
        for flow, acts in lost.items():
            print(f"  FAIL {flow}: the designer would delete {', '.join(acts)} on open (link order, gotchas F37)")
        return 1 if real or lost else 0
