-- Stream visibility (DGI employees vs private invite) and invited viewers
ALTER TABLE streams ADD COLUMN IF NOT EXISTS visibility VARCHAR(32) NOT NULL DEFAULT 'dgi_employees';
ALTER TABLE streams ADD COLUMN IF NOT EXISTS mediamtx_path VARCHAR(255);
ALTER TABLE streams ADD COLUMN IF NOT EXISTS recording_dir VARCHAR(512);

CREATE TABLE IF NOT EXISTS stream_viewers (
    stream_id UUID NOT NULL REFERENCES streams(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (stream_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_stream_viewers_user ON stream_viewers(user_id);

COMMENT ON COLUMN streams.visibility IS 'dgi_employees | private';
