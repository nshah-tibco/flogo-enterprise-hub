-- ============================================================================
-- Real Estate Lead Engagement Assistant — RESET to a clean, current-dated demo
-- Run between demo runs to undo agent writes (bookings, stage changes,
-- recommendations, follow-ups) and refresh volatile dates.
--
--   psql -U postgres -d realestate -f reset_data.sql
-- ============================================================================

TRUNCATE follow_up_tasks, appointments, lead_activity, listings, leads, agents, area_market_stats
  RESTART IDENTITY CASCADE;

-- standalone sequences (not reset by RESTART IDENTITY)
ALTER SEQUENCE appt_seq RESTART WITH 70001;
ALTER SEQUENCE task_seq RESTART WITH 90001;

INSERT INTO agents (agent_id, full_name, email, phone, brokerage, license_no, service_area, specialization) VALUES
('AGT-001','Rachel Green','rachel.green@brightpathrealty.com','+1-512-555-0142','Brightpath Realty','TX-0678901','Austin, TX','Buyer Representation'),
('AGT-002','Tom Alvarez','tom.alvarez@brightpathrealty.com','+1-512-555-0176','Brightpath Realty','TX-0678944','Round Rock, TX','Listings & Sellers'),
('AGT-003','Nina Patel','nina.patel@brightpathrealty.com','+1-512-555-0188','Brightpath Realty','TX-0679002','Cedar Park, TX','Luxury Homes'),
('AGT-004','Chris Bauer','chris.bauer@brightpathrealty.com','+1-512-555-0199','Brightpath Realty','TX-0679055','Austin Metro','First-Time Buyers');

INSERT INTO leads (lead_id, first_name, last_name, email, phone, lead_type, stage, budget_min, budget_max, preferred_city, preferred_zip, min_bedrooms, min_bathrooms, property_type_pref, timeline, source, assigned_agent_id, created_at, last_activity_at, notes) VALUES
('LEAD-2026-00001','Ava','Thompson','ava.thompson@example.com','+1-512-555-1001','Buyer','Nurturing',500000,750000,'Austin','78704',3,2.0,'Single Family','0-3 months','Facebook Ad','AGT-001', CURRENT_TIMESTAMP - INTERVAL '21 days', CURRENT_TIMESTAMP - INTERVAL '2 days','Warm buyer, wants Bouldin/Zilker area, pre-approved.'),
('LEAD-2026-00002','Marcus','Reed','marcus.reed@example.com','+1-512-555-1002','Buyer','Active',400000,600000,'Round Rock','78664',3,2.0,'Single Family','0-3 months','Website','AGT-002', CURRENT_TIMESTAMP - INTERVAL '35 days', CURRENT_TIMESTAMP - INTERVAL '1 days','Has an upcoming showing booked.'),
('LEAD-2026-00003','Priya','Nair','priya.nair@example.com','+1-512-555-1003','Buyer','New',300000,450000,'Austin','78745',2,2.0,'Condo','3-6 months','Google Ad','AGT-004', CURRENT_TIMESTAMP - INTERVAL '3 days', CURRENT_TIMESTAMP - INTERVAL '3 days','New lead from search ad, first-time buyer.'),
('LEAD-2026-00004','Daniel','Cho','daniel.cho@example.com','+1-512-555-1004','Seller','Active',NULL,NULL,'Cedar Park','78613',NULL,NULL,'Single Family','0-3 months','Referral','AGT-002', CURRENT_TIMESTAMP - INTERVAL '14 days', CURRENT_TIMESTAMP - INTERVAL '4 days','Selling current home, wants market pricing guidance.'),
('LEAD-2026-00005','Sofia','Ramirez','sofia.ramirez@example.com','+1-512-555-1005','Buyer','Under Contract',600000,800000,'Austin','78704',4,3.0,'Single Family','Closing','Website','AGT-001', CURRENT_TIMESTAMP - INTERVAL '60 days', CURRENT_TIMESTAMP - INTERVAL '5 days','Offer accepted, in escrow — no new bookings.'),
('LEAD-2026-00006','Liam','O''Brien','liam.obrien@example.com','+1-512-555-1006','Buyer','Lost',250000,350000,'Round Rock','78664',2,1.0,'Condo','No timeline','Google Ad','AGT-004', CURRENT_TIMESTAMP - INTERVAL '120 days', CURRENT_TIMESTAMP - INTERVAL '75 days','Went cold, out of budget for area — re-engage only.'),
('LEAD-2026-00007','Grace','Kim','grace.kim@example.com','+1-512-555-1007','Both','Nurturing',900000,1400000,'Cedar Park','78613',4,3.5,'Single Family','6-12 months','Referral','AGT-003', CURRENT_TIMESTAMP - INTERVAL '18 days', CURRENT_TIMESTAMP - INTERVAL '6 days','Luxury buyer, also selling; long timeline.'),
('LEAD-2026-00008','Noah','Bennett','noah.bennett@example.com','+1-512-555-1008','Buyer','Nurturing',450000,650000,'Austin','78745',3,2.0,'Townhouse','3-6 months','Facebook Ad','AGT-004', CURRENT_TIMESTAMP - INTERVAL '10 days', CURRENT_TIMESTAMP - INTERVAL '2 days','Recently sent home recommendations; opened email.');

INSERT INTO listings (listing_id, mls_id, address, city, state, zip, price, bedrooms, bathrooms, sqft, lot_size_sqft, property_type, year_built, status, days_on_market, listing_agent_id, description, url) VALUES
('LST-50001','MLS-1001','512 Bouldin Ave','Austin','TX','78704',689000,3,2.0,1650,6100,'Single Family',1998,'Active',12,'AGT-001','Updated bungalow steps from Zilker, open kitchen, large deck.','https://listings.example.com/LST-50001'),
('LST-50002','MLS-1002','908 Live Oak St','Austin','TX','78704',725000,3,2.5,1820,5800,'Single Family',2005,'Active',7,'AGT-001','Modern 2-story, primary down, walkable to South Congress.','https://listings.example.com/LST-50002'),
('LST-50003','MLS-1003','245 Sunset Trl #12','Austin','TX','78745',415000,2,2.0,1100,0,'Condo',2016,'Active',21,'AGT-004','Bright corner condo, community pool, low HOA.','https://listings.example.com/LST-50003'),
('LST-50004','MLS-1004','77 Riverside Dr #210','Austin','TX','78745',389000,2,2.0,980,0,'Condo',2012,'Active',30,'AGT-004','Move-in ready condo near shops, covered parking.','https://listings.example.com/LST-50004'),
('LST-50005','MLS-1005','1330 Forest Creek Dr','Round Rock','TX','78664',525000,3,2.0,1900,7200,'Single Family',2009,'Active',9,'AGT-002','Single-story with office, greenbelt lot, great schools.','https://listings.example.com/LST-50005'),
('LST-50006','MLS-1006','402 Deer Run Ln','Round Rock','TX','78664',575000,4,2.5,2200,7600,'Single Family',2014,'Active',15,'AGT-002','Spacious 4-bed, game room, covered patio.','https://listings.example.com/LST-50006'),
('LST-50007','MLS-1007','88 Hill Country Blvd','Cedar Park','TX','78613',1195000,4,3.5,3400,12000,'Single Family',2019,'Active',24,'AGT-003','Luxury build, chef kitchen, pool, hill-country views.','https://listings.example.com/LST-50007'),
('LST-50008','MLS-1008','15 Vista Ridge Ct','Cedar Park','TX','78613',1350000,5,4.5,4100,15000,'Single Family',2021,'Active',33,'AGT-003','Estate home, media room, 3-car garage, oversized lot.','https://listings.example.com/LST-50008'),
('LST-50009','MLS-1009','630 Meadow Ln','Austin','TX','78704',640000,3,2.0,1580,5400,'Single Family',2001,'Pending',40,'AGT-001','Charming home, under contract — accepting backups.','https://listings.example.com/LST-50009'),
('LST-50010','MLS-1010','210 Oak Bend Dr','Cedar Park','TX','78613',720000,4,3.0,2600,9000,'Single Family',2011,'Sold',0,'AGT-003','Recently sold — comparable for pricing only.','https://listings.example.com/LST-50010'),
('LST-50011','MLS-1011','501 Congress Ave #1802','Austin','TX','78701',899000,2,2.0,1400,0,'Condo',2018,'Active',18,'AGT-003','Downtown high-rise condo, skyline views, concierge.','https://listings.example.com/LST-50011'),
('LST-50012','MLS-1012','1725 Parkside Dr','Austin','TX','78745',610000,3,2.5,1750,3200,'Townhouse',2017,'Active',11,'AGT-004','End-unit townhome, rooftop terrace, 2-car garage.','https://listings.example.com/LST-50012');

INSERT INTO lead_activity (lead_id, listing_id, activity_type, detail, created_at) VALUES
('LEAD-2026-00001',NULL,'Search','3-bed single family in 78704 under $750k', CURRENT_TIMESTAMP - INTERVAL '9 days'),
('LEAD-2026-00001','LST-50001','Viewed Listing','Viewed 512 Bouldin Ave', CURRENT_TIMESTAMP - INTERVAL '8 days'),
('LEAD-2026-00001','LST-50001','Saved Listing','Saved 512 Bouldin Ave', CURRENT_TIMESTAMP - INTERVAL '8 days'),
('LEAD-2026-00001','LST-50002','Viewed Listing','Viewed 908 Live Oak St', CURRENT_TIMESTAMP - INTERVAL '2 days'),
('LEAD-2026-00002','LST-50005','Viewed Listing','Viewed 1330 Forest Creek Dr', CURRENT_TIMESTAMP - INTERVAL '6 days'),
('LEAD-2026-00002','LST-50006','Saved Listing','Saved 402 Deer Run Ln', CURRENT_TIMESTAMP - INTERVAL '5 days'),
('LEAD-2026-00003',NULL,'Search','2-bed condo in 78745 under $450k', CURRENT_TIMESTAMP - INTERVAL '3 days'),
('LEAD-2026-00007','LST-50007','Viewed Listing','Viewed 88 Hill Country Blvd', CURRENT_TIMESTAMP - INTERVAL '6 days'),
('LEAD-2026-00008','LST-50012','Viewed Listing','Viewed 1725 Parkside Dr', CURRENT_TIMESTAMP - INTERVAL '4 days'),
('LEAD-2026-00008',NULL,'Recommendation Sent','Sent listings: LST-50012, LST-50003 (townhome + condo matches)', CURRENT_TIMESTAMP - INTERVAL '3 days'),
('LEAD-2026-00008',NULL,'Email Opened','Opened recommendation email', CURRENT_TIMESTAMP - INTERVAL '2 days');

INSERT INTO appointments (lead_id, listing_id, agent_id, scheduled_for, status, notes) VALUES
('LEAD-2026-00002','LST-50005','AGT-002', CURRENT_DATE + INTERVAL '3 days' + TIME '15:00', 'Confirmed','Showing at 1330 Forest Creek Dr.');

-- follow_up_tasks intentionally empty (agent-filled)

INSERT INTO area_market_stats (city, zip, median_price, avg_days_on_market, active_listings, median_price_per_sqft, yoy_price_change_pct, as_of_month) VALUES
('Austin','78704',735000,28,42,465.00,3.20, to_char(CURRENT_DATE,'Mon YYYY')),
('Austin','78745',520000,33,55,360.00,2.10, to_char(CURRENT_DATE,'Mon YYYY')),
('Round Rock','78664',545000,25,38,250.00,4.00, to_char(CURRENT_DATE,'Mon YYYY')),
('Cedar Park','78613',815000,40,22,300.00,1.50, to_char(CURRENT_DATE,'Mon YYYY'));
