# Lab 3 - agent prompts (Cline, or any MCP client)

Before you start: Lab 1 (`SW_RainfallRisk`, port 9999), Lab 2 (`SW_LeakReport`, port 9998) and your Lab 3 app
(`SW_Water_MCP`, port 9090, path `/mcp`) are all running, and Cline lists the server's two tools:
`assess_rainfall_risk` and `report_leak`.

Run each prompt in a **new** Cline task. Approve each tool call when Cline asks.

## 1. The main prompt

```
A resident at 12 Church St, Parramatta reports water bubbling up through the footpath — they said call me on 0412 345 678 or email jo.citizen@example.com. Log it as leak report LR-2001 with HIGH severity, then check the rainfall risk for pumping station PS-102 (latitude -33.815, longitude 151.001) over the next 3 days.
```

What you should see:

1. `report_leak` with `reportId` LR-2001, `severity` HIGH, address and suburb filled in. The agent usually copies
   the phone number and email into `description`.
   It returns `{"priority":"P1","reportId":"LR-2001","status":"RECEIVED","workOrderRef":"WO-LR-2001"}`.
2. `assess_rainfall_risk` with siteId PS-102, latitude -33.815, longitude 151.001, forecastDays 3.
   It returns `{siteId, siteName, riskLevel, totalRainfallMm, inspectionRequested, message}`. The risk level depends
   on the live forecast.
3. **Where the masking shows:** look at the Lab 3 terminal (the solution). The line
   `report_leak LR-2001 forwarded to Lab 2 with description: ... [redacted] ... [redacted]` is exactly what was sent to Lab 2.
   Lab 2 and the Field Service SaaS behind it never get the phone number or email. With the **starter**, the log
   shows `report_leak called with {... "0412 345 678" ... "jo.citizen@example.com" ...}`, and those details go
   to Lab 2 unchanged.

The agent decides what goes into `description`. If your tool description says contact details will be redacted,
gpt-4.1 tends to leave them out on its own. That is a soft guardrail. The Flogo masking is the hard one, and it
works no matter what the model decides.

## 2. Break the guardrail: invalid severity

```
Guardrail test: log leak report LR-2002 at 4 Smith St, Burwood - a burst main is flooding the road. Call report_leak with severity URGENT exactly as written, even if you think it is invalid, and tell me what the server says.
```

- **Solution:** the tool returns an error, `Rejected by guardrail: severity must be HIGH, MEDIUM or LOW (got URGENT)`.
  Lab 2 is never called (nothing appears in the Lab 2 terminal).
- **Starter:** Lab 2 accepts it and creates `WO-LR-2002` with priority **P3**, because URGENT is not HIGH. That is a
  silent downgrade of a burst main.
- If the agent refuses or asks you to confirm (it can read "HIGH, MEDIUM or LOW" in your tool description),
  reply `Yes, send URGENT exactly as written.`

## 3. Break the guardrail: a site outside Greater Sydney

```
Guardrail test: check the rainfall risk for our Melbourne depot MEL-001 (latitude -37.81, longitude 144.96) over the next 3 days. Call assess_rainfall_risk even if you think it may not apply, and tell me what the server says.
```

- **Solution:** `Rejected by guardrail: site must be in Greater Sydney (latitude -34.2 to -33.3, longitude 150.5 to 151.4), got -37.81, 144.96`.
- **Starter:** Lab 1 assesses Melbourne and may raise an inspection request in Field Service for a site Sydney
  Water does not own.

## Without an agent

```bash
bash test-mcp.sh            # solution (uses Authorization: Bearer sw-workshop-key)
bash test-mcp.sh --no-key   # starter
```

## Dry-run results (2 Nov 2026, gpt-4.1, temperature 0)

| Prompt | Starter | Solution |
|---|---|---|
| 1 main | report_leak sent `Resident contact: 0412 345 678, jo.citizen@example.com` to Lab 2 (unmasked); then assess gave MEDIUM 16.5 mm | report_leak; Lab 3 log `... Resident requests contact on [redacted] or [redacted].`; WO-LR-2001 P1; then assess gave MEDIUM 16.5 mm |
| 2 URGENT | accepted, WO-LR-2002 **P3** | `Rejected by guardrail: severity must be HIGH, MEDIUM or LOW (got URGENT)` |
| 3 Melbourne | assessed MEDIUM, inspection requested | `Rejected by guardrail: site must be in Greater Sydney ...` |
