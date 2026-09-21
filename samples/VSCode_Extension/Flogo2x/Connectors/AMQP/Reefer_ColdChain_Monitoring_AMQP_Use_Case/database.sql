-- =====================================================================
-- Reefer Cold-Chain Monitoring — PostgreSQL schema + seed data
-- Database: reefer_monitoring
-- Used by: ReeferMonitorProcessor_AMQP.flogo (consumer/processor app)
--   * reefer_containers  — reference data (per-container setpoint, tolerance,
--                          cargo, customer, destination) used to ENRICH each
--                          telemetry reading and decide if it is a breach.
--   * reefer_alerts      — audit trail of every breach the processor detects.
--
-- Setup:
--   createdb -U postgres reefer_monitoring
--   psql -U postgres -d reefer_monitoring -f database.sql
-- =====================================================================

DROP TABLE IF EXISTS reefer_alerts;
DROP TABLE IF EXISTS reefer_containers;

-- ---------------------------------------------------------------------
-- Reference: registered reefer containers and their cargo profiles.
-- A reading is "normal" when power is ON and the temperature is within
-- [set_point_c - allowed_deviation_c , set_point_c + allowed_deviation_c].
-- ---------------------------------------------------------------------
CREATE TABLE reefer_containers (
    container_id        VARCHAR(20)  PRIMARY KEY,
    cargo_type          VARCHAR(60)  NOT NULL,
    set_point_c         NUMERIC(5,2) NOT NULL,   -- target temperature (Celsius)
    allowed_deviation_c NUMERIC(5,2) NOT NULL,   -- +/- tolerance band (Celsius)
    customer_name       VARCHAR(80)  NOT NULL,
    destination_port    VARCHAR(60)  NOT NULL,
    priority            VARCHAR(10)  NOT NULL     -- HIGH | MEDIUM | LOW
);

-- ---------------------------------------------------------------------
-- Audit: one row per detected breach (temperature excursion or power loss).
-- alert_id / alerted_at are DB-generated so each processed tick is stamped.
-- ---------------------------------------------------------------------
CREATE TABLE reefer_alerts (
    alert_id        SERIAL PRIMARY KEY,
    container_id    VARCHAR(20)  NOT NULL,
    cargo_type      VARCHAR(60),
    reported_temp_c NUMERIC(6,2),
    set_point_c     NUMERIC(5,2),
    deviation_c     NUMERIC(5,2),
    power_status    VARCHAR(10),
    alert_reason    TEXT,
    event_time      VARCHAR(40),                 -- reading timestamp (as reported)
    alerted_at      TIMESTAMP DEFAULT now()      -- when the processor persisted it
);

-- ---------------------------------------------------------------------
-- Seed containers. The first five (RCON-1001..1005) are the fleet the
-- ReeferTelemetryPublisher_AMQP app streams every tick:
--   RCON-1001 vaccines  -20+/-2  -> reading -20.1 ON  = NORMAL
--   RCON-1002 seafood   -18+/-3  -> reading  -8.0 ON  = BREACH (too warm)
--   RCON-1003 produce    13+/-1  -> reading  13.2 OFF = BREACH (power off)
--   RCON-1004 dairy       4+/-2  -> reading   4.2 ON  = NORMAL
--   RCON-1005 insulin     5+/-1  -> reading   9.3 ON  = BREACH (too warm, HIGH pri)
-- RCON-1006 / RCON-1007 are extra profiles for manual test publishes.
-- ---------------------------------------------------------------------
INSERT INTO reefer_containers
    (container_id, cargo_type, set_point_c, allowed_deviation_c, customer_name, destination_port, priority)
VALUES
    ('RCON-1001', 'Pharma-Vaccines',  -20, 2, 'Singapore BioPharma', 'Rotterdam',    'HIGH'),
    ('RCON-1002', 'Frozen Seafood',   -18, 3, 'Ocean Harvest Ltd',   'Hamburg',      'MEDIUM'),
    ('RCON-1003', 'Fresh Produce',     13, 1, 'Tropical Fruits Co',  'Yokohama',     'MEDIUM'),
    ('RCON-1004', 'Dairy',              4, 2, 'DairyBest Exports',   'Sydney',       'LOW'),
    ('RCON-1005', 'Pharma-Insulin',     5, 1, 'MediCore Logistics',  'Los Angeles',  'HIGH'),
    ('RCON-1006', 'Frozen Meat',       -18, 2, 'Prime Meats Intl',   'Busan',        'MEDIUM'),
    ('RCON-1007', 'Chocolate',          16, 2, 'SweetTreats Co',     'Dubai',        'LOW');
