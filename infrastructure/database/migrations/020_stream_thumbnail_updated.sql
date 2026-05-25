-- Время последнего обновления превью (для cache-bust в UI)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'streams' AND column_name = 'thumbnail_updated_at'
    ) THEN
        ALTER TABLE streams ADD COLUMN thumbnail_updated_at TIMESTAMPTZ;
    END IF;
END $$;
