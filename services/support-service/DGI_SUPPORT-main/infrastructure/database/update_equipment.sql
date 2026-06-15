-- Update equipment assignments to new users
-- New user IDs:
-- a1b2c3d4-e5f6-7890-abcd-ef1234567890 - IvanovII (engineer)
-- b2c3d4e5-f6a7-8901-bcde-f12345678901 - PetrovaAN (engineer)
-- c3d4e5f6-a7b8-9012-cdef-123456789012 - SidorovPV (engineer)
-- d4e5f6a7-b8c9-0123-def0-234567890123 - KuznetsovaMS (user)
-- e5f6a7b8-c9d0-1234-ef01-345678901234 - SmirnovAV (user)
-- f6a7b8c9-d0e1-2345-f012-456789012345 - VolkovaEA (user)
-- a7b8c9d0-e1f2-3456-0123-567890123456 - MorozovDK (user)
-- b8c9d0e1-f2a3-4567-1234-678901234567 - NovikovaSV (user)
-- c9d0e1f2-a3b4-5678-2345-789012345678 - SokolovAA (admin)
-- d0e1f2a3-b4c5-6789-3456-890123456789 - FedorovIV (engineer)
-- e1f2a3b4-c5d6-7890-4567-901234567890 - KozlovaMN (engineer)

-- Assign printers to offices
UPDATE support.equipment SET assigned_to_user_id = 'd4e5f6a7-b8c9-0123-def0-234567890123' WHERE id = 21; -- HP Printer 12.23 -> KuznetsovaMS (бухгалтер)
UPDATE support.equipment SET assigned_to_user_id = 'e5f6a7b8-c9d0-1234-ef01-345678901234' WHERE id = 22; -- HP Printer 18.26 -> SmirnovAV (юрист)

-- Assign monoblocks to new users
UPDATE support.equipment SET assigned_to_user_id = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890' WHERE id = 1; -- HP -> IvanovII (engineer)
UPDATE support.equipment SET assigned_to_user_id = 'b2c3d4e5-f6a7-8901-bcde-f12345678901' WHERE id = 14; -- HP -> PetrovaAN (engineer)
UPDATE support.equipment SET assigned_to_user_id = 'c3d4e5f6-a7b8-9012-cdef-123456789012' WHERE id = 16; -- HP Monoblock Engineer -> SidorovPV (engineer)
UPDATE support.equipment SET assigned_to_user_id = 'f6a7b8c9-d0e1-2345-f012-456789012345' WHERE id = 18; -- Dell Monoblock User 1 -> VolkovaEA (менеджер)
UPDATE support.equipment SET assigned_to_user_id = 'a7b8c9d0-e1f2-3456-0123-567890123456' WHERE id = 19; -- Dell Monoblock User 2 -> MorozovDK (HR)

-- Assign consumables to new users
UPDATE support.equipment SET assigned_to_user_id = 'b8c9d0e1-f2a3-4567-1234-678901234567' WHERE id = 28; -- Бумага A4 выдано -> NovikovaSV (секретарь)
UPDATE support.equipment SET assigned_to_user_id = 'd0e1f2a3-b4c5-6789-3456-890123456789' WHERE id = 31; -- Картридж HP 26A выдан -> FedorovIV (системный администратор)
UPDATE support.equipment SET assigned_to_user_id = 'e1f2a3b4-c5d6-7890-4567-901234567890' WHERE id = 35; -- Кабель USB-C выдан -> KozlovaMN (администратор БД)

-- Add new equipment for admin
INSERT INTO support.equipment (name, category, status, assigned_to_user_id, location, notes, created_at) VALUES
('Dell XPS 15 Admin', 'monoblock', 'assigned', 'c9d0e1f2-a3b4-5678-2345-789012345678', '15.01', 'Ноутбук для заместителя директора', NOW() - INTERVAL '10 days'),
('HP EliteBook Admin', 'monoblock', 'in_stock', NULL, '15.01', 'Запасной ноутбук для руководства', NOW() - INTERVAL '10 days');

-- Add new equipment for IT department
INSERT INTO support.equipment (name, category, status, assigned_to_user_id, location, notes, created_at) VALUES
('Dell Server Rack', 'monoblock', 'assigned', 'd0e1f2a3-b4c5-6789-3456-890123456789', '16.01', 'Серверное оборудование', NOW() - INTERVAL '8 days'),
('NAS Synology', 'monoblock', 'assigned', 'e1f2a3b4-c5d6-7890-4567-901234567890', '16.02', 'Система хранения данных', NOW() - INTERVAL '8 days'),
('Cisco Switch 24-port', 'monoblock', 'in_stock', NULL, '16.01', 'Коммутатор для сети', NOW() - INTERVAL '7 days');

-- Add new equipment for regular users
INSERT INTO support.equipment (name, category, status, assigned_to_user_id, location, notes, created_at) VALUES
('HP Laptop User1', 'monoblock', 'assigned', 'd4e5f6a7-b8c9-0123-def0-234567890123', '12.01', 'Ноутбук для бухгалтерии', NOW() - INTERVAL '5 days'),
('HP Laptop User2', 'monoblock', 'assigned', 'e5f6a7b8-c9d0-1234-ef01-345678901234', '12.02', 'Ноутбук для юр. отдела', NOW() - INTERVAL '5 days'),
('HP Laptop User3', 'monoblock', 'assigned', 'f6a7b8c9-d0e1-2345-f012-456789012345', '13.01', 'Ноутбук для отдела продаж', NOW() - INTERVAL '5 days'),
('HP Laptop User4', 'monoblock', 'assigned', 'a7b8c9d0-e1f2-3456-0123-567890123456', '13.02', 'Ноутбук для HR', NOW() - INTERVAL '5 days'),
('HP Laptop User5', 'monoblock', 'assigned', 'b8c9d0e1-f2a3-4567-1234-678901234567', '14.01', 'Ноутбук для секретаря', NOW() - INTERVAL '5 days');

-- Add more consumables
INSERT INTO support.equipment (name, category, status, assigned_to_user_id, location, notes, created_at) VALUES
('Бумага A4 пачка 4', 'consumable', 'in_stock', NULL, 'Склад', 'Бумага для принтеров', NOW() - INTERVAL '3 days'),
('Бумага A4 пачка 5', 'consumable', 'in_stock', NULL, 'Склад', 'Бумага для принтеров', NOW() - INTERVAL '3 days'),
('Картридж HP 26A #3', 'consumable', 'in_stock', NULL, 'Склад', 'Запасной картридж', NOW() - INTERVAL '2 days'),
('Картридж Canon 057 #2', 'consumable', 'in_stock', NULL, 'Склад', 'Запасной картридж', NOW() - INTERVAL '2 days'),
('Кабель HDMI 2м #3', 'consumable', 'in_stock', NULL, 'Склад', 'Кабель для мониторов', NOW() - INTERVAL '2 days'),
('Кабель USB-C #2', 'consumable', 'in_stock', NULL, 'Склад', 'Кабель для подключения', NOW() - INTERVAL '2 days'),
('Мышь Logitech #3', 'consumable', 'in_stock', NULL, 'Склад', 'Запасная мышь', NOW() - INTERVAL '2 days'),
('Клавиатура Logitech #2', 'consumable', 'in_stock', NULL, 'Склад', 'Запасная клавиатура', NOW() - INTERVAL '2 days');
