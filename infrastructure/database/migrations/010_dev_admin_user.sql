-- Логин admin / admin123 (как dev_admin) для входа через портал
INSERT INTO roles (id, name, description)
SELECT gen_random_uuid(), 'admin', 'Administrator'
WHERE NOT EXISTS (SELECT 1 FROM roles WHERE name = 'admin');

INSERT INTO users (id, username, email, password_hash, is_employee, is_active, role_id, full_name)
VALUES (
  gen_random_uuid(),
  'admin',
  'admin@dgi.local',
  '$2b$12$ef3qJ1ml214zOLcjKEhYJ.H84nDLuNxDTwPUQ6rwvd4JfU.nmRZya',
  true,
  true,
  (SELECT id FROM roles WHERE name = 'admin' ORDER BY id LIMIT 1),
  'Admin'
)
ON CONFLICT (username) DO UPDATE SET
  password_hash = EXCLUDED.password_hash,
  is_active = true,
  is_employee = true;

INSERT INTO user_service_roles (user_id, service_role_id, granted_by)
SELECT u.id, sr.id, u.id
FROM users u
JOIN service_roles sr ON sr.name = 'admin'
JOIN services s ON s.id = sr.service_id AND s.slug = 'video'
WHERE u.username = 'admin'
ON CONFLICT (user_id, service_role_id) DO NOTHING;
