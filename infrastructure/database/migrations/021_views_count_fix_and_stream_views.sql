-- Просмотры видео: NULL + 1 в PostgreSQL даёт NULL — нормализуем и пересчитываем из video_views
UPDATE videos SET views_count = 0 WHERE views_count IS NULL;

UPDATE videos v
SET views_count = sub.cnt
FROM (
    SELECT video_id, COUNT(*)::int AS cnt
    FROM video_views
    GROUP BY video_id
) sub
WHERE v.id = sub.video_id;

-- Просмотры трансляций (уникальные зрители + пик одновременных)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'streams' AND column_name = 'views_count'
    ) THEN
        ALTER TABLE streams ADD COLUMN views_count INTEGER NOT NULL DEFAULT 0;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'streams' AND column_name = 'peak_viewers'
    ) THEN
        ALTER TABLE streams ADD COLUMN peak_viewers INTEGER NOT NULL DEFAULT 0;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS stream_views (
    stream_id UUID NOT NULL REFERENCES streams(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    viewed_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (stream_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_stream_views_stream_id ON stream_views(stream_id);
