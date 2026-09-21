-- =============================================================================
-- Logistics / Transport - Shipper Self-Service Assistant
-- PostgreSQL schema + demo seed data
-- =============================================================================
-- Persona: a shipper/customer who self-serves over a chat assistant.
-- 5 read tables are seeded; 3 agent-written tables (delivery_changes,
-- pickup_requests, claims) start EMPTY and are filled by the A2A agents.
-- Dates are CURRENT_DATE-relative so the demo (delays, ETAs) stays fresh.
--
-- Load:   psql -h <host> -p <port> -U <user> -d <db> -f database.sql
-- Reset:  psql ... -f reset_data.sql   (re-seeds; empties agent tables)
-- =============================================================================

DROP TABLE IF EXISTS claims           CASCADE;
DROP TABLE IF EXISTS pickup_requests  CASCADE;
DROP TABLE IF EXISTS delivery_changes CASCADE;
DROP TABLE IF EXISTS tracking_events  CASCADE;
DROP TABLE IF EXISTS shipments        CASCADE;
DROP TABLE IF EXISTS addresses        CASCADE;
DROP TABLE IF EXISTS service_levels   CASCADE;
DROP TABLE IF EXISTS customers        CASCADE;

-- -----------------------------------------------------------------------------
-- Reference / read tables (seeded)
-- -----------------------------------------------------------------------------

CREATE TABLE customers (
    customer_id   VARCHAR(20)  PRIMARY KEY,
    name          VARCHAR(120) NOT NULL,
    email         VARCHAR(160) NOT NULL,
    phone         VARCHAR(40),
    account_type  VARCHAR(20)  NOT NULL DEFAULT 'Individual',  -- Individual | Business
    loyalty_tier  VARCHAR(20)  DEFAULT 'Standard',             -- Standard | Silver | Gold
    created_at    TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE TABLE addresses (
    address_id    VARCHAR(20)  PRIMARY KEY,
    customer_id   VARCHAR(20)  NOT NULL REFERENCES customers(customer_id),
    label         VARCHAR(40)  NOT NULL,                        -- Home | Office | Warehouse
    line1         VARCHAR(160) NOT NULL,
    city          VARCHAR(80)  NOT NULL,
    state         VARCHAR(80),
    postal_code   VARCHAR(20),
    country       VARCHAR(60)  NOT NULL,
    is_default    BOOLEAN      NOT NULL DEFAULT FALSE
);

CREATE TABLE service_levels (
    service_code      VARCHAR(20)  PRIMARY KEY,                 -- SAME_DAY | EXP | STD | ECO
    name              VARCHAR(60)  NOT NULL,
    description       VARCHAR(200) NOT NULL,
    transit_days_min  INT          NOT NULL,
    transit_days_max  INT          NOT NULL,
    price_per_kg      NUMERIC(10,2) NOT NULL,
    max_weight_kg     NUMERIC(10,2) NOT NULL
);

CREATE TABLE shipments (
    tracking_number     VARCHAR(30) PRIMARY KEY,
    customer_id         VARCHAR(20) NOT NULL REFERENCES customers(customer_id),
    origin_city         VARCHAR(80) NOT NULL,
    origin_country      VARCHAR(60) NOT NULL,
    destination_city    VARCHAR(80) NOT NULL,
    destination_country VARCHAR(60) NOT NULL,
    destination_address VARCHAR(200),
    service_code        VARCHAR(20) NOT NULL REFERENCES service_levels(service_code),
    status              VARCHAR(30) NOT NULL,                   -- Label Created|In Transit|Out for Delivery|Delivered|Delayed|Exception|Returned
    weight_kg           NUMERIC(10,2) NOT NULL,
    declared_value      NUMERIC(12,2) NOT NULL,
    currency            VARCHAR(6)  NOT NULL DEFAULT 'USD',
    carrier             VARCHAR(60) NOT NULL,
    dimensions_cm       VARCHAR(40),
    ship_date           DATE,
    estimated_delivery  DATE,
    actual_delivery     DATE,
    current_location    VARCHAR(120)
);

CREATE TABLE tracking_events (
    event_id        SERIAL PRIMARY KEY,
    tracking_number VARCHAR(30) NOT NULL REFERENCES shipments(tracking_number),
    event_time      TIMESTAMP   NOT NULL,
    location        VARCHAR(120) NOT NULL,
    status          VARCHAR(40)  NOT NULL,
    description     VARCHAR(200) NOT NULL
);

-- -----------------------------------------------------------------------------
-- Agent-written tables (start EMPTY; the A2A agents INSERT here)
-- -----------------------------------------------------------------------------

CREATE TABLE delivery_changes (
    change_id         SERIAL PRIMARY KEY,
    tracking_number   VARCHAR(30) NOT NULL REFERENCES shipments(tracking_number),
    customer_id       VARCHAR(20) NOT NULL REFERENCES customers(customer_id),
    change_type       VARCHAR(20) NOT NULL,                    -- Reschedule | Redirect | Hold
    new_delivery_date DATE,
    new_address       VARCHAR(200),
    reason            VARCHAR(200),
    status            VARCHAR(20) NOT NULL DEFAULT 'Requested',
    requested_at      TIMESTAMP   NOT NULL DEFAULT NOW()
);

CREATE TABLE pickup_requests (
    pickup_id      SERIAL PRIMARY KEY,
    customer_id    VARCHAR(20) NOT NULL REFERENCES customers(customer_id),
    address        VARCHAR(200) NOT NULL,
    pickup_date    DATE        NOT NULL,
    time_window    VARCHAR(40)  NOT NULL,
    package_count  INT          NOT NULL DEFAULT 1,
    notes          VARCHAR(200),
    status         VARCHAR(20)  NOT NULL DEFAULT 'Scheduled',
    requested_at   TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE TABLE claims (
    claim_id        SERIAL PRIMARY KEY,
    tracking_number VARCHAR(30) NOT NULL REFERENCES shipments(tracking_number),
    customer_id     VARCHAR(20) NOT NULL REFERENCES customers(customer_id),
    claim_type      VARCHAR(20) NOT NULL,                      -- Lost | Damaged
    description     VARCHAR(400) NOT NULL,
    claim_amount    NUMERIC(12,2) NOT NULL,
    currency        VARCHAR(6)  NOT NULL DEFAULT 'USD',
    status          VARCHAR(20) NOT NULL DEFAULT 'Submitted',
    filed_at        TIMESTAMP   NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- SEED DATA
-- =============================================================================

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
-- Engineered per scenario:
--  TRK-2026-0007  Delayed  -> flagship "redirect + email" multi-step demo
--  TRK-2026-0001  Delivered -> file a Damaged claim
--  TRK-2026-0002  In Transit on-time
--  TRK-2026-0003  Out for Delivery -> reschedule demo
--  TRK-2026-0004  Exception (address issue) -> redirect demo
--  TRK-2026-0005  Delivered on-time
--  TRK-2026-0006  Label Created (not yet shipped)
--  TRK-2026-0008  Delivered (Lost-in-transit history for claim variety)
--  TRK-2026-0009  In Transit (Nordic)
--  TRK-2026-0010  Delayed (London)
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

-- Tracking events (scan history for the active shipments) ----------------------
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

-- Agent-written tables intentionally left EMPTY (delivery_changes, pickup_requests, claims)

-- Sanity summary --------------------------------------------------------------
-- SELECT 'customers' t, COUNT(*) FROM customers
-- UNION ALL SELECT 'shipments', COUNT(*) FROM shipments
-- UNION ALL SELECT 'tracking_events', COUNT(*) FROM tracking_events;
