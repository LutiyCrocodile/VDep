-- Seed additional users for support-service
-- New users with different positions, roles, offices

INSERT INTO support.support_profiles (id, username, full_name, position, internal_number, office, role, is_active, needs_approval, created_at) VALUES
-- Engineers (technical support staff)
('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'IvanovII', 'Иванов Иван Иванович', 'Инженер 1 категории', '21-001', '11.01', 'engineer', true, false, NOW() - INTERVAL '30 days'),
('b2c3d4e5-f6a7-8901-bcde-f12345678901', 'PetrovaAN', 'Петрова Анна Николаевна', 'Инженер 2 категории', '21-002', '11.02', 'engineer', true, false, NOW() - INTERVAL '25 days'),
('c3d4e5f6-a7b8-9012-cdef-123456789012', 'SidorovPV', 'Сидоров Петр Владимирович', 'Старший инженер', '21-003', '11.03', 'engineer', true, false, NOW() - INTERVAL '20 days'),

-- Regular users (employees from different departments)
('d4e5f6a7-b8c9-0123-def0-234567890123', 'KuznetsovaMS', 'Кузнецова Мария Сергеевна', 'Бухгалтер', '22-001', '12.01', 'user', true, false, NOW() - INTERVAL '35 days'),
('e5f6a7b8-c9d0-1234-ef01-345678901234', 'SmirnovAV', 'Смирнов Андрей Викторович', 'Юрист', '22-002', '12.02', 'user', true, false, NOW() - INTERVAL '40 days'),
('f6a7b8c9-d0e1-2345-f012-456789012345', 'VolkovaEA', 'Волкова Елена Александровна', 'Менеджер по продажам', '23-001', '13.01', 'user', true, false, NOW() - INTERVAL '28 days'),
('a7b8c9d0-e1f2-3456-0123-567890123456', 'MorozovDK', 'Морозов Дмитрий Константинович', 'Специалист по кадрам', '23-002', '13.02', 'user', true, false, NOW() - INTERVAL '32 days'),
('b8c9d0e1-f2a3-4567-1234-678901234567', 'NovikovaSV', 'Новикова Светлана Владимировна', 'Секретарь', '24-001', '14.01', 'user', true, false, NOW() - INTERVAL '22 days'),

-- Additional admin
('c9d0e1f2-a3b4-5678-2345-789012345678', 'SokolovAA', 'Соколов Алексей Андреевич', 'Заместитель директора', '25-001', '15.01', 'admin', true, false, NOW() - INTERVAL '45 days'),

-- IT Department users
('d0e1f2a3-b4c5-6789-3456-890123456789', 'FedorovIV', 'Федоров Игорь Владимирович', 'Системный администратор', '26-001', '16.01', 'engineer', true, false, NOW() - INTERVAL '18 days'),
('e1f2a3b4-c5d6-7890-4567-901234567890', 'KozlovaMN', 'Козлова Марина Николаевна', 'Администратор баз данных', '26-002', '16.02', 'engineer', true, false, NOW() - INTERVAL '15 days');
