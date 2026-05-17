-- Каналы для тестовых пользователей (если ещё нет). Пароль входа не меняется.
-- Запуск:
--   Get-Content -Raw "infrastructure\database\migrations\008_dev_channels.sql" | docker exec -i video_dgim_mos-db-1 psql -U user -d video_hosting

INSERT INTO channels (id, name, description, handle, owner_id, subscribers_count, is_verified, created_at, updated_at)
SELECT gen_random_uuid(), v.name, v.description, v.handle, u.id, 0, false, NOW(), NOW()
FROM (VALUES
  ('dev_viewer', 'Канал Dev Viewer', 'Тестовый канал', 'devviewer'),
  ('dev_uploader', 'Канал Dev Uploader', 'Тестовый канал загрузки', 'devuploader')
) AS v(username, name, description, handle)
JOIN users u ON u.username = v.username
WHERE NOT EXISTS (SELECT 1 FROM channels c WHERE c.owner_id = u.id);

SELECT u.username, c.handle, c.name
FROM users u
LEFT JOIN channels c ON c.owner_id = u.id
WHERE u.username LIKE 'dev_%'
ORDER BY u.username;
