-- Уникальность (video_id, user_id) для ON CONFLICT в grant_access
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_video_user_access_video_user'
    ) THEN
        ALTER TABLE video_user_access
            ADD CONSTRAINT uq_video_user_access_video_user UNIQUE (video_id, user_id);
    END IF;
END $$;
