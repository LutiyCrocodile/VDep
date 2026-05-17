-- Исправить legacy-пути HLS (убрать лишний префикс /videos/ в значении)
UPDATE videos
SET hls_playlist_url = regexp_replace(hls_playlist_url, '^/videos/', '')
WHERE hls_playlist_url LIKE '/videos/%';
