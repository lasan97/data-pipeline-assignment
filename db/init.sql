CREATE TABLE IF NOT EXISTS events (
    event_id UUID PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    partner_id VARCHAR(50) NOT NULL,
    user_id VARCHAR(50),
    session_id VARCHAR(50) NOT NULL,
    device_type VARCHAR(20),
    properties JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT events_event_type_check CHECK (
        event_type IN (
            'session_start',
            'landing_page_view',
            'content_view',
            'purchase_start',
            'purchase_complete',
            'payment_failed'
        )
    )
);

CREATE INDEX IF NOT EXISTS idx_events_occurred_at ON events (occurred_at);
CREATE INDEX IF NOT EXISTS idx_events_partner_id ON events (partner_id);
CREATE INDEX IF NOT EXISTS idx_events_event_type ON events (event_type);
CREATE INDEX IF NOT EXISTS idx_events_session_id ON events (session_id);
