-- Схема мессенджера (variant B): профили по UUID из auth-service, без локальных паролей.
-- Таблицы также создаются через SQLAlchemy init_db при старте messenger-service.

CREATE SCHEMA IF NOT EXISTS messenger;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS messenger.departments (
    id UUID PRIMARY KEY,
    name VARCHAR(300) NOT NULL,
    short_name VARCHAR(100),
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO messenger.departments (id, name, short_name)
VALUES
    ('00000000-0000-0000-0000-000000000001', 'Управление информатизации', 'УИ'),
    ('00000000-0000-0000-0000-000000000002', 'Управление государственной службы и кадров', 'УГСК'),
    ('00000000-0000-0000-0000-000000000003', 'Управление имущества', 'УИм'),
    ('00000000-0000-0000-0000-000000000004', 'Управление земельных ресурсов', 'УЗР'),
    ('00000000-0000-0000-0000-000000000005', 'Правовое управление', 'ПУ'),
    ('00000000-0000-0000-0000-000000000006', 'Управление бухгалтерского учета и отчетности', 'УБУО')
ON CONFLICT (id) DO NOTHING;

-- Доступ к мессенджеру для dev-пользователей и глобального admin
INSERT INTO user_service_roles (user_id, service_role_id, granted_by)
SELECT u.id, sr.id, u.id
FROM users u
JOIN service_roles sr ON sr.name IN ('admin', 'user')
JOIN services s ON s.id = sr.service_id AND s.slug = 'messenger'
WHERE u.username IN ('admin', 'dev_admin', 'dev_viewer', 'dev_uploader')
ON CONFLICT (user_id, service_role_id) DO NOTHING;
