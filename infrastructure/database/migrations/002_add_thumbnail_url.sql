-- Add thumbnail_url column to videos table if not exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'videos' AND column_name = 'thumbnail_url') THEN
        ALTER TABLE videos ADD COLUMN thumbnail_url VARCHAR(500);
    END IF;
END $$;
