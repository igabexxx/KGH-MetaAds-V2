-- =============================================================
-- KGH META ADS — DATABASE SCHEMA
-- PostgreSQL 16
-- =============================================================

-- Create separate schema for n8n
CREATE DATABASE n8n OWNER kgh;

-- =============================================================
-- CAMPAIGNS
-- =============================================================
CREATE TABLE IF NOT EXISTS campaigns (
    id              SERIAL PRIMARY KEY,
    meta_id         VARCHAR(50) UNIQUE NOT NULL,
    name            VARCHAR(255) NOT NULL,
    objective       VARCHAR(100),
    status          VARCHAR(20) DEFAULT 'UNKNOWN',  -- ACTIVE, PAUSED, DELETED, ARCHIVED
    buying_type     VARCHAR(50),
    daily_budget    DECIMAL(15,2),
    lifetime_budget DECIMAL(15,2),
    start_date      DATE,
    end_date        DATE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ad_sets (
    id                  SERIAL PRIMARY KEY,
    meta_id             VARCHAR(50) UNIQUE NOT NULL,
    campaign_id         INTEGER REFERENCES campaigns(id) ON DELETE CASCADE,
    name                VARCHAR(255) NOT NULL,
    status              VARCHAR(20) DEFAULT 'UNKNOWN',
    daily_budget        DECIMAL(15,2),
    lifetime_budget     DECIMAL(15,2),
    targeting_summary   TEXT,
    optimization_goal   VARCHAR(100),
    billing_event       VARCHAR(100),
    bid_amount          DECIMAL(15,2),
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ads (
    id              SERIAL PRIMARY KEY,
    meta_id         VARCHAR(50) UNIQUE NOT NULL,
    adset_id        INTEGER REFERENCES ad_sets(id) ON DELETE CASCADE,
    name            VARCHAR(255) NOT NULL,
    status          VARCHAR(20) DEFAULT 'UNKNOWN',
    creative_type   VARCHAR(50),
    preview_url     TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================
-- CAMPAIGN METRICS (time-series)
-- =============================================================
CREATE TABLE IF NOT EXISTS campaign_metrics (
    id              SERIAL PRIMARY KEY,
    campaign_id     INTEGER REFERENCES campaigns(id) ON DELETE CASCADE,
    date            DATE NOT NULL,
    impressions     BIGINT DEFAULT 0,
    clicks          BIGINT DEFAULT 0,
    spend           DECIMAL(15,2) DEFAULT 0,
    reach           BIGINT DEFAULT 0,
    frequency       DECIMAL(8,4) DEFAULT 0,
    ctr             DECIMAL(8,4) DEFAULT 0,   -- Click-through rate %
    cpc             DECIMAL(15,4) DEFAULT 0,  -- Cost per click
    cpm             DECIMAL(15,4) DEFAULT 0,  -- Cost per 1000 impressions
    cpp             DECIMAL(15,4) DEFAULT 0,  -- Cost per 1000 people reached
    conversions     INTEGER DEFAULT 0,
    cost_per_result DECIMAL(15,4) DEFAULT 0,
    roas            DECIMAL(10,4) DEFAULT 0,
    video_views     BIGINT DEFAULT 0,
    link_clicks     BIGINT DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(campaign_id, date)
);

CREATE TABLE IF NOT EXISTS adset_metrics (
    id              SERIAL PRIMARY KEY,
    adset_id        INTEGER REFERENCES ad_sets(id) ON DELETE CASCADE,
    date            DATE NOT NULL,
    impressions     BIGINT DEFAULT 0,
    clicks          BIGINT DEFAULT 0,
    spend           DECIMAL(15,2) DEFAULT 0,
    reach           BIGINT DEFAULT 0,
    ctr             DECIMAL(8,4) DEFAULT 0,
    cpc             DECIMAL(15,4) DEFAULT 0,
    cpm             DECIMAL(15,4) DEFAULT 0,
    conversions     INTEGER DEFAULT 0,
    cost_per_result DECIMAL(15,4) DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(adset_id, date)
);

-- =============================================================
-- LEADS
-- =============================================================
CREATE TABLE IF NOT EXISTS lead_forms (
    id              SERIAL PRIMARY KEY,
    meta_form_id    VARCHAR(100) UNIQUE NOT NULL,
    name            VARCHAR(255),
    campaign_id     INTEGER REFERENCES campaigns(id),
    questions       JSONB DEFAULT '[]',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS leads (
    id              SERIAL PRIMARY KEY,
    meta_lead_id    VARCHAR(100) UNIQUE,
    form_id         INTEGER REFERENCES lead_forms(id),
    campaign_id     INTEGER REFERENCES campaigns(id),
    ad_id           INTEGER REFERENCES ads(id),
    -- Contact Info
    full_name       VARCHAR(255),
    email           VARCHAR(255),
    phone           VARCHAR(50),
    -- Custom fields from form
    custom_fields   JSONB DEFAULT '{}',
    -- Scoring
    score           INTEGER DEFAULT 0,
    score_label     VARCHAR(10) DEFAULT 'COLD',  -- HOT, WARM, COLD
    score_reason    TEXT,
    -- Status & Assignment
    status          VARCHAR(20) DEFAULT 'NEW',   -- NEW, CONTACTED, QUALIFIED, PROPOSAL, WON, LOST
    assigned_to     VARCHAR(100),
    notes           TEXT,
    -- Source tracking
    source          VARCHAR(50) DEFAULT 'META_LEAD_ADS',
    utm_source      VARCHAR(100),
    utm_medium      VARCHAR(100),
    utm_campaign    VARCHAR(100),
    -- Timestamps
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    contacted_at    TIMESTAMPTZ,
    qualified_at    TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS lead_activities (
    id              SERIAL PRIMARY KEY,
    lead_id         INTEGER REFERENCES leads(id) ON DELETE CASCADE,
    action_type     VARCHAR(50) NOT NULL,  -- STATUS_CHANGE, NOTE_ADDED, CALL, WHATSAPP, EMAIL
    description     TEXT,
    performed_by    VARCHAR(100) DEFAULT 'system',
    metadata        JSONB DEFAULT '{}',
    timestamp       TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================
-- AUTOMATION RULES
-- =============================================================
CREATE TABLE IF NOT EXISTS automation_rules (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    trigger_type    VARCHAR(50) NOT NULL,  -- METRIC_THRESHOLD, SCHEDULE, WEBHOOK
    conditions      JSONB NOT NULL DEFAULT '[]',
    -- e.g.: [{"metric": "cpa", "operator": ">", "value": 150000, "window_hours": 24}]
    actions         JSONB NOT NULL DEFAULT '[]',
    -- e.g.: [{"type": "PAUSE_AD", "target": "campaign"}, {"type": "NOTIFY", "channel": "telegram"}]
    scope           VARCHAR(20) DEFAULT 'ALL',  -- ALL, CAMPAIGN, ADSET, AD
    scope_ids       JSONB DEFAULT '[]',
    is_active       BOOLEAN DEFAULT true,
    last_triggered  TIMESTAMPTZ,
    trigger_count   INTEGER DEFAULT 0,
    cooldown_minutes INTEGER DEFAULT 60,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS automation_logs (
    id              SERIAL PRIMARY KEY,
    rule_id         INTEGER REFERENCES automation_rules(id) ON DELETE SET NULL,
    rule_name       VARCHAR(255),
    action_taken    VARCHAR(100),
    target_type     VARCHAR(50),
    target_id       VARCHAR(100),
    details         JSONB DEFAULT '{}',
    status          VARCHAR(20) DEFAULT 'SUCCESS',  -- SUCCESS, FAILED, SKIPPED
    error_message   TEXT,
    executed_at     TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================
-- AI INSIGHTS
-- =============================================================
CREATE TABLE IF NOT EXISTS ai_insights (
    id              SERIAL PRIMARY KEY,
    insight_type    VARCHAR(50) NOT NULL,  -- DAILY_REPORT, CAMPAIGN_ANALYSIS, LEAD_SCORING
    subject         VARCHAR(255),
    content         TEXT NOT NULL,
    data_snapshot   JSONB DEFAULT '{}',
    model_used      VARCHAR(100),
    tokens_used     INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================
-- NOTIFICATIONS
-- =============================================================
CREATE TABLE IF NOT EXISTS notifications (
    id              SERIAL PRIMARY KEY,
    title           VARCHAR(255) NOT NULL,
    message         TEXT NOT NULL,
    type            VARCHAR(30) DEFAULT 'INFO',  -- INFO, SUCCESS, WARNING, ERROR
    channel         VARCHAR(30),  -- TELEGRAM, EMAIL, DASHBOARD
    is_read         BOOLEAN DEFAULT false,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================
-- SYSTEM CONFIG
-- =============================================================
CREATE TABLE IF NOT EXISTS system_config (
    key             VARCHAR(100) PRIMARY KEY,
    value           TEXT,
    description     TEXT,
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Default config values
INSERT INTO system_config (key, value, description) VALUES
    ('sync_interval_minutes', '15', 'How often to sync data from Meta API'),
    ('default_score_hot_threshold', '70', 'Score >= this = HOT lead'),
    ('default_score_warm_threshold', '40', 'Score >= this = WARM lead'),
    ('daily_report_hour_wib', '8', 'Hour in WIB to send daily AI report'),
    ('max_cpa_alert', '200000', 'Alert when CPA exceeds this (IDR)'),
    ('budget_guard_enabled', 'true', 'Enable automatic budget guard')
ON CONFLICT (key) DO NOTHING;

-- =============================================================
-- INDEXES for performance
-- =============================================================
CREATE INDEX IF NOT EXISTS idx_campaigns_meta_id ON campaigns(meta_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status);
CREATE INDEX IF NOT EXISTS idx_campaign_metrics_date ON campaign_metrics(date);
CREATE INDEX IF NOT EXISTS idx_campaign_metrics_campaign_date ON campaign_metrics(campaign_id, date);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_score_label ON leads(score_label);
CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at);
CREATE INDEX IF NOT EXISTS idx_leads_phone ON leads(phone);
CREATE INDEX IF NOT EXISTS idx_lead_activities_lead_id ON lead_activities(lead_id);
CREATE INDEX IF NOT EXISTS idx_automation_logs_executed_at ON automation_logs(executed_at);
CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(is_read);

-- =============================================================
-- UPDATED_AT trigger function
-- =============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_campaigns_updated_at
    BEFORE UPDATE ON campaigns FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_leads_updated_at
    BEFORE UPDATE ON leads FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_automation_rules_updated_at
    BEFORE UPDATE ON automation_rules FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================
-- SEED: Default automation rules
-- =============================================================
INSERT INTO automation_rules (name, description, trigger_type, conditions, actions, is_active) VALUES
(
    'Budget Guard — High CPA Alert',
    'Pause campaign jika CPA > 200.000 IDR dalam 24 jam terakhir',
    'METRIC_THRESHOLD',
    '[{"metric": "cost_per_result", "operator": ">", "value": 200000, "window_hours": 24}]',
    '[{"type": "NOTIFY", "channel": "telegram", "message": "⚠️ CPA tinggi: {campaign_name} CPA = {cpa}"}]',
    true
),
(
    'CTR Drop Alert',
    'Notifikasi jika CTR turun lebih dari 50% dibanding 3 hari sebelumnya',
    'METRIC_THRESHOLD',
    '[{"metric": "ctr", "operator": "drop_pct", "value": 50, "window_hours": 72}]',
    '[{"type": "NOTIFY", "channel": "telegram", "message": "📉 CTR turun drastis: {campaign_name}"}]',
    true
),
(
    'Spend Spike Alert',
    'Alert jika spend harian melebihi 150% dari rata-rata 7 hari',
    'METRIC_THRESHOLD',
    '[{"metric": "spend", "operator": "spike_pct", "value": 150, "window_days": 7}]',
    '[{"type": "NOTIFY", "channel": "telegram", "message": "🔥 Spend spike terdeteksi: {campaign_name}"}]',
    true
)
ON CONFLICT DO NOTHING;
