-- PostgreSQL schema for video hosting microservices
-- Run this script to initialize the database

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Users and authentication
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    parent_id UUID REFERENCES roles(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE role_permissions (
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255), -- NULL for LDAP/ESIA users
    ldap_dn VARCHAR(255),
    esia_id VARCHAR(255),
    role_id UUID NOT NULL REFERENCES roles(id),
    is_active BOOLEAN DEFAULT TRUE,
    is_employee BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Channels
CREATE TABLE channels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    handle VARCHAR(50) UNIQUE NOT NULL, -- @username style handle
    avatar_url VARCHAR(500),
    banner_url VARCHAR(500),
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subscribers_count INTEGER DEFAULT 0,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Videos
CREATE TABLE videos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    channel_id UUID REFERENCES channels(id) ON DELETE SET NULL,
    duration INTERVAL,
    resolution VARCHAR(20), -- e.g., '1920x1080'
    bitrate INTEGER, -- in kbps
    file_size BIGINT, -- in bytes
    minio_key VARCHAR(255) UNIQUE NOT NULL,
    hls_playlist_url VARCHAR(500),
    thumbnail_url VARCHAR(500),
    status VARCHAR(20) DEFAULT 'uploaded' CHECK (status IN ('uploaded', 'transcoding', 'ready', 'failed')),
    is_private BOOLEAN DEFAULT FALSE,
    tags TEXT[], -- array of tags
    views_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Live streams
CREATE TABLE streams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rtmp_key VARCHAR(255) UNIQUE NOT NULL,
    hls_url VARCHAR(500),
    is_live BOOLEAN DEFAULT FALSE,
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    archived_video_id UUID REFERENCES videos(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Video views and analytics
CREATE TABLE video_views (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    ip_address INET,
    user_agent TEXT,
    watched_duration INTERVAL,
    viewed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Video likes
CREATE TABLE video_likes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(video_id, user_id)
);

-- Subtitles
CREATE TABLE subtitles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    language VARCHAR(10) DEFAULT 'ru',
    content TEXT NOT NULL, -- WebVTT format
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Search index (for Elasticsearch sync)
CREATE TABLE search_index (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    title_vector TSVECTOR,
    description_vector TSVECTOR,
    subtitles_vector TSVECTOR,
    tags_vector TSVECTOR,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Subscriptions
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subscriber_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    channel_id UUID NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(subscriber_id, channel_id)
);

-- Notifications
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL, -- 'video_ready', 'stream_start', 'new_video', etc.
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Audit logs
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50), -- 'video', 'stream', etc.
    resource_id UUID,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role_id ON users(role_id);
CREATE INDEX idx_channels_owner_id ON channels(owner_id);
CREATE INDEX idx_channels_handle ON channels(handle);
CREATE INDEX idx_videos_user_id ON videos(user_id);
CREATE INDEX idx_videos_channel_id ON videos(channel_id);
CREATE INDEX idx_videos_status ON videos(status);
CREATE INDEX idx_videos_created_at ON videos(created_at DESC);
CREATE INDEX idx_streams_user_id ON streams(user_id);
CREATE INDEX idx_streams_is_live ON streams(is_live);
CREATE INDEX idx_video_views_video_id ON video_views(video_id);
CREATE INDEX idx_video_views_user_id ON video_views(user_id);
CREATE INDEX idx_subtitles_video_id ON subtitles(video_id);
CREATE INDEX idx_subscriptions_subscriber_id ON subscriptions(subscriber_id);
CREATE INDEX idx_subscriptions_channel_id ON subscriptions(channel_id);
CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_is_read ON notifications(is_read);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);

-- Full-text search indexes
CREATE INDEX idx_search_title ON search_index USING GIN (title_vector);
CREATE INDEX idx_search_description ON search_index USING GIN (description_vector);
CREATE INDEX idx_search_subtitles ON search_index USING GIN (subtitles_vector);
CREATE INDEX idx_search_tags ON search_index USING GIN (tags_vector);

-- Triggers for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_channels_updated_at BEFORE UPDATE ON channels FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_videos_updated_at BEFORE UPDATE ON videos FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger for search_index update
CREATE OR REPLACE FUNCTION update_search_index()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO search_index (video_id, title_vector, description_vector, tags_vector, updated_at)
    VALUES (NEW.id, to_tsvector('russian', NEW.title), to_tsvector('russian', COALESCE(NEW.description, '')), to_tsvector('russian', array_to_string(NEW.tags, ' ')), NOW())
    ON CONFLICT (video_id) DO UPDATE SET
        title_vector = to_tsvector('russian', EXCLUDED.title_vector),
        description_vector = to_tsvector('russian', EXCLUDED.description_vector),
        tags_vector = to_tsvector('russian', EXCLUDED.tags_vector),
        updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trigger_update_search_index AFTER INSERT OR UPDATE ON videos FOR EACH ROW EXECUTE FUNCTION update_search_index();

-- Insert default roles and permissions
INSERT INTO roles (name, description) VALUES
('admin', 'System administrator with full access'),
('manager', 'Department manager'),
('employee', 'Regular employee');

INSERT INTO permissions (name, description) VALUES
('upload_video', 'Can upload videos'),
('view_private_videos', 'Can view private videos'),
('manage_users', 'Can manage users'),
('manage_streams', 'Can manage live streams'),
('view_audit_logs', 'Can view audit logs');

-- Assign permissions to roles (example)
INSERT INTO role_permissions (role_id, permission_id) VALUES
((SELECT id FROM roles WHERE name = 'admin'), (SELECT id FROM permissions WHERE name = 'upload_video')),
((SELECT id FROM roles WHERE name = 'admin'), (SELECT id FROM permissions WHERE name = 'view_private_videos')),
((SELECT id FROM roles WHERE name = 'admin'), (SELECT id FROM permissions WHERE name = 'manage_users')),
((SELECT id FROM roles WHERE name = 'admin'), (SELECT id FROM permissions WHERE name = 'manage_streams')),
((SELECT id FROM roles WHERE name = 'admin'), (SELECT id FROM permissions WHERE name = 'view_audit_logs')),
((SELECT id FROM roles WHERE name = 'manager'), (SELECT id FROM permissions WHERE name = 'upload_video')),
((SELECT id FROM roles WHERE name = 'manager'), (SELECT id FROM permissions WHERE name = 'view_private_videos')),
((SELECT id FROM roles WHERE name = 'manager'), (SELECT id FROM permissions WHERE name = 'manage_streams')),
((SELECT id FROM roles WHERE name = 'employee'), (SELECT id FROM permissions WHERE name = 'upload_video'));

-- Service-specific roles and permissions for multi-service architecture
-- Video service roles
INSERT INTO service_roles (service_id, name, description) VALUES
((SELECT id FROM services WHERE slug = 'video'), 'admin', 'Video service administrator'),
((SELECT id FROM services WHERE slug = 'video'), 'manager', 'Video service manager'),
((SELECT id FROM services WHERE slug = 'video'), 'uploader', 'Can upload and manage own videos'),
((SELECT id FROM services WHERE slug = 'video'), 'viewer', 'Can view public videos');

-- Video service permissions
INSERT INTO service_permissions (service_id, name, description) VALUES
((SELECT id FROM services WHERE slug = 'video'), 'video:upload', 'Can upload videos'),
((SELECT id FROM services WHERE slug = 'video'), 'video:view_private', 'Can view private videos'),
((SELECT id FROM services WHERE slug = 'video'), 'video:manage_own', 'Can manage own videos'),
((SELECT id FROM services WHERE slug = 'video'), 'video:manage_all', 'Can manage all videos'),
((SELECT id FROM services WHERE slug = 'video'), 'video:stream', 'Can create live streams'),
((SELECT id FROM services WHERE slug = 'video'), 'video:moderate', 'Can moderate content'),
((SELECT id FROM services WHERE slug = 'video'), 'video:audit', 'Can view audit logs');

-- Assign video permissions to roles
INSERT INTO service_role_permissions (role_id, permission_id) VALUES
((SELECT sr.id FROM service_roles sr JOIN services s ON sr.service_id = s.id WHERE s.slug = 'video' AND sr.name = 'admin'), (SELECT sp.id FROM service_permissions sp JOIN services s ON sp.service_id = s.id WHERE s.slug = 'video' AND sp.name = 'video:upload')),
((SELECT sr.id FROM service_roles sr JOIN services s ON sr.service_id = s.id WHERE s.slug = 'video' AND sr.name = 'admin'), (SELECT sp.id FROM service_permissions sp JOIN services s ON sp.service_id = s.id WHERE s.slug = 'video' AND sp.name = 'video:view_private')),
((SELECT sr.id FROM service_roles sr JOIN services s ON sr.service_id = s.id WHERE s.slug = 'video' AND sr.name = 'admin'), (SELECT sp.id FROM service_permissions sp JOIN services s ON sp.service_id = s.id WHERE s.slug = 'video' AND sp.name = 'video:manage_all')),
((SELECT sr.id FROM service_roles sr JOIN services s ON sr.service_id = s.id WHERE s.slug = 'video' AND sr.name = 'admin'), (SELECT sp.id FROM service_permissions sp JOIN services s ON sp.service_id = s.id WHERE s.slug = 'video' AND sp.name = 'video:stream')),
((SELECT sr.id FROM service_roles sr JOIN services s ON sr.service_id = s.id WHERE s.slug = 'video' AND sr.name = 'admin'), (SELECT sp.id FROM service_permissions sp JOIN services s ON sp.service_id = s.id WHERE s.slug = 'video' AND sp.name = 'video:moderate')),
((SELECT sr.id FROM service_roles sr JOIN services s ON sr.service_id = s.id WHERE s.slug = 'video' AND sr.name = 'admin'), (SELECT sp.id FROM service_permissions sp JOIN services s ON sp.service_id = s.id WHERE s.slug = 'video' AND sp.name = 'video:audit')),
((SELECT sr.id FROM service_roles sr JOIN services s ON sr.service_id = s.id WHERE s.slug = 'video' AND sr.name = 'manager'), (SELECT sp.id FROM service_permissions sp JOIN services s ON sp.service_id = s.id WHERE s.slug = 'video' AND sp.name = 'video:upload')),
((SELECT sr.id FROM service_roles sr JOIN services s ON sr.service_id = s.id WHERE s.slug = 'video' AND sr.name = 'manager'), (SELECT sp.id FROM service_permissions sp JOIN services s ON sp.service_id = s.id WHERE s.slug = 'video' AND sp.name = 'video:view_private')),
((SELECT sr.id FROM service_roles sr JOIN services s ON sr.service_id = s.id WHERE s.slug = 'video' AND sr.name = 'manager'), (SELECT sp.id FROM service_permissions sp JOIN services s ON sp.service_id = s.id WHERE s.slug = 'video' AND sp.name = 'video:stream')),
((SELECT sr.id FROM service_roles sr JOIN services s ON sr.service_id = s.id WHERE s.slug = 'video' AND sr.name = 'uploader'), (SELECT sp.id FROM service_permissions sp JOIN services s ON sp.service_id = s.id WHERE s.slug = 'video' AND sp.name = 'video:upload')),
((SELECT sr.id FROM service_roles sr JOIN services s ON sr.service_id = s.id WHERE s.slug = 'video' AND sr.name = 'uploader'), (SELECT sp.id FROM service_permissions sp JOIN services s ON sp.service_id = s.id WHERE s.slug = 'video' AND sp.name = 'video:manage_own'));

-- Messenger service roles
INSERT INTO service_roles (service_id, name, description) VALUES
((SELECT id FROM services WHERE slug = 'messenger'), 'admin', 'Messenger administrator'),
((SELECT id FROM services WHERE slug = 'messenger'), 'moderator', 'Can moderate chats'),
((SELECT id FROM services WHERE slug = 'messenger'), 'user', 'Regular messenger user');

-- Messenger permissions
INSERT INTO service_permissions (service_id, name, description) VALUES
((SELECT id FROM services WHERE slug = 'messenger'), 'messenger:send', 'Can send messages'),
((SELECT id FROM services WHERE slug = 'messenger'), 'messenger:create_chat', 'Can create group chats'),
((SELECT id FROM services WHERE slug = 'messenger'), 'messenger:moderate', 'Can moderate messages'),
((SELECT id FROM services WHERE slug = 'messenger'), 'messenger:admin', 'Full messenger administration');

-- Dashboard service roles
INSERT INTO service_roles (service_id, name, description) VALUES
((SELECT id FROM services WHERE slug = 'dashboard'), 'admin', 'Dashboard administrator'),
((SELECT id FROM services WHERE slug = 'dashboard'), 'viewer', 'Can view dashboard data'),
((SELECT id FROM services WHERE slug = 'dashboard'), 'editor', 'Can edit dashboard configurations');

-- Dashboard permissions
INSERT INTO service_permissions (service_id, name, description) VALUES
((SELECT id FROM services WHERE slug = 'dashboard'), 'dashboard:view', 'Can view dashboard'),
((SELECT id FROM services WHERE slug = 'dashboard'), 'dashboard:edit', 'Can edit dashboard'),
((SELECT id FROM services WHERE slug = 'dashboard'), 'dashboard:admin', 'Full dashboard administration');

-- Support service roles
INSERT INTO service_roles (service_id, name, description) VALUES
((SELECT id FROM services WHERE slug = 'support'), 'admin', 'Support administrator'),
((SELECT id FROM services WHERE slug = 'support'), 'agent', 'Support agent'),
((SELECT id FROM services WHERE slug = 'support'), 'user', 'Can submit support tickets');

-- Support permissions
INSERT INTO service_permissions (service_id, name, description) VALUES
((SELECT id FROM services WHERE slug = 'support'), 'support:create_ticket', 'Can create support tickets'),
((SELECT id FROM services WHERE slug = 'support'), 'support:respond', 'Can respond to tickets'),
((SELECT id FROM services WHERE slug = 'support'), 'support:close', 'Can close tickets'),
((SELECT id FROM services WHERE slug = 'support'), 'support:admin', 'Full support administration');
