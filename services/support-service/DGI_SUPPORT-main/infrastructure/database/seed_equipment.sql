-- Seed data for equipment
-- Users:
-- 1b907610-f900-479b-92e1-4bcad8042901 | EvteevAS | Евтеев Артем Сергеевич | admin
-- 749b46df-6450-4d6c-aee8-45f755314430 | ZaycES   | Зайцева Елена Сергеевна | user
-- d9247e78-b285-48a8-9cec-e73e8e370afd | MaksTA   | Трошин Максим Андреевич | engineer
-- fca16fce-173b-4faa-b35c-dea91cf5e0fa | MahAD    | Махмудова Аминат Долгатовна | user

-- Monoblocks
INSERT INTO support.equipment (category, status, consumable_type, model, serial_number, name, assigned_to_user_id, location, is_warehouse, notes, created_at) VALUES
('monoblock', 'assigned', NULL, 'HP ProDesk 600 G6', 'SN123456789', 'HP Monoblock Admin', '1b907610-f900-479b-92e1-4bcad8042901', '18.26', false, 'Основной рабочий компьютер администратора', NOW() - INTERVAL '30 days'),
('monoblock', 'assigned', NULL, 'HP ProDesk 600 G6', 'SN123456790', 'HP Monoblock Engineer', 'd9247e78-b285-48a8-9cec-e73e8e370afd', '18.26', false, 'Рабочий компьютер инженера', NOW() - INTERVAL '25 days'),
('monoblock', 'in_stock', NULL, 'HP ProDesk 600 G6', 'SN123456791', 'HP Monoblock Spare', NULL, NULL, true, 'Запасной моноблок на складе', NOW() - INTERVAL '20 days'),
('monoblock', 'assigned', NULL, 'Dell OptiPlex 7090', 'SN987654321', 'Dell Monoblock User 1', '749b46df-6450-4d6c-aee8-45f755314430', '12.23', false, 'Рабочий компьютер сотрудника', NOW() - INTERVAL '15 days'),
('monoblock', 'assigned', NULL, 'Dell OptiPlex 7090', 'SN987654322', 'Dell Monoblock User 2', 'fca16fce-173b-4faa-b35c-dea91cf5e0fa', '12.23', false, 'Рабочий компьютер сотрудника', NOW() - INTERVAL '10 days'),
('monoblock', 'retired', NULL, 'HP ProDesk 400 G5', 'SN111222333', 'HP Monoblock Old', NULL, NULL, false, 'Списан из-за устаревания', NOW() - INTERVAL '60 days');

-- Printers
INSERT INTO support.equipment (category, status, consumable_type, model, serial_number, name, assigned_to_user_id, location, is_warehouse, notes, created_at) VALUES
('printer', 'assigned', NULL, 'HP LaserJet Pro M404dn', 'SN555666777', 'HP Printer 12.23', NULL, '12.23', false, 'Принтер в кабинете 12.23', NOW() - INTERVAL '45 days'),
('printer', 'assigned', NULL, 'HP LaserJet Pro M404dn', 'SN555666778', 'HP Printer 18.26', NULL, '18.26', false, 'Принтер в кабинете 18.26', NOW() - INTERVAL '40 days'),
('printer', 'in_stock', NULL, 'Canon imageCLASS MF244dw', 'SN888999000', 'Canon Printer Spare', NULL, NULL, true, 'Запасной принтер на складе', NOW() - INTERVAL '35 days'),
('printer', 'retired', NULL, 'HP LaserJet 1020', 'SN000111222', 'HP Printer Old', NULL, NULL, false, 'Списан из-за поломки', NOW() - INTERVAL '90 days');

-- Consumables - Paper
INSERT INTO support.equipment (category, status, consumable_type, model, serial_number, name, assigned_to_user_id, location, is_warehouse, notes, created_at) VALUES
('consumable', 'in_stock', 'paper', 'A4 80gsm', NULL, 'Бумага A4 пачка 1', NULL, NULL, true, '500 листов', NOW() - INTERVAL '5 days'),
('consumable', 'in_stock', 'paper', 'A4 80gsm', NULL, 'Бумага A4 пачка 2', NULL, NULL, true, '500 листов', NOW() - INTERVAL '5 days'),
('consumable', 'in_stock', 'paper', 'A4 80gsm', NULL, 'Бумага A4 пачка 3', NULL, NULL, true, '500 листов', NOW() - INTERVAL '5 days'),
('consumable', 'retired', 'paper', 'A4 80gsm', NULL, 'Бумага A4 выдано', '749b46df-6450-4d6c-aee8-45f755314430', NULL, false, 'Выдано сотруднику', NOW() - INTERVAL '1 day');

-- Consumables - Toner
INSERT INTO support.equipment (category, status, consumable_type, model, serial_number, name, assigned_to_user_id, location, is_warehouse, notes, created_at) VALUES
('consumable', 'in_stock', 'toner', 'HP 26A (CF226A)', NULL, 'Картридж HP 26A #1', NULL, NULL, true, 'Для HP LaserJet Pro M404dn', NOW() - INTERVAL '10 days'),
('consumable', 'in_stock', 'toner', 'HP 26A (CF226A)', NULL, 'Картридж HP 26A #2', NULL, NULL, true, 'Для HP LaserJet Pro M404dn', NOW() - INTERVAL '10 days'),
('consumable', 'retired', 'toner', 'HP 26A (CF226A)', NULL, 'Картридж HP 26A выдан', 'd9247e78-b285-48a8-9cec-e73e8e370afd', NULL, false, 'Выдано инженеру для замены', NOW() - INTERVAL '3 days'),
('consumable', 'in_stock', 'toner', 'Canon 057 (CRG057)', NULL, 'Картридж Canon 057', NULL, NULL, true, 'Для Canon imageCLASS MF244dw', NOW() - INTERVAL '15 days');

-- Consumables - Cables
INSERT INTO support.equipment (category, status, consumable_type, model, serial_number, name, assigned_to_user_id, location, is_warehouse, notes, created_at) VALUES
('consumable', 'in_stock', 'cable', 'HDMI 2m', NULL, 'Кабель HDMI 2м #1', NULL, NULL, true, 'Для подключения мониторов', NOW() - INTERVAL '7 days'),
('consumable', 'in_stock', 'cable', 'HDMI 2m', NULL, 'Кабель HDMI 2м #2', NULL, NULL, true, 'Для подключения мониторов', NOW() - INTERVAL '7 days'),
('consumable', 'retired', 'cable', 'USB-C 1.5m', NULL, 'Кабель USB-C выдан', 'fca16fce-173b-4faa-b35c-dea91cf5e0fa', NULL, false, 'Выдано сотруднику', NOW() - INTERVAL '2 days'),
('consumable', 'in_stock', 'cable', 'Ethernet Cat6 5m', NULL, 'Кабель Ethernet 5м', NULL, NULL, true, 'Для сетевого подключения', NOW() - INTERVAL '8 days');

-- Consumables - Other
INSERT INTO support.equipment (category, status, consumable_type, model, serial_number, name, assigned_to_user_id, location, is_warehouse, notes, created_at) VALUES
('consumable', 'in_stock', 'mouse', 'Logitech M185', NULL, 'Мышь Logitech #1', NULL, NULL, true, 'Беспроводная мышь', NOW() - INTERVAL '6 days'),
('consumable', 'in_stock', 'mouse', 'Logitech M185', NULL, 'Мышь Logitech #2', NULL, NULL, true, 'Беспроводная мышь', NOW() - INTERVAL '6 days'),
('consumable', 'retired', 'mouse', 'Logitech M185', NULL, 'Мышь Logitech выдана', '749b46df-6450-4d6c-aee8-45f755314430', NULL, false, 'Выдано сотруднику', NOW() - INTERVAL '4 days'),
('consumable', 'in_stock', 'keyboard', 'Logitech K120', NULL, 'Клавиатура Logitech', NULL, NULL, true, 'USB клавиатура', NOW() - INTERVAL '9 days'),
('consumable', 'in_stock', 'adapter', 'USB-C to HDMI', NULL, 'Адаптер USB-C-HDMI', NULL, NULL, true, 'Для подключения внешнего монитора', NOW() - INTERVAL '5 days');
