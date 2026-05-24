-- Сохранять ли запись эфира на канал после завершения
ALTER TABLE streams ADD COLUMN IF NOT EXISTS save_recording BOOLEAN NOT NULL DEFAULT true;
