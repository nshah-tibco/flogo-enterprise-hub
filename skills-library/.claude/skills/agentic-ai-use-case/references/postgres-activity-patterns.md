# PostgreSQL Activity Patterns (the gotchas that cause mapper errors)

The `wi-postgres` `#query` and `#insert` activities parameterize via `?placeholder` in the SQL,
`Fields[]` entries, an `input.mapping` object, and a `schemas.input.input.value` JSON-Schema string.
Get any of these out of alignment and the Flogo mapper shows a red ✗ on the activity's Input tab.

**Golden rule (activity level):** for a given activity, the set of `?params` in the Query must exactly
equal the `Fields` param names, the `input.mapping.parameters` keys, and the schema's
`parameters.properties` keys. Never use `RuntimeQuery` for parameters. Verify by running the real SQL
against a loaded DB.

**Two levels of wiring.** The golden rule above is the *activity-level* alignment. Inside an **A2A agent
flow** there is a second, *flow-level* piece: the flow must declare `toolParams` as a flow input (with a
schema) so `=$flow.toolParams.<field>` resolves in the designer. Miss it and the mapper shows a red ✗
even when the SQL is perfect. The full picture is a **3-part contract** — see the next section.

---

## The 3-part designer contract (A2A agent flows)

An A2A write agent receives its inputs from the LLM as `toolParams` and feeds them to a `#query`/`#insert`.
For that to both **run** and **validate in the designer**, three things must agree. The trigger **Sync**
button regenerates all three together.

| # | Where | What it is | Symptom if missing/wrong |
|---|-------|-----------|--------------------------|
| 1 | `activity.input.input.mapping.parameters.<placeholder>` = `"=$flow.toolParams.<field>"` | **Runtime mapping** — the ONLY part the engine reads at run time | runtime error `query execution failed: missing substitution for: <name>` |
| 2 | flow input schema: `resource.data.metadata.input[name=toolParams].schema` = `{"type":"json","value":"<compact-properties-json>"}` | **Flow-input schema** — tells the designer `$flow.toolParams.<field>` exists | design-time red ✗ on `$flow.toolParams.<field>` |
| 3 | `activity.schemas.input.input.value` (draft-04, with `properties.parameters.properties.<p>`) | **Activity-input schema** — tells the designer the mapping *target* exists | design-time red ✗ on the activity Input tab |

Only **#1 runs**; #2 and #3 are design-time validation only (the engine ignores `schemas` blocks at run
time). Therefore:

- To make a broken/generated app **run**, hand-patch **#1** — that alone clears `missing substitution`.
- To make it **validate** (clear every red ✗), the cleanest path is: hand-patch #1, then open each agent
  flow and click the trigger **Sync** — the designer regenerates #2 and #3 consistently. The #3 draft-04
  blob is error-prone to hand-write; let Sync emit it. (Lesson: patching #1 and #2 but forgetting #3
  leaves the red ✗; Sync fixes all three.)
- If you must hand-write #2: its `value` is the **compact `properties` object only** — i.e.
  `{"<field>":{"type":"string"},...}` serialized to a string — NOT the full `type`/`required` wrapper.

**A query-text-only change keeps all three parts valid.** If you edit only the SQL string (and the `State`
copy of it) **without changing the `?placeholder` set**, #1/#2/#3 still align, so no Sync is needed. This
is what makes the derive-FK pattern in Section D a safe surgical patch.

> ⚠️ **Never write to a `.flogo` that is open in the Flogo web designer.** A disk write races with the
> designer's unsaved in-memory state; if the user clicked **Sync** but not **Save**, your patch is
> invisible and their Sync is lost on reload ("your fix messed up my mappings"). Tell the user to Save or
> set aside unsaved work first, patch on disk, then **Discard** unsaved changes and reload so the app
> picks up the on-disk fix. Prefer on-disk patching (covers all flows at once) over dictating manual steps.

---

## A. Read-only tool query (MCP server) — no parameters

`SELECT * FROM <table>` returning all rows (the LLM filters). Every column is a result Field with
`Parameter:false`; there are no params.

```json
{
  "id": "PostgreSQLQuery",
  "settings": { "retryOnError": { "count": 0, "interval": 0 } },
  "activity": {
    "ref": "#query",
    "input": {
      "Connection": "conn://<pg-uuid>",
      "Schema": "public",
      "Query": "SELECT * FROM public.<table> ORDER BY <col> ASC;",
      "manualmode": false,
      "Fields": [
        { "FieldName": "<col1>", "Type": "VARCHAR",  "Selected": true, "Parameter": false, "isEditable": false },
        { "FieldName": "<col2>", "Type": "INTEGER",  "Selected": true, "Parameter": false, "isEditable": false },
        { "FieldName": "<col3>", "Type": "NUMERIC",  "Selected": true, "Parameter": false, "isEditable": false }
      ],
      "RuntimeQuery": "",
      "State": "<uuid><the same SELECT statement>"
    },
    "schemas": {
      "input":  { "input":  { "type": "json", "value": "{\"$schema\":\"http://json-schema.org/draft-04/schema#\",\"type\":\"object\",\"definitions\":{},\"properties\":{\"parameters\":{\"type\":\"object\",\"properties\":{}}}}" } },
      "output": { "Output": { "type": "json", "value": "{\"$schema\":\"http://json-schema.org/draft-04/schema#\",\"type\":\"object\",\"definitions\":{},\"properties\":{\"records\":{\"type\":\"array\",\"items\":{\"type\":\"object\",\"properties\":{\"<col1>\":{\"type\":\"string\"},\"<col2>\":{\"type\":\"integer\"},\"<col3>\":{\"type\":\"number\"}}}}}}" } }
    }
  }
}
```
Column `Type` → schema type: `VARCHAR/DATE/TIMESTAMP` → `"string"`, `INTEGER` → `"integer"`, `NUMERIC` → `"number"`. `State` must be present (any uuid prefix + the query string).

---

## B. Parameterized SELECT or UPDATE — params under `parameters`

A **SELECT with a WHERE**, or any **UPDATE** (`#insert` activity with an UPDATE statement), has no
INSERT column-list, so **all `?placeholders` are parameters** and can safely reuse column names.

```json
"input": {
  "Connection": "conn://<pg-uuid>",
  "Schema": "public",
  "Query": "SELECT a.col1, b.col2 FROM t1 a JOIN t2 b ON ... WHERE a.key = ?key ORDER BY a.id ASC;",
  "manualmode": false,
  "Fields": [
    { "FieldName": "key",  "Type": "LONGVARCHAR", "Selected": false, "Parameter": true,  "isEditable": false },
    { "FieldName": "col1", "Type": "VARCHAR",     "Selected": true,  "Parameter": false, "isEditable": false },
    { "FieldName": "col2", "Type": "VARCHAR",     "Selected": true,  "Parameter": false, "isEditable": false }
  ],
  "RuntimeQuery": "",
  "State": "<uuid><the query>",
  "input": { "mapping": { "parameters": { "key": "=$flow.toolParams.key" } } }
}
```
Schema `input.value`: `{"...","properties":{"parameters":{"type":"object","properties":{"key":{"type":"string"}}}}}`.
(For UPDATE via `#insert`: same idea — `Fields` params `Parameter:true, Value:false`, schema has
`values.items.properties:{}` empty and `parameters.properties` = the params.)

---

## C. INSERT — THE ONE THAT BREAKS. Suffix placeholder names so they DON'T match columns.

For `INSERT INTO t (colA, colB, ...) VALUES (?...)`, the designer auto-classifies each `?placeholder`:
a placeholder whose **name matches a column in the column-list** is moved to the `values` slot; a
name that **doesn't match** stays a `parameter`. If you map everything under `parameters` (the pattern
that works at runtime) but your placeholder names equal the column names, the designer moves them to
`values`, the parameters mapping no longer lines up, and you get the red ✗ (the mapping collapses to a
single object at the top of the mapper).

**Fix (canonical — matches the shipped `PostgreSQL-CRUD` sample `?id1, ?name1, …`):** name every
INSERT placeholder so it does **not** match any column — append a digit or suffix (`?colA1`). Then all
placeholders stay parameters, and the parameters mapping is clean AND runtime-correct.

```json
{
  "id": "PostgreSQLInsert",
  "settings": { "retryOnError": { "count": 0, "interval": 0 } },
  "activity": {
    "ref": "#insert",
    "input": {
      "Connection": "conn://<pg-uuid>",
      "Schema": "public",
      "Query": "INSERT INTO t (colA, colB, amount, status) VALUES (?colA1, ?colB1, ?amount1, 'OPEN');",
      "manualmode": false,
      "Fields": [
        { "FieldName": "colA1",   "Type": "VARCHAR", "Selected": false, "Parameter": true, "isEditable": false, "Value": false },
        { "FieldName": "colB1",   "Type": "VARCHAR", "Selected": false, "Parameter": true, "isEditable": false, "Value": false },
        { "FieldName": "amount1", "Type": "NUMERIC", "Selected": false, "Parameter": true, "isEditable": false, "Value": false }
      ],
      "RuntimeQuery": "",
      "State": "<uuid><the INSERT statement>",
      "input": { "mapping": { "parameters": {
        "colA1":   "=$flow.toolParams.colA",
        "colB1":   "=$flow.toolParams.colB",
        "amount1": "=$flow.toolParams.amount"
      } } }
    },
    "schemas": {
      "input":  { "input":  { "type": "json",
        "value": "{\"$schema\":\"http://json-schema.org/draft-04/schema#\",\"type\":\"object\",\"definitions\":{},\"properties\":{\"values\":{\"type\":\"array\",\"items\":{\"type\":\"object\",\"properties\":{}}},\"parameters\":{\"type\":\"object\",\"properties\":{\"colA1\":{\"type\":\"string\"},\"colB1\":{\"type\":\"string\"},\"amount1\":{\"type\":\"number\"}}}}}" } },
      "output": { "Output": { "type": "json",
        "value": "{\"$schema\":\"http://json-schema.org/draft-04/schema#\",\"type\":\"object\",\"definitions\":{},\"properties\":{\"records\":{\"type\":\"array\",\"items\":{\"type\":\"object\",\"properties\":{}}}}}" } }
    }
  }
}
```

Rules for INSERT:
- **Placeholder names ≠ column names** (append `1`/suffix). Positional order still maps them to the
  right columns; the name is only a bind identifier.
- Every param Field: `Parameter:true, Value:false`.
- Schema: `values.items.properties` **empty `{}`**; put all params under `parameters.properties`.
- Map under `input.mapping.parameters`, keyed by the suffixed names → `=$flow.toolParams.<realName>`.
- Literals (`'OPEN'`, `CURRENT_DATE`, `CURRENT_DATE + INTERVAL '5 days'`, `CURRENT_TIMESTAMP`) go
  straight in the SQL — no placeholder needed.
- Also keep the copy of the statement in `State` in sync with `Query`.

Note: `fe_metadata` mirrors `value` in each schema block — set both to the same string.

---

## D. Deriving a NOT-NULL foreign key the prompt never carries (INSERT … SELECT)

Write agents often INSERT into a table with a **NOT-NULL foreign-key column** (e.g. an owner/account id)
that a natural-language prompt will never contain — the user names an entity by a *friendly* key (an order
number, a tracking code, an email), not by the internal FK. If the INSERT maps that FK column from
`=$flow.toolParams.<fk>`, the LLM sends null and you get
`pq: null value in column "<fk>" violates not-null constraint`. The agent then stalls, asking the user for
an id they don't know.

**Fix — derive the FK in SQL from the parent row the user DID name.** When the flow can look up a parent
by a provided key, rewrite the INSERT as `INSERT … SELECT` that pulls the FK from that parent row, with
`COALESCE(NULLIF(?fk,''), parent.<fk>)` so an explicitly-supplied value still wins:

```sql
INSERT INTO public.<child> (<key_col>, <fk_col>, <c3>, <c4>, status)
SELECT p.<key_col>, COALESCE(NULLIF(?p2,''), p.<fk_col>), ?p3, NULLIF(?p4,'')::date, 'Requested'
FROM   public.<parent> p
WHERE  p.<key_col> = ?p1;
```

Rules:
- **Keep the same `?placeholder` set** (`?p1…?pN` all still referenced). This is a **query-text-only**
  change, so the 3-part contract above stays aligned — no Sync, no red ✗ (patch `Query` **and** `State`).
- Reference the lookup key `?p1` **once**, in the `WHERE`; take every derived column from the
  `SELECT … FROM <parent>` row. Referencing the same placeholder twice invites duplicate-param ambiguity.
- Use `NULLIF(?p,'')` to treat the LLM's empty string as "not supplied", then apply `::date` / `::numeric`
  casts *after* the `NULLIF`.
- **Validate before shipping** with a rolled-back transaction:
  `BEGIN; INSERT … RETURNING *; ROLLBACK;`.
- Applies whenever the child has a NOT-NULL FK derivable from a parent the prompt DOES name. It does
  **not** apply when there is no parent to derive from — then the FK is a genuine required input the
  orchestrator/agent must collect or default explicitly.

---

## Consistency check (run after authoring any A2A app)

```python
import json, re
d = json.load(open("<App>A2AServers.flogo", encoding="utf-8"))
for res in d["resources"]:
    for t in res["data"]["tasks"]:
        a = t.get("activity", {})
        if a.get("ref") not in ("#insert", "#query"): continue
        inp = a["input"]
        qp = sorted(re.findall(r"\?(\w+)", inp["Query"]))
        fp = sorted(f["FieldName"] for f in inp["Fields"] if f.get("Parameter"))
        mp = sorted(inp.get("input", {}).get("mapping", {}).get("parameters", {}).keys())
        sp = sorted(json.loads(a["schemas"]["input"]["input"]["value"])["properties"]["parameters"]["properties"].keys())
        assert qp == fp == mp == sp, (t["id"], qp, fp, mp, sp)
print("all query/insert params aligned")
```
For INSERTs also assert `values.items.properties` is empty and that no `?param` equals a target column name.

Also verify each agent flow declares the **flow-input `toolParams` schema** (part #2 of the 3-part
contract) — a flow that reads `$flow.toolParams.*` but has no `toolParams` input schema will red-✗ in the
designer:

```python
for res in d["resources"]:
    md_in = res.get("data", {}).get("metadata", {}).get("input", [])
    tp = next((i for i in md_in if i.get("name") == "toolParams"), None)
    uses_tp = "$flow.toolParams" in json.dumps(res)
    assert not uses_tp or (tp and tp.get("schema", {}).get("value")), (res.get("id"), "missing toolParams flow-input schema — click trigger Sync")
print("all agent flows declare toolParams input schema")
```
