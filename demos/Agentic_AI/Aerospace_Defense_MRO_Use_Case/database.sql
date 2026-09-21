-- Aerospace & Defense - MRO & AOG Operations Assistant - Database Schema & Demo Data
-- PostgreSQL 14+
-- Database: aerospace_mro
-- Dataset: 8 aircraft, 10 work orders, 10 parts, 6 technicians, 3 AOG incidents
-- Demo data is engineered per scenario (one clean/happy-path record + one exception per write agent).

-- Drop existing objects (reverse dependency order)
DROP TABLE IF EXISTS notification_log CASCADE;
DROP TABLE IF EXISTS aog_incidents CASCADE;
DROP TABLE IF EXISTS part_orders CASCADE;
DROP TABLE IF EXISTS parts_inventory CASCADE;
DROP TABLE IF EXISTS work_orders CASCADE;
DROP TABLE IF EXISTS technicians CASCADE;
DROP TABLE IF EXISTS aircraft CASCADE;
DROP SEQUENCE IF EXISTS wo_seq;
DROP SEQUENCE IF EXISTS po_seq;

-- Sequences used by the A2A write agents to mint unique ids without colliding with seed rows.
CREATE SEQUENCE wo_seq START 200;   -- schedule_maintenance_agent -> WO-2026-00200+
CREATE SEQUENCE po_seq START 100;   -- order_part_agent          -> PO-2026-0100+

-- 1. Aircraft - fleet master, keyed by tail_number (the natural id used in chat)
CREATE TABLE aircraft (
    id              SERIAL PRIMARY KEY,
    tail_number     VARCHAR(12) NOT NULL UNIQUE,
    model           VARCHAR(60) NOT NULL,
    platform_type   VARCHAR(20) NOT NULL,               -- Commercial, Defense
    base_location   VARCHAR(60) NOT NULL,
    flight_hours    INTEGER NOT NULL DEFAULT 0,
    cycles          INTEGER NOT NULL DEFAULT 0,
    status          VARCHAR(20) NOT NULL DEFAULT 'IN_SERVICE', -- IN_SERVICE, IN_MAINTENANCE, AOG, GROUNDED
    next_check_type VARCHAR(30),                         -- A-Check, C-Check, Phase Inspection, 100-Hour
    next_check_due  DATE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_ac_status   CHECK (status IN ('IN_SERVICE','IN_MAINTENANCE','AOG','GROUNDED')),
    CONSTRAINT chk_ac_platform CHECK (platform_type IN ('Commercial','Defense'))
);

-- 2. Technicians - maintenance roster with certifications + availability
CREATE TABLE technicians (
    id              SERIAL PRIMARY KEY,
    tech_id         VARCHAR(20) NOT NULL UNIQUE,         -- TECH-101
    name            VARCHAR(80) NOT NULL,
    base_location   VARCHAR(60) NOT NULL,
    certifications  VARCHAR(200) NOT NULL,               -- comma-separated skills
    shift           VARCHAR(20),                         -- Day, Night, Swing
    availability    VARCHAR(15) NOT NULL DEFAULT 'AVAILABLE', -- AVAILABLE, ON_SHIFT, OFF
    email           VARCHAR(100),
    phone           VARCHAR(30),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_tech_avail CHECK (availability IN ('AVAILABLE','ON_SHIFT','OFF'))
);

-- 3. Work Orders - maintenance work orders; write-target for schedule_maintenance_agent.
--    Closed rows double as maintenance history.
CREATE TABLE work_orders (
    id              SERIAL PRIMARY KEY,
    wo_number       VARCHAR(20) NOT NULL UNIQUE,         -- WO-2026-00101
    tail_number     VARCHAR(12) NOT NULL REFERENCES aircraft(tail_number),
    wo_type         VARCHAR(20) NOT NULL,                -- Scheduled, Unscheduled, AOG, Inspection
    description     VARCHAR(300) NOT NULL,
    priority        VARCHAR(10) NOT NULL DEFAULT 'ROUTINE', -- ROUTINE, URGENT, AOG
    status          VARCHAR(20) NOT NULL DEFAULT 'OPEN',    -- OPEN, IN_PROGRESS, AWAITING_PARTS, CLOSED
    opened_date     DATE NOT NULL DEFAULT CURRENT_DATE,
    due_date        DATE,
    assigned_technician VARCHAR(20),                     -- tech_id or NULL
    closed_date     DATE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_wo_type     CHECK (wo_type IN ('Scheduled','Unscheduled','AOG','Inspection')),
    CONSTRAINT chk_wo_priority CHECK (priority IN ('ROUTINE','URGENT','AOG')),
    CONSTRAINT chk_wo_status   CHECK (status IN ('OPEN','IN_PROGRESS','AWAITING_PARTS','CLOSED'))
);

-- 4. Parts Inventory - spares stock with reorder levels + lead times
CREATE TABLE parts_inventory (
    id               SERIAL PRIMARY KEY,
    part_number      VARCHAR(30) NOT NULL UNIQUE,        -- PN-4471-A
    description      VARCHAR(150) NOT NULL,
    applicable_model VARCHAR(60),
    quantity_on_hand INTEGER NOT NULL DEFAULT 0,
    reorder_level    INTEGER NOT NULL DEFAULT 0,
    warehouse_location VARCHAR(60),
    unit_price       NUMERIC(10,2),
    lead_time_days   INTEGER DEFAULT 0,
    supplier         VARCHAR(80),
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Part Orders - part order/expedite records; write-target for order_part_agent
CREATE TABLE part_orders (
    id              SERIAL PRIMARY KEY,
    order_id        VARCHAR(20) NOT NULL UNIQUE,         -- PO-2026-0001
    part_number     VARCHAR(30) NOT NULL,
    quantity        INTEGER NOT NULL,
    tail_number     VARCHAR(12),
    wo_number       VARCHAR(20),
    priority        VARCHAR(10) NOT NULL DEFAULT 'ROUTINE', -- ROUTINE, EXPEDITE
    status          VARCHAR(15) NOT NULL DEFAULT 'ORDERED', -- ORDERED, IN_TRANSIT, RECEIVED
    ordered_date    DATE NOT NULL DEFAULT CURRENT_DATE,
    expected_delivery DATE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_po_priority CHECK (priority IN ('ROUTINE','EXPEDITE')),
    CONSTRAINT chk_po_status   CHECK (status IN ('ORDERED','IN_TRANSIT','RECEIVED'))
);

-- 6. AOG Incidents - Aircraft-on-Ground events; status updated during triage
CREATE TABLE aog_incidents (
    id              SERIAL PRIMARY KEY,
    aog_id          VARCHAR(20) NOT NULL UNIQUE,         -- AOG-2026-001
    tail_number     VARCHAR(12) NOT NULL REFERENCES aircraft(tail_number),
    location        VARCHAR(80) NOT NULL,
    reported_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reason          VARCHAR(250) NOT NULL,
    severity        VARCHAR(15) NOT NULL DEFAULT 'HIGH', -- CRITICAL, HIGH, MEDIUM
    status          VARCHAR(15) NOT NULL DEFAULT 'OPEN', -- OPEN, RESOLVING, RESOLVED
    resolution      VARCHAR(300),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_aog_sev    CHECK (severity IN ('CRITICAL','HIGH','MEDIUM')),
    CONSTRAINT chk_aog_status CHECK (status IN ('OPEN','RESOLVING','RESOLVED'))
);

-- 7. Notification Log - email audit; write-only, filled by send_confirmation_email_agent
CREATE TABLE notification_log (
    id              SERIAL PRIMARY KEY,
    recipient       VARCHAR(100) NOT NULL,
    subject         VARCHAR(200),
    body            TEXT,
    sent_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes on identifiers + foreign keys
CREATE INDEX idx_wo_tail       ON work_orders(tail_number);
CREATE INDEX idx_wo_status     ON work_orders(status);
CREATE INDEX idx_po_part       ON part_orders(part_number);
CREATE INDEX idx_aog_tail      ON aog_incidents(tail_number);
CREATE INDEX idx_aog_status    ON aog_incidents(status);

-- =====================================================================
-- DEMO DATA
-- =====================================================================

-- Aircraft (8): mixed commercial-derivative + defense; AD-0142 is the flagship AOG.
INSERT INTO aircraft (tail_number, model, platform_type, base_location, flight_hours, cycles, status, next_check_type, next_check_due) VALUES
('N738MA', 'Boeing 737-700',                 'Commercial', 'Meridian Field', 24500, 12300, 'IN_SERVICE',     'A-Check',           CURRENT_DATE + INTERVAL '5 days'),
('N901MA', 'Boeing 737-800',                 'Commercial', 'Meridian Field', 31000, 15400, 'IN_SERVICE',     'C-Check',           CURRENT_DATE + INTERVAL '60 days'),
('N512MA', 'Bombardier Challenger 650',      'Commercial', 'Meridian Field',  8900,  4100, 'IN_SERVICE',     'C-Check',           CURRENT_DATE + INTERVAL '40 days'),
('N245MA', 'Gulfstream G550',                'Commercial', 'Meridian Field', 11200,  5000, 'GROUNDED',       'AD Compliance',     CURRENT_DATE + INTERVAL '7 days'),
('AD-0142','Lockheed C-130J-30 Super Hercules','Defense',  'Edwards AFB',    15200,  6800, 'AOG',            'Phase Inspection',  CURRENT_DATE + INTERVAL '2 days'),
('AD-0177','Lockheed C-130J-30 Super Hercules','Defense',  'Edwards AFB',    14000,  6300, 'IN_SERVICE',     'Phase Inspection',  CURRENT_DATE + INTERVAL '25 days'),
('AD-0198','Beechcraft King Air 350ER ISR',  'Defense',    'Palmdale',        6400,  5900, 'IN_MAINTENANCE', 'Phase Inspection',  CURRENT_DATE + INTERVAL '10 days'),
('AD-0203','Sikorsky UH-60M Black Hawk',     'Defense',    'Edwards AFB',     3100,  2200, 'IN_SERVICE',     '100-Hour',          CURRENT_DATE + INTERVAL '15 days');

-- Technicians (6): TECH-101 (Marcus Reid) is the hydraulics/C-130J tech for the AOG flagship.
INSERT INTO technicians (tech_id, name, base_location, certifications, shift, availability, email, phone) VALUES
('TECH-101','Marcus Reid',    'Edwards AFB',    'Hydraulics, Powerplant, C-130J', 'Day',   'AVAILABLE', 'marcus.reid@meridian-ad.example',   '+1-661-555-0142'),
('TECH-102','Elena Vargas',   'Meridian Field', 'Avionics, Electrical, Boeing 737','Day',  'ON_SHIFT',  'elena.vargas@meridian-ad.example',  '+1-480-555-0110'),
('TECH-103','David Okafor',   'Meridian Field', 'Powerplant, APU, Boeing 737',    'Night', 'AVAILABLE', 'david.okafor@meridian-ad.example',  '+1-480-555-0133'),
('TECH-104','Priya Nair',     'Palmdale',       'Structures, Landing Gear, King Air','Day', 'ON_SHIFT',  'priya.nair@meridian-ad.example',    '+1-661-555-0177'),
('TECH-105','Sam Whitfield',  'Edwards AFB',    'Rotary, Rotor Systems, UH-60',   'Swing', 'AVAILABLE', 'sam.whitfield@meridian-ad.example', '+1-661-555-0205'),
('TECH-106','Lena Torres',    'Meridian Field', 'Avionics, Structures, Gulfstream','Day',  'OFF',       'lena.torres@meridian-ad.example',   '+1-480-555-0166');

-- Work Orders (10): open/in-progress/awaiting-parts/closed mix. WO-2026-00101 = AOG hydraulic pump.
INSERT INTO work_orders (wo_number, tail_number, wo_type, description, priority, status, opened_date, due_date, assigned_technician, closed_date) VALUES
('WO-2026-00101','AD-0142','AOG',        'No.2 hydraulic system pump failure - aircraft AOG at Edwards; awaiting pump PN-4471-A', 'AOG',    'AWAITING_PARTS', CURRENT_DATE - INTERVAL '1 day',  CURRENT_DATE + INTERVAL '1 day',  NULL,       NULL),
('WO-2026-00102','AD-0198','Inspection', 'Phase 2 inspection - main landing gear actuator leak (PN-8830-C on order)',            'URGENT', 'AWAITING_PARTS', CURRENT_DATE - INTERVAL '3 days', CURRENT_DATE + INTERVAL '7 days', 'TECH-104',  NULL),
('WO-2026-00103','AD-0203','Scheduled',  '100-hour inspection - rotor system and drivetrain checks',                             'ROUTINE','OPEN',           CURRENT_DATE - INTERVAL '1 day',  CURRENT_DATE + INTERVAL '15 days', NULL,       NULL),
('WO-2026-00104','N901MA','Unscheduled', 'Cabin pressurization intermittent warning - controller replacement in progress',       'URGENT', 'IN_PROGRESS',    CURRENT_DATE - INTERVAL '2 days', CURRENT_DATE + INTERVAL '3 days', 'TECH-102',  NULL),
('WO-2026-00105','N512MA','Scheduled',   'Engine borescope inspection - both engines',                                           'ROUTINE','OPEN',           CURRENT_DATE - INTERVAL '1 day',  CURRENT_DATE + INTERVAL '12 days', NULL,       NULL),
('WO-2026-00106','AD-0177','Inspection', 'Phase 1 inspection - completed, returned to service',                                  'ROUTINE','CLOSED',         CURRENT_DATE - INTERVAL '18 days',CURRENT_DATE - INTERVAL '10 days','TECH-101',  CURRENT_DATE - INTERVAL '10 days'),
('WO-2026-00107','N738MA','Unscheduled', 'APU fault code investigation - starter PN-3315-E replaced',                            'ROUTINE','CLOSED',         CURRENT_DATE - INTERVAL '25 days',CURRENT_DATE - INTERVAL '20 days','TECH-103',  CURRENT_DATE - INTERVAL '20 days'),
('WO-2026-00108','N245MA','Unscheduled', 'AD compliance - wing spar inspection required before next flight',                     'URGENT', 'OPEN',           CURRENT_DATE - INTERVAL '2 days', CURRENT_DATE + INTERVAL '7 days', NULL,       NULL),
('WO-2026-00109','AD-0142','Inspection', 'Phase inspection deferred pending AOG pump replacement',                              'ROUTINE','OPEN',           CURRENT_DATE - INTERVAL '1 day',  CURRENT_DATE + INTERVAL '2 days', NULL,       NULL),
('WO-2026-00110','AD-0203','Scheduled',  'Main rotor blade track and balance - completed',                                       'ROUTINE','CLOSED',         CURRENT_DATE - INTERVAL '8 days', CURRENT_DATE - INTERVAL '5 days', 'TECH-105',  CURRENT_DATE - INTERVAL '5 days');

-- Parts Inventory (10): PN-4471-A below reorder (AOG flagship), PN-8830-C out of stock (long lead).
INSERT INTO parts_inventory (part_number, description, applicable_model, quantity_on_hand, reorder_level, warehouse_location, unit_price, lead_time_days, supplier) VALUES
('PN-4471-A','Hydraulic Pump Assembly, No.2 System','C-130J-30',        1, 2, 'Warehouse A - Edwards',  48750.00, 21, 'Parker Aerospace'),
('PN-4471-B','Hydraulic Pump Seal Kit',             'C-130J-30',       10, 4, 'Warehouse A - Edwards',    850.00,  5, 'Parker Aerospace'),
('PN-2210-B','Avionics Multifunction Display Unit', 'King Air 350ER',   5, 2, 'Warehouse B - Palmdale', 22100.00, 14, 'Collins Aerospace'),
('PN-8830-C','Main Landing Gear Actuator',          'King Air 350ER',   0, 1, 'Warehouse B - Palmdale', 63400.00, 45, 'Heroux-Devtek'),
('PN-1002-D','Brake Assembly',                      'Boeing 737',       8, 3, 'Warehouse A - Edwards',   9800.00, 10, 'Honeywell'),
('PN-3315-E','APU Starter',                         'Boeing 737',       3, 2, 'Warehouse A - Edwards',  15200.00, 12, 'Honeywell'),
('PN-5540-F','Main Rotor Blade',                    'UH-60M',           4, 2, 'Warehouse C - Edwards',  38900.00, 30, 'Sikorsky'),
('PN-6621-G','Cabin Pressurization Controller',     'Boeing 737',       2, 1, 'Warehouse A - Edwards',  12750.00, 18, 'Honeywell'),
('PN-7788-H','Engine Fuel Nozzle Set',              'Challenger 650',   6, 2, 'Warehouse B - Palmdale',  7400.00,  9, 'GE Aerospace'),
('PN-9012-J','Wing Spar Inspection Kit',            'Gulfstream G550',  2, 1, 'Warehouse B - Palmdale',  3100.00,  7, 'Gulfstream');

-- Part Orders (2 pre-seeded so GetPartOrders has status to show; rest agent-written)
INSERT INTO part_orders (order_id, part_number, quantity, tail_number, wo_number, priority, status, ordered_date, expected_delivery) VALUES
('PO-2026-0001','PN-8830-C', 1, 'AD-0198','WO-2026-00102','EXPEDITE','IN_TRANSIT', CURRENT_DATE - INTERVAL '5 days', CURRENT_DATE + INTERVAL '3 days'),
('PO-2026-0002','PN-6621-G', 1, 'N901MA', 'WO-2026-00104','ROUTINE', 'ORDERED',    CURRENT_DATE - INTERVAL '1 day',  CURRENT_DATE + INTERVAL '17 days');

-- AOG Incidents (3): AOG-2026-001 = flagship OPEN; one RESOLVING; one RESOLVED (history).
INSERT INTO aog_incidents (aog_id, tail_number, location, reported_at, reason, severity, status, resolution) VALUES
('AOG-2026-001','AD-0142','Edwards AFB', CURRENT_TIMESTAMP - INTERVAL '1 day',  'No.2 hydraulic system pump failure found during pre-flight; aircraft grounded', 'CRITICAL','OPEN',     NULL),
('AOG-2026-002','AD-0198','Palmdale',    CURRENT_TIMESTAMP - INTERVAL '3 days', 'Main landing gear actuator leak found on phase inspection',                     'HIGH',    'RESOLVING','Expedite order PO-2026-0001 placed; technician TECH-104 assigned'),
('AOG-2026-003','N901MA', 'Meridian Field',CURRENT_TIMESTAMP - INTERVAL '6 days','Cabin pressurization controller intermittent fault',                            'MEDIUM',  'RESOLVED', 'Controller PN-6621-G replaced; aircraft returned to service');

-- notification_log intentionally left empty (filled by send_confirmation_email_agent)
