# Manual-config gap — the "below things are not configured…" section

`fda` builds the whole app graph, but a few things depend on **your** environment, **your** secrets, or a **running backend** — they can't be baked into a portable, secret-free app. Paste the block below (edited to the actual use case) at the **end of the generated `README.md`**, and tell the user the same thing when you hand off.

Keep the heading verbatim so it's unmistakable.

---

## ⚠️ Below things are NOT configured — please configure them manually before running the app end to end

The apps were generated with the Flogo Design CLI and build to `.exe`, but the following are intentionally **not** set (environment-, secret-, or backend-specific). Configure each before an end-to-end run:

1. **LLM credentials & endpoint.**
   - `API_Key` — set to your real provider key (kept out of the repo; inject as an app property / env at deploy).
   - `LLM_Base_URL` — must be a **real endpoint** (e.g. `https://api.openai.com/v1`). It is **not** blank on purpose: an empty value becomes the literal `New_value` and the LLM call fails with `unsupported protocol scheme`.
   - `LLM_Model` — confirm the model name is one your key can access.

2. **PostgreSQL database & credentials.**
   - Create the database and load `database.sql` (then `reset_data.sql` to reset between demos).
   - Set `PostgreSQL.PostgresConn.Host/Port/Database_Name/User/Password` to your instance. The `Password` should be a real secret, not committed in plaintext.
   - Verify connectivity: run each MCP tool's `SELECT` and each A2A write's SQL against the DB.

3. **Ports must be free & consistent.**
   - MCP `<mcpPort>`, each A2A `<agentPort>`, and the orchestrator `<wsPort>` must be free on the host.
   - The orchestrator's MCP `serverUrl` and each A2A `serverUrl` must match the MCP/A2A ports. If you change a port, change it in the property **and** in the corresponding orchestrator connection URL.

4. **Backend REST services for A2A action agents** *(NOT created by default — only present if the user explicitly asked for a REST backend).*
   - By default the A2A action agents write **directly to PostgreSQL** and no separate REST/backend app exists, so this item usually does not apply — **omit it from the README unless the build actually includes a REST agent.**
   - If a REST agent *was* requested: agents that `InvokeRESTService` need the target API **running and reachable** at the configured `<Backend>_URL` (including any `{pathParams}`). Stand up the real backend (or a mock) before invoking those agents. Without it, the agent's REST step fails even though the app is otherwise correct.

5. **Email / SMTP** *(only if an email agent is included).*
   - Set `Email_Username`, `Email_App_Password` (an app-specific password, not the account password), and the recipient property.
   - Confirm outbound SMTP (Gmail: `smtp.gmail.com:465`, SSL) is allowed from the host/network.
   - **Re-enter `Email_App_Password` in the designer's App Properties panel so it is stored as a `SECRET:` value — do NOT change its type.** FDA `cap` writes the password as a plaintext `string`, but the `#sendmail` `Password` field only binds cleanly to a **secret-valued** property; a plaintext one shows *"Type of field 'Password' (password) differs from bound app property (string)"*. Fix it by opening App Properties and re-typing the password value once — the designer encrypts it to `SECRET:…`, which clears the ✗. ⚠️ **Leave the property's type as `string`.** There is no `password` app-property type; setting one makes the designer *silently drop the property on save*, turning the warning into a hard error: *"'Password' is bound to app property 'Email_App_Password' which does not exist."* It builds/runs as a string either way — this only clears designer validation.

6. **Chatbot / WebSocket client.**
   - The orchestrator exposes `ws://<host>:<wsPort>/<usecase>`. Point your chat UI (or a WS test client) at it. There is no bundled UI.

7. **Deploy-time secret injection** *(if deploying to TIBCO Platform / Control Plane rather than running the local `.exe`).*
   - Provide `API_Key`, DB `Password`, and `Email_App_Password` as platform secrets / app properties at deploy time; do not ship them inside the app.
   - Ensure the build context / runtime version matches your target environment.

8. **Flogo Design Assistant (FDA) manual steps** *(Tech-Preview limitations — the apps still build/run as `.exe`; these clear designer validation and cover things FDA cannot configure). Full list + rationale in the skill's `fda-limitations.md`.*
   - **Sync every trigger.** FDA-built triggers are non-OpenAPI (`tr_mcpserver`, `tr_agent`, `tr_wsserver`), so some trigger/flow-input fields don't render and the `toolParams`/input mappings show a red ✗ until you click **"Sync"** once on each trigger. *(Documented limitation: "Manual Sync for Non-OpenAPI Triggers".)*
   - **Validate every connection.** FDA creates connections **without validating** them. Open each (PostgreSQL, LLM provider, MCP, A2A) and click **Connect / Test** to establish and verify it before running.
   - **Set the email password as a secret.** Re-enter `Email_App_Password` in **App Properties** so it is stored as `SECRET:` (see item 5). FDA app properties support only string/boolean/number — **never set the type to `password`** (it's invalid and gets dropped → *"property … does not exist"*).
   - **Certificates (if any).** FDA cannot add certificates. If a connection/trigger/activity needs one (secure DB/TLS, HTTPS or SMTP **Server Certificate**), add it manually.
   - **Branches / activity loops / error handlers (only if the use case uses them).** FDA cannot create or modify branches (success↔error, conditional links — these need direct `.flogo` edits), configure activity loops, or add activities to an error handler. Configure these manually in the designer.

**Quick pre-flight checklist**

- [ ] DB created, `database.sql` loaded, row counts sane
- [ ] LLM `API_Key`, `LLM_Base_URL` (real endpoint), `LLM_Model` set
- [ ] All ports free; orchestrator MCP/A2A URLs match the MCP/A2A ports
- [ ] REST backends running (if any REST agent) / SMTP reachable (if email agent)
- [ ] Start order: MCP → A2A → Orchestrator; each logs a clean start
- [ ] WebSocket client connects to `ws://<host>:<wsPort>/<usecase>` and gets a reply

---

### Note for the skill author (not for the README)

Everything else — including the `mcpServers` / `remoteAgents` `conn://` arrays, tool/handler schemas, the wsserver headers schema, and the `wsconnection:any` typing — **is** configured automatically by the `fda` recipes. Do **not** list those as manual steps; they were common failure points precisely because people set them by hand, and the recipes now handle them. List the environment/secret/backend items 1–7 (trimmed to the ones this use case actually uses), **plus item 8 (the FDA Tech-Preview limitations)** — item 8 is *not* a recipe gap; those steps (Sync triggers, validate connections, password-as-secret, and any certs/branches/loops/error-handlers) are manual because the product documents them as unsupported. See `fda-limitations.md`.
