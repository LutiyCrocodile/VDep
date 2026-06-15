-- Очистка старых звонков из базы данных messenger
-- Удаляет звонки со статусом 'ended' или 'missed' старше 30 дней

-- Удаляем участников звонков
DELETE FROM messenger.call_participants
WHERE call_id IN (
    SELECT id FROM messenger.calls
    WHERE status IN ('ended', 'missed')
    AND created_at < NOW() - INTERVAL '30 days'
);

-- Удаляем сами звонки
DELETE FROM messenger.calls
WHERE status IN ('ended', 'missed')
AND created_at < NOW() - INTERVAL '30 days';

-- Для удаления всех завершённых звонков (независимо от даты):
-- DELETE FROM messenger.call_participants WHERE call_id IN (SELECT id FROM messenger.calls WHERE status IN ('ended', 'missed'));
-- DELETE FROM messenger.calls WHERE status IN ('ended', 'missed');
