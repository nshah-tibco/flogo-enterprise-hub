-- =============================================================================
-- Maritime Container Shipping — RESET demo data
-- Restores a clean demo state between runs: truncates every table, re-seeds the
-- read tables + the one pre-seeded claim, and leaves the agent-written tables
-- (booking_amendments, charge_disputes, and any agent-created bookings/claims)
-- empty. Volatile dates are CURRENT_DATE-relative so the demo always looks live.
--   psql -h <host> -p <port> -U <user> -d container_shipping -f reset_data.sql
-- =============================================================================

TRUNCATE charge_disputes, booking_amendments, claims, charges, tracking_events,
         containers, bookings, rates, voyages, container_types, vessels, ports,
         customers
    RESTART IDENTITY CASCADE;

-- Restart the booking-reference sequence used by agent-created bookings.
ALTER SEQUENCE booking_seq RESTART WITH 100;

-- Customers ------------------------------------------------------------------
INSERT INTO customers (customer_code, company_name, account_type, loyalty_tier, contact_name, contact_email, contact_phone, country, credit_terms, active_since) VALUES
 ('CUST-SHIP-1001','Pacific Traders Inc',         'BCO',       'Gold',   'Sarah Chen',    'sarah.chen@pacifictraders.example.com',   '+1-415-555-0111','United States','Net 30', CURRENT_DATE - INTERVAL '6 years'),
 ('CUST-SHIP-1002','Global Spice Co',             'BCO',       'Silver', 'Raj Patel',     'raj.patel@globalspice.example.com',       '+91-22-555-0122','India',        'Net 15', CURRENT_DATE - INTERVAL '4 years'),
 ('CUST-SHIP-1003','Continental Machinery GmbH',  'Enterprise','Gold',   'Klaus Weber',   'klaus.weber@contimach.example.com',       '+49-40-555-0133','Germany',      'Net 45', CURRENT_DATE - INTERVAL '8 years'),
 ('CUST-SHIP-1004','AutoParts Direct LLC',        'BCO',       'Bronze', 'Maria Gonzalez','maria.gonzalez@autopartsdirect.example.com','+1-310-555-0144','United States','Net 30', CURRENT_DATE - INTERVAL '2 years'),
 ('CUST-SHIP-1005','MediShip Pharma',             'Enterprise','Gold',   'Emma Wilson',   'emma.wilson@medishippharma.example.com',  '+44-20-555-0155','United Kingdom','Net 30', CURRENT_DATE - INTERVAL '5 years'),
 ('CUST-SHIP-1006','Sunrise Textiles Ltd',        'BCO',       'Silver', 'Ahmed Hassan',  'ahmed.hassan@sunrisetextiles.example.com','+971-4-555-0166','United Arab Emirates','Net 15', CURRENT_DATE - INTERVAL '3 years');

-- Ports ----------------------------------------------------------------------
INSERT INTO ports (port_code, port_name, country, region) VALUES
 ('CNSHA','Shanghai',             'China',         'Asia'),
 ('SGSIN','Singapore',            'Singapore',     'Asia'),
 ('INNSA','Nhava Sheva (Mumbai)', 'India',         'Asia'),
 ('HKHKG','Hong Kong',            'Hong Kong',     'Asia'),
 ('AEJEA','Jebel Ali (Dubai)',    'United Arab Emirates','Middle East'),
 ('NLRTM','Rotterdam',            'Netherlands',   'Europe'),
 ('DEHAM','Hamburg',              'Germany',       'Europe'),
 ('GBFXT','Felixstowe',           'United Kingdom','Europe'),
 ('USLAX','Los Angeles',          'United States', 'North America'),
 ('USNYC','New York',             'United States', 'North America');

-- Vessels --------------------------------------------------------------------
INSERT INTO vessels (vessel_id, vessel_name, imo_number, operator, flag, capacity_teu) VALUES
 ('V001','Pacific Voyager',  '9811000','Oceanic Lines','Panama',          14000),
 ('V002','Atlantic Pioneer', '9811001','Oceanic Lines','Liberia',         18000),
 ('V003','Indian Star',      '9811002','Oceanic Lines','Singapore',       10000),
 ('V004','Europa Express',   '9811003','Oceanic Lines','Malta',           20000),
 ('V005','Asia Trader',      '9811004','Oceanic Lines','Marshall Islands',12000);

-- Container types ------------------------------------------------------------
INSERT INTO container_types (type_code, description, teu, max_payload_kg) VALUES
 ('20GP','20ft General Purpose',1.0,28200),
 ('40GP','40ft General Purpose',2.0,26700),
 ('40HC','40ft High Cube',      2.0,26500),
 ('20RF','20ft Reefer',         1.0,27700);

-- Voyages --------------------------------------------------------------------
INSERT INTO voyages (voyage_id, vessel_id, service_name, origin_port, destination_port, etd, eta, transit_days, status) VALUES
 ('VOY-501','V001','Trans-Pacific TP1','CNSHA','USLAX', CURRENT_DATE + INTERVAL '2 days',  CURRENT_DATE + INTERVAL '16 days', 14,'Scheduled'),
 ('VOY-502','V002','Trans-Atlantic AT1','NLRTM','USNYC',CURRENT_DATE + INTERVAL '3 days',  CURRENT_DATE + INTERVAL '12 days',  9,'Scheduled'),
 ('VOY-503','V003','India-Europe IE2', 'INNSA','NLRTM', CURRENT_DATE - INTERVAL '1 day',   CURRENT_DATE + INTERVAL '20 days', 21,'Departed'),
 ('VOY-504','V004','Asia-Europe AE1',  'CNSHA','DEHAM', CURRENT_DATE + INTERVAL '5 days',  CURRENT_DATE + INTERVAL '33 days', 28,'Scheduled'),
 ('VOY-505','V005','Intra-Asia IA3',   'SGSIN','CNSHA', CURRENT_DATE - INTERVAL '1 day',   CURRENT_DATE + INTERVAL '5 days',   5,'Departed'),
 ('VOY-506','V001','Trans-Pacific TP1','CNSHA','USLAX', CURRENT_DATE - INTERVAL '10 days', CURRENT_DATE + INTERVAL '6 days',  14,'Delayed'),
 ('VOY-507','V004','Asia-Europe AE1',  'INNSA','NLRTM', CURRENT_DATE - INTERVAL '5 days',  CURRENT_DATE + INTERVAL '16 days', 21,'Departed'),
 ('VOY-508','V002','Trans-Atlantic AT1','USNYC','NLRTM',CURRENT_DATE + INTERVAL '7 days',  CURRENT_DATE + INTERVAL '18 days', 11,'Scheduled');

-- Rate card ------------------------------------------------------------------
INSERT INTO rates (rate_id, origin_port, destination_port, container_type, base_rate_usd, currency, transit_days, valid_from, valid_to) VALUES
 ('RATE-001','CNSHA','USLAX','20GP',1850.00,'USD',14, CURRENT_DATE - INTERVAL '30 days', CURRENT_DATE + INTERVAL '60 days'),
 ('RATE-002','CNSHA','USLAX','40GP',2400.00,'USD',14, CURRENT_DATE - INTERVAL '30 days', CURRENT_DATE + INTERVAL '60 days'),
 ('RATE-003','CNSHA','USLAX','40HC',2500.00,'USD',14, CURRENT_DATE - INTERVAL '30 days', CURRENT_DATE + INTERVAL '60 days'),
 ('RATE-004','INNSA','NLRTM','40HC',2200.00,'USD',21, CURRENT_DATE - INTERVAL '30 days', CURRENT_DATE + INTERVAL '60 days'),
 ('RATE-005','INNSA','NLRTM','20GP',1600.00,'USD',21, CURRENT_DATE - INTERVAL '30 days', CURRENT_DATE + INTERVAL '60 days'),
 ('RATE-006','CNSHA','DEHAM','40HC',2800.00,'USD',28, CURRENT_DATE - INTERVAL '30 days', CURRENT_DATE + INTERVAL '60 days'),
 ('RATE-007','SGSIN','CNSHA','20GP', 650.00,'USD', 5, CURRENT_DATE - INTERVAL '30 days', CURRENT_DATE + INTERVAL '60 days'),
 ('RATE-008','NLRTM','USNYC','40HC',2100.00,'USD', 9, CURRENT_DATE - INTERVAL '30 days', CURRENT_DATE + INTERVAL '60 days');

-- Bookings -------------------------------------------------------------------
INSERT INTO bookings (booking_ref, customer_code, voyage_id, origin_port, destination_port, container_type, quantity, cargo_description, total_amount_usd, currency, status, booking_date) VALUES
 ('BKG-2026-0001','CUST-SHIP-1001','VOY-503','INNSA','NLRTM','40HC',2,'Textiles',        4400.00,'USD','Discharged', CURRENT_DATE - INTERVAL '25 days'),
 ('BKG-2026-0002','CUST-SHIP-1002','VOY-505','SGSIN','CNSHA','20GP',1,'Electronics',      650.00,'USD','Delivered',  CURRENT_DATE - INTERVAL '20 days'),
 ('BKG-2026-0003','CUST-SHIP-1001','VOY-501','CNSHA','USLAX','40HC',3,'Furniture',       7500.00,'USD','Confirmed',  CURRENT_DATE - INTERVAL '3 days'),
 ('BKG-2026-0004','CUST-SHIP-1003','VOY-502','NLRTM','USNYC','40HC',1,'Machinery',       2100.00,'USD','In Transit', CURRENT_DATE - INTERVAL '8 days'),
 ('BKG-2026-0005','CUST-SHIP-1004','VOY-504','CNSHA','DEHAM','40HC',2,'Auto Parts',      5600.00,'USD','Confirmed',  CURRENT_DATE - INTERVAL '2 days'),
 ('BKG-2026-0006','CUST-SHIP-1002','VOY-507','INNSA','NLRTM','20GP',4,'Spices',          6400.00,'USD','In Transit', CURRENT_DATE - INTERVAL '6 days'),
 ('BKG-2026-0007','CUST-SHIP-1001','VOY-506','CNSHA','USLAX','40HC',2,'Retail Goods',    5000.00,'USD','Delayed',    CURRENT_DATE - INTERVAL '12 days'),
 ('BKG-2026-0008','CUST-SHIP-1005','VOY-508','USNYC','NLRTM','40HC',1,'Pharmaceuticals', 2100.00,'USD','Confirmed',  CURRENT_DATE - INTERVAL '1 day');

-- Containers -----------------------------------------------------------------
INSERT INTO containers (container_no, booking_ref, container_type, seal_no, status, current_location, gross_weight_kg) VALUES
 ('MSKU1000001','BKG-2026-0001','40HC','SL1000001','Discharged','NLRTM',21000),
 ('OOLU2000001','BKG-2026-0002','20GP','SL2000001','Delivered', 'CNSHA',12000),
 ('MSKU3000001','BKG-2026-0003','40HC','SL3000001','Loaded',    'CNSHA',22000),
 ('MSKU3000002','BKG-2026-0003','40HC','SL3000002','Loaded',    'CNSHA',21500),
 ('MSKU3000003','BKG-2026-0003','40HC','SL3000003','Loaded',    'CNSHA',21000),
 ('HLBU4000001','BKG-2026-0004','40HC','SL4000001','In Transit','USNYC',24000),
 ('MSKU6000001','BKG-2026-0006','20GP','SL6000001','In Transit','SGSIN',18000),
 ('MSKU7000001','BKG-2026-0007','40HC','SL7000001','Hold',      'SGSIN',23000),
 ('MSKU7000002','BKG-2026-0007','40HC','SL7000002','Hold',      'SGSIN',22800),
 ('OOLU8000001','BKG-2026-0008','40HC','SL8000001','Loaded',    'USNYC',20000);

-- Tracking events ------------------------------------------------------------
INSERT INTO tracking_events (container_no, event_time, location_port, event_type, description) VALUES
 ('MSKU1000001', CURRENT_DATE - INTERVAL '25 days', 'INNSA','Gate In',        'Container gated in at origin terminal'),
 ('MSKU1000001', CURRENT_DATE - INTERVAL '24 days', 'INNSA','Loaded',         'Loaded on Indian Star VOY-503'),
 ('MSKU1000001', CURRENT_DATE - INTERVAL '24 days', 'INNSA','Vessel Departed','Vessel departed origin port'),
 ('MSKU1000001', CURRENT_DATE - INTERVAL '4 days',  'NLRTM','Vessel Arrived', 'Vessel arrived at destination port'),
 ('MSKU1000001', CURRENT_DATE - INTERVAL '3 days',  'NLRTM','Discharged',     'Container discharged from vessel'),
 ('OOLU2000001', CURRENT_DATE - INTERVAL '20 days', 'SGSIN','Gate In',        'Container gated in at origin terminal'),
 ('OOLU2000001', CURRENT_DATE - INTERVAL '19 days', 'SGSIN','Loaded',         'Loaded on Asia Trader VOY-505'),
 ('OOLU2000001', CURRENT_DATE - INTERVAL '14 days', 'CNSHA','Vessel Arrived', 'Vessel arrived at destination port'),
 ('OOLU2000001', CURRENT_DATE - INTERVAL '13 days', 'CNSHA','Discharged',     'Container discharged from vessel'),
 ('OOLU2000001', CURRENT_DATE - INTERVAL '12 days', 'CNSHA','Delivered',      'Delivered to consignee'),
 ('HLBU4000001', CURRENT_DATE - INTERVAL '8 days',  'NLRTM','Gate In',        'Container gated in at origin terminal'),
 ('HLBU4000001', CURRENT_DATE - INTERVAL '7 days',  'NLRTM','Loaded',         'Loaded on Atlantic Pioneer VOY-502'),
 ('HLBU4000001', CURRENT_DATE - INTERVAL '7 days',  'NLRTM','Vessel Departed','Vessel departed origin port'),
 ('HLBU4000001', CURRENT_DATE - INTERVAL '2 days',  'USNYC','In Transit',     'Vessel en route to destination'),
 ('MSKU6000001', CURRENT_DATE - INTERVAL '6 days',  'INNSA','Gate In',        'Container gated in at origin terminal'),
 ('MSKU6000001', CURRENT_DATE - INTERVAL '5 days',  'INNSA','Loaded',         'Loaded on Europa Express VOY-507'),
 ('MSKU6000001', CURRENT_DATE - INTERVAL '5 days',  'INNSA','Vessel Departed','Vessel departed origin port'),
 ('MSKU7000001', CURRENT_DATE - INTERVAL '12 days', 'CNSHA','Gate In',        'Container gated in at origin terminal'),
 ('MSKU7000001', CURRENT_DATE - INTERVAL '11 days', 'CNSHA','Loaded',         'Loaded on Pacific Voyager VOY-506'),
 ('MSKU7000001', CURRENT_DATE - INTERVAL '11 days', 'CNSHA','Vessel Departed','Vessel departed origin port'),
 ('MSKU7000001', CURRENT_DATE - INTERVAL '6 days',  'SGSIN','Transshipment',  'Discharged at transshipment hub'),
 ('MSKU7000001', CURRENT_DATE - INTERVAL '3 days',  'SGSIN','Hold',           'Held at transshipment hub — severe weather delay, onward sailing postponed');

-- Charges --------------------------------------------------------------------
INSERT INTO charges (charge_id, booking_ref, charge_type, amount_usd, currency, free_days, days_used, status, charge_date) VALUES
 ('CHG-1001','BKG-2026-0001','Freight',   4400.00,'USD',0,0,'Paid',    CURRENT_DATE - INTERVAL '25 days'),
 ('CHG-1002','BKG-2026-0002','Freight',    650.00,'USD',0,0,'Paid',    CURRENT_DATE - INTERVAL '20 days'),
 ('CHG-1003','BKG-2026-0003','Freight',   7500.00,'USD',0,0,'Invoiced',CURRENT_DATE - INTERVAL '3 days'),
 ('CHG-1004','BKG-2026-0004','Freight',   2100.00,'USD',0,0,'Invoiced',CURRENT_DATE - INTERVAL '8 days'),
 ('CHG-1005','BKG-2026-0004','Detention',  600.00,'USD',4,2,'Invoiced',CURRENT_DATE - INTERVAL '2 days'),
 ('CHG-1006','BKG-2026-0006','Freight',   6400.00,'USD',0,0,'Paid',    CURRENT_DATE - INTERVAL '6 days'),
 ('CHG-1007','BKG-2026-0007','Freight',   5000.00,'USD',0,0,'Invoiced',CURRENT_DATE - INTERVAL '12 days'),
 ('CHG-1008','BKG-2026-0007','Demurrage', 1200.00,'USD',5,8,'Invoiced',CURRENT_DATE - INTERVAL '1 day'),
 ('CHG-1009','BKG-2026-0005','Freight',   5600.00,'USD',0,0,'Invoiced',CURRENT_DATE - INTERVAL '2 days'),
 ('CHG-1010','BKG-2026-0008','BAF',        315.00,'USD',0,0,'Invoiced',CURRENT_DATE - INTERVAL '1 day');

-- Claims (one pre-seeded; agent-created rows are cleared on reset) ------------
INSERT INTO claims (booking_ref, customer_code, claim_type, description, claim_amount_usd, currency, status, filed_date) VALUES
 ('BKG-2026-0002','CUST-SHIP-1002','Shortage','Short-landed 2 cartons of electronics on delivery', 450.00,'USD','Under Review', CURRENT_DATE - INTERVAL '5 days');

-- booking_amendments and charge_disputes intentionally left EMPTY.
