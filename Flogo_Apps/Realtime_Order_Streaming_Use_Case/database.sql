-- =============================================================================
-- Real-time Order Streaming Use Case - PostgreSQL setup
-- =============================================================================
-- Sets up the schema and seed data for the "Real-time Order Streaming" demo:
--   * customers        - enrichment lookup keyed by customer_id (6 seed rows)
--   * flagged_orders   - audit sink written by the flagged branch of the flow
--
-- This script is idempotent: it DROPs both tables first, recreates them, and
-- re-seeds the 6 customer rows. Safe to re-run at any time.
--
-- The database "order_streaming" must already exist. You cannot CREATE DATABASE
-- from inside a connected script, so run this line separately first (once):
--
--   CREATE DATABASE order_streaming;
--
-- Then run this file against that database:
--
--   psql -d order_streaming -f database.sql
-- =============================================================================

-- Drop children/sinks before lookup tables to keep the order clean.
DROP TABLE IF EXISTS flagged_orders;
DROP TABLE IF EXISTS customers;

-- -----------------------------------------------------------------------------
-- Table 1: customers  (enrichment lookup, keyed by customer_id)
-- -----------------------------------------------------------------------------
CREATE TABLE customers (
    customer_id    INT PRIMARY KEY,
    name           TEXT NOT NULL,
    email          TEXT,
    tier           TEXT NOT NULL,
    region         TEXT,
    account_status TEXT NOT NULL,
    credit_limit   NUMERIC(12,2),
    CONSTRAINT customers_tier_check
        CHECK (tier IN ('STANDARD','GOLD','VIP')),
    CONSTRAINT customers_account_status_check
        CHECK (account_status IN ('ACTIVE','SUSPENDED','FRAUD_HOLD'))
);

-- -----------------------------------------------------------------------------
-- Table 2: flagged_orders  (audit sink written by the flagged branch)
-- -----------------------------------------------------------------------------
CREATE TABLE flagged_orders (
    id             SERIAL PRIMARY KEY,
    order_id       TEXT NOT NULL,
    customer_id    INT,
    customer_name  TEXT,
    amount         NUMERIC(12,2),
    tier           TEXT,
    account_status TEXT,
    flag_reason    TEXT,
    flagged_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- -----------------------------------------------------------------------------
-- Seed data: 6 customers chosen to show both NORMAL and FLAGGED outcomes
-- -----------------------------------------------------------------------------
INSERT INTO customers (customer_id, name, email, tier, region, account_status, credit_limit) VALUES
    (101, 'Alice Chen',    'alice.chen@example.com',    'GOLD',     'North America', 'ACTIVE',     10000.00),
    (102, 'Bob Martinez',  'bob.martinez@example.com',  'VIP',      'EMEA',          'ACTIVE',     50000.00),
    (103, 'Carol Idris',   'carol.idris@example.com',   'STANDARD', 'APAC',          'ACTIVE',      3000.00),
    (104, 'David Okafor',  'david.okafor@example.com',  'STANDARD', 'EMEA',          'SUSPENDED',   2000.00),
    (105, 'Emma Rossi',    'emma.rossi@example.com',    'GOLD',     'EMEA',          'FRAUD_HOLD',  8000.00),
    (106, 'Frank Li',      'frank.li@example.com',      'STANDARD', 'APAC',          'ACTIVE',      1500.00);
