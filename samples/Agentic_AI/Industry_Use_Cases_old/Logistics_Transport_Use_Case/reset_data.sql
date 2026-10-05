-- =============================================================================
-- Logistics / Transport - Shipper Self-Service Assistant
-- RESET script: re-seed read tables, EMPTY the agent-written tables.
-- =============================================================================
-- Run this between demos. It does NOT drop/recreate tables (schema stays);
-- it truncates everything, re-inserts the read data with CURRENT_DATE-relative
-- dates so delays/ETAs stay fresh, and leaves delivery_changes / pickup_requests
-- / claims empty so each demo starts from a clean slate.
--
--   psql -h <host> -p <port> -U <user> -d <db> -f reset_data.sql
-- =============================================================================

-- Wipe everything (RESTART IDENTITY resets SERIAL counters; CASCADE handles FKs)
TRUNCATE TABLE claims, pickup_requests, delivery_changes,
               tracking_events, shipments, addresses,
               service_levels, customers
        RESTART IDENTITY CASCADE;

-- Customers -------------------------------------------------------------------
INSERT INTO customers (customer_id, name, email, phone, account_type, loyalty_tier) VALUES
 ('CUST-LOG-1001', 'Acme Retail Ltd',      'ops@acmeretail.example',      '+1-415-555-0111', 'Business',   'Gold'),
 ('CUST-LOG-1002', 'Maria Gonzalez',       'maria.gonzalez@example.com',  '+1-512-555-0148', 'Individual', 'Silver'),
 ('CUST-LOG-1003', 'Nordic Components AB', 'logistics@nordiccomp.example','+46-8-555-0199',  'Business',   'Gold'),
 ('CUST-LOG-1004', 'James Whitfield',      'james.whitfield@example.com', '+44-20-5550-0123','Individual', 'Standard'),
 ('CUST-LOG-1005', 'Sunrise Foods Inc',    'ship@sunrisefoods.example',   '+1-312-555-0176', 'Business',   'Silver');

-- Addresses -------------------------------------------------------------------
INSERT INTO addresses (address_id, customer_id, label, line1, city, state, postal_code, country, is_default) VALUES
 ('ADDR-1001', 'CUST-LOG-1001', 'Warehouse', '2200 Industrial Pkwy',   'San Francisco', 'CA', '94124', 'USA',    TRUE),
 ('ADDR-1002', 'CUST-LOG-1001', 'Office',    '55 Market St, Ste 900',  'Austin',        'TX', '78701', 'USA',    FALSE),
 ('ADDR-1003', 'CUST-LOG-1002', 'Home',      '1804 Cypress Ave',       'Austin',        'TX', '78702', 'USA',    TRUE),
 ('ADDR-1004', 'CUST-LOG-1003', 'Warehouse', 'Kungsgatan 12',          'Stockholm',     NULL, '11143', 'Sweden', TRUE),
 ('ADDR-1005', 'CUST-LOG-1004', 'Home',      '14 Baker Mews',          'London',        NULL, 'W1U 6TU','UK',    TRUE),
 ('ADDR-1006', 'CUST-LOG-1005', 'Warehouse', '900 W Fulton Market',    'Chicago',       'IL', '60607', 'USA',    TRUE);

-- Service levels (rate card) --------------------------------------------------
INSERT INTO service_levels (service_code, name, description, transit_days_min, transit_days_max, price_per_kg, max_weight_kg) VALUES
 ('SAME_DAY', 'Same-Day Courier',  'Delivered same business day within metro areas.',            0, 0, 12.50, 30.00),
 ('EXP',      'Express',           'Priority air, 1-2 business days, end-of-day delivery.',      1, 2,  6.75, 70.00),
 ('STD',      'Standard Ground',   'Economy ground, 3-5 business days, most cost-effective.',    3, 5,  2.40, 150.00),
 ('ECO',      'Eco Freight',       'Consolidated freight for heavy/bulk, 5-8 business days.',    5, 8,  1.10, 1000.00);

-- Shipments -------------------------------------------------------------------
INSERT INTO shipments
 (tracking_number, customer_id, origin_city, origin_country, destination_city, destination_country, destination_address,
  service_code, status, weight_kg, declared_value, currency, carrier, dimensions_cm,
  ship_date, estimated_delivery, actual_delivery, current_location) VALUES
 ('TRK-2026-0001', 'CUST-LOG-1001', 'San Francisco', 'USA', 'Austin',    'USA', '55 Market St, Ste 900, Austin, TX 78701',
   'EXP', 'Delivered',        4.20, 850.00,  'USD', 'SwiftAir',   '40x30x20', CURRENT_DATE - 6, CURRENT_DATE - 4, CURRENT_DATE - 4, 'Austin, TX'),
 ('TRK-2026-0002', 'CUST-LOG-1002', 'Austin',        'USA', 'Denver',    'USA', '77 Larimer St, Denver, CO 80202',
   'STD', 'In Transit',       2.10, 120.00,  'USD', 'GroundLink', '30x20x15', CURRENT_DATE - 2, CURRENT_DATE + 2, NULL,             'Amarillo, TX'),
 ('TRK-2026-0003', 'CUST-LOG-1001', 'San Francisco', 'USA', 'Seattle',   'USA', '400 Pine St, Seattle, WA 98101',
   'EXP', 'Out for Delivery', 1.80,  95.00,  'USD', 'SwiftAir',   '25x20x10', CURRENT_DATE - 1, CURRENT_DATE,     NULL,             'Seattle, WA'),
 ('TRK-2026-0004', 'CUST-LOG-1004', 'London',        'UK',  'Manchester','UK',  '14 Deansgate, Manchester M3 1AR',
   'STD', 'Exception',        6.50, 300.00,  'GBP', 'BritCarry',  '50x40x30', CURRENT_DATE - 3, CURRENT_DATE - 1, NULL,             'Birmingham, UK'),
 ('TRK-2026-0005', 'CUST-LOG-1005', 'Chicago',       'USA', 'Detroit',   'USA', '120 Woodward Ave, Detroit, MI 48226',
   'STD', 'Delivered',       12.00, 540.00,  'USD', 'GroundLink', '60x40x40', CURRENT_DATE - 7, CURRENT_DATE - 3, CURRENT_DATE - 3, 'Detroit, MI'),
 ('TRK-2026-0006', 'CUST-LOG-1002', 'Austin',        'USA', 'Miami',     'USA', '801 Brickell Ave, Miami, FL 33131',
   'ECO', 'Label Created',   45.00, 1200.00, 'USD', 'FreightOne', '120x80x80',NULL,             CURRENT_DATE + 7, NULL,             'Austin, TX'),
 ('TRK-2026-0007', 'CUST-LOG-1001', 'San Francisco', 'USA', 'Dallas',    'USA', '2200 Industrial Pkwy, San Francisco, CA 94124',
   'EXP', 'Delayed',          3.30, 410.00,  'USD', 'SwiftAir',   '35x25x20', CURRENT_DATE - 4, CURRENT_DATE - 1, NULL,             'Phoenix, AZ'),
 ('TRK-2026-0008', 'CUST-LOG-1003', 'Stockholm',     'Sweden','Hamburg', 'Germany','Speicherstadt 5, 20457 Hamburg',
   'EXP', 'Delivered',        8.90, 2200.00, 'EUR', 'EuroFreight','45x35x30', CURRENT_DATE - 9, CURRENT_DATE - 6, CURRENT_DATE - 6, 'Hamburg, DE'),
 ('TRK-2026-0009', 'CUST-LOG-1003', 'Stockholm',     'Sweden','Oslo',    'Norway','Karl Johans gate 22, 0159 Oslo',
   'STD', 'In Transit',       5.40, 320.00,  'EUR', 'EuroFreight','40x30x25', CURRENT_DATE - 1, CURRENT_DATE + 3, NULL,             'Gothenburg, SE'),
 ('TRK-2026-0010', 'CUST-LOG-1004', 'London',        'UK',  'Edinburgh', 'UK',  '9 Princes St, Edinburgh EH2 2AN',
   'EXP', 'Delayed',          2.70, 180.00,  'GBP', 'BritCarry',  '30x25x15', CURRENT_DATE - 3, CURRENT_DATE - 1, NULL,             'Leeds, UK');

-- Tracking events -------------------------------------------------------------
INSERT INTO tracking_events (tracking_number, event_time, location, status, description) VALUES
 ('TRK-2026-0001', CURRENT_DATE - 6 + TIME '09:10', 'San Francisco, CA', 'Picked Up',        'Shipment picked up from origin'),
 ('TRK-2026-0001', CURRENT_DATE - 5 + TIME '22:40', 'Phoenix, AZ',       'In Transit',       'Departed sorting hub'),
 ('TRK-2026-0001', CURRENT_DATE - 4 + TIME '11:05', 'Austin, TX',        'Delivered',        'Delivered, signed by front desk'),
 ('TRK-2026-0002', CURRENT_DATE - 2 + TIME '08:30', 'Austin, TX',        'Picked Up',        'Shipment picked up from origin'),
 ('TRK-2026-0002', CURRENT_DATE - 1 + TIME '19:15', 'Amarillo, TX',      'In Transit',       'Arrived at regional facility'),
 ('TRK-2026-0003', CURRENT_DATE - 1 + TIME '07:50', 'San Francisco, CA', 'Picked Up',        'Shipment picked up from origin'),
 ('TRK-2026-0003', CURRENT_DATE     + TIME '06:20', 'Seattle, WA',       'Out for Delivery', 'On vehicle for delivery'),
 ('TRK-2026-0004', CURRENT_DATE - 3 + TIME '10:00', 'London, UK',        'Picked Up',        'Shipment picked up from origin'),
 ('TRK-2026-0004', CURRENT_DATE - 1 + TIME '14:25', 'Birmingham, UK',    'Exception',        'Address incomplete - delivery on hold'),
 ('TRK-2026-0005', CURRENT_DATE - 7 + TIME '09:00', 'Chicago, IL',       'Picked Up',        'Shipment picked up from origin'),
 ('TRK-2026-0005', CURRENT_DATE - 3 + TIME '13:40', 'Detroit, MI',       'Delivered',        'Delivered to loading dock'),
 ('TRK-2026-0007', CURRENT_DATE - 4 + TIME '08:15', 'San Francisco, CA', 'Picked Up',        'Shipment picked up from origin'),
 ('TRK-2026-0007', CURRENT_DATE - 3 + TIME '21:30', 'Phoenix, AZ',       'In Transit',       'Departed sorting hub'),
 ('TRK-2026-0007', CURRENT_DATE - 1 + TIME '16:45', 'Phoenix, AZ',       'Delayed',          'Weather delay at regional hub'),
 ('TRK-2026-0008', CURRENT_DATE - 9 + TIME '10:30', 'Stockholm, SE',     'Picked Up',        'Shipment picked up from origin'),
 ('TRK-2026-0008', CURRENT_DATE - 6 + TIME '15:10', 'Hamburg, DE',       'Delivered',        'Delivered, signed by warehouse'),
 ('TRK-2026-0009', CURRENT_DATE - 1 + TIME '09:45', 'Stockholm, SE',     'Picked Up',        'Shipment picked up from origin'),
 ('TRK-2026-0009', CURRENT_DATE     + TIME '05:30', 'Gothenburg, SE',    'In Transit',       'Arrived at regional facility'),
 ('TRK-2026-0010', CURRENT_DATE - 3 + TIME '11:20', 'London, UK',        'Picked Up',        'Shipment picked up from origin'),
 ('TRK-2026-0010', CURRENT_DATE - 1 + TIME '18:05', 'Leeds, UK',         'Delayed',          'Mechanical delay on line-haul');

-- delivery_changes / pickup_requests / claims left EMPTY on purpose.
