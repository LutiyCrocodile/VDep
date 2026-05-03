-- Seed data for testing
-- Creates a default role and test user with empty password hash

-- Create default 'user' role if not exists
INSERT INTO roles (id, name, description, created_at, updated_at)
VALUES (
    gen_random_uuid(),
    'user',
    'Default user role',
    NOW(),
    NOW()
)
ON CONFLICT (name) DO NOTHING;

-- Create test user with password 'test' (bcrypt hash)
-- Hash generated with: bcrypt.hashpw(b'test', bcrypt.gensalt())
INSERT INTO users (id, username, email, hashed_password, full_name, is_active, role_id, created_at, updated_at)
SELECT
    gen_random_uuid(),
    'testuser',
    'test@test.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYA.qGZvKG6G',  -- password: 'test'
    'Test User',
    true,
    r.id,
    NOW(),
    NOW()
FROM roles r WHERE r.name = 'user'
ON CONFLICT (username) DO NOTHING;
