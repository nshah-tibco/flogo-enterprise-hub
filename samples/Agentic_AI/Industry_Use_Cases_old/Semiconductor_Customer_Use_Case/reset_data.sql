-- =====================================================================
-- Semiconductor Customer & Order Assistant — RESET script
-- Restores a clean, current-dated demo baseline and undoes agent writes.
-- Run before each demo run:  psql -U postgres -d semiconductor -f reset_data.sql
--
-- Volatile dates are CURRENT_DATE-relative so the demo always looks current.
-- Agent-written tables: rma_cases + sample_requests are re-seeded to their
-- single baseline row; alert_subscriptions is left EMPTY.
-- =====================================================================

TRUNCATE alert_subscriptions, sample_requests, rma_cases, cross_references,
         pcn_notices, order_lines, orders, price_breaks, inventory,
         products, customers
    RESTART IDENTITY CASCADE;

-- customers (7) ------------------------------------------------------
INSERT INTO customers (customer_id, company_name, contact_name, email, phone, region, industry, account_tier, currency, credit_status) VALUES
 ('CUST-10001','Aurora Automotive Systems','Lena Vogt','lena.vogt@aurora-auto.example.com','+49-511-555-0142','EMEA','Automotive','Direct-Gold','USD','Good'),
 ('CUST-10002','Shenzhen PowerTech','Wei Chen','wei.chen@szpowertech.example.com','+86-755-5550-118','APAC','Industrial','Direct-Silver','USD','Good'),
 ('CUST-10003','Innolux Consumer Devices','Hana Sato','hana.sato@innolux-cd.example.com','+81-3-5550-7781','APAC','Consumer','Distributor','USD','Good'),
 ('CUST-10004','Helios Renewable Energy','Marcus Reed','marcus.reed@helios-energy.example.com','+1-408-555-0193','Americas','Energy','Direct-Gold','USD','Good'),
 ('CUST-10005','Meridian Medical Devices','Priya Nair','priya.nair@meridian-med.example.com','+1-617-555-0166','Americas','Medical','Direct-Silver','USD','Good'),
 ('CUST-10006','Baltic Drives','Erik Laine','erik.laine@baltic-drives.example.com','+372-555-2210','EMEA','Industrial','Direct-Bronze','USD','Good'),
 ('CUST-10007','Copperline Robotics','Diego Alvarez','diego.alvarez@copperline.example.com','+1-512-555-0177','Americas','Industrial','Distributor','USD','Good');

-- products (10) ------------------------------------------------------
INSERT INTO products (part_number, description, category, package, automotive_qualified, aec_qualification, rohs_compliant, lifecycle_status, moq, unit_price_ref, datasheet_url) VALUES
 ('TMN4010Q','Automotive N-channel Trench MOSFET 40V 100A','MOSFET','LFPAK56',TRUE,'AEC-Q101',TRUE,'Active',100,1.8500,'https://datasheets.example.com/TMN4010Q.pdf'),
 ('SBD3020EP','Schottky Barrier Rectifier 30V 2A','Schottky Rectifier','CFP3',FALSE,NULL,TRUE,'Active',1000,0.2200,'https://datasheets.example.com/SBD3020EP.pdf'),
 ('PMN8033YS','Power MOSFET 80V 3.3 mOhm','MOSFET','LFPAK56',FALSE,NULL,TRUE,'Active',100,2.4000,'https://datasheets.example.com/PMN8033YS.pdf'),
 ('74LVC1G08','Single 2-input AND gate, low-voltage CMOS','Logic Gate','TSSOP-5',FALSE,NULL,TRUE,'Active',1000,0.1100,'https://datasheets.example.com/74LVC1G08.pdf'),
 ('ESD1CANQ','Automotive CAN-bus ESD Protection Diode','ESD Protection','SOT23',TRUE,'AEC-Q101',TRUE,'Active',1000,0.3400,'https://datasheets.example.com/ESD1CANQ.pdf'),
 ('BC847BW','NPN General-Purpose Transistor 45V 100mA','Bipolar Transistor','SOT323',FALSE,NULL,TRUE,'NRND',1000,0.0600,'https://datasheets.example.com/BC847BW.pdf'),
 ('SBD2010A','Schottky Barrier Rectifier 20V 1A','Schottky Rectifier','SOD123',FALSE,NULL,TRUE,'EOL',1000,0.1900,'https://datasheets.example.com/SBD2010A.pdf'),
 ('74AHC1G14','Schmitt-Trigger Inverter, advanced high-speed CMOS','Logic Gate','SOT353',FALSE,NULL,TRUE,'Active',1000,0.1300,'https://datasheets.example.com/74AHC1G14.pdf'),
 ('GAN65R060','650V GaN Power FET 60 mOhm','GaN FET','GaNPAK',FALSE,NULL,TRUE,'Active',50,8.5000,'https://datasheets.example.com/GAN65R060.pdf'),
 ('TMN2508','Small-Signal N-channel MOSFET 25V 8A','MOSFET','SOT23',FALSE,NULL,TRUE,'Active',1000,0.2800,'https://datasheets.example.com/TMN2508.pdf');

-- inventory (14) -----------------------------------------------------
INSERT INTO inventory (part_number, warehouse, qty_available, lead_time_days, next_restock_date) VALUES
 ('TMN4010Q','Hong Kong DC',250000,14, CURRENT_DATE + INTERVAL '14 days'),
 ('TMN4010Q','Hamburg DC',   80000,21, CURRENT_DATE + INTERVAL '21 days'),
 ('SBD3020EP','Hong Kong DC',500000,10, CURRENT_DATE + INTERVAL '10 days'),
 ('PMN8033YS','Dallas DC',   120000,28, CURRENT_DATE + INTERVAL '28 days'),
 ('74LVC1G08','Hong Kong DC',2000000,7, CURRENT_DATE + INTERVAL '7 days'),
 ('ESD1CANQ','Hamburg DC',   350000,14, CURRENT_DATE + INTERVAL '14 days'),
 ('ESD1CANQ','Hong Kong DC',180000,14, CURRENT_DATE + INTERVAL '14 days'),
 ('BC847BW','Hong Kong DC',  900000,12, CURRENT_DATE + INTERVAL '12 days'),
 ('SBD2010A','Hong Kong DC',  15000, 0, NULL),
 ('74AHC1G14','Hong Kong DC',750000, 9, CURRENT_DATE + INTERVAL '9 days'),
 ('GAN65R060','Dallas DC',    18000,35, CURRENT_DATE + INTERVAL '35 days'),
 ('GAN65R060','Hamburg DC',    6000,35, CURRENT_DATE + INTERVAL '42 days'),
 ('TMN2508','Hong Kong DC',  600000,10, CURRENT_DATE + INTERVAL '10 days'),
 ('PMN8033YS','Hong Kong DC',  45000,28, CURRENT_DATE + INTERVAL '28 days');

-- price_breaks (USD) -------------------------------------------------
INSERT INTO price_breaks (part_number, min_qty, unit_price) VALUES
 ('TMN4010Q',1,1.8500),('TMN4010Q',1000,1.4200),('TMN4010Q',5000,1.1800),('TMN4010Q',25000,0.9800),
 ('SBD3020EP',1,0.2200),('SBD3020EP',1000,0.1400),('SBD3020EP',10000,0.0890),('SBD3020EP',100000,0.0710),
 ('PMN8033YS',1,2.4000),('PMN8033YS',1000,1.9500),('PMN8033YS',10000,1.5500),
 ('74LVC1G08',1,0.1100),('74LVC1G08',1000,0.0450),('74LVC1G08',10000,0.0280),('74LVC1G08',100000,0.0190),
 ('ESD1CANQ',1,0.3400),('ESD1CANQ',1000,0.2100),('ESD1CANQ',10000,0.1400),
 ('BC847BW',1,0.0600),('BC847BW',1000,0.0210),('BC847BW',10000,0.0130),
 ('SBD2010A',1,0.1900),('SBD2010A',1000,0.1200),
 ('74AHC1G14',1,0.1300),('74AHC1G14',1000,0.0500),('74AHC1G14',10000,0.0310),
 ('GAN65R060',1,8.5000),('GAN65R060',500,6.9000),('GAN65R060',2500,5.7500),
 ('TMN2508',1,0.2800),('TMN2508',1000,0.1900),('TMN2508',10000,0.1200);

-- orders (4) + order_lines (7) --------------------------------------
INSERT INTO orders (order_id, customer_id, po_number, order_date, status, currency, total_amount) VALUES
 ('SO-2026-0001','CUST-10001','AUR-PO-88231', CURRENT_DATE - INTERVAL '20 days','In Production','USD', 8700.00),
 ('SO-2026-0002','CUST-10001','AUR-PO-88245', CURRENT_DATE - INTERVAL '12 days','Confirmed','USD',   21300.00),
 ('SO-2026-0003','CUST-10004','HEL-PO-4471',  CURRENT_DATE - INTERVAL '30 days','Shipped','USD',      14375.00),
 ('SO-2026-0004','CUST-10002','SPT-77-231',   CURRENT_DATE - INTERVAL '4 days','Open','USD',          17400.00);

INSERT INTO order_lines (order_id, part_number, quantity, unit_price, requested_date, promised_date, line_status) VALUES
 ('SO-2026-0001','TMN4010Q',  5000, 1.1800, CURRENT_DATE + INTERVAL '10 days', CURRENT_DATE + INTERVAL '10 days','In Production'),
 ('SO-2026-0001','ESD1CANQ', 20000, 0.1400, CURRENT_DATE + INTERVAL '10 days', CURRENT_DATE + INTERVAL '10 days','In Production'),
 ('SO-2026-0002','SBD3020EP',100000,0.0890, CURRENT_DATE + INTERVAL '25 days', CURRENT_DATE + INTERVAL '25 days','Confirmed'),
 ('SO-2026-0002','PMN8033YS', 8000, 1.5500, CURRENT_DATE + INTERVAL '30 days', CURRENT_DATE + INTERVAL '30 days','Confirmed'),
 ('SO-2026-0003','GAN65R060', 2500, 5.7500, CURRENT_DATE - INTERVAL '5 days',  CURRENT_DATE - INTERVAL '5 days', 'Shipped'),
 ('SO-2026-0004','74LVC1G08',100000,0.0190, CURRENT_DATE + INTERVAL '15 days', CURRENT_DATE + INTERVAL '15 days','Open'),
 ('SO-2026-0004','PMN8033YS',10000, 1.5500, CURRENT_DATE + INTERVAL '20 days', CURRENT_DATE + INTERVAL '20 days','Open');

-- pcn_notices (3) ----------------------------------------------------
INSERT INTO pcn_notices (pcn_id, part_number, notice_type, title, description, effective_date, last_time_buy_date, replacement_part, status) VALUES
 ('PCN-2026-0001','SBD2010A','EOL','End-of-Life: SBD2010A Schottky Rectifier',
   'SBD2010A (20V 1A, SOD123) is being discontinued. Place last-time-buy orders before the LTB date. Recommended replacement SBD2010B is a drop-in with improved forward voltage.',
   CURRENT_DATE + INTERVAL '90 days', CURRENT_DATE + INTERVAL '60 days','SBD2010B','Published'),
 ('PCN-2026-0002','BC847BW','PCN','Assembly Site Change: BC847BW',
   'Manufacturing of BC847BW (SOT323) transfers to an alternate assembly site. Form, fit and function unchanged; requalification data available on request.',
   CURRENT_DATE + INTERVAL '30 days', NULL, NULL,'Published'),
 ('PCN-2026-0003','PMN8033YS','PCN','Mold Compound Change: PMN8033YS',
   'Mold compound for PMN8033YS (LFPAK56) updated to a greener compound. No change to electrical or thermal performance.',
   CURRENT_DATE + INTERVAL '45 days', NULL, NULL,'Published');

-- cross_references (5) -----------------------------------------------
INSERT INTO cross_references (part_number, alternative_part, xref_type, source, notes) VALUES
 ('SBD2010A','SBD2010B','Replacement','Multi-source','Drop-in EOL replacement, improved forward voltage'),
 ('SBD3020EP','SBD3025EP','Upgrade','Multi-source','Higher 2.5A current rating, same footprint'),
 ('74LVC1G08','74AHC1G08','Pin-Compatible','Multi-source','AHC logic family, higher speed, same pinout'),
 ('BC847BW','BC847CW','Second-Source','Multi-source','Higher gain (C) bin, same package'),
 ('TMN4010Q','TMN4010QX','Second-Source','Multi-source','Alternate assembly site, identical datasheet specs');

-- rma_cases (re-seed the single baseline row) ------------------------
INSERT INTO rma_cases (rma_id, customer_id, order_id, part_number, quantity, defect_type, description, status, opened_date, est_resolution_date) VALUES
 ('RMA-2026-0001','CUST-10004','SO-2026-0003','GAN65R060',40,'Field Return',
   'Intermittent gate-drive failures reported on field units from shipped lot.','Under Review',
   CURRENT_DATE - INTERVAL '6 days', CURRENT_DATE + INTERVAL '8 days');

-- sample_requests (re-seed the single baseline row) ------------------
INSERT INTO sample_requests (sample_id, customer_id, part_number, quantity, purpose, status, requested_date, ship_to) VALUES
 ('SMP-2026-0001','CUST-10005','ESD1CANQ',25,'Design-in evaluation for infusion pump','Shipped',
   CURRENT_DATE - INTERVAL '9 days','Meridian Medical Devices, Boston MA, USA');

-- alert_subscriptions: intentionally left EMPTY.
