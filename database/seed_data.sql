-- seed_data.sql
-- Test data for DGI Video Hosting Platform
-- Run: docker exec -i infrastructure-docker-db-1 psql -U user -d video_hosting < database/seed_data.sql

-- ============================================
-- 1. ROLES (Global)
-- ============================================
INSERT INTO roles (id, name, description) VALUES
  (gen_random_uuid(), 'admin', 'Administrator with full access'),
  (gen_random_uuid(), 'moderator', 'Content moderator'),
  (gen_random_uuid(), 'user', 'Standard user'),
  (gen_random_uuid(), 'guest', 'Guest user with limited access')
ON CONFLICT (name) DO NOTHING;

-- ============================================
-- 2. SERVICES
-- ============================================
INSERT INTO services (id, slug, name, description) VALUES
  (gen_random_uuid(), 'video', 'Видеохостинг ДГИ', 'Система видеохостинга'),
  (gen_random_uuid(), 'messenger', 'Мессенджер ДГИ', 'Корпоративный мессенджер'),
  (gen_random_uuid(), 'dashboard', 'Дашборд ДГИ', 'Аналитический дашборд'),
  (gen_random_uuid(), 'support', 'Техподдержка ДГИ', 'Система техподдержки')
ON CONFLICT (slug) DO NOTHING;

-- ============================================
-- 3. SERVICE ROLES
-- ============================================
-- Video Service Roles
INSERT INTO service_roles (id, service_id, name, description) SELECT gen_random_uuid(), s.id, 'admin', 'Video admin' FROM services s WHERE s.slug = 'video' ON CONFLICT DO NOTHING;
INSERT INTO service_roles (id, service_id, name, description) SELECT gen_random_uuid(), s.id, 'manager', 'Video manager' FROM services s WHERE s.slug = 'video' ON CONFLICT DO NOTHING;
INSERT INTO service_roles (id, service_id, name, description) SELECT gen_random_uuid(), s.id, 'uploader', 'Can upload videos' FROM services s WHERE s.slug = 'video' ON CONFLICT DO NOTHING;
INSERT INTO service_roles (id, service_id, name, description) SELECT gen_random_uuid(), s.id, 'viewer', 'Can view videos' FROM services s WHERE s.slug = 'video' ON CONFLICT DO NOTHING;

-- Messenger Service Roles
INSERT INTO service_roles (id, service_id, name, description) SELECT gen_random_uuid(), s.id, 'admin', 'Messenger admin' FROM services s WHERE s.slug = 'messenger' ON CONFLICT DO NOTHING;
INSERT INTO service_roles (id, service_id, name, description) SELECT gen_random_uuid(), s.id, 'user', 'Messenger user' FROM services s WHERE s.slug = 'messenger' ON CONFLICT DO NOTHING;

-- Dashboard Service Roles
INSERT INTO service_roles (id, service_id, name, description) SELECT gen_random_uuid(), s.id, 'admin', 'Dashboard admin' FROM services s WHERE s.slug = 'dashboard' ON CONFLICT DO NOTHING;
INSERT INTO service_roles (id, service_id, name, description) SELECT gen_random_uuid(), s.id, 'analyst', 'Analyst' FROM services s WHERE s.slug = 'dashboard' ON CONFLICT DO NOTHING;
INSERT INTO service_roles (id, service_id, name, description) SELECT gen_random_uuid(), s.id, 'viewer', 'Dashboard viewer' FROM services s WHERE s.slug = 'dashboard' ON CONFLICT DO NOTHING;

-- Support Service Roles
INSERT INTO service_roles (id, service_id, name, description) SELECT gen_random_uuid(), s.id, 'admin', 'Support admin' FROM services s WHERE s.slug = 'support' ON CONFLICT DO NOTHING;
INSERT INTO service_roles (id, service_id, name, description) SELECT gen_random_uuid(), s.id, 'agent', 'Support agent' FROM services s WHERE s.slug = 'support' ON CONFLICT DO NOTHING;
INSERT INTO service_roles (id, service_id, name, description) SELECT gen_random_uuid(), s.id, 'user', 'Support user' FROM services s WHERE s.slug = 'support' ON CONFLICT DO NOTHING;

-- ============================================
-- 4. SERVICE PERMISSIONS
-- ============================================
-- Video Permissions
INSERT INTO service_permissions (id, service_id, name, description) SELECT gen_random_uuid(), s.id, 'video:upload', 'Can upload videos' FROM services s WHERE s.slug = 'video' ON CONFLICT DO NOTHING;
INSERT INTO service_permissions (id, service_id, name, description) SELECT gen_random_uuid(), s.id, 'video:view_private', 'Can view private videos' FROM services s WHERE s.slug = 'video' ON CONFLICT DO NOTHING;
INSERT INTO service_permissions (id, service_id, name, description) SELECT gen_random_uuid(), s.id, 'video:manage_own', 'Can manage own videos' FROM services s WHERE s.slug = 'video' ON CONFLICT DO NOTHING;
INSERT INTO service_permissions (id, service_id, name, description) SELECT gen_random_uuid(), s.id, 'video:manage_all', 'Can manage all videos' FROM services s WHERE s.slug = 'video' ON CONFLICT DO NOTHING;
INSERT INTO service_permissions (id, service_id, name, description) SELECT gen_random_uuid(), s.id, 'video:stream', 'Can create streams' FROM services s WHERE s.slug = 'video' ON CONFLICT DO NOTHING;
INSERT INTO service_permissions (id, service_id, name, description) SELECT gen_random_uuid(), s.id, 'video:moderate', 'Can moderate content' FROM services s WHERE s.slug = 'video' ON CONFLICT DO NOTHING;

-- Messenger Permissions
INSERT INTO service_permissions (id, service_id, name, description) SELECT gen_random_uuid(), s.id, 'messenger:send', 'Can send messages' FROM services s WHERE s.slug = 'messenger' ON CONFLICT DO NOTHING;
INSERT INTO service_permissions (id, service_id, name, description) SELECT gen_random_uuid(), s.id, 'messenger:read', 'Can read messages' FROM services s WHERE s.slug = 'messenger' ON CONFLICT DO NOTHING;
INSERT INTO service_permissions (id, service_id, name, description) SELECT gen_random_uuid(), s.id, 'messenger:create_group', 'Can create groups' FROM services s WHERE s.slug = 'messenger' ON CONFLICT DO NOTHING;

-- Dashboard Permissions
INSERT INTO service_permissions (id, service_id, name, description) SELECT gen_random_uuid(), s.id, 'dashboard:view_all', 'Can view all metrics' FROM services s WHERE s.slug = 'dashboard' ON CONFLICT DO NOTHING;
INSERT INTO service_permissions (id, service_id, name, description) SELECT gen_random_uuid(), s.id, 'dashboard:view_own', 'Can view own metrics' FROM services s WHERE s.slug = 'dashboard' ON CONFLICT DO NOTHING;
INSERT INTO service_permissions (id, service_id, name, description) SELECT gen_random_uuid(), s.id, 'dashboard:export', 'Can export reports' FROM services s WHERE s.slug = 'dashboard' ON CONFLICT DO NOTHING;

-- Support Permissions
INSERT INTO service_permissions (id, service_id, name, description) SELECT gen_random_uuid(), s.id, 'support:create_ticket', 'Can create tickets' FROM services s WHERE s.slug = 'support' ON CONFLICT DO NOTHING;
INSERT INTO service_permissions (id, service_id, name, description) SELECT gen_random_uuid(), s.id, 'support:view_own', 'Can view own tickets' FROM services s WHERE s.slug = 'support' ON CONFLICT DO NOTHING;
INSERT INTO service_permissions (id, service_id, name, description) SELECT gen_random_uuid(), s.id, 'support:view_all', 'Can view all tickets' FROM services s WHERE s.slug = 'support' ON CONFLICT DO NOTHING;

-- ============================================
-- 5. TEST USERS
-- ============================================
-- Passwords: bcrypt for "admin123" (regenerate: docker run --rm -v ./scripts:/scripts python:3.11-slim bash -c "pip install -q bcrypt && python /scripts/gen_bcrypt.py")
-- Admin user (full access to all services)
INSERT INTO users (id, username, email, password_hash, is_employee, is_active) VALUES
  (gen_random_uuid(), 'admin', 'admin@dgi.mos.ru',
   '$2b$12$ef3qJ1ml214zOLcjKEhYJ.H84nDLuNxDTwPUQ6rwvd4JfU.nmRZya',
   true, true)
ON CONFLICT (username) DO NOTHING;

-- Video Admin
INSERT INTO users (id, username, email, password_hash, is_employee, is_active) VALUES
  (gen_random_uuid(), 'video_admin', 'video.admin@dgi.mos.ru',
   '$2b$12$ef3qJ1ml214zOLcjKEhYJ.H84nDLuNxDTwPUQ6rwvd4JfU.nmRZya',
   true, true)
ON CONFLICT (username) DO NOTHING;

-- Messenger User
INSERT INTO users (id, username, email, password_hash, is_employee, is_active) VALUES
  (gen_random_uuid(), 'messenger_user', 'messenger.user@dgi.mos.ru',
   '$2b$12$ef3qJ1ml214zOLcjKEhYJ.H84nDLuNxDTwPUQ6rwvd4JfU.nmRZya',
   true, true)
ON CONFLICT (username) DO NOTHING;

-- Dashboard Analyst
INSERT INTO users (id, username, email, password_hash, is_employee, is_active) VALUES
  (gen_random_uuid(), 'analyst', 'analyst@dgi.mos.ru',
   '$2b$12$ef3qJ1ml214zOLcjKEhYJ.H84nDLuNxDTwPUQ6rwvd4JfU.nmRZya',
   true, true)
ON CONFLICT (username) DO NOTHING;

-- Support Agent
INSERT INTO users (id, username, email, password_hash, is_employee, is_active) VALUES
  (gen_random_uuid(), 'support_agent', 'support@dgi.mos.ru',
   '$2b$12$ef3qJ1ml214zOLcjKEhYJ.H84nDLuNxDTwPUQ6rwvd4JfU.nmRZya',
   true, true)
ON CONFLICT (username) DO NOTHING;

-- Standard employee
INSERT INTO users (id, username, email, password_hash, is_employee, is_active) VALUES
  (gen_random_uuid(), 'employee', 'employee@dgi.mos.ru',
   '$2b$12$ef3qJ1ml214zOLcjKEhYJ.H84nDLuNxDTwPUQ6rwvd4JfU.nmRZya',
   true, true)
ON CONFLICT (username) DO NOTHING;

-- External user (non-employee, limited access)
INSERT INTO users (id, username, email, password_hash, is_employee, is_active) VALUES
  (gen_random_uuid(), 'external', 'external@example.com',
   '$2b$12$ef3qJ1ml214zOLcjKEhYJ.H84nDLuNxDTwPUQ6rwvd4JfU.nmRZya',
   false, true)
ON CONFLICT (username) DO NOTHING;

-- Сброс пароля тестовых пользователей на admin123 (если строки уже были без пароля или со старым хешем)
UPDATE users SET password_hash = '$2b$12$ef3qJ1ml214zOLcjKEhYJ.H84nDLuNxDTwPUQ6rwvd4JfU.nmRZya'
WHERE username IN ('admin', 'video_admin', 'messenger_user', 'analyst', 'support_agent', 'employee', 'external');

-- ============================================
-- 6. USER SERVICE ROLES (Assign permissions)
-- ============================================
-- Helper: Get role IDs
DO $$ 
DECLARE
    admin_role_id UUID;
    video_admin_role_id UUID;
    video_viewer_role_id UUID;
    messenger_user_role_id UUID;
    dashboard_analyst_role_id UUID;
    dashboard_viewer_role_id UUID;
    support_agent_role_id UUID;
    support_user_role_id UUID;
    
    video_service_id UUID;
    messenger_service_id UUID;
    dashboard_service_id UUID;
    support_service_id UUID;
    
    admin_user_id UUID;
    video_admin_user_id UUID;
    messenger_user_user_id UUID;
    analyst_user_id UUID;
    support_agent_user_id UUID;
    employee_user_id UUID;
BEGIN
    -- Get service IDs
    SELECT id INTO video_service_id FROM services WHERE slug = 'video';
    SELECT id INTO messenger_service_id FROM services WHERE slug = 'messenger';
    SELECT id INTO dashboard_service_id FROM services WHERE slug = 'dashboard';
    SELECT id INTO support_service_id FROM services WHERE slug = 'support';
    
    -- Get global admin role
    SELECT id INTO admin_role_id FROM roles WHERE name = 'admin';
    
    -- Get service role IDs
    SELECT id INTO video_admin_role_id FROM service_roles WHERE service_id = video_service_id AND name = 'admin';
    SELECT id INTO video_viewer_role_id FROM service_roles WHERE service_id = video_service_id AND name = 'viewer';
    SELECT id INTO messenger_user_role_id FROM service_roles WHERE service_id = messenger_service_id AND name = 'user';
    SELECT id INTO dashboard_analyst_role_id FROM service_roles WHERE service_id = dashboard_service_id AND name = 'analyst';
    SELECT id INTO dashboard_viewer_role_id FROM service_roles WHERE service_id = dashboard_service_id AND name = 'viewer';
    SELECT id INTO support_agent_role_id FROM service_roles WHERE service_id = support_service_id AND name = 'agent';
    SELECT id INTO support_user_role_id FROM service_roles WHERE service_id = support_service_id AND name = 'user';
    
    -- Get user IDs
    SELECT id INTO admin_user_id FROM users WHERE username = 'admin';
    SELECT id INTO video_admin_user_id FROM users WHERE username = 'video_admin';
    SELECT id INTO messenger_user_user_id FROM users WHERE username = 'messenger_user';
    SELECT id INTO analyst_user_id FROM users WHERE username = 'analyst';
    SELECT id INTO support_agent_user_id FROM users WHERE username = 'support_agent';
    SELECT id INTO employee_user_id FROM users WHERE username = 'employee';
    
    -- Assign admin role to admin user (global admin gets access to all)
    INSERT INTO user_service_roles (user_id, service_role_id, granted_by)
    VALUES (admin_user_id, video_admin_role_id, admin_user_id)
    ON CONFLICT DO NOTHING;
    
    INSERT INTO user_service_roles (user_id, service_role_id, granted_by)
    VALUES (admin_user_id, messenger_user_role_id, admin_user_id)
    ON CONFLICT DO NOTHING;
    
    INSERT INTO user_service_roles (user_id, service_role_id, granted_by)
    VALUES (admin_user_id, dashboard_analyst_role_id, admin_user_id)
    ON CONFLICT DO NOTHING;
    
    INSERT INTO user_service_roles (user_id, service_role_id, granted_by)
    VALUES (admin_user_id, support_agent_role_id, admin_user_id)
    ON CONFLICT DO NOTHING;
    
    -- Video admin gets video admin role
    INSERT INTO user_service_roles (user_id, service_role_id, granted_by)
    VALUES (video_admin_user_id, video_admin_role_id, admin_user_id)
    ON CONFLICT DO NOTHING;
    
    -- Messenger user gets messenger user role
    INSERT INTO user_service_roles (user_id, service_role_id, granted_by)
    VALUES (messenger_user_user_id, messenger_user_role_id, admin_user_id)
    ON CONFLICT DO NOTHING;
    
    -- Analyst gets dashboard analyst role
    INSERT INTO user_service_roles (user_id, service_role_id, granted_by)
    VALUES (analyst_user_id, dashboard_analyst_role_id, admin_user_id)
    ON CONFLICT DO NOTHING;
    
    -- Support agent gets support agent role
    INSERT INTO user_service_roles (user_id, service_role_id, granted_by)
    VALUES (support_agent_user_id, support_agent_role_id, admin_user_id)
    ON CONFLICT DO NOTHING;
    
    -- Standard employee gets viewer access to video and dashboard
    INSERT INTO user_service_roles (user_id, service_role_id, granted_by)
    VALUES (employee_user_id, video_viewer_role_id, admin_user_id)
    ON CONFLICT DO NOTHING;
    
    INSERT INTO user_service_roles (user_id, service_role_id, granted_by)
    VALUES (employee_user_id, dashboard_viewer_role_id, admin_user_id)
    ON CONFLICT DO NOTHING;
    
    INSERT INTO user_service_roles (user_id, service_role_id, granted_by)
    VALUES (employee_user_id, support_user_role_id, admin_user_id)
    ON CONFLICT DO NOTHING;
    
    RAISE NOTICE 'Test users and roles created successfully';
END $$;

-- ============================================
-- 7. VERIFY DATA
-- ============================================
SELECT 'Users created:' as info;
SELECT username, email, is_employee FROM users;

SELECT 'Service roles assigned:' as info;
SELECT u.username, s.slug as service, sr.name as role
FROM user_service_roles usr
JOIN users u ON usr.user_id = u.id
JOIN service_roles sr ON usr.service_role_id = sr.id
JOIN services s ON sr.service_id = s.id
ORDER BY u.username, s.slug;
