-- drop db if exists 
DROP DATABASE IF EXISTS icscv;

-- Create Database
CREATE DATABASE IF NOT EXISTS icscv;
USE icscv;

-- Create Carriers Table
CREATE TABLE IF NOT EXISTS carriers (
    carrier_id INT AUTO_INCREMENT PRIMARY KEY,
    legal_name VARCHAR(255) NOT NULL,
    naic_code VARCHAR(10) NOT NULL,
    payer_id VARCHAR(10),
    contact_phone VARCHAR(20),
    website_url VARCHAR(255),
    state_domicile VARCHAR(2),
    last_updated DATE,
    
    -- Indexes for fast search performance
    INDEX idx_legal_name (legal_name),
    INDEX idx_naic_code (naic_code),
    INDEX idx_payer_id (payer_id)
);

-- Optional: Insert a few dummy records for testing
INSERT INTO carriers (legal_name, naic_code, payer_id, contact_phone, website_url, state_domicile, last_updated)
VALUES 
('Blue Cross Blue Shield of Texas', '12345', 'BCBS01', '800-555-0199', 'https://www.bcbstx.com', 'TX', CURDATE()),
('UnitedHealthcare', '67890', '87726', '800-555-0299', 'https://www.uhc.com', 'MN', CURDATE()),
('Humana Insurance Company', '11223', '60054', '800-555-0399', 'https://www.aetna.com', 'CT', CURDATE()),
('United HealthCare Insurance Company', '12345', 'UHC01', '800-555-1212', 'https://www.uhc.com', 'MN', CURDATE()),
('Aetna Life Insurance Company', '67890', 'AETNA', '888-222-3333', 'https://www.aetna.com', 'CT', CURDATE()),
('Progressive Casualty Insurance Company', '54321', NULL, '800-776-4737', 'https://www.progressive.com', 'OH', CURDATE()),
('United Healthcare Group Insurance Company', '79456', '87765', '1-800-456-7890', 'https://www.uhc.com/providers', 'MN', CURDATE()),
('GEICO Indemnity Company', '35882', 'GEC01', '1-800-841-3000', 'https://www.geico.com/claims', 'MD', CURDATE()),
('State Farm Mutual Automobile Insurance Company', '25178', 'SFI01', '1-800-440-0900', 'https://www.statefarm.com/agent', 'IL', CURDATE());













USE icscv;

ALTER TABLE carriers 
ADD COLUMN address_claims_street VARCHAR(255) NULL,
ADD COLUMN address_claims_city VARCHAR(100) NULL,
ADD COLUMN address_claims_state VARCHAR(2) NULL,
ADD COLUMN address_claims_zip VARCHAR(10) NULL,
ADD COLUMN phone_claims VARCHAR(20) NULL,
ADD COLUMN phone_prior_auth VARCHAR(20) NULL,
ADD COLUMN phone_eligibility VARCHAR(20) NULL,
ADD COLUMN line_of_business VARCHAR(50) NULL COMMENT 'e.g., Commercial, Medicare, Medicaid';

-- Optional: Update existing dummy data with new fields for testing
UPDATE carriers SET 
    address_claims_street = 'P.O. Box 9876',
    address_claims_city = 'Austin',
    address_claims_state = 'TX',
    address_claims_zip = '78701',
    phone_claims = '800-444-1234',
    phone_prior_auth = '800-444-5678',
    phone_eligibility = '800-444-9012',
    line_of_business = 'Commercial, Medicare'
WHERE naic_code = '12345';