-- Seed data for support tickets
-- Users:
-- 1b907610-f900-479b-92e1-4bcad8042901 | EvteevAS | Евтеев Артем Сергеевич | admin
-- 749b46df-6450-4d6c-aee8-45f755314430 | ZaycES   | Зайцева Елена Сергеевна | user
-- d9247e78-b285-48a8-9cec-e73e8e370afd | MaksTA   | Трошин Максим Андреевич | engineer
-- fca16fce-173b-4faa-b35c-dea91cf5e0fa | MahAD    | Махмудова Аминат Долгатовна | user

-- High priority tickets
INSERT INTO support.tickets (title, description, status, priority, created_by_id, assigned_to_id, created_at, updated_at) VALUES
('Не работает принтер в кабинете 12.23', 'Принтер HP LaserJet не печатает, горит красный индикатор ошибки. Перезагрузка не помогла.', 'open', 'high', '749b46df-6450-4d6c-aee8-45f755314430', 'd9247e78-b285-48a8-9cec-e73e8e370afd', NOW() - INTERVAL '2 days', NOW() - INTERVAL '2 days'),

('Нет доступа к корпоративной сети', 'Не могу подключиться к VPN с домашнего компьютера. Ошибка соединения timeout.', 'in_progress', 'high', 'fca16fce-173b-4faa-b35c-dea91cf5e0fa', 'd9247e78-b285-48a8-9cec-e73e8e370afd', NOW() - INTERVAL '1 day', NOW() - INTERVAL '12 hours'),

('Сервер базы данных не отвечает', 'Приложение выдает ошибку подключения к БД. Проверьте статус сервера.', 'open', 'high', '1b907610-f900-479b-92e1-4bcad8042901', 'd9247e78-b285-48a8-9cec-e73e8e370afd', NOW() - INTERVAL '3 hours', NOW() - INTERVAL '3 hours');

-- Medium priority tickets
INSERT INTO support.tickets (title, description, status, priority, created_by_id, assigned_to_id, created_at, updated_at) VALUES
('Нужен доступ к папке на файловом сервере', 'Требуется доступ к папке \\server\documents\projectX для работы с документами.', 'open', 'medium', '749b46df-6450-4d6c-aee8-45f755314430', NULL, NOW() - INTERVAL '5 hours', NOW() - INTERVAL '5 hours'),

('Установить Microsoft Office на новый ноутбук', 'Новый сотрудник получил ноутбук, нужно установить Office 2021.', 'in_progress', 'medium', 'fca16fce-173b-4faa-b35c-dea91cf5e0fa', 'd9247e78-b285-48a8-9cec-e73e8e370afd', NOW() - INTERVAL '1 day', NOW() - INTERVAL '8 hours'),

('Проблема с почтовым клиентом', 'Outlook не синхронизирует почту, выдает ошибку 0x8004010F.', 'resolved', 'medium', '749b46df-6450-4d6c-aee8-45f755314430', 'd9247e78-b285-48a8-9cec-e73e8e370afd', NOW() - INTERVAL '3 days', NOW() - INTERVAL '2 days'),

('Медленная работа компьютера', 'Компьютер в кабинете 18.26 работает очень медленно, возможно нужно добавить оперативную память.', 'open', 'medium', 'fca16fce-173b-4faa-b35c-dea91cf5e0fa', NULL, NOW() - INTERVAL '6 hours', NOW() - INTERVAL '6 hours'),

('Настроить видеоконференцию', 'Нужно настроить Zoom для проведения совещания с партнерами в 14:00.', 'resolved', 'medium', '1b907610-f900-479b-92e1-4bcad8042901', 'd9247e78-b285-48a8-9cec-e73e8e370afd', NOW() - INTERVAL '4 days', NOW() - INTERVAL '4 days'),

('Блокировка аккаунта', 'Мой аккаунт заблокирован после нескольких неудачных попыток входа.', 'in_progress', 'medium', '749b46df-6450-4d6c-aee8-45f755314430', 'd9247e78-b285-48a8-9cec-e73e8e370afd', NOW() - INTERVAL '2 hours', NOW() - INTERVAL '1 hour');

-- Low priority tickets
INSERT INTO support.tickets (title, description, status, priority, created_by_id, assigned_to_id, created_at, updated_at) VALUES
('Запрос на дополнительный монитор', 'Хотел бы запросить второй монитор для повышения продуктивности.', 'open', 'low', '749b46df-6450-4d6c-aee8-45f755314430', NULL, NOW() - INTERVAL '1 day', NOW() - INTERVAL '1 day'),

('Обновить версию Adobe Reader', 'Текущая версия Adobe Reader устарела, нужно обновить до последней.', 'resolved', 'low', 'fca16fce-173b-4faa-b35c-dea91cf5e0fa', 'd9247e78-b285-48a8-9cec-e73e8e370afd', NOW() - INTERVAL '5 days', NOW() - INTERVAL '5 days'),

('Вопрос по использованию CRM', 'Нужна консультация по работе с новой CRM системой, как создавать отчеты.', 'open', 'low', 'fca16fce-173b-4faa-b35c-dea91cf5e0fa', NULL, NOW() - INTERVAL '4 hours', NOW() - INTERVAL '4 hours'),

('Сменить пароль на Wi-Fi', 'Хочу сменить пароль на корпоративную точку доступа Wi-Fi.', 'resolved', 'low', '749b46df-6450-4d6c-aee8-45f755314430', 'd9247e78-b285-48a8-9cec-e73e8e370afd', NOW() - INTERVAL '6 days', NOW() - INTERVAL '6 days'),

('Запрос на обучение', 'Хотел бы пройти обучение по работе с новой системой документооборота.', 'open', 'low', '1b907610-f900-479b-92e1-4bcad8042901', NULL, NOW() - INTERVAL '2 days', NOW() - INTERVAL '2 days'),

('Проблема с шрифтом в Word', 'При открытии документов Word отображаются странные символы вместо текста.', 'in_progress', 'low', 'fca16fce-173b-4faa-b35c-dea91cf5e0fa', 'd9247e78-b285-48a8-9cec-e73e8e370afd', NOW() - INTERVAL '3 hours', NOW() - INTERVAL '2 hours');

-- Add some comments to tickets
INSERT INTO support.ticket_comments (ticket_id, author_id, body, created_at) VALUES
(1, 'd9247e78-b285-48a8-9cec-e73e8e370afd', 'Проверил принтер, проблема с картриджем. Заказал новый.', NOW() - INTERVAL '1 day'),
(1, '749b46df-6450-4d6c-aee8-45f755314430', 'Спасибо, когда ожидается доставка?', NOW() - INTERVAL '20 hours'),
(2, 'd9247e78-b285-48a8-9cec-e73e8e370afd', 'Проверил настройки VPN, проблема на стороне провайдера. Работаем над решением.', NOW() - INTERVAL '10 hours'),
(2, 'fca16fce-173b-4faa-b35c-dea91cf5e0fa', 'Понял, буду ждать.', NOW() - INTERVAL '8 hours'),
(6, 'd9247e78-b285-48a8-9cec-e73e8e370afd', 'Проблема решена - был неправильно настроен профиль Exchange.', NOW() - INTERVAL '2 days'),
(6, '749b46df-6450-4d6c-aee8-45f755314430', 'Отлично, спасибо за помощь!', NOW() - INTERVAL '2 days'),
(8, 'd9247e78-b285-48a8-9cec-e73e8e370afd', 'Adobe Reader обновлен до версии 23.003.', NOW() - INTERVAL '5 days'),
(10, 'd9247e78-b285-48a8-9cec-e73e8e370afd', 'Пароль изменен. Новый пароль: DGI2024Secure', NOW() - INTERVAL '6 days'),
(12, 'd9247e78-b285-48a8-9cec-e73e8e370afd', 'Установлен недостающий шрифт Arial. Проблема решена.', NOW() - INTERVAL '1 hour');
