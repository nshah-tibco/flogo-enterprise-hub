-- Telecom Invoice Chatbot — Reset Demo Data (US provider, USD)
-- Restores a clean demo state (undoes agent writes) with today-relative dates.
-- Currency: USD. Taxes & Regulatory Fees ~10%. Subscribers identified by +1 mobile numbers.
-- PostgreSQL 14+

TRUNCATE recharges, disputes, recharge_offers, payments, plans, usage_records,
         invoice_line_items, invoices, customers RESTART IDENTITY CASCADE;

-- Customers (22) — US subscribers. 555-01xx numbers are reserved for fictional use.
-- CUST-...887..892 are dedicated "wrong charge" accounts for dispute demos.
INSERT INTO customers (customer_id, mobile_number, first_name, last_name, email, segment, account_type, status, active_since) VALUES
('CUST-10042871', '+1-415-555-0142', 'James', 'Anderson', 'james.anderson@email.com', 'Premium', 'Postpaid', 'Active', '2019-03-15'),
('CUST-10042872', '+1-212-555-0178', 'Emily', 'Carter', 'emily.carter@email.com', 'Consumer', 'Postpaid', 'Active', '2021-07-22'),
('CUST-10042873', '+1-312-555-0163', 'Michael', 'Rodriguez', 'michael.rodriguez@email.com', 'Consumer', 'Postpaid', 'Active', '2020-11-05'),
('CUST-10042874', '+1-206-555-0119', 'Sarah', 'Thompson', 'sarah.thompson@email.com', 'Consumer', 'Prepaid', 'Active', '2022-02-18'),
('CUST-10042875', '+1-617-555-0187', 'David', 'Martinez', 'david.martinez@email.com', 'Business', 'Postpaid', 'Active', '2018-06-30'),
('CUST-10042876', '+1-305-555-0134', 'Jessica', 'Williams', 'jessica.williams@email.com', 'VIP', 'Postpaid', 'Active', '2017-09-12'),
('CUST-10042877', '+1-702-555-0155', 'Christopher', 'Lee', 'christopher.lee@email.com', 'Consumer', 'Prepaid', 'Active', '2023-01-25'),
('CUST-10042878', '+1-512-555-0198', 'Amanda', 'Davis', 'amanda.davis@email.com', 'Premium', 'Postpaid', 'Active', '2019-12-08'),
('CUST-10042879', '+1-404-555-0172', 'Robert', 'Johnson', 'robert.johnson@email.com', 'Consumer', 'Postpaid', 'Active', '2020-05-14'),
('CUST-10042880', '+1-646-555-0110', 'Ashley', 'Brown', 'ashley.brown@email.com', 'Premium', 'Postpaid', 'Active', '2018-10-02'),
('CUST-10042881', '+1-773-555-0145', 'Daniel', 'Wilson', 'daniel.wilson@email.com', 'Business', 'Postpaid', 'Active', '2019-08-19'),
('CUST-10042882', '+1-480-555-0166', 'Michelle', 'Garcia', 'michelle.garcia@email.com', 'Consumer', 'Prepaid', 'Active', '2022-11-30'),
('CUST-10042883', '+1-215-555-0129', 'Matthew', 'Miller', 'matthew.miller@email.com', 'Consumer', 'Postpaid', 'Active', '2021-03-08'),
('CUST-10042884', '+1-503-555-0181', 'Stephanie', 'Moore', 'stephanie.moore@email.com', 'Premium', 'Postpaid', 'Active', '2020-01-27'),
('CUST-10042885', '+1-725-555-0193', 'Kevin', 'Taylor', 'kevin.taylor@email.com', 'VIP', 'Postpaid', 'Active', '2016-04-11'),
('CUST-10042886', '+1-919-555-0157', 'Nicole', 'Jackson', 'nicole.jackson@email.com', 'Consumer', 'Prepaid', 'Active', '2023-06-05'),
('CUST-10042887', '+1-408-555-0102', 'Brian', 'Hall', 'brian.hall@email.com', 'Consumer', 'Postpaid', 'Active', '2021-05-10'),
('CUST-10042888', '+1-619-555-0113', 'Laura', 'Adams', 'laura.adams@email.com', 'Premium', 'Postpaid', 'Active', '2020-08-14'),
('CUST-10042889', '+1-716-555-0124', 'Kevin', 'Nguyen', 'kevin.nguyen@email.com', 'Consumer', 'Postpaid', 'Active', '2022-03-22'),
('CUST-10042890', '+1-813-555-0135', 'Rachel', 'Scott', 'rachel.scott@email.com', 'Consumer', 'Postpaid', 'Active', '2021-09-01'),
('CUST-10042891', '+1-901-555-0146', 'Justin', 'King', 'justin.king@email.com', 'Premium', 'Postpaid', 'Active', '2019-11-19'),
('CUST-10042892', '+1-303-555-0157', 'Megan', 'Wright', 'megan.wright@email.com', 'Consumer', 'Postpaid', 'Active', '2022-06-05');

-- Invoices (June 2026; tax = Taxes & Regulatory Fees ~10%; totals computed from line items). Due dates relative to today.
INSERT INTO invoices (invoice_id, customer_id, billing_month, period_start, period_end, subtotal, tax, total_amount, currency, due_date, status) VALUES
('INV-2026-06-871', 'CUST-10042871', 'June 2026', '2026-06-01', '2026-06-30', 127.00, 12.70, 139.70, 'USD', CURRENT_DATE + INTERVAL '7 days', 'Unpaid'),
('INV-2026-06-872', 'CUST-10042872', 'June 2026', '2026-06-01', '2026-06-30', 85.00, 8.50, 93.50, 'USD', CURRENT_DATE + INTERVAL '7 days', 'Unpaid'),
('INV-2026-06-873', 'CUST-10042873', 'June 2026', '2026-06-01', '2026-06-30', 40.00, 4.00, 44.00, 'USD', CURRENT_DATE + INTERVAL '7 days', 'Unpaid'),
('INV-2026-06-875', 'CUST-10042875', 'June 2026', '2026-06-01', '2026-06-30', 175.00, 17.50, 192.50, 'USD', CURRENT_DATE + INTERVAL '7 days', 'Unpaid'),
('INV-2026-06-876', 'CUST-10042876', 'June 2026', '2026-06-01', '2026-06-30', 240.00, 24.00, 264.00, 'USD', CURRENT_DATE + INTERVAL '7 days', 'Unpaid'),
('INV-2026-06-878', 'CUST-10042878', 'June 2026', '2026-06-01', '2026-06-30', 70.00, 7.00, 77.00, 'USD', CURRENT_DATE + INTERVAL '7 days', 'Unpaid'),
('INV-2026-06-879', 'CUST-10042879', 'June 2026', '2026-06-01', '2026-06-30', 65.00, 6.50, 71.50, 'USD', CURRENT_DATE + INTERVAL '7 days', 'Unpaid'),
('INV-2026-06-880', 'CUST-10042880', 'June 2026', '2026-06-01', '2026-06-30', 145.00, 14.50, 159.50, 'USD', CURRENT_DATE + INTERVAL '7 days', 'Unpaid'),
('INV-2026-06-881', 'CUST-10042881', 'June 2026', '2026-06-01', '2026-06-30', 138.00, 13.80, 151.80, 'USD', CURRENT_DATE + INTERVAL '7 days', 'Unpaid'),
('INV-2026-06-883', 'CUST-10042883', 'June 2026', '2026-06-01', '2026-06-30', 30.00, 3.00, 33.00, 'USD', CURRENT_DATE + INTERVAL '7 days', 'Unpaid'),
('INV-2026-06-884', 'CUST-10042884', 'June 2026', '2026-06-01', '2026-06-30', 110.00, 11.00, 121.00, 'USD', CURRENT_DATE + INTERVAL '7 days', 'Unpaid'),
('INV-2026-06-885', 'CUST-10042885', 'June 2026', '2026-06-01', '2026-06-30', 308.00, 30.80, 338.80, 'USD', CURRENT_DATE + INTERVAL '7 days', 'Unpaid'),
-- Wrong-charge invoices (disputable)
('INV-2026-06-887', 'CUST-10042887', 'June 2026', '2026-06-01', '2026-06-30', 85.00, 8.50, 93.50, 'USD', CURRENT_DATE + INTERVAL '7 days', 'Unpaid'),
('INV-2026-06-888', 'CUST-10042888', 'June 2026', '2026-06-01', '2026-06-30', 108.00, 10.80, 118.80, 'USD', CURRENT_DATE + INTERVAL '7 days', 'Unpaid'),
('INV-2026-06-889', 'CUST-10042889', 'June 2026', '2026-06-01', '2026-06-30', 60.00, 6.00, 66.00, 'USD', CURRENT_DATE + INTERVAL '7 days', 'Unpaid'),
('INV-2026-06-890', 'CUST-10042890', 'June 2026', '2026-06-01', '2026-06-30', 59.99, 6.00, 65.99, 'USD', CURRENT_DATE + INTERVAL '7 days', 'Unpaid'),
('INV-2026-06-891', 'CUST-10042891', 'June 2026', '2026-06-01', '2026-06-30', 100.00, 10.00, 110.00, 'USD', CURRENT_DATE + INTERVAL '7 days', 'Unpaid'),
('INV-2026-06-892', 'CUST-10042892', 'June 2026', '2026-06-01', '2026-06-30', 40.00, 4.00, 44.00, 'USD', CURRENT_DATE + INTERVAL '7 days', 'Unpaid');

-- Invoice Line Items
INSERT INTO invoice_line_items (invoice_id, customer_id, category, description, amount) VALUES
('INV-2026-06-871', 'CUST-10042871', 'PLAN', 'Premium Unlimited (monthly)', 70.00),
('INV-2026-06-871', 'CUST-10042871', 'IDD', 'International Calls (Mexico)', 12.00),
('INV-2026-06-871', 'CUST-10042871', 'ADDON', 'Data Add-on 10GB', 15.00),
('INV-2026-06-871', 'CUST-10042871', 'ROAMING', 'Roaming Mexico (3 days)', 30.00),
('INV-2026-06-871', 'CUST-10042871', 'TAX', 'Taxes & Regulatory Fees', 12.70),
('INV-2026-06-872', 'CUST-10042872', 'PLAN', 'Value 5GB (monthly)', 40.00),
('INV-2026-06-872', 'CUST-10042872', 'ROAMING', 'Roaming Mexico (5 days)', 45.00),
('INV-2026-06-872', 'CUST-10042872', 'TAX', 'Taxes & Regulatory Fees', 8.50),
('INV-2026-06-873', 'CUST-10042873', 'PLAN', 'Essential 15GB (monthly)', 30.00),
('INV-2026-06-873', 'CUST-10042873', 'ADDON', 'Data Add-on 5GB', 10.00),
('INV-2026-06-873', 'CUST-10042873', 'TAX', 'Taxes & Regulatory Fees', 4.00),
('INV-2026-06-875', 'CUST-10042875', 'PLAN', 'Business Unlimited Pro (monthly)', 120.00),
('INV-2026-06-875', 'CUST-10042875', 'ADDON', 'International Calling Pack', 20.00),
('INV-2026-06-875', 'CUST-10042875', 'IDD', 'International Calls (Japan)', 35.00),
('INV-2026-06-875', 'CUST-10042875', 'TAX', 'Taxes & Regulatory Fees', 17.50),
('INV-2026-06-876', 'CUST-10042876', 'PLAN', 'VIP Platinum Unlimited (monthly)', 150.00),
('INV-2026-06-876', 'CUST-10042876', 'ROAMING', 'Roaming Japan (7 days)', 90.00),
('INV-2026-06-876', 'CUST-10042876', 'TAX', 'Taxes & Regulatory Fees', 24.00),
('INV-2026-06-878', 'CUST-10042878', 'PLAN', 'Premium Unlimited (monthly)', 70.00),
('INV-2026-06-878', 'CUST-10042878', 'TAX', 'Taxes & Regulatory Fees', 7.00),
('INV-2026-06-879', 'CUST-10042879', 'PLAN', 'Value 5GB (monthly)', 40.00),
('INV-2026-06-879', 'CUST-10042879', 'IDD', 'International Calls (China)', 25.00),
('INV-2026-06-879', 'CUST-10042879', 'TAX', 'Taxes & Regulatory Fees', 6.50),
('INV-2026-06-880', 'CUST-10042880', 'PLAN', 'Premium Unlimited (monthly)', 70.00),
('INV-2026-06-880', 'CUST-10042880', 'ADDON', 'Data Add-on 10GB', 15.00),
('INV-2026-06-880', 'CUST-10042880', 'ROAMING', 'Roaming Canada (5 days)', 50.00),
('INV-2026-06-880', 'CUST-10042880', 'IDD', 'International Calls (Canada)', 10.00),
('INV-2026-06-880', 'CUST-10042880', 'TAX', 'Taxes & Regulatory Fees', 14.50),
('INV-2026-06-881', 'CUST-10042881', 'PLAN', 'Business Unlimited Pro (monthly)', 120.00),
('INV-2026-06-881', 'CUST-10042881', 'IDD', 'International Calls (UK / Germany)', 18.00),
('INV-2026-06-881', 'CUST-10042881', 'TAX', 'Taxes & Regulatory Fees', 13.80),
('INV-2026-06-883', 'CUST-10042883', 'PLAN', 'Essential 15GB (monthly)', 30.00),
('INV-2026-06-883', 'CUST-10042883', 'TAX', 'Taxes & Regulatory Fees', 3.00),
('INV-2026-06-884', 'CUST-10042884', 'PLAN', 'Premium Unlimited (monthly)', 70.00),
('INV-2026-06-884', 'CUST-10042884', 'ROAMING', 'Roaming Mexico (4 days)', 40.00),
('INV-2026-06-884', 'CUST-10042884', 'TAX', 'Taxes & Regulatory Fees', 11.00),
('INV-2026-06-885', 'CUST-10042885', 'PLAN', 'VIP Platinum Unlimited (monthly)', 150.00),
('INV-2026-06-885', 'CUST-10042885', 'ADDON', 'International Calling Pack', 20.00),
('INV-2026-06-885', 'CUST-10042885', 'ROAMING', 'Roaming Japan (9 days)', 110.00),
('INV-2026-06-885', 'CUST-10042885', 'IDD', 'International Calls (Japan)', 28.00),
('INV-2026-06-885', 'CUST-10042885', 'TAX', 'Taxes & Regulatory Fees', 30.80),
-- Wrong-charge line items (each contradicted by usage records below)
('INV-2026-06-887', 'CUST-10042887', 'PLAN', 'Value 5GB (monthly)', 40.00),
('INV-2026-06-887', 'CUST-10042887', 'ROAMING', 'Roaming Mexico (5 days)', 45.00),          -- WRONG: 0 roaming days
('INV-2026-06-887', 'CUST-10042887', 'TAX', 'Taxes & Regulatory Fees', 8.50),
('INV-2026-06-888', 'CUST-10042888', 'PLAN', 'Premium Unlimited (monthly)', 70.00),
('INV-2026-06-888', 'CUST-10042888', 'IDD', 'International Calls (India)', 38.00),           -- WRONG: 0 intl minutes
('INV-2026-06-888', 'CUST-10042888', 'TAX', 'Taxes & Regulatory Fees', 10.80),
('INV-2026-06-889', 'CUST-10042889', 'PLAN', 'Essential 15GB (monthly)', 30.00),
('INV-2026-06-889', 'CUST-10042889', 'PLAN', 'Essential 15GB (monthly)', 30.00),            -- WRONG: base plan billed twice
('INV-2026-06-889', 'CUST-10042889', 'TAX', 'Taxes & Regulatory Fees', 6.00),
('INV-2026-06-890', 'CUST-10042890', 'PLAN', 'Value 5GB (monthly)', 40.00),
('INV-2026-06-890', 'CUST-10042890', 'OTHER', 'Premium Content Subscription (GameZone Unlimited)', 19.99),  -- WRONG: never authorized
('INV-2026-06-890', 'CUST-10042890', 'TAX', 'Taxes & Regulatory Fees', 6.00),
('INV-2026-06-891', 'CUST-10042891', 'PLAN', 'Premium Unlimited (monthly)', 70.00),
('INV-2026-06-891', 'CUST-10042891', 'OTHER', 'Data Overage Charge (5GB over limit)', 30.00),  -- WRONG: usage under limit
('INV-2026-06-891', 'CUST-10042891', 'TAX', 'Taxes & Regulatory Fees', 10.00),
('INV-2026-06-892', 'CUST-10042892', 'PLAN', 'Essential 15GB (monthly)', 30.00),
('INV-2026-06-892', 'CUST-10042892', 'OTHER', 'Late Payment Fee', 10.00),                   -- WRONG: paid on time
('INV-2026-06-892', 'CUST-10042892', 'TAX', 'Taxes & Regulatory Fees', 4.00);

-- Usage Records (June 2026). Wrong-charge accounts show 0 roaming/intl or under-limit data to prove the discrepancy.
INSERT INTO usage_records (customer_id, billing_period, data_used_gb, data_limit_gb, local_call_minutes, intl_call_minutes, sms_count, roaming_days, roaming_country) VALUES
('CUST-10042871', 'June 2026', 38.70, 50.00, 342, 47, 12, 3, 'Mexico'),
('CUST-10042872', 'June 2026', 4.20, 5.00, 210, 0, 8, 0, NULL),
('CUST-10042873', 'June 2026', 19.60, 20.00, 88, 0, 3, 0, NULL),
('CUST-10042874', 'June 2026', 6.40, 10.00, 60, 0, 15, 0, NULL),
('CUST-10042875', 'June 2026', 72.50, 100.00, 540, 230, 45, 0, NULL),
('CUST-10042876', 'June 2026', 95.00, 9999.00, 320, 88, 20, 7, 'Japan'),
('CUST-10042877', 'June 2026', 3.10, 5.00, 40, 0, 5, 0, NULL),
('CUST-10042878', 'June 2026', 22.40, 50.00, 180, 12, 9, 0, NULL),
('CUST-10042879', 'June 2026', 15.20, 20.00, 130, 0, 6, 0, NULL),
('CUST-10042880', 'June 2026', 41.80, 50.00, 260, 95, 14, 5, 'Canada'),
('CUST-10042881', 'June 2026', 96.50, 100.00, 480, 60, 30, 0, NULL),
('CUST-10042882', 'June 2026', 8.50, 10.00, 70, 0, 20, 0, NULL),
('CUST-10042883', 'June 2026', 11.00, 15.00, 95, 0, 4, 0, NULL),
('CUST-10042884', 'June 2026', 28.30, 50.00, 150, 22, 7, 4, 'Mexico'),
('CUST-10042885', 'June 2026', 88.00, 9999.00, 410, 160, 25, 9, 'Japan'),
('CUST-10042886', 'June 2026', 2.80, 5.00, 35, 0, 8, 0, NULL),
('CUST-10042887', 'June 2026', 4.10, 5.00, 110, 0, 6, 0, NULL),
('CUST-10042888', 'June 2026', 30.50, 50.00, 240, 0, 10, 0, NULL),
('CUST-10042889', 'June 2026', 12.00, 15.00, 100, 0, 5, 0, NULL),
('CUST-10042890', 'June 2026', 4.80, 5.00, 85, 0, 12, 0, NULL),
('CUST-10042891', 'June 2026', 32.00, 50.00, 150, 0, 8, 0, NULL),
('CUST-10042892', 'June 2026', 9.50, 15.00, 70, 0, 6, 0, NULL);

-- Plans (base + add-ons)
INSERT INTO plans (customer_id, plan_name, plan_type, monthly_fee, data_allowance_gb, voice_minutes, status, start_date, expiry_date) VALUES
('CUST-10042871', 'Premium Unlimited', 'BASE', 70.00, 50.00, 9999, 'Active', '2019-03-15', NULL),
('CUST-10042871', 'Data Add-on 10GB', 'ADDON', 15.00, 10.00, 0, 'Active', CURRENT_DATE - INTERVAL '20 days', CURRENT_DATE + INTERVAL '10 days'),
('CUST-10042872', 'Value 5GB', 'BASE', 40.00, 5.00, 500, 'Active', '2021-07-22', NULL),
('CUST-10042873', 'Essential 15GB', 'BASE', 30.00, 15.00, 300, 'Active', '2020-11-05', NULL),
('CUST-10042873', 'Data Add-on 5GB', 'ADDON', 10.00, 5.00, 0, 'Active', CURRENT_DATE - INTERVAL '20 days', CURRENT_DATE + INTERVAL '10 days'),
('CUST-10042874', 'Prepaid Freedom', 'BASE', 35.00, 10.00, 500, 'Active', '2022-02-18', NULL),
('CUST-10042875', 'Business Unlimited Pro', 'BASE', 120.00, 100.00, 9999, 'Active', '2018-06-30', NULL),
('CUST-10042875', 'International Calling Pack', 'ADDON', 20.00, 0.00, 0, 'Active', CURRENT_DATE - INTERVAL '20 days', CURRENT_DATE + INTERVAL '10 days'),
('CUST-10042876', 'VIP Platinum Unlimited', 'BASE', 150.00, 9999.00, 9999, 'Active', '2017-09-12', NULL),
('CUST-10042877', 'Prepaid Super Saver', 'BASE', 20.00, 5.00, 200, 'Active', '2023-01-25', NULL),
('CUST-10042878', 'Premium Unlimited', 'BASE', 70.00, 50.00, 9999, 'Active', '2019-12-08', NULL),
('CUST-10042879', 'Value 5GB', 'BASE', 40.00, 5.00, 500, 'Active', '2020-05-14', NULL),
('CUST-10042880', 'Premium Unlimited', 'BASE', 70.00, 50.00, 9999, 'Active', '2018-10-02', NULL),
('CUST-10042880', 'Data Add-on 10GB', 'ADDON', 15.00, 10.00, 0, 'Active', CURRENT_DATE - INTERVAL '20 days', CURRENT_DATE + INTERVAL '10 days'),
('CUST-10042881', 'Business Unlimited Pro', 'BASE', 120.00, 100.00, 9999, 'Active', '2019-08-19', NULL),
('CUST-10042882', 'Prepaid Freedom', 'BASE', 35.00, 10.00, 500, 'Active', '2022-11-30', NULL),
('CUST-10042883', 'Essential 15GB', 'BASE', 30.00, 15.00, 300, 'Active', '2021-03-08', NULL),
('CUST-10042884', 'Premium Unlimited', 'BASE', 70.00, 50.00, 9999, 'Active', '2020-01-27', NULL),
('CUST-10042885', 'VIP Platinum Unlimited', 'BASE', 150.00, 9999.00, 9999, 'Active', '2016-04-11', NULL),
('CUST-10042885', 'International Calling Pack', 'ADDON', 20.00, 0.00, 0, 'Active', CURRENT_DATE - INTERVAL '20 days', CURRENT_DATE + INTERVAL '10 days'),
('CUST-10042886', 'Prepaid Super Saver', 'BASE', 20.00, 5.00, 200, 'Active', '2023-06-05', NULL),
('CUST-10042887', 'Value 5GB', 'BASE', 40.00, 5.00, 500, 'Active', '2021-05-10', NULL),
('CUST-10042888', 'Premium Unlimited', 'BASE', 70.00, 50.00, 9999, 'Active', '2020-08-14', NULL),
('CUST-10042889', 'Essential 15GB', 'BASE', 30.00, 15.00, 300, 'Active', '2022-03-22', NULL),
('CUST-10042890', 'Value 5GB', 'BASE', 40.00, 5.00, 500, 'Active', '2021-09-01', NULL),
('CUST-10042891', 'Premium Unlimited', 'BASE', 70.00, 50.00, 9999, 'Active', '2019-11-19', NULL),
('CUST-10042892', 'Essential 15GB', 'BASE', 30.00, 15.00, 300, 'Active', '2022-06-05', NULL);

-- Payments (dates relative to today). US payment methods, USD.
INSERT INTO payments (customer_id, payment_date, amount, currency, method, status, reference_number, invoice_id) VALUES
('CUST-10042871', CURRENT_DATE - INTERVAL '3 days', 138.60, 'USD', 'Auto-Pay', 'Success', 'PAY-2026-87101', 'INV-2026-05-871'),
('CUST-10042871', CURRENT_DATE - INTERVAL '33 days', 141.90, 'USD', 'Auto-Pay', 'Success', 'PAY-2026-87102', 'INV-2026-04-871'),
('CUST-10042871', CURRENT_DATE - INTERVAL '63 days', 135.30, 'USD', 'Credit Card', 'Success', 'PAY-2026-87103', 'INV-2026-03-871'),
('CUST-10042872', CURRENT_DATE - INTERVAL '4 days', 44.00, 'USD', 'Credit Card', 'Success', 'PAY-2026-87201', 'INV-2026-05-872'),
('CUST-10042872', CURRENT_DATE - INTERVAL '34 days', 44.00, 'USD', 'Bank Transfer', 'Success', 'PAY-2026-87202', 'INV-2026-04-872'),
('CUST-10042873', CURRENT_DATE - INTERVAL '2 days', 44.00, 'USD', 'PayPal', 'Success', 'PAY-2026-87301', 'INV-2026-05-873'),
('CUST-10042873', CURRENT_DATE - INTERVAL '32 days', 44.00, 'USD', 'PayPal', 'Success', 'PAY-2026-87302', 'INV-2026-04-873'),
('CUST-10042874', CURRENT_DATE - INTERVAL '5 days', 35.00, 'USD', 'Debit Card', 'Success', 'PAY-2026-87401', NULL),
('CUST-10042874', CURRENT_DATE - INTERVAL '20 days', 35.00, 'USD', 'Debit Card', 'Success', 'PAY-2026-87402', NULL),
('CUST-10042875', CURRENT_DATE - INTERVAL '3 days', 192.50, 'USD', 'Auto-Pay', 'Success', 'PAY-2026-87501', 'INV-2026-05-875'),
('CUST-10042875', CURRENT_DATE - INTERVAL '33 days', 188.10, 'USD', 'Auto-Pay', 'Success', 'PAY-2026-87502', 'INV-2026-04-875'),
('CUST-10042875', CURRENT_DATE - INTERVAL '63 days', 190.30, 'USD', 'Auto-Pay', 'Success', 'PAY-2026-87503', 'INV-2026-03-875'),
('CUST-10042875', CURRENT_DATE - INTERVAL '93 days', 185.80, 'USD', 'Bank Transfer', 'Success', 'PAY-2026-87504', 'INV-2026-02-875'),
('CUST-10042875', CURRENT_DATE - INTERVAL '123 days', 191.40, 'USD', 'Credit Card', 'Success', 'PAY-2026-87505', 'INV-2026-01-875'),
('CUST-10042876', CURRENT_DATE - INTERVAL '3 days', 181.50, 'USD', 'Auto-Pay', 'Success', 'PAY-2026-87601', 'INV-2026-05-876'),
('CUST-10042876', CURRENT_DATE - INTERVAL '34 days', 179.30, 'USD', 'Auto-Pay', 'Success', 'PAY-2026-87602', 'INV-2026-04-876'),
('CUST-10042876', CURRENT_DATE - INTERVAL '64 days', 180.40, 'USD', 'Credit Card', 'Success', 'PAY-2026-87603', 'INV-2026-03-876'),
('CUST-10042877', CURRENT_DATE - INTERVAL '1 days', 20.00, 'USD', 'Apple Pay', 'Success', 'PAY-2026-87701', NULL),
('CUST-10042877', CURRENT_DATE - INTERVAL '18 days', 20.00, 'USD', 'Apple Pay', 'Success', 'PAY-2026-87702', NULL),
('CUST-10042878', CURRENT_DATE - INTERVAL '6 days', 77.00, 'USD', 'Credit Card', 'Success', 'PAY-2026-87801', 'INV-2026-05-878'),
('CUST-10042878', CURRENT_DATE - INTERVAL '36 days', 77.00, 'USD', 'Credit Card', 'Success', 'PAY-2026-87802', 'INV-2026-04-878'),
('CUST-10042879', CURRENT_DATE - INTERVAL '4 days', 44.00, 'USD', 'Bank Transfer', 'Success', 'PAY-2026-87901', 'INV-2026-05-879'),
('CUST-10042879', CURRENT_DATE - INTERVAL '34 days', 44.00, 'USD', 'Bank Transfer', 'Success', 'PAY-2026-87902', 'INV-2026-04-879'),
('CUST-10042880', CURRENT_DATE - INTERVAL '3 days', 93.50, 'USD', 'Auto-Pay', 'Success', 'PAY-2026-88001', 'INV-2026-05-880'),
('CUST-10042880', CURRENT_DATE - INTERVAL '33 days', 93.50, 'USD', 'Auto-Pay', 'Success', 'PAY-2026-88002', 'INV-2026-04-880'),
('CUST-10042881', CURRENT_DATE - INTERVAL '2 days', 151.80, 'USD', 'Auto-Pay', 'Success', 'PAY-2026-88101', 'INV-2026-05-881'),
('CUST-10042881', CURRENT_DATE - INTERVAL '32 days', 148.50, 'USD', 'Auto-Pay', 'Success', 'PAY-2026-88102', 'INV-2026-04-881'),
('CUST-10042881', CURRENT_DATE - INTERVAL '62 days', 150.70, 'USD', 'Bank Transfer', 'Success', 'PAY-2026-88103', 'INV-2026-03-881'),
('CUST-10042882', CURRENT_DATE - INTERVAL '5 days', 35.00, 'USD', 'Google Pay', 'Success', 'PAY-2026-88201', NULL),
('CUST-10042883', CURRENT_DATE - INTERVAL '3 days', 33.00, 'USD', 'PayPal', 'Success', 'PAY-2026-88301', 'INV-2026-05-883'),
('CUST-10042883', CURRENT_DATE - INTERVAL '33 days', 33.00, 'USD', 'PayPal', 'Success', 'PAY-2026-88302', 'INV-2026-04-883'),
('CUST-10042884', CURRENT_DATE - INTERVAL '4 days', 77.00, 'USD', 'Credit Card', 'Success', 'PAY-2026-88401', 'INV-2026-05-884'),
('CUST-10042884', CURRENT_DATE - INTERVAL '34 days', 77.00, 'USD', 'Credit Card', 'Success', 'PAY-2026-88402', 'INV-2026-04-884'),
('CUST-10042885', CURRENT_DATE - INTERVAL '3 days', 187.00, 'USD', 'Auto-Pay', 'Success', 'PAY-2026-88501', 'INV-2026-05-885'),
('CUST-10042885', CURRENT_DATE - INTERVAL '33 days', 187.00, 'USD', 'Auto-Pay', 'Success', 'PAY-2026-88502', 'INV-2026-04-885'),
('CUST-10042885', CURRENT_DATE - INTERVAL '63 days', 190.00, 'USD', 'Auto-Pay', 'Success', 'PAY-2026-88503', 'INV-2026-03-885'),
('CUST-10042885', CURRENT_DATE - INTERVAL '93 days', 185.00, 'USD', 'Credit Card', 'Success', 'PAY-2026-88504', 'INV-2026-02-885'),
('CUST-10042886', CURRENT_DATE - INTERVAL '1 days', 20.00, 'USD', 'Apple Pay', 'Success', 'PAY-2026-88601', NULL),
('CUST-10042887', CURRENT_DATE - INTERVAL '4 days', 44.00, 'USD', 'Credit Card', 'Success', 'PAY-2026-88701', 'INV-2026-05-887'),
('CUST-10042887', CURRENT_DATE - INTERVAL '34 days', 44.00, 'USD', 'Credit Card', 'Success', 'PAY-2026-88702', 'INV-2026-04-887'),
('CUST-10042888', CURRENT_DATE - INTERVAL '5 days', 77.00, 'USD', 'Auto-Pay', 'Success', 'PAY-2026-88801', 'INV-2026-05-888'),
('CUST-10042888', CURRENT_DATE - INTERVAL '35 days', 77.00, 'USD', 'Auto-Pay', 'Success', 'PAY-2026-88802', 'INV-2026-04-888'),
('CUST-10042889', CURRENT_DATE - INTERVAL '3 days', 33.00, 'USD', 'PayPal', 'Success', 'PAY-2026-88901', 'INV-2026-05-889'),
('CUST-10042889', CURRENT_DATE - INTERVAL '33 days', 33.00, 'USD', 'PayPal', 'Success', 'PAY-2026-88902', 'INV-2026-04-889'),
('CUST-10042890', CURRENT_DATE - INTERVAL '4 days', 44.00, 'USD', 'Debit Card', 'Success', 'PAY-2026-89001', 'INV-2026-05-890'),
('CUST-10042890', CURRENT_DATE - INTERVAL '34 days', 44.00, 'USD', 'Debit Card', 'Success', 'PAY-2026-89002', 'INV-2026-04-890'),
('CUST-10042891', CURRENT_DATE - INTERVAL '3 days', 77.00, 'USD', 'Auto-Pay', 'Success', 'PAY-2026-89101', 'INV-2026-05-891'),
('CUST-10042891', CURRENT_DATE - INTERVAL '33 days', 77.00, 'USD', 'Auto-Pay', 'Success', 'PAY-2026-89102', 'INV-2026-04-891'),
('CUST-10042892', CURRENT_DATE - INTERVAL '25 days', 33.00, 'USD', 'Auto-Pay', 'Success', 'PAY-2026-89201', 'INV-2026-05-892'),
('CUST-10042892', CURRENT_DATE - INTERVAL '34 days', 33.00, 'USD', 'Auto-Pay', 'Success', 'PAY-2026-89202', 'INV-2026-04-892');

-- Recharge Offers (global catalog, USD)
INSERT INTO recharge_offers (offer_id, offer_name, offer_type, price, currency, data_amount_gb, validity_days, description) VALUES
('OFF-DATA-5GB', 'Data Booster 5GB', 'DATA', 10.00, 'USD', 5.00, 30, '5GB high-speed data valid for 30 days'),
('OFF-DATA-10GB', 'Data Booster 10GB', 'DATA', 15.00, 'USD', 10.00, 30, '10GB high-speed data valid for 30 days'),
('OFF-DATA-25GB', 'Data Max 25GB', 'DATA', 30.00, 'USD', 25.00, 30, '25GB high-speed data valid for 30 days'),
('OFF-DATA-50GB', 'Data Jumbo 50GB', 'DATA', 50.00, 'USD', 50.00, 30, '50GB high-speed data valid for 30 days'),
('OFF-IDD-INTL', 'IDD International 100 min', 'IDD', 15.00, 'USD', 0.00, 30, '100 international minutes valid for 30 days'),
('OFF-ROAM-NA', 'Roaming North America 3-Day Pass', 'ROAMING', 30.00, 'USD', 3.00, 3, 'Unlimited US/Canada/Mexico roaming calls + 3GB data for 3 days'),
('OFF-ROAM-INTL', 'Roaming International 5-Day Pass', 'ROAMING', 60.00, 'USD', 5.00, 5, 'International roaming calls + 5GB data for 5 days'),
('OFF-COMBO-SOCIAL', 'Combo Social', 'COMBO', 20.00, 'USD', 15.00, 30, '15GB data + unlimited social media valid for 30 days');

-- Disputes (timestamps relative to today)
INSERT INTO disputes (dispute_id, customer_id, invoice_id, reason, status, created_at, estimated_resolution, last_update, resolution) VALUES
('DSP-2026-0001', 'CUST-10042876', 'INV-2026-05-876', 'Disputed premium content SMS charges of USD 25.00 not recognized by customer', 'UNDER_REVIEW', CURRENT_DATE - INTERVAL '12 days', CURRENT_DATE + INTERVAL '3 days', CURRENT_DATE - INTERVAL '2 days', NULL),
('DSP-2026-0002', 'CUST-10042883', 'INV-2026-04-883', 'Incorrect late payment fee applied', 'RESOLVED', CURRENT_DATE - INTERVAL '40 days', CURRENT_DATE - INTERVAL '33 days', CURRENT_DATE - INTERVAL '35 days', 'Late payment fee of USD 10.00 waived and credited to the account.'),
('DSP-2026-0003', 'CUST-10042873', 'INV-2026-05-873', 'Data add-on charged twice on the same billing cycle', 'OPEN', CURRENT_DATE - INTERVAL '5 days', CURRENT_DATE + INTERVAL '5 days', CURRENT_DATE - INTERVAL '5 days', NULL);

-- Recharges: intentionally left empty (populated by the recharge_agent at runtime).
