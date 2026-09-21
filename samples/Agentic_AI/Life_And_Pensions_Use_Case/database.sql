-- =====================================================================
-- Life & Pensions Member Assistant — Agentic AI Use Case
-- PostgreSQL 14+   |   Database: life_pensions
-- Locale: United States  |  Currency: USD
--
-- Domain: a mutual life, pensions & investments provider (member
-- self-service). Read data via MCP tools; write actions via A2A agents:
--   update beneficiary, change contribution, fund switch, submit claim,
--   book adviser callback, send confirmation email.
--
-- Data is engineered so every demo scenario is demonstrable:
--   * A flagship persona (James Carter, MBR-100001) fully populated.
--   * One "exception" record per write path (outdated beneficiary,
--     under-matched contribution, over-weight high-risk fund, a
--     claimable policy with no existing claim).
-- =====================================================================

-- Drop in reverse-dependency order -----------------------------------
DROP TABLE IF EXISTS fund_switches      CASCADE;
DROP TABLE IF EXISTS adviser_callbacks  CASCADE;
DROP TABLE IF EXISTS claims             CASCADE;
DROP TABLE IF EXISTS beneficiaries      CASCADE;
DROP TABLE IF EXISTS contributions      CASCADE;
DROP TABLE IF EXISTS holdings           CASCADE;
DROP TABLE IF EXISTS funds              CASCADE;
DROP TABLE IF EXISTS retirement_accounts CASCADE;
DROP TABLE IF EXISTS policies           CASCADE;
DROP TABLE IF EXISTS members            CASCADE;

-- =====================================================================
-- 1. members — the member (policyholder / account holder) profile
-- =====================================================================
CREATE TABLE members (
    member_id       VARCHAR(20) PRIMARY KEY,          -- MBR-1000NN
    first_name      VARCHAR(60)  NOT NULL,
    last_name       VARCHAR(60)  NOT NULL,
    email           VARCHAR(120) NOT NULL,
    phone           VARCHAR(20),
    date_of_birth   DATE         NOT NULL,
    address         VARCHAR(160),
    city            VARCHAR(80),
    state           VARCHAR(2),
    zip             VARCHAR(10),
    ssn_last4       VARCHAR(4),
    marital_status  VARCHAR(12) CHECK (marital_status IN ('Single','Married','Divorced','Widowed')),
    member_since    DATE         NOT NULL
);

-- =====================================================================
-- 2. policies — one row per protection / investment product a member holds
--    (retirement accounts are modeled separately, see table 3)
-- =====================================================================
CREATE TABLE policies (
    policy_id         VARCHAR(20) PRIMARY KEY,        -- POL-2026-XXXX
    member_id         VARCHAR(20) NOT NULL REFERENCES members(member_id),
    product_type      VARCHAR(20) NOT NULL
        CHECK (product_type IN ('Life','CriticalIllness','IncomeProtection','Investment')),
    product_name      VARCHAR(80) NOT NULL,
    status            VARCHAR(12) NOT NULL
        CHECK (status IN ('Active','Lapsed','Pending','Cancelled')),
    coverage_amount   NUMERIC(12,2) NOT NULL,         -- sum assured, or account value for Investment
    premium           NUMERIC(10,2) NOT NULL,         -- USD per premium_frequency
    premium_frequency VARCHAR(10) NOT NULL
        CHECK (premium_frequency IN ('Monthly','Quarterly','Annual')),
    start_date        DATE NOT NULL,
    renewal_date      DATE
);

-- =====================================================================
-- 3. retirement_accounts — 401(k) / IRA balances (writeable: contribution)
-- =====================================================================
CREATE TABLE retirement_accounts (
    account_id               VARCHAR(20) PRIMARY KEY, -- RET-XXXX
    member_id                VARCHAR(20) NOT NULL REFERENCES members(member_id),
    account_type             VARCHAR(20) NOT NULL
        CHECK (account_type IN ('401(k)','Traditional IRA','Roth IRA')),
    balance                  NUMERIC(14,2) NOT NULL,
    ytd_contribution         NUMERIC(12,2) NOT NULL DEFAULT 0,
    contribution_rate        NUMERIC(5,2)  NOT NULL DEFAULT 0,  -- % of salary (401k) or n/a for IRA
    employer_match_rate      NUMERIC(5,2)  NOT NULL DEFAULT 0,  -- max % employer will match
    annual_contribution_limit NUMERIC(10,2) NOT NULL,
    vested_balance           NUMERIC(14,2) NOT NULL,
    opened_date              DATE NOT NULL
);

-- =====================================================================
-- 4. funds — investment fund catalog (shared, not per member)
-- =====================================================================
CREATE TABLE funds (
    fund_id        VARCHAR(20) PRIMARY KEY,           -- FND-XXX
    fund_name      VARCHAR(80) NOT NULL,
    category       VARCHAR(16) NOT NULL
        CHECK (category IN ('Equity','Bond','Balanced','Money Market','Target Date','Index')),
    risk_level     VARCHAR(8) NOT NULL
        CHECK (risk_level IN ('Low','Medium','High')),
    ytd_return     NUMERIC(6,2) NOT NULL,             -- %
    one_yr_return  NUMERIC(6,2) NOT NULL,             -- %
    three_yr_return NUMERIC(6,2) NOT NULL,            -- %
    expense_ratio  NUMERIC(5,3) NOT NULL,             -- %
    nav            NUMERIC(10,2) NOT NULL             -- net asset value per unit, USD
);

-- =====================================================================
-- 5. holdings — a retirement account's allocation across funds (writeable: switch)
-- =====================================================================
CREATE TABLE holdings (
    holding_id     VARCHAR(20) PRIMARY KEY,           -- HLD-XXX
    account_id     VARCHAR(20) NOT NULL REFERENCES retirement_accounts(account_id),
    fund_id        VARCHAR(20) NOT NULL REFERENCES funds(fund_id),
    units          NUMERIC(14,4) NOT NULL,
    value          NUMERIC(14,2) NOT NULL,            -- USD
    allocation_pct NUMERIC(5,2) NOT NULL              -- % of account balance
);

-- =====================================================================
-- 6. contributions — contribution / premium payment history (writeable: change)
-- =====================================================================
CREATE TABLE contributions (
    contribution_id   VARCHAR(20) PRIMARY KEY,        -- CON-XXXX
    member_id         VARCHAR(20) NOT NULL REFERENCES members(member_id),
    account_id        VARCHAR(20) REFERENCES retirement_accounts(account_id),
    policy_id         VARCHAR(20) REFERENCES policies(policy_id),
    amount            NUMERIC(12,2) NOT NULL,         -- USD
    contribution_type VARCHAR(12) NOT NULL
        CHECK (contribution_type IN ('Employee','Employer','Premium','Rollover')),
    frequency         VARCHAR(10) NOT NULL
        CHECK (frequency IN ('Monthly','Quarterly','Annual','OneTime')),
    contribution_date DATE NOT NULL
);

-- =====================================================================
-- 7. beneficiaries — nominated beneficiaries per policy (writeable: update)
-- =====================================================================
CREATE TABLE beneficiaries (
    beneficiary_id   VARCHAR(20) PRIMARY KEY,         -- BEN-XXX
    policy_id        VARCHAR(20) NOT NULL REFERENCES policies(policy_id),
    beneficiary_name VARCHAR(120) NOT NULL,
    relationship     VARCHAR(12) NOT NULL
        CHECK (relationship IN ('Spouse','Child','Parent','Sibling','Trust','Other')),
    share_pct        NUMERIC(5,2) NOT NULL,           -- % of benefit
    is_primary       BOOLEAN NOT NULL DEFAULT TRUE,
    date_added       DATE NOT NULL
);

-- =====================================================================
-- 8. claims — protection claims (writeable: submit)
-- =====================================================================
CREATE TABLE claims (
    claim_id     VARCHAR(20) PRIMARY KEY,             -- CLM-2026-XXX
    policy_id    VARCHAR(20) NOT NULL REFERENCES policies(policy_id),
    member_id    VARCHAR(20) NOT NULL REFERENCES members(member_id),
    claim_type   VARCHAR(20) NOT NULL
        CHECK (claim_type IN ('Life','CriticalIllness','IncomeProtection','Disability')),
    amount       NUMERIC(12,2) NOT NULL,
    status       VARCHAR(12) NOT NULL
        CHECK (status IN ('Submitted','UnderReview','Approved','Paid','Denied')),
    submitted_date DATE NOT NULL,
    description  VARCHAR(300),
    last_update  TIMESTAMP NOT NULL
);

-- =====================================================================
-- 9. adviser_callbacks — adviser callback requests (AGENT-WRITTEN, empty at reset)
-- =====================================================================
CREATE TABLE adviser_callbacks (
    callback_id    VARCHAR(20) PRIMARY KEY,           -- CBK-XXXX
    member_id      VARCHAR(20) NOT NULL REFERENCES members(member_id),
    topic          VARCHAR(120) NOT NULL,
    preferred_time VARCHAR(60) NOT NULL,
    phone          VARCHAR(20),
    status         VARCHAR(12) NOT NULL
        CHECK (status IN ('Requested','Scheduled','Completed','Cancelled')),
    created_at     TIMESTAMP NOT NULL
);

-- =====================================================================
-- 10. fund_switches — fund switch requests (AGENT-WRITTEN, empty at reset)
-- =====================================================================
CREATE TABLE fund_switches (
    switch_id    VARCHAR(20) PRIMARY KEY,             -- SWT-XXXX
    account_id   VARCHAR(20) NOT NULL REFERENCES retirement_accounts(account_id),
    from_fund_id VARCHAR(20) NOT NULL REFERENCES funds(fund_id),
    to_fund_id   VARCHAR(20) NOT NULL REFERENCES funds(fund_id),
    amount       NUMERIC(14,2) NOT NULL,
    status       VARCHAR(12) NOT NULL
        CHECK (status IN ('Requested','Processing','Completed')),
    created_at   TIMESTAMP NOT NULL
);

-- Indexes -------------------------------------------------------------
CREATE INDEX idx_policies_member        ON policies(member_id);
CREATE INDEX idx_retirement_member      ON retirement_accounts(member_id);
CREATE INDEX idx_holdings_account       ON holdings(account_id);
CREATE INDEX idx_holdings_fund          ON holdings(fund_id);
CREATE INDEX idx_contributions_member   ON contributions(member_id);
CREATE INDEX idx_contributions_account  ON contributions(account_id);
CREATE INDEX idx_beneficiaries_policy   ON beneficiaries(policy_id);
CREATE INDEX idx_claims_member          ON claims(member_id);
CREATE INDEX idx_claims_policy          ON claims(policy_id);
CREATE INDEX idx_callbacks_member       ON adviser_callbacks(member_id);
CREATE INDEX idx_switches_account       ON fund_switches(account_id);

-- =====================================================================
-- === DEMO DATA ===
-- =====================================================================

-- ---- members --------------------------------------------------------
INSERT INTO members (member_id, first_name, last_name, email, phone, date_of_birth, address, city, state, zip, ssn_last4, marital_status, member_since) VALUES
('MBR-100001','James','Carter','james.carter@example.com','+1-415-555-0101','1968-03-14','120 Market St','San Francisco','CA','94105','4821','Divorced','2009-06-01'),   -- FLAGSHIP persona
('MBR-100002','Maria','Gonzalez','maria.gonzalez@example.com','+1-312-555-0102','1985-09-22','88 Lakeshore Dr','Chicago','IL','60601','7719','Married','2016-02-15'),
('MBR-100003','David','Chen','david.chen@example.com','+1-206-555-0103','1979-12-05','45 Pine Ave','Seattle','WA','98101','3355','Married','2013-11-20'),
('MBR-100004','Susan','Miller','susan.miller@example.com','+1-617-555-0104','1990-07-30','12 Beacon St','Boston','MA','02108','9042','Single','2020-08-10'),
('MBR-100005','Robert','Johnson','robert.johnson@example.com','+1-303-555-0105','1962-01-19','300 Larimer St','Denver','CO','80202','1187','Married','2007-04-25'),
('MBR-100006','Linda','Williams','linda.williams@example.com','+1-512-555-0106','1974-11-11','700 Congress Ave','Austin','TX','78701','6620','Widowed','2011-09-05'),
('MBR-100007','Michael','Brown','michael.brown@example.com','+1-404-555-0107','1988-05-02','15 Peachtree St','Atlanta','GA','30303','4408','Single','2018-03-12'),
('MBR-100008','Jennifer','Davis','jennifer.davis@example.com','+1-305-555-0108','1983-08-17','950 Ocean Dr','Miami','FL','33139','2231','Married','2015-07-19'),
('MBR-100009','William','Martinez','william.martinez@example.com','+1-602-555-0109','1971-04-28','55 Camelback Rd','Phoenix','AZ','85012','5573','Married','2010-10-30'),
('MBR-100010','Patricia','Wilson','patricia.wilson@example.com','+1-503-555-0110','1995-02-09','21 Burnside St','Portland','OR','97209','8890','Single','2021-05-14');

-- ---- policies -------------------------------------------------------
INSERT INTO policies (policy_id, member_id, product_type, product_name, status, coverage_amount, premium, premium_frequency, start_date, renewal_date) VALUES
-- James Carter (flagship): full protection stack, and NO existing claim (so he can submit one)
('POL-2026-1001','MBR-100001','Life','20-Year Term Life',           'Active', 500000.00, 45.00, 'Monthly','2015-06-01','2035-06-01'),
('POL-2026-1002','MBR-100001','CriticalIllness','Critical Illness Protect','Active',100000.00, 28.50, 'Monthly','2018-04-10','2028-04-10'),
('POL-2026-1003','MBR-100001','IncomeProtection','Income Shield Plan','Active',   4000.00, 32.00, 'Monthly','2019-01-15','2029-01-15'),
-- Maria Gonzalez
('POL-2026-1004','MBR-100002','Life','Whole Life Secure',           'Active', 250000.00, 68.00, 'Monthly','2016-02-15','2046-02-15'),
('POL-2026-1005','MBR-100002','Investment','Managed Growth Portfolio','Active', 65000.00,200.00, 'Monthly','2017-03-01', NULL),
-- David Chen
('POL-2026-1006','MBR-100003','IncomeProtection','Income Shield Plan','Active',   5500.00, 41.00, 'Monthly','2014-06-01','2034-06-01'),
('POL-2026-1007','MBR-100003','Life','20-Year Term Life',           'Active', 400000.00, 52.00, 'Monthly','2014-06-01','2034-06-01'),
-- Susan Miller (a LAPSED policy — edge case)
('POL-2026-1008','MBR-100004','Life','10-Year Term Life',           'Lapsed', 300000.00, 24.00, 'Monthly','2020-08-10','2030-08-10'),
-- Robert Johnson (near retirement)
('POL-2026-1009','MBR-100005','CriticalIllness','Critical Illness Protect','Active',150000.00, 62.00,'Monthly','2010-05-01','2030-05-01'),
('POL-2026-1010','MBR-100005','Life','Whole Life Secure',           'Active', 350000.00, 95.00, 'Monthly','2007-04-25','2047-04-25'),
-- Linda Williams
('POL-2026-1011','MBR-100006','IncomeProtection','Income Shield Plan','Active',   3800.00, 30.00, 'Monthly','2016-01-10','2036-01-10'),
('POL-2026-1012','MBR-100006','Life','20-Year Term Life',           'Active', 450000.00, 58.00, 'Monthly','2011-09-05','2031-09-05'),
-- Michael Brown
('POL-2026-1013','MBR-100007','Life','20-Year Term Life',           'Active', 200000.00, 22.00, 'Monthly','2018-03-12','2038-03-12'),
-- Jennifer Davis
('POL-2026-1014','MBR-100008','IncomeProtection','Income Shield Plan','Active',   4500.00, 36.00, 'Monthly','2015-07-19','2035-07-19'),
('POL-2026-1015','MBR-100008','Investment','Balanced Investor Plan', 'Active', 42000.00,150.00, 'Monthly','2019-02-01', NULL),
-- William Martinez
('POL-2026-1016','MBR-100009','Life','Whole Life Secure',           'Active', 300000.00, 80.00, 'Monthly','2010-10-30','2050-10-30'),
-- Patricia Wilson (new, pending underwriting)
('POL-2026-1017','MBR-100010','CriticalIllness','Critical Illness Protect','Pending',75000.00,26.00,'Monthly','2026-07-01','2036-07-01');

-- ---- retirement_accounts -------------------------------------------
-- RET-5001 James: 401(k) contributing only 3% while employer matches up to 6% -> UNDER-MATCHED (change-contribution scenario)
INSERT INTO retirement_accounts (account_id, member_id, account_type, balance, ytd_contribution, contribution_rate, employer_match_rate, annual_contribution_limit, vested_balance, opened_date) VALUES
('RET-5001','MBR-100001','401(k)',        181685.00,  9200.00, 3.00, 6.00, 23500.00, 181685.00,'2009-06-01'),  -- WRONG: only 3% vs 6% match
('RET-5002','MBR-100001','Roth IRA',       45300.00,  3500.00, 0.00, 0.00,  7000.00,  45300.00,'2016-01-10'),
('RET-5003','MBR-100002','401(k)',         98250.00,  8100.00, 6.00, 6.00, 23500.00,  92000.00,'2016-02-15'),
('RET-5004','MBR-100003','Traditional IRA',127400.00, 6500.00, 0.00, 0.00,  7000.00, 127400.00,'2013-11-20'),
('RET-5005','MBR-100005','401(k)',        512300.00, 15000.00, 8.00, 6.00, 23500.00, 512300.00,'2007-04-25'),  -- near-retirement, large balance
('RET-5006','MBR-100006','401(k)',        203900.00, 10200.00, 5.00, 5.00, 23500.00, 198000.00,'2011-09-05'),
('RET-5007','MBR-100007','Roth IRA',        31800.00, 4200.00, 0.00, 0.00,  7000.00,  31800.00,'2018-03-12'),
('RET-5008','MBR-100008','401(k)',         76400.00,  7300.00, 4.00, 5.00, 23500.00,  70000.00,'2015-07-19');

-- ---- funds (catalog) -----------------------------------------------
INSERT INTO funds (fund_id, fund_name, category, risk_level, ytd_return, one_yr_return, three_yr_return, expense_ratio, nav) VALUES
('FND-001','Aggressive Growth Equity Fund','Equity','High',      14.20, 18.50, 12.10, 0.850, 42.15),  -- HIGH risk (fund-switch source)
('FND-002','S&P 500 Index Fund',           'Index','Medium',     11.50, 15.20, 10.80, 0.040, 88.40),
('FND-003','Total Bond Market Fund',       'Bond','Low',          3.20,  4.10,  2.50, 0.050, 10.85),
('FND-004','Balanced Allocation Fund',     'Balanced','Medium',   7.80,  9.50,  6.90, 0.350, 25.60),
('FND-005','Target Retirement 2045 Fund',  'Target Date','Medium',9.10, 11.80,  8.20, 0.150, 33.20),
('FND-006','Money Market Fund',            'Money Market','Low',  4.90,  5.10,  3.80, 0.110,  1.00),
('FND-007','International Equity Fund',     'Equity','High',      10.30, 13.70,  7.50, 0.550, 29.75),
('FND-008','Dividend Value Fund',          'Equity','Medium',     8.60, 10.90,  8.00, 0.400, 51.30),
('FND-009','Short-Term Treasury Fund',     'Bond','Low',          2.80,  3.50,  2.10, 0.080, 20.10),
('FND-010','Target Retirement 2035 Fund',  'Target Date','Medium',8.30, 10.50,  7.60, 0.150, 28.90);

-- ---- holdings ------------------------------------------------------
-- James 401(k) RET-5001: over-weight in HIGH-risk Aggressive Growth (FND-001) -> fund-switch scenario
INSERT INTO holdings (holding_id, account_id, fund_id, units, value, allocation_pct) VALUES
('HLD-001','RET-5001','FND-001', 1500.0000, 63225.00, 34.80),   -- HIGH risk, over-weight near retirement
('HLD-002','RET-5001','FND-002',  800.0000, 70720.00, 38.92),
('HLD-003','RET-5001','FND-003', 4400.0000, 47740.00, 26.28),
('HLD-004','RET-5002','FND-005', 1364.4578, 45300.00,100.00),   -- James Roth IRA
('HLD-005','RET-5003','FND-002',  650.0000, 57460.00, 58.48),   -- Maria
('HLD-006','RET-5003','FND-004', 1593.7500, 40800.00, 41.52),
('HLD-007','RET-5004','FND-008', 1200.0000, 61560.00, 48.32),   -- David
('HLD-008','RET-5004','FND-003', 6067.2811, 65830.00, 51.68),
('HLD-009','RET-5005','FND-005', 9500.0000,315400.00, 61.57),   -- Robert (near retirement)
('HLD-010','RET-5005','FND-003',18147.0000,196900.00, 38.43),
('HLD-011','RET-5006','FND-002', 1500.0000,132600.00, 65.03),   -- Linda
('HLD-012','RET-5006','FND-003', 6571.4286, 71300.00, 34.97),
('HLD-013','RET-5007','FND-001',  754.4484, 31800.00,100.00),   -- Michael
('HLD-014','RET-5008','FND-004', 1789.0625, 45800.00, 59.95),   -- Jennifer
('HLD-015','RET-5008','FND-006',30600.0000, 30600.00, 40.05);

-- ---- contributions (history) ---------------------------------------
INSERT INTO contributions (contribution_id, member_id, account_id, policy_id, amount, contribution_type, frequency, contribution_date) VALUES
('CON-9001','MBR-100001','RET-5001',NULL,  383.33,'Employee','Monthly','2026-07-01'),
('CON-9002','MBR-100001','RET-5001',NULL,  766.66,'Employer','Monthly','2026-07-01'),
('CON-9003','MBR-100001','RET-5001',NULL,  383.33,'Employee','Monthly','2026-06-01'),
('CON-9004','MBR-100001','RET-5002',NULL,  291.66,'Employee','Monthly','2026-07-01'),
('CON-9005','MBR-100001',NULL,'POL-2026-1001', 45.00,'Premium','Monthly','2026-07-01'),
('CON-9006','MBR-100002','RET-5003',NULL,  675.00,'Employee','Monthly','2026-07-01'),
('CON-9007','MBR-100002','RET-5003',NULL,  675.00,'Employer','Monthly','2026-07-01'),
('CON-9008','MBR-100003','RET-5004',NULL,  541.66,'Employee','Monthly','2026-07-01'),
('CON-9009','MBR-100005','RET-5005',NULL, 1250.00,'Employee','Monthly','2026-07-01'),
('CON-9010','MBR-100005','RET-5005',NULL,  937.50,'Employer','Monthly','2026-07-01'),
('CON-9011','MBR-100006','RET-5006',NULL,  850.00,'Employee','Monthly','2026-07-01'),
('CON-9012','MBR-100007','RET-5007',NULL,  350.00,'Employee','Monthly','2026-07-01'),
('CON-9013','MBR-100008','RET-5008',NULL,  608.33,'Employee','Monthly','2026-07-01'),
('CON-9014','MBR-100002',NULL,'POL-2026-1005',200.00,'Premium','Monthly','2026-07-01'),
('CON-9015','MBR-100008',NULL,'POL-2026-1015',150.00,'Premium','Monthly','2026-07-01'),
('CON-9016','MBR-100001','RET-5002',NULL, 2000.00,'Rollover','OneTime','2026-01-15');

-- ---- beneficiaries -------------------------------------------------
-- James's Life policy names an EX-SPOUSE (Divorced) -> update-beneficiary scenario
INSERT INTO beneficiaries (beneficiary_id, policy_id, beneficiary_name, relationship, share_pct, is_primary, date_added) VALUES
('BEN-001','POL-2026-1001','Emily Carter','Spouse',100.00, TRUE, '2015-06-01'),   -- OUTDATED (ex-spouse; member is Divorced)
('BEN-002','POL-2026-1002','Emily Carter','Spouse',100.00, TRUE, '2018-04-10'),   -- OUTDATED
('BEN-003','POL-2026-1004','Carlos Gonzalez','Spouse',100.00, TRUE,'2016-02-15'),
('BEN-004','POL-2026-1007','Grace Chen','Spouse', 60.00, TRUE, '2014-06-01'),
('BEN-005','POL-2026-1007','Ethan Chen','Child', 40.00, FALSE,'2014-06-01'),
('BEN-006','POL-2026-1010','Nancy Johnson','Spouse',100.00, TRUE,'2007-04-25'),
('BEN-007','POL-2026-1012','The Williams Family Trust','Trust',100.00, TRUE,'2011-09-05'),
('BEN-008','POL-2026-1013','Karen Brown','Parent',100.00, TRUE,'2018-03-12'),
('BEN-009','POL-2026-1016','Sofia Martinez','Spouse',50.00, TRUE,'2010-10-30'),
('BEN-010','POL-2026-1016','Diego Martinez','Child',50.00, FALSE,'2010-10-30');

-- ---- claims (seeded; James/MBR-100001 intentionally has NONE) -------
INSERT INTO claims (claim_id, policy_id, member_id, claim_type, amount, status, submitted_date, description, last_update) VALUES
('CLM-2026-001','POL-2026-1006','MBR-100003','IncomeProtection', 5500.00,'UnderReview','2026-06-18','Signed off work — back injury, monthly benefit claim','2026-06-25 09:30:00'),
('CLM-2026-002','POL-2026-1009','MBR-100005','CriticalIllness',150000.00,'Approved',  '2026-05-02','Critical illness diagnosis — cardiac','2026-05-20 14:15:00'),
('CLM-2026-003','POL-2026-1014','MBR-100008','IncomeProtection', 4500.00,'Paid',      '2026-03-10','Temporary disability — recovered','2026-04-15 11:00:00'),
('CLM-2026-004','POL-2026-1011','MBR-100006','IncomeProtection', 3800.00,'Denied',    '2026-04-22','Claim outside waiting period','2026-05-01 16:45:00');

-- ---- adviser_callbacks : AGENT-WRITTEN — intentionally EMPTY --------
-- (book-adviser-callback A2A agent inserts rows here at demo time)

-- ---- fund_switches : AGENT-WRITTEN — intentionally EMPTY ------------
-- (fund-switch A2A agent inserts rows here at demo time)

-- =====================================================================
-- End of database.sql
-- =====================================================================
