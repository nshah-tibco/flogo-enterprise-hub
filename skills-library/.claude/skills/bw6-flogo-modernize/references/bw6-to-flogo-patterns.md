# BW6 → Flogo translation patterns

How to turn what `analyze_bw6.py` decoded into Flogo logic. "Verified" = proven by a parity run;
"planned" = the intended approach, verify with `parity_check.py` before relying on it.

## Process structure

| BW6 | Flogo | Status |
|---|---|---|
| `pick` / `onMessage(operation, partnerLink)` per REST operation | one flow per operation (`cas`), handler on the `tr_rest` trigger | verified |
| `reply` with XSLT (partBinding) | `ConfigureHTTPResponse` (typed `{body}` wrapper) → `Return`, field-by-field `mm` | verified |
| several replies / fault replies | extra `act_general_httpresponse` + `actreturn` per status code, conditional links | verified |
| `bpws:link` with condition | `cl` + link `type=expression`, `value=<expr>` | verified |
| scope + `catch`/`catchAll` | flow error handler or error branch reading `$error[<Activity>].message` | planned |
| several conditional links converging on one activity (branch join) | link each branch end to the join activity; Flogo runs it once the taken branch finishes (verified with three alternative INSERTs → one UPDATE) | verified (`examples/operations_logic.py`) |
| `Throw` / no reply on a branch (BW: 500 / "missing reply") | explicit JSON error branch: 400 invalid input, 403 not allowed, 404 not found, 422 unsupported | verified |
| subprocess call | `act_default_subflow` (`settings.flowURI = res://flow:<name>`) | verified (MCP flows) |
| group `Iterate` over a list + `accumulate` | `Logic.subflow(...)` for the loop body + `Logic.call(..., iterate="=<array>")` (task type `iterator`, items as `$iteration[value]`, outputs accumulated) | verified (`examples/policy_logic.py`) |

## Activities

| BW6 `activityTypeID` | Flogo | Status / notes |
|---|---|---|
| `bw.restjson.JsonParser` over a literal | `Logic.static_data` / `static_dataset` (several arrays, schemas inferred): mapper seeded by `mm --jsonValue` (a JSON literal in parsejson's string field is flagged by the designer). **Use each operation's own BW literal** (`L.bw_json(flow, name)`) — BW branches often carry diverging copies | verified |
| `bw.restjson.JsonParser` over a runtime string | `act_general_parsejson` + `schemas.output.jsonObject` | planned |
| `bw.restjson.JsonRender` | `utility.renderJSON(obj, false)` in a mapping | verified (MCP flows) |
| `bw.generalactivities.mapper` | `act_general_mapper` (`sms <flow>.<act>.input` + `mm .input.input.mapping.<field>`) | verified |
| `bw.generalactivities.log` | `act_general_log` | verified |
| `bw.jdbcResource` (shared resource) | `Logic.db_connection(name, dbURL, user, password)` → `con_sqlserver`, password stored as `SECRET:` | verified (SQL Server) |
| `bw.jdbc.JDBCQuery` | `Logic.sql(flow, name, "query", sql, conn, params, columns)` → `act_sqlserver_query`; rows at `$activity[X].Output.records` | verified (SQL Server) |
| `bw.jdbc.update` (INSERT / UPDATE) | `Logic.sql(..., "insert"|"update", ...)`; `$activity[X].Output.rowsAffected` replaces BW `noOfUpdates` | verified (SQL Server) |
| `bw.jdbc.SQLDirect` with a fixed statement batch | one `Logic.sql(..., "delete"|"update", ...)` per statement, chained (not `act_sqlserver_sqldirect`, which opens its own dynamic connection) | verified (reset) |
| BW positional `?` parameters | rename to `?name` in the order of the BW input XSLT; `Logic.lint_sql` enforces the bind rules | verified |
| JDBC Query over other DBs (Postgres, MySQL, Oracle) | same helper shape with that connector's activities | planned |
| `bw.restjson.Rest` / HTTP client | `act_general_rest` or `act_http_client` (`http_client` for binary) | planned |
| `bw.java.javamethod` | **first check the analyzer's "not used by the reply" list** — a Java converter + ParseXml were dead code in `examples/inventory_logic.py` (verified). Otherwise try mapper functions (string/json/array/datetime); else a Flogo Go extension | verified (dead-code case) / planned |
| `parsexml` | `act_general_xmltojson` (skip it when it only feeds a dead Java step) | planned |
| BW AI plugin RAG (`chunk`, `ingest`, `query`) — verified variant | repo-local `extensions/openAI`: `ResolveStore` subflow (vectorStoreList -> find by name; reset = delete + create; missing = create), `AddDocument` subflow (`act_file_write` the text, then `fileupload` into the store with the document metadata as `fileAttributes`), query = `vectorsearch` -> normalize rows -> `Logic.llm` answer (Agentic AI LLM Client). Metadata comes back in the search rows' attributes, so nothing is inferred from chunk text | verified (`examples/policy_logic.py`, SEMANTIC parity) |
| BW AI plugin RAG (`chunk`, `ingest`, `query`) — alternatives | Agentic AI `ChunkAndEmbedDocuments` + vector activities (ActiveSpaces only in 2.26.9) or REST calls to the vector DB (e.g. Weaviate) + LLM Client | planned — decide with the user |
| accumulate / iterate groups | activity iterator or `@foreach` mapping | planned |

## XSLT → Flogo expressions

| XSLT | Flogo mapping | Status |
|---|---|---|
| `<xsl:value-of select="'literal'"/>` | `"literal"` (no `=`) | verified |
| `<xsl:value-of select="10"/>`, `true()` | `mm ... 10 --type number`, `true --type boolean` | verified |
| `$get.parameters/tns:x` (query param) | `=$flow.queryParams.x` | verified |
| `$get.parameters/tns:x` (path param, `/items/{x}`) | `=$flow.pathParams.x` | verified (`examples/orders_logic.py`) |
| `$post.item/tns:x` (body field) | `=$flow.body.x` | verified |
| `<xsl:if test="x">` around an optional field | plain mapping + `FLOGO_MAPPING_OMIT_NULLS=true` | verified |
| `<xsl:for-each select="$A/item[key = $p]">` | `Logic.select(...)` → `@foreach(src, it, $loop[it].key == <p>)`; read `$activity[M].output.<field>[0].x` | verified |
| repeated literal element (`<items>…</items>`) | `mm <path> --jsonValue '[{...}]'` (typed array) | verified |
| `concat(a, b)` | `string.concat(a, b)` | verified |
| `xsl:choose` / `when` | ternary `cond ? a : b` at the top level of a mapping (functions inside the branches are fine; a ternary *inside* a function argument is not) | verified (`examples/orders_logic.py`) |
| `count($x)` | `array.count($x)` | verified (link conditions) |
| `current-dateTime()` | `datetime.now()` | planned |
| `days-from-duration(date(a) - date(b))` | `datetime.diff(datetime.parse(b, "UTC"), datetime.parse(a, "UTC"), "days")` (= a - b, float) + `coerce.toInt` | verified (`examples/orders_logic.py`) |
| `abs(x)` | no Flogo `abs()`: `x < 0 ? coerce.toInt(0 - x) : coerce.toInt(x)` at the top level | verified |
| `<xsl:variable name="v" select="..."/>` | `Logic.compute(...)`: a mapper of typed derived values read as `$activity[<M>].output.v`; chain two when one depends on another | verified |
| nested `for-each[key = current()/x]` (join) | a second `Logic.select` whose predicate reads the first match: `$loop[p].key == $activity[FindParent].output.matches[0].key` | verified (`examples/orders_logic.py`) |
| `concat("...", string($n), "...")` | `string.concat("...", coerce.toString($n), "...")` | verified |
| `x <= y` as a boolean field | `=$a <= $b` mapped to a boolean field | verified |
| `$post.item/x` used as a lookup key | `Logic.require_params(..., body_fields=("x",))` + `$flow.body.x` in the select predicate | verified (`examples/inventory_logic.py`) |
| `xsl:copy-of` + a synthetic record appended when nothing matches ("unknown") | one response branch per outcome (found / unknown-with-name / unknown), each its own `httpresponse` 200 + conditional link; conditions must be mutually exclusive and exhaustive | verified (`examples/inventory_logic.py`) |
| `choose/when string-length(x) > 0 … otherwise ''` | `=coerce.toString(x)` (nil → "") | verified |
| a static list reshaped by the XSLT (fields dropped/emptied) | apply the same reshaping in the logic script to the BW literal and map it as a typed `--jsonValue` | verified (`examples/inventory_logic.py`) |
| `tib:parse-json` / `tib:render-json` | `json.*` functions / `utility.renderJSON` | planned |

## Data the BW6 app hardcodes

BW demo modules often return literals from XSLT (`analyze_bw6.py` lists them per operation under
`literals`). Keep them as literals in the Flogo mappings; for lookup data load the BW JSON literal into a
`static_data` mapper so both apps hold the same records.

## Extension / SDK outputs

| Situation | Flogo | Status |
|---|---|---|
| an extension activity returns typed Go/SDK structs (e.g. `[]*openai.VectorStoreSearchResponse`) | normalize once in a mapper: `coerce.toArray(coerce.toString($activity[X].<field>))` with a typed schema, then map fields / `json.jq` from that; SDK unions serialize as `{"OfString": ..}` | verified |
| a literal list/object containing `=expressions` as an activity input (e.g. `fileAttributes`) | store it under `{"mapping": <value>}` (`Logic._set_input` does) — a bare literal is passed verbatim | verified |
| BW `base64-to-string(x)` | `string.base64ToString(x)` | verified |
