-- Колонки users для auth-service / портала (если база создана до появления полей в модели).
-- Можно выполнить отдельно до seed / 004 / 005.

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'is_employee'
  ) THEN
    ALTER TABLE users ADD COLUMN is_employee boolean NOT NULL DEFAULT true;
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'full_name'
  ) THEN
    ALTER TABLE users ADD COLUMN full_name varchar(255);
  END IF;
END $$;
