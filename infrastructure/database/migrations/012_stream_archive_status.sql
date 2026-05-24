-- Статус сохранения записи эфира на видеохостинг
ALTER TABLE streams ADD COLUMN IF NOT EXISTS archive_status VARCHAR(32);
ALTER TABLE streams ADD COLUMN IF NOT EXISTS archive_error TEXT;
