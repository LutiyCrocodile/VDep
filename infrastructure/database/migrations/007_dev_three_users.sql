-- Три тестовых пользователя для локальной разработки (пароль у всех: admin123)
-- Запуск (из корня репозитория, PowerShell):
--   Get-Content -Raw "infrastructure\database\migrations\007_dev_three_users.sql" | docker exec -i video_dgim_mos-db-1 psql -U user -d video_hosting

-- bcrypt hash для пароля admin123
-- $2b$12$ef3qJ1ml214zOLcjKEhYJ.H84nDLuNxDTwPUQ6rwvd4JfU.nmRZya

INSERT INTO roles (id, name, description)
SELECT gen_random_uuid(), v.name, v.description
FROM (VALUES
  ('admin', 'Administrator'),
  ('user', 'Standard user')
) AS v(name, description)
WHERE NOT EXISTS (SELECT 1 FROM roles r WHERE r.name = v.name);

INSERT INTO users (id, username, email, password_hash, is_employee, is_active, role_id, full_name)
VALUES
  (
    gen_random_uuid(),
    'dev_admin',
    'dev.admin@dgi.local',
    '$2b$12$ef3qJ1ml214zOLcjKEhYJ.H84nDLuNxDTwPUQ6rwvd4JfU.nmRZya',
    true,
    true,
    (SELECT id FROM roles WHERE name = 'admin' ORDER BY id LIMIT 1),
    'Dev Admin'
  ),
  (
    gen_random_uuid(),
    'dev_viewer',
    'moren280806@yandex.ru',
    '$2b$12$ef3qJ1ml214zOLcjKEhYJ.H84nDLuNxDTwPUQ6rwvd4JfU.nmRZya',
    true,
    true,
    (SELECT id FROM roles WHERE name = 'user' ORDER BY id LIMIT 1),
    'Dev Viewer'
  ),
  (
    gen_random_uuid(),
    'dev_uploader',
    'dev.uploader@dgi.local',
    '$2b$12$ef3qJ1ml214zOLcjKEhYJ.H84nDLuNxDTwPUQ6rwvd4JfU.nmRZya',
    true,
    true,
    (SELECT id FROM roles WHERE name = 'user' ORDER BY id LIMIT 1),
    'Dev Uploader'
  )
ON CONFLICT (username) DO UPDATE SET
  email = EXCLUDED.email,
  password_hash = EXCLUDED.password_hash,
  is_employee = EXCLUDED.is_employee,
  is_active = EXCLUDED.is_active,
  role_id = EXCLUDED.role_id,
  full_name = EXCLUDED.full_name;

-- Сервисные роли video
INSERT INTO user_service_roles (user_id, service_role_id, granted_by)
SELECT u.id, sr.id, u.id
FROM users u
JOIN service_roles sr ON sr.name = 'admin'
JOIN services s ON s.id = sr.service_id AND s.slug = 'video'
WHERE u.username = 'dev_admin'
ON CONFLICT (user_id, service_role_id) DO NOTHING;

INSERT INTO user_service_roles (user_id, service_role_id, granted_by)
SELECT u.id, sr.id, u.id
FROM users u
JOIN service_roles sr ON sr.name = 'viewer'
JOIN services s ON s.id = sr.service_id AND s.slug = 'video'
WHERE u.username = 'dev_viewer'
ON CONFLICT (user_id, service_role_id) DO NOTHING;

INSERT INTO user_service_roles (user_id, service_role_id, granted_by)
SELECT u.id, sr.id, u.id
FROM users u
JOIN service_roles sr ON sr.name = 'uploader'
JOIN services s ON s.id = sr.service_id AND s.slug = 'video'
WHERE u.username = 'dev_uploader'
ON CONFLICT (user_id, service_role_id) DO NOTHING;

-- Права video:stream у viewer (если ещё не назначено bootstrap/004)
INSERT INTO service_role_permissions (role_id, permission_id)
SELECT sr.id, sp.id
FROM service_roles sr
JOIN services s ON s.id = sr.service_id AND s.slug = 'video'
JOIN service_permissions sp ON sp.service_id = s.id AND sp.name = 'video:stream'
WHERE sr.name = 'viewer'
ON CONFLICT (role_id, permission_id) DO NOTHING;

SELECT u.username, u.email, u.is_employee, sr.name AS video_role
FROM users u
LEFT JOIN user_service_roles usr ON usr.user_id = u.id
LEFT JOIN service_roles sr ON sr.id = usr.service_role_id
LEFT JOIN services s ON s.id = sr.service_id AND s.slug = 'video'
WHERE u.username IN ('dev_admin', 'dev_viewer', 'dev_uploader')
ORDER BY u.username;
