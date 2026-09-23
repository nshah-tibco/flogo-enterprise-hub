#!/usr/bin/env python3
"""Pre-ship validator for Agentic AI .flogo apps — nothing app-specific is hardcoded.

Catches the two defect classes that recur when hand-authoring/cloning these apps:

  1. PostgreSQL #query/#insert/#update mapping-mode integrity. A write activity is valid in EITHER
     values-mode (Fields[].Value=true, mapping under input.mapping.values[0], schema under
     values.items.properties) OR parameters-mode (Fields[].Parameter=true, mapping under
     input.mapping.parameters, schema under parameters.properties). What breaks is a HYBRID where the
     Fields flag points at one container but the mapping/schema live in the other — the designer then
     reads the empty container and shows no mappings. See postgres-activity-patterns.md.
       - every ?placeholder in the Query is mapped exactly once (else runtime 'missing substitution')
       - Fields[] is non-empty on any write
       - the populated schema container's names == the mapping keys
       - input.State is a verbatim copy of input.Query
  2. Password-typed connector fields (e.g. #sendmail 'Password'). The designer DERIVES dataType=password
     from a leading 'SECRET:' on the value; a plain string makes it infer dataType=string and the field
     errors with wrongTypeProp. So a password-bound app property must resolve to a SECRET: value (a
     designer-produced dummy is fine — it decrypts under Flogo's default data-secret key and leaks
     nothing), never a plain placeholder.

Also verifies A2A flows that read $flow.toolParams declare a toolParams flow-input schema (part #2 of
the 3-part designer contract).

Usage:
    python validate_flogo_apps.py <app1.flogo> [app2.flogo ...]   # explicit files
    python validate_flogo_apps.py                                 # scan **/*.flogo under cwd
Exit code 0 = clean, 1 = one or more problems (printed). No hardcoded app/column/property/blob names.
"""
import json, re, sys, glob, os

PG_REFS = ("#query", "#insert", "#update")


def _flag(v):
    """Fields[].Value / .Parameter appear as JSON booleans in some apps and as the STRINGS
    'true'/'false' in others — normalize both (a bare non-empty string like 'false' is truthy in
    Python, which would otherwise misread parameters-mode as values-mode)."""
    if isinstance(v, str):
        return v.strip().lower() == "true"
    return bool(v)


def _schema_names(schema_str, container):
    """Names declared under a schema container ('values' -> items.properties, else .properties)."""
    try:
        s = json.loads(schema_str)
    except Exception:
        return set()
    node = s.get("properties", {}).get(container, {}) or {}
    if container == "values":
        node = node.get("items", {}) or {}
    return set((node.get("properties", {}) or {}).keys())


def _resolve_property(app, expr):
    """'=$property[Name]' -> (name, value) from the app's top-level properties; (name, None) if absent."""
    m = re.search(r"\$property\[([^\]]+)\]", expr or "")
    if not m:
        return None, None
    name = m.group(1).strip("'\"")
    for p in app.get("properties", []) or []:
        if p.get("name") == name:
            return name, p.get("value")
    return name, None


def check_app(path):
    problems = []
    with open(path, encoding="utf-8") as fh:
        app = json.load(fh)

    tasks = []
    for res in app.get("resources", []) or []:
        data = res.get("data", {}) or {}
        for t in data.get("tasks", []) or []:
            tasks.append((res, t))
        # 3-part contract, part #2: flow reads $flow.toolParams but declares no toolParams input schema
        if "$flow.toolParams" in json.dumps(res):
            md_in = data.get("metadata", {}).get("input", []) or []
            tp = next((i for i in md_in if i.get("name") == "toolParams"), None)
            if not (tp and tp.get("schema", {}).get("value")):
                problems.append(f"{res.get('id')}: reads $flow.toolParams but has no toolParams "
                                f"flow-input schema (click the trigger Sync)")

    for res, t in tasks:
        a = t.get("activity", {}) or {}
        ref = a.get("ref", "")
        inp = a.get("input", {}) or {}
        tid = t.get("id")
        if not isinstance(inp, dict):
            continue

        # ---- PostgreSQL activities -------------------------------------------------------------
        if ref in PG_REFS and "Query" in inp:
            q = inp.get("Query", "") or ""
            placeholders = sorted(set(re.findall(r"\?(\w+)", q)))
            fields = inp.get("Fields", []) or []
            is_write = ref in ("#insert", "#update") or \
                q.strip().upper().startswith(("INSERT", "UPDATE", "DELETE"))

            mapping = inp.get("input", {}).get("mapping", {}) if isinstance(inp.get("input"), dict) else {}
            val_map = mapping.get("values")
            par_map = mapping.get("parameters")
            mapped = set()
            if isinstance(val_map, list) and val_map and isinstance(val_map[0], dict):
                mapped |= set(val_map[0].keys())
            if isinstance(par_map, dict):
                mapped |= set(par_map.keys())

            # every ?placeholder must be mapped (any mode)
            missing = [p for p in placeholders if p not in mapped]
            if missing:
                problems.append(f"{tid}: ?placeholders with no mapping -> runtime "
                                f"'missing substitution': {missing}")
            # writes need column metadata
            if is_write and not fields:
                problems.append(f"{tid}: write activity has empty Fields[] (designer shows no columns)")
            # State mirrors Query (design-time SQL cache; 184/196 shipped activities keep State=uuid+Query)
            st = inp.get("State", "") or ""
            if st and q and q not in st:
                problems.append(f"{tid}: input.State has no verbatim copy of input.Query "
                                f"(design-time SQL cache is stale/bare — set State = uuid + Query)")

            # mode integrity: Fields[].Value is the AUTHORITATIVE mode signal. In values-mode the mapped
            # fields carry Value=true (they also carry Parameter=true, so Parameter is NOT a mode
            # signal); in parameters-mode the mapped fields are Parameter=true with Value=false. The
            # mapping container and schema container must both agree with that flag.
            schema_str = a.get("schemas", {}).get("input", {}).get("input", {}).get("value", "")
            sp_val = _schema_names(schema_str, "values")
            sp_par = _schema_names(schema_str, "parameters")
            has_val_map = isinstance(val_map, list) and bool(val_map) and bool(val_map[0])
            has_par_map = isinstance(par_map, dict) and bool(par_map)
            value_fields = [f for f in fields if _flag(f.get("Value"))]
            param_only_fields = [f for f in fields if _flag(f.get("Parameter")) and not _flag(f.get("Value"))]
            flag_mode = "values" if value_fields else ("parameters" if param_only_fields else None)

            if flag_mode == "values":
                if (has_par_map or sp_par) and not has_val_map and not sp_val:
                    problems.append(f"{tid}: HYBRID — Fields[].Value=true says values-mode, but the "
                                    f"mapping/schema are under 'parameters'. Move the mapping to "
                                    f"input.mapping.values[0] and the schema names to "
                                    f"values.items.properties (or flip Fields to parameters-mode).")
                else:
                    if not has_val_map:
                        problems.append(f"{tid}: values-mode but no mapping under input.mapping.values[0]")
                    if has_par_map:
                        problems.append(f"{tid}: values-mode but a stray parameters mapping is also present")
                    if sp_par:
                        problems.append(f"{tid}: values-mode but schema still declares "
                                        f"parameters.properties {sorted(sp_par)} (should be empty)")
                    if has_val_map and not sp_val:
                        problems.append(f"{tid}: values-mode but schema has no values.items.properties names")
            elif flag_mode == "parameters":
                if (has_val_map or sp_val) and not has_par_map and not sp_par:
                    problems.append(f"{tid}: HYBRID — Fields[] say parameters-mode, but the mapping/schema "
                                    f"are under 'values'. Move the mapping to input.mapping.parameters and "
                                    f"the schema names to parameters.properties (or flip Fields to "
                                    f"values-mode).")
                else:
                    if not has_par_map:
                        problems.append(f"{tid}: parameters-mode but no mapping under input.mapping.parameters")
                    if has_val_map:
                        problems.append(f"{tid}: parameters-mode but a stray values mapping is also present")
                    if sp_val:
                        problems.append(f"{tid}: parameters-mode but schema still declares "
                                        f"values.items.properties {sorted(sp_val)} (should be empty)")
                    if has_par_map and not sp_par:
                        problems.append(f"{tid}: parameters-mode but schema has no parameters.properties names")

            # populated schema container names must equal the mapping keys
            declared = (sp_val | sp_par)
            if declared and mapped and declared != mapped:
                problems.append(f"{tid}: schema names {sorted(declared)} != mapping keys "
                                f"{sorted(mapped)}")

        # ---- password-typed connector fields (e.g. #sendmail Password) -------------------------
        for key, v in inp.items():
            if key.lower() != "password" or not isinstance(v, str) or not v:
                continue
            if v.startswith("=$property["):
                pname, pval = _resolve_property(app, v)
                if pval is not None and not str(pval).startswith("SECRET:"):
                    problems.append(f"{tid}.{key}: bound property '{pname}' value is a plain string, not "
                                    f"SECRET: — designer infers dataType=string -> wrongTypeProp")
            elif not v.startswith("=") and not v.startswith("SECRET:"):
                problems.append(f"{tid}.{key}: literal plain-string password; bind to a SECRET: app "
                                f"property instead (a designer-produced dummy is fine)")

    return problems


def main():
    files = sys.argv[1:] or glob.glob("**/*.flogo", recursive=True)
    total = 0
    for f in files:
        try:
            probs = check_app(f)
        except Exception as e:
            print(f"[PARSE-FAIL] {f}: {e}")
            total += 1
            continue
        for p in probs:
            print(f"[{os.path.basename(f)}] {p}")
        total += len(probs)
    print(f"\n{'OK - no issues' if total == 0 else str(total) + ' issue(s) found'} "
          f"across {len(files)} file(s)")
    sys.exit(0 if total == 0 else 1)


if __name__ == "__main__":
    main()
