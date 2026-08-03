-- Hospital Post-Discharge Coordination — Database Schema & Demo Data
-- PostgreSQL 14+   |   Database: hospital
-- Built for the spec-driven Hospital use case (MCP reads + A2A writes + orchestrator).

-- Drop (reverse dependency order)
DROP TABLE IF EXISTS discharge_medications CASCADE;
DROP TABLE IF EXISTS patient_discharges CASCADE;
DROP TABLE IF EXISTS pharmacy_orders CASCADE;
DROP TABLE IF EXISTS appointments CASCADE;
DROP TABLE IF EXISTS beds CASCADE;
DROP TABLE IF EXISTS medication_catalog CASCADE;
DROP TABLE IF EXISTS patients CASCADE;
DROP TABLE IF EXISTS specialties CASCADE;

-- 1. Specialties (reference)
CREATE TABLE specialties (
    specialty_code VARCHAR(20) PRIMARY KEY,
    specialty_name VARCHAR(100) NOT NULL
);

-- 2. Patients (master; keyed by patient_id)
CREATE TABLE patients (
    patient_id   VARCHAR(20) PRIMARY KEY,   -- P-YYYY-NNNNN
    first_name   VARCHAR(50) NOT NULL,
    last_name    VARCHAR(50) NOT NULL,
    phone_number VARCHAR(20),
    email        VARCHAR(100)
);

-- 3. Patient discharges
CREATE TABLE patient_discharges (
    discharge_id       SERIAL PRIMARY KEY,
    patient_id         VARCHAR(20) NOT NULL REFERENCES patients(patient_id),
    discharge_date     VARCHAR(20) NOT NULL,     -- YYYY-MM-DD
    ward_id            VARCHAR(20),
    bed_id             VARCHAR(20),
    follow_up_required BOOLEAN NOT NULL DEFAULT FALSE,
    specialty_code     VARCHAR(20)
);

-- 4. Discharge medications
CREATE TABLE discharge_medications (
    id              SERIAL PRIMARY KEY,
    discharge_id    INTEGER NOT NULL REFERENCES patient_discharges(discharge_id),
    medication_code VARCHAR(20) NOT NULL,
    days_supply     INTEGER NOT NULL
);

-- 5. Medication catalog (reference)
CREATE TABLE medication_catalog (
    medication_code VARCHAR(20) PRIMARY KEY,
    medication_name VARCHAR(100) NOT NULL,
    ready_hours     VARCHAR(10)
);

-- 6. Appointments (written by book_appointment_agent)
CREATE TABLE appointments (
    appointment_id SERIAL PRIMARY KEY,
    patient_id     VARCHAR(20) NOT NULL,
    specialty      VARCHAR(50),
    scheduled_date VARCHAR(20),
    scheduled_time VARCHAR(10),
    status         VARCHAR(20) NOT NULL DEFAULT 'CONFIRMED'
);

-- 7. Pharmacy orders (written by pharmacy_order_agent)
CREATE TABLE pharmacy_orders (
    order_id        SERIAL PRIMARY KEY,
    patient_id      VARCHAR(20) NOT NULL,
    medication_code VARCHAR(20),
    medication_name VARCHAR(100),
    days_supply     VARCHAR(10),
    pickup_location VARCHAR(20),
    ready_by        VARCHAR(30),
    status          VARCHAR(20) NOT NULL DEFAULT 'PROCESSING'
);

-- 8. Beds (turnover managed by bed_turnover_agent)
CREATE TABLE beds (
    id              SERIAL PRIMARY KEY,
    bed_id          VARCHAR(20) NOT NULL,
    ward_id         VARCHAR(20) NOT NULL,
    patient_id      VARCHAR(20),
    status          VARCHAR(30) NOT NULL DEFAULT 'AVAILABLE',  -- AVAILABLE, OCCUPIED, CLEANING_REQUESTED, CLEANING_IN_PROGRESS
    updated_at      VARCHAR(30),
    estimated_ready VARCHAR(30)
);

-- Indexes
CREATE INDEX idx_discharges_patient ON patient_discharges(patient_id);
CREATE INDEX idx_dmeds_discharge   ON discharge_medications(discharge_id);
CREATE INDEX idx_appts_patient     ON appointments(patient_id);
CREATE INDEX idx_pharmacy_patient  ON pharmacy_orders(patient_id);
CREATE INDEX idx_beds_bed          ON beds(bed_id);

-- ============================================================
-- DEMO DATA — 10 patients with varied follow-up / medication / bed states
-- ============================================================

INSERT INTO specialties (specialty_code, specialty_name) VALUES
('CARDIOLOGY','Cardiology'),
('NEUROLOGY','Neurology'),
('ORTHOPEDICS','Orthopedics'),
('GENERAL','General Medicine'),
('ONCOLOGY','Oncology');

INSERT INTO medication_catalog (medication_code, medication_name, ready_hours) VALUES
('MED001','Aspirin 100mg','4'),
('MED002','Metoprolol 50mg','4'),
('MED003','Lisinopril 10mg','4'),
('MED004','Atorvastatin 20mg','4'),
('MED005','Omeprazole 20mg','2'),
('MED006','Paracetamol 500mg','1'),
('MED007','Amoxicillin 500mg','2'),
('MED008','Metformin 500mg','4'),
('MED009','Warfarin 5mg','4'),
('MED010','Gabapentin 300mg','3');

INSERT INTO patients (patient_id, first_name, last_name, phone_number, email) VALUES
('P-2024-00121','Alice','Ng','+65 9111 0121','alice.ng@email.com'),
('P-2024-00122','Bob','Tan','+65 9111 0122','bob.tan@email.com'),
('P-2024-00123','John','Tan','+65 9123 4567','john.tan@email.com'),
('P-2024-00124','Mary','Lim','+65 9234 5678','mary.lim@email.com'),
('P-2024-00125','David','Wong','+65 9345 6789','david.wong@email.com'),
('P-2024-00126','Sarah','Chen','+65 9456 7890','sarah.chen@email.com'),
('P-2024-00127','Michael','Lee','+65 9567 8901','michael.lee@email.com'),
('P-2024-00128','Emily','Goh','+65 9678 9012','emily.goh@email.com'),
('P-2024-00129','Grace','Lim','+65 9789 0123','grace.lim@email.com'),
('P-2024-00130','Henry','Ng','+65 9890 1234','henry.ng@email.com');

-- Discharges — insert order fixes discharge_id 1..10
INSERT INTO patient_discharges (patient_id, discharge_date, ward_id, bed_id, follow_up_required, specialty_code) VALUES
('P-2024-00123','2026-06-20','WARD-4A','BED-4A-010', TRUE,  'CARDIOLOGY'),   -- 1  full workflow, 3 meds
('P-2024-00124','2026-06-20','WARD-3B','BED-3B-002', TRUE,  'ORTHOPEDICS'),  -- 2  appt + 2 meds
('P-2024-00125','2026-06-19','WARD-2A','BED-2A-002', FALSE, NULL),           -- 3  no follow-up, 1 med
('P-2024-00126','2026-06-20','WARD-5C','BED-5C-001', TRUE,  'NEUROLOGY'),    -- 4  appt + 2 meds
('P-2024-00121','2026-06-18','WARD-2A','BED-2A-001', FALSE, NULL),           -- 5  no follow-up, no meds
('P-2024-00122','2026-06-20','WARD-3B','BED-3B-001', TRUE,  'ORTHOPEDICS'),  -- 6  appt + 1 med
('P-2024-00127','2026-06-18','WARD-4A','BED-4A-012', TRUE,  'CARDIOLOGY'),   -- 7  has existing appt/order
('P-2024-00128','2026-06-21','WARD-1A','BED-1A-001', TRUE,  'GENERAL'),      -- 8  follow-up, no meds
('P-2024-00129','2026-06-21','WARD-5C','BED-5C-002', TRUE,  'NEUROLOGY'),    -- 9  appt + 1 med
('P-2024-00130','2026-06-19','WARD-3B','BED-3B-003', FALSE, NULL);           -- 10 no follow-up, no meds

INSERT INTO discharge_medications (discharge_id, medication_code, days_supply) VALUES
(1,'MED001',30),(1,'MED002',30),(1,'MED004',30),   -- John: Aspirin, Metoprolol, Atorvastatin
(2,'MED006',7),(2,'MED005',14),                     -- Mary: Paracetamol, Omeprazole
(3,'MED007',7),                                     -- David: Amoxicillin
(4,'MED010',30),(4,'MED006',14),                    -- Sarah: Gabapentin, Paracetamol
(6,'MED006',7),                                     -- Bob: Paracetamol
(7,'MED001',30),(7,'MED004',30),                    -- Michael: Aspirin, Atorvastatin
(9,'MED010',30);                                    -- Grace: Gabapentin

-- Pre-existing appointments (for GetAppointments lookups)
INSERT INTO appointments (patient_id, specialty, scheduled_date, scheduled_time, status) VALUES
('P-2024-00127','CARDIOLOGY','2026-06-25','09:00','CONFIRMED'),
('P-2024-00124','ORTHOPEDICS','2026-06-27','14:00','CONFIRMED');

-- Pre-existing pharmacy orders
INSERT INTO pharmacy_orders (patient_id, medication_code, medication_name, days_supply, pickup_location, ready_by, status) VALUES
('P-2024-00127','MED001','Aspirin 100mg','30','PHARMACY_A','2026-06-21 14:00','READY'),
('P-2024-00124','MED006','Paracetamol 500mg','7','PHARMACY_B','2026-06-21 16:00','PROCESSING');

-- Beds (mixed statuses across wards)
INSERT INTO beds (bed_id, ward_id, patient_id, status, updated_at, estimated_ready) VALUES
('BED-4A-010','WARD-4A','P-2024-00123','OCCUPIED','2026-06-20 08:00',NULL),
('BED-4A-011','WARD-4A',NULL,'AVAILABLE','2026-06-20 10:00',NULL),
('BED-4A-012','WARD-4A','P-2024-00127','OCCUPIED','2026-06-20 09:00',NULL),
('BED-3B-001','WARD-3B','P-2024-00122','OCCUPIED','2026-06-20 07:30',NULL),
('BED-3B-002','WARD-3B','P-2024-00124','OCCUPIED','2026-06-20 08:15',NULL),
('BED-3B-003','WARD-3B',NULL,'CLEANING_IN_PROGRESS','2026-06-20 14:00','2026-06-20 14:30'),
('BED-2A-001','WARD-2A','P-2024-00121','OCCUPIED','2026-06-18 09:00',NULL),
('BED-2A-002','WARD-2A','P-2024-00125','OCCUPIED','2026-06-19 09:00',NULL),
('BED-5C-001','WARD-5C','P-2024-00126','OCCUPIED','2026-06-20 07:00',NULL),
('BED-5C-002','WARD-5C','P-2024-00129','OCCUPIED','2026-06-21 07:00',NULL),
('BED-1A-001','WARD-1A','P-2024-00128','OCCUPIED','2026-06-21 08:00',NULL),
('BED-1A-002','WARD-1A',NULL,'AVAILABLE','2026-06-20 11:00',NULL);
