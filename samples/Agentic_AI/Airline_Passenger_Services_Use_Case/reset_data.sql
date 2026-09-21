-- Airline Passenger Services — Reset Demo Data
-- Run this to reset all tables with fresh, today-relative test data
-- PostgreSQL 14+

-- Clear all data (reverse dependency order)
TRUNCATE rebooking_log, booking_segments, bookings, frequentflyer, passengers, flights RESTART IDENTITY CASCADE;

-- Flights — use CURRENT_DATE for today-relative scheduling
INSERT INTO flights (flight_number, origin, origin_city, destination, destination_city, scheduled_departure, estimated_departure, scheduled_arrival, estimated_arrival, status, gate, delay_minutes, delay_reason, aircraft) VALUES
('FL801', 'DEN', 'Denver', 'ATL', 'Atlanta', CURRENT_DATE + INTERVAL '8 hours 30 minutes', CURRENT_DATE + INTERVAL '10 hours 0 minutes', CURRENT_DATE + INTERVAL '11 hours 15 minutes', CURRENT_DATE + INTERVAL '12 hours 45 minutes', 'DELAYED', 'B12', 90, 'Late arriving aircraft from DFW', 'Boeing 737 MAX 9'),
('FL445', 'ATL', 'Atlanta', 'MIA', 'Miami', CURRENT_DATE + INTERVAL '12 hours 30 minutes', NULL, CURRENT_DATE + INTERVAL '16 hours 45 minutes', NULL, 'ON_TIME', 'A08', 0, NULL, 'Boeing 737-800'),
('FL447', 'ATL', 'Atlanta', 'MIA', 'Miami', CURRENT_DATE + INTERVAL '15 hours 30 minutes', NULL, CURRENT_DATE + INTERVAL '19 hours 45 minutes', NULL, 'ON_TIME', 'A12', 0, NULL, 'Boeing 737 MAX 9'),
('FL215', 'LAX', 'Los Angeles', 'ATL', 'Atlanta', CURRENT_DATE + INTERVAL '6 hours 0 minutes', NULL, CURRENT_DATE + INTERVAL '11 hours 30 minutes', NULL, 'ON_TIME', 'C04', 0, NULL, 'Boeing 737 MAX 9'),
('FL302', 'ATL', 'Atlanta', 'JFK', 'New York', CURRENT_DATE + INTERVAL '13 hours 0 minutes', NULL, CURRENT_DATE + INTERVAL '19 hours 15 minutes', NULL, 'ON_TIME', 'A15', 0, NULL, 'Boeing 737 MAX 9'),
('FL510', 'SEA', 'Seattle', 'ATL', 'Atlanta', CURRENT_DATE + INTERVAL '7 hours 15 minutes', CURRENT_DATE + INTERVAL '8 hours 0 minutes', CURRENT_DATE + INTERVAL '12 hours 45 minutes', CURRENT_DATE + INTERVAL '13 hours 30 minutes', 'DELAYED', 'C08', 45, 'Weather conditions in Seattle', 'Boeing 737-800'),
('FL612', 'ATL', 'Atlanta', 'ORD', 'Chicago', CURRENT_DATE + INTERVAL '14 hours 0 minutes', NULL, CURRENT_DATE + INTERVAL '19 hours 30 minutes', NULL, 'ON_TIME', 'A20', 0, NULL, 'Boeing 737 MAX 9'),
('FL725', 'BOS', 'Boston', 'ATL', 'Atlanta', CURRENT_DATE + INTERVAL '9 hours 0 minutes', NULL, CURRENT_DATE + INTERVAL '13 hours 30 minutes', NULL, 'ON_TIME', 'B06', 0, NULL, 'Boeing 737-800'),
('FL803', 'DEN', 'Denver', 'ATL', 'Atlanta', CURRENT_DATE + INTERVAL '12 hours 0 minutes', NULL, CURRENT_DATE + INTERVAL '15 hours 45 minutes', NULL, 'ON_TIME', 'B14', 0, NULL, 'Boeing 737 MAX 9'),
('FL512', 'SEA', 'Seattle', 'ATL', 'Atlanta', CURRENT_DATE + INTERVAL '8 hours 30 minutes', NULL, CURRENT_DATE + INTERVAL '16 hours 0 minutes', NULL, 'ON_TIME', 'C10', 0, NULL, 'Boeing 737-800'),
('FL217', 'LAX', 'Los Angeles', 'ATL', 'Atlanta', CURRENT_DATE + INTERVAL '9 hours 30 minutes', NULL, CURRENT_DATE + INTERVAL '15 hours 30 minutes', CURRENT_DATE + INTERVAL '16 hours 30 minutes', 'DELAYED', 'C06', 120, 'Air traffic control delay', 'Boeing 737 MAX 9'),
('FL727', 'BOS', 'Boston', 'ATL', 'Atlanta', CURRENT_DATE + INTERVAL '10 hours 0 minutes', NULL, CURRENT_DATE + INTERVAL '14 hours 30 minutes', CURRENT_DATE + INTERVAL '15 hours 30 minutes', 'DELAYED', 'B08', 60, 'Crew scheduling delay', 'Boeing 737-800'),
('FL930', 'ORD', 'Chicago', 'ATL', 'Atlanta', CURRENT_DATE + INTERVAL '9 hours 0 minutes', NULL, CURRENT_DATE + INTERVAL '12 hours 0 minutes', NULL, 'ON_TIME', 'B10', 0, NULL, 'Boeing 737 MAX 9'),
('FL932', 'ORD', 'Chicago', 'ATL', 'Atlanta', CURRENT_DATE + INTERVAL '11 hours 0 minutes', NULL, CURRENT_DATE + INTERVAL '14 hours 0 minutes', NULL, 'CANCELLED', 'B11', 0, 'Aircraft maintenance', 'Boeing 737 MAX 9'),
('FL410', 'JFK', 'New York', 'ATL', 'Atlanta', CURRENT_DATE + INTERVAL '8 hours 45 minutes', NULL, CURRENT_DATE + INTERVAL '11 hours 45 minutes', NULL, 'ON_TIME', 'A05', 0, NULL, 'Airbus A321neo'),
('FL412', 'JFK', 'New York', 'ATL', 'Atlanta', CURRENT_DATE + INTERVAL '12 hours 30 minutes', NULL, CURRENT_DATE + INTERVAL '15 hours 0 minutes', CURRENT_DATE + INTERVAL '16 hours 15 minutes', 'DELAYED', 'A07', 75, 'Late arriving aircraft', 'Airbus A321neo'),
('FL620', 'SFO', 'San Francisco', 'ATL', 'Atlanta', CURRENT_DATE + INTERVAL '8 hours 0 minutes', NULL, CURRENT_DATE + INTERVAL '15 hours 0 minutes', CURRENT_DATE + INTERVAL '18 hours 0 minutes', 'DELAYED', 'C12', 180, 'Weather conditions in San Francisco', 'Boeing 737 MAX 9'),
('FL450', 'MIA', 'Miami', 'ATL', 'Atlanta', CURRENT_DATE + INTERVAL '9 hours 15 minutes', NULL, CURRENT_DATE + INTERVAL '12 hours 15 minutes', NULL, 'ON_TIME', 'A09', 0, NULL, 'Boeing 737-800'),
('FL449', 'ATL', 'Atlanta', 'MIA', 'Miami', CURRENT_DATE + INTERVAL '18 hours 30 minutes', NULL, CURRENT_DATE + INTERVAL '22 hours 45 minutes', NULL, 'ON_TIME', 'A10', 0, NULL, 'Boeing 737-800'),
('FL304', 'ATL', 'Atlanta', 'JFK', 'New York', CURRENT_DATE + INTERVAL '16 hours 0 minutes', NULL, CURRENT_DATE + INTERVAL '22 hours 15 minutes', NULL, 'ON_TIME', 'A16', 0, NULL, 'Boeing 737 MAX 9'),
('FL306', 'ATL', 'Atlanta', 'JFK', 'New York', CURRENT_DATE + INTERVAL '19 hours 30 minutes', NULL, CURRENT_DATE + INTERVAL '23 hours 45 minutes', NULL, 'ON_TIME', 'A17', 0, NULL, 'Airbus A321neo'),
('FL614', 'ATL', 'Atlanta', 'ORD', 'Chicago', CURRENT_DATE + INTERVAL '17 hours 0 minutes', NULL, CURRENT_DATE + INTERVAL '18 hours 45 minutes', NULL, 'ON_TIME', 'A21', 0, NULL, 'Boeing 737 MAX 9'),
('FL616', 'ATL', 'Atlanta', 'ORD', 'Chicago', CURRENT_DATE + INTERVAL '20 hours 0 minutes', NULL, CURRENT_DATE + INTERVAL '21 hours 45 minutes', NULL, 'ON_TIME', 'A23', 0, NULL, 'Boeing 737-800'),
('FL520', 'ATL', 'Atlanta', 'LAX', 'Los Angeles', CURRENT_DATE + INTERVAL '15 hours 0 minutes', NULL, CURRENT_DATE + INTERVAL '17 hours 30 minutes', NULL, 'ON_TIME', 'A22', 0, NULL, 'Boeing 737 MAX 9'),
('FL522', 'ATL', 'Atlanta', 'LAX', 'Los Angeles', CURRENT_DATE + INTERVAL '18 hours 0 minutes', NULL, CURRENT_DATE + INTERVAL '20 hours 30 minutes', NULL, 'ON_TIME', 'A24', 0, NULL, 'Boeing 737 MAX 9'),
('FL715', 'ATL', 'Atlanta', 'SEA', 'Seattle', CURRENT_DATE + INTERVAL '14 hours 30 minutes', NULL, CURRENT_DATE + INTERVAL '17 hours 15 minutes', NULL, 'ON_TIME', 'C14', 0, NULL, 'Boeing 737-800'),
('FL717', 'ATL', 'Atlanta', 'SEA', 'Seattle', CURRENT_DATE + INTERVAL '18 hours 15 minutes', NULL, CURRENT_DATE + INTERVAL '21 hours 0 minutes', NULL, 'ON_TIME', 'C16', 0, NULL, 'Boeing 737-800'),
('FL810', 'ATL', 'Atlanta', 'DEN', 'Denver', CURRENT_DATE + INTERVAL '16 hours 0 minutes', NULL, CURRENT_DATE + INTERVAL '17 hours 30 minutes', NULL, 'ON_TIME', 'B16', 0, NULL, 'Boeing 737 MAX 9'),
('FL812', 'ATL', 'Atlanta', 'DEN', 'Denver', CURRENT_DATE + INTERVAL '19 hours 0 minutes', NULL, CURRENT_DATE + INTERVAL '20 hours 30 minutes', NULL, 'ON_TIME', 'B18', 0, NULL, 'Boeing 737 MAX 9'),
('FL730', 'ATL', 'Atlanta', 'BOS', 'Boston', CURRENT_DATE + INTERVAL '15 hours 45 minutes', NULL, CURRENT_DATE + INTERVAL '19 hours 0 minutes', NULL, 'ON_TIME', 'B20', 0, NULL, 'Airbus A321neo'),
('FL732', 'ATL', 'Atlanta', 'BOS', 'Boston', CURRENT_DATE + INTERVAL '19 hours 15 minutes', NULL, CURRENT_DATE + INTERVAL '22 hours 30 minutes', NULL, 'ON_TIME', 'B22', 0, NULL, 'Airbus A321neo'),
('FL625', 'ATL', 'Atlanta', 'SFO', 'San Francisco', CURRENT_DATE + INTERVAL '16 hours 30 minutes', NULL, CURRENT_DATE + INTERVAL '19 hours 0 minutes', NULL, 'ON_TIME', 'C18', 0, NULL, 'Boeing 737 MAX 9');

-- Passengers
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

-- FrequentFlyer
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

-- Bookings
INSERT INTO bookings (pnr, passenger_id, booking_date) VALUES
('ABCDE1', 'PAX-2026-00101', CURRENT_DATE - INTERVAL '36 days'),
('FGHIJ2', 'PAX-2026-00102', CURRENT_DATE - INTERVAL '31 days'),
('KLMNO3', 'PAX-2026-00103', CURRENT_DATE - INTERVAL '20 days'),
('PQRST4', 'PAX-2026-00104', CURRENT_DATE - INTERVAL '16 days'),
('UVWXY5', 'PAX-2026-00105', CURRENT_DATE - INTERVAL '23 days'),
('BCDEF6', 'PAX-2026-00106', CURRENT_DATE - INTERVAL '11 days'),
('GHIJK7', 'PAX-2026-00107', CURRENT_DATE - INTERVAL '9 days'),
('LMNOP8', 'PAX-2026-00110', CURRENT_DATE - INTERVAL '13 days'),
('HIJKL9', 'PAX-2026-00111', CURRENT_DATE - INTERVAL '40 days'),
('MNOPQ0', 'PAX-2026-00112', CURRENT_DATE - INTERVAL '7 days'),
('RSTUV1', 'PAX-2026-00113', CURRENT_DATE - INTERVAL '15 days'),
('WXYZA2', 'PAX-2026-00114', CURRENT_DATE - INTERVAL '5 days'),
('BCDFG3', 'PAX-2026-00115', CURRENT_DATE - INTERVAL '18 days'),
('HJKLM4', 'PAX-2026-00116', CURRENT_DATE - INTERVAL '12 days'),
('NPQRS5', 'PAX-2026-00117', CURRENT_DATE - INTERVAL '6 days'),
('TVWXY6', 'PAX-2026-00118', CURRENT_DATE - INTERVAL '21 days'),
('ZABCD7', 'PAX-2026-00119', CURRENT_DATE - INTERVAL '26 days'),
('EFGHI8', 'PAX-2026-00120', CURRENT_DATE - INTERVAL '4 days'),
('JKLMN9', 'PAX-2026-00121', CURRENT_DATE - INTERVAL '8 days'),
('OPQRS0', 'PAX-2026-00122', CURRENT_DATE - INTERVAL '14 days'),
('UVWXZ1', 'PAX-2026-00108', CURRENT_DATE - INTERVAL '19 days'),
('CDEFH2', 'PAX-2026-00109', CURRENT_DATE - INTERVAL '10 days');

-- Booking Segments (all today-relative)
-- Carlos: DEN->ATL->MIA (MISSED)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(1, 1, 'FL801', 'DEN', 'ATL', CURRENT_DATE + INTERVAL '8 hours 30 minutes', CURRENT_DATE + INTERVAL '11 hours 15 minutes', '4A', 'Business', 'CHECKED_IN'),
(1, 2, 'FL445', 'ATL', 'MIA', CURRENT_DATE + INTERVAL '12 hours 30 minutes', CURRENT_DATE + INTERVAL '16 hours 45 minutes', '3C', 'Business', 'CONFIRMED');

-- Ana: LAX->ATL->JFK (SAFE)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(2, 1, 'FL215', 'LAX', 'ATL', CURRENT_DATE + INTERVAL '6 hours 0 minutes', CURRENT_DATE + INTERVAL '11 hours 30 minutes', '12B', 'Economy', 'CHECKED_IN'),
(2, 2, 'FL302', 'ATL', 'JFK', CURRENT_DATE + INTERVAL '13 hours 0 minutes', CURRENT_DATE + INTERVAL '19 hours 15 minutes', '14A', 'Economy', 'CONFIRMED');

-- Roberto: ATL->MIA direct
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(3, 1, 'FL445', 'ATL', 'MIA', CURRENT_DATE + INTERVAL '12 hours 30 minutes', CURRENT_DATE + INTERVAL '16 hours 45 minutes', '1A', 'Business', 'CONFIRMED');

-- Maria: SEA->ATL->ORD (AT_RISK)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(4, 1, 'FL510', 'SEA', 'ATL', CURRENT_DATE + INTERVAL '7 hours 15 minutes', CURRENT_DATE + INTERVAL '12 hours 45 minutes', '8C', 'Economy', 'CHECKED_IN'),
(4, 2, 'FL612', 'ATL', 'ORD', CURRENT_DATE + INTERVAL '14 hours 0 minutes', CURRENT_DATE + INTERVAL '19 hours 30 minutes', '10A', 'Economy', 'CONFIRMED');

-- Jorge: BOS->ATL->MIA (SAFE)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(5, 1, 'FL725', 'BOS', 'ATL', CURRENT_DATE + INTERVAL '9 hours 0 minutes', CURRENT_DATE + INTERVAL '13 hours 30 minutes', '15D', 'Economy', 'CONFIRMED'),
(5, 2, 'FL447', 'ATL', 'MIA', CURRENT_DATE + INTERVAL '15 hours 30 minutes', CURRENT_DATE + INTERVAL '19 hours 45 minutes', '16A', 'Economy', 'CONFIRMED');

-- Isabella: DEN->ATL one-way
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(6, 1, 'FL801', 'DEN', 'ATL', CURRENT_DATE + INTERVAL '8 hours 30 minutes', CURRENT_DATE + INTERVAL '11 hours 15 minutes', '6B', 'Economy', 'CHECKED_IN');

-- Diego: DEN->ATL->JFK (MISSED)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(7, 1, 'FL801', 'DEN', 'ATL', CURRENT_DATE + INTERVAL '8 hours 30 minutes', CURRENT_DATE + INTERVAL '11 hours 15 minutes', '22A', 'Economy', 'CHECKED_IN'),
(7, 2, 'FL302', 'ATL', 'JFK', CURRENT_DATE + INTERVAL '13 hours 0 minutes', CURRENT_DATE + INTERVAL '19 hours 15 minutes', '20C', 'Economy', 'CONFIRMED');

-- Camila: LAX->ATL->ORD (SAFE)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(8, 1, 'FL215', 'LAX', 'ATL', CURRENT_DATE + INTERVAL '6 hours 0 minutes', CURRENT_DATE + INTERVAL '11 hours 30 minutes', '18B', 'Economy', 'CONFIRMED'),
(8, 2, 'FL612', 'ATL', 'ORD', CURRENT_DATE + INTERVAL '14 hours 0 minutes', CURRENT_DATE + INTERVAL '19 hours 30 minutes', '19A', 'Economy', 'CONFIRMED');

-- Lucas: LAX->ATL->JFK (MISSED, FL217 delayed)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(9, 1, 'FL217', 'LAX', 'ATL', CURRENT_DATE + INTERVAL '9 hours 30 minutes', CURRENT_DATE + INTERVAL '15 hours 30 minutes', '14C', 'Economy', 'CHECKED_IN'),
(9, 2, 'FL304', 'ATL', 'JFK', CURRENT_DATE + INTERVAL '16 hours 0 minutes', CURRENT_DATE + INTERVAL '22 hours 15 minutes', '12A', 'Economy', 'CONFIRMED');

-- Sofia: SFO->ATL->SEA (MISSED, no same-day alt)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(10, 1, 'FL620', 'SFO', 'ATL', CURRENT_DATE + INTERVAL '8 hours 0 minutes', CURRENT_DATE + INTERVAL '15 hours 0 minutes', '5A', 'Business', 'CHECKED_IN'),
(10, 2, 'FL717', 'ATL', 'SEA', CURRENT_DATE + INTERVAL '18 hours 15 minutes', CURRENT_DATE + INTERVAL '21 hours 0 minutes', '6C', 'Business', 'CONFIRMED');

-- Mateo: JFK->ATL->ORD (AT_RISK)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(11, 1, 'FL412', 'JFK', 'ATL', CURRENT_DATE + INTERVAL '12 hours 30 minutes', CURRENT_DATE + INTERVAL '15 hours 0 minutes', '20B', 'Economy', 'CHECKED_IN'),
(11, 2, 'FL614', 'ATL', 'ORD', CURRENT_DATE + INTERVAL '17 hours 0 minutes', CURRENT_DATE + INTERVAL '18 hours 45 minutes', '18C', 'Economy', 'CONFIRMED');

-- Valeria (Platinum): BOS->ATL->MIA (MISSED)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(12, 1, 'FL727', 'BOS', 'ATL', CURRENT_DATE + INTERVAL '10 hours 0 minutes', CURRENT_DATE + INTERVAL '14 hours 30 minutes', '2A', 'Business', 'CHECKED_IN'),
(12, 2, 'FL447', 'ATL', 'MIA', CURRENT_DATE + INTERVAL '15 hours 30 minutes', CURRENT_DATE + INTERVAL '19 hours 45 minutes', '1C', 'Business', 'CONFIRMED');

-- Nicolas: SEA->ATL->LAX (SAFE)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(13, 1, 'FL512', 'SEA', 'ATL', CURRENT_DATE + INTERVAL '8 hours 30 minutes', CURRENT_DATE + INTERVAL '16 hours 0 minutes', '16A', 'Economy', 'CONFIRMED'),
(13, 2, 'FL522', 'ATL', 'LAX', CURRENT_DATE + INTERVAL '18 hours 0 minutes', CURRENT_DATE + INTERVAL '20 hours 30 minutes', '17B', 'Economy', 'CONFIRMED');

-- Gabriela: DEN->ATL->SEA (SAFE despite FL801 delay)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(14, 1, 'FL801', 'DEN', 'ATL', CURRENT_DATE + INTERVAL '8 hours 30 minutes', CURRENT_DATE + INTERVAL '11 hours 15 minutes', '9C', 'Economy', 'CHECKED_IN'),
(14, 2, 'FL715', 'ATL', 'SEA', CURRENT_DATE + INTERVAL '14 hours 30 minutes', CURRENT_DATE + INTERVAL '17 hours 15 minutes', '10A', 'Economy', 'CONFIRMED');

-- Daniel: ORD->ATL->MIA (inbound FL932 CANCELLED)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(15, 1, 'FL932', 'ORD', 'ATL', CURRENT_DATE + INTERVAL '11 hours 0 minutes', CURRENT_DATE + INTERVAL '14 hours 0 minutes', '21D', 'Economy', 'CONFIRMED'),
(15, 2, 'FL447', 'ATL', 'MIA', CURRENT_DATE + INTERVAL '15 hours 30 minutes', CURRENT_DATE + INTERVAL '19 hours 45 minutes', '22A', 'Economy', 'CONFIRMED');

-- Renata: JFK->ATL->MIA (AT_RISK)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(16, 1, 'FL410', 'JFK', 'ATL', CURRENT_DATE + INTERVAL '8 hours 45 minutes', CURRENT_DATE + INTERVAL '11 hours 45 minutes', '11B', 'Economy', 'CHECKED_IN'),
(16, 2, 'FL445', 'ATL', 'MIA', CURRENT_DATE + INTERVAL '12 hours 30 minutes', CURRENT_DATE + INTERVAL '16 hours 45 minutes', '12C', 'Economy', 'CONFIRMED');

-- Tomas: LAX->ATL->SEA (SAFE)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(17, 1, 'FL215', 'LAX', 'ATL', CURRENT_DATE + INTERVAL '6 hours 0 minutes', CURRENT_DATE + INTERVAL '11 hours 30 minutes', '13A', 'Economy', 'CONFIRMED'),
(17, 2, 'FL715', 'ATL', 'SEA', CURRENT_DATE + INTERVAL '14 hours 30 minutes', CURRENT_DATE + INTERVAL '17 hours 15 minutes', '14B', 'Economy', 'CONFIRMED');

-- Elena (Platinum): SFO->ATL->DEN (SAFE, borderline)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(18, 1, 'FL620', 'SFO', 'ATL', CURRENT_DATE + INTERVAL '8 hours 0 minutes', CURRENT_DATE + INTERVAL '15 hours 0 minutes', '3A', 'Business', 'CHECKED_IN'),
(18, 2, 'FL812', 'ATL', 'DEN', CURRENT_DATE + INTERVAL '19 hours 0 minutes', CURRENT_DATE + INTERVAL '20 hours 30 minutes', '4B', 'Business', 'CONFIRMED');

-- Felipe: DEN->ATL->BOS (MISSED, tight schedule)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(19, 1, 'FL803', 'DEN', 'ATL', CURRENT_DATE + INTERVAL '12 hours 0 minutes', CURRENT_DATE + INTERVAL '15 hours 45 minutes', '19A', 'Economy', 'CONFIRMED'),
(19, 2, 'FL730', 'ATL', 'BOS', CURRENT_DATE + INTERVAL '15 hours 45 minutes', CURRENT_DATE + INTERVAL '19 hours 0 minutes', '20C', 'Economy', 'CONFIRMED');

-- Paula: ATL->SFO direct
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(20, 1, 'FL625', 'ATL', 'SFO', CURRENT_DATE + INTERVAL '16 hours 30 minutes', CURRENT_DATE + INTERVAL '19 hours 0 minutes', '15A', 'Economy', 'CONFIRMED');

-- Valentina (Platinum): MIA->ATL->DEN (SAFE, long layover)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(21, 1, 'FL450', 'MIA', 'ATL', CURRENT_DATE + INTERVAL '9 hours 15 minutes', CURRENT_DATE + INTERVAL '12 hours 15 minutes', '2C', 'Business', 'CHECKED_IN'),
(21, 2, 'FL810', 'ATL', 'DEN', CURRENT_DATE + INTERVAL '16 hours 0 minutes', CURRENT_DATE + INTERVAL '17 hours 30 minutes', '3A', 'Business', 'CONFIRMED');

-- Andres: BOS->ATL->JFK (AT_RISK)
INSERT INTO booking_segments (booking_id, segment_order, flight_number, origin, destination, departure_time, arrival_time, seat_number, cabin, segment_status) VALUES
(22, 1, 'FL727', 'BOS', 'ATL', CURRENT_DATE + INTERVAL '10 hours 0 minutes', CURRENT_DATE + INTERVAL '14 hours 30 minutes', '24B', 'Economy', 'CHECKED_IN'),
(22, 2, 'FL304', 'ATL', 'JFK', CURRENT_DATE + INTERVAL '16 hours 0 minutes', CURRENT_DATE + INTERVAL '22 hours 15 minutes', '23A', 'Economy', 'CONFIRMED');
