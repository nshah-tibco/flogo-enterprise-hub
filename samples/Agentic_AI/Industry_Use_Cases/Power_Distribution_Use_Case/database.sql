-- Electric Power Distribution — Residential Self-Service — Database Schema & Demo Data
-- PostgreSQL 14+
-- Database: power_distribution
-- Electric transmission & distribution (T&D) utility — residential self-service.
-- Currency USD (US Dollar). Taxes & Regulatory Fees ~7%. Residents identified by
-- account number (ACCT-XXXXXXXX), the phone on file (+1-XXX-555-01XX), or service address.
-- NOTE: operational tables (outages / tickets / appointments / service requests) use
-- today-relative timestamps so the demo is live-ready the moment this file loads.

-- Drop existing tables (reverse dependency order)
DROP TABLE IF EXISTS service_requests CASCADE;
DROP TABLE IF EXISTS service_appointments CASCADE;
DROP TABLE IF EXISTS outage_tickets CASCADE;
DROP TABLE IF EXISTS outages CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS usage_records CASCADE;
DROP TABLE IF EXISTS bill_line_items CASCADE;
DROP TABLE IF EXISTS invoices CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS rate_plans CASCADE;

-- 1. Rate Plans — residential delivery rate catalog
CREATE TABLE rate_plans (
    id                    SERIAL PRIMARY KEY,
    plan_id               VARCHAR(20) NOT NULL UNIQUE,        -- RP-STD, RP-TOU, RP-EV, RP-SOLAR
    plan_name             VARCHAR(80) NOT NULL,
    description           VARCHAR(240),
    base_service_charge   NUMERIC(10,2) NOT NULL DEFAULT 0,   -- fixed monthly $ / meter
    delivery_per_kwh      NUMERIC(8,4) NOT NULL DEFAULT 0,    -- flat $/kWh (non-TOU plans)
    tou_enabled           BOOLEAN NOT NULL DEFAULT FALSE,
    on_peak_per_kwh       NUMERIC(8,4) NOT NULL DEFAULT 0,    -- $/kWh on-peak (TOU plans)
    off_peak_per_kwh      NUMERIC(8,4) NOT NULL DEFAULT 0     -- $/kWh off-peak / overnight (TOU plans)
);

-- 2. Customers — account master (one residential account = one service point / meter)
CREATE TABLE customers (
    id                SERIAL PRIMARY KEY,
    account_id        VARCHAR(20) NOT NULL UNIQUE,            -- ACCT-XXXXXXXX
    phone             VARCHAR(25) NOT NULL,                   -- +1-XXX-555-01XX (on file)
    first_name        VARCHAR(50) NOT NULL,
    last_name         VARCHAR(50) NOT NULL,
    email             VARCHAR(120),
    service_address   VARCHAR(160) NOT NULL,
    city              VARCHAR(60) NOT NULL,
    state             VARCHAR(4)  NOT NULL DEFAULT 'TX',
    zip               VARCHAR(10) NOT NULL,
    segment           VARCHAR(40) NOT NULL DEFAULT 'Residential',
                          -- Residential, Residential-Medical-Baseline,
                          -- Residential-Budget-Billing, Residential-Solar-NetMeter, Residential-EV
    account_status    VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',  -- ACTIVE, PAST_DUE, FINAL
    meter_number      VARCHAR(20) NOT NULL,                   -- MTR-XXXXXX
    meter_type        VARCHAR(12) NOT NULL DEFAULT 'SMART',   -- SMART, ANALOG
    connection_status VARCHAR(15) NOT NULL DEFAULT 'CONNECTED',-- CONNECTED, DISCONNECTED, PENDING
    rate_plan_id      VARCHAR(20) NOT NULL REFERENCES rate_plans(plan_id),
    feeder_id         VARCHAR(20) NOT NULL,                   -- FDR-XXX (distribution circuit)
    enrolled_date     DATE NOT NULL,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_segment CHECK (segment IN ('Residential','Residential-Medical-Baseline','Residential-Budget-Billing','Residential-Solar-NetMeter','Residential-EV')),
    CONSTRAINT chk_acct_status CHECK (account_status IN ('ACTIVE','PAST_DUE','FINAL')),
    CONSTRAINT chk_meter_type CHECK (meter_type IN ('SMART','ANALOG')),
    CONSTRAINT chk_conn_status CHECK (connection_status IN ('CONNECTED','DISCONNECTED','PENDING'))
);

-- 3. Invoices — monthly electric bill header (delivery utility)
CREATE TABLE invoices (
    id              SERIAL PRIMARY KEY,
    invoice_id      VARCHAR(25) NOT NULL UNIQUE,        -- INV-2026-06-XXXX
    account_id      VARCHAR(20) NOT NULL REFERENCES customers(account_id),
    billing_month   VARCHAR(20) NOT NULL,               -- e.g. June 2026
    period_start    DATE NOT NULL,
    period_end      DATE NOT NULL,
    subtotal        NUMERIC(12,2) NOT NULL DEFAULT 0,
    taxes_fees      NUMERIC(12,2) NOT NULL DEFAULT 0,
    total_amount    NUMERIC(12,2) NOT NULL DEFAULT 0,
    currency        VARCHAR(3) NOT NULL DEFAULT 'USD',
    due_date        DATE NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'Unpaid',   -- Unpaid, Paid, Overdue
    CONSTRAINT chk_invoice_status CHECK (status IN ('Unpaid','Paid','Overdue'))
);

-- 4. Bill Line Items — itemized charges that make up an invoice
CREATE TABLE bill_line_items (
    id              SERIAL PRIMARY KEY,
    invoice_id      VARCHAR(25) NOT NULL REFERENCES invoices(invoice_id),
    account_id      VARCHAR(20) NOT NULL,
    category        VARCHAR(30) NOT NULL,
                        -- BASE_CHARGE, DELIVERY, TOU_ON_PEAK, TOU_OFF_PEAK, RIDER,
                        -- SOLAR_CREDIT, MEDICAL_BASELINE_CREDIT, BUDGET_BILLING,
                        -- ESTIMATED_READ, TAXES_FEES
    description     VARCHAR(200) NOT NULL,
    amount          NUMERIC(12,2) NOT NULL
);

-- 5. Usage Records — metered kWh usage for a billing period (drives bill explanations)
CREATE TABLE usage_records (
    id               SERIAL PRIMARY KEY,
    account_id       VARCHAR(20) NOT NULL REFERENCES customers(account_id),
    billing_period   VARCHAR(20) NOT NULL,          -- e.g. June 2026
    kwh_used         NUMERIC(10,2) NOT NULL DEFAULT 0,
    peak_demand_kw   NUMERIC(8,2)  NOT NULL DEFAULT 0,
    on_peak_kwh      NUMERIC(10,2) NOT NULL DEFAULT 0,
    off_peak_kwh     NUMERIC(10,2) NOT NULL DEFAULT 0,
    solar_export_kwh NUMERIC(10,2) NOT NULL DEFAULT 0,
    avg_daily_kwh    NUMERIC(8,2)  NOT NULL DEFAULT 0,
    days_in_period   INTEGER NOT NULL DEFAULT 30,
    prior_year_kwh   NUMERIC(10,2) NOT NULL DEFAULT 0,
    read_type        VARCHAR(12) NOT NULL DEFAULT 'ACTUAL'   -- ACTUAL, ESTIMATED
);

-- 6. Payments — payment history
CREATE TABLE payments (
    id                  SERIAL PRIMARY KEY,
    account_id          VARCHAR(20) NOT NULL REFERENCES customers(account_id),
    payment_date        DATE NOT NULL,
    amount              NUMERIC(12,2) NOT NULL,
    currency            VARCHAR(3) NOT NULL DEFAULT 'USD',
    method              VARCHAR(30) NOT NULL,     -- Auto-Pay, Credit Card, Debit Card, Bank Draft, Check, Online
    status              VARCHAR(20) NOT NULL DEFAULT 'Success',
    reference_number    VARCHAR(30) NOT NULL,
    invoice_id          VARCHAR(25),
    CONSTRAINT chk_payment_status CHECK (status IN ('Success','Failed','Pending'))
);

-- 7. Outages — AREA-level active outages (read-only; "is there an outage near me?")
CREATE TABLE outages (
    id                    SERIAL PRIMARY KEY,
    outage_id             VARCHAR(25) NOT NULL UNIQUE,   -- OUT-2026-XXXX
    feeder_id             VARCHAR(20) NOT NULL,
    zip                   VARCHAR(10) NOT NULL,
    area                  VARCHAR(80) NOT NULL,
    cause                 VARCHAR(20) NOT NULL,          -- STORM, EQUIPMENT, VEGETATION, PLANNED
    status                VARCHAR(20) NOT NULL,          -- INVESTIGATING, CREW_ASSIGNED, RESTORING, RESTORED
    start_time            TIMESTAMP NOT NULL,
    estimated_restoration TIMESTAMP,
    customers_affected    INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT chk_outage_cause CHECK (cause IN ('STORM','EQUIPMENT','VEGETATION','PLANNED')),
    CONSTRAINT chk_outage_status CHECK (status IN ('INVESTIGATING','CREW_ASSIGNED','RESTORING','RESTORED'))
);

-- 8. Outage Tickets — customer-reported outages + crew dispatch (WRITTEN by outage_dispatch_agent)
CREATE TABLE outage_tickets (
    id                SERIAL PRIMARY KEY,
    ticket_id         VARCHAR(25) NOT NULL UNIQUE,       -- OTKT-2026-XXXX
    account_id        VARCHAR(20) NOT NULL,
    premise_address   VARCHAR(160),
    description       VARCHAR(300) NOT NULL,
    status            VARCHAR(20) NOT NULL DEFAULT 'OPEN',   -- OPEN, CREW_DISPATCHED, RESTORED
    crew_id           VARCHAR(20),
    reported_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    eta               TIMESTAMP,
    CONSTRAINT chk_ticket_status CHECK (status IN ('OPEN','CREW_DISPATCHED','RESTORED'))
);

-- 9. Service Appointments — scheduled field appointments (WRITTEN by service_appointment_agent)
CREATE TABLE service_appointments (
    id                SERIAL PRIMARY KEY,
    appointment_id    VARCHAR(25) NOT NULL UNIQUE,       -- APPT-2026-XXXX
    account_id        VARCHAR(20) NOT NULL,
    appt_type         VARCHAR(30) NOT NULL,              -- METER_INSPECTION, NEW_SERVICE, TREE_TRIM, METER_UPGRADE, SITE_SURVEY
    scheduled_date    VARCHAR(40) NOT NULL,              -- text date (avoids param date-cast issues)
    time_window       VARCHAR(40) NOT NULL,
    status            VARCHAR(20) NOT NULL DEFAULT 'SCHEDULED', -- SCHEDULED, COMPLETED, CANCELLED
    notes             VARCHAR(300),
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 10. Service Requests — reconnect / disconnect / transfer requests (WRITTEN by service_change_agent)
CREATE TABLE service_requests (
    id                SERIAL PRIMARY KEY,
    request_id        VARCHAR(25) NOT NULL UNIQUE,       -- SRV-2026-XXXX
    account_id        VARCHAR(20) NOT NULL,
    request_type      VARCHAR(20) NOT NULL,              -- RECONNECT, DISCONNECT, TRANSFER
    effective_date    VARCHAR(40),                       -- text date
    status            VARCHAR(20) NOT NULL DEFAULT 'SUBMITTED', -- SUBMITTED, IN_PROGRESS, COMPLETED
    reason            VARCHAR(300),
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_request_type CHECK (request_type IN ('RECONNECT','DISCONNECT','TRANSFER'))
);

-- Indexes
CREATE INDEX idx_customers_account ON customers(account_id);
CREATE INDEX idx_customers_phone ON customers(phone);
CREATE INDEX idx_customers_zip ON customers(zip);
CREATE INDEX idx_invoices_account ON invoices(account_id);
CREATE INDEX idx_invoices_invoice ON invoices(invoice_id);
CREATE INDEX idx_line_items_invoice ON bill_line_items(invoice_id);
CREATE INDEX idx_usage_account ON usage_records(account_id);
CREATE INDEX idx_payments_account ON payments(account_id);
CREATE INDEX idx_outages_zip ON outages(zip);
CREATE INDEX idx_outage_tickets_account ON outage_tickets(account_id);
CREATE INDEX idx_appointments_account ON service_appointments(account_id);
CREATE INDEX idx_requests_account ON service_requests(account_id);

-- ============================================================
-- DEMO DATA — residential electric-utility customers (currency USD)
-- ============================================================

-- Rate Plans
INSERT INTO rate_plans (plan_id, plan_name, description, base_service_charge, delivery_per_kwh, tou_enabled, on_peak_per_kwh, off_peak_per_kwh) VALUES
('RP-STD',   'Residential Standard',          'Flat residential delivery rate. Best for typical households with steady usage.', 9.50,  0.0450, FALSE, 0.0000, 0.0000),
('RP-TOU',   'Residential Time-of-Use',       'Lower off-peak delivery, higher on-peak (2pm-8pm weekdays). Best if you can shift usage to evenings/weekends.', 12.00, 0.0000, TRUE,  0.0950, 0.0280),
('RP-EV',    'EV Owner Time-of-Use',          'Super off-peak overnight rate (12am-6am) for EV charging; higher on-peak. Best for electric-vehicle owners.', 12.00, 0.0000, TRUE,  0.1100, 0.0220),
('RP-SOLAR', 'Residential Solar Net Metering','Standard delivery with net-metering credit for solar energy exported to the grid.', 10.00, 0.0450, FALSE, 0.0000, 0.0000);

-- Customers (18) — 555-01xx phone numbers are reserved for fictional use.
INSERT INTO customers (account_id, phone, first_name, last_name, email, service_address, city, state, zip, segment, account_status, meter_number, meter_type, connection_status, rate_plan_id, feeder_id, enrolled_date) VALUES
('ACCT-50010001', '+1-469-555-0142', 'Laura',   'Bennett',  'laura.bennett@email.com',   '412 Cedar Springs Rd',   'Cedar Springs', 'TX', '75001', 'Residential',                 'ACTIVE', 'MTR-100001', 'SMART',  'CONNECTED',    'RP-STD',   'FDR-101', '2018-05-14'),
('ACCT-50010002', '+1-214-555-0178', 'Marcus',  'Reed',     'marcus.reed@email.com',     '88 Willow Bend Dr',      'Maple Grove',   'TX', '75002', 'Residential-EV',              'ACTIVE', 'MTR-100002', 'SMART',  'CONNECTED',    'RP-EV',    'FDR-102', '2020-09-03'),
('ACCT-50010003', '+1-972-555-0163', 'Priya',   'Nair',     'priya.nair@email.com',      '1507 Sunflower Ln',      'Riverton',      'TX', '75003', 'Residential-Solar-NetMeter',  'ACTIVE', 'MTR-100003', 'SMART',  'CONNECTED',    'RP-SOLAR', 'FDR-103', '2021-04-19'),
('ACCT-50010004', '+1-682-555-0119', 'Diane',   'Foster',   'diane.foster@email.com',    '23 Prairie View Ct',     'Oakdale',       'TX', '75004', 'Residential-Medical-Baseline','ACTIVE', 'MTR-100004', 'SMART',  'CONNECTED',    'RP-STD',   'FDR-104', '2016-11-27'),
('ACCT-50010005', '+1-940-555-0187', 'Tom',     'Alvarez',  'tom.alvarez@email.com',     '640 Highland Park Ave',  'Highland',      'TX', '75005', 'Residential',                 'ACTIVE', 'MTR-100005', 'SMART',  'CONNECTED',    'RP-TOU',   'FDR-105', '2019-02-08'),
('ACCT-50010006', '+1-817-555-0134', 'Grace',   'Kim',      'grace.kim@email.com',       '19 Birchwood Cir',       'Fair Meadows',  'TX', '75006', 'Residential',                 'ACTIVE', 'MTR-100006', 'ANALOG', 'CONNECTED',    'RP-STD',   'FDR-106', '2015-07-15'),
('ACCT-50010007', '+1-469-555-0155', 'Henry',   'Wu',       'henry.wu@email.com',        '305 Aspen Trail',        'Cedar Springs', 'TX', '75007', 'Residential',                 'ACTIVE', 'MTR-100007', 'SMART',  'DISCONNECTED', 'RP-STD',   'FDR-107', '2022-01-25'),
('ACCT-50010008', '+1-214-555-0198', 'Olivia',  'Brooks',   'olivia.brooks@email.com',   '77 Magnolia St',         'Maple Grove',   'TX', '75008', 'Residential',                 'ACTIVE', 'MTR-100008', 'SMART',  'CONNECTED',    'RP-STD',   'FDR-108', '2020-06-30'),
('ACCT-50010009', '+1-972-555-0172', 'Samuel',  'Ortiz',    'samuel.ortiz@email.com',    '1120 Ranch Rd',          'Riverton',      'TX', '75009', 'Residential',                 'ACTIVE', 'MTR-100009', 'SMART',  'CONNECTED',    'RP-STD',   'FDR-109', '2019-10-14'),
('ACCT-50010010', '+1-682-555-0110', 'Rebecca', 'Lynn',     'rebecca.lynn@email.com',    '58 Elm Hollow Way',      'Oakdale',       'TX', '75010', 'Residential',                 'ACTIVE', 'MTR-100010', 'SMART',  'CONNECTED',    'RP-STD',   'FDR-110', '2018-03-02'),
('ACCT-50010011', '+1-940-555-0145', 'David',   'Chen',     'david.chen@email.com',      '902 Lakeside Blvd',      'Lakeside',      'TX', '75011', 'Residential',                 'ACTIVE', 'MTR-100011', 'SMART',  'CONNECTED',    'RP-STD',   'FDR-111', '2021-08-19'),
('ACCT-50010012', '+1-817-555-0166', 'Angela',  'Price',    'angela.price@email.com',    '46 Prairie View Ct',     'Oakdale',       'TX', '75004', 'Residential',                 'ACTIVE', 'MTR-100012', 'SMART',  'CONNECTED',    'RP-STD',   'FDR-104', '2017-12-11'),
('ACCT-50010013', '+1-469-555-0129', 'Nathan',  'Cole',     'nathan.cole@email.com',     '211 Meadowbrook Dr',     'Fair Meadows',  'TX', '75013', 'Residential-Budget-Billing',  'ACTIVE', 'MTR-100013', 'SMART',  'CONNECTED',    'RP-STD',   'FDR-113', '2020-03-08'),
('ACCT-50010014', '+1-214-555-0181', 'Sophia',  'Turner',   'sophia.turner@email.com',   '134 Juniper Ct',         'Highland',      'TX', '75014', 'Residential',                 'ACTIVE', 'MTR-100014', 'SMART',  'CONNECTED',    'RP-STD',   'FDR-114', '2019-01-27'),
('ACCT-50010015', '+1-972-555-0193', 'Ethan',   'Mills',    'ethan.mills@email.com',     '870 Foxglove Ave',       'Lakeside',      'TX', '75015', 'Residential',                 'ACTIVE', 'MTR-100015', 'SMART',  'CONNECTED',    'RP-STD',   'FDR-115', '2016-04-11'),
('ACCT-50010016', '+1-682-555-0157', 'Maria',   'Gonzalez', 'maria.gonzalez@email.com',  '52 Sycamore Ln',         'Riverton',      'TX', '75016', 'Residential',                 'ACTIVE', 'MTR-100016', 'SMART',  'PENDING',      'RP-STD',   'FDR-116', '2023-06-05'),
('ACCT-50010017', '+1-817-555-0102', 'William', 'Scott',    'william.scott@email.com',   '15 Copperfield Rd',      'Highland',      'TX', '75017', 'Residential',                 'ACTIVE', 'MTR-100017', 'SMART',  'CONNECTED',    'RP-STD',   'FDR-117', '2021-05-10'),
('ACCT-50010018', '+1-940-555-0113', 'Chloe',   'Adams',    'chloe.adams@email.com',     '318 Brookstone Dr',      'Maple Grove',   'TX', '75018', 'Residential-EV',              'ACTIVE', 'MTR-100018', 'SMART',  'CONNECTED',    'RP-EV',    'FDR-118', '2020-08-14');

-- Invoices (June 2026; taxes & regulatory fees ~7% of subtotal; total = subtotal + taxes_fees). Due dates relative to today.
INSERT INTO invoices (invoice_id, account_id, billing_month, period_start, period_end, subtotal, taxes_fees, total_amount, currency, due_date, status) VALUES
('INV-2026-06-0001', 'ACCT-50010001', 'June 2026', '2026-06-01', '2026-06-30', 117.00,  8.19, 125.19, 'USD', CURRENT_DATE + INTERVAL '10 days', 'Unpaid'),
('INV-2026-06-0002', 'ACCT-50010002', 'June 2026', '2026-06-01', '2026-06-30',  77.60,  5.43,  83.03, 'USD', CURRENT_DATE + INTERVAL '10 days', 'Unpaid'),
('INV-2026-06-0003', 'ACCT-50010003', 'June 2026', '2026-06-01', '2026-06-30',  34.60,  2.42,  37.02, 'USD', CURRENT_DATE + INTERVAL '10 days', 'Unpaid'),
('INV-2026-06-0004', 'ACCT-50010004', 'June 2026', '2026-06-01', '2026-06-30',  71.25,  4.99,  76.24, 'USD', CURRENT_DATE + INTERVAL '10 days', 'Unpaid'),
('INV-2026-06-0005', 'ACCT-50010005', 'June 2026', '2026-06-01', '2026-06-30', 134.45,  9.41, 143.86, 'USD', CURRENT_DATE + INTERVAL '10 days', 'Unpaid'),
('INV-2026-06-0006', 'ACCT-50010006', 'June 2026', '2026-06-01', '2026-06-30', 106.00,  7.42, 113.42, 'USD', CURRENT_DATE + INTERVAL '10 days', 'Unpaid'),
('INV-2026-06-0007', 'ACCT-50010007', 'June 2026', '2026-06-01', '2026-06-30',  16.25,  1.14,  17.39, 'USD', CURRENT_DATE - INTERVAL '5 days',  'Paid'),
('INV-2026-06-0008', 'ACCT-50010008', 'June 2026', '2026-06-01', '2026-06-30',  73.00,  5.11,  78.11, 'USD', CURRENT_DATE + INTERVAL '10 days', 'Unpaid'),
('INV-2026-06-0009', 'ACCT-50010009', 'June 2026', '2026-06-01', '2026-06-30',  80.75,  5.65,  86.40, 'USD', CURRENT_DATE + INTERVAL '10 days', 'Unpaid'),
('INV-2026-06-0010', 'ACCT-50010010', 'June 2026', '2026-06-01', '2026-06-30',  65.60,  4.59,  70.19, 'USD', CURRENT_DATE + INTERVAL '10 days', 'Unpaid'),
('INV-2026-06-0011', 'ACCT-50010011', 'June 2026', '2026-06-01', '2026-06-30',  76.60,  5.36,  81.96, 'USD', CURRENT_DATE + INTERVAL '10 days', 'Unpaid'),
('INV-2026-06-0012', 'ACCT-50010012', 'June 2026', '2026-06-01', '2026-06-30',  84.40,  5.91,  90.31, 'USD', CURRENT_DATE + INTERVAL '10 days', 'Unpaid'),
('INV-2026-06-0013', 'ACCT-50010013', 'June 2026', '2026-06-01', '2026-06-30',  87.00,  6.09,  93.09, 'USD', CURRENT_DATE + INTERVAL '10 days', 'Unpaid'),
('INV-2026-06-0014', 'ACCT-50010014', 'June 2026', '2026-06-01', '2026-06-30',  69.75,  4.88,  74.63, 'USD', CURRENT_DATE + INTERVAL '10 days', 'Unpaid'),
('INV-2026-06-0015', 'ACCT-50010015', 'June 2026', '2026-06-01', '2026-06-30',  79.80,  5.59,  85.39, 'USD', CURRENT_DATE + INTERVAL '10 days', 'Unpaid'),
('INV-2026-06-0016', 'ACCT-50010016', 'June 2026', '2026-06-01', '2026-06-30',  18.50,  1.30,  19.80, 'USD', CURRENT_DATE + INTERVAL '10 days', 'Unpaid'),
('INV-2026-06-0017', 'ACCT-50010017', 'June 2026', '2026-06-01', '2026-06-30',  60.55,  4.24,  64.79, 'USD', CURRENT_DATE + INTERVAL '10 days', 'Unpaid'),
('INV-2026-06-0018', 'ACCT-50010018', 'June 2026', '2026-06-01', '2026-06-30',  67.90,  4.75,  72.65, 'USD', CURRENT_DATE + INTERVAL '10 days', 'Unpaid');

-- Bill Line Items (each invoice's subtotal = sum of non-TAX rows; TAXES_FEES row = taxes_fees)
INSERT INTO bill_line_items (invoice_id, account_id, category, description, amount) VALUES
-- 0001 Laura — summer AC spike (valid high bill)
('INV-2026-06-0001', 'ACCT-50010001', 'BASE_CHARGE', 'Basic Service Charge', 9.50),
('INV-2026-06-0001', 'ACCT-50010001', 'DELIVERY',    'Energy Delivery Charge (1,850 kWh @ $0.045)', 83.25),
('INV-2026-06-0001', 'ACCT-50010001', 'RIDER',       'Grid Access & Transmission Cost Recovery', 24.25),
('INV-2026-06-0001', 'ACCT-50010001', 'TAXES_FEES',  'Taxes & Regulatory Fees', 8.19),
-- 0002 Marcus — EV overnight charging (high usage but cheap off-peak)
('INV-2026-06-0002', 'ACCT-50010002', 'BASE_CHARGE',  'Basic Service Charge', 12.00),
('INV-2026-06-0002', 'ACCT-50010002', 'TOU_ON_PEAK',  'On-Peak Delivery (220 kWh @ $0.110)', 24.20),
('INV-2026-06-0002', 'ACCT-50010002', 'TOU_OFF_PEAK', 'Overnight/Off-Peak Delivery (1,200 kWh @ $0.022)', 26.40),
('INV-2026-06-0002', 'ACCT-50010002', 'RIDER',        'Grid Access & Transmission Cost Recovery', 15.00),
('INV-2026-06-0002', 'ACCT-50010002', 'TAXES_FEES',   'Taxes & Regulatory Fees', 5.43),
-- 0003 Priya — solar net metering (export credit)
('INV-2026-06-0003', 'ACCT-50010003', 'BASE_CHARGE',  'Basic Service Charge', 10.00),
('INV-2026-06-0003', 'ACCT-50010003', 'DELIVERY',     'Energy Delivery Charge (900 kWh @ $0.045)', 40.50),
('INV-2026-06-0003', 'ACCT-50010003', 'RIDER',        'Grid Access & Transmission Cost Recovery', 12.00),
('INV-2026-06-0003', 'ACCT-50010003', 'SOLAR_CREDIT', 'Net Metering Export Credit (620 kWh exported)', -27.90),
('INV-2026-06-0003', 'ACCT-50010003', 'TAXES_FEES',   'Taxes & Regulatory Fees', 2.42),
-- 0004 Diane — medical baseline credit
('INV-2026-06-0004', 'ACCT-50010004', 'BASE_CHARGE',            'Basic Service Charge', 9.50),
('INV-2026-06-0004', 'ACCT-50010004', 'DELIVERY',               'Energy Delivery Charge (1,350 kWh @ $0.045)', 60.75),
('INV-2026-06-0004', 'ACCT-50010004', 'RIDER',                  'Grid Access & Transmission Cost Recovery', 16.00),
('INV-2026-06-0004', 'ACCT-50010004', 'MEDICAL_BASELINE_CREDIT','Medical Baseline Program Credit', -15.00),
('INV-2026-06-0004', 'ACCT-50010004', 'TAXES_FEES',             'Taxes & Regulatory Fees', 4.99),
-- 0005 Tom — TOU on-peak heavy (valid high bill)
('INV-2026-06-0005', 'ACCT-50010005', 'BASE_CHARGE',  'Basic Service Charge', 12.00),
('INV-2026-06-0005', 'ACCT-50010005', 'TOU_ON_PEAK',  'On-Peak Delivery (950 kWh @ $0.095)', 90.25),
('INV-2026-06-0005', 'ACCT-50010005', 'TOU_OFF_PEAK', 'Off-Peak Delivery (650 kWh @ $0.028)', 18.20),
('INV-2026-06-0005', 'ACCT-50010005', 'RIDER',        'Grid Access & Transmission Cost Recovery', 14.00),
('INV-2026-06-0005', 'ACCT-50010005', 'TAXES_FEES',   'Taxes & Regulatory Fees', 9.41),
-- 0006 Grace — ESTIMATED read (analog meter not read this cycle)
('INV-2026-06-0006', 'ACCT-50010006', 'BASE_CHARGE',   'Basic Service Charge', 9.50),
('INV-2026-06-0006', 'ACCT-50010006', 'ESTIMATED_READ','Energy Delivery Charge (1,700 kWh — ESTIMATED read)', 76.50),
('INV-2026-06-0006', 'ACCT-50010006', 'RIDER',         'Grid Access & Transmission Cost Recovery', 20.00),
('INV-2026-06-0006', 'ACCT-50010006', 'TAXES_FEES',    'Taxes & Regulatory Fees', 7.42),
-- 0007 Henry — disconnected most of month (low), paid
('INV-2026-06-0007', 'ACCT-50010007', 'BASE_CHARGE', 'Basic Service Charge', 9.50),
('INV-2026-06-0007', 'ACCT-50010007', 'DELIVERY',    'Energy Delivery Charge (150 kWh @ $0.045)', 6.75),
('INV-2026-06-0007', 'ACCT-50010007', 'TAXES_FEES',  'Taxes & Regulatory Fees', 1.14),
-- 0008 Olivia
('INV-2026-06-0008', 'ACCT-50010008', 'BASE_CHARGE', 'Basic Service Charge', 9.50),
('INV-2026-06-0008', 'ACCT-50010008', 'DELIVERY',    'Energy Delivery Charge (1,100 kWh @ $0.045)', 49.50),
('INV-2026-06-0008', 'ACCT-50010008', 'RIDER',       'Grid Access & Transmission Cost Recovery', 14.00),
('INV-2026-06-0008', 'ACCT-50010008', 'TAXES_FEES',  'Taxes & Regulatory Fees', 5.11),
-- 0009 Samuel
('INV-2026-06-0009', 'ACCT-50010009', 'BASE_CHARGE', 'Basic Service Charge', 9.50),
('INV-2026-06-0009', 'ACCT-50010009', 'DELIVERY',    'Energy Delivery Charge (1,250 kWh @ $0.045)', 56.25),
('INV-2026-06-0009', 'ACCT-50010009', 'RIDER',       'Grid Access & Transmission Cost Recovery', 15.00),
('INV-2026-06-0009', 'ACCT-50010009', 'TAXES_FEES',  'Taxes & Regulatory Fees', 5.65),
-- 0010 Rebecca
('INV-2026-06-0010', 'ACCT-50010010', 'BASE_CHARGE', 'Basic Service Charge', 9.50),
('INV-2026-06-0010', 'ACCT-50010010', 'DELIVERY',    'Energy Delivery Charge (980 kWh @ $0.045)', 44.10),
('INV-2026-06-0010', 'ACCT-50010010', 'RIDER',       'Grid Access & Transmission Cost Recovery', 12.00),
('INV-2026-06-0010', 'ACCT-50010010', 'TAXES_FEES',  'Taxes & Regulatory Fees', 4.59),
-- 0011 David
('INV-2026-06-0011', 'ACCT-50010011', 'BASE_CHARGE', 'Basic Service Charge', 9.50),
('INV-2026-06-0011', 'ACCT-50010011', 'DELIVERY',    'Energy Delivery Charge (1,180 kWh @ $0.045)', 53.10),
('INV-2026-06-0011', 'ACCT-50010011', 'RIDER',       'Grid Access & Transmission Cost Recovery', 14.00),
('INV-2026-06-0011', 'ACCT-50010011', 'TAXES_FEES',  'Taxes & Regulatory Fees', 5.36),
-- 0012 Angela
('INV-2026-06-0012', 'ACCT-50010012', 'BASE_CHARGE', 'Basic Service Charge', 9.50),
('INV-2026-06-0012', 'ACCT-50010012', 'DELIVERY',    'Energy Delivery Charge (1,320 kWh @ $0.045)', 59.40),
('INV-2026-06-0012', 'ACCT-50010012', 'RIDER',       'Grid Access & Transmission Cost Recovery', 15.50),
('INV-2026-06-0012', 'ACCT-50010012', 'TAXES_FEES',  'Taxes & Regulatory Fees', 5.91),
-- 0013 Nathan — budget billing (levelized)
('INV-2026-06-0013', 'ACCT-50010013', 'BASE_CHARGE',    'Basic Service Charge', 9.50),
('INV-2026-06-0013', 'ACCT-50010013', 'DELIVERY',       'Energy Delivery Charge (1,600 kWh @ $0.045)', 72.00),
('INV-2026-06-0013', 'ACCT-50010013', 'RIDER',          'Grid Access & Transmission Cost Recovery', 18.00),
('INV-2026-06-0013', 'ACCT-50010013', 'BUDGET_BILLING', 'Budget Billing Levelization Adjustment', -12.50),
('INV-2026-06-0013', 'ACCT-50010013', 'TAXES_FEES',     'Taxes & Regulatory Fees', 6.09),
-- 0014 Sophia
('INV-2026-06-0014', 'ACCT-50010014', 'BASE_CHARGE', 'Basic Service Charge', 9.50),
('INV-2026-06-0014', 'ACCT-50010014', 'DELIVERY',    'Energy Delivery Charge (1,050 kWh @ $0.045)', 47.25),
('INV-2026-06-0014', 'ACCT-50010014', 'RIDER',       'Grid Access & Transmission Cost Recovery', 13.00),
('INV-2026-06-0014', 'ACCT-50010014', 'TAXES_FEES',  'Taxes & Regulatory Fees', 4.88),
-- 0015 Ethan
('INV-2026-06-0015', 'ACCT-50010015', 'BASE_CHARGE', 'Basic Service Charge', 9.50),
('INV-2026-06-0015', 'ACCT-50010015', 'DELIVERY',    'Energy Delivery Charge (1,240 kWh @ $0.045)', 55.80),
('INV-2026-06-0015', 'ACCT-50010015', 'RIDER',       'Grid Access & Transmission Cost Recovery', 14.50),
('INV-2026-06-0015', 'ACCT-50010015', 'TAXES_FEES',  'Taxes & Regulatory Fees', 5.59),
-- 0016 Maria — pending reconnect (low)
('INV-2026-06-0016', 'ACCT-50010016', 'BASE_CHARGE', 'Basic Service Charge', 9.50),
('INV-2026-06-0016', 'ACCT-50010016', 'DELIVERY',    'Energy Delivery Charge (200 kWh @ $0.045)', 9.00),
('INV-2026-06-0016', 'ACCT-50010016', 'TAXES_FEES',  'Taxes & Regulatory Fees', 1.30),
-- 0017 William
('INV-2026-06-0017', 'ACCT-50010017', 'BASE_CHARGE', 'Basic Service Charge', 9.50),
('INV-2026-06-0017', 'ACCT-50010017', 'DELIVERY',    'Energy Delivery Charge (890 kWh @ $0.045)', 40.05),
('INV-2026-06-0017', 'ACCT-50010017', 'RIDER',       'Grid Access & Transmission Cost Recovery', 11.00),
('INV-2026-06-0017', 'ACCT-50010017', 'TAXES_FEES',  'Taxes & Regulatory Fees', 4.24),
-- 0018 Chloe — EV
('INV-2026-06-0018', 'ACCT-50010018', 'BASE_CHARGE',  'Basic Service Charge', 12.00),
('INV-2026-06-0018', 'ACCT-50010018', 'TOU_ON_PEAK',  'On-Peak Delivery (180 kWh @ $0.110)', 19.80),
('INV-2026-06-0018', 'ACCT-50010018', 'TOU_OFF_PEAK', 'Overnight/Off-Peak Delivery (1,050 kWh @ $0.022)', 23.10),
('INV-2026-06-0018', 'ACCT-50010018', 'RIDER',        'Grid Access & Transmission Cost Recovery', 13.00),
('INV-2026-06-0018', 'ACCT-50010018', 'TAXES_FEES',   'Taxes & Regulatory Fees', 4.75);

-- Usage Records (June 2026). on_peak/off_peak populated for TOU/EV plans.
INSERT INTO usage_records (account_id, billing_period, kwh_used, peak_demand_kw, on_peak_kwh, off_peak_kwh, solar_export_kwh, avg_daily_kwh, days_in_period, prior_year_kwh, read_type) VALUES
('ACCT-50010001', 'June 2026', 1850.00, 6.80,    0.00,    0.00,   0.00, 61.67, 30, 1210.00, 'ACTUAL'),
('ACCT-50010002', 'June 2026', 1420.00, 9.20,  220.00, 1200.00,   0.00, 47.33, 30, 1380.00, 'ACTUAL'),
('ACCT-50010003', 'June 2026',  900.00, 5.10,    0.00,    0.00, 620.00, 30.00, 30,  950.00, 'ACTUAL'),
('ACCT-50010004', 'June 2026', 1350.00, 5.90,    0.00,    0.00,   0.00, 45.00, 30, 1300.00, 'ACTUAL'),
('ACCT-50010005', 'June 2026', 1600.00, 8.10,  950.00,  650.00,   0.00, 53.33, 30, 1150.00, 'ACTUAL'),
('ACCT-50010006', 'June 2026', 1700.00, 7.40,    0.00,    0.00,   0.00, 56.67, 30, 1150.00, 'ESTIMATED'),
('ACCT-50010007', 'June 2026',  150.00, 2.10,    0.00,    0.00,   0.00,  5.00, 30, 1050.00, 'ACTUAL'),
('ACCT-50010008', 'June 2026', 1100.00, 5.50,    0.00,    0.00,   0.00, 36.67, 30, 1120.00, 'ACTUAL'),
('ACCT-50010009', 'June 2026', 1250.00, 6.00,    0.00,    0.00,   0.00, 41.67, 30, 1200.00, 'ACTUAL'),
('ACCT-50010010', 'June 2026',  980.00, 4.80,    0.00,    0.00,   0.00, 32.67, 30, 1000.00, 'ACTUAL'),
('ACCT-50010011', 'June 2026', 1180.00, 5.70,    0.00,    0.00,   0.00, 39.33, 30, 1150.00, 'ACTUAL'),
('ACCT-50010012', 'June 2026', 1320.00, 6.20,    0.00,    0.00,   0.00, 44.00, 30, 1290.00, 'ACTUAL'),
('ACCT-50010013', 'June 2026', 1600.00, 7.00,    0.00,    0.00,   0.00, 53.33, 30, 1500.00, 'ACTUAL'),
('ACCT-50010014', 'June 2026', 1050.00, 5.20,    0.00,    0.00,   0.00, 35.00, 30, 1030.00, 'ACTUAL'),
('ACCT-50010015', 'June 2026', 1240.00, 5.90,    0.00,    0.00,   0.00, 41.33, 30, 1210.00, 'ACTUAL'),
('ACCT-50010016', 'June 2026',  200.00, 2.50,    0.00,    0.00,   0.00,  6.67, 30,  900.00, 'ACTUAL'),
('ACCT-50010017', 'June 2026',  890.00, 4.40,    0.00,    0.00,   0.00, 29.67, 30,  900.00, 'ACTUAL'),
('ACCT-50010018', 'June 2026', 1230.00, 8.40,  180.00, 1050.00,   0.00, 41.00, 30, 1200.00, 'ACTUAL');

-- Payments (2 per account; C7 Henry has an extra recent payment that cleared his past-due balance -> reconnect eligible)
INSERT INTO payments (account_id, payment_date, amount, currency, method, status, reference_number, invoice_id) VALUES
('ACCT-50010001', DATE '2026-07-08', 121.40, 'USD', 'Auto-Pay',    'Success', 'PAY-2026-0101', 'INV-2026-05-0001'),
('ACCT-50010001', DATE '2026-06-08', 118.75, 'USD', 'Auto-Pay',    'Success', 'PAY-2026-0102', 'INV-2026-04-0001'),
('ACCT-50010002', DATE '2026-07-07',  81.20, 'USD', 'Credit Card', 'Success', 'PAY-2026-0201', 'INV-2026-05-0002'),
('ACCT-50010002', DATE '2026-06-07',  79.90, 'USD', 'Credit Card', 'Success', 'PAY-2026-0202', 'INV-2026-04-0002'),
('ACCT-50010003', DATE '2026-07-09',  35.60, 'USD', 'Bank Draft',  'Success', 'PAY-2026-0301', 'INV-2026-05-0003'),
('ACCT-50010003', DATE '2026-06-09',  33.10, 'USD', 'Bank Draft',  'Success', 'PAY-2026-0302', 'INV-2026-04-0003'),
('ACCT-50010004', DATE '2026-07-08',  74.80, 'USD', 'Auto-Pay',    'Success', 'PAY-2026-0401', 'INV-2026-05-0004'),
('ACCT-50010004', DATE '2026-06-08',  73.20, 'USD', 'Auto-Pay',    'Success', 'PAY-2026-0402', 'INV-2026-04-0004'),
('ACCT-50010005', DATE '2026-07-06', 128.30, 'USD', 'Online',      'Success', 'PAY-2026-0501', 'INV-2026-05-0005'),
('ACCT-50010005', DATE '2026-06-06', 112.40, 'USD', 'Online',      'Success', 'PAY-2026-0502', 'INV-2026-04-0005'),
('ACCT-50010006', DATE '2026-07-10',  92.10, 'USD', 'Check',       'Success', 'PAY-2026-0601', 'INV-2026-05-0006'),
('ACCT-50010006', DATE '2026-06-10',  88.60, 'USD', 'Check',       'Success', 'PAY-2026-0602', 'INV-2026-04-0006'),
('ACCT-50010007', DATE '2026-07-24', 142.50, 'USD', 'Debit Card',  'Success', 'PAY-2026-0701', 'INV-2026-05-0007'),
('ACCT-50010007', DATE '2026-06-05',  16.80, 'USD', 'Debit Card',  'Success', 'PAY-2026-0702', 'INV-2026-04-0007'),
('ACCT-50010008', DATE '2026-07-08',  76.90, 'USD', 'Auto-Pay',    'Success', 'PAY-2026-0801', 'INV-2026-05-0008'),
('ACCT-50010008', DATE '2026-06-08',  75.40, 'USD', 'Auto-Pay',    'Success', 'PAY-2026-0802', 'INV-2026-04-0008'),
('ACCT-50010009', DATE '2026-07-09',  85.10, 'USD', 'Credit Card', 'Success', 'PAY-2026-0901', 'INV-2026-05-0009'),
('ACCT-50010009', DATE '2026-06-09',  83.70, 'USD', 'Credit Card', 'Success', 'PAY-2026-0902', 'INV-2026-04-0009'),
('ACCT-50010010', DATE '2026-07-07',  69.00, 'USD', 'Auto-Pay',    'Success', 'PAY-2026-1001', 'INV-2026-05-0010'),
('ACCT-50010010', DATE '2026-06-07',  67.80, 'USD', 'Auto-Pay',    'Success', 'PAY-2026-1002', 'INV-2026-04-0010'),
('ACCT-50010011', DATE '2026-07-08',  80.40, 'USD', 'Online',      'Success', 'PAY-2026-1101', 'INV-2026-05-0011'),
('ACCT-50010011', DATE '2026-06-08',  78.90, 'USD', 'Online',      'Success', 'PAY-2026-1102', 'INV-2026-04-0011'),
('ACCT-50010012', DATE '2026-07-09',  88.60, 'USD', 'Auto-Pay',    'Success', 'PAY-2026-1201', 'INV-2026-05-0012'),
('ACCT-50010012', DATE '2026-06-09',  87.10, 'USD', 'Auto-Pay',    'Success', 'PAY-2026-1202', 'INV-2026-04-0012'),
('ACCT-50010013', DATE '2026-07-08',  93.00, 'USD', 'Auto-Pay',    'Success', 'PAY-2026-1301', 'INV-2026-05-0013'),
('ACCT-50010013', DATE '2026-06-08',  93.00, 'USD', 'Auto-Pay',    'Success', 'PAY-2026-1302', 'INV-2026-04-0013'),
('ACCT-50010014', DATE '2026-07-07',  73.20, 'USD', 'Credit Card', 'Success', 'PAY-2026-1401', 'INV-2026-05-0014'),
('ACCT-50010014', DATE '2026-06-07',  71.90, 'USD', 'Credit Card', 'Success', 'PAY-2026-1402', 'INV-2026-04-0014'),
('ACCT-50010015', DATE '2026-07-08',  83.70, 'USD', 'Auto-Pay',    'Success', 'PAY-2026-1501', 'INV-2026-05-0015'),
('ACCT-50010015', DATE '2026-06-08',  82.30, 'USD', 'Auto-Pay',    'Success', 'PAY-2026-1502', 'INV-2026-04-0015'),
('ACCT-50010016', DATE '2026-07-10',  19.20, 'USD', 'Online',      'Success', 'PAY-2026-1601', 'INV-2026-05-0016'),
('ACCT-50010016', DATE '2026-06-10',  18.40, 'USD', 'Online',      'Success', 'PAY-2026-1602', 'INV-2026-04-0016'),
('ACCT-50010017', DATE '2026-07-08',  63.50, 'USD', 'Auto-Pay',    'Success', 'PAY-2026-1701', 'INV-2026-05-0017'),
('ACCT-50010017', DATE '2026-06-08',  62.10, 'USD', 'Auto-Pay',    'Success', 'PAY-2026-1702', 'INV-2026-04-0017'),
('ACCT-50010018', DATE '2026-07-07',  71.30, 'USD', 'Credit Card', 'Success', 'PAY-2026-1801', 'INV-2026-05-0018'),
('ACCT-50010018', DATE '2026-06-07',  70.10, 'USD', 'Credit Card', 'Success', 'PAY-2026-1802', 'INV-2026-04-0018');

-- Outages — AREA-level active outages (today-relative so they read as live).
INSERT INTO outages (outage_id, feeder_id, zip, area, cause, status, start_time, estimated_restoration, customers_affected) VALUES
('OUT-2026-0001', 'FDR-104', '75004', 'Oakdale / Prairie View', 'STORM',     'RESTORING',    CURRENT_TIMESTAMP - INTERVAL '4 hours', CURRENT_TIMESTAMP + INTERVAL '2 hours', 1240),
('OUT-2026-0002', 'FDR-110', '75010', 'Oakdale / Elm Hollow',   'PLANNED',   'CREW_ASSIGNED', CURRENT_TIMESTAMP + INTERVAL '20 hours', CURRENT_TIMESTAMP + INTERVAL '24 hours', 320),
('OUT-2026-0003', 'FDR-117', '75017', 'Highland / Copperfield', 'EQUIPMENT', 'INVESTIGATING', CURRENT_TIMESTAMP - INTERVAL '1 hours', CURRENT_TIMESTAMP + INTERVAL '3 hours', 85);

-- Outage Tickets — pre-seed one CREW_DISPATCHED ticket for status demos (Ethan). New ones written by outage_dispatch_agent.
INSERT INTO outage_tickets (ticket_id, account_id, premise_address, description, status, crew_id, reported_at, eta) VALUES
('OTKT-2026-0001', 'ACCT-50010015', '870 Foxglove Ave, Lakeside, TX 75015', 'Customer reports total loss of power at residence; neighbors also dark.', 'CREW_DISPATCHED', 'CREW-07', CURRENT_TIMESTAMP - INTERVAL '3 hours', CURRENT_TIMESTAMP + INTERVAL '90 minutes');

-- Service Appointments — pre-seed one SCHEDULED appointment for status demos (Sophia). New ones written by service_appointment_agent.
INSERT INTO service_appointments (appointment_id, account_id, appt_type, scheduled_date, time_window, status, notes) VALUES
('APPT-2026-0001', 'ACCT-50010014', 'METER_INSPECTION', to_char(CURRENT_DATE + INTERVAL '3 days', 'YYYY-MM-DD'), '8:00 AM - 12:00 PM', 'SCHEDULED', 'Customer reported flickering lights; inspect service drop and meter.');

-- Service Requests — pre-seed one IN_PROGRESS reconnect for status demos (Maria). New ones written by service_change_agent.
INSERT INTO service_requests (request_id, account_id, request_type, effective_date, status, reason) VALUES
('SRV-2026-0001', 'ACCT-50010016', 'RECONNECT', to_char(CURRENT_DATE + INTERVAL '1 days', 'YYYY-MM-DD'), 'IN_PROGRESS', 'Reconnection after payment received; field crew scheduled.');
