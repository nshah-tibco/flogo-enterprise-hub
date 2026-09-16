-- =====================================================================
-- Auto Insurance Policyholder Assistant — RESET demo data
-- Restores a clean demo state and undoes agent writes between runs.
-- Run against database: auto_insurance
--   psql -d auto_insurance -f reset_data.sql
-- =====================================================================
-- NOTE: document_index is preserved (it holds the vector store id created by the
-- RAG ingestion app). To force a fresh RAG ingest, add document_index to the
-- TRUNCATE list below and re-run the ingestion app.

TRUNCATE contact_change_log, callbacks, payments, claims, coverages, vehicles, policies, policyholders
    RESTART IDENTITY CASCADE;

-- Policyholders --------------------------------------------------------------
INSERT INTO policyholders (policyholder_id, first_name, last_name, email, phone_number, address_line1, city, state, zip, date_of_birth) VALUES
('PH-2026-0001','Michael','Carter','michael.carter@example.com','+1-415-555-0101','120 Sunset Blvd','San Jose','CA','95112','1986-03-14'),
('PH-2026-0002','Sarah','Johnson','sarah.johnson@example.com','+1-415-555-0102','48 Maple Avenue','Austin','TX','73301','1990-07-22'),
('PH-2026-0003','David','Martinez','david.martinez@example.com','+1-415-555-0103','9 Lakeshore Drive','Denver','CO','80202','1979-11-05'),
('PH-2026-0004','Emily','Chen','emily.chen@example.com','+1-415-555-0104','305 Birch Street','Seattle','WA','98101','1995-02-18'),
('PH-2026-0005','James','Wilson','james.wilson@example.com','+1-415-555-0105','77 Oakwood Lane','Chicago','IL','60601','1983-09-30'),
('PH-2026-0006','Olivia','Brown','olivia.brown@example.com','+1-415-555-0106','1450 Willow Court','Miami','FL','33101','1992-12-11'),
('PH-2026-0007','Daniel','Lee','daniel.lee@example.com','+1-415-555-0107','62 Cedar Parkway','Boston','MA','02108','1988-06-08');

-- Policies -------------------------------------------------------------------
INSERT INTO policies (policy_number, policyholder_id, product_tier, status, effective_date, renewal_date, annual_premium, payment_frequency, ncd_years, ncd_protected) VALUES
('POL-AUTO-100001','PH-2026-0001','Comprehensive',            'Active',          TO_CHAR(CURRENT_DATE - INTERVAL '250 days','YYYY-MM-DD'), TO_CHAR(CURRENT_DATE + INTERVAL '115 days','YYYY-MM-DD'), 1180.00,'Annual', 6,'Yes'),
('POL-AUTO-100002','PH-2026-0002','Comprehensive',            'Active',          TO_CHAR(CURRENT_DATE - INTERVAL '300 days','YYYY-MM-DD'), TO_CHAR(CURRENT_DATE + INTERVAL '65 days','YYYY-MM-DD'),  1345.50,'Monthly',3,'No'),
('POL-AUTO-100003','PH-2026-0003','Third Party Fire & Theft', 'Active',          TO_CHAR(CURRENT_DATE - INTERVAL '350 days','YYYY-MM-DD'), TO_CHAR(CURRENT_DATE + INTERVAL '15 days','YYYY-MM-DD'),  620.00, 'Annual', 4,'No'),
('POL-AUTO-100004','PH-2026-0004','Third Party Only',         'Active',          TO_CHAR(CURRENT_DATE - INTERVAL '120 days','YYYY-MM-DD'), TO_CHAR(CURRENT_DATE + INTERVAL '245 days','YYYY-MM-DD'), 410.00, 'Annual', 1,'No'),
('POL-AUTO-100005','PH-2026-0005','Comprehensive',            'Pending Renewal', TO_CHAR(CURRENT_DATE - INTERVAL '360 days','YYYY-MM-DD'), TO_CHAR(CURRENT_DATE + INTERVAL '5 days','YYYY-MM-DD'),   1520.00,'Annual', 8,'Yes'),
('POL-AUTO-100006','PH-2026-0006','Comprehensive',            'Lapsed',          TO_CHAR(CURRENT_DATE - INTERVAL '400 days','YYYY-MM-DD'), TO_CHAR(CURRENT_DATE - INTERVAL '35 days','YYYY-MM-DD'),  1290.00,'Monthly',2,'No'),
('POL-AUTO-100007','PH-2026-0007','Comprehensive',            'Active',          TO_CHAR(CURRENT_DATE - INTERVAL '200 days','YYYY-MM-DD'), TO_CHAR(CURRENT_DATE + INTERVAL '165 days','YYYY-MM-DD'), 1075.00,'Annual', 5,'Yes');

-- Vehicles -------------------------------------------------------------------
INSERT INTO vehicles (vehicle_id, policy_number, registration, make, model, model_year, vin, body_type, engine_cc, market_value, usage_class) VALUES
('VEH-0001','POL-AUTO-100001','7ABC123','Toyota','Camry',      2021,'JT2BF22K1W0123456','Sedan',    2500, 24500.00,'Social & Commuting'),
('VEH-0002','POL-AUTO-100002','8XYZ456','Honda', 'CR-V',       2022,'2HKRW2H85MH123457','SUV',      1500, 29800.00,'Social & Commuting'),
('VEH-0003','POL-AUTO-100003','9LMN789','Ford',  'Focus',      2018,'1FADP3F20JL123458','Hatchback',1600, 12300.00,'Social Only'),
('VEH-0004','POL-AUTO-100004','5PQR012','Nissan','Sentra',     2016,'3N1AB7AP7GY123459','Sedan',    1800,  8900.00,'Social Only'),
('VEH-0005','POL-AUTO-100005','3STU345','Tesla', 'Model 3',    2023,'5YJ3E1EA7PF123460','Sedan',    0,   41200.00,'Social & Commuting'),
('VEH-0006','POL-AUTO-100006','2VWX678','BMW',   '3 Series',   2020,'WBA5R1C50LFH12461','Sedan',    2000, 27600.00,'Business Use'),
('VEH-0007','POL-AUTO-100007','1YZA901','Subaru','Outback',    2021,'4S4BSANC5M3123462','Estate',   2500, 26100.00,'Social & Commuting');

-- Coverages ------------------------------------------------------------------
INSERT INTO coverages (coverage_id, policy_number, coverage_type, limit_amount, excess_amount, is_included) VALUES
('COV-0001','POL-AUTO-100001','Own Damage',            24500.00, 500.00,'Yes'),
('COV-0002','POL-AUTO-100001','Third Party Liability', 1000000.00, 0.00,'Yes'),
('COV-0003','POL-AUTO-100001','Fire & Theft',          24500.00, 500.00,'Yes'),
('COV-0004','POL-AUTO-100001','Windshield',            1000.00, 100.00,'Yes'),
('COV-0005','POL-AUTO-100001','Personal Accident',     50000.00, 0.00,'Yes'),
('COV-0006','POL-AUTO-100001','Roadside Assistance',   NULL, 0.00,'Yes'),
('COV-0007','POL-AUTO-100002','Own Damage',            29800.00, 750.00,'Yes'),
('COV-0008','POL-AUTO-100002','Third Party Liability', 1000000.00, 0.00,'Yes'),
('COV-0009','POL-AUTO-100002','Fire & Theft',          29800.00, 750.00,'Yes'),
('COV-0010','POL-AUTO-100002','Windshield',            1200.00, 150.00,'Yes'),
('COV-0011','POL-AUTO-100003','Third Party Liability', 750000.00, 0.00,'Yes'),
('COV-0012','POL-AUTO-100003','Fire & Theft',          12300.00, 400.00,'Yes'),
('COV-0013','POL-AUTO-100004','Third Party Liability', 500000.00, 0.00,'Yes'),
('COV-0014','POL-AUTO-100005','Own Damage',            41200.00, 1000.00,'Yes'),
('COV-0015','POL-AUTO-100005','Third Party Liability', 1000000.00, 0.00,'Yes'),
('COV-0016','POL-AUTO-100005','Fire & Theft',          41200.00, 1000.00,'Yes'),
('COV-0017','POL-AUTO-100005','Windshield',            1500.00, 100.00,'Yes'),
('COV-0018','POL-AUTO-100005','Zero Depreciation',     41200.00, 0.00,'Yes'),
('COV-0019','POL-AUTO-100005','Hire Car',              1500.00, 0.00,'Yes'),
('COV-0020','POL-AUTO-100005','Roadside Assistance',   NULL, 0.00,'Yes'),
('COV-0021','POL-AUTO-100006','Own Damage',            27600.00, 600.00,'Yes'),
('COV-0022','POL-AUTO-100006','Third Party Liability', 1000000.00, 0.00,'Yes'),
('COV-0023','POL-AUTO-100006','Fire & Theft',          27600.00, 600.00,'Yes'),
('COV-0024','POL-AUTO-100007','Own Damage',            26100.00, 500.00,'Yes'),
('COV-0025','POL-AUTO-100007','Third Party Liability', 1000000.00, 0.00,'Yes'),
('COV-0026','POL-AUTO-100007','Fire & Theft',          26100.00, 500.00,'Yes'),
('COV-0027','POL-AUTO-100007','Windshield',            1000.00, 100.00,'Yes'),
('COV-0028','POL-AUTO-100007','Personal Accident',     50000.00, 0.00,'Yes');

-- Claims (pre-seeded history) ------------------------------------------------
INSERT INTO claims (claim_number, policy_number, policyholder_id, claim_type, incident_date, description, status, estimated_amount, filed_date) VALUES
('CLM-2026-5001','POL-AUTO-100002','PH-2026-0002','Windshield', TO_CHAR(CURRENT_DATE - INTERVAL '12 days','YYYY-MM-DD'),'Cracked windshield from a stone thrown up on the highway; chip spread across driver side.','Under Review', 850.00, TO_CHAR(CURRENT_DATE - INTERVAL '10 days','YYYY-MM-DD')),
('CLM-2026-5002','POL-AUTO-100007','PH-2026-0007','Collision',  TO_CHAR(CURRENT_DATE - INTERVAL '75 days','YYYY-MM-DD'),'Rear-ended at a traffic light; rear bumper and boot damage. Third party admitted fault.','Settled', 3200.00, TO_CHAR(CURRENT_DATE - INTERVAL '72 days','YYYY-MM-DD')),
('CLM-2026-5003','POL-AUTO-100005','PH-2026-0005','Theft',      TO_CHAR(CURRENT_DATE - INTERVAL '40 days','YYYY-MM-DD'),'Attempted theft; broken door lock and damaged steering column.','Approved', 1450.00, TO_CHAR(CURRENT_DATE - INTERVAL '38 days','YYYY-MM-DD'));

-- Payments -------------------------------------------------------------------
INSERT INTO payments (payment_id, policy_number, policyholder_id, amount, due_date, paid_date, method, status, reference) VALUES
('PAY-0001','POL-AUTO-100001','PH-2026-0001',1180.00, TO_CHAR(CURRENT_DATE - INTERVAL '250 days','YYYY-MM-DD'), TO_CHAR(CURRENT_DATE - INTERVAL '250 days','YYYY-MM-DD'),'Card',        'Paid','RCPT-AUTO-0001'),
('PAY-0002','POL-AUTO-100002','PH-2026-0002',112.13,  TO_CHAR(CURRENT_DATE - INTERVAL '30 days','YYYY-MM-DD'),  TO_CHAR(CURRENT_DATE - INTERVAL '30 days','YYYY-MM-DD'), 'Card',        'Paid','RCPT-AUTO-0002'),
('PAY-0003','POL-AUTO-100002','PH-2026-0002',112.13,  TO_CHAR(CURRENT_DATE + INTERVAL '1 days','YYYY-MM-DD'),   NULL,                                                    'Card',        'Due', 'RCPT-AUTO-0003'),
('PAY-0004','POL-AUTO-100003','PH-2026-0003',620.00,  TO_CHAR(CURRENT_DATE + INTERVAL '15 days','YYYY-MM-DD'),  NULL,                                                    'Bank Transfer','Due','RCPT-AUTO-0004'),
('PAY-0005','POL-AUTO-100004','PH-2026-0004',410.00,  TO_CHAR(CURRENT_DATE - INTERVAL '120 days','YYYY-MM-DD'), TO_CHAR(CURRENT_DATE - INTERVAL '120 days','YYYY-MM-DD'),'Card',        'Paid','RCPT-AUTO-0005'),
('PAY-0006','POL-AUTO-100005','PH-2026-0005',1520.00, TO_CHAR(CURRENT_DATE + INTERVAL '5 days','YYYY-MM-DD'),   NULL,                                                    'Card',        'Due', 'RCPT-AUTO-0006'),
('PAY-0007','POL-AUTO-100006','PH-2026-0006',107.50,  TO_CHAR(CURRENT_DATE - INTERVAL '40 days','YYYY-MM-DD'),  NULL,                                                    'Card',        'Failed','RCPT-AUTO-0007'),
('PAY-0008','POL-AUTO-100007','PH-2026-0007',1075.00, TO_CHAR(CURRENT_DATE - INTERVAL '200 days','YYYY-MM-DD'), TO_CHAR(CURRENT_DATE - INTERVAL '200 days','YYYY-MM-DD'),'Bank Transfer','Paid','RCPT-AUTO-0008');

-- callbacks and contact_change_log intentionally left EMPTY (the A2A agents fill them).
-- document_index preserved across resets (see note at top).
