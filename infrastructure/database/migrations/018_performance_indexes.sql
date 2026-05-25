-- Индексы для горячих запросов (фаза 2 оптимизации)

CREATE INDEX IF NOT EXISTS idx_videos_status_created
    ON videos (status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_videos_user_id
    ON videos (user_id);

CREATE INDEX IF NOT EXISTS idx_videos_channel_status
    ON videos (channel_id, status)
    WHERE channel_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_channels_owner_id
    ON channels (owner_id);

CREATE INDEX IF NOT EXISTS idx_subscriptions_channel_id
    ON subscriptions (channel_id);

CREATE INDEX IF NOT EXISTS idx_subscriptions_subscriber_id
    ON subscriptions (subscriber_id);

CREATE INDEX IF NOT EXISTS idx_video_user_access_video_user
    ON video_user_access (video_id, user_id);
