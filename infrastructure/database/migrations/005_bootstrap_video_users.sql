-- Bootstrap: если 004 дал UPDATE 0 / INSERT 0 0 — в БД нет тестовых пользователей или не создан видеосервис.
-- Этот скрипт: создаёт сервис video, права, роли, связи RBAC, учётки admin и employee (пароль admin123),
-- назначает admin роль video/admin, employee — video/viewer (с video:stream у viewer).
-- Запуск из корня репозитория (PowerShell):
--   Get-Content -Raw "infrastructure\database\migrations\005_bootstrap_video_users.sql" | docker exec -i <db> env PGPASSWORD=password psql -U user -d video_hosting

-- bcrypt для пароля admin123 (совпадает с database/seed_data.sql)

-- 0) Старые БД без колонок под auth-service (иначе INSERT в users падает)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'is_employee'
  ) THEN
    ALTER TABLE users ADD COLUMN is_employee boolean NOT NULL DEFAULT true;
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'full_name'
  ) THEN
    ALTER TABLE users ADD COLUMN full_name varchar(255);
  END IF;
END $$;

-- 0.5) Глобальные роли (таблица roles) — обязательный FK users.role_id в старых схемах
INSERT INTO roles (id, name, description)
SELECT gen_random_uuid(), v.name, v.description
FROM (VALUES
  ('admin', 'Administrator with full access'),
  ('moderator', 'Content moderator'),
  ('user', 'Standard user'),
  ('guest', 'Guest user with limited access')
) AS v(name, description)
WHERE NOT EXISTS (SELECT 1 FROM roles r WHERE r.name = v.name);

-- 1) Сервис video
INSERT INTO services (id, slug, name, description, is_active)
SELECT gen_random_uuid(), 'video', 'Видеохостинг ДГИ', 'Система видеохостинга', true
WHERE NOT EXISTS (SELECT 1 FROM services WHERE slug = 'video');

-- 2) Права видеосервиса (как в auth-service initialize_services для video)
INSERT INTO service_permissions (id, service_id, name, description)
SELECT gen_random_uuid(), s.id, v.name, v.description
FROM services s
CROSS JOIN (VALUES
  ('video:upload', 'Can upload videos'),
  ('video:view_private', 'Can view private videos'),
  ('video:manage_own', 'Can manage own videos'),
  ('video:manage_all', 'Can manage all videos'),
  ('video:stream', 'Can create streams'),
  ('video:moderate', 'Can moderate content'),
  ('video:audit', 'Can audit')
) AS v(name, description)
WHERE s.slug = 'video'
  AND NOT EXISTS (
    SELECT 1 FROM service_permissions sp2
    WHERE sp2.service_id = s.id AND sp2.name = v.name
  );

-- 3) Роли видеосервиса
INSERT INTO service_roles (id, service_id, name, description, is_active)
SELECT gen_random_uuid(), s.id, r.name, r.description, true
FROM services s
CROSS JOIN (VALUES
  ('admin', 'Video admin'),
  ('manager', 'Video manager'),
  ('uploader', 'Can upload videos'),
  ('viewer', 'Can view videos')
) AS r(name, description)
WHERE s.slug = 'video'
  AND NOT EXISTS (
    SELECT 1 FROM service_roles sr2
    WHERE sr2.service_id = s.id AND sr2.name = r.name
  );

-- 4) Права на роли: admin — все права video; manager/uploader/viewer — как в коде auth
INSERT INTO service_role_permissions (role_id, permission_id)
SELECT sr.id, sp.id
FROM service_roles sr
JOIN services s ON s.id = sr.service_id AND s.slug = 'video'
JOIN service_permissions sp ON sp.service_id = s.id
WHERE sr.name = 'admin'
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO service_role_permissions (role_id, permission_id)
SELECT sr.id, sp.id
FROM service_roles sr
JOIN services s ON s.id = sr.service_id AND s.slug = 'video'
JOIN service_permissions sp ON sp.service_id = s.id AND sp.name IN ('video:upload', 'video:view_private', 'video:stream')
WHERE sr.name = 'manager'
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO service_role_permissions (role_id, permission_id)
SELECT sr.id, sp.id
FROM service_roles sr
JOIN services s ON s.id = sr.service_id AND s.slug = 'video'
JOIN service_permissions sp ON sp.service_id = s.id AND sp.name IN ('video:upload', 'video:manage_own')
WHERE sr.name = 'uploader'
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO service_role_permissions (role_id, permission_id)
SELECT sr.id, sp.id
FROM service_roles sr
JOIN services s ON s.id = sr.service_id AND s.slug = 'video'
JOIN service_permissions sp ON sp.service_id = s.id AND sp.name = 'video:stream'
WHERE sr.name = 'viewer'
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- 5) Учётные записи (UPSERT по username); role_id — глобальная роль из roles (NOT NULL в старых БД)
INSERT INTO users (id, username, email, password_hash, is_employee, is_active, role_id)
VALUES
  (gen_random_uuid(), 'admin', 'admin@dgi.mos.ru',
   '$2b$12$ef3qJ1ml214zOLcjKEhYJ.H84nDLuNxDTwPUQ6rwvd4JfU.nmRZya', true, true,
   (SELECT id FROM roles WHERE name = 'admin' ORDER BY id LIMIT 1)),
  (gen_random_uuid(), 'employee', 'employee@dgi.mos.ru',
   '$2b$12$ef3qJ1ml214zOLcjKEhYJ.H84nDLuNxDTwPUQ6rwvd4JfU.nmRZya', true, true,
   (SELECT id FROM roles WHERE name = 'user' ORDER BY id LIMIT 1))
ON CONFLICT (username) DO UPDATE SET
  password_hash = EXCLUDED.password_hash,
  is_active = EXCLUDED.is_active,
  is_employee = EXCLUDED.is_employee,
  role_id = EXCLUDED.role_id;

-- На случай отличия регистра логина; выставляем role_id и пароль
UPDATE users SET
  password_hash = '$2b$12$ef3qJ1ml214zOLcjKEhYJ.H84nDLuNxDTwPUQ6rwvd4JfU.nmRZya',
  role_id = (SELECT id FROM roles WHERE name = 'admin' ORDER BY id LIMIT 1)
WHERE lower(trim(username)) = 'admin';

UPDATE users SET
  password_hash = '$2b$12$ef3qJ1ml214zOLcjKEhYJ.H84nDLuNxDTwPUQ6rwvd4JfU.nmRZya',
  role_id = (SELECT id FROM roles WHERE name = 'user' ORDER BY id LIMIT 1)
WHERE lower(trim(username)) = 'employee';

-- 6) Привязка к видеосервису: admin — одна роль video/admin; employee — одна video/viewer (при дублях service_roles — min(id))
INSERT INTO user_service_roles (user_id, service_role_id, granted_by)
SELECT DISTINCT ON (u.id) u.id, sr.id, u.id
FROM users u
JOIN service_roles sr ON sr.name = 'admin'
JOIN services s ON s.id = sr.service_id AND s.slug = 'video'
WHERE u.username = 'admin'
ORDER BY u.id, sr.id
ON CONFLICT (user_id, service_role_id) DO NOTHING;

INSERT INTO user_service_roles (user_id, service_role_id, granted_by)
SELECT DISTINCT ON (u.id) u.id, sr.id, u.id
FROM users u
JOIN service_roles sr ON sr.name = 'viewer'
JOIN services s ON s.id = sr.service_id AND s.slug = 'video'
WHERE u.username = 'employee'
ORDER BY u.id, sr.id
ON CONFLICT (user_id, service_role_id) DO NOTHING;

-- Проверка (должны быть строки)
SELECT 'users' AS t, username, left(password_hash, 7) AS hash_prefix FROM users WHERE username IN ('admin', 'employee');
SELECT 'video rbac' AS t, u.username, sr.name AS video_role, array_agg(sp.name ORDER BY sp.name) AS perms
FROM users u
JOIN user_service_roles usr ON usr.user_id = u.id
JOIN service_roles sr ON sr.id = usr.service_role_id
JOIN services s ON s.id = sr.service_id AND s.slug = 'video'
LEFT JOIN service_role_permissions srp ON srp.role_id = sr.id
LEFT JOIN service_permissions sp ON sp.id = srp.permission_id
WHERE u.username IN ('admin', 'employee')
GROUP BY u.username, sr.name;
