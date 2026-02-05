-- IPL (Individual Pacing List) Database Setup
-- Run this entire script in your PostgreSQL database

-- Create IPL Modules table
CREATE TABLE ipl_modules (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL UNIQUE,
    subject VARCHAR(50),
    grade_level INTEGER,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create IPL Entries table
CREATE TABLE ipl_entries (
    id SERIAL PRIMARY KEY,
    module_id INTEGER NOT NULL REFERENCES ipl_modules(id) ON DELETE CASCADE,
    unit_name VARCHAR(200),
    ipl_title VARCHAR(200), 
    goal_text TEXT,
    order_index INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX idx_ipl_entries_module_id ON ipl_entries(module_id);
CREATE INDEX idx_ipl_entries_order ON ipl_entries(module_id, order_index);

-- Insert 28 IPL modules
INSERT INTO ipl_modules (id, name) VALUES
(1, 'Module: Astronomy'),
(2, 'Module: Bioengineering'),
(3, 'Module: Chemical Math'),
(4, 'Module: Climate Change'),
(5, 'Module: Confident Consumer'),
(6, 'Module: Environmental Math'),
(7, 'Module: Factoring and Polynomials'),
(8, 'Module: Forensic Math'),
(9, 'Module: Geometric Packing'),
(10, 'Module: Gravity of Algebra'),
(11, 'Module: Home Makeover'),
(12, 'Module: Hotel Management'),
(13, 'Module: Laser Geometry'),
(14, 'Module: Lenses and Optics'),
(15, 'Module: Math Behind Your Meals'),
(16, 'Module: Nuclear Energy'),
(17, 'Module: Population Perspectives'),
(18, 'Module: Projectile Motion'),
(19, 'Module: Properties of Math'),
(20, 'Module: Sports Statistics'),
(21, 'Module: Statistical Analysis'),
(22, 'Module: Supply and Demand'),
(23, 'Module: The Universe'),
(24, 'Module: Unsolved Mysteries'),
(25, 'Module: Water Management'),
(26, 'Module: Water Quality'),
(27, 'Module: Weights and Measures'),
(28, 'Module: Where in the World');

-- Reset module sequence
SELECT setval('ipl_modules_id_seq', 28);

-- Note: Due to length, the entry data would be inserted via separate commands
-- This file creates the structure. Run the generated INSERT statements separately.

-- Summary query to check setup
-- SELECT 
--     m.name as module_name,
--     COUNT(e.id) as entry_count
-- FROM ipl_modules m 
-- LEFT JOIN ipl_entries e ON m.id = e.module_id 
-- GROUP BY m.id, m.name 
-- ORDER BY m.id;