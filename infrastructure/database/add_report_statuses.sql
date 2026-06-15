-- Добавить статусы отчетов
INSERT INTO reports_app_reportstatus (name, description, created_at, updated_at) VALUES
('Черновик', 'Отчёт в черновике', NOW(), NOW()),
('На согласовании', 'Отчёт на согласовании', NOW(), NOW()),
('Согласован', 'Отчёт согласован', NOW(), NOW()),
('Отклонён', 'Отчёт отклонён', NOW(), NOW()),
('Опубликован', 'Отчёт опубликован', NOW(), NOW())
ON CONFLICT DO NOTHING;
