-- Превью трансляции (до эфира, в эфире, на записи)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'streams' AND column_name = 'thumbnail_url'
    ) THEN
        ALTER TABLE streams ADD COLUMN thumbnail_url VARCHAR(500);
    END IF;
END $$;
