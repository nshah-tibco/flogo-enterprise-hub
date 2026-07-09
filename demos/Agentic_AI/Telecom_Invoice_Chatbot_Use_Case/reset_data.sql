-- Telecom Invoice Chatbot — Reset Demo Data (Indonesian provider, IDR)
-- Restores a clean demo state (undoes agent writes) with today-relative dates.
-- PostgreSQL 14+

TRUNCATE recharges, disputes, recharge_offers, payments, plans, usage_records,
         invoice_line_items, invoices, customers RESTART IDENTITY CASCADE;

-- Customers
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

-- Invoices (due dates relative to today)
INSERT INTO invoices (invoice_id, customer_id, billing_month, period_start, period_end, subtotal, tax, total_amount, currency, due_date, status) VALUES
('INV-2026-06-871', 'CUST-10042871', 'June 2026', '2026-06-01', '2026-06-30', 450000.00, 49500.00, 499500.00, 'IDR', CURRENT_DATE + INTERVAL '7 days', 'Unpaid'),
('INV-2026-06-872', 'CUST-10042872', 'June 2026', '2026-06-01', '2026-06-30', 320000.00, 35200.00, 355200.00, 'IDR', CURRENT_DATE + INTERVAL '7 days', 'Unpaid'),
('INV-2026-06-873', 'CUST-10042873', 'June 2026', '2026-06-01', '2026-06-30', 105000.00, 11550.00, 116550.00, 'IDR', CURRENT_DATE + INTERVAL '7 days', 'Unpaid'),
('INV-2026-06-875', 'CUST-10042875', 'June 2026', '2026-06-01', '2026-06-30', 635000.00, 69850.00, 704850.00, 'IDR', CURRENT_DATE + INTERVAL '7 days', 'Unpaid'),
('INV-2026-06-876', 'CUST-10042876', 'June 2026', '2026-06-01', '2026-06-30', 1130000.00, 124300.00, 1254300.00, 'IDR', CURRENT_DATE + INTERVAL '7 days', 'Unpaid'),
('INV-2026-06-878', 'CUST-10042878', 'June 2026', '2026-06-01', '2026-06-30', 150000.00, 16500.00, 166500.00, 'IDR', CURRENT_DATE + INTERVAL '7 days', 'Unpaid'),
('INV-2026-06-879', 'CUST-10042879', 'June 2026', '2026-06-01', '2026-06-30', 195000.00, 21450.00, 216450.00, 'IDR', CURRENT_DATE + INTERVAL '7 days', 'Unpaid'),
('INV-2026-06-880', 'CUST-10042880', 'June 2026', '2026-06-01', '2026-06-30', 570000.00, 62700.00, 632700.00, 'IDR', CURRENT_DATE + INTERVAL '7 days', 'Unpaid'),
('INV-2026-06-881', 'CUST-10042881', 'June 2026', '2026-06-01', '2026-06-30', 490000.00, 53900.00, 543900.00, 'IDR', CURRENT_DATE + INTERVAL '7 days', 'Unpaid'),
('INV-2026-06-883', 'CUST-10042883', 'June 2026', '2026-06-01', '2026-06-30', 75000.00, 8250.00, 83250.00, 'IDR', CURRENT_DATE + INTERVAL '7 days', 'Unpaid'),
('INV-2026-06-884', 'CUST-10042884', 'June 2026', '2026-06-01', '2026-06-30', 330000.00, 36300.00, 366300.00, 'IDR', CURRENT_DATE + INTERVAL '7 days', 'Unpaid'),
('INV-2026-06-885', 'CUST-10042885', 'June 2026', '2026-06-01', '2026-06-30', 1445000.00, 158950.00, 1603950.00, 'IDR', CURRENT_DATE + INTERVAL '7 days', 'Unpaid');

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

-- Usage Records
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

-- Plans
INSERT INTO plans (customer_id, plan_name, plan_type, monthly_fee, data_allowance_gb, voice_minutes, status, start_date, expiry_date) VALUES
('CUST-10042871', 'Pascabayar Prime 100', 'BASE', 150000.00, 40.00, 500, 'Active', '2019-03-15', NULL),
('CUST-10042871', 'Data Add-on 10GB', 'ADDON', 50000.00, 10.00, 0, 'Active', CURRENT_DATE - INTERVAL '20 days', CURRENT_DATE + INTERVAL '10 days'),
('CUST-10042872', 'Pascabayar Value 50', 'BASE', 100000.00, 20.00, 200, 'Active', '2021-07-22', NULL),
('CUST-10042873', 'Pascabayar Smart 30', 'BASE', 75000.00, 15.00, 100, 'Active', '2020-11-05', NULL),
('CUST-10042873', 'Data Add-on 5GB', 'ADDON', 30000.00, 5.00, 0, 'Active', CURRENT_DATE - INTERVAL '20 days', CURRENT_DATE + INTERVAL '10 days'),
('CUST-10042874', 'Prabayar Freedom', 'BASE', 50000.00, 10.00, 100, 'Active', '2022-02-18', NULL),
('CUST-10042875', 'Business Unlimited Pro', 'BASE', 400000.00, 100.00, 9999, 'Active', '2018-06-30', NULL),
('CUST-10042875', 'IDD SLI Pack', 'ADDON', 60000.00, 0.00, 0, 'Active', CURRENT_DATE - INTERVAL '20 days', CURRENT_DATE + INTERVAL '10 days'),
('CUST-10042876', 'VIP Platinum Unlimited', 'BASE', 750000.00, 9999.00, 9999, 'Active', '2017-09-12', NULL),
('CUST-10042877', 'Prabayar Super Hemat', 'BASE', 25000.00, 5.00, 60, 'Active', '2023-01-25', NULL),
('CUST-10042878', 'Pascabayar Prime 100', 'BASE', 150000.00, 40.00, 500, 'Active', '2019-12-08', NULL),
('CUST-10042879', 'Pascabayar Value 50', 'BASE', 100000.00, 20.00, 200, 'Active', '2020-05-14', NULL),
('CUST-10042880', 'Pascabayar Prime 100', 'BASE', 150000.00, 40.00, 500, 'Active', '2018-10-02', NULL),
('CUST-10042880', 'Data Add-on 10GB', 'ADDON', 50000.00, 10.00, 0, 'Active', CURRENT_DATE - INTERVAL '20 days', CURRENT_DATE + INTERVAL '10 days'),
('CUST-10042881', 'Business Unlimited Pro', 'BASE', 400000.00, 100.00, 9999, 'Active', '2019-08-19', NULL),
('CUST-10042882', 'Prabayar Freedom', 'BASE', 50000.00, 10.00, 100, 'Active', '2022-11-30', NULL),
('CUST-10042883', 'Pascabayar Smart 30', 'BASE', 75000.00, 15.00, 100, 'Active', '2021-03-08', NULL),
('CUST-10042884', 'Pascabayar Prime 100', 'BASE', 150000.00, 40.00, 500, 'Active', '2020-01-27', NULL),
('CUST-10042885', 'VIP Platinum Unlimited', 'BASE', 750000.00, 9999.00, 9999, 'Active', '2016-04-11', NULL),
('CUST-10042885', 'IDD SLI Pack', 'ADDON', 60000.00, 0.00, 0, 'Active', CURRENT_DATE - INTERVAL '20 days', CURRENT_DATE + INTERVAL '10 days'),
('CUST-10042886', 'Prabayar Super Hemat', 'BASE', 25000.00, 5.00, 60, 'Active', '2023-06-05', NULL);

-- Payments (dates relative to today)
INSERT INTO payments (customer_id, payment_date, amount, currency, method, status, reference_number, invoice_id) VALUES
('CUST-10042871', CURRENT_DATE - INTERVAL '3 days', 480000.00, 'IDR', 'Auto-Debit', 'Success', 'PAY-2026-87101', 'INV-2026-05-871'),
('CUST-10042871', CURRENT_DATE - INTERVAL '33 days', 465000.00, 'IDR', 'Auto-Debit', 'Success', 'PAY-2026-87102', 'INV-2026-04-871'),
('CUST-10042871', CURRENT_DATE - INTERVAL '63 days', 450000.00, 'IDR', 'Credit Card', 'Success', 'PAY-2026-87103', 'INV-2026-03-871'),
('CUST-10042872', CURRENT_DATE - INTERVAL '4 days', 340000.00, 'IDR', 'GoPay', 'Success', 'PAY-2026-87201', 'INV-2026-05-872'),
('CUST-10042872', CURRENT_DATE - INTERVAL '34 days', 335000.00, 'IDR', 'Bank Transfer', 'Success', 'PAY-2026-87202', 'INV-2026-04-872'),
('CUST-10042873', CURRENT_DATE - INTERVAL '2 days', 116000.00, 'IDR', 'OVO', 'Success', 'PAY-2026-87301', 'INV-2026-05-873'),
('CUST-10042873', CURRENT_DATE - INTERVAL '32 days', 110000.00, 'IDR', 'OVO', 'Success', 'PAY-2026-87302', 'INV-2026-04-873'),
('CUST-10042874', CURRENT_DATE - INTERVAL '5 days', 50000.00, 'IDR', 'GoPay', 'Success', 'PAY-2026-87401', NULL),
('CUST-10042874', CURRENT_DATE - INTERVAL '20 days', 50000.00, 'IDR', 'GoPay', 'Success', 'PAY-2026-87402', NULL),
('CUST-10042875', CURRENT_DATE - INTERVAL '3 days', 700000.00, 'IDR', 'Auto-Debit', 'Success', 'PAY-2026-87501', 'INV-2026-05-875'),
('CUST-10042875', CURRENT_DATE - INTERVAL '33 days', 690000.00, 'IDR', 'Auto-Debit', 'Success', 'PAY-2026-87502', 'INV-2026-04-875'),
('CUST-10042875', CURRENT_DATE - INTERVAL '63 days', 710000.00, 'IDR', 'Auto-Debit', 'Success', 'PAY-2026-87503', 'INV-2026-03-875'),
('CUST-10042875', CURRENT_DATE - INTERVAL '93 days', 680000.00, 'IDR', 'Virtual Account', 'Success', 'PAY-2026-87504', 'INV-2026-02-875'),
('CUST-10042875', CURRENT_DATE - INTERVAL '123 days', 695000.00, 'IDR', 'Credit Card', 'Success', 'PAY-2026-87505', 'INV-2026-01-875'),
('CUST-10042876', CURRENT_DATE - INTERVAL '3 days', 1250000.00, 'IDR', 'Auto-Debit', 'Success', 'PAY-2026-87601', 'INV-2026-05-876'),
('CUST-10042876', CURRENT_DATE - INTERVAL '34 days', 1200000.00, 'IDR', 'Auto-Debit', 'Success', 'PAY-2026-87602', 'INV-2026-04-876'),
('CUST-10042876', CURRENT_DATE - INTERVAL '64 days', 1230000.00, 'IDR', 'Credit Card', 'Success', 'PAY-2026-87603', 'INV-2026-03-876'),
('CUST-10042877', CURRENT_DATE - INTERVAL '1 days', 25000.00, 'IDR', 'DANA', 'Success', 'PAY-2026-87701', NULL),
('CUST-10042877', CURRENT_DATE - INTERVAL '18 days', 25000.00, 'IDR', 'DANA', 'Success', 'PAY-2026-87702', NULL),
('CUST-10042878', CURRENT_DATE - INTERVAL '6 days', 166000.00, 'IDR', 'Credit Card', 'Success', 'PAY-2026-87801', 'INV-2026-05-878'),
('CUST-10042878', CURRENT_DATE - INTERVAL '36 days', 160000.00, 'IDR', 'Credit Card', 'Success', 'PAY-2026-87802', 'INV-2026-04-878'),
('CUST-10042879', CURRENT_DATE - INTERVAL '4 days', 210000.00, 'IDR', 'Bank Transfer', 'Success', 'PAY-2026-87901', 'INV-2026-05-879'),
('CUST-10042879', CURRENT_DATE - INTERVAL '34 days', 205000.00, 'IDR', 'Bank Transfer', 'Success', 'PAY-2026-87902', 'INV-2026-04-879'),
('CUST-10042880', CURRENT_DATE - INTERVAL '3 days', 630000.00, 'IDR', 'Auto-Debit', 'Success', 'PAY-2026-88001', 'INV-2026-05-880'),
('CUST-10042880', CURRENT_DATE - INTERVAL '33 days', 610000.00, 'IDR', 'Auto-Debit', 'Success', 'PAY-2026-88002', 'INV-2026-04-880'),
('CUST-10042881', CURRENT_DATE - INTERVAL '2 days', 540000.00, 'IDR', 'Auto-Debit', 'Success', 'PAY-2026-88101', 'INV-2026-05-881'),
('CUST-10042881', CURRENT_DATE - INTERVAL '32 days', 520000.00, 'IDR', 'Auto-Debit', 'Success', 'PAY-2026-88102', 'INV-2026-04-881'),
('CUST-10042881', CURRENT_DATE - INTERVAL '62 days', 535000.00, 'IDR', 'Virtual Account', 'Success', 'PAY-2026-88103', 'INV-2026-03-881'),
('CUST-10042882', CURRENT_DATE - INTERVAL '5 days', 50000.00, 'IDR', 'GoPay', 'Success', 'PAY-2026-88201', NULL),
('CUST-10042883', CURRENT_DATE - INTERVAL '3 days', 83000.00, 'IDR', 'OVO', 'Success', 'PAY-2026-88301', 'INV-2026-05-883'),
('CUST-10042883', CURRENT_DATE - INTERVAL '33 days', 80000.00, 'IDR', 'OVO', 'Success', 'PAY-2026-88302', 'INV-2026-04-883'),
('CUST-10042884', CURRENT_DATE - INTERVAL '4 days', 366000.00, 'IDR', 'Credit Card', 'Success', 'PAY-2026-88401', 'INV-2026-05-884'),
('CUST-10042884', CURRENT_DATE - INTERVAL '34 days', 350000.00, 'IDR', 'Credit Card', 'Success', 'PAY-2026-88402', 'INV-2026-04-884'),
('CUST-10042885', CURRENT_DATE - INTERVAL '3 days', 1600000.00, 'IDR', 'Auto-Debit', 'Success', 'PAY-2026-88501', 'INV-2026-05-885'),
('CUST-10042885', CURRENT_DATE - INTERVAL '33 days', 1550000.00, 'IDR', 'Auto-Debit', 'Success', 'PAY-2026-88502', 'INV-2026-04-885'),
('CUST-10042885', CURRENT_DATE - INTERVAL '63 days', 1580000.00, 'IDR', 'Auto-Debit', 'Success', 'PAY-2026-88503', 'INV-2026-03-885'),
('CUST-10042885', CURRENT_DATE - INTERVAL '93 days', 1520000.00, 'IDR', 'Credit Card', 'Success', 'PAY-2026-88504', 'INV-2026-02-885'),
('CUST-10042886', CURRENT_DATE - INTERVAL '1 days', 25000.00, 'IDR', 'DANA', 'Success', 'PAY-2026-88601', NULL);

-- Recharge Offers
INSERT INTO recharge_offers (offer_id, offer_name, offer_type, price, currency, data_amount_gb, validity_days, description) VALUES
('OFF-DATA-5GB', 'Data Booster 5GB', 'DATA', 30000.00, 'IDR', 5.00, 30, '5GB high-speed data valid for 30 days'),
('OFF-DATA-10GB', 'Data Booster 10GB', 'DATA', 50000.00, 'IDR', 10.00, 30, '10GB high-speed data valid for 30 days'),
('OFF-DATA-25GB', 'Data Max 25GB', 'DATA', 100000.00, 'IDR', 25.00, 30, '25GB high-speed data valid for 30 days'),
('OFF-DATA-50GB', 'Data Jumbo 50GB', 'DATA', 175000.00, 'IDR', 50.00, 30, '50GB high-speed data valid for 30 days'),
('OFF-IDD-ASIA', 'IDD Asia 100 min', 'IDD', 45000.00, 'IDR', 0.00, 30, '100 international minutes to Asia valid for 30 days'),
('OFF-ROAM-ASEAN', 'Roaming ASEAN 3-Day Pass', 'ROAMING', 150000.00, 'IDR', 3.00, 3, 'Unlimited ASEAN roaming calls + 3GB data for 3 days'),
('OFF-ROAM-JAPAN', 'Roaming Japan 5-Day Pass', 'ROAMING', 350000.00, 'IDR', 5.00, 5, 'Japan roaming calls + 5GB data for 5 days'),
('OFF-COMBO-SOCIAL', 'Combo Sakti Social', 'COMBO', 65000.00, 'IDR', 15.00, 30, '15GB data + unlimited social media valid for 30 days');

-- Disputes (timestamps relative to today)
INSERT INTO disputes (dispute_id, customer_id, invoice_id, reason, status, created_at, estimated_resolution, last_update, resolution) VALUES
('DSP-2026-0001', 'CUST-10042876', 'INV-2026-05-876', 'Disputed premium content SMS charges of IDR 45,000 not recognised by customer', 'UNDER_REVIEW', CURRENT_DATE - INTERVAL '12 days', CURRENT_DATE + INTERVAL '3 days', CURRENT_DATE - INTERVAL '2 days', NULL),
('DSP-2026-0002', 'CUST-10042883', 'INV-2026-04-883', 'Incorrect late payment fee applied', 'RESOLVED', CURRENT_DATE - INTERVAL '40 days', CURRENT_DATE - INTERVAL '33 days', CURRENT_DATE - INTERVAL '35 days', 'Late payment fee of IDR 25,000 waived and credited to the account.'),
('DSP-2026-0003', 'CUST-10042873', 'INV-2026-05-873', 'Data add-on charged twice on the same billing cycle', 'OPEN', CURRENT_DATE - INTERVAL '5 days', CURRENT_DATE + INTERVAL '5 days', CURRENT_DATE - INTERVAL '5 days', NULL);

-- Recharges: intentionally left empty (populated by the recharge_agent at runtime).
