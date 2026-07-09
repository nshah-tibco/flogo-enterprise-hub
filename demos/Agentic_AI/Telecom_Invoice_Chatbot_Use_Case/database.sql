-- Telecom Invoice Chatbot — Database Schema & Demo Data
-- PostgreSQL 14+
-- Database: telecom
-- Indonesian telecom provider — currency IDR (Indonesian Rupiah), VAT/PPN 11%

-- Drop existing tables (reverse dependency order)
DROP TABLE IF EXISTS recharges CASCADE;
DROP TABLE IF EXISTS disputes CASCADE;
DROP TABLE IF EXISTS recharge_offers CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS plans CASCADE;
DROP TABLE IF EXISTS usage_records CASCADE;
DROP TABLE IF EXISTS invoice_line_items CASCADE;
DROP TABLE IF EXISTS invoices CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

-- 1. Customers â€” CRM master records (subscriber identified by mobile number)
CREATE TABLE customers (
    id              SERIAL PRIMARY KEY,
    customer_id     VARCHAR(20) NOT NULL UNIQUE,        -- CUST-XXXXXXXX
    mobile_number   VARCHAR(25) NOT NULL UNIQUE,        -- +62-8XX-XXXX-XXXX
    first_name      VARCHAR(50) NOT NULL,
    last_name       VARCHAR(50) NOT NULL,
    email           VARCHAR(100),
    segment         VARCHAR(20) NOT NULL DEFAULT 'Consumer',   -- Consumer, Premium, Business, VIP
    account_type    VARCHAR(20) NOT NULL DEFAULT 'Postpaid',   -- Prepaid, Postpaid
    status          VARCHAR(20) NOT NULL DEFAULT 'Active',      -- Active, Suspended, Closed
    active_since    DATE NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_segment CHECK (segment IN ('Consumer','Premium','Business','VIP')),
    CONSTRAINT chk_account_type CHECK (account_type IN ('Prepaid','Postpaid'))
);

-- 2. Invoices â€” monthly invoice header
CREATE TABLE invoices (
    id              SERIAL PRIMARY KEY,
    invoice_id      VARCHAR(25) NOT NULL UNIQUE,        -- INV-2026-06-XXX
    customer_id     VARCHAR(20) NOT NULL REFERENCES customers(customer_id),
    billing_month   VARCHAR(20) NOT NULL,               -- e.g. June 2026
    period_start    DATE NOT NULL,
    period_end      DATE NOT NULL,
    subtotal        NUMERIC(12,2) NOT NULL DEFAULT 0,
    tax             NUMERIC(12,2) NOT NULL DEFAULT 0,
    total_amount    NUMERIC(12,2) NOT NULL DEFAULT 0,
    currency        VARCHAR(3) NOT NULL DEFAULT 'IDR',
    due_date        DATE NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'Unpaid',      -- Unpaid, Paid, Overdue
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_invoice_status CHECK (status IN ('Unpaid','Paid','Overdue'))
);

-- 3. Invoice Line Items â€” charges that make up an invoice
CREATE TABLE invoice_line_items (
    id              SERIAL PRIMARY KEY,
    invoice_id      VARCHAR(25) NOT NULL REFERENCES invoices(invoice_id),
    customer_id     VARCHAR(20) NOT NULL,
    category        VARCHAR(20) NOT NULL,               -- PLAN, IDD, ADDON, ROAMING, TAX, OTHER
    description     VARCHAR(200) NOT NULL,
    amount          NUMERIC(12,2) NOT NULL,
    CONSTRAINT chk_li_category CHECK (category IN ('PLAN','IDD','ADDON','ROAMING','TAX','OTHER'))
);

-- 4. Usage Records â€” metered usage vs limits for a billing period
CREATE TABLE usage_records (
    id                  SERIAL PRIMARY KEY,
    customer_id         VARCHAR(20) NOT NULL REFERENCES customers(customer_id),
    billing_period      VARCHAR(20) NOT NULL,           -- e.g. June 2026
    data_used_gb        NUMERIC(6,2) NOT NULL DEFAULT 0,
    data_limit_gb       NUMERIC(6,2) NOT NULL DEFAULT 0,
    local_call_minutes  INTEGER NOT NULL DEFAULT 0,
    intl_call_minutes   INTEGER NOT NULL DEFAULT 0,
    sms_count           INTEGER NOT NULL DEFAULT 0,
    roaming_days        INTEGER NOT NULL DEFAULT 0,
    roaming_country     VARCHAR(50)
);

-- 5. Plans â€” subscribed base plan and add-ons
CREATE TABLE plans (
    id                  SERIAL PRIMARY KEY,
    customer_id         VARCHAR(20) NOT NULL REFERENCES customers(customer_id),
    plan_name           VARCHAR(80) NOT NULL,
    plan_type           VARCHAR(20) NOT NULL DEFAULT 'BASE',    -- BASE, ADDON
    monthly_fee         NUMERIC(12,2) NOT NULL DEFAULT 0,
    data_allowance_gb   NUMERIC(6,2) NOT NULL DEFAULT 0,        -- 9999 = unlimited
    voice_minutes       INTEGER NOT NULL DEFAULT 0,             -- 9999 = unlimited
    status              VARCHAR(20) NOT NULL DEFAULT 'Active',
    start_date          DATE NOT NULL,
    expiry_date         DATE,
    CONSTRAINT chk_plan_type CHECK (plan_type IN ('BASE','ADDON'))
);

-- 6. Payments â€” payment / top-up history
CREATE TABLE payments (
    id                  SERIAL PRIMARY KEY,
    customer_id         VARCHAR(20) NOT NULL REFERENCES customers(customer_id),
    payment_date        DATE NOT NULL,
    amount              NUMERIC(12,2) NOT NULL,
    currency            VARCHAR(3) NOT NULL DEFAULT 'IDR',
    method              VARCHAR(30) NOT NULL,           -- GoPay, OVO, DANA, Bank Transfer, Credit Card, Auto-Debit, Virtual Account
    status              VARCHAR(20) NOT NULL DEFAULT 'Success',     -- Success, Failed, Pending
    reference_number    VARCHAR(30) NOT NULL,
    invoice_id          VARCHAR(25),                    -- may reference a prior invoice not seeded
    CONSTRAINT chk_payment_status CHECK (status IN ('Success','Failed','Pending'))
);

-- 7. Recharge Offers â€” global catalog of available recharge packs
CREATE TABLE recharge_offers (
    id              SERIAL PRIMARY KEY,
    offer_id        VARCHAR(25) NOT NULL UNIQUE,        -- OFF-DATA-10GB
    offer_name      VARCHAR(80) NOT NULL,
    offer_type      VARCHAR(20) NOT NULL,               -- DATA, IDD, ROAMING, COMBO
    price           NUMERIC(12,2) NOT NULL,
    currency        VARCHAR(3) NOT NULL DEFAULT 'IDR',
    data_amount_gb  NUMERIC(6,2) NOT NULL DEFAULT 0,
    validity_days   INTEGER NOT NULL DEFAULT 30,
    description     VARCHAR(200),
    CONSTRAINT chk_offer_type CHECK (offer_type IN ('DATA','IDD','ROAMING','COMBO'))
);

-- 8. Disputes â€” billing dispute tickets (pre-seeded + written by dispute agent)
CREATE TABLE disputes (
    id                  SERIAL PRIMARY KEY,
    dispute_id          VARCHAR(25) NOT NULL UNIQUE,    -- DSP-2026-XXXX
    customer_id         VARCHAR(20) NOT NULL REFERENCES customers(customer_id),
    invoice_id          VARCHAR(25) NOT NULL,
    reason              VARCHAR(300) NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'OPEN',    -- OPEN, UNDER_REVIEW, RESOLVED, REJECTED
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    estimated_resolution DATE,
    last_update         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolution          VARCHAR(300),
    CONSTRAINT chk_dispute_status CHECK (status IN ('OPEN','UNDER_REVIEW','RESOLVED','REJECTED'))
);

-- 9. Recharges â€” recharge activation log (starts empty; written by recharge agent)
CREATE TABLE recharges (
    id              SERIAL PRIMARY KEY,
    recharge_id     VARCHAR(25) NOT NULL,               -- RCG-2026-XXXX
    customer_id     VARCHAR(20) NOT NULL,
    offer_id        VARCHAR(25) NOT NULL,
    offer_name      VARCHAR(80),
    amount          NUMERIC(12,2),
    data_added_gb   NUMERIC(6,2),
    status          VARCHAR(20) DEFAULT 'ACTIVE',       -- ACTIVE, PENDING, EXPIRED
    applied_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validity_start  DATE,
    validity_end    DATE
);

-- Indexes
CREATE INDEX idx_customers_mobile ON customers(mobile_number);
CREATE INDEX idx_customers_customer ON customers(customer_id);
CREATE INDEX idx_invoices_customer ON invoices(customer_id);
CREATE INDEX idx_invoices_invoice ON invoices(invoice_id);
CREATE INDEX idx_line_items_invoice ON invoice_line_items(invoice_id);
CREATE INDEX idx_usage_customer ON usage_records(customer_id);
CREATE INDEX idx_plans_customer ON plans(customer_id);
CREATE INDEX idx_payments_customer ON payments(customer_id);
CREATE INDEX idx_disputes_customer ON disputes(customer_id);
CREATE INDEX idx_disputes_dispute ON disputes(dispute_id);
CREATE INDEX idx_recharges_customer ON recharges(customer_id);

-- ============================================================
-- DEMO DATA — Indonesian telecom subscribers (currency IDR)
-- ============================================================

-- Customers (16)
INSERT INTO customers (customer_id, mobile_number, first_name, last_name, email, segment, account_type, status, active_since) VALUES
('CUST-10042871', '+62-812-3456-7890', 'Budi', 'Santoso', 'budi.santoso@email.co.id', 'Premium', 'Postpaid', 'Active', '2019-03-15'),
('CUST-10042872', '+62-813-2345-6789', 'Siti', 'Nurhaliza', 'siti.nurhaliza@email.co.id', 'Consumer', 'Postpaid', 'Active', '2021-07-22'),
('CUST-10042873', '+62-852-3456-7891', 'Ahmad', 'Wijaya', 'ahmad.wijaya@email.co.id', 'Consumer', 'Postpaid', 'Active', '2020-11-05'),
('CUST-10042874', '+62-857-4567-8901', 'Dewi', 'Lestari', 'dewi.lestari@email.co.id', 'Consumer', 'Prepaid', 'Active', '2022-02-18'),
('CUST-10042875', '+62-811-5678-9012', 'Rudi', 'Hartono', 'rudi.hartono@email.co.id', 'Business', 'Postpaid', 'Active', '2018-06-30'),
('CUST-10042876', '+62-812-6789-0123', 'Maya', 'Sari', 'maya.sari@email.co.id', 'VIP', 'Postpaid', 'Active', '2017-09-12'),
('CUST-10042877', '+62-853-7890-1234', 'Andi', 'Pratama', 'andi.pratama@email.co.id', 'Consumer', 'Prepaid', 'Active', '2023-01-25'),
('CUST-10042878', '+62-878-8901-2345', 'Rina', 'Melati', 'rina.melati@email.co.id', 'Premium', 'Postpaid', 'Active', '2019-12-08'),
('CUST-10042879', '+62-856-9012-3456', 'Joko', 'Susilo', 'joko.susilo@email.co.id', 'Consumer', 'Postpaid', 'Active', '2020-05-14'),
('CUST-10042880', '+62-838-0123-4567', 'Putri', 'Anggraini', 'putri.anggraini@email.co.id', 'Premium', 'Postpaid', 'Active', '2018-10-02'),
('CUST-10042881', '+62-817-1234-5678', 'Bambang', 'Kusuma', 'bambang.kusuma@email.co.id', 'Business', 'Postpaid', 'Active', '2019-08-19'),
('CUST-10042882', '+62-819-2345-6780', 'Sri', 'Wahyuni', 'sri.wahyuni@email.co.id', 'Consumer', 'Prepaid', 'Active', '2022-11-30'),
('CUST-10042883', '+62-822-3456-7801', 'Agus', 'Salim', 'agus.salim@email.co.id', 'Consumer', 'Postpaid', 'Active', '2021-03-08'),
('CUST-10042884', '+62-812-4567-8902', 'Fitri', 'Handayani', 'fitri.handayani@email.co.id', 'Premium', 'Postpaid', 'Active', '2020-01-27'),
('CUST-10042885', '+62-813-5678-9013', 'Hendra', 'Gunawan', 'hendra.gunawan@email.co.id', 'VIP', 'Postpaid', 'Active', '2016-04-11'),
('CUST-10042886', '+62-858-6789-0124', 'Lia', 'Permata', 'lia.permata@email.co.id', 'Consumer', 'Prepaid', 'Active', '2023-06-05');

-- Invoices (12 postpaid — June 2026; tax = PPN 11%, totals computed from line items)
INSERT INTO invoices (invoice_id, customer_id, billing_month, period_start, period_end, subtotal, tax, total_amount, currency, due_date, status) VALUES
('INV-2026-06-871', 'CUST-10042871', 'June 2026', '2026-06-01', '2026-06-30', 450000.00, 49500.00, 499500.00, 'IDR', '2026-07-15', 'Unpaid'),
('INV-2026-06-872', 'CUST-10042872', 'June 2026', '2026-06-01', '2026-06-30', 320000.00, 35200.00, 355200.00, 'IDR', '2026-07-15', 'Unpaid'),
('INV-2026-06-873', 'CUST-10042873', 'June 2026', '2026-06-01', '2026-06-30', 105000.00, 11550.00, 116550.00, 'IDR', '2026-07-15', 'Unpaid'),
('INV-2026-06-875', 'CUST-10042875', 'June 2026', '2026-06-01', '2026-06-30', 635000.00, 69850.00, 704850.00, 'IDR', '2026-07-15', 'Unpaid'),
('INV-2026-06-876', 'CUST-10042876', 'June 2026', '2026-06-01', '2026-06-30', 1130000.00, 124300.00, 1254300.00, 'IDR', '2026-07-15', 'Unpaid'),
('INV-2026-06-878', 'CUST-10042878', 'June 2026', '2026-06-01', '2026-06-30', 150000.00, 16500.00, 166500.00, 'IDR', '2026-07-15', 'Unpaid'),
('INV-2026-06-879', 'CUST-10042879', 'June 2026', '2026-06-01', '2026-06-30', 195000.00, 21450.00, 216450.00, 'IDR', '2026-07-15', 'Unpaid'),
('INV-2026-06-880', 'CUST-10042880', 'June 2026', '2026-06-01', '2026-06-30', 570000.00, 62700.00, 632700.00, 'IDR', '2026-07-15', 'Unpaid'),
('INV-2026-06-881', 'CUST-10042881', 'June 2026', '2026-06-01', '2026-06-30', 490000.00, 53900.00, 543900.00, 'IDR', '2026-07-15', 'Unpaid'),
('INV-2026-06-883', 'CUST-10042883', 'June 2026', '2026-06-01', '2026-06-30', 75000.00, 8250.00, 83250.00, 'IDR', '2026-07-15', 'Unpaid'),
('INV-2026-06-884', 'CUST-10042884', 'June 2026', '2026-06-01', '2026-06-30', 330000.00, 36300.00, 366300.00, 'IDR', '2026-07-15', 'Unpaid'),
('INV-2026-06-885', 'CUST-10042885', 'June 2026', '2026-06-01', '2026-06-30', 1445000.00, 158950.00, 1603950.00, 'IDR', '2026-07-15', 'Unpaid');

-- Invoice Line Items
INSERT INTO invoice_line_items (invoice_id, customer_id, category, description, amount) VALUES
('INV-2026-06-871', 'CUST-10042871', 'PLAN', 'Pascabayar Prime 100 (monthly)', 150000.00),
('INV-2026-06-871', 'CUST-10042871', 'IDD', 'International Calls (Singapore)', 85000.00),
('INV-2026-06-871', 'CUST-10042871', 'ADDON', 'Data Add-on 10GB', 50000.00),
('INV-2026-06-871', 'CUST-10042871', 'ROAMING', 'Roaming Singapore (3 days)', 165000.00),
('INV-2026-06-871', 'CUST-10042871', 'TAX', 'VAT (PPN) 11%', 49500.00),
('INV-2026-06-872', 'CUST-10042872', 'PLAN', 'Pascabayar Value 50 (monthly)', 100000.00),
('INV-2026-06-872', 'CUST-10042872', 'ROAMING', 'Roaming Thailand (5 days)', 220000.00),
('INV-2026-06-872', 'CUST-10042872', 'TAX', 'VAT (PPN) 11%', 35200.00),
('INV-2026-06-873', 'CUST-10042873', 'PLAN', 'Pascabayar Smart 30 (monthly)', 75000.00),
('INV-2026-06-873', 'CUST-10042873', 'ADDON', 'Data Add-on 5GB', 30000.00),
('INV-2026-06-873', 'CUST-10042873', 'TAX', 'VAT (PPN) 11%', 11550.00),
('INV-2026-06-875', 'CUST-10042875', 'PLAN', 'Business Unlimited Pro (monthly)', 400000.00),
('INV-2026-06-875', 'CUST-10042875', 'ADDON', 'IDD SLI Pack', 60000.00),
('INV-2026-06-875', 'CUST-10042875', 'IDD', 'International Calls (US / Japan)', 175000.00),
('INV-2026-06-875', 'CUST-10042875', 'TAX', 'VAT (PPN) 11%', 69850.00),
('INV-2026-06-876', 'CUST-10042876', 'PLAN', 'VIP Platinum Unlimited (monthly)', 750000.00),
('INV-2026-06-876', 'CUST-10042876', 'ROAMING', 'Roaming Japan (7 days)', 380000.00),
('INV-2026-06-876', 'CUST-10042876', 'TAX', 'VAT (PPN) 11%', 124300.00),
('INV-2026-06-878', 'CUST-10042878', 'PLAN', 'Pascabayar Prime 100 (monthly)', 150000.00),
('INV-2026-06-878', 'CUST-10042878', 'TAX', 'VAT (PPN) 11%', 16500.00),
('INV-2026-06-879', 'CUST-10042879', 'PLAN', 'Pascabayar Value 50 (monthly)', 100000.00),
('INV-2026-06-879', 'CUST-10042879', 'IDD', 'International Calls (China)', 95000.00),
('INV-2026-06-879', 'CUST-10042879', 'TAX', 'VAT (PPN) 11%', 21450.00),
('INV-2026-06-880', 'CUST-10042880', 'PLAN', 'Pascabayar Prime 100 (monthly)', 150000.00),
('INV-2026-06-880', 'CUST-10042880', 'ADDON', 'Data Add-on 10GB', 50000.00),
('INV-2026-06-880', 'CUST-10042880', 'ROAMING', 'Roaming Australia (5 days)', 310000.00),
('INV-2026-06-880', 'CUST-10042880', 'IDD', 'International Calls (Australia)', 60000.00),
('INV-2026-06-880', 'CUST-10042880', 'TAX', 'VAT (PPN) 11%', 62700.00),
('INV-2026-06-881', 'CUST-10042881', 'PLAN', 'Business Unlimited Pro (monthly)', 400000.00),
('INV-2026-06-881', 'CUST-10042881', 'IDD', 'International Calls (Singapore / Malaysia)', 90000.00),
('INV-2026-06-881', 'CUST-10042881', 'TAX', 'VAT (PPN) 11%', 53900.00),
('INV-2026-06-883', 'CUST-10042883', 'PLAN', 'Pascabayar Smart 30 (monthly)', 75000.00),
('INV-2026-06-883', 'CUST-10042883', 'TAX', 'VAT (PPN) 11%', 8250.00),
('INV-2026-06-884', 'CUST-10042884', 'PLAN', 'Pascabayar Prime 100 (monthly)', 150000.00),
('INV-2026-06-884', 'CUST-10042884', 'ROAMING', 'Roaming Malaysia (4 days)', 180000.00),
('INV-2026-06-884', 'CUST-10042884', 'TAX', 'VAT (PPN) 11%', 36300.00),
('INV-2026-06-885', 'CUST-10042885', 'PLAN', 'VIP Platinum Unlimited (monthly)', 750000.00),
('INV-2026-06-885', 'CUST-10042885', 'ADDON', 'IDD SLI Pack', 60000.00),
('INV-2026-06-885', 'CUST-10042885', 'ROAMING', 'Roaming Saudi Arabia (9 days)', 495000.00),
('INV-2026-06-885', 'CUST-10042885', 'IDD', 'International Calls (Saudi Arabia)', 140000.00),
('INV-2026-06-885', 'CUST-10042885', 'TAX', 'VAT (PPN) 11%', 158950.00);

-- Usage Records (June 2026)
INSERT INTO usage_records (customer_id, billing_period, data_used_gb, data_limit_gb, local_call_minutes, intl_call_minutes, sms_count, roaming_days, roaming_country) VALUES
('CUST-10042871', 'June 2026', 38.70, 50.00, 342, 47, 12, 3, 'Singapore'),
('CUST-10042872', 'June 2026', 12.30, 20.00, 210, 0, 8, 0, NULL),
('CUST-10042873', 'June 2026', 19.60, 20.00, 88, 0, 3, 0, NULL),
('CUST-10042874', 'June 2026', 6.40, 10.00, 60, 0, 15, 0, NULL),
('CUST-10042875', 'June 2026', 72.50, 100.00, 540, 230, 45, 0, NULL),
('CUST-10042876', 'June 2026', 95.00, 9999.00, 320, 88, 20, 7, 'Japan'),
('CUST-10042877', 'June 2026', 3.10, 5.00, 40, 0, 5, 0, NULL),
('CUST-10042878', 'June 2026', 22.40, 40.00, 180, 12, 9, 0, NULL),
('CUST-10042879', 'June 2026', 15.20, 20.00, 130, 0, 6, 0, NULL),
('CUST-10042880', 'June 2026', 41.80, 50.00, 260, 95, 14, 5, 'Australia'),
('CUST-10042881', 'June 2026', 96.50, 100.00, 480, 60, 30, 0, NULL),
('CUST-10042882', 'June 2026', 8.50, 10.00, 70, 0, 20, 0, NULL),
('CUST-10042883', 'June 2026', 11.00, 15.00, 95, 0, 4, 0, NULL),
('CUST-10042884', 'June 2026', 28.30, 40.00, 150, 22, 7, 4, 'Malaysia'),
('CUST-10042885', 'June 2026', 88.00, 9999.00, 410, 160, 25, 9, 'Saudi Arabia'),
('CUST-10042886', 'June 2026', 2.80, 5.00, 35, 0, 8, 0, NULL);

-- Plans (base + add-ons)
INSERT INTO plans (customer_id, plan_name, plan_type, monthly_fee, data_allowance_gb, voice_minutes, status, start_date, expiry_date) VALUES
('CUST-10042871', 'Pascabayar Prime 100', 'BASE', 150000.00, 40.00, 500, 'Active', '2019-03-15', NULL),
('CUST-10042871', 'Data Add-on 10GB', 'ADDON', 50000.00, 10.00, 0, 'Active', '2026-06-01', '2026-06-30'),
('CUST-10042872', 'Pascabayar Value 50', 'BASE', 100000.00, 20.00, 200, 'Active', '2021-07-22', NULL),
('CUST-10042873', 'Pascabayar Smart 30', 'BASE', 75000.00, 15.00, 100, 'Active', '2020-11-05', NULL),
('CUST-10042873', 'Data Add-on 5GB', 'ADDON', 30000.00, 5.00, 0, 'Active', '2026-06-01', '2026-06-30'),
('CUST-10042874', 'Prabayar Freedom', 'BASE', 50000.00, 10.00, 100, 'Active', '2022-02-18', NULL),
('CUST-10042875', 'Business Unlimited Pro', 'BASE', 400000.00, 100.00, 9999, 'Active', '2018-06-30', NULL),
('CUST-10042875', 'IDD SLI Pack', 'ADDON', 60000.00, 0.00, 0, 'Active', '2026-06-01', '2026-06-30'),
('CUST-10042876', 'VIP Platinum Unlimited', 'BASE', 750000.00, 9999.00, 9999, 'Active', '2017-09-12', NULL),
('CUST-10042877', 'Prabayar Super Hemat', 'BASE', 25000.00, 5.00, 60, 'Active', '2023-01-25', NULL),
('CUST-10042878', 'Pascabayar Prime 100', 'BASE', 150000.00, 40.00, 500, 'Active', '2019-12-08', NULL),
('CUST-10042879', 'Pascabayar Value 50', 'BASE', 100000.00, 20.00, 200, 'Active', '2020-05-14', NULL),
('CUST-10042880', 'Pascabayar Prime 100', 'BASE', 150000.00, 40.00, 500, 'Active', '2018-10-02', NULL),
('CUST-10042880', 'Data Add-on 10GB', 'ADDON', 50000.00, 10.00, 0, 'Active', '2026-06-01', '2026-06-30'),
('CUST-10042881', 'Business Unlimited Pro', 'BASE', 400000.00, 100.00, 9999, 'Active', '2019-08-19', NULL),
('CUST-10042882', 'Prabayar Freedom', 'BASE', 50000.00, 10.00, 100, 'Active', '2022-11-30', NULL),
('CUST-10042883', 'Pascabayar Smart 30', 'BASE', 75000.00, 15.00, 100, 'Active', '2021-03-08', NULL),
('CUST-10042884', 'Pascabayar Prime 100', 'BASE', 150000.00, 40.00, 500, 'Active', '2020-01-27', NULL),
('CUST-10042885', 'VIP Platinum Unlimited', 'BASE', 750000.00, 9999.00, 9999, 'Active', '2016-04-11', NULL),
('CUST-10042885', 'IDD SLI Pack', 'ADDON', 60000.00, 0.00, 0, 'Active', '2026-06-01', '2026-06-30'),
('CUST-10042886', 'Prabayar Super Hemat', 'BASE', 25000.00, 5.00, 60, 'Active', '2023-06-05', NULL);

-- Payments / top-ups
INSERT INTO payments (customer_id, payment_date, amount, currency, method, status, reference_number, invoice_id) VALUES
('CUST-10042871', DATE '2026-05-21' - 3, 480000.00, 'IDR', 'Auto-Debit', 'Success', 'PAY-2026-87101', 'INV-2026-05-871'),
('CUST-10042871', DATE '2026-05-21' - 33, 465000.00, 'IDR', 'Auto-Debit', 'Success', 'PAY-2026-87102', 'INV-2026-04-871'),
('CUST-10042871', DATE '2026-05-21' - 63, 450000.00, 'IDR', 'Credit Card', 'Success', 'PAY-2026-87103', 'INV-2026-03-871'),
('CUST-10042872', DATE '2026-05-21' - 4, 340000.00, 'IDR', 'GoPay', 'Success', 'PAY-2026-87201', 'INV-2026-05-872'),
('CUST-10042872', DATE '2026-05-21' - 34, 335000.00, 'IDR', 'Bank Transfer', 'Success', 'PAY-2026-87202', 'INV-2026-04-872'),
('CUST-10042873', DATE '2026-05-21' - 2, 116000.00, 'IDR', 'OVO', 'Success', 'PAY-2026-87301', 'INV-2026-05-873'),
('CUST-10042873', DATE '2026-05-21' - 32, 110000.00, 'IDR', 'OVO', 'Success', 'PAY-2026-87302', 'INV-2026-04-873'),
('CUST-10042874', DATE '2026-05-21' - 5, 50000.00, 'IDR', 'GoPay', 'Success', 'PAY-2026-87401', NULL),
('CUST-10042874', DATE '2026-05-21' - 20, 50000.00, 'IDR', 'GoPay', 'Success', 'PAY-2026-87402', NULL),
('CUST-10042875', DATE '2026-05-21' - 3, 700000.00, 'IDR', 'Auto-Debit', 'Success', 'PAY-2026-87501', 'INV-2026-05-875'),
('CUST-10042875', DATE '2026-05-21' - 33, 690000.00, 'IDR', 'Auto-Debit', 'Success', 'PAY-2026-87502', 'INV-2026-04-875'),
('CUST-10042875', DATE '2026-05-21' - 63, 710000.00, 'IDR', 'Auto-Debit', 'Success', 'PAY-2026-87503', 'INV-2026-03-875'),
('CUST-10042875', DATE '2026-05-21' - 93, 680000.00, 'IDR', 'Virtual Account', 'Success', 'PAY-2026-87504', 'INV-2026-02-875'),
('CUST-10042875', DATE '2026-05-21' - 123, 695000.00, 'IDR', 'Credit Card', 'Success', 'PAY-2026-87505', 'INV-2026-01-875'),
('CUST-10042876', DATE '2026-05-21' - 3, 1250000.00, 'IDR', 'Auto-Debit', 'Success', 'PAY-2026-87601', 'INV-2026-05-876'),
('CUST-10042876', DATE '2026-05-21' - 34, 1200000.00, 'IDR', 'Auto-Debit', 'Success', 'PAY-2026-87602', 'INV-2026-04-876'),
('CUST-10042876', DATE '2026-05-21' - 64, 1230000.00, 'IDR', 'Credit Card', 'Success', 'PAY-2026-87603', 'INV-2026-03-876'),
('CUST-10042877', DATE '2026-05-21' - 1, 25000.00, 'IDR', 'DANA', 'Success', 'PAY-2026-87701', NULL),
('CUST-10042877', DATE '2026-05-21' - 18, 25000.00, 'IDR', 'DANA', 'Success', 'PAY-2026-87702', NULL),
('CUST-10042878', DATE '2026-05-21' - 6, 166000.00, 'IDR', 'Credit Card', 'Success', 'PAY-2026-87801', 'INV-2026-05-878'),
('CUST-10042878', DATE '2026-05-21' - 36, 160000.00, 'IDR', 'Credit Card', 'Success', 'PAY-2026-87802', 'INV-2026-04-878'),
('CUST-10042879', DATE '2026-05-21' - 4, 210000.00, 'IDR', 'Bank Transfer', 'Success', 'PAY-2026-87901', 'INV-2026-05-879'),
('CUST-10042879', DATE '2026-05-21' - 34, 205000.00, 'IDR', 'Bank Transfer', 'Success', 'PAY-2026-87902', 'INV-2026-04-879'),
('CUST-10042880', DATE '2026-05-21' - 3, 630000.00, 'IDR', 'Auto-Debit', 'Success', 'PAY-2026-88001', 'INV-2026-05-880'),
('CUST-10042880', DATE '2026-05-21' - 33, 610000.00, 'IDR', 'Auto-Debit', 'Success', 'PAY-2026-88002', 'INV-2026-04-880'),
('CUST-10042881', DATE '2026-05-21' - 2, 540000.00, 'IDR', 'Auto-Debit', 'Success', 'PAY-2026-88101', 'INV-2026-05-881'),
('CUST-10042881', DATE '2026-05-21' - 32, 520000.00, 'IDR', 'Auto-Debit', 'Success', 'PAY-2026-88102', 'INV-2026-04-881'),
('CUST-10042881', DATE '2026-05-21' - 62, 535000.00, 'IDR', 'Virtual Account', 'Success', 'PAY-2026-88103', 'INV-2026-03-881'),
('CUST-10042882', DATE '2026-05-21' - 5, 50000.00, 'IDR', 'GoPay', 'Success', 'PAY-2026-88201', NULL),
('CUST-10042883', DATE '2026-05-21' - 3, 83000.00, 'IDR', 'OVO', 'Success', 'PAY-2026-88301', 'INV-2026-05-883'),
('CUST-10042883', DATE '2026-05-21' - 33, 80000.00, 'IDR', 'OVO', 'Success', 'PAY-2026-88302', 'INV-2026-04-883'),
('CUST-10042884', DATE '2026-05-21' - 4, 366000.00, 'IDR', 'Credit Card', 'Success', 'PAY-2026-88401', 'INV-2026-05-884'),
('CUST-10042884', DATE '2026-05-21' - 34, 350000.00, 'IDR', 'Credit Card', 'Success', 'PAY-2026-88402', 'INV-2026-04-884'),
('CUST-10042885', DATE '2026-05-21' - 3, 1600000.00, 'IDR', 'Auto-Debit', 'Success', 'PAY-2026-88501', 'INV-2026-05-885'),
('CUST-10042885', DATE '2026-05-21' - 33, 1550000.00, 'IDR', 'Auto-Debit', 'Success', 'PAY-2026-88502', 'INV-2026-04-885'),
('CUST-10042885', DATE '2026-05-21' - 63, 1580000.00, 'IDR', 'Auto-Debit', 'Success', 'PAY-2026-88503', 'INV-2026-03-885'),
('CUST-10042885', DATE '2026-05-21' - 93, 1520000.00, 'IDR', 'Credit Card', 'Success', 'PAY-2026-88504', 'INV-2026-02-885'),
('CUST-10042886', DATE '2026-05-21' - 1, 25000.00, 'IDR', 'DANA', 'Success', 'PAY-2026-88601', NULL);

-- Recharge Offers (global catalog)
INSERT INTO recharge_offers (offer_id, offer_name, offer_type, price, currency, data_amount_gb, validity_days, description) VALUES
('OFF-DATA-5GB', 'Data Booster 5GB', 'DATA', 30000.00, 'IDR', 5.00, 30, '5GB high-speed data valid for 30 days'),
('OFF-DATA-10GB', 'Data Booster 10GB', 'DATA', 50000.00, 'IDR', 10.00, 30, '10GB high-speed data valid for 30 days'),
('OFF-DATA-25GB', 'Data Max 25GB', 'DATA', 100000.00, 'IDR', 25.00, 30, '25GB high-speed data valid for 30 days'),
('OFF-DATA-50GB', 'Data Jumbo 50GB', 'DATA', 175000.00, 'IDR', 50.00, 30, '50GB high-speed data valid for 30 days'),
('OFF-IDD-ASIA', 'IDD Asia 100 min', 'IDD', 45000.00, 'IDR', 0.00, 30, '100 international minutes to Asia valid for 30 days'),
('OFF-ROAM-ASEAN', 'Roaming ASEAN 3-Day Pass', 'ROAMING', 150000.00, 'IDR', 3.00, 3, 'Unlimited ASEAN roaming calls + 3GB data for 3 days'),
('OFF-ROAM-JAPAN', 'Roaming Japan 5-Day Pass', 'ROAMING', 350000.00, 'IDR', 5.00, 5, 'Japan roaming calls + 5GB data for 5 days'),
('OFF-COMBO-SOCIAL', 'Combo Sakti Social', 'COMBO', 65000.00, 'IDR', 15.00, 30, '15GB data + unlimited social media valid for 30 days');

-- Disputes (pre-seeded for status lookup; new ones added by the dispute agent)
INSERT INTO disputes (dispute_id, customer_id, invoice_id, reason, status, created_at, estimated_resolution, last_update, resolution) VALUES
('DSP-2026-0001', 'CUST-10042876', 'INV-2026-05-876', 'Disputed premium content SMS charges of IDR 45,000 not recognised by customer', 'UNDER_REVIEW', '2026-05-21 10:15:00'::timestamp - INTERVAL '12 days', DATE '2026-05-21' + 3, '2026-05-21 09:30:00'::timestamp - INTERVAL '2 days', NULL),
('DSP-2026-0002', 'CUST-10042883', 'INV-2026-04-883', 'Incorrect late payment fee applied', 'RESOLVED', '2026-05-21 10:15:00'::timestamp - INTERVAL '40 days', DATE '2026-05-21' + -33, '2026-05-21 09:30:00'::timestamp - INTERVAL '35 days', 'Late payment fee of IDR 25,000 waived and credited to the account.'),
('DSP-2026-0003', 'CUST-10042873', 'INV-2026-05-873', 'Data add-on charged twice on the same billing cycle', 'OPEN', '2026-05-21 10:15:00'::timestamp - INTERVAL '5 days', DATE '2026-05-21' + 5, '2026-05-21 09:30:00'::timestamp - INTERVAL '5 days', NULL);

-- Recharges: starts empty. Rows are inserted by the recharge_agent at runtime.
