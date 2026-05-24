-- Почта получателя dev_viewer (SMTP отправитель: lutcrocodil@yandex.ru в .env)
UPDATE users
SET email = 'moren280806@yandex.ru'
WHERE username = 'dev_viewer';

SELECT username, email FROM users WHERE username = 'dev_viewer';
