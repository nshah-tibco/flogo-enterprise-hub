-- =============================================
-- Retail Banking Assistant - Reset to clean demo state
-- PostgreSQL 14+  |  Database name: banking
-- =============================================
-- Restores the baseline and UNDOES agent writes between demo runs:
--   * disputes  -> only the single pre-seeded dispute remains (agent-filed disputes removed)
--   * cards     -> statuses restored (a card the agent BLOCKED is set back to ACTIVE)
-- Volatile dates are made relative to CURRENT_DATE so the demo always looks current.
--   Run:  psql -U postgres -d banking -f reset_data.sql
-- =============================================

TRUNCATE disputes, transactions, cards, loans, accounts, branches, customers RESTART IDENTITY CASCADE;

-- Customers
INSERT INTO customers (customer_id, first_name, last_name, phone_number, email) VALUES
('CUST-2026-00101', 'James',   'Miller',   '+1 415-555-0101', 'james.miller@example.com'),
('CUST-2026-00102', 'Olivia',  'Davis',    '+1 415-555-0102', 'olivia.davis@example.com'),
('CUST-2026-00103', 'William', 'Garcia',   '+1 312-555-0103', 'william.garcia@example.com'),
('CUST-2026-00104', 'Sophia',  'Martinez', '+1 212-555-0104', 'sophia.martinez@example.com'),
('CUST-2026-00105', 'Benjamin','Lee',      '+1 206-555-0105', 'benjamin.lee@example.com'),
('CUST-2026-00106', 'Emma',    'Johnson',  '+1 617-555-0106', 'emma.johnson@example.com'),
('CUST-2026-00107', 'Michael', 'Brown',    '+1 305-555-0107', 'michael.brown@example.com');

-- Accounts  (opened_date is a stable fact -> kept fixed)
INSERT INTO accounts (account_id, customer_id, account_number, account_type, balance, currency, status, opened_date) VALUES
('ACC-1001', 'CUST-2026-00101', '****3401', 'CHECKING', 4250.75,  'USD', 'ACTIVE', '2019-03-14'),
('ACC-1002', 'CUST-2026-00101', '****3402', 'SAVINGS',  18500.00, 'USD', 'ACTIVE', '2019-03-14'),
('ACC-1003', 'CUST-2026-00102', '****5521', 'CHECKING', 2780.40,  'USD', 'ACTIVE', '2020-07-22'),
('ACC-1004', 'CUST-2026-00103', '****6612', 'SAVINGS',  9120.00,  'USD', 'ACTIVE', '2018-11-02'),
('ACC-1005', 'CUST-2026-00104', '****7731', 'CHECKING', 1540.20,  'USD', 'ACTIVE', '2021-01-19'),
('ACC-1006', 'CUST-2026-00105', '****8842', 'CHECKING', 6300.00,  'USD', 'ACTIVE', '2017-05-30'),
('ACC-1007', 'CUST-2026-00106', '****9953', 'CHECKING', 3015.55,  'USD', 'ACTIVE', '2022-09-10'),
('ACC-1008', 'CUST-2026-00106', '****9954', 'SAVINGS',  25000.00, 'USD', 'ACTIVE', '2022-09-10'),
('ACC-1009', 'CUST-2026-00107', '****1064', 'CHECKING', 890.10,   'USD', 'ACTIVE', '2023-02-27');

-- Transactions  (txn_date relative to today so history always looks recent)
INSERT INTO transactions (transaction_id, account_id, customer_id, txn_date, description, merchant, amount, txn_type, category, status) VALUES
('TXN-50001', 'ACC-1001', 'CUST-2026-00101', TO_CHAR(CURRENT_DATE - INTERVAL '1 day',  'YYYY-MM-DD'), 'Groceries',              'Whole Foods Market',      84.30,  'DEBIT',  'GROCERIES',    'POSTED'),
('TXN-50002', 'ACC-1001', 'CUST-2026-00101', TO_CHAR(CURRENT_DATE - INTERVAL '2 days', 'YYYY-MM-DD'), 'Payroll deposit',        'Contoso Inc',             3200.00,'CREDIT', 'INCOME',       'POSTED'),
('TXN-50003', 'ACC-1001', 'CUST-2026-00101', TO_CHAR(CURRENT_DATE - INTERVAL '3 days', 'YYYY-MM-DD'), 'Card purchase',          'QUICKPAY*XYZ 872-555',    249.99, 'DEBIT',  'UNCATEGORIZED','POSTED'),
('TXN-50004', 'ACC-1001', 'CUST-2026-00101', TO_CHAR(CURRENT_DATE - INTERVAL '4 days', 'YYYY-MM-DD'), 'Online shopping',        'Amazon.com',              56.20,  'DEBIT',  'SHOPPING',     'POSTED'),
('TXN-50005', 'ACC-1001', 'CUST-2026-00101', TO_CHAR(CURRENT_DATE - INTERVAL '5 days', 'YYYY-MM-DD'), 'Fuel',                   'Shell',                   41.10,  'DEBIT',  'FUEL',         'POSTED'),
('TXN-50006', 'ACC-1003', 'CUST-2026-00102', TO_CHAR(CURRENT_DATE - INTERVAL '1 day',  'YYYY-MM-DD'), 'Coffee',                 'Starbucks',               6.75,   'DEBIT',  'DINING',       'POSTED'),
('TXN-50007', 'ACC-1003', 'CUST-2026-00102', TO_CHAR(CURRENT_DATE - INTERVAL '3 days', 'YYYY-MM-DD'), 'Streaming subscription', 'Netflix',                 15.49,  'DEBIT',  'ENTERTAINMENT','POSTED'),
('TXN-50008', 'ACC-1004', 'CUST-2026-00103', TO_CHAR(CURRENT_DATE - INTERVAL '2 days', 'YYYY-MM-DD'), 'ATM withdrawal',         'Bank ATM #221',           200.00, 'DEBIT',  'CASH',         'POSTED'),
('TXN-50009', 'ACC-1005', 'CUST-2026-00104', TO_CHAR(CURRENT_DATE - INTERVAL '6 days', 'YYYY-MM-DD'), 'Card purchase',          'GLOBAL*DIGITAL 900-555',  129.00, 'DEBIT',  'UNCATEGORIZED','POSTED'),
('TXN-50010', 'ACC-1006', 'CUST-2026-00105', TO_CHAR(CURRENT_DATE - INTERVAL '1 day',  'YYYY-MM-DD'), 'Utilities',              'City Power & Light',      132.44, 'DEBIT',  'UTILITIES',    'POSTED'),
('TXN-50011', 'ACC-1006', 'CUST-2026-00105', TO_CHAR(CURRENT_DATE - INTERVAL '4 days', 'YYYY-MM-DD'), 'Restaurant',             'Olive Garden',            63.28,  'DEBIT',  'DINING',       'POSTED'),
('TXN-50012', 'ACC-1007', 'CUST-2026-00106', TO_CHAR(CURRENT_DATE - INTERVAL '2 days', 'YYYY-MM-DD'), 'Payroll deposit',        'Globex Corp',             2900.00,'CREDIT', 'INCOME',       'POSTED'),
('TXN-50013', 'ACC-1001', 'CUST-2026-00101', TO_CHAR(CURRENT_DATE - INTERVAL '6 days', 'YYYY-MM-DD'), 'Card purchase',          'QUICKPAY*XYZ 872-555',    18.75,  'DEBIT',  'UNCATEGORIZED','POSTED'),
('TXN-50014', 'ACC-1009', 'CUST-2026-00107', TO_CHAR(CURRENT_DATE - INTERVAL '5 days', 'YYYY-MM-DD'), 'Pharmacy',               'CVS Pharmacy',            27.60,  'DEBIT',  'HEALTH',       'POSTED'),
('TXN-50015', 'ACC-1002', 'CUST-2026-00101', TO_CHAR(CURRENT_DATE - INTERVAL '10 days','YYYY-MM-DD'), 'Interest earned',        'Interest',                12.34,  'CREDIT', 'INTEREST',     'POSTED');

-- Cards  (statuses restored -- CARD-9005 BLOCKED and CARD-9007 EXPIRED are baseline facts)
INSERT INTO cards (card_id, customer_id, account_id, card_number_masked, card_type, network, status, expiry, credit_limit) VALUES
('CARD-9001', 'CUST-2026-00101', 'ACC-1001', '**** **** **** 1123', 'DEBIT',  'VISA',       'ACTIVE',  '08/28', NULL),
('CARD-9002', 'CUST-2026-00102', 'ACC-1003', '**** **** **** 4477', 'CREDIT', 'MASTERCARD', 'ACTIVE',  '11/27', 10000.00),
('CARD-9003', 'CUST-2026-00103', 'ACC-1004', '**** **** **** 6612', 'DEBIT',  'VISA',       'ACTIVE',  '02/29', NULL),
('CARD-9004', 'CUST-2026-00104', 'ACC-1005', '**** **** **** 2231', 'CREDIT', 'VISA',       'ACTIVE',  '05/28', 8000.00),
('CARD-9005', 'CUST-2026-00105', 'ACC-1006', '**** **** **** 7788', 'DEBIT',  'MASTERCARD', 'BLOCKED', '09/27', NULL),
('CARD-9006', 'CUST-2026-00106', 'ACC-1007', '**** **** **** 3390', 'DEBIT',  'VISA',       'ACTIVE',  '12/28', NULL),
('CARD-9007', 'CUST-2026-00107', 'ACC-1009', '**** **** **** 1010', 'CREDIT', 'VISA',       'EXPIRED', '03/25', 5000.00);

-- Loans  (next_due_date relative to today)
INSERT INTO loans (loan_id, customer_id, loan_type, principal, outstanding_balance, interest_rate, emi_amount, next_due_date, status) VALUES
('LOAN-3001', 'CUST-2026-00101', 'HOME',     320000.00, 285400.50, 6.25,  2103.45, TO_CHAR(CURRENT_DATE + INTERVAL '11 days', 'YYYY-MM-DD'), 'ACTIVE'),
('LOAN-3002', 'CUST-2026-00102', 'PERSONAL', 15000.00,  8200.00,   11.50, 490.00,  TO_CHAR(CURRENT_DATE + INTERVAL '15 days', 'YYYY-MM-DD'), 'ACTIVE'),
('LOAN-3003', 'CUST-2026-00105', 'AUTO',     42000.00,  31750.00,  7.90,  812.33,  TO_CHAR(CURRENT_DATE + INTERVAL '13 days', 'YYYY-MM-DD'), 'ACTIVE');

-- Disputes  (ONLY the pre-seeded dispute; agent-filed disputes are cleared by the TRUNCATE)
INSERT INTO disputes (dispute_id, customer_id, transaction_id, reason, status, estimated_resolution, last_update) VALUES
('DSP-2026-0001', 'CUST-2026-00104', 'TXN-50009', 'Unrecognized digital subscription charge', 'OPEN',
    TO_CHAR(CURRENT_DATE + INTERVAL '2 days', 'YYYY-MM-DD'),
    TO_CHAR(CURRENT_DATE - INTERVAL '6 days', 'YYYY-MM-DD HH24:MI'));

-- Branches (reference -- stable)
INSERT INTO branches (branch_id, branch_name, address, city, state, zip, phone, hours) VALUES
('BR-001', 'Downtown Financial District', '101 Market St',   'San Francisco', 'CA', '94105', '+1 415-555-1000', 'Mon-Fri 9:00-17:00'),
('BR-002', 'Midtown Center',              '500 5th Ave',     'New York',      'NY', '10110', '+1 212-555-1000', 'Mon-Fri 9:00-18:00'),
('BR-003', 'The Loop',                    '233 S Wacker Dr', 'Chicago',       'IL', '60606', '+1 312-555-1000', 'Mon-Fri 9:00-17:00'),
('BR-004', 'Capitol Hill',               '1420 Broadway',   'Seattle',       'WA', '98122', '+1 206-555-1000', 'Mon-Fri 9:00-17:00'),
('BR-005', 'Back Bay',                    '800 Boylston St', 'Boston',        'MA', '02199', '+1 617-555-1000', 'Mon-Sat 9:00-16:00');
