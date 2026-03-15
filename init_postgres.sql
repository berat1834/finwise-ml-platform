-- FinWise Production Database Initialization
-- PostgreSQL 15 compatible schema

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Applications table
CREATE TABLE IF NOT EXISTS applications (
    id SERIAL PRIMARY KEY,
    application_id VARCHAR(50) UNIQUE NOT NULL,
    customer_id VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Personal Information
    person_age INTEGER,
    person_income DECIMAL(12, 2),
    person_emp_length INTEGER,
    person_home_ownership VARCHAR(20),
    
    -- Loan Information
    loan_amnt DECIMAL(12, 2),
    loan_intent VARCHAR(50),
    loan_grade VARCHAR(5),
    loan_int_rate DECIMAL(5, 2),
    loan_percent_income DECIMAL(5, 4),
    
    -- Credit History
    cb_person_cred_hist_length INTEGER,
    cb_person_default_on_file VARCHAR(1),
    
    -- Model Prediction
    prediction INTEGER,
    probability DECIMAL(5, 4),
    model_version VARCHAR(20),
    
    -- Decision
    decision VARCHAR(20),
    decision_reason TEXT,
    manual_override BOOLEAN DEFAULT FALSE,
    override_reason TEXT,
    
    -- Metadata
    processing_time_ms INTEGER,
    api_version VARCHAR(10)
);

-- Decisions table
CREATE TABLE IF NOT EXISTS decisions (
    id SERIAL PRIMARY KEY,
    application_id VARCHAR(50) NOT NULL,
    decision VARCHAR(20) NOT NULL,
    decision_reason TEXT,
    decided_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    decided_by VARCHAR(100),
    
    FOREIGN KEY (application_id) REFERENCES applications(application_id)
);

-- Users table (JWT authentication)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE
);

-- Manual overrides table
CREATE TABLE IF NOT EXISTS manual_overrides (
    id SERIAL PRIMARY KEY,
    application_id VARCHAR(50) NOT NULL,
    original_decision VARCHAR(20),
    new_decision VARCHAR(20),
    override_reason TEXT,
    overridden_by VARCHAR(100),
    overridden_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (application_id) REFERENCES applications(application_id)
);

-- SLA violations table
CREATE TABLE IF NOT EXISTS sla_violations (
    id SERIAL PRIMARY KEY,
    customer_id VARCHAR(50),
    violation_type VARCHAR(50),
    expected_value DECIMAL(10, 2),
    actual_value DECIMAL(10, 2),
    severity VARCHAR(20),
    ticket_id VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_notes TEXT
);

-- Customer subscriptions table
CREATE TABLE IF NOT EXISTS customer_subscriptions (
    id SERIAL PRIMARY KEY,
    customer_id VARCHAR(50) UNIQUE NOT NULL,
    tier VARCHAR(20) DEFAULT 'basic',
    monthly_fee DECIMAL(10, 2),
    max_requests INTEGER,
    sla_uptime DECIMAL(5, 2),
    sla_response_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE
);

-- Model drift metrics table
CREATE TABLE IF NOT EXISTS drift_metrics (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(100),
    metric_value DECIMAL(10, 6),
    threshold DECIMAL(10, 6),
    is_violation BOOLEAN,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    model_version VARCHAR(20)
);

-- Fairness audit log
CREATE TABLE IF NOT EXISTS fairness_audit_log (
    id SERIAL PRIMARY KEY,
    audit_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    income_quintile VARCHAR(10),
    approval_rate DECIMAL(5, 4),
    disparate_impact_ratio DECIMAL(5, 4),
    is_compliant BOOLEAN,
    notes TEXT
);

-- Indexes for performance
CREATE INDEX idx_applications_customer_id ON applications(customer_id);
CREATE INDEX idx_applications_created_at ON applications(created_at);
CREATE INDEX idx_applications_decision ON applications(decision);
CREATE INDEX idx_decisions_application_id ON decisions(application_id);
CREATE INDEX idx_decisions_decided_at ON decisions(decided_at);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_sla_violations_customer_id ON sla_violations(customer_id);
CREATE INDEX idx_drift_metrics_recorded_at ON drift_metrics(recorded_at);

-- Insert default admin user (password: admin123)
INSERT INTO users (username, password_hash, email, role) 
VALUES (
    'admin',
    'pbkdf2:sha256:260000$8Z3qJ5jK$7c6f8d9e8b7a6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1',
    'admin@finwise.local',
    'admin'
) ON CONFLICT (username) DO NOTHING;

-- Insert sample subscription tiers
INSERT INTO customer_subscriptions (customer_id, tier, monthly_fee, max_requests, sla_uptime, sla_response_time_ms)
VALUES 
    ('customer_001', 'enterprise', 299.99, 100000, 99.9, 100),
    ('customer_002', 'professional', 99.99, 10000, 99.5, 200),
    ('customer_003', 'basic', 29.99, 1000, 99.0, 500)
ON CONFLICT (customer_id) DO NOTHING;

COMMIT;
