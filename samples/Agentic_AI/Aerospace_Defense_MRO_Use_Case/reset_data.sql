-- Aerospace & Defense - MRO & AOG Operations Assistant - Reset Demo Data
-- PostgreSQL 14+  |  Database: aerospace_mro
-- Restores a clean demo state and undoes agent writes. Volatile dates are CURRENT_DATE-relative.
-- Run:  psql -d aerospace_mro -f reset_data.sql

TRUNCATE notification_log, aog_incidents, part_orders, parts_inventory, work_orders, technicians, aircraft
    RESTART IDENTITY CASCADE;

-- Reset the agent id sequences so re-runs start clean (no drift, no collisions with seed ids).
ALTER SEQUENCE wo_seq RESTART WITH 200;
ALTER SEQUENCE po_seq RESTART WITH 100;

-- Aircraft (8)
INSERT INTO aircraft (tail_number, model, platform_type, base_location, flight_hours, cycles, status, next_check_type, next_check_due) VALUES
('N738MA', 'Boeing 737-700',                 'Commercial', 'Meridian Field', 24500, 12300, 'IN_SERVICE',     'A-Check',           CURRENT_DATE + INTERVAL '5 days'),
('N901MA', 'Boeing 737-800',                 'Commercial', 'Meridian Field', 31000, 15400, 'IN_SERVICE',     'C-Check',           CURRENT_DATE + INTERVAL '60 days'),
('N512MA', 'Bombardier Challenger 650',      'Commercial', 'Meridian Field',  8900,  4100, 'IN_SERVICE',     'C-Check',           CURRENT_DATE + INTERVAL '40 days'),
('N245MA', 'Gulfstream G550',                'Commercial', 'Meridian Field', 11200,  5000, 'GROUNDED',       'AD Compliance',     CURRENT_DATE + INTERVAL '7 days'),
('AD-0142','Lockheed C-130J-30 Super Hercules','Defense',  'Edwards AFB',    15200,  6800, 'AOG',            'Phase Inspection',  CURRENT_DATE + INTERVAL '2 days'),
('AD-0177','Lockheed C-130J-30 Super Hercules','Defense',  'Edwards AFB',    14000,  6300, 'IN_SERVICE',     'Phase Inspection',  CURRENT_DATE + INTERVAL '25 days'),
('AD-0198','Beechcraft King Air 350ER ISR',  'Defense',    'Palmdale',        6400,  5900, 'IN_MAINTENANCE', 'Phase Inspection',  CURRENT_DATE + INTERVAL '10 days'),
('AD-0203','Sikorsky UH-60M Black Hawk',     'Defense',    'Edwards AFB',     3100,  2200, 'IN_SERVICE',     '100-Hour',          CURRENT_DATE + INTERVAL '15 days');

-- Technicians (6)
INSERT INTO technicians (tech_id, name, base_location, certifications, shift, availability, email, phone) VALUES
('TECH-101','Marcus Reid',    'Edwards AFB',    'Hydraulics, Powerplant, C-130J', 'Day',   'AVAILABLE', 'marcus.reid@meridian-ad.example',   '+1-661-555-0142'),
('TECH-102','Elena Vargas',   'Meridian Field', 'Avionics, Electrical, Boeing 737','Day',  'ON_SHIFT',  'elena.vargas@meridian-ad.example',  '+1-480-555-0110'),
('TECH-103','David Okafor',   'Meridian Field', 'Powerplant, APU, Boeing 737',    'Night', 'AVAILABLE', 'david.okafor@meridian-ad.example',  '+1-480-555-0133'),
('TECH-104','Priya Nair',     'Palmdale',       'Structures, Landing Gear, King Air','Day', 'ON_SHIFT',  'priya.nair@meridian-ad.example',    '+1-661-555-0177'),
('TECH-105','Sam Whitfield',  'Edwards AFB',    'Rotary, Rotor Systems, UH-60',   'Swing', 'AVAILABLE', 'sam.whitfield@meridian-ad.example', '+1-661-555-0205'),
('TECH-106','Lena Torres',    'Meridian Field', 'Avionics, Structures, Gulfstream','Day',  'OFF',       'lena.torres@meridian-ad.example',   '+1-480-555-0166');

-- Work Orders (10)
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

-- Parts Inventory (10)
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

-- Part Orders (2 pre-seeded)
INSERT INTO part_orders (order_id, part_number, quantity, tail_number, wo_number, priority, status, ordered_date, expected_delivery) VALUES
('PO-2026-0001','PN-8830-C', 1, 'AD-0198','WO-2026-00102','EXPEDITE','IN_TRANSIT', CURRENT_DATE - INTERVAL '5 days', CURRENT_DATE + INTERVAL '3 days'),
('PO-2026-0002','PN-6621-G', 1, 'N901MA', 'WO-2026-00104','ROUTINE', 'ORDERED',    CURRENT_DATE - INTERVAL '1 day',  CURRENT_DATE + INTERVAL '17 days');

-- AOG Incidents (3)
INSERT INTO aog_incidents (aog_id, tail_number, location, reported_at, reason, severity, status, resolution) VALUES
('AOG-2026-001','AD-0142','Edwards AFB', CURRENT_TIMESTAMP - INTERVAL '1 day',  'No.2 hydraulic system pump failure found during pre-flight; aircraft grounded', 'CRITICAL','OPEN',     NULL),
('AOG-2026-002','AD-0198','Palmdale',    CURRENT_TIMESTAMP - INTERVAL '3 days', 'Main landing gear actuator leak found on phase inspection',                     'HIGH',    'RESOLVING','Expedite order PO-2026-0001 placed; technician TECH-104 assigned'),
('AOG-2026-003','N901MA', 'Meridian Field',CURRENT_TIMESTAMP - INTERVAL '6 days','Cabin pressurization controller intermittent fault',                            'MEDIUM',  'RESOLVED', 'Controller PN-6621-G replaced; aircraft returned to service');

-- notification_log intentionally left empty
