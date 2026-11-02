# Flogo apps with the FDA skills (Sydney Water Flogo Workshop)

You build TIBCO Flogo 2.26 apps (`.flogo` files) for an integration developer. The `fda` skills
(`fda`, `fda-mapping`, `flogobuild`, `flogo-unit-testing`) document the Flogo Design Assistant CLI.

## Tools and workflow
- **Load the skills first.** Before the first fda command of a task, load the `fda` skill and the
  `fda-mapping` skill. Follow their "Things to avoid" and "Designer-only rules".
- **Run fda as `~/FlogoLab/cline/tools/fda`.** It is a wrapper that finds `flogodesign-cli` in the
  installed Flogo VS Code extension (never hard-code the extension folder). Wherever a skill shows
  `fda <task> ...`, run `~/FlogoLab/cline/tools/fda <task> ...`. Start with `~/FlogoLab/cline/tools/fda version`.
  If it is missing, ask the user to run `bash ~/FlogoLab/cline/setup-flogo-skills.sh`.
- **Change `.flogo` files only with fda.** Never write, patch or regenerate `.flogo` JSON with file tools,
  python, sed or jq. If fda cannot do something, list it for the user to finish in the Flogo designer.
- Always pass `-f <full path to the .flogo>`. Create the folder first (`mkdir -p`). `fda cp` creates the file.
- One fda change per command (you may chain a few simple ones with `&&`). Read each result; if it says
  `(ERROR)`, fix that step before going on. `~/FlogoLab/cline/tools/fda help <task>` shows the flags.
- Put expressions in **single quotes** so bash does not expand `$`: `'=$flow.body.siteId'`. A mapping value
  that is an expression starts with `=`; a literal has no `=`. Always qualify functions (`string.concat`).
- Do not use `fda ff` / format-flow (it can delete activities). Do not hand-edit JSON. Do not use `--force`
  except where these rules or the skills show it.
- Do not build or run the app (no `flogobuild`, no Go) unless the user asks: participants run it from the
  designer (Run as Executable).
- Finish every build with `~/FlogoLab/cline/tools/fda cm -f <file>` and
  `python3 ~/FlogoLab/cline/tools/validate_flogo_apps.py <file>`. `TR_REST_NO_SWAGGER` from `cm` is a known
  false positive for a REST trigger without a spec: ignore it, never create a spec, never switch to `tr_http`.
  Then summarise what you built and what the user must finish or check in the designer.

## Designer-only rules (the engine runs these, the VS Code designer rejects them)
1. **Trigger/handler settings and the Invoke REST URL take a literal or ONE whole property**, never an
   expression: `fda sa activity <Flow>.<Task>.input.Uri <Prop.Name> -C app-property` (writes
   `=$property["Prop.Name"]`). Never `string.concat(...)` in a URL; one property per endpoint.
2. **In an error-link branch read `$error[<FailedTask>].message`**, never plain `$error.message`.
3. **Password fields** (MCP Server trigger Secret): the app property stays type `string` and its value is the
   `SECRET:...` text printed by `~/FlogoLab/cline/tools/flogo-encrypt <plain>`; create it with
   `fda cap <Name> string "$(~/FlogoLab/cline/tools/flogo-encrypt <plain>)"`. Never use type `password`.

## Recipes the skills do not spell out (verified with fda 0.9.3)
- **Number app property:** `fda cap Risk.HighMm number 25` (stored as float64).
- **REST trigger (`tr_rest`):** `fda ct ReceiveHTTPMessage tr_rest`, then
  `fda sa trigger ReceiveHTTPMessage.settings.port 9999 -C number`, then
  `fda cth <Flow> ReceiveHTTPMessage --restResourcePath /the/path --restHandlerMethod POST`.
  The handler is named after the flow, so its selector is `ReceiveHTTPMessage.<Flow>`.
  Request body: `fda cs <ReqSchema> '<JSON schema>'` + `fda sa handler ReceiveHTTPMessage.<Flow>.schemas.output.body <ReqSchema> -C schema --force`.
  Reply data: `fda cs <RespSchema> ...` + `fda sa handler ReceiveHTTPMessage.<Flow>.schemas.reply.data <RespSchema> -C schema --force`.
  Then wire ONCE: `fda wth <Flow> ReceiveHTTPMessage.<Flow> --force --input headers:object,body:object --output code:integer,data:object`.
  The flow then reads `$flow.body.<field>`.
- **MCP Server trigger (`tr_mcpserver`):** `fda ct MCPServer tr_mcpserver`; settings with
  `fda sa trigger MCPServer.settings.<name> <value>`: `serverName`, `serverVersion`, `serverPort` (plain
  value, e.g. `9090`), `serverEndpointPath`, `authType` (`None` or `API Key`), `authToken`
  (`fda sa trigger MCPServer.settings.authToken <Prop> -C app-property`). One tool per flow:
  `fda cth <Flow> MCPServer --mcpHandlerType Tool --mcpHandlerName <tool_name> --mcpHandlerDescription "<text>"`.
  Tool arguments: `fda cs <ArgsSchema> '<JSON schema>'` + `fda sa handler MCPServer.<Flow>.schemas.output.arguments <ArgsSchema> -C schema --force`,
  then `fda wth <Flow> MCPServer.<Flow>`. Handler settings: `toolTitle`, and the booleans
  `readOnlyToolHint`, `destructiveToolHint`, `idempotentToolHint`, `openWorldToolHint`
  (`fda sa handler MCPServer.<Flow>.settings.openWorldToolHint true -C boolean`). The flow reads
  `$flow.arguments.<field>`; it answers through a Return whose `response` has `data` (string) or `error` (string,
  becomes an MCP error result): `fda mm <Flow>.<Return>.input.mappings.response.mapping.data '=coerce.toString(...)'`
  or `fda mm <Flow>.<Return>.input.mappings.response.mapping.error '=string.concat(...)'`. Keep the `.mapping.`
  segment: without it (`...mappings.response.error`) the expression is returned as literal text.
- **Activity types:** Log `act_general_log`, Invoke REST `act_general_rest`, Mapper `act_general_mapper`,
  Return `act_default_actreturn`. `fda cf` adds a `StartActivity` (no-op); keep it as the first activity.
- **Always add activities with `--doNotLink`:** `fda ca <Flow> <Name> <type> --doNotLink -f <file>`. Without it
  fda links the new activity from whatever activity was added last, which is wrong as soon as a flow branches.
- **Create every link, and set its type, with `~/FlogoLab/cline/tools/fda-link`** (it runs `fda cl` and
  `fda sa flow '<Flow>.links[N]...'` for you and finds N itself):
  - `fda-link <file> <Flow> <From> <To>` - success link
  - `fda-link <file> <Flow> <From> <To> expression '<condition>'` - success with condition (no leading `=`)
  - `fda-link <file> <Flow> <From> <To> exprOtherwise` - success with no matching condition (otherwise)
  - `fda-link <file> <Flow> <From> <To> error` - error link
  - `fda-link <file> <Flow>` - list the links. To delete a link: `fda rl <Flow> <From> <To> -f <file>`.
  When all links are made, list them and compare with every link the user asked for.
- **Every activity except `StartActivity` needs an incoming link.** An activity without one runs as soon as
  the flow starts (a Return without an incoming link answers before anything else runs).
- **Log message:** `fda mm '<Flow>.<Log>.input.message' '=string.concat("text ", $flow.body.x)'` (no schema / `sms` on a Log).
- **Mapper:** `fda sms <Flow>.<Mapper> --json-value-to-schema '<sample JSON>'`, then one
  `fda mm <Flow>.<Mapper>.input.input.mapping.<field> '<expr>'` per field. Downstream: `$activity[<Mapper>].output.<field>`.
  A mapper cannot read its own outputs: repeat the expression instead.
- **Invoke REST:** `fda sa activity <Flow>.<Task>.input.Method POST`; URL as designer rule 1.
  Query parameters: `fda cs <QSchema> '<schema>'` + `fda sa activity <Flow>.<Task>.schemas.input.queryParams <QSchema> -C schema --force`,
  then `fda mm <Flow>.<Task>.input.queryParams.mapping.<param> <value>`.
  JSON body: `fda cs <BodySchema> ...` + `fda sa activity <Flow>.<Task>.schemas.input.body <BodySchema> -C schema --force`,
  then `fda mm <Flow>.<Task>.input.body.mapping.<field> <value>`.
  Response schema: `fda sa activity <Flow>.<Task>.schemas.output.responseBody <RespSchema> -C schema --force`;
  read it downstream as `$activity[<Task>].responseBody.<field>`, status as `$activity[<Task>].statusCode`.
  Throw Error: `fda sa activity <Flow>.<Task>.output.throwError true -C boolean --force`.
  Response Type text/plain: `fda sa activity <Flow>.<Task>.output.responseType text/plain --force`.
- **Return (`actreturn`) for a REST trigger:** `fda mm <Flow>.<Return>.input.mappings.code 201 --type number`
  and one `fda mm <Flow>.<Return>.input.mappings.data.mapping.<field> <value>` per reply field (keep `.mapping.`)
  (literal booleans: `--type boolean`).
