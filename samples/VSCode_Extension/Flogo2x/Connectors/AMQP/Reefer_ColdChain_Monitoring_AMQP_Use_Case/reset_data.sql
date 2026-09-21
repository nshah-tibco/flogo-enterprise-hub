-- =====================================================================
-- Reefer Cold-Chain Monitoring — reset between demo runs
-- Database: reefer_monitoring
--
-- Clears the breach audit trail and restores the reference fleet to its
-- seeded state, WITHOUT dropping/recreating the tables. Run this to give
-- a clean slate before re-demoing:
--   psql -U postgres -d reefer_monitoring -f reset_data.sql
-- =====================================================================

-- 1) Wipe the audit trail and reset alert_id back to 1.
TRUNCATE TABLE reefer_alerts RESTART IDENTITY;

-- 2) Restore the reference fleet to its known-good seed (idempotent upsert).
INSERT INTO reefer_containers
    (container_id, cargo_type, set_point_c, allowed_deviation_c, customer_name, destination_port, priority)
VALUES
    ('RCON-1001', 'Pharma-Vaccines',  -20, 2, 'Singapore BioPharma', 'Rotterdam',    'HIGH'),
    ('RCON-1002', 'Frozen Seafood',   -18, 3, 'Ocean Harvest Ltd',   'Hamburg',      'MEDIUM'),
    ('RCON-1003', 'Fresh Produce',     13, 1, 'Tropical Fruits Co',  'Yokohama',     'MEDIUM'),
    ('RCON-1004', 'Dairy',              4, 2, 'DairyBest Exports',   'Sydney',       'LOW'),
    ('RCON-1005', 'Pharma-Insulin',     5, 1, 'MediCore Logistics',  'Los Angeles',  'HIGH'),
    ('RCON-1006', 'Frozen Meat',       -18, 2, 'Prime Meats Intl',   'Busan',        'MEDIUM'),
    ('RCON-1007', 'Chocolate',          16, 2, 'SweetTreats Co',     'Dubai',        'LOW')
ON CONFLICT (container_id) DO UPDATE SET
    cargo_type          = EXCLUDED.cargo_type,
    set_point_c         = EXCLUDED.set_point_c,
    allowed_deviation_c = EXCLUDED.allowed_deviation_c,
    customer_name       = EXCLUDED.customer_name,
    destination_port    = EXCLUDED.destination_port,
    priority            = EXCLUDED.priority;
