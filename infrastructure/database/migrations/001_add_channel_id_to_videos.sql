-- Migration: Add channel_id column to videos table
-- Created: 2026-05-03

-- Add channel_id column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'videos' 
        AND column_name = 'channel_id'
    ) THEN
        ALTER TABLE videos 
        ADD COLUMN channel_id UUID REFERENCES channels(id) ON DELETE SET NULL;
        
        CREATE INDEX IF NOT EXISTS idx_videos_channel_id ON videos(channel_id);
        
        RAISE NOTICE 'Added channel_id column to videos table';
    ELSE
        RAISE NOTICE 'channel_id column already exists in videos table';
    END IF;
END $$;
