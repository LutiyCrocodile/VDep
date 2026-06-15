-- Dev users for testing all roles (video + messenger).
-- Password for all users below: admin123
-- bcrypt hash from existing dev migrations:
--   $2b$12$ef3qJ1ml214zOLcjKEhYJ.H84nDLuNxDTwPUQ6rwvd4JfU.nmRZya

-- 0) Ensure global roles exist (roles table used by users.role_id)
INSERT INTO roles (id, name, description)
SELECT gen_random_uuid(), v.name, v.description
FROM (VALUES
  ('admin', 'Administrator'),
  ('moderator', 'Moderator'),
  ('user', 'Standard user'),
  ('guest', 'Guest')
) AS v(name, description)
WHERE NOT EXISTS (SELECT 1 FROM roles r WHERE r.name = v.name);

-- 1) Ensure services exist
INSERT INTO services (id, slug, name, description, is_active)
SELECT gen_random_uuid(), v.slug, v.name, v.description, true
FROM (VALUES
  ('video', 'Видеохостинг ДГИ', 'Система видеохостинга'),
  ('messenger', 'Мессенджер ДГИ', 'Корпоративный мессенджер'),
  ('dashboard', 'Дашборд ДГИ', 'Аналитический дашборд'),
  ('support', 'Техподдержка ДГИ', 'Система техподдержки')
) AS v(slug, name, description)
WHERE NOT EXISTS (SELECT 1 FROM services s WHERE s.slug = v.slug);

-- 2) Ensure service permissions exist (video)
INSERT INTO service_permissions (id, service_id, name, description)
SELECT gen_random_uuid(), s.id, v.name, v.description
FROM services s
CROSS JOIN (VALUES
  ('video:upload', 'Can upload videos'),
  ('video:view_private', 'Can view private videos'),
  ('video:manage_own', 'Can manage own videos'),
  ('video:manage_all', 'Can manage all videos'),
  ('video:stream', 'Can create live streams'),
  ('video:moderate', 'Can moderate content'),
  ('video:audit', 'Can view audit logs')
) AS v(name, description)
WHERE s.slug = 'video'
  AND NOT EXISTS (
    SELECT 1 FROM service_permissions sp
    WHERE sp.service_id = s.id AND sp.name = v.name
  );

-- 3) Ensure service roles exist (video)
INSERT INTO service_roles (id, service_id, name, description, is_active)
SELECT gen_random_uuid(), s.id, r.name, r.description, true
FROM services s
CROSS JOIN (VALUES
  ('admin', 'Video service administrator'),
  ('manager', 'Video service manager'),
  ('uploader', 'Can upload and manage own videos'),
  ('viewer', 'Can view public videos')
) AS r(name, description)
WHERE s.slug = 'video'
  AND NOT EXISTS (
    SELECT 1 FROM service_roles sr
    WHERE sr.service_id = s.id AND sr.name = r.name
  );

-- 4) Ensure service role-permissions mapping exists (video) — matches auth-service initialize_services
-- admin -> all video perms
INSERT INTO service_role_permissions (role_id, permission_id)
SELECT sr.id, sp.id
FROM service_roles sr
JOIN services s ON s.id = sr.service_id AND s.slug = 'video'
JOIN service_permissions sp ON sp.service_id = s.id
WHERE sr.name = 'admin'
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- manager -> upload, view_private, stream
INSERT INTO service_role_permissions (role_id, permission_id)
SELECT sr.id, sp.id
FROM service_roles sr
JOIN services s ON s.id = sr.service_id AND s.slug = 'video'
JOIN service_permissions sp ON sp.service_id = s.id AND sp.name IN ('video:upload', 'video:view_private', 'video:stream')
WHERE sr.name = 'manager'
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- uploader -> upload, manage_own
INSERT INTO service_role_permissions (role_id, permission_id)
SELECT sr.id, sp.id
FROM service_roles sr
JOIN services s ON s.id = sr.service_id AND s.slug = 'video'
JOIN service_permissions sp ON sp.service_id = s.id AND sp.name IN ('video:upload', 'video:manage_own')
WHERE sr.name = 'uploader'
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- viewer -> stream
INSERT INTO service_role_permissions (role_id, permission_id)
SELECT sr.id, sp.id
FROM service_roles sr
JOIN services s ON s.id = sr.service_id AND s.slug = 'video'
JOIN service_permissions sp ON sp.service_id = s.id AND sp.name = 'video:stream'
WHERE sr.name = 'viewer'
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- 5) Ensure service permissions exist (messenger)
INSERT INTO service_permissions (id, service_id, name, description)
SELECT gen_random_uuid(), s.id, v.name, v.description
FROM services s
CROSS JOIN (VALUES
  ('messenger:send', 'Can send messages'),
  ('messenger:create_chat', 'Can create group chats'),
  ('messenger:moderate', 'Can moderate messages'),
  ('messenger:admin', 'Full messenger administration')
) AS v(name, description)
WHERE s.slug = 'messenger'
  AND NOT EXISTS (
    SELECT 1 FROM service_permissions sp
    WHERE sp.service_id = s.id AND sp.name = v.name
  );

-- 6) Ensure service roles exist (messenger)
INSERT INTO service_roles (id, service_id, name, description, is_active)
SELECT gen_random_uuid(), s.id, r.name, r.description, true
FROM services s
CROSS JOIN (VALUES
  ('admin', 'Messenger administrator'),
  ('moderator', 'Can moderate chats'),
  ('user', 'Regular messenger user')
) AS r(name, description)
WHERE s.slug = 'messenger'
  AND NOT EXISTS (
    SELECT 1 FROM service_roles sr
    WHERE sr.service_id = s.id AND sr.name = r.name
  );

-- 7) Ensure service role-permissions mapping exists (messenger) — matches auth-service initialize_services
-- admin -> all perms
INSERT INTO service_role_permissions (role_id, permission_id)
SELECT sr.id, sp.id
FROM service_roles sr
JOIN services s ON s.id = sr.service_id AND s.slug = 'messenger'
JOIN service_permissions sp ON sp.service_id = s.id
WHERE sr.name = 'admin'
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- moderator -> send, create_chat, moderate
INSERT INTO service_role_permissions (role_id, permission_id)
SELECT sr.id, sp.id
FROM service_roles sr
JOIN services s ON s.id = sr.service_id AND s.slug = 'messenger'
JOIN service_permissions sp ON sp.service_id = s.id AND sp.name IN ('messenger:send', 'messenger:create_chat', 'messenger:moderate')
WHERE sr.name = 'moderator'
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- user -> send
INSERT INTO service_role_permissions (role_id, permission_id)
SELECT sr.id, sp.id
FROM service_roles sr
JOIN services s ON s.id = sr.service_id AND s.slug = 'messenger'
JOIN service_permissions sp ON sp.service_id = s.id AND sp.name = 'messenger:send'
WHERE sr.name = 'user'
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- 7b) Ensure service permissions exist (dashboard)
INSERT INTO service_permissions (id, service_id, name, description)
SELECT gen_random_uuid(), s.id, v.name, v.description
FROM services s
CROSS JOIN (VALUES
  ('dashboard:view', 'Can view dashboard'),
  ('dashboard:edit', 'Can edit dashboard'),
  ('dashboard:admin', 'Full dashboard administration')
) AS v(name, description)
WHERE s.slug = 'dashboard'
  AND NOT EXISTS (
    SELECT 1 FROM service_permissions sp
    WHERE sp.service_id = s.id AND sp.name = v.name
  );

-- 7c) Ensure service roles exist (dashboard)
INSERT INTO service_roles (id, service_id, name, description, is_active)
SELECT gen_random_uuid(), s.id, r.name, r.description, true
FROM services s
CROSS JOIN (VALUES
  ('admin', 'Dashboard administrator'),
  ('viewer', 'Can view dashboard data'),
  ('editor', 'Can edit dashboard configurations')
) AS r(name, description)
WHERE s.slug = 'dashboard'
  AND NOT EXISTS (
    SELECT 1 FROM service_roles sr
    WHERE sr.service_id = s.id AND sr.name = r.name
  );

-- 7d) Ensure service role-permissions mapping exists (dashboard)
-- admin -> all perms
INSERT INTO service_role_permissions (role_id, permission_id)
SELECT sr.id, sp.id
FROM service_roles sr
JOIN services s ON s.id = sr.service_id AND s.slug = 'dashboard'
JOIN service_permissions sp ON sp.service_id = s.id
WHERE sr.name = 'admin'
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- editor -> view, edit
INSERT INTO service_role_permissions (role_id, permission_id)
SELECT sr.id, sp.id
FROM service_roles sr
JOIN services s ON s.id = sr.service_id AND s.slug = 'dashboard'
JOIN service_permissions sp ON sp.service_id = s.id AND sp.name IN ('dashboard:view', 'dashboard:edit')
WHERE sr.name = 'editor'
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- viewer -> view
INSERT INTO service_role_permissions (role_id, permission_id)
SELECT sr.id, sp.id
FROM service_roles sr
JOIN services s ON s.id = sr.service_id AND s.slug = 'dashboard'
JOIN service_permissions sp ON sp.service_id = s.id AND sp.name = 'dashboard:view'
WHERE sr.name = 'viewer'
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- 7e) Ensure service permissions exist (support)
INSERT INTO service_permissions (id, service_id, name, description)
SELECT gen_random_uuid(), s.id, v.name, v.description
FROM services s
CROSS JOIN (VALUES
  ('support:create_ticket', 'Can create support tickets'),
  ('support:respond', 'Can respond to tickets'),
  ('support:close', 'Can close tickets'),
  ('support:admin', 'Full support administration')
) AS v(name, description)
WHERE s.slug = 'support'
  AND NOT EXISTS (
    SELECT 1 FROM service_permissions sp
    WHERE sp.service_id = s.id AND sp.name = v.name
  );

-- 7f) Ensure service roles exist (support)
INSERT INTO service_roles (id, service_id, name, description, is_active)
SELECT gen_random_uuid(), s.id, r.name, r.description, true
FROM services s
CROSS JOIN (VALUES
  ('admin', 'Support administrator'),
  ('agent', 'Support agent'),
  ('user', 'Can submit support tickets')
) AS r(name, description)
WHERE s.slug = 'support'
  AND NOT EXISTS (
    SELECT 1 FROM service_roles sr
    WHERE sr.service_id = s.id AND sr.name = r.name
  );

-- 7g) Ensure service role-permissions mapping exists (support)
-- admin -> all perms
INSERT INTO service_role_permissions (role_id, permission_id)
SELECT sr.id, sp.id
FROM service_roles sr
JOIN services s ON s.id = sr.service_id AND s.slug = 'support'
JOIN service_permissions sp ON sp.service_id = s.id
WHERE sr.name = 'admin'
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- agent -> create, respond, close
INSERT INTO service_role_permissions (role_id, permission_id)
SELECT sr.id, sp.id
FROM service_roles sr
JOIN services s ON s.id = sr.service_id AND s.slug = 'support'
JOIN service_permissions sp ON sp.service_id = s.id AND sp.name IN ('support:create_ticket', 'support:respond', 'support:close')
WHERE sr.name = 'agent'
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- user -> create
INSERT INTO service_role_permissions (role_id, permission_id)
SELECT sr.id, sp.id
FROM service_roles sr
JOIN services s ON s.id = sr.service_id AND s.slug = 'support'
JOIN service_permissions sp ON sp.service_id = s.id AND sp.name = 'support:create_ticket'
WHERE sr.name = 'user'
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- 8) Create dev users (UPSERT by username)
INSERT INTO users (id, username, email, password_hash, is_employee, is_active, role_id, full_name)
VALUES
  (gen_random_uuid(), 'video_admin', 'video.admin@dgi.local',
   '$2b$12$ef3qJ1ml214zOLcjKEhYJ.H84nDLuNxDTwPUQ6rwvd4JfU.nmRZya', true, true,
   (SELECT id FROM roles WHERE name = 'admin' ORDER BY id LIMIT 1), 'Video Admin'),
  (gen_random_uuid(), 'video_manager', 'video.manager@dgi.local',
   '$2b$12$ef3qJ1ml214zOLcjKEhYJ.H84nDLuNxDTwPUQ6rwvd4JfU.nmRZya', true, true,
   (SELECT id FROM roles WHERE name = 'user' ORDER BY id LIMIT 1), 'Video Manager'),
  (gen_random_uuid(), 'video_uploader', 'video.uploader@dgi.local',
   '$2b$12$ef3qJ1ml214zOLcjKEhYJ.H84nDLuNxDTwPUQ6rwvd4JfU.nmRZya', true, true,
   (SELECT id FROM roles WHERE name = 'user' ORDER BY id LIMIT 1), 'Video Uploader'),
  (gen_random_uuid(), 'video_viewer', 'video.viewer@dgi.local',
   '$2b$12$ef3qJ1ml214zOLcjKEhYJ.H84nDLuNxDTwPUQ6rwvd4JfU.nmRZya', true, true,
   (SELECT id FROM roles WHERE name = 'user' ORDER BY id LIMIT 1), 'Video Viewer'),

  (gen_random_uuid(), 'messenger_admin', 'messenger.admin@dgi.local',
   '$2b$12$ef3qJ1ml214zOLcjKEhYJ.H84nDLuNxDTwPUQ6rwvd4JfU.nmRZya', true, true,
   (SELECT id FROM roles WHERE name = 'admin' ORDER BY id LIMIT 1), 'Messenger Admin'),
  (gen_random_uuid(), 'messenger_moderator', 'messenger.moderator@dgi.local',
   '$2b$12$ef3qJ1ml214zOLcjKEhYJ.H84nDLuNxDTwPUQ6rwvd4JfU.nmRZya', true, true,
   (SELECT id FROM roles WHERE name = 'moderator' ORDER BY id LIMIT 1), 'Messenger Moderator'),
  (gen_random_uuid(), 'messenger_user', 'messenger.user@dgi.local',
   '$2b$12$ef3qJ1ml214zOLcjKEhYJ.H84nDLuNxDTwPUQ6rwvd4JfU.nmRZya', true, true,
   (SELECT id FROM roles WHERE name = 'user' ORDER BY id LIMIT 1), 'Messenger User')
ON CONFLICT (username) DO UPDATE SET
  email = EXCLUDED.email,
  password_hash = EXCLUDED.password_hash,
  is_employee = EXCLUDED.is_employee,
  is_active = EXCLUDED.is_active,
  role_id = EXCLUDED.role_id,
  full_name = EXCLUDED.full_name;

-- 9) Assign service roles
-- Video
INSERT INTO user_service_roles (user_id, service_role_id, granted_by)
SELECT u.id, sr.id, u.id
FROM users u
JOIN services s ON s.slug = 'video'
JOIN service_roles sr ON sr.service_id = s.id AND sr.name = 'admin'
WHERE u.username = 'video_admin'
ON CONFLICT (user_id, service_role_id) DO NOTHING;

INSERT INTO user_service_roles (user_id, service_role_id, granted_by)
SELECT u.id, sr.id, u.id
FROM users u
JOIN services s ON s.slug = 'video'
JOIN service_roles sr ON sr.service_id = s.id AND sr.name = 'manager'
WHERE u.username = 'video_manager'
ON CONFLICT (user_id, service_role_id) DO NOTHING;

INSERT INTO user_service_roles (user_id, service_role_id, granted_by)
SELECT u.id, sr.id, u.id
FROM users u
JOIN services s ON s.slug = 'video'
JOIN service_roles sr ON sr.service_id = s.id AND sr.name = 'uploader'
WHERE u.username = 'video_uploader'
ON CONFLICT (user_id, service_role_id) DO NOTHING;

INSERT INTO user_service_roles (user_id, service_role_id, granted_by)
SELECT u.id, sr.id, u.id
FROM users u
JOIN services s ON s.slug = 'video'
JOIN service_roles sr ON sr.service_id = s.id AND sr.name = 'viewer'
WHERE u.username = 'video_viewer'
ON CONFLICT (user_id, service_role_id) DO NOTHING;

-- Messenger
INSERT INTO user_service_roles (user_id, service_role_id, granted_by)
SELECT u.id, sr.id, u.id
FROM users u
JOIN services s ON s.slug = 'messenger'
JOIN service_roles sr ON sr.service_id = s.id AND sr.name = 'admin'
WHERE u.username = 'messenger_admin'
ON CONFLICT (user_id, service_role_id) DO NOTHING;

INSERT INTO user_service_roles (user_id, service_role_id, granted_by)
SELECT u.id, sr.id, u.id
FROM users u
JOIN services s ON s.slug = 'messenger'
JOIN service_roles sr ON sr.service_id = s.id AND sr.name = 'moderator'
WHERE u.username = 'messenger_moderator'
ON CONFLICT (user_id, service_role_id) DO NOTHING;

INSERT INTO user_service_roles (user_id, service_role_id, granted_by)
SELECT u.id, sr.id, u.id
FROM users u
JOIN services s ON s.slug = 'messenger'
JOIN service_roles sr ON sr.service_id = s.id AND sr.name = 'user'
WHERE u.username = 'messenger_user'
ON CONFLICT (user_id, service_role_id) DO NOTHING;

