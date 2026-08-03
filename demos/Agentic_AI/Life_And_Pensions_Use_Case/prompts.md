# Life & Pensions Member Assistant -- Demo Prompts

US mutual life, pensions & investments provider. Members are identified by their **`member_id`** (e.g. `MBR-100001`), or by **name / email** — the agent resolves the member from any of these, then uses the `member_id` for all other tools. Currency is **USD**.

> Flagship persona: **James Carter — `MBR-100001` — james.carter@example.com** (San Francisco, CA; Divorced). His data drives every write scenario below. Other personas are listed where useful for variety.

---

## 1. Member Profile & Policies (MCP Only)

```
Show me my policy details. My member ID is MBR-100001.
```
```
What protection cover do I have? MBR-100001.
```
```
Look up my profile — my email is james.carter@example.com.
```

---

## 2. Retirement Savings / Pension Pot (MCP Only)

### James Carter -- 401(k) + Roth IRA (under-matched at 3%)
```
What's my 401(k) balance? My member ID is MBR-100001.
```
```
How much do I have saved for retirement? MBR-100001.
```

### Robert Johnson -- near retirement, large pot
```
What's my pension pot worth? My member ID is MBR-100005.
```

---

## 3. Investments / Fund Holdings (MCP Only)

### James Carter -- over-weight in a HIGH-risk fund
```
How is my 401(k) invested? MBR-100001.
```
```
What funds am I holding, and how risky are they? MBR-100001.
```

### Fund catalog lookup
```
What funds do you offer, and what are their returns? MBR-100001.
```

---

## 4. Contributions & Premiums (MCP Only)

```
Show me my recent contributions. My member ID is MBR-100001.
```
```
How much has gone into my 401(k) this year? MBR-100001.
```

---

## 5. Claims Lookup (MCP Only: GetClaims)

### David Chen -- Income Protection claim UnderReview (CLM-2026-001)
```
What's the status of my claim? My member ID is MBR-100003.
```

### Robert Johnson -- Critical Illness claim Approved (CLM-2026-002)
```
Did my critical illness claim get approved? MBR-100005.
```

### James Carter -- has NO claims
```
Do I have any open claims? MBR-100001.
```

---

## 6. Change Contribution (MCP + A2A: change_contribution_agent)

### James Carter -- raise 401(k) from 3% to 6% to capture full employer match
```
Prompt 1: What's my 401(k) contribution rate, and am I getting the full employer match? MBR-100001.
Prompt 2: Increase my contribution to 6% so I capture the full match.
```

Generated change is logged as `CON-2026-XXXX`.

---

## 7. Fund Switch (MCP + A2A: fund_switch_agent)

### James Carter -- move out of the HIGH-risk Aggressive Growth fund
```
Prompt 1: Is any of my 401(k) in high-risk funds? MBR-100001.
Prompt 2: Move my Aggressive Growth Equity Fund holding into the Target Retirement 2045 fund.
```

Alternative target (defensive):
```
Switch my Aggressive Growth holding into the Total Bond Market Fund instead. MBR-100001.
```

Generated switch is recorded as `SWT-2026-XXXX`.

---

## 8. Update Beneficiary (MCP + A2A: update_beneficiary_agent)

### James Carter -- policy still names ex-spouse Emily Carter
```
Prompt 1: Who is the beneficiary on my Term Life policy? MBR-100001.
Prompt 2: That's my ex-wife. Change the beneficiary on POL-2026-1001 to my daughter, Sarah Carter.
```

Also update the Critical Illness policy:
```
Update the beneficiary on POL-2026-1002 to Sarah Carter as well. MBR-100001.
```

Generated beneficiary record is `BEN-2026-XXXX`.

---

## 9. Submit a Claim (MCP + A2A: submit_claim_agent)

### James Carter -- file an Income Protection claim on POL-2026-1003 (he has none)
```
Prompt 1: I've been signed off work with an injury. Can I claim on my income protection policy? MBR-100001.
Prompt 2: Yes, please file the claim.
```

Generated claim is `CLM-2026-XXX`.

---

## 10. Book an Adviser Callback (A2A: adviser_callback_agent)

### James Carter -- retirement-planning call
```
Prompt 1: I'd like to speak to a financial adviser about my retirement plan. MBR-100001.
Prompt 2: Tomorrow afternoon works best — call me on my mobile.
```

Generated callback is `CBK-2026-XXXX`.

---

## 11. Full Workflow with Email Confirmation (All Agents)

### Increase contribution, then email confirmation
```
Prompt 1: I want to make sure I'm getting my full employer match on my 401(k). MBR-100001.
Prompt 2: Yes, raise my contribution to 6%.
Prompt 3: Please send me an email confirmation.
```

### File a claim, then email confirmation
```
Prompt 1: I need to make an income protection claim — I've been off work sick. MBR-100001.
Prompt 2: Go ahead and submit it.
Prompt 3: Email me the confirmation, please.
```

The `send_confirmation_email` agent sends to the member's email on file (james.carter@example.com).

---

## 12. Multi-Turn Retirement Review (James Carter)

A single conversation that touches read + multiple write paths:

```
Turn 1: Hi, I'm James Carter, member ID MBR-100001. Can you review my retirement plan?
Turn 2: What's my 401(k) balance and am I getting the full employer match?
Turn 3: Please raise my contribution to 6%.
Turn 4: A third of my 401(k) is in that high-risk fund — move it into Target Retirement 2045.
Turn 5: Also, my Term Life policy still names my ex-wife. Change it to my daughter Sarah Carter.
Turn 6: Book me a call with an adviser for next week, and email me confirmations of everything.
```

---

## 13. Edge Cases & Out of Scope

### Claim on a Lapsed policy (agent should decline)
Susan Miller (`MBR-100004`) — her only policy (POL-2026-1008) is **Lapsed**.
```
I want to make a claim on my life policy. My member ID is MBR-100004.
```

### Action on a Pending policy (agent should explain it's not yet active)
Patricia Wilson (`MBR-100010`) — POL-2026-1017 is **Pending** underwriting.
```
Can I claim on my critical illness policy? MBR-100010.
```

### Unknown member
```
What's my pension balance? My member ID is MBR-999999.
```

### Out of scope (agent should politely decline)
```
Can you give me stock tips to beat the market?
Should I pull all my money out of the market right now?
Can you file my taxes for me?
Transfer USD 50,000 from my 401(k) to my bank account today.
What's the weather in San Francisco?
```
