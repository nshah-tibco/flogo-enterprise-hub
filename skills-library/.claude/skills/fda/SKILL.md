---
name: flogo-design-assistant
description: A command line tool to create and modify TIBCO Flogo Integration Applications (both Flogo 2.x and Flogo 3.x)
user-invocable: true
---

> **Preflight:** resolve the CLI first — AGENT.md → *Resolving the `fda` CLI* (decide Flogo 2.x or 3.x, find that version's `flogodesign-cli`, report `fda version`). This skill is written against **fda 0.9.5** (Flogo extension 2.26.9 for 2.x, `tibco.flogo3` 3.0.2 for 3.x). If `fda version` fails, install/update the TIBCO Flogo VS Code extension.

Everything in this skill applies to **both Flogo 2.x and Flogo 3.x** apps unless a line explicitly says otherwise.

Follow the multi-step processes and "Things to avoid" below — do not skip steps.

`fda` (Flogo Design Assistant) builds and edits Flogo Integration apps from the command line. Every task takes the same global flags and either prints a human-readable result or, with `-j`, emits machine-readable JSON.

## Global flags (all tasks)

| Flag | Short | Env var | Meaning |
|---|---|---|---|
| `--file` | `-f` | `FLOGO_DESIGN_FLOGO_FILE` | Target project. **2.x CLI:** a Flogo file (default `flogo-project.flogo`). **3.x CLI:** a project directory, e.g. `MyProject` (default `flogo-project/`, resolved to `flogo-project/app.fgmd`) |
| `--type` | `-t` | | Type of the Flogo file (default `flow`) |
| `--json` | `-j` | | JSON output — only when you need the exact structure (see "Reading output") |
| `--configuration` | `-c` | `FLOGO_DESIGN_CONFIG_FILE` | Layer a config file over the bundled defaults |
| `--history` | `-H` | `FLOGO_DESIGN_ENABLE_HISTORY` | Record task history for the project |
| `--debug` | | | Verbose debug output (great for diagnosing arg parsing) |
| `--force` | `-F` | | Force-create / force-remove past validation guards (only some tasks honor it — see "Things to avoid") |

There is **no `--help` flag**; help is the `fda help [<task>]` task.

**Reading output:** use the default readable output, and narrow it with the task's own filter argument (`fda lct sql`, `fda lat string`) or `fda da <type> [<selector>]`. Don't assume `jq` is installed (Git Bash on Windows doesn't ship it). Use `-j` only when you need the exact JSON structure and read it directly; with `-j`, list-style tasks emit a JSON body and CRUD tasks return a `{message, ...}` shape, and tables are suppressed.

### 2.x vs 3.x project shape

|                        | 2.x                     | 3.x                                  |
|---|---|---|
| `cp <name>` creates    | `<name>.flogo` (file)   | `<name>/app.fgmd` (folder)           |
| Later commands use `-f <app>` | `<app>` = `<path>/<name>.flogo` | `<app>` = `<path>/<name>` (the project folder) |
| Default with no `-f`   | `flogo-project.flogo`   | `flogo-project/app.fgmd`             |

- **`-T` / `--flogo-type`:** the CLI creates its own version by default, so omit `-T`. Pass it only for cross-type creation: `-T 2x`/`-T 2` from a 3.x CLI, `-T 3x`/`-T 3` from a 2.x CLI.
- **`create-project` and `-f`: the path's shape decides the version.** Apps go in `FLOGO_APPS_DIR` (AGENT.md), so pass `-f` with the shape that matches the version you want:
  - 2.x: `fda cp MyApp "My app" -f <FLOGO_APPS_DIR>/MyApp.flogo`
  - 3.x: `fda cp MyApp "My app" -f <FLOGO_APPS_DIR>/MyApp/app.fgmd`
  - **Never a plain path with no `.flogo` / `app.fgmd`** — from the 3.x CLI, `-f <dir>/MyApp` silently writes a single-file 2.x-style app named `MyApp` (no extension) instead of a 3.x project. Without `-f`, `cp` creates the app in the current directory.
  - Always pass the app name as the first positional — without it the project defaults to `Flogo_project`.
- **Always pass `-f` on every later command.** Without it, read-only tasks fail, and tasks that write silently auto-create the default project.

## Tasks

The signatures below are current for fda 0.9.5 — use them instead of running `help`. Run `fda help <task>` (or `fda help <shortcode>`) only when a command fails or you need a flag that isn't listed here. Inline parameters use `<>` brackets; flags use `--name` or the short form shown.

### general

| Task | Alias | Description | Usage |
|---|---|---|---|
| `version` | `v` | Display version | `fda version` |
| `help` | `h` | Show help | `fda help [<task>]` |
| `explain` | `exp` | Explain a function, activity, connector or trigger | `fda explain <type(function\|activity\|connector\|trigger)> <name>` |
| `show-design-config` | `sdc` | Show current Flogo Design configuration | `fda show-design-config [<config-pointer>]` |
| `export-design-config` | `edc` | Export Flogo Design configuration to file | `fda export-design-config [<config-file>] [--mode SINGLE_FILE\|MULTI_FILE]` |
| `list-flogo-projects` | `ls`, `lfp` | List flogo project files in current directory | `fda list-flogo-projects [--include-history-folder]` |
| `analyze-vscode-extension` | `ave` | Check for unknown imports in VSCode extension | `fda analyze-vscode-extension [<folder>] [--toConfigFile <path>] [--type(-T) <all\|activity\|trigger\|connection\|contribution\|function>] [--filter(-F) <str>] [--ignoreDefaultConfig] [--ignoreOverlay] [--customOverlayFile(-O) <path>] [--flogoVersion(-V) <ver>]` |
| `model-context-protocol` | `mcp` | Start an MCP server for Flogo development | `fda model-context-protocol [<stdio\|http\|sse>] [<port>] [--buildFlogoLocation <path>] [--multiFileMode]` |

### process-development

| Task | Alias | Description | Usage |
|---|---|---|---|
| `create-project` | `cp` | Create a new Flogo Project | `fda cp <name> <description> [--flogo-type (-T) 2x\|2\|3x\|3]` |
| `describe-project` | `dp` | Describe a Flogo Project | `fda dp [--json]` |
| `create-flow` | `cf` | Create a new Flogo Flow | `fda cf <flow-name> <flow-description>` |
| `remove-flow` | `rf` | Remove a Flogo Flow | `fda rf <flow-name>` |
| `create-activity` | `ca`, `aa`, `add-activity` | Add a Flogo Activity | `fda ca <flow> <name> <type> <description> [--doNotLink] [--connection (-C) <name>]` |
| `change-activity-type` | `cat` | Change activity type | `fda cat <flow> <activity> <new-type>` |
| `create-link` | `cl` | Link two activities in a flow | `fda cl <flow> <from-activity> <to-activity>` |
| `remove-link` | `rl` | Remove a link between activities | `fda rl <flow> <from-activity> <to-activity>` |
| `format-flow` | `ff` | Format a flow layout | `fda ff <flow> <format(auto\|snake\|dagre\|straight\|straight-down\|stairs)> [--all]` |
| `create-api-skeleton` | `cas` | Create flows from an API definition | `fda cas <spec-name> <skeleton(none\|logReply)>` |
| `create-mcp-skeleton` | `cms` | Create flows for MCP from an API definition | `fda cms <spec-name> [--readOnly] [--methodFilter <GET,POST,...>] [--token <token>]` |
| `describe-imports` | `di` | Describe imports in a project | `fda di [<filter>] [--json]` |
| `add-import` | `ai` | Add an import | `fda ai [<import-url>] [--alias <alias>] [--force (-F)]` |
| `remove-import` | `ri` | Remove an import | `fda ri <import-identifier> [--force (-F)]` |
| `describe-contributions` | `dco` | Describe contributions | `fda dco [<filter>] [--json]` |
| `add-contribution` | `aco` | Add a contribution | `fda aco <identifier> [--force (-F)]` |
| `remove-contribution` | `rco` | Remove a contribution | `fda rco <identifier> [--force (-F)]` |
| `describe-attributes` | `da` | Describe attributes of a Flogo item | `fda da <item-type(flow\|activity\|trigger\|handler\|connection\|property\|any)> [<selector>] [--json]` (selector required for `handler`) |
| `analyze-project` | `ap` | Check for unknown imports | `fda ap [--toConfigFile <path>]` |

### data-management

| Task | Alias | Description | Usage |
|---|---|---|---|
| `create-schema` | `cs` | Create a schema | `fda cs <schema-name> <json-schema> [--jsonSchemaFile <path>]` |
| `update-schema` | `us` | Add or remove a property in a schema | `fda us <schema-name> [--add-property (-ap) <name:type>] [--remove-property (-rp) <name>] [--required (-R)]` |
| `remove-schema` | `rs` | Remove a schema | `fda rs <schema-name>` |
| `create-spec` | `csp` | Create an API specification | `fda csp <spec-name> <spec-json> [--specFile <path>]` |
| `remove-spec` | `rsp` | Remove a spec | `fda rsp <spec-name>` |
| `create-app-property` | `cap` | Create an application property | `fda cap <[group.]name> <type(string\|number\|boolean)> <value>` |
| `remove-app-property` | `rap` | Remove an application property | `fda rap <[group.]name>` |
| `set-attribute` | `sa`, `sc`, `set-configuration` | Set attribute for a Flogo object | see "Detailed tasks" below |

### connectivity

| Task | Alias | Description | Usage |
|---|---|---|---|
| `create-trigger` | `ct` | Create a new trigger | `fda ct <trigger-id> <trigger-type> <description> [--connection <name>]` |
| `create-trigger-handler` | `cth` | Create a trigger handler | `fda cth <flow> <trigger-id> <description> [--restResourcePath <path>] [--restHandlerMethod <GET\|POST\|...>] [--mcpHandlerType <Tool\|Resource\|Prompt>] [--mcpHandlerName <name>] [--mcpHandlerDescription <desc>]` |
| `remove-trigger` | `rt` | Remove a trigger | `fda rt <trigger-id>` |
| `remove-trigger-handler` | `rth` | Remove a trigger handler | `fda rth <trigger-id> <handler-name>` |
| `create-connection` | `cc` | Create a new connector | `fda cc <connection-name> <connection-type>` |
| `remove-connection` | `rc` | Remove a connection | `fda rc <connection-name>` |
| `list-trigger-types` | `ltt` | List possible trigger types | `fda ltt [filter] [--json]` |
| `list-activity-types` | `lat` | List possible activity types | `fda lat [filter] [--json]` |
| `list-connection-types` | `lct` | List possible connection types | `fda lct [filter] [--json]` |
| `list-contributions` | `lco` | List configured contributions | `fda lco [filter] [--json]` |
| `list-types` | `lt` | List all types known to the CLI | `fda lt [filter] [--json]` |

### testing

| Task | Alias | Description | Usage |
|---|---|---|---|
| `check` | `ch`, `va`, `validate` | Check validity of a Flogo object | `fda ch <type> <name> <validation(exists\|not-exists\|has-correct-value)> [<value>]` |
| `create-test-file` | `ctf` | Create a new test file | `fda ctf [--test-file (-s) <name>]` |
| `describe-test-file` | `dt` | Describe a test file | `fda dt [--test-file (-s) <name>] [--json]` |
| `create-test-suite` | `cts` | Create a test suite | `fda cts <suite-name> [--test-file (-s) <name>]` |
| `create-test-case` | `ctc` | Create a test case | `fda ctc <case-name> <flow> <description> <flow-inputs-json> [--test-file (-s) <name>]` |
| `create-assertion` | `cass`, `ass`, `add-assertion` | Add an assertion to a test case | `fda cass <case-name> <location> <type> <name> <value> [--test-file (-s) <name>]` |
| `add-test-case-to-suite` | `ats` | Add test case to a suite | `fda ats <case-name> <suite-name> [--test-file (-s) <name>]` |

### mapping

| Task | Alias | Description | Usage |
|---|---|---|---|
| `list-functions` | `lf` | List Flogo functions | `fda lf [<filter>]` |
| `describe-mapping-fields` | `dmf` | List all mappable fields (what *can* be mapped) | `fda dmf [<filter>]` |
| `list-mapping-sources` | `lms` | List mapping sources for a target (what to map *from*) | `fda lms <mapping-field> [<filter>]` |
| `list-mappings` | `lm` | List currently-set mappings (what *is* mapped) | `fda lm [<filter>]` |
| `check-mappings` | `cm`, `validate-mappings` | Check mappings (refs, imports, `@foreach` scopes) | `fda cm [<filter>] [--verbose (-v)]` |
| `make-mapping` | `mm` | Set a mapper field value (or `@foreach` scope) | see "Detailed tasks" below |
| `remove-mapping` | `rmm` | Remove a mapping entry | `fda rmm <field>` |
| `wire-trigger-handler` | `wth` | Wire a trigger handler ↔ flow (inputs + reply mappings) | see "Detailed tasks" below |
| `set-mapping-schema` | `sms` | Attach a JSON Schema to a mappable activity or flow I/O | `fda sms <flow.activity[.direction]\|flow.<input\|output\|both>> [<schema-name>] [--json-schema (-js) <json>] [--json-schema-file (-jsf) <path>] [--json-value-to-schema (-jvs) <sample-json>] [--json-value-to-schema-file (-jvf) <path>] [--field (-fd) <name>] [--force (-F)]` |
| `remove-mapping-schema` | `rms` | Detach a JSON Schema from a mappable activity | `fda rms <flow.activity[.direction]> [--field (-fd) <name>]` |
| `update-mapping-schema` | `ums` | Add or remove a property in an activity's schema | `fda ums <flow.activity[.direction]\|flow.<input\|output\|both>> [--add-property (-ap) <name:type>] [--remove-property (-rp) <name>] [--required (-R)] [--field (-fd) <name>]` |

### history

| Task | Alias | Description | Usage |
|---|---|---|---|
| `show-history` | `sh` | Show history of executed tasks | `fda sh [<task-name>] [--all (-a)] [--json]` |
| `restore-history` | `rhi` | Restore app to a version in history | `fda rhi <task-name-or-number>` |
| `script-history` | `sch` | Create a script from historical commands | `fda sch <script-file>` |

History is only recorded when `-H` was passed on the originating commands (or `FLOGO_DESIGN_ENABLE_HISTORY=true`).

## How to use `fda` from Claude Code in VS Code

The `fda` CLI is the right tool for any "edit this Flogo file" or "tell me what's in this Flogo file" task. Use it directly — don't hand-edit the JSON (`.flogo` for 2.x, `app.fgmd` and its folder for 3.x). Reasons: every task validates against the live FDev configuration, every save runs the contrib re-derivation + defensive function-import sweep, and history is recorded so a bad change can be rolled back via `restore-history`.

### Working rules

- **Discover before creating.** `list-trigger-types`, `list-activity-types`, `list-connection-types`, `list-functions`, `explain <type> <name>`. Type strings are validated — never guess one.
- **Read before mapping.** `list-mapping-sources` for what you can map *from*, `describe-mapping-fields` for what can be mapped *to*.
- **`dmf` before `mm`.** Always run `dmf <flow>.<activity>` and use its exact path as the `mm` field — mapping path structures differ by activity type.
- **`lf` / `exp function` before using any function in `mm`.** Run `fda exp function <package>` to confirm the function exists and its exact name. Never guess — e.g. `coerce.toNumber()` does not exist; the correct function is `coerce.toInt()`.
- **Prefer the composite.** `wire-trigger-handler` does the four-slot trigger↔flow wiring in one call; don't hand-wire those slots.
- **Format after adding activities.** `create-activity` and `cms` place items at a default position that overlaps existing activities in the designer. Run `fda ff <flow> auto -f <app>` after adding activities (`--all` after `cms`). On fda 0.9.5 `ff` only moves activities: if one has no path from the start activity it stops with `No path found from StartActivity to <activity>` and changes nothing — link the activity, then re-run.
- **Validate after mutating.** `check-mappings`, `check`, `analyze-project` — after the change, not only at the very end.
- **Report with `describe-project`.**
- **After `wth`, read back `fda da flow <flow>.metadata -f <app>` and confirm every reply field you plan to map exists.**

### 1. Discover before you mutate

Always start a non-trivial task with the matching `list-*` / `describe-*` / `explain` task to confirm the entity exists and to see its real shape:

```bash
fda dp -f <app>                              # project summary, incl. flow names
fda da activity Flow1.MyActivity -f <app>    # one activity's full attributes
fda lct sql                                  # connection types matching "sql"
fda lat string                               # activity types matching "string"
fda lf string                                # functions matching "string" (last line gives the count)
fda exp activity log                         # full input-field list for log
fda exp function string                      # all functions in the string package
```

**To verify app properties or connection values, use `fda da property -f <app>` / `fda da connection -f <app>` (or `fda dp -f <app>`) — never inspect the raw JSON with `python3`, `cat`, or `jq`.**

### 2. Mutate idempotently, validate after

CRUD tasks are idempotent for create (existing entries get re-bound to the new config) but error on remove if the target doesn't exist. After a sequence of edits, run a validator and a re-read to confirm the state is what you expected:

```bash
fda cf MyFlow "My flow" -f <app>
fda ca MyFlow Mapper mapper "Build the payload" -f <app>
fda mm 'MyFlow.Mapper.input.input.mapping.uuid' '=utils.uuid()' -f <app>
fda cm -f <app>                                  # sweep for broken refs / missing imports
fda check activity Mapper exists -f <app>        # script-friendly assertion (bare activity name)
```

`fda check ...` is the assertion-style task — it exits non-zero on failure, perfect for shell scripts and CI.

> ⚠ **A "success" message + a clean `fda cm` do NOT guarantee the designer will render the result correctly.** A few classes of bug (a mapping whose schema doesn't declare the mapped keys, a connection written as a plain name) are written silently and pass every static check, yet break in the VSCode designer. For anything structural — connection bindings, parameterized-activity schemas, mapping shapes — **read the value back and compare it against a known-good, designer-authored app** of the same kind before considering it done. Trust the on-disk shape, not the exit status.

### 3. Mappings are first-class

The `mapping` category covers the entire Flogo VSCode UI mapping panel — see the `fda-mapping` skill for the full how-to. The path shape is `<flow>.<activity>.input.input.mapping.<dotted>` for mapper activities and `<flow>.<activity>.input.<field>` for any other activity (log, rest, …). `dmf` only surfaces fields that are mappable in the UI's "Activity inputs" panel — settings (the UI's other tab) are filtered out via the `mappableFields` allow-list on each activity's FCon entry, populated by `analyze-vscode-extension` from the descriptor's `display.mappable` rule. `mm`/`rmm` are NOT filtered — you can still set any input field directly. Sources have a fixed syntax — `$flowctx["X"]`, `$property["X"]`, `$activity[Name].output.X`, `$loop[name].X` — and function calls auto-add the matching package to the project's `imports`.

```bash
# Discover what can be mapped + what can be mapped FROM
fda dmf -f <app>
fda lms 'MyFlow.Mapper.input.input.mapping.orderId' -f <app>

# Set a literal, an expression, and an @foreach loop
fda mm 'MyFlow.Mapper.input.input.mapping.customerId' 1234 --type number -f <app>
fda mm 'MyFlow.Mapper.input.input.mapping.tag' '=$property["Env"]' -f <app>
fda mm 'MyFlow.Mapper.input.input.mapping.lineItems' \
       --foreach '$activity[Setter].output.items' --as items -f <app>
fda mm 'MyFlow.Mapper.input.input.mapping.lineItems.sku' '=$loop[items].sku' -f <app>

# Validate before building
fda cm -f <app>
```

## Detailed tasks

### `set-attribute` (`sa`, `sc`, `set-configuration`)

```
fda sa <item-type> <item-selector> <value> [--jsonValue <json>] [--jsonFile <file>] [--configType (-C) <type>] [--force (-F)]
```

**item-type:** `flow`, `activity`, `trigger`, `handler`, `connection`, `property`, `any`

**Selector patterns:**
- **flow:** `<flow>.<configuration>.*`
- **activity:** `<flow>.<activity>.<configuration>.*`
- **trigger:** `<trigger-id>.<configuration>.*`
- **handler:** `<trigger-id>.<handler>.<configuration>.*`
- **connection:** `<connection>.<configuration>.*`
- **property:** `<property-name>.*`

**configType (-C):** `string`, `number`, `boolean`, `spec` (writes `spec://<id>`), `app-property` (writes `=$property["<name>"]`), `schema` (writes `schema://<name>`), `connection` (writes `conn://<uuid>` in 2.x, `conn://<ConnName>.fgconn` in 3.x)

**For `sa property`, use the bare property name as the selector** (e.g., `AppName`), not `AppName.value`. The selector resolves to the property's value directly — appending `.value` or `.type` causes a "Property not found" error.

```bash
fda sa flow MyFlow.description "Processes signup" -f <app>
fda sa activity MainFlow.Log.input.message "Hello World" -f <app>
fda sa activity Flow1.Log1.input.flowInfo true -C boolean -f <app>
fda sa connection EMS.settings.userName EMSAdmin -f <app>
fda sa trigger MyTrigger.settings.swagger MySpec -C spec -f <app>
fda sa trigger MyTrigger.settings.conn MyConnection -C connection -f <app>
fda sa trigger MyTrigger.settings.schema CustomerSchema -C schema -f <app>
```

### `wire-trigger-handler` (`wth`)

```
fda wth <flow> <trigger.handler> [flags]
```

| Flag | Short | Description |
|---|---|---|
| `--inputs-only` | `-io` | Wire only request side (skip reply) |
| `--reply-only` | `-ro` | Wire only response side (skip request) |
| `--input` | `-in` | Override input field — `name[:type]` (repeatable, comma-separated) |
| `--output` | `-ou` | Override output field — `name[:type]` (repeatable, comma-separated) |
| `--force` | `-F` | Overwrite existing wiring |
| `--input-schema` | `-is` | Existing schema name for input |
| `--input-schema-from-json` | `-isj` | Sample JSON to derive input schema |
| `--input-schema-from-json-file` | `-isjf` | Path to sample-JSON file for input side |
| `--output-schema` | `-os` | Existing schema name for output |
| `--output-schema-from-json` | `-osj` | Sample JSON to derive output schema |
| `--output-schema-from-json-file` | `-osjf` | Path to sample-JSON file for output side |
| `--input-mapping` | `-im` | Override action.input mapping template |
| `--reply-mapping` | `-rm` | Override reply mapping template |
| `--no-auto-derive-output-schema` | `-nad` | Disable auto-derivation of output schema from connected mapper |

Timer triggers skip wiring by default. Skip-if-already-wired — pass `--force` to overwrite. Default shapes per trigger and the schema prerequisites are in "Wiring trigger handlers ↔ flows" below.

```bash
fda wth MyFlow Timer.MyFlow --inputs-only -f <app>
fda wth MyFlow HTTP.GetUsers --reply-only -f <app>
fda wth MyFlow X.Y --input id:string,qty:integer --output result:object -f <app>
```

### `make-mapping` (`mm`)

```
fda mm <field> [<value>] [--jsonValue (-jv) <json>] [--jsonValueFile (-jvf) <path>] [--type (-ty) <string|number|boolean>] [--foreach (-fe) <expr>] [--as (-as) <name>]
```

**field** selector: `<flow>.<activity>.input.input.mapping.<dotted-path>` (mapper) or `<flow>.<activity>.input.<field>` (other activities) — copy it from `dmf`.
**value**: literal, or `=` prefix for expression. Function calls auto-add imports.

**Mapping values** (prefix with `=`):
- `$property["name"]` — app property
- `$flowctx["name"]` — flow context var
- `$activity[Name].output.field` — upstream activity output (must be upstream via links)
- `$loop[iter].field` — inside a `@foreach` scope
- `$.field` — inside `handler.action.input/output` (runtime accepts **only** `$.` there)
- Functions like `string.concat(...)` — `make-mapping` adds the function import automatically

Use `--jsonValue '<json>'` (or `--jsonValueFile <path>`) when shells make a positional `{...}` value clunky to express — the JSON is parsed and used as the mapping value. JSON arrays and objects passed as the positional value are auto-detected and stored as native typed values (NOT as a string expression).

```bash
fda mm Flow.Mapper.input.input.mapping.id 1234 -f <app>
fda mm Flow.Mapper.input.input.mapping.name '=$property["AppName"]' -f <app>
fda mm Flow.Mapper.input.input.mapping.label '=string.concat("X-", $property["P1"])' -f <app>
# Static JSON-array literal — stored as a real array of objects
fda mm Flow.Sensors.input.input.mapping.readings '[{"sensor":"S1","value":75},{"sensor":"S2","value":20}]' -f <app>
# @foreach loop
fda mm Flow.Mapper.input.input.mapping.items --foreach '$activity[Src].output.items' --as items -f <app>
fda mm Flow.Mapper.input.input.mapping.items.code '=$loop[items].sku' -f <app>
```

### `set-mapping-schema` (`sms`) — flow scope

In addition to the activity scope (`<flow>.<activity>[.<direction>]`), `sms` supports **flow scope** via selectors `<flow>.input` / `<flow>.output` / `<flow>.both`. This targets the flow's own `metadata.input/output` — the "Flow Inputs & Outputs" panel in the VSCode extension. The supplied JSON Schema is walked and one entry is emitted per top-level property; the full schema is also stringified into `flow.metadata.fe_metadata` for the VSCode JSON-Schema view to round-trip.

```bash
# Flow input schema
fda sms MyFlow.input --json-schema '{"type":"object","properties":{"body":{"type":"object","properties":{"msg":{"type":"string"}}},"method":{"type":"string"}}}' -f <app>

# Flow output schema derived from a sample
fda sms MyFlow.output --json-value-to-schema '{"code":200,"data":{"outputMessage":"hi"}}' -f <app>
```

`update-mapping-schema` (`ums`) also supports flow scope — updates the flow's own input/output metadata, regenerating both the runtime `metadata.<side>[]` array and the designer `metadata.fe_metadata.<side>` schema in lockstep:

```bash
fda ums MyFlow.input --add-property orderId:string --required -f <app>
```

## Picking a trigger

The trigger choice shapes the whole flow shape; getting it wrong leads to runtime panics that no static check catches before `flogobuild build-exe`.

| Trigger | When to use | Needs |
|---|---|---|
| `tr_rest` (TIBCO REST) | The user says "REST" or the prompt/image mentions a REST API — use this regardless of whether a swagger spec exists. If the user provides a spec, pair with `cas` (`create-api-skeleton`). Without a swagger, `tr_rest` still works — do NOT fall back to `tr_http`. | Configure method/path via handler settings. Optionally `settings.swagger` if user provides a spec. |
| `tr_http` (project-flogo HTTP, mode: Data) | Only when the user explicitly says "HTTP trigger" | Wire `handler.reply.{statusCode, responseBody}` (the runtime contract — NOT `code`/`data`/`headers`) from the upstream `actreturn` output, otherwise the response is HTTP 0 and the runtime panics with `invalid WriteHeader code 0`. `wth` seeds `reply.statusCode = 200` and `reply.responseBody = ""` as safe defaults, and `cm` flags any remaining gaps as `TR_HTTP_REPLY_STATUSCODE_ZERO` / `HTTP_TRIGGER_REPLY_UNWIRED`. |
| `tr_timer` | Periodic invocation; no I/O coupling | Just `Repeating` / `Time Interval` / `Interval Unit` settings. |

Quick rule: **prompt/image says "REST" or "Receive HTTP Message" → `tr_rest`** (no swagger needed). **User explicitly provides a spec → `cas` with `tr_rest`.** **User explicitly says "HTTP trigger" → `tr_http`.** Never auto-create a swagger spec. Never fall back to `tr_http` just because no spec exists. If `cm` reports `TR_REST_NO_SWAGGER` and the user didn't provide a spec, silently ignore it — don't create a spec or ask about it.

## Common runtime failures (and how `fda cm` catches them)

`fda cm` is the layer between "build succeeded" and "first request crashes the engine". Run it before every `flogobuild build-exe`. The rules below cover the failures most likely to bite — each maps to a cm code so the user knows what to fix.

| Symptom at runtime | cm code | Fix |
|---|---|---|
| `connection with id 'conn://' not configured` at engine init | (caught by `analyze-vscode-extension` — `conn://` defaults are blanked at seed-time, never appear in the flogo) | Re-seed `default-config.json` if you see one: `fda ave <path-to-extension> --type activity --toConfigFile <path>` (`<path-to-extension>` = the extension folder resolved as in AGENT.md → *Resolving the `fda` CLI* — never pin the version) |
| `WriteHeader code 0` panic from an `actreturn` flow | `INPUT_VS_SETTINGS_MISWRITE` | `actreturn.mappings` lives under `settings`, not `input`. `mm` and `sa` rewrite the path automatically (settingFields metadata); legacy files trip the cm error and need the block moved. |
| None: `tr_rest` runs without a spec | `TR_REST_NO_SWAGGER` | `cm` reports it as an **error** and its message says the runtime will panic, but a spec-less `tr_rest` is the supported default — when the user gave no spec, ignore it ("Picking a trigger"). Add `settings.swagger` via `cas` only when the user provides one. |
| `function [length] is not installed` at runtime | `FUNCTION_AMBIGUOUS` / `FUNCTION_NOT_QUALIFIED` | **Always qualify function calls** with the package name (`string.length(...)`, `utils.uuid(...)`). `mm` rejects every bare call at write-time, regardless of whether it currently resolves to one package or many — uniform rule, future-proof against extensions adding same-named functions. |
| `error parsing expression '=$activity[…]'` inside an `@foreach` | `FOREACH_HAS_LEADING_EQUALS` | The `--foreach` value must NOT have a leading `=` — the `@foreach()` wrapper is itself the expression marker. `mm` strips the `=` proactively now; legacy files trip the cm warning. |
| `failed to resolve activity attr 'output'` | `ACTIVITY_OUTPUT_LEAF_UNKNOWN` | Non-mapper activities expose top-level outputs by name (`responseBody`, `statusCode`, etc.), not a single `.output` object. `lms` enumerates the real outputs; `cm` validates `$activity[X].<leaf>` against the schema. |
| Handler created (cth) but flow doesn't receive request data / can't reply | `TRIGGER_HANDLER_UNWIRED` | A handler bound to a flow needs four mutations wired (flow.metadata.input/output + handler.action.input/output + handler.reply). Use `fda wth <flow> <trigger.handler>` — one call does both directions, with sensible defaults per trigger ref. |
| Flogo VSCode UI shows mapping JSON as raw text instead of a typed tree; `schema://X` reference doesn't resolve at runtime | `MAPPING_SCHEMA_REF_MISSING` / `MAPPING_SCHEMA_INLINE_MALFORMED` | Mappable activities need a schema attached at `activity.schemas.<dir>.<field>`. Either reference a top-level schema (`fda sms <flow>.<activity> <name>`) or write content directly (`--json-schema` / `--json-value-to-schema`). Both sides default to the same schema for mapper activities. `cm` flags dangling `schema://` references and malformed inline blocks. |
| Reply fields missing / mismatched | `FLOW_OUTPUT_VS_ACTION_OUTPUT_MISMATCH` | `flow.metadata.output[].name` and `handler.action.output` keys must align. |
| Return mappings ignored | `FLOW_OUTPUT_VS_ACTRETURN_MISMATCH` | `actreturn.settings.mappings` keys must match `flow.metadata.output[].name`. |
| Guaranteed `WriteHeader code 0` panic on `tr_http` | `TR_HTTP_REPLY_STATUSCODE_ZERO` | `tr_http` handler with `reply.statusCode=0` and no `action.output.statusCode` mapping. |
| A literal mapping value starting with a CLI flag was swallowed | `EXPRESSION_LITERAL_LEAK` | Literal mapping values start with a CLI flag (`--jsonValue`, `--type`, etc.) — the parser absorbed the flag. Re-run `mm` with the value passed via `--jsonValue`. |

## Setting schemas on trigger handlers (prerequisite for `wth`)

`wth` only copies schemas that are already set on the trigger handler — it does not discover application-level schemas on its own. Triggers with empty `defaultWiring` (notably `tr_rest` for `pathParams` / `queryParams`) require schemas to be explicitly associated with the handler's output fields before `wth` can propagate them to `flow.metadata.input`.

Use `fda sa handler` to associate a schema with a handler output field — this is the CLI equivalent of the "Set Mapping Schema" toggle in the VSCode Flogo UI's Output Settings panel. **The form depends on the field:**

```bash
# pathParams / queryParams — inline {type, value, fe_metadata} envelope from a file
fda sa handler "<trigger>.<handler>.schemas.output.<field>" --jsonFile <file.json> --force -f <app>
# body / headers / reply — a named schema via -C schema
fda sa handler "<trigger>.<handler>.schemas.output.<field>" <schema_name> -C schema --force -f <app>
```

**Never use `-C schema` on `pathParams` or `queryParams`** — it writes a `schema://` reference that panics at runtime (`parameter.go` type assertion). `-C schema` is fine for `body`, `headers`, and `reply` schemas.

### `tr_rest` — schema association required before `wth`

`tr_rest` has default wiring for `headers`, `requestURI`, `method` (plus `body` on POST/PUT/PATCH) → and `code`, `message` ←. For extra fields (`pathParams`, `queryParams`), associate a schema with the handler output before running `wth`. **Only associate schemas for the fields the API actually needs** — skip the rest:

| Output field | When needed | Flow access after wiring |
|---|---|---|
| `pathParams` | Resource path has `{paramName}` placeholders | `$flow.pathParams.<name>` |
| `queryParams` | API accepts `?key=value` query parameters | `$flow.queryParams.<name>` |
| `headers` | Flow needs request headers (e.g. Authorization, correlation IDs) | `$flow.headers.<name>` |
| `body` | POST / PUT / PATCH with a request body | `$flow.body.<name>` |

#### Steps — example: GET `/books/{id}?genre=fiction` (needs pathParams + queryParams)

**Step 1.** Write each schema as a `{type, value, fe_metadata}` envelope file and set it on the handler output (repeat per needed field):

```bash
# pathparams.json → {"type":"json","value":"{\"$schema\":\"http://json-schema.org/draft-04/schema#\",\"type\":\"object\",\"properties\":{\"id\":{\"type\":\"string\"}},\"required\":[\"id\"]}","fe_metadata":"[{\"parameterName\":\"id\",\"repeating\":\"false\",\"type\":\"string\",\"required\":\"true\"}]"}
fda sa handler "$TRIGGER.$HANDLER.schemas.output.pathParams" --jsonFile pathparams.json --force -f "$FILE"

# queryparams.json → {"type":"json","value":"{\"$schema\":\"http://json-schema.org/draft-04/schema#\",\"type\":\"object\",\"properties\":{\"genre\":{\"type\":\"string\"}}}","fe_metadata":"[{\"parameterName\":\"genre\",\"repeating\":\"false\",\"type\":\"string\",\"required\":\"false\"}]"}
fda sa handler "$TRIGGER.$HANDLER.schemas.output.queryParams" --jsonFile queryparams.json --force -f "$FILE"
```

**Step 2a.** Run `wth` without `--input` to discover default fields and types:

```bash
fda wth "$FLOW" "$TRIGGER.$HANDLER" --force -f "$FILE"
# GET  → flow.metadata.input : headers:object, requestURI:string, method:string
# (a POST/PUT/PATCH handler also gets body:object)
```

**Step 2b.** Re-run `wth` with every default field from 2a's output (preserving name:type) **plus** the extra fields, all **comma-separated in a single `--input`**:

```bash
fda wth "$FLOW" "$TRIGGER.$HANDLER" --force \
    --input headers:object,requestURI:string,method:string,pathParams:object,queryParams:object \
    -f "$FILE"
```

**IMPORTANT:** Never hardcode field names or types in step 2b — always read them from 2a's `flow.metadata.input` output. Different triggers produce different defaults, and types may vary. Without the `:type` suffix (e.g. bare `--input fieldName`), fields are downgraded to `any`.

#### More examples — typed `body` and `headers`

`headers`, `requestURI`, `method` (and `body` on POST/PUT/PATCH handlers) are already default-wired (Step 2a discovers them), so you don't add them to `--input` just to receive them. Associate a schema on one of these fields only when the flow needs **typed** field access to it (e.g. `$flow.body.title`, `$flow.headers.Authorization` instead of a generic object). Do the schema association in Step 1, then run the same two-step `wth`.

```bash
# POST /books with a JSON body — type the body for $flow.body.<field> access
fda cs BookRequest '{"type":"object","properties":{"title":{"type":"string"},"author":{"type":"string"}},"required":["title"]}' -f "$FILE"
fda sa handler "$TRIGGER.$HANDLER.schemas.output.body" BookRequest -C schema --force -f "$FILE"

# Type a specific request header (e.g. Authorization) for $flow.headers.<name> access
fda cs BookHeaders '{"type":"object","properties":{"Authorization":{"type":"string"}}}' -f "$FILE"
fda sa handler "$TRIGGER.$HANDLER.schemas.output.headers" BookHeaders -C schema --force -f "$FILE"
```

Then run Step 2a (discover defaults) and Step 2b (re-apply every default field with its `name:type`, adding any extra `pathParams`/`queryParams` you associated).

- **3.x (until `wth` is fixed):** `wth` can't resolve `schema://` on `body`/`headers` — run all `wth` steps first, then `sa … -C schema`, then `fda sms <flow>.input` with every 2b field, keeping each field's schema and adding the full schema on that field.

### `tr_rest` — response schema on reply side

To bind a response schema to a REST trigger handler's reply, use `schemas.reply.data`:

```bash
fda sa handler "$TRIGGER.$HANDLER.schemas.reply.data" <ResponseSchemaName> -C schema --force -f "$FILE"
```

The field name is `data` — **not** `responseBody` or `message`. Using the wrong field name writes to the flogo file but the UI's Response Schema toggle stays off.

### Triggers that do NOT need this step

The following triggers have built-in `defaultWiring` — `wth` auto-discovers their output fields without manual schema association:

| Trigger | Auto-wired inputs |
|---|---|
| `tr_http` | `pathParams` + `queryParams` + `headers` + `content` |
| `tr_mcpserver` | `arguments` |
| `tr_timer` | none (no payloads) |

### Schema for non-REST trigger data (e.g. SQS `Message`, Kafka `jsonValue`)

`wth` can't add a schema to these fields, so add it in three steps:

1. `fda sa handler "<trigger>.<handler>.schemas.output.<field>" --jsonFile <schema.json> --force -f <app>`
2. `fda wth "<flow>" "<trigger>.<handler>" --force -f <app>` (add `--input <field>:array` if the field is a list), and note every input field and type it prints
3. `fda sms "<flow>.input" --json-schema '<schema>' -f <app>`, where the schema lists **every** field from step 2 with its type and gives the full schema only to `<field>`. Fields left out are removed from the flow.

- **Check the field's real type before step 2:** FDA's default type can be wrong (e.g. SQS `Message` is a list, not an object). Confirm it from the trigger's output in the designer, and if it's a list, map the whole field (`$flow.<field>`), not `$flow.<field>.<child>`.

## Wiring trigger handlers ↔ flows (`wth`)

> **If the flow needs fields beyond the trigger's default wiring** (e.g. pathParams or queryParams on `tr_rest`), complete the schema association steps in "Setting schemas on trigger handlers" above first, then use the two-step `wth` process (2a: without `--input` to discover default types, 2b: with combined `--input`).

`fda wth <flow> <trigger.handler>` does the four-step wiring in one call: populates `flow.metadata.input/output`, `handler.action.input/output`, and `handler.reply`. The field shapes come from the trigger ref's `defaultWiring` template (seeded by `analyze-vscode-extension`):

| Trigger | Default shape |
|---|---|
| `tr_mcpserver` | `arguments` (any) → / `response` (object) ← |
| `tr_http` | `pathParams` + `queryParams` + `headers` + `content` → / `statusCode` + `responseBody` ← |
| `tr_timer` | none (timer doesn't carry payloads) |
| `tr_rest` | `headers` + `requestURI` + `method` (+ `body` on POST/PUT/PATCH) → / `code` + `message` ← (`pathParams`/`queryParams` still need explicit schema association + `--input` override when the API uses them) |
| Custom | error: pass `--input` / `--output` explicitly |

Override defaults with `--input <name>[:<type>]` and `--output <name>[:<type>]` (comma-separated for multiple: `--input a:string,b:object`). Use `--inputs-only` / `--reply-only` to wire just one direction. `--force` overwrites already-wired sides (default behaviour skips with a warning, so you don't accidentally clobber hand-tuned mappings). All reply mappings use the action-scope resolver `=$.<name>` (the runtime rejects `$flow` in `handler.action.output` slots — `cm` catches strays as `RESOLVER_UNKNOWN`).

`wth` also propagates JSON-Schema to the four typed-tree slots (flow.metadata, handler.action, handler.reply) when given `--output-schema <name>` (or `--output-schema-from-json '<sample>'`). Without those flags, `wth` auto-derives the response schema from a connected mapper's output schema if the actreturn binds one — chain `mapper → actreturn → flow.metadata.output → handler.action.output → handler.reply` is fully knowable at design time. Disable with `--no-auto-derive-output-schema`.

`createMCPSkeleton` (`cms`) calls `wth` internally — same template, single source of truth for the wiring shape.

## Binding schemas on activity input fields (non-mapper activities)

For any activity with a schema-capable input field (visible via `fda exp activity <type>` — look for fields like `jsonSchema`, `responseSchema`, etc.), bind the schema at `schemas.input.<fieldName>` using `fda sa`:

```bash
fda sa activity "<flow>.<activity>.schemas.input.<fieldName>" <SchemaName> -C schema --force -f <app>
```

The `<fieldName>` must match the input field name from `exp`. **Do NOT** set `input.<fieldName>` directly (UI toggle won't activate) or use `sms --field` (writes to the wrong key).

- **Output fields work the same way:** bind a response/output schema at `schemas.output.<fieldName>` (e.g. `responseBody`), using the same `sa … -C schema --force` command.

## Things to avoid (common pitfalls)

### CLI usage

- **Prefix `MSYS_NO_PATHCONV=1` when passing values that start with `/`.** Git Bash on Windows converts `/path` arguments to `C:/Program Files/Git/path`. Always use `MSYS_NO_PATHCONV=1 fda ...` for commands like `cth --restResourcePath /books/{id}` or any `sa`/`mm` value starting with `/`. This is harmless on Linux/Mac (just an unused env var).
- **`ff` and older fda versions.** On fda 0.9.5 `ff` is safe (see "Working rules"). Older fda builds could drop activities missing from the computed layout (including `actreturn`) — if `fda version` reports something older than 0.9.5, skip `ff`; the designer lays activities out from the links anyway.
- **After `cp`, run `dp` to check if a flow exists — if not, run `cf` before `ct`/`cth`.**
- **Do NOT manually run `wth` after `cas` or `cms`.** Both are self-contained skeleton builders — they call `wth` internally and derive schemas from the spec automatically. Manual `wth` wiring is only needed when creating triggers and handlers individually (via `ct` + `cth`).
- **After `cth`, always run `wth` to wire the trigger handler to the flow.** Without wiring, the flow cannot receive trigger data or send replies (`TRIGGER_HANDLER_UNWIRED`). For triggers with path parameters, associate the pathParams schema before running `wth` (see "Setting schemas on trigger handlers"). The only exception is `tr_timer`, which carries no payloads.
- **Never use `--force` unless the skill docs explicitly show it for that exact command.** `--force` bypasses validation guards — using it unnecessarily can silently create malformed attributes or overwrite correct state. The ONLY places `--force` is required are: (1) `fda sa handler "...schemas.output.<field>" … --force` (and `schemas.reply.data`) for schema association on trigger handlers, (2) `fda sa activity "...schemas.<dir>.<field>" … --force` for activity schema binding, (3) `fda wth ... --force` to overwrite already-wired sides, and (4) `fda sa ... --force` to create an attribute path that doesn't exist yet. Every other `fda` command must be run WITHOUT `--force`. If a command fails without it, investigate the root cause instead of forcing past it; check `fda lt` when a type string is rejected.
- **Confirm before destructive tasks.** `restore-history` overwrites the project, and `remove-*` deletes without cascading cleanup. Ask the user first when the target is a real project.
- **Pass the `--file` global with the right shape.** A bare `fda <task>` with no `-f` opens `flogo-project.flogo` (2.x) or `flogo-project/` (3.x) in the cwd and AUTO-CREATES it if missing — a silent no-op trap when you meant to operate on a different file. When scripting, always pass `-f <path>` explicitly.
- **`fda cc` requires the full connection type name (e.g. `con_sqlserver`), not the short alias (e.g. `sqlserver`).** `fda cc MyConn sqlserver -f <app>` fails — use `fda cc MyConn con_sqlserver -f <app>`. Run `fda lct` to find the full type name.
- **Activity aliases use `<group>_<entity>`** for everything outside the `general`, `default`, and `ems` groups (e.g. `mysql_query`, `salesforce_delete`, `auditsafe_query` — not bare `query`). Connection / trigger aliases stay bare (`kafka`, `ems`, `mysql`) — there are no clashes there. `fda lat <filter>` and `fda exp activity <name>` show the canonical name + alias; `analyze-vscode-extension` warns at the end of its run if it spots any remaining alias clashes (`mapXxxAlias()` would silently pick the first match otherwise — `helper-validate-shortcodes` is the strict CI gate for the same check).
- **`exp function <name>` has four modes** — `category.fnName` (qualified), bare unique name (works), bare ambiguous name (errors with disambiguation), and bare category name (expands to every function in the package). When in doubt, qualify with `category.`.
- **`check activity` uses just the activity name, not `flow.activity`.** Unlike `sa` and `da` which use `<flow>.<activity>`, `check activity` takes only the bare activity name (`fda ch activity Act1 exists -f <app>`, not `fda ch activity MainFlow.Act1 exists -f <app>`). The `flow.activity` form gives a false "does not exist" result.
- **`check link` puts the flow name in `<name>` and `from.to` in `<value>`:** `fda ch link <flow> exists <from>.<to> -f <app>` — e.g. `fda ch link MainFlow exists StartActivity.Act1 -f <app>`. Putting `from.to` in the name position errors with "validation value for link must be in the format <from>.<to>".
- **`da handler` needs a trigger id:** `fda da handler <trigger-id>[.<handler>] -f <app>`.
- **Always pass `-C <type>` when using `sa` for non-string values.** `sa` defaults to writing every value as a string (e.g. `"true"` instead of `true`, `"200"` instead of `200`). The UI won't recognise the value if the type is wrong — boolean toggles stay unset, number fields show as text. Use `-C boolean` for true/false and `-C number` for numeric values: `fda sa activity Flow1.Log1.input.flowInfo true -C boolean -f <app>`.
- **Use `--jsonSchemaFile` for complex nested JSON schemas.** When a schema has more than 2 levels of object/array nesting (e.g. arrays of objects containing sub-arrays), write the JSON to a file and use `fda cs <name> --jsonSchemaFile <path> -f <app>` (or `sms --json-schema-file`) instead of inline JSON. Inline JSON with deeply nested structures is error-prone — miscounting closing braces `}` is nearly impossible to spot visually and leads to invalid JSON or silently malformed schemas. For simple flat schemas (1-2 levels), inline JSON is fine.
  ```bash
  # Complex nested schema — write to file first, then reference it
  fda cs OrderRequest --jsonSchemaFile ./schemas/order_request.json -f <app>

  # Simple flat schema — inline is fine
  fda cs BookPathParams '{"type":"object","properties":{"id":{"type":"string"}},"required":["id"]}' -f <app>
  ```
- **Stale `default-config.json`.** When working on a fresh clone the function catalog (`fda lf`, `fda exp function ...`) needs to be seeded once: `fda ave <path-to-extension> --type function --toConfigFile tibcopilot-flogo-command-line-developer/default-config/default-config.json`, where `<path-to-extension>` is the extension folder resolved as in AGENT.md → *Resolving the `fda` CLI*. The repo's committed `default-config.json` already has it; only matters if someone has reset that file.

### Designer validation

- **A passing build or API test does not mean the designer accepts the app.** The engine runs values the VS Code designer rejects, so check generated apps against the designer-only rules (full table in the `fda-mapping` skill, "Designer-only rules"):
  - **No expressions in settings.** Trigger and handler settings and the Invoke REST `Uri` take a literal or one whole `=$property["…"]`. `=string.concat($property["Base"], "/path")` is blanked on load (*"URL is required"*). Give each endpoint its own property, with any `{name}` placeholder inside the property value plus an `input.pathParams` mapping.
  - **Error branches read `$error[<FailedTask>].<field>`.** Plain `$error.message` is for the flow's Error Handler tab; in an error branch the designer flags it.
  - **Password fields need a `SECRET:` value.** `cap` has no password type (keep `string`; never write `type: password`, which stops the engine with `unknown type: password`). Encrypt the value with the CLI that ships in the Flogo extension and pass the result to `cap`; `cap` stores it as-is and the designer then treats the property as a password:
    ```bash
    # Prints the SECRET:… cipherText for $1. Searches the same extension roots as the fda resolver
    # (AGENT.md) and fails if the extension is not installed or prints no cipherText.
    # Set FLOGO_CLI_BIN to the bin/ folder you resolved fda from to pin the extension (2.x or 3.x);
    # otherwise it uses the newest Flogo 2.x extension.
    flogo_encrypt() {
      local name=flogo-vscode-cli cli="" dir out home="${HOME:-$USERPROFILE}"
      # Windows: the extension ships a Linux binary of the same name too; use the .exe
      [[ "$OSTYPE" == msys* || "$OSTYPE" == cygwin* || "$OSTYPE" == win32 ]] && name=flogo-vscode-cli.exe
      if [ -n "$FLOGO_CLI_BIN" ]; then
        cli="$FLOGO_CLI_BIN/$name"; [ -x "$cli" ] || cli=""
      else
        for dir in "$home/.vscode/extensions" "$home/.vscode-insiders/extensions" "$home/.vscode-server/extensions"; do
          cli=$(ls -td "$dir"/tibco.flogo-2.*/bin/"$name" 2>/dev/null | head -1)
          [ -n "$cli" ] && break
        done
      fi
      [ -n "$cli" ] || { echo "flogo-vscode-cli not found: install the TIBCO Flogo VS Code extension" >&2; return 1; }
      # output is JSON with "cipherText": "SECRET:<base64>" on its own line; sed avoids needing python
      out=$("$cli" secret encrypt -p "$1" | sed -n 's/.*"cipherText": *"\(SECRET:[^"]*\)".*/\1/p')
      [ -n "$out" ] || { echo "flogo-vscode-cli secret encrypt returned no cipherText" >&2; return 1; }
      printf '%s\n' "$out"
    }
    SECRET=$(flogo_encrypt "$PLAIN_VALUE") && fda cap MCP.ApiKey string "$SECRET" -f "$FILE"
    ```
    The CLI accepts the value only as an argument (`-p`), so it is visible in the process list while it runs: encrypt real secrets only on your own machine, and a dummy value for anything you publish.
    Encrypt before the property's first `cap`. If it already exists as plaintext, `fda rap MCP.ApiKey -f "$FILE"` first: `cap` on an existing name does not overwrite — it silently adds `MCP.ApiKey_1` and the binding keeps the plaintext property.
    The ciphertext uses Flogo's default data-secret key, so it decrypts in any app built with that default (`flogo-vscode-cli secret decrypt -c "$SECRET"` shows the plain value). It applies to the MCP Server trigger **Secret** (`authToken`) and to connector fields such as `#sendmail` `Password`.
  - Run `agentic-ai-use-case-builder/references/validate_flogo_apps.py <app.flogo>`: it checks all three.
- **Don't hand-edit the .flogo JSON.** The `flogoProject.contrib` blob is base64-encoded and re-derived on every save; ad-hoc edits to it vanish on the next `fda` write. Use the dedicated tasks.

### Connections

- **Bind connections by name with `-C`:** `ca … -C <ConnName>`, `ct … --connection <ConnName>`, or `sa … <ConnName> -C connection` (activity or trigger). fda writes `conn://<uuid>` (2.x) or `conn://<ConnName>.fgconn` (3.x). Verified on fda 0.9.5: all three bind the named connection even when it is not the first one in a multi-connection app, and later `fda` writes leave the binding alone.
- **Without `-C`, or via `mm`, the name is written as plain text** (`ConnB` or `conn://SQLServerConn`) and fails at runtime — `cm` won't catch it. Never use `fda mm` for connection fields.
- **Read the binding back — don't trust the success message.** For each DB/connector activity and trigger, confirm `input.Connection` / the trigger's connection setting maps to the intended connection's `name` (`fda da connection -f <app>` lists them). `fda da` hides the 3.x `.fgconn` suffix — `conn://<ConnName>` there is correct; only a bare name with no `conn://` is a bad binding.
- **Older fda (0.9.3) bound the FIRST connection.** On fda 0.9.3, `fda sa activity "<flow>.<task>.input.Connection" …` reported success but wrote the UUID of the first entry in the `connections` map, overwriting a correct `ca -C` binding, and `fda sa trigger` wrote the name literally instead of resolving it. If `fda version` is older than 0.9.5, bind with `ca -C` / `ct --connection` only, and fix a wrong binding with `fda sa any "resources.<i>.data.tasks.<j>.activity.input.Connection" --jsonValue '"conn://<uuid>"' -f <app>` (the generic path keeps the value you pass).
- **To update a connection field that is backed by an app property, use `rap` + `cap` — not `sa`.** When a connection field value is an app property reference (e.g. `=$property[PostgreSQL.POSTGRESQL_HOST]`), using `fda sa` would replace the reference with a hardcoded literal, breaking the property binding. There is no "update app property" command, so the correct sequence is: (1) `fda rap <PropertyName> -f <app>` to remove the old property, then (2) `fda cap <PropertyName> <type> <newValue> -f <app>` to recreate it with the updated value. Conversely, if the connection field currently holds a hardcoded value (no `=$property[...]` reference), `fda sa` can be used directly to change it. **`fda cap` type must be `number` (not `float64`) for numeric properties** — `float64` is rejected with `Unknown Flogo Property Type`.

### Database activities

- **SQL queries must end with `;`.** The trailing semicolon terminates the query so the engine can fetch metadata (column names, types). Without it, metadata discovery fails silently and downstream mappings may not resolve.
- **SQL placeholders must use `?<name>` syntax.** Prepared-statement parameters are written as `?keyName` (e.g. `?BookId`), not `@param`, `:param`, or bare `?`. Example: `SELECT * FROM BookStore WHERE id = ?BookId;`
- **Clear `input.input` BEFORE setting the SQL query, not after.** Applies to all DB connector activities (PostgreSQL, MySQL, SQL Server, etc.). `rmm` also clears the auto-generated schema; setting the query after `rmm` regenerates it. Correct order: (1) `rmm` on `input.input`, (2) `sa` to set `input.Query`, (3) `da --json` to confirm `parameters.properties` is populated — if empty (no live DB connection), fix with `sms` by declaring every `?param` from the query: `fda sms <flow>.<activity>.input --json-schema '{"type":"object","properties":{"parameters":{"type":"object","properties":{"<p1>":{"type":"<t1>"},"<p2>":{"type":"<t2>"}}}}}' --field input -f <app>`, (4) `mm` on each leaf field via `input.input.mapping.parameters.<paramName>`. Wrong order causes `mm` to write a JSON blob on the parent.
- **SQL query `Output` is an object with a nested `records` array — not a flat array.** Database query activities (`sqlserver_query`, `postgresql_query`, `mysql_query`) return `Output` as an object shaped `{"records": [...]}`. When using `@foreach` in a Mapper to iterate over query results, the source must be `$activity[QueryName].Output.records` — **not** `$activity[QueryName].Output`. Using the bare `.Output` causes a type error in the UI: `Expected type of parameter 'input' to be 'any[]' but got 'object'`. Always run `fda da activity <flow>.<activity>` to inspect the output schema and confirm the correct path before setting up `@foreach`.
- **A parameterized DB activity's input SCHEMA must declare the same params the mapping targets — or the designer dumps the mapping on the ROOT node.** When you bind `?param` placeholders via `input.input.mapping.parameters.<name>`, the activity's input schema (`schemas.input.input`) MUST list every one of those params under `properties.parameters.properties.<name>` (with matching types). For INSERT/UPDATE activities the auto-derived schema frequently gets this wrong: it puts the `?param` fields under `values.items.properties` (the bulk-row-insert shape) and leaves `parameters.properties` empty `{}`. When the schema's `parameters` doesn't contain the keys your mapping writes to, the VSCode designer can't bind them to leaf nodes and renders the entire mapping as one raw JSON blob on the ROOT `input` node with a red error. **This is a designer-only symptom — the runtime and `fda cm` both still pass**, so you won't catch it from validation alone. Fix: make `parameters.properties` hold every `?param` field; keep `values.items.properties` empty `{}` for the placeholder-param pattern (values is only used for the bulk-array insert style, which is a different mapping shape). Verify by reading back `schemas.input.input` and comparing against a known-good, designer-authored DB activity of the same kind (query vs insert).

### REST trigger & reply

- **REST API identifiers belong in path parameters, not query parameters.** When a REST API accepts an identifier (BookId, userId, orderId, etc.), use path parameters (`/resource/{id}`) rather than query parameters (`/resource?id=`). Path parameters are the REST convention for resource identifiers. When creating `cth` for a REST trigger, use `--restResourcePath /resource/{paramName}`, write a pathParams envelope with matching property names, and associate it with the handler output before running `wth`.
- **Reply has both `data` and `message` → put the payload only in `data`.** Put the value meant for `message` into `data` as-is, and map `message` to a constant (`fda mm <flow>.<actreturn>.input.mappings.message OK -f <app>`) — unmapped fails `cm`. If `data` is missing, create it via `schemas.reply.data` ("`tr_rest` — response schema on reply side") before `wth`, then in step 2b also pass `--output <every field from 2a's flow.metadata.output>,data:object`. Then run `fda sms <flow>.output` with every output field and the full reply schema on `data` — `wth --output` leaves `data` untyped, so the designer shows its Return mapping as raw JSON.
- **Don't hardcode HTTP status code in actreturn mappings.** When setting up `actreturn` `settings.mappings` for `code`, create an app property (`fda cap HttpStatusCode number 200 -f <app>`) and map it as `"code": "=$property[\"HttpStatusCode\"]"` instead of hardcoding `"code": 200`. This makes the response code configurable at deployment time.

### Mappings

- **Don't use `set-attribute` (sa) for mapper input fields when `make-mapping` (mm) exists.** `mm` proactively adds function imports for any expression you write; `sa` doesn't, so you'd rely on the defensive sweep at save time. The sweep catches it eventually but `mm` is more explicit and surfaces errors immediately. Use `sa` only for non-mapping settings.
- **Never guess activity output paths — run `fda lms <target-field>` before any `mm` that reads from another activity's output.**
- **Mapper vs non-mapper `mm` paths — get it from `dmf`, never construct by hand.** Mapper (`act_general_mapper`): `<flow>.<activity>.input.input.mapping.<field>`. All other activities: `<flow>.<activity>.input.<field>`. Using the mapper path on a non-mapper silently writes to the wrong location — CLI reports success but no field is actually set. Always copy the exact PATH from `dmf` output into `mm`.
- **Don't use `sms` on Mapper activity output side.** The Mapper's Output tab in the UI is read-only — it always mirrors the input schema. Setting an inline schema on the output via `sms --json-schema` or `--json-value-to-schema` writes to the JSON file but has no effect in the UI. Only use `sms` on the input side (or omit the direction to apply to both, which is the default).
- **`actreturn` settings.mappings — use `fda mm`, not `sa` or hand-editing.** The actreturn mappings live under `settings.mappings` as a flat object (keys = flow output names from `flow.metadata.output`, values = literals or `=expression` strings). `fda mm` rewrites the path from `input.mappings` to `settings.mappings` automatically via the settingFields metadata, so always use `mm` to set actreturn mappings. Do NOT use `fda sa` — it mangles JSON objects. Do NOT hand-edit the `.flogo` JSON — that contradicts the tool's purpose and the `contrib` blob gets re-derived on every `fda` save. Example:
  ```bash
  fda mm "<flow>.<actreturn>.input.mappings.code" '=$property["HttpStatusCode"]' -f <app>
  fda mm "<flow>.<actreturn>.input.mappings.message" '=coerce.toString($activity[QueryDB].Output)' -f <app>
  ```
- **Dynamic input settings (e.g. MessageAttributeNames) require named entries.** Set the names array as `[{"Name":"X","Type":"String"}]` objects via `sa --jsonValue`. For activities, also map each value individually via `mm` on the parent object's children (e.g. `mm ...MessageAttributes.X "val"`) — never as a single JSON blob. For trigger handlers, only add the attribute names — values are picked up automatically from the activity.
- **Link condition values don't take a leading `=`.** When setting a condition on a link via `fda sa flow '<Flow>.links[N].value'`, the value is already evaluated as an expression — don't prefix with `=`. Only mapping values (`mm`) need the `=` prefix. Example: `fda sa flow 'MyFlow.links[0].value' 'string.equals($flow.pathParams.type, "domestic")' -f <app>` — note no `=` before `string.equals(...)`.
- **Check source vs target types before mapping; use `coerce.toXxx()` for mismatches.** Compare source type (from `da` or `lms`) against target type. The live-DB-derived schema is the source of truth — never override it to match the source type. REST path/query params are always strings; bridge mismatches with `coerce.toXxx()` in the mapping. Before every `mm` on a DB activity parameter: (1) run `fda da activity <flow>.<activity>` to read the DB-derived types, (2) apply the matching coerce (`coerce.toInt` for integer, `coerce.toFloat64` for float, etc.), (3) run `fda exp function coerce` to confirm the function exists. Don't wrap when types already match.
- **Prefer simple direct mappings.** Add a function only when a type conversion is needed (`coerce.toXxx()`), never to reshape data on your own (e.g. `array.get`).
- **Never use `[N]` bracket indexing on function results or arrays in mapping expressions.** The Flogo expression engine parses `[N]` as a resolver reference (looking for a name), not array indexing — `json.jq(...)[0]` fails with "Invalid reference, cannot find name '0'". When you do need an element, use `array.get(arr, N)` instead. This applies to any function that returns an array (e.g. `json.jq`, `array.slice`, `array.flatten`). Example: `=array.get(json.jq($activity[Source].output.catalog, ".[] | select(.code == \"P001\")"), 0)` — NOT `=json.jq(...)[0]`.
- **`flow.metadata.input` and `flow.metadata.output` must be arrays of `{"name","type","value"}` descriptors** — not nested objects. The UI calls `.reduce()` on them; a non-array causes `e.reduce is not a function`. Correct: `fda sa flow "Flow1.metadata" --jsonValue '{"output":[{"name":"result","type":"object","value":null}]}' -f <app>`. Wrong: `'{"output":{"result":{"type":"object"}}}'`.
- **Schema-typed or object fields on non-mapper activities (including Return/actreturn outputs) need `.mapping.` in the child path.** When a non-mapper activity has a schema bound via `sms --field <fieldName>`, map children as `<flow>.<activity>.input.<field>.mapping.<child>` — not `input.<field>.<child>`. Without `.mapping.`, children collapse into a JSON blob on the parent. Example: `fda mm "Flow1.Publish.input.payload.mapping.MsgText" "hello" -f <app>` — not `...input.payload.MsgText`.

## When the user asks "build and run this app"

`fda` itself doesn't build/run — that's `flogobuild` (see the `flogobuild` skill). Typical end-to-end loop is:

1. `fda` to construct/edit the project
2. `fda cm -f <app>` to validate mappings before building
3. `flogobuild build-exe -f <app>.flogo` to compile to a native binary (the `flogobuild` skill covers 2.x `.flogo` apps)
4. `./<binary>` to run it

Use the `flogobuild` skill for the build/run side; this skill is for the design-time edits that come before.
