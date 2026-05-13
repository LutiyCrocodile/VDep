-- Fix: reset test passwords to admin123; grant video:stream to role "viewer" (video service).
-- Если psql показал UPDATE 0 — в этой базе нет пользователей с такими username (не тот инстанс БД
-- или не прогнан seed). Тогда выполните 005_bootstrap_video_users.sql или весь database/seed_data.sql.

UPDATE users SET password_hash = '$2b$12$ef3qJ1ml214zOLcjKEhYJ.H84nDLuNxDTwPUQ6rwvd4JfU.nmRZya'
WHERE username IN ('admin', 'video_admin', 'messenger_user', 'analyst', 'support_agent', 'employee', 'external');

INSERT INTO service_role_permissions (role_id, permission_id)
SELECT sr.id, sp.id
FROM service_roles sr
JOIN services s ON sr.service_id = s.id AND s.slug = 'video'
JOIN service_permissions sp ON sp.service_id = s.id AND sp.name = 'video:stream'
WHERE sr.name = 'viewer' AND sr.service_id = s.id
  AND NOT EXISTS (
    SELECT 1 FROM service_role_permissions rp
    WHERE rp.role_id = sr.id AND rp.permission_id = sp.id
  );

-- Диагностика (ожидается: хотя бы одна строка users с admin; для viewer — perms содержит video:stream)
-- SELECT count(*) AS users_named FROM users WHERE username IN ('admin', 'employee');
-- SELECT sr.id, sp.name FROM service_roles sr JOIN services s ON s.id = sr.service_id AND s.slug = 'video'
--   JOIN service_role_permissions srp ON srp.role_id = sr.id JOIN service_permissions sp ON sp.id = srp.permission_id
--   WHERE sr.name = 'viewer';
