-- Hospital Post-Discharge — Reset Demo Data
-- Restores a clean baseline (removes agent-written appointments/pharmacy orders beyond the
-- pre-seeded two, and resets bed statuses). Discharge dates are relative to today so that
-- "book follow-up 7 days from discharge" lands in the future during live demos.
-- PostgreSQL 14+

TRUNCATE discharge_medications, patient_discharges, pharmacy_orders, appointments,
         beds, medication_catalog, patients, specialties RESTART IDENTITY CASCADE;

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

-- Discharges (discharge_id 1..10 by insert order); dates relative to today
INSERT INTO patient_discharges (patient_id, discharge_date, ward_id, bed_id, follow_up_required, specialty_code) VALUES
('P-2024-00123', to_char(CURRENT_DATE, 'YYYY-MM-DD'),                      'WARD-4A','BED-4A-010', TRUE,  'CARDIOLOGY'),
('P-2024-00124', to_char(CURRENT_DATE, 'YYYY-MM-DD'),                      'WARD-3B','BED-3B-002', TRUE,  'ORTHOPEDICS'),
('P-2024-00125', to_char(CURRENT_DATE - INTERVAL '1 day','YYYY-MM-DD'),    'WARD-2A','BED-2A-002', FALSE, NULL),
('P-2024-00126', to_char(CURRENT_DATE, 'YYYY-MM-DD'),                      'WARD-5C','BED-5C-001', TRUE,  'NEUROLOGY'),
('P-2024-00121', to_char(CURRENT_DATE - INTERVAL '2 days','YYYY-MM-DD'),   'WARD-2A','BED-2A-001', FALSE, NULL),
('P-2024-00122', to_char(CURRENT_DATE, 'YYYY-MM-DD'),                      'WARD-3B','BED-3B-001', TRUE,  'ORTHOPEDICS'),
('P-2024-00127', to_char(CURRENT_DATE - INTERVAL '2 days','YYYY-MM-DD'),   'WARD-4A','BED-4A-012', TRUE,  'CARDIOLOGY'),
('P-2024-00128', to_char(CURRENT_DATE + INTERVAL '1 day','YYYY-MM-DD'),    'WARD-1A','BED-1A-001', TRUE,  'GENERAL'),
('P-2024-00129', to_char(CURRENT_DATE + INTERVAL '1 day','YYYY-MM-DD'),    'WARD-5C','BED-5C-002', TRUE,  'NEUROLOGY'),
('P-2024-00130', to_char(CURRENT_DATE - INTERVAL '1 day','YYYY-MM-DD'),    'WARD-3B','BED-3B-003', FALSE, NULL);

INSERT INTO discharge_medications (discharge_id, medication_code, days_supply) VALUES
(1,'MED001',30),(1,'MED002',30),(1,'MED004',30),
(2,'MED006',7),(2,'MED005',14),
(3,'MED007',7),
(4,'MED010',30),(4,'MED006',14),
(6,'MED006',7),
(7,'MED001',30),(7,'MED004',30),
(9,'MED010',30);

INSERT INTO appointments (patient_id, specialty, scheduled_date, scheduled_time, status) VALUES
('P-2024-00127','CARDIOLOGY', to_char(CURRENT_DATE + INTERVAL '5 days','YYYY-MM-DD'),'09:00','CONFIRMED'),
('P-2024-00124','ORTHOPEDICS',to_char(CURRENT_DATE + INTERVAL '7 days','YYYY-MM-DD'),'14:00','CONFIRMED');

INSERT INTO pharmacy_orders (patient_id, medication_code, medication_name, days_supply, pickup_location, ready_by, status) VALUES
('P-2024-00127','MED001','Aspirin 100mg','30','PHARMACY_A', to_char(CURRENT_DATE + INTERVAL '1 day','YYYY-MM-DD')||' 14:00','READY'),
('P-2024-00124','MED006','Paracetamol 500mg','7','PHARMACY_B', to_char(CURRENT_DATE + INTERVAL '1 day','YYYY-MM-DD')||' 16:00','PROCESSING');

INSERT INTO beds (bed_id, ward_id, patient_id, status, updated_at, estimated_ready) VALUES
('BED-4A-010','WARD-4A','P-2024-00123','OCCUPIED', to_char(CURRENT_DATE,'YYYY-MM-DD')||' 08:00',NULL),
('BED-4A-011','WARD-4A',NULL,'AVAILABLE', to_char(CURRENT_DATE,'YYYY-MM-DD')||' 10:00',NULL),
('BED-4A-012','WARD-4A','P-2024-00127','OCCUPIED', to_char(CURRENT_DATE,'YYYY-MM-DD')||' 09:00',NULL),
('BED-3B-001','WARD-3B','P-2024-00122','OCCUPIED', to_char(CURRENT_DATE,'YYYY-MM-DD')||' 07:30',NULL),
('BED-3B-002','WARD-3B','P-2024-00124','OCCUPIED', to_char(CURRENT_DATE,'YYYY-MM-DD')||' 08:15',NULL),
('BED-3B-003','WARD-3B',NULL,'CLEANING_IN_PROGRESS', to_char(CURRENT_DATE,'YYYY-MM-DD')||' 14:00', to_char(CURRENT_DATE,'YYYY-MM-DD')||' 14:30'),
('BED-2A-001','WARD-2A','P-2024-00121','OCCUPIED', to_char(CURRENT_DATE - INTERVAL '2 days','YYYY-MM-DD')||' 09:00',NULL),
('BED-2A-002','WARD-2A','P-2024-00125','OCCUPIED', to_char(CURRENT_DATE - INTERVAL '1 day','YYYY-MM-DD')||' 09:00',NULL),
('BED-5C-001','WARD-5C','P-2024-00126','OCCUPIED', to_char(CURRENT_DATE,'YYYY-MM-DD')||' 07:00',NULL),
('BED-5C-002','WARD-5C','P-2024-00129','OCCUPIED', to_char(CURRENT_DATE + INTERVAL '1 day','YYYY-MM-DD')||' 07:00',NULL),
('BED-1A-001','WARD-1A','P-2024-00128','OCCUPIED', to_char(CURRENT_DATE + INTERVAL '1 day','YYYY-MM-DD')||' 08:00',NULL),
('BED-1A-002','WARD-1A',NULL,'AVAILABLE', to_char(CURRENT_DATE,'YYYY-MM-DD')||' 11:00',NULL);
