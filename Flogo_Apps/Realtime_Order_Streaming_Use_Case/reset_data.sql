-- =============================================================================
-- Real-time Order Streaming Use Case - reset demo state between runs
-- =============================================================================
-- Re-runnable script that resets the demo to a clean starting state WITHOUT
-- dropping or recreating tables (schema is left intact):
--   * empties flagged_orders and resets its SERIAL id back to 1
--   * clears and re-seeds the 6 customer lookup rows
--
-- Use this between demo runs so the audit table starts empty and customer
-- data is back to its known-good seed values.
--
-- Run against the existing order_streaming database:
--
--   psql -d order_streaming -f reset_data.sql
-- =============================================================================

-- Empty the audit sink and restart its id sequence at 1.
TRUNCATE TABLE flagged_orders RESTART IDENTITY;

-- Clear and re-seed the enrichment lookup.
DELETE FROM customers;

INSERT INTO customers (customer_id, name, email, tier, region, account_status, credit_limit) VALUES
    (101, 'Alice Chen',    'alice.chen@example.com',    'GOLD',     'North America', 'ACTIVE',     10000.00),
    (102, 'Bob Martinez',  'bob.martinez@example.com',  'VIP',      'EMEA',          'ACTIVE',     50000.00),
    (103, 'Carol Idris',   'carol.idris@example.com',   'STANDARD', 'APAC',          'ACTIVE',      3000.00),
    (104, 'David Okafor',  'david.okafor@example.com',  'STANDARD', 'EMEA',          'SUSPENDED',   2000.00),
    (105, 'Emma Rossi',    'emma.rossi@example.com',    'GOLD',     'EMEA',          'FRAUD_HOLD',  8000.00),
    (106, 'Frank Li',      'frank.li@example.com',      'STANDARD', 'APAC',          'ACTIVE',      1500.00);
