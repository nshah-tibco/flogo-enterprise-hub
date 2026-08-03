-- =====================================================================
-- Life & Pensions Member Assistant — RESET script
-- Restores clean demo state between runs.
--   * TRUNCATEs all tables, reloads the same demo data as database.sql.
--   * Volatile dates (contributions, claims, pending policy) are made
--     RELATIVE TO TODAY so the demo always looks current.
--   * adviser_callbacks and fund_switches are AGENT-WRITTEN -> left EMPTY.
-- Run this (not database.sql) to reset between demo runs; assumes the
-- schema from database.sql already exists.
-- =====================================================================

TRUNCATE members, policies, retirement_accounts, funds, holdings,
         contributions, beneficiaries, claims, adviser_callbacks, fund_switches
    RESTART IDENTITY CASCADE;

-- ---- members --------------------------------------------------------
INSERT INTO members (member_id, first_name, last_name, email, phone, date_of_birth, address, city, state, zip, ssn_last4, marital_status, member_since) VALUES
('MBR-100001','James','Carter','james.carter@example.com','+1-415-555-0101','1968-03-14','120 Market St','San Francisco','CA','94105','4821','Divorced','2009-06-01'),
('MBR-100002','Maria','Gonzalez','maria.gonzalez@example.com','+1-312-555-0102','1985-09-22','88 Lakeshore Dr','Chicago','IL','60601','7719','Married','2016-02-15'),
('MBR-100003','David','Chen','david.chen@example.com','+1-206-555-0103','1979-12-05','45 Pine Ave','Seattle','WA','98101','3355','Married','2013-11-20'),
('MBR-100004','Susan','Miller','susan.miller@example.com','+1-617-555-0104','1990-07-30','12 Beacon St','Boston','MA','02108','9042','Single','2020-08-10'),
('MBR-100005','Robert','Johnson','robert.johnson@example.com','+1-303-555-0105','1962-01-19','300 Larimer St','Denver','CO','80202','1187','Married','2007-04-25'),
('MBR-100006','Linda','Williams','linda.williams@example.com','+1-512-555-0106','1974-11-11','700 Congress Ave','Austin','TX','78701','6620','Widowed','2011-09-05'),
('MBR-100007','Michael','Brown','michael.brown@example.com','+1-404-555-0107','1988-05-02','15 Peachtree St','Atlanta','GA','30303','4408','Single','2018-03-12'),
('MBR-100008','Jennifer','Davis','jennifer.davis@example.com','+1-305-555-0108','1983-08-17','950 Ocean Dr','Miami','FL','33139','2231','Married','2015-07-19'),
('MBR-100009','William','Martinez','william.martinez@example.com','+1-602-555-0109','1971-04-28','55 Camelback Rd','Phoenix','AZ','85012','5573','Married','2010-10-30'),
('MBR-100010','Patricia','Wilson','patricia.wilson@example.com','+1-503-555-0110','1995-02-09','21 Burnside St','Portland','OR','97209','8890','Single','2021-05-14');

-- ---- policies (POL-2026-1017 pending start made relative) -----------
INSERT INTO policies (policy_id, member_id, product_type, product_name, status, coverage_amount, premium, premium_frequency, start_date, renewal_date) VALUES
('POL-2026-1001','MBR-100001','Life','20-Year Term Life',           'Active', 500000.00, 45.00, 'Monthly','2015-06-01','2035-06-01'),
('POL-2026-1002','MBR-100001','CriticalIllness','Critical Illness Protect','Active',100000.00, 28.50, 'Monthly','2018-04-10','2028-04-10'),
('POL-2026-1003','MBR-100001','IncomeProtection','Income Shield Plan','Active',   4000.00, 32.00, 'Monthly','2019-01-15','2029-01-15'),
('POL-2026-1004','MBR-100002','Life','Whole Life Secure',           'Active', 250000.00, 68.00, 'Monthly','2016-02-15','2046-02-15'),
('POL-2026-1005','MBR-100002','Investment','Managed Growth Portfolio','Active', 65000.00,200.00, 'Monthly','2017-03-01', NULL),
('POL-2026-1006','MBR-100003','IncomeProtection','Income Shield Plan','Active',   5500.00, 41.00, 'Monthly','2014-06-01','2034-06-01'),
('POL-2026-1007','MBR-100003','Life','20-Year Term Life',           'Active', 400000.00, 52.00, 'Monthly','2014-06-01','2034-06-01'),
('POL-2026-1008','MBR-100004','Life','10-Year Term Life',           'Lapsed', 300000.00, 24.00, 'Monthly','2020-08-10','2030-08-10'),
('POL-2026-1009','MBR-100005','CriticalIllness','Critical Illness Protect','Active',150000.00, 62.00,'Monthly','2010-05-01','2030-05-01'),
('POL-2026-1010','MBR-100005','Life','Whole Life Secure',           'Active', 350000.00, 95.00, 'Monthly','2007-04-25','2047-04-25'),
('POL-2026-1011','MBR-100006','IncomeProtection','Income Shield Plan','Active',   3800.00, 30.00, 'Monthly','2016-01-10','2036-01-10'),
('POL-2026-1012','MBR-100006','Life','20-Year Term Life',           'Active', 450000.00, 58.00, 'Monthly','2011-09-05','2031-09-05'),
('POL-2026-1013','MBR-100007','Life','20-Year Term Life',           'Active', 200000.00, 22.00, 'Monthly','2018-03-12','2038-03-12'),
('POL-2026-1014','MBR-100008','IncomeProtection','Income Shield Plan','Active',   4500.00, 36.00, 'Monthly','2015-07-19','2035-07-19'),
('POL-2026-1015','MBR-100008','Investment','Balanced Investor Plan', 'Active', 42000.00,150.00, 'Monthly','2019-02-01', NULL),
('POL-2026-1016','MBR-100009','Life','Whole Life Secure',           'Active', 300000.00, 80.00, 'Monthly','2010-10-30','2050-10-30'),
('POL-2026-1017','MBR-100010','CriticalIllness','Critical Illness Protect','Pending',75000.00,26.00,'Monthly', CURRENT_DATE - INTERVAL '28 days', CURRENT_DATE + INTERVAL '3650 days');

-- ---- retirement_accounts -------------------------------------------
INSERT INTO retirement_accounts (account_id, member_id, account_type, balance, ytd_contribution, contribution_rate, employer_match_rate, annual_contribution_limit, vested_balance, opened_date) VALUES
('RET-5001','MBR-100001','401(k)',        181685.00,  9200.00, 3.00, 6.00, 23500.00, 181685.00,'2009-06-01'),
('RET-5002','MBR-100001','Roth IRA',       45300.00,  3500.00, 0.00, 0.00,  7000.00,  45300.00,'2016-01-10'),
('RET-5003','MBR-100002','401(k)',         98250.00,  8100.00, 6.00, 6.00, 23500.00,  92000.00,'2016-02-15'),
('RET-5004','MBR-100003','Traditional IRA',127400.00, 6500.00, 0.00, 0.00,  7000.00, 127400.00,'2013-11-20'),
('RET-5005','MBR-100005','401(k)',        512300.00, 15000.00, 8.00, 6.00, 23500.00, 512300.00,'2007-04-25'),
('RET-5006','MBR-100006','401(k)',        203900.00, 10200.00, 5.00, 5.00, 23500.00, 198000.00,'2011-09-05'),
('RET-5007','MBR-100007','Roth IRA',        31800.00, 4200.00, 0.00, 0.00,  7000.00,  31800.00,'2018-03-12'),
('RET-5008','MBR-100008','401(k)',         76400.00,  7300.00, 4.00, 5.00, 23500.00,  70000.00,'2015-07-19');

-- ---- funds (catalog) -----------------------------------------------
INSERT INTO funds (fund_id, fund_name, category, risk_level, ytd_return, one_yr_return, three_yr_return, expense_ratio, nav) VALUES
('FND-001','Aggressive Growth Equity Fund','Equity','High',      14.20, 18.50, 12.10, 0.850, 42.15),
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
INSERT INTO holdings (holding_id, account_id, fund_id, units, value, allocation_pct) VALUES
('HLD-001','RET-5001','FND-001', 1500.0000, 63225.00, 34.80),
('HLD-002','RET-5001','FND-002',  800.0000, 70720.00, 38.92),
('HLD-003','RET-5001','FND-003', 4400.0000, 47740.00, 26.28),
('HLD-004','RET-5002','FND-005', 1364.4578, 45300.00,100.00),
('HLD-005','RET-5003','FND-002',  650.0000, 57460.00, 58.48),
('HLD-006','RET-5003','FND-004', 1593.7500, 40800.00, 41.52),
('HLD-007','RET-5004','FND-008', 1200.0000, 61560.00, 48.32),
('HLD-008','RET-5004','FND-003', 6067.2811, 65830.00, 51.68),
('HLD-009','RET-5005','FND-005', 9500.0000,315400.00, 61.57),
('HLD-010','RET-5005','FND-003',18147.0000,196900.00, 38.43),
('HLD-011','RET-5006','FND-002', 1500.0000,132600.00, 65.03),
('HLD-012','RET-5006','FND-003', 6571.4286, 71300.00, 34.97),
('HLD-013','RET-5007','FND-001',  754.4484, 31800.00,100.00),
('HLD-014','RET-5008','FND-004', 1789.0625, 45800.00, 59.95),
('HLD-015','RET-5008','FND-006',30600.0000, 30600.00, 40.05);

-- ---- contributions (recent dates made relative to today) -----------
INSERT INTO contributions (contribution_id, member_id, account_id, policy_id, amount, contribution_type, frequency, contribution_date) VALUES
('CON-9001','MBR-100001','RET-5001',NULL,  383.33,'Employee','Monthly', CURRENT_DATE - INTERVAL '5 days'),
('CON-9002','MBR-100001','RET-5001',NULL,  766.66,'Employer','Monthly', CURRENT_DATE - INTERVAL '5 days'),
('CON-9003','MBR-100001','RET-5001',NULL,  383.33,'Employee','Monthly', CURRENT_DATE - INTERVAL '35 days'),
('CON-9004','MBR-100001','RET-5002',NULL,  291.66,'Employee','Monthly', CURRENT_DATE - INTERVAL '5 days'),
('CON-9005','MBR-100001',NULL,'POL-2026-1001', 45.00,'Premium','Monthly', CURRENT_DATE - INTERVAL '5 days'),
('CON-9006','MBR-100002','RET-5003',NULL,  675.00,'Employee','Monthly', CURRENT_DATE - INTERVAL '5 days'),
('CON-9007','MBR-100002','RET-5003',NULL,  675.00,'Employer','Monthly', CURRENT_DATE - INTERVAL '5 days'),
('CON-9008','MBR-100003','RET-5004',NULL,  541.66,'Employee','Monthly', CURRENT_DATE - INTERVAL '5 days'),
('CON-9009','MBR-100005','RET-5005',NULL, 1250.00,'Employee','Monthly', CURRENT_DATE - INTERVAL '5 days'),
('CON-9010','MBR-100005','RET-5005',NULL,  937.50,'Employer','Monthly', CURRENT_DATE - INTERVAL '5 days'),
('CON-9011','MBR-100006','RET-5006',NULL,  850.00,'Employee','Monthly', CURRENT_DATE - INTERVAL '5 days'),
('CON-9012','MBR-100007','RET-5007',NULL,  350.00,'Employee','Monthly', CURRENT_DATE - INTERVAL '5 days'),
('CON-9013','MBR-100008','RET-5008',NULL,  608.33,'Employee','Monthly', CURRENT_DATE - INTERVAL '5 days'),
('CON-9014','MBR-100002',NULL,'POL-2026-1005',200.00,'Premium','Monthly', CURRENT_DATE - INTERVAL '5 days'),
('CON-9015','MBR-100008',NULL,'POL-2026-1015',150.00,'Premium','Monthly', CURRENT_DATE - INTERVAL '5 days'),
('CON-9016','MBR-100001','RET-5002',NULL, 2000.00,'Rollover','OneTime', CURRENT_DATE - INTERVAL '180 days');

-- ---- beneficiaries (James still names ex-spouse -> update scenario) -
INSERT INTO beneficiaries (beneficiary_id, policy_id, beneficiary_name, relationship, share_pct, is_primary, date_added) VALUES
('BEN-001','POL-2026-1001','Emily Carter','Spouse',100.00, TRUE, '2015-06-01'),
('BEN-002','POL-2026-1002','Emily Carter','Spouse',100.00, TRUE, '2018-04-10'),
('BEN-003','POL-2026-1004','Carlos Gonzalez','Spouse',100.00, TRUE,'2016-02-15'),
('BEN-004','POL-2026-1007','Grace Chen','Spouse', 60.00, TRUE, '2014-06-01'),
('BEN-005','POL-2026-1007','Ethan Chen','Child', 40.00, FALSE,'2014-06-01'),
('BEN-006','POL-2026-1010','Nancy Johnson','Spouse',100.00, TRUE,'2007-04-25'),
('BEN-007','POL-2026-1012','The Williams Family Trust','Trust',100.00, TRUE,'2011-09-05'),
('BEN-008','POL-2026-1013','Karen Brown','Parent',100.00, TRUE,'2018-03-12'),
('BEN-009','POL-2026-1016','Sofia Martinez','Spouse',50.00, TRUE,'2010-10-30'),
('BEN-010','POL-2026-1016','Diego Martinez','Child',50.00, FALSE,'2010-10-30');

-- ---- claims (submitted/last_update dates made relative to today) ----
INSERT INTO claims (claim_id, policy_id, member_id, claim_type, amount, status, submitted_date, description, last_update) VALUES
('CLM-2026-001','POL-2026-1006','MBR-100003','IncomeProtection', 5500.00,'UnderReview', CURRENT_DATE - INTERVAL '41 days','Signed off work — back injury, monthly benefit claim', CURRENT_TIMESTAMP - INTERVAL '34 days'),
('CLM-2026-002','POL-2026-1009','MBR-100005','CriticalIllness',150000.00,'Approved',    CURRENT_DATE - INTERVAL '88 days','Critical illness diagnosis — cardiac', CURRENT_TIMESTAMP - INTERVAL '70 days'),
('CLM-2026-003','POL-2026-1014','MBR-100008','IncomeProtection', 4500.00,'Paid',        CURRENT_DATE - INTERVAL '140 days','Temporary disability — recovered', CURRENT_TIMESTAMP - INTERVAL '105 days'),
('CLM-2026-004','POL-2026-1011','MBR-100006','IncomeProtection', 3800.00,'Denied',      CURRENT_DATE - INTERVAL '98 days','Claim outside waiting period', CURRENT_TIMESTAMP - INTERVAL '89 days');

-- ---- adviser_callbacks : AGENT-WRITTEN — left EMPTY -----------------
-- ---- fund_switches    : AGENT-WRITTEN — left EMPTY -----------------

-- =====================================================================
-- End of reset_data.sql
-- =====================================================================
