-- Add metadata columns for enhanced semantic search
ALTER TABLE airports 
ADD COLUMN IF NOT EXISTS hub_type VARCHAR(50),
ADD COLUMN IF NOT EXISTS price_tier VARCHAR(20),
ADD COLUMN IF NOT EXISTS annual_passengers INT,
ADD COLUMN IF NOT EXISTS facilities TEXT,
ADD COLUMN IF NOT EXISTS description TEXT;

-- Update airports with hub classifications based on route count
UPDATE airports a
SET hub_type = CASE
    WHEN (SELECT COUNT(*) FROM routes WHERE source_airport_id = a.id OR dest_airport_id = a.id) > 50 THEN 'major-hub'
    WHEN (SELECT COUNT(*) FROM routes WHERE source_airport_id = a.id OR dest_airport_id = a.id) > 20 THEN 'regional-hub'
    WHEN (SELECT COUNT(*) FROM routes WHERE source_airport_id = a.id OR dest_airport_id = a.id) > 5 THEN 'connector'
    ELSE 'small'
END;

-- Assign price tiers based on country (simplified heuristic)
UPDATE airports 
SET price_tier = CASE
    WHEN country IN ('United States', 'United Kingdom', 'Japan', 'Switzerland', 'Norway', 'Singapore') THEN 'premium'
    WHEN country IN ('India', 'Thailand', 'Vietnam', 'Indonesia', 'Philippines', 'Malaysia') THEN 'budget-friendly'
    WHEN country IN ('United Arab Emirates', 'Qatar', 'Saudi Arabia') THEN 'luxury'
    ELSE 'moderate'
END;

-- Add sample passenger data (realistic estimates based on hub type)
UPDATE airports
SET annual_passengers = CASE
    WHEN hub_type = 'major-hub' THEN 20000000 + (id % 30000000)
    WHEN hub_type = 'regional-hub' THEN 5000000 + (id % 10000000)
    WHEN hub_type = 'connector' THEN 1000000 + (id % 3000000)
    ELSE 100000 + (id % 900000)
END;

-- Add facilities descriptions
UPDATE airports
SET facilities = CASE
    WHEN price_tier = 'luxury' THEN 'Premium lounges, Duty-free shopping, Spa services, Fine dining, Private terminals'
    WHEN price_tier = 'premium' THEN 'Business lounges, Shopping, Restaurants, Fast WiFi, Conference rooms'
    WHEN price_tier = 'budget-friendly' THEN 'Basic amenities, Food courts, Budget shops, Free WiFi'
    ELSE 'Standard services, Cafes, Shops, WiFi'
END;

-- Create enhanced description for semantic search
UPDATE airports
SET description = CONCAT(
    name, ' in ', city, ', ', country, '. ',
    'A ', hub_type, ' airport with ', price_tier, ' pricing. ',
    'Handles approximately ', FORMAT(annual_passengers, 0), ' passengers annually. ',
    facilities
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_hub_type ON airports(hub_type);
CREATE INDEX IF NOT EXISTS idx_price_tier ON airports(price_tier);
CREATE INDEX IF NOT EXISTS idx_passengers ON airports(annual_passengers);
