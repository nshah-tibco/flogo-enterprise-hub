-- Airline Passenger Services — Database Schema & Demo Data
-- PostgreSQL 14+
-- Generated dataset: 32 flights, 22 passengers, 22 PNRs (mixed connection scenarios)

-- Drop existing tables (reverse dependency order)
DROP TABLE IF EXISTS rebooking_log CASCADE;
DROP TABLE IF EXISTS booking_segments CASCADE;
DROP TABLE IF EXISTS bookings CASCADE;
DROP TABLE IF EXISTS frequentflyer CASCADE;
DROP TABLE IF EXISTS passengers CASCADE;
DROP TABLE IF EXISTS flights CASCADE;

-- 1. Flights â€” Flight schedule with real-time status
CREATE TABLE flights (
    id              SERIAL PRIMARY KEY,
    flight_number   VARCHAR(10) NOT NULL,
    origin          VARCHAR(3) NOT NULL,        -- IATA code
    origin_city     VARCHAR(50) NOT NULL,
    destination     VARCHAR(3) NOT NULL,        -- IATA code
    destination_city VARCHAR(50) NOT NULL,
    scheduled_departure TIMESTAMP WITH TIME ZONE NOT NULL,
    estimated_departure TIMESTAMP WITH TIME ZONE,
    scheduled_arrival   TIMESTAMP WITH TIME ZONE NOT NULL,
    estimated_arrival   TIMESTAMP WITH TIME ZONE,
    status          VARCHAR(20) NOT NULL DEFAULT 'ON_TIME',  -- ON_TIME, DELAYED, BOARDING, DEPARTED, CANCELLED
    gate            VARCHAR(5),
    delay_minutes   INTEGER DEFAULT 0,
    delay_reason    VARCHAR(200),
    aircraft        VARCHAR(50) DEFAULT 'Boeing 737 MAX 9',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_status CHECK (status IN ('ON_TIME','DELAYED','BOARDING','DEPARTED','CANCELLED'))
);

-- 2. Passengers â€” Passenger master records
CREATE TABLE passengers (
    id              SERIAL PRIMARY KEY,
    passenger_id    VARCHAR(20) NOT NULL UNIQUE,   -- PAX-2026-XXXXX
    first_name      VARCHAR(50) NOT NULL,
    last_name       VARCHAR(50) NOT NULL,
    email           VARCHAR(100),
    phone           VARCHAR(30),
    nationality     VARCHAR(3),                    -- ISO country code
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. FrequentFlyer â€” Loyalty program membership
CREATE TABLE frequentflyer (
    id                  SERIAL PRIMARY KEY,
    passenger_id        VARCHAR(20) NOT NULL REFERENCES passengers(passenger_id),
    frequentflyer_number VARCHAR(20) NOT NULL UNIQUE,  -- CM-XXXXXXXX
    tier                VARCHAR(20) NOT NULL DEFAULT 'Basic',  -- Basic, Silver, Gold, Platinum
    miles_balance       INTEGER DEFAULT 0,
    tier_miles_ytd      INTEGER DEFAULT 0,
    CONSTRAINT chk_tier CHECK (tier IN ('Basic','Silver','Gold','Platinum'))
);

-- 4. Bookings â€” PNR-based itineraries
CREATE TABLE bookings (
    id              SERIAL PRIMARY KEY,
    pnr             VARCHAR(6) NOT NULL UNIQUE,    -- 6-character PNR
    passenger_id    VARCHAR(20) NOT NULL REFERENCES passengers(passenger_id),
    booking_date    DATE NOT NULL DEFAULT CURRENT_DATE,
    booking_status  VARCHAR(20) NOT NULL DEFAULT 'CONFIRMED',  -- CONFIRMED, CANCELLED, COMPLETED
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Booking Segments â€” Individual flight legs per booking
CREATE TABLE booking_segments (
    id              SERIAL PRIMARY KEY,
    booking_id      INTEGER NOT NULL REFERENCES bookings(id),
    segment_order   INTEGER NOT NULL,              -- 1, 2, 3... for multi-leg
    flight_number   VARCHAR(10) NOT NULL,
    origin          VARCHAR(3) NOT NULL,
    destination     VARCHAR(3) NOT NULL,
    departure_time  TIMESTAMP WITH TIME ZONE NOT NULL,
    arrival_time    TIMESTAMP WITH TIME ZONE NOT NULL,
    seat_number     VARCHAR(5),
    cabin           VARCHAR(20) DEFAULT 'Economy', -- Economy, Business
    segment_status  VARCHAR(20) DEFAULT 'CONFIRMED', -- CONFIRMED, CHECKED_IN, BOARDED, COMPLETED, CANCELLED, REBOOKED
    CONSTRAINT chk_cabin CHECK (cabin IN ('Economy','Business')),
    CONSTRAINT chk_seg_status CHECK (segment_status IN ('CONFIRMED','CHECKED_IN','BOARDED','COMPLETED','CANCELLED','REBOOKED'))
);

-- 6. Rebooking Log â€” Tracks all passenger rebookings
CREATE TABLE rebooking_log (
    id              SERIAL PRIMARY KEY,
    pnr             VARCHAR(6) NOT NULL,
    passenger_id    VARCHAR(20),
    original_flight VARCHAR(10) NOT NULL,
    new_flight      VARCHAR(10) NOT NULL,
    original_seat   VARCHAR(5),
    new_seat        VARCHAR(5),
    reason          VARCHAR(200),
    rebooked_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status          VARCHAR(20) DEFAULT 'COMPLETED'
);

-- Indexes
CREATE INDEX idx_rebooking_pnr ON rebooking_log(pnr);
CREATE INDEX idx_flights_number ON flights(flight_number);
CREATE INDEX idx_flights_status ON flights(status);
CREATE INDEX idx_passengers_id ON passengers(passenger_id);
CREATE INDEX idx_bookings_pnr ON bookings(pnr);
CREATE INDEX idx_bookings_passenger ON bookings(passenger_id);
CREATE INDEX idx_segments_booking ON booking_segments(booking_id);
CREATE INDEX idx_frequentflyer_passenger ON frequentflyer(passenger_id);

-- ============================================================
-- DEMO DATA — Airline Route Network through ATL Hub
-- ============================================================

-- Flights (32 — hub-and-spoke through ATL, several delayed/cancelled + alternatives)
INSERT INTO flights (flight_number, origin, origin_city, destination, destination_city, scheduled_departure, estimated_departure, scheduled_arrival, estimated_arrival, status, gate, delay_minutes, delay_reason, aircraft) VALUES
('FL801', 'DEN', 'Denver', 'ATL', 'Atlanta', '2026-05-21 08:30:00-05:00', '2026-05-21 10:00:00-05:00', '2026-05-21 11:15:00-05:00', '2026-05-21 12:45:00-05:00', 'DELAYED', 'B12', 90, 'Late arriving aircraft from DFW', 'Boeing 737 MAX 9'),
('FL445', 'ATL', 'Atlanta', 'MIA', 'Miami', '2026-05-21 12:30:00-05:00', NULL, '2026-05-21 16:45:00-04:00', NULL, 'ON_TIME', 'A08', 0, NULL, 'Boeing 737-800'),
('FL447', 'ATL', 'Atlanta', 'MIA', 'Miami', '2026-05-21 15:30:00-05:00', NULL, '2026-05-21 19:45:00-04:00', NULL, 'ON_TIME', 'A12', 0, NULL, 'Boeing 737 MAX 9'),
('FL215', 'LAX', 'Los Angeles', 'ATL', 'Atlanta', '2026-05-21 06:00:00-03:00', NULL, '2026-05-21 11:30:00-05:00', NULL, 'ON_TIME', 'C04', 0, NULL, 'Boeing 737 MAX 9'),
('FL302', 'ATL', 'Atlanta', 'JFK', 'New York', '2026-05-21 13:00:00-05:00', NULL, '2026-05-21 19:15:00-04:00', NULL, 'ON_TIME', 'A15', 0, NULL, 'Boeing 737 MAX 9'),
('FL510', 'SEA', 'Seattle', 'ATL', 'Atlanta', '2026-05-21 07:15:00-04:00', '2026-05-21 08:00:00-04:00', '2026-05-21 12:45:00-05:00', '2026-05-21 13:30:00-05:00', 'DELAYED', 'C08', 45, 'Weather conditions in Seattle', 'Boeing 737-800'),
('FL612', 'ATL', 'Atlanta', 'ORD', 'Chicago', '2026-05-21 14:00:00-05:00', NULL, '2026-05-21 19:30:00-05:00', NULL, 'ON_TIME', 'A20', 0, NULL, 'Boeing 737 MAX 9'),
('FL725', 'BOS', 'Boston', 'ATL', 'Atlanta', '2026-05-21 09:00:00-05:00', NULL, '2026-05-21 13:30:00-05:00', NULL, 'ON_TIME', 'B06', 0, NULL, 'Boeing 737-800'),
('FL803', 'DEN', 'Denver', 'ATL', 'Atlanta', '2026-05-21 12:00:00-06:00', NULL, '2026-05-21 15:45:00-05:00', NULL, 'ON_TIME', 'B14', 0, NULL, 'Boeing 737 MAX 9'),
('FL512', 'SEA', 'Seattle', 'ATL', 'Atlanta', '2026-05-21 08:30:00-07:00', NULL, '2026-05-21 16:00:00-05:00', NULL, 'ON_TIME', 'C10', 0, NULL, 'Boeing 737-800'),
('FL217', 'LAX', 'Los Angeles', 'ATL', 'Atlanta', '2026-05-21 09:30:00-07:00', NULL, '2026-05-21 15:30:00-05:00', '2026-05-21 16:30:00-05:00', 'DELAYED', 'C06', 120, 'Air traffic control delay', 'Boeing 737 MAX 9'),
('FL727', 'BOS', 'Boston', 'ATL', 'Atlanta', '2026-05-21 10:00:00-04:00', NULL, '2026-05-21 14:30:00-05:00', '2026-05-21 15:30:00-05:00', 'DELAYED', 'B08', 60, 'Crew scheduling delay', 'Boeing 737-800'),
('FL930', 'ORD', 'Chicago', 'ATL', 'Atlanta', '2026-05-21 09:00:00-05:00', NULL, '2026-05-21 12:00:00-05:00', NULL, 'ON_TIME', 'B10', 0, NULL, 'Boeing 737 MAX 9'),
('FL932', 'ORD', 'Chicago', 'ATL', 'Atlanta', '2026-05-21 11:00:00-05:00', NULL, '2026-05-21 14:00:00-05:00', NULL, 'CANCELLED', 'B11', 0, 'Aircraft maintenance', 'Boeing 737 MAX 9'),
('FL410', 'JFK', 'New York', 'ATL', 'Atlanta', '2026-05-21 08:45:00-04:00', NULL, '2026-05-21 11:45:00-05:00', NULL, 'ON_TIME', 'A05', 0, NULL, 'Airbus A321neo'),
('FL412', 'JFK', 'New York', 'ATL', 'Atlanta', '2026-05-21 12:30:00-04:00', NULL, '2026-05-21 15:00:00-05:00', '2026-05-21 16:15:00-05:00', 'DELAYED', 'A07', 75, 'Late arriving aircraft', 'Airbus A321neo'),
('FL620', 'SFO', 'San Francisco', 'ATL', 'Atlanta', '2026-05-21 08:00:00-07:00', NULL, '2026-05-21 15:00:00-05:00', '2026-05-21 18:00:00-05:00', 'DELAYED', 'C12', 180, 'Weather conditions in San Francisco', 'Boeing 737 MAX 9'),
('FL450', 'MIA', 'Miami', 'ATL', 'Atlanta', '2026-05-21 09:15:00-04:00', NULL, '2026-05-21 12:15:00-05:00', NULL, 'ON_TIME', 'A09', 0, NULL, 'Boeing 737-800'),
('FL449', 'ATL', 'Atlanta', 'MIA', 'Miami', '2026-05-21 18:30:00-05:00', NULL, '2026-05-21 22:45:00-04:00', NULL, 'ON_TIME', 'A10', 0, NULL, 'Boeing 737-800'),
('FL304', 'ATL', 'Atlanta', 'JFK', 'New York', '2026-05-21 16:00:00-05:00', NULL, '2026-05-21 22:15:00-04:00', NULL, 'ON_TIME', 'A16', 0, NULL, 'Boeing 737 MAX 9'),
('FL306', 'ATL', 'Atlanta', 'JFK', 'New York', '2026-05-21 19:30:00-05:00', NULL, '2026-05-21 23:45:00-04:00', NULL, 'ON_TIME', 'A17', 0, NULL, 'Airbus A321neo'),
('FL614', 'ATL', 'Atlanta', 'ORD', 'Chicago', '2026-05-21 17:00:00-05:00', NULL, '2026-05-21 18:45:00-05:00', NULL, 'ON_TIME', 'A21', 0, NULL, 'Boeing 737 MAX 9'),
('FL616', 'ATL', 'Atlanta', 'ORD', 'Chicago', '2026-05-21 20:00:00-05:00', NULL, '2026-05-21 21:45:00-05:00', NULL, 'ON_TIME', 'A23', 0, NULL, 'Boeing 737-800'),
('FL520', 'ATL', 'Atlanta', 'LAX', 'Los Angeles', '2026-05-21 15:00:00-05:00', NULL, '2026-05-21 17:30:00-07:00', NULL, 'ON_TIME', 'A22', 0, NULL, 'Boeing 737 MAX 9'),
('FL522', 'ATL', 'Atlanta', 'LAX', 'Los Angeles', '2026-05-21 18:00:00-05:00', NULL, '2026-05-21 20:30:00-07:00', NULL, 'ON_TIME', 'A24', 0, NULL, 'Boeing 737 MAX 9'),
('FL715', 'ATL', 'Atlanta', 'SEA', 'Seattle', '2026-05-21 14:30:00-05:00', NULL, '2026-05-21 17:15:00-07:00', NULL, 'ON_TIME', 'C14', 0, NULL, 'Boeing 737-800'),
('FL717', 'ATL', 'Atlanta', 'SEA', 'Seattle', '2026-05-21 18:15:00-05:00', NULL, '2026-05-21 21:00:00-07:00', NULL, 'ON_TIME', 'C16', 0, NULL, 'Boeing 737-800'),
('FL810', 'ATL', 'Atlanta', 'DEN', 'Denver', '2026-05-21 16:00:00-05:00', NULL, '2026-05-21 17:30:00-06:00', NULL, 'ON_TIME', 'B16', 0, NULL, 'Boeing 737 MAX 9'),
('FL812', 'ATL', 'Atlanta', 'DEN', 'Denver', '2026-05-21 19:00:00-05:00', NULL, '2026-05-21 20:30:00-06:00', NULL, 'ON_TIME', 'B18', 0, NULL, 'Boeing 737 MAX 9'),
('FL730', 'ATL', 'Atlanta', 'BOS', 'Boston', '2026-05-21 15:45:00-05:00', NULL, '2026-05-21 19:00:00-04:00', NULL, 'ON_TIME', 'B20', 0, NULL, 'Airbus A321neo'),
('FL732', 'ATL', 'Atlanta', 'BOS', 'Boston', '2026-05-21 19:15:00-05:00', NULL, '2026-05-21 22:30:00-04:00', NULL, 'ON_TIME', 'B22', 0, NULL, 'Airbus A321neo'),
('FL625', 'ATL', 'Atlanta', 'SFO', 'San Francisco', '2026-05-21 16:30:00-05:00', NULL, '2026-05-21 19:00:00-07:00', NULL, 'ON_TIME', 'C18', 0, NULL, 'Boeing 737 MAX 9');

-- Passengers (22)
INSERT INTO passengers (passenger_id, first_name, last_name, email, phone, nationality) VALUES
('PAX-2026-00101', 'Carlos', 'Martinez', 'carlos.martinez@email.com', '+57-310-555-0101', 'COL'),
('PAX-2026-00102', 'Ana', 'Silva', 'ana.silva@email.com', '+55-11-555-0102', 'BRA'),
('PAX-2026-00103', 'Roberto', 'Gonzalez', 'roberto.gonzalez@email.com', '+507-6555-0103', 'PAN'),
('PAX-2026-00104', 'Maria', 'Fernandez', 'maria.fernandez@email.com', '+56-9-555-0104', 'CHL'),
('PAX-2026-00105', 'Jorge', 'Lopez', 'jorge.lopez@email.com', '+51-1-555-0105', 'PER'),
('PAX-2026-00106', 'Isabella', 'Ramirez', 'isabella.ramirez@email.com', '+54-11-555-0106', 'ARG'),
('PAX-2026-00107', 'Diego', 'Torres', 'diego.torres@email.com', '+57-1-555-0107', 'COL'),
('PAX-2026-00108', 'Valentina', 'Herrera', 'valentina.herrera@email.com', '+507-6555-0108', 'PAN'),
('PAX-2026-00109', 'Andres', 'Morales', 'andres.morales@email.com', '+1-305-555-0109', 'USA'),
('PAX-2026-00110', 'Camila', 'Rojas', 'camila.rojas@email.com', '+55-21-555-0110', 'BRA'),
('PAX-2026-00111', 'Lucas', 'Pereira', 'lucas.pereira@email.com', '+55-11-555-0111', 'BRA'),
('PAX-2026-00112', 'Sofia', 'Castro', 'sofia.castro@email.com', '+52-55-555-0112', 'MEX'),
('PAX-2026-00113', 'Mateo', 'Ramos', 'mateo.ramos@email.com', '+54-11-555-0113', 'ARG'),
('PAX-2026-00114', 'Valeria', 'Cruz', 'valeria.cruz@email.com', '+57-1-555-0114', 'COL'),
('PAX-2026-00115', 'Nicolas', 'Vargas', 'nicolas.vargas@email.com', '+56-9-555-0115', 'CHL'),
('PAX-2026-00116', 'Gabriela', 'Mendez', 'gabriela.mendez@email.com', '+51-1-555-0116', 'PER'),
('PAX-2026-00117', 'Daniel', 'Ortiz', 'daniel.ortiz@email.com', '+1-305-555-0117', 'USA'),
('PAX-2026-00118', 'Renata', 'Alves', 'renata.alves@email.com', '+55-21-555-0118', 'BRA'),
('PAX-2026-00119', 'Tomas', 'Reyes', 'tomas.reyes@email.com', '+507-6555-0119', 'PAN'),
('PAX-2026-00120', 'Elena', 'Navarro', 'elena.navarro@email.com', '+34-91-555-0120', 'ESP'),
('PAX-2026-00121', 'Felipe', 'Guerrero', 'felipe.guerrero@email.com', '+57-1-555-0121', 'COL'),
('PAX-2026-00122', 'Paula', 'Rios', 'paula.rios@email.com', '+55-11-555-0122', 'BRA');

-- FrequentFlyer loyalty program (22)
INSERT INTO frequentflyer (passenger_id, frequentflyer_number, tier, miles_balance, tier_miles_ytd) VALUES
('PAX-2026-00101', 'FF-98765432', 'Gold', 87500, 52000),
('PAX-2026-00102', 'FF-87654321', 'Silver', 34200, 28000),
('PAX-2026-00103', 'FF-76543210', 'Platinum', 245000, 95000),
('PAX-2026-00104', 'FF-65432109', 'Basic', 12300, 8000),
('PAX-2026-00105', 'FF-54321098', 'Silver', 41000, 31000),
('PAX-2026-00106', 'FF-43210987', 'Gold', 68000, 48000),
('PAX-2026-00107', 'FF-32109876', 'Basic', 5200, 3000),
('PAX-2026-00108', 'FF-21098765', 'Platinum', 312000, 110000),
('PAX-2026-00109', 'FF-10987654', 'Silver', 29000, 22000),
('PAX-2026-00110', 'FF-99887766', 'Gold', 71000, 45000),
('PAX-2026-00111', 'FF-11223344', 'Silver', 38000, 26000),
('PAX-2026-00112', 'FF-22334455', 'Gold', 79000, 51000),
('PAX-2026-00113', 'FF-33445566', 'Basic', 4200, 2500),
('PAX-2026-00114', 'FF-44556677', 'Platinum', 268000, 102000),
('PAX-2026-00115', 'FF-55667788', 'Silver', 33000, 24000),
('PAX-2026-00116', 'FF-66778899', 'Gold', 72000, 47000),
('PAX-2026-00117', 'FF-77889900', 'Basic', 6100, 3500),
('PAX-2026-00118', 'FF-88990011', 'Silver', 45000, 30000),
('PAX-2026-00119', 'FF-99001122', 'Gold', 69000, 44000),
('PAX-2026-00120', 'FF-00112233', 'Platinum', 295000, 108000),
('PAX-2026-00121', 'FF-12344321', 'Basic', 3100, 1800),
('PAX-2026-00122', 'FF-23455432', 'Silver', 36000, 25000);

-- Bookings (22 PNRs)
INSERT INTO bookings (pnr, passenger_id, booking_date) VALUES
('ABCDE1', 'PAX-2026-00101', DATE '2026-05-21' - 36),
('FGHIJ2', 'PAX-2026-00102', DATE '2026-05-21' - 31),
('KLMNO3', 'PAX-2026-00103', DATE '2026-05-21' - 20),
('PQRST4', 'PAX-2026-00104', DATE '2026-05-21' - 16),
('UVWXY5', 'PAX-2026-00105', DATE '2026-05-21' - 23),
('BCDEF6', 'PAX-2026-00106', DATE '2026-05-21' - 11),
('GHIJK7', 'PAX-2026-00107', DATE '2026-05-21' - 9),
('LMNOP8', 'PAX-2026-00110', DATE '2026-05-21' - 13),
('HIJKL9', 'PAX-2026-00111', DATE '2026-05-21' - 40),
('MNOPQ0', 'PAX-2026-00112', DATE '2026-05-21' - 7),
('RSTUV1', 'PAX-2026-00113', DATE '2026-05-21' - 15),
('WXYZA2', 'PAX-2026-00114', DATE '2026-05-21' - 5),
('BCDFG3', 'PAX-2026-00115', DATE '2026-05-21' - 18),
('HJKLM4', 'PAX-2026-00116', DATE '2026-05-21' - 12),
('NPQRS5', 'PAX-2026-00117', DATE '2026-05-21' - 6),
('TVWXY6', 'PAX-2026-00118', DATE '2026-05-21' - 21),
('ZABCD7', 'PAX-2026-00119', DATE '2026-05-21' - 26),
('EFGHI8', 'PAX-2026-00120', DATE '2026-05-21' - 4),
('JKLMN9', 'PAX-2026-00121', DATE '2026-05-21' - 8),
('OPQRS0', 'PAX-2026-00122', DATE '2026-05-21' - 14),
('UVWXZ1', 'PAX-2026-00108', DATE '2026-05-21' - 19),
('CDEFH2', 'PAX-2026-00109', DATE '2026-05-21' - 10);

-- Booking Segments (multi-leg itineraries)
-- Carlos: DEN->ATL->MIA (MISSED)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(1, 1, 'FL801', 'DEN', 'ATL', '2026-05-21 08:30:00-05:00', '2026-05-21 11:15:00-05:00', '4A', 'Business', 'CHECKED_IN'),
(1, 2, 'FL445', 'ATL', 'MIA', '2026-05-21 12:30:00-05:00', '2026-05-21 16:45:00-04:00', '3C', 'Business', 'CONFIRMED');

-- Ana: LAX->ATL->JFK (SAFE)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(2, 1, 'FL215', 'LAX', 'ATL', '2026-05-21 06:00:00-03:00', '2026-05-21 11:30:00-05:00', '12B', 'Economy', 'CHECKED_IN'),
(2, 2, 'FL302', 'ATL', 'JFK', '2026-05-21 13:00:00-05:00', '2026-05-21 19:15:00-04:00', '14A', 'Economy', 'CONFIRMED');

-- Roberto: ATL->MIA direct
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(3, 1, 'FL445', 'ATL', 'MIA', '2026-05-21 12:30:00-05:00', '2026-05-21 16:45:00-04:00', '1A', 'Business', 'CONFIRMED');

-- Maria: SEA->ATL->ORD (AT_RISK)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(4, 1, 'FL510', 'SEA', 'ATL', '2026-05-21 07:15:00-04:00', '2026-05-21 12:45:00-05:00', '8C', 'Economy', 'CHECKED_IN'),
(4, 2, 'FL612', 'ATL', 'ORD', '2026-05-21 14:00:00-05:00', '2026-05-21 19:30:00-05:00', '10A', 'Economy', 'CONFIRMED');

-- Jorge: BOS->ATL->MIA (SAFE)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(5, 1, 'FL725', 'BOS', 'ATL', '2026-05-21 09:00:00-05:00', '2026-05-21 13:30:00-05:00', '15D', 'Economy', 'CONFIRMED'),
(5, 2, 'FL447', 'ATL', 'MIA', '2026-05-21 15:30:00-05:00', '2026-05-21 19:45:00-04:00', '16A', 'Economy', 'CONFIRMED');

-- Isabella: DEN->ATL one-way
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(6, 1, 'FL801', 'DEN', 'ATL', '2026-05-21 08:30:00-05:00', '2026-05-21 11:15:00-05:00', '6B', 'Economy', 'CHECKED_IN');

-- Diego: DEN->ATL->JFK (MISSED)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(7, 1, 'FL801', 'DEN', 'ATL', '2026-05-21 08:30:00-05:00', '2026-05-21 11:15:00-05:00', '22A', 'Economy', 'CHECKED_IN'),
(7, 2, 'FL302', 'ATL', 'JFK', '2026-05-21 13:00:00-05:00', '2026-05-21 19:15:00-04:00', '20C', 'Economy', 'CONFIRMED');

-- Camila: LAX->ATL->ORD (SAFE)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(8, 1, 'FL215', 'LAX', 'ATL', '2026-05-21 06:00:00-03:00', '2026-05-21 11:30:00-05:00', '18B', 'Economy', 'CONFIRMED'),
(8, 2, 'FL612', 'ATL', 'ORD', '2026-05-21 14:00:00-05:00', '2026-05-21 19:30:00-05:00', '19A', 'Economy', 'CONFIRMED');

-- Lucas: LAX->ATL->JFK (MISSED, FL217 delayed)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(9, 1, 'FL217', 'LAX', 'ATL', '2026-05-21 09:30:00-07:00', '2026-05-21 15:30:00-05:00', '14C', 'Economy', 'CHECKED_IN'),
(9, 2, 'FL304', 'ATL', 'JFK', '2026-05-21 16:00:00-05:00', '2026-05-21 22:15:00-04:00', '12A', 'Economy', 'CONFIRMED');

-- Sofia: SFO->ATL->SEA (MISSED, no same-day alt)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(10, 1, 'FL620', 'SFO', 'ATL', '2026-05-21 08:00:00-07:00', '2026-05-21 15:00:00-05:00', '5A', 'Business', 'CHECKED_IN'),
(10, 2, 'FL717', 'ATL', 'SEA', '2026-05-21 18:15:00-05:00', '2026-05-21 21:00:00-07:00', '6C', 'Business', 'CONFIRMED');

-- Mateo: JFK->ATL->ORD (AT_RISK)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(11, 1, 'FL412', 'JFK', 'ATL', '2026-05-21 12:30:00-04:00', '2026-05-21 15:00:00-05:00', '20B', 'Economy', 'CHECKED_IN'),
(11, 2, 'FL614', 'ATL', 'ORD', '2026-05-21 17:00:00-05:00', '2026-05-21 18:45:00-05:00', '18C', 'Economy', 'CONFIRMED');

-- Valeria (Platinum): BOS->ATL->MIA (MISSED)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(12, 1, 'FL727', 'BOS', 'ATL', '2026-05-21 10:00:00-04:00', '2026-05-21 14:30:00-05:00', '2A', 'Business', 'CHECKED_IN'),
(12, 2, 'FL447', 'ATL', 'MIA', '2026-05-21 15:30:00-05:00', '2026-05-21 19:45:00-04:00', '1C', 'Business', 'CONFIRMED');

-- Nicolas: SEA->ATL->LAX (SAFE)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(13, 1, 'FL512', 'SEA', 'ATL', '2026-05-21 08:30:00-07:00', '2026-05-21 16:00:00-05:00', '16A', 'Economy', 'CONFIRMED'),
(13, 2, 'FL522', 'ATL', 'LAX', '2026-05-21 18:00:00-05:00', '2026-05-21 20:30:00-07:00', '17B', 'Economy', 'CONFIRMED');

-- Gabriela: DEN->ATL->SEA (SAFE despite FL801 delay)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(14, 1, 'FL801', 'DEN', 'ATL', '2026-05-21 08:30:00-05:00', '2026-05-21 11:15:00-05:00', '9C', 'Economy', 'CHECKED_IN'),
(14, 2, 'FL715', 'ATL', 'SEA', '2026-05-21 14:30:00-05:00', '2026-05-21 17:15:00-07:00', '10A', 'Economy', 'CONFIRMED');

-- Daniel: ORD->ATL->MIA (inbound FL932 CANCELLED)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(15, 1, 'FL932', 'ORD', 'ATL', '2026-05-21 11:00:00-05:00', '2026-05-21 14:00:00-05:00', '21D', 'Economy', 'CONFIRMED'),
(15, 2, 'FL447', 'ATL', 'MIA', '2026-05-21 15:30:00-05:00', '2026-05-21 19:45:00-04:00', '22A', 'Economy', 'CONFIRMED');

-- Renata: JFK->ATL->MIA (AT_RISK)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(16, 1, 'FL410', 'JFK', 'ATL', '2026-05-21 08:45:00-04:00', '2026-05-21 11:45:00-05:00', '11B', 'Economy', 'CHECKED_IN'),
(16, 2, 'FL445', 'ATL', 'MIA', '2026-05-21 12:30:00-05:00', '2026-05-21 16:45:00-04:00', '12C', 'Economy', 'CONFIRMED');

-- Tomas: LAX->ATL->SEA (SAFE)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(17, 1, 'FL215', 'LAX', 'ATL', '2026-05-21 06:00:00-03:00', '2026-05-21 11:30:00-05:00', '13A', 'Economy', 'CONFIRMED'),
(17, 2, 'FL715', 'ATL', 'SEA', '2026-05-21 14:30:00-05:00', '2026-05-21 17:15:00-07:00', '14B', 'Economy', 'CONFIRMED');

-- Elena (Platinum): SFO->ATL->DEN (SAFE, borderline)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(18, 1, 'FL620', 'SFO', 'ATL', '2026-05-21 08:00:00-07:00', '2026-05-21 15:00:00-05:00', '3A', 'Business', 'CHECKED_IN'),
(18, 2, 'FL812', 'ATL', 'DEN', '2026-05-21 19:00:00-05:00', '2026-05-21 20:30:00-06:00', '4B', 'Business', 'CONFIRMED');

-- Felipe: DEN->ATL->BOS (MISSED, tight schedule)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(19, 1, 'FL803', 'DEN', 'ATL', '2026-05-21 12:00:00-06:00', '2026-05-21 15:45:00-05:00', '19A', 'Economy', 'CONFIRMED'),
(19, 2, 'FL730', 'ATL', 'BOS', '2026-05-21 15:45:00-05:00', '2026-05-21 19:00:00-04:00', '20C', 'Economy', 'CONFIRMED');

-- Paula: ATL->SFO direct
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(20, 1, 'FL625', 'ATL', 'SFO', '2026-05-21 16:30:00-05:00', '2026-05-21 19:00:00-07:00', '15A', 'Economy', 'CONFIRMED');

-- Valentina (Platinum): MIA->ATL->DEN (SAFE, long layover)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(21, 1, 'FL450', 'MIA', 'ATL', '2026-05-21 09:15:00-04:00', '2026-05-21 12:15:00-05:00', '2C', 'Business', 'CHECKED_IN'),
(21, 2, 'FL810', 'ATL', 'DEN', '2026-05-21 16:00:00-05:00', '2026-05-21 17:30:00-06:00', '3A', 'Business', 'CONFIRMED');

-- Andres: BOS->ATL->JFK (AT_RISK)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(22, 1, 'FL727', 'BOS', 'ATL', '2026-05-21 10:00:00-04:00', '2026-05-21 14:30:00-05:00', '24B', 'Economy', 'CHECKED_IN'),
(22, 2, 'FL304', 'ATL', 'JFK', '2026-05-21 16:00:00-05:00', '2026-05-21 22:15:00-04:00', '23A', 'Economy', 'CONFIRMED');
