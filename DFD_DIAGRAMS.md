# DFD Диаграммы потоков данных для микросервисного видеохостинга

## DFD Уровень 0: Контекстная диаграмма системы

```mermaid
graph TD
    User[Пользователь] -->|HTTP/HTTPS| System[Система видеохостинга ДГИ]
    System -->|HTTP/HTTPS| User
    
    subgraph Внешние системы
        AD[Active Directory]
        ESIA[ЕСИА]
        SMTP[SMTP сервер]
    end
    
    System -->|LDAP протокол| AD
    System -->|OAuth 2.0| ESIA
    System -->|Email уведомления| SMTP
    
    style System fill:#e1f5ff
    style User fill:#fff4e1
    style AD fill:#ffe1e1
    style ESIA fill:#ffe1e1
    style SMTP fill:#ffe1e1
```

## DFD Уровень 1: Основные процессы системы

```mermaid
graph TD
    User[Пользователь] -->|1. Логин/Регистрация| P1[Процесс 1: Аутентификация]
    User -->|2. Загрузка видео| P2[Процесс 2: Управление видео]
    User -->|3. Просмотр видео| P3[Процесс 3: Воспроизведение]
    User -->|4. Создание стрима| P4[Процесс 4: Стриминг]
    User -->|5. Поиск| P5[Процесс 5: Поиск]
    User -->|6. Управление уведомлениями| P6[Процесс 6: Уведомления]
    
    P1 -->|JWT токен| User
    P1 -->|Проверка пользователя| D1[(PostgreSQL)]
    P1 -->|LDAP запрос| AD[Active Directory]
    P1 -->|OAuth запрос| ESIA[ЕСИА]
    
    P2 -->|Сохранение файла| S1[MinIO]
    P2 -->|Метаданные видео| D1
    P2 -->|Задача на транскодирование| Q1[RabbitMQ]
    P2 -->|Уведомление о статусе| P6
    
    P3 -->|HLS плейлист| S1
    P3 -->|Статистика просмотра| D1
    P3 -->|Запрос субтитров| P5
    
    P4 -->|RTMP поток| NginxRTMP[Nginx RTMP]
    P4 -->|HLS URL| User
    P4 -->|Архив| S1
    P4 -->|Метаданные стрима| D1
    P4 -->|Уведомление о стриме| P6
    
    P5 -->|Поисковый запрос| ES[Elasticsearch]
    ES -->|Результаты поиска| P5
    P5 -->|Ссылки на видео| User
    P5 -->|Субтитры| D1
    
    P6 -->|Email уведомления| SMTP[SMTP сервер]
    P6 -->|WebSocket уведомления| User
    
    subgraph Очереди сообщений
        Q1[RabbitMQ]
        Q2[Redis Queue]
    end
    
    subgraph Обработка фоновых задач
        CW[Celery Worker]
        SW[Subtitle Worker]
    end
    
    Q1 -->|Транскодирование| CW
    CW -->|HLS чанки| S1
    CW -->|Статус видео| D1
    CW -->|Задача на субтитры| Q2
    
    Q2 -->|Распознавание речи| SW
    SW -->|Субтитры WebVTT| D1
    SW -->|Индексация текста| ES
    
    style P1 fill:#e1f5ff
    style P2 fill:#e1f5ff
    style P3 fill:#e1f5ff
    style P4 fill:#e1f5ff
    style P5 fill:#e1f5ff
    style P6 fill:#e1f5ff
    style D1 fill:#fff4e1
    style S1 fill:#fff4e1
    style ES fill:#fff4e1
```

## DFD Уровень 2: Детальный процесс аутентификации

```mermaid
graph TD
    User[Пользователь] -->|1. POST /login| AS[Auth Service]
    AS -->|2. Поиск пользователя| D1[(PostgreSQL)]
    D1 -->|3. Данные пользователя| AS
    
    AS -->|4. Проверка пароля| BCrypt[BCrypt Hashing]
    BCrypt -->|5. Результат проверки| AS
    
    AS -->|6. Локальная аутентификация неуспешна?| Decision{Локальный пользователь?}
    Decision -->|Да| AS
    Decision -->|Нет| LDAP[LDAP Client]
    
    LDAP -->|7. Bind запрос| AD[Active Directory]
    AD -->|8. Результат аутентификации| LDAP
    LDAP -->|9. Создание пользователя| D1
    LDAP -->|10. Данные пользователя| AS
    
    AS -->|11. Генерация Access Token| JWT[JWT Generation]
    AS -->|12. Генерация Refresh Token| JWT
    JWT -->|13. Токены| AS
    
    AS -->|14. Запись сессии| Redis[(Redis Cache)]
    AS -->|15. Ответ с токенами| User
    
    User -->|16. Хранение токенов| LocalStorage[LocalStorage]
    
    subgraph Безопасность
        BCrypt[BCrypt Hashing]
        JWT[JWT Generation]
    end
    
    style AS fill:#e1f5ff
    style D1 fill:#fff4e1
    style Redis fill:#fff4e1
    style AD fill:#ffe1e1
```

## DFD Уровень 2: Детальный процесс загрузки видео

```mermaid
graph TD
    User[Пользователь] -->|1. Выбор файла| UI[Frontend UI]
    UI -->|2. POST /upload/init| VS[Video Service]
    
    VS -->|3. Валидация токена| AS[Auth Service]
    AS -->|4. Пользователь валиден| VS
    
    VS -->|5. Создание записи видео| D1[(PostgreSQL)]
    D1 -->|6. video_id, minio_key| VS
    
    VS -->|7. Генерация Presigned URL| MinIO[MinIO Client]
    MinIO -->|8. Presigned URL| VS
    VS -->|9. upload_url, video_id| UI
    
    UI -->|10. Разделение на чанки| Chunker[Chunk Splitter]
    Chunker -->|11. Чанки 5MB| UI
    
    UI -->|12. PUT чанка| MinIO
    MinIO -->|13. Прогресс| UI
    
    UI -->|14. POST /complete| VS
    VS -->|15. Обновление статуса: uploaded| D1
    VS -->|16. Отправка задачи| RQ[RabbitMQ]
    
    RQ -->|17. transcode_video| CW[Celery Worker]
    
    CW -->|18. Скачать оригинал| MinIO
    MinIO -->|19. Видео файл| CW
    
    CW -->|20. Анализ метаданных| FFprobe[FFprobe]
    FFprobe -->|21. duration, resolution, bitrate| CW
    CW -->|22. Обновление метаданных| D1
    
    CW -->|23. FFmpeg транскодирование| FFmpeg[FFmpeg]
    
    subgraph Генерация HLS
        FFmpeg -->|24. 180p| HLS1[HLS 180p]
        FFmpeg -->|25. 360p| HLS2[HLS 360p]
        FFmpeg -->|26. 480p| HLS3[HLS 480p]
        FFmpeg -->|27. 720p| HLS4[HLS 720p]
        FFmpeg -->|28. 1080p| HLS5[HLS 1080p]
    end
    
    HLS1 -->|29. Загрузка HLS| MinIO
    HLS2 -->|29| MinIO
    HLS3 -->|29| MinIO
    HLS4 -->|29| MinIO
    HLS5 -->|29| MinIO
    
    CW -->|30. Генерация мастер-плейлиста| FFmpeg
    FFmpeg -->|31. master.m3u8| MinIO
    
    CW -->|32. Обновление статуса: ready| D1
    CW -->|33. Сохранение HLS URL| D1
    
    CW -->|34. Задача на субтитры| RQ2[Redis Queue]
    
    RQ2 -->|35. generate_subtitles| SW[Subtitle Worker]
    
    SW -->|36. Скачать аудио| MinIO
    MinIO -->|37. Аудио дорожка| SW
    
    SW -->|38. Распознавание речи Vosk| Vosk[Vosk STT]
    Vosk -->|39. Текст с таймкодами| SW
    
    SW -->|40. Генерация WebVTT| WebVTT[WebVTT Generator]
    WebVTT -->|41. Субтитры| D1
    
    SW -->|42. Задача на индексацию| RQ3[RabbitMQ]
    
    RQ3 -->|43. index_video| SS[Search Service]
    SS -->|44. Индексация в Elasticsearch| ES[Elasticsearch]
    ES -->|45. Поисковый индекс| SS
    
    SS -->|46. Уведомление| NS[Notification Service]
    NS -->|47. Email| SMTP[SMTP]
    NS -->|48. WebSocket| UI
    
    UI -->|49. Показать уведомление| User
    
    style VS fill:#e1f5ff
    style CW fill:#e1f5ff
    style SW fill:#e1f5ff
    style SS fill:#e1f5ff
    style NS fill:#e1f5ff
    style D1 fill:#fff4e1
    style MinIO fill:#fff4e1
    style ES fill:#fff4e1
```

## DFD Уровень 2: Детальный процесс воспроизведения видео

```mermaid
graph TD
    User[Пользователь] -->|1. Запрос страницы видео| UI[Frontend]
    UI -->|"2. GET /videos/{id}"| VS[Video Service]
    
    VS -->|3. Проверка токена| AS[Auth Service]
    AS -->|4. Разрешения пользователя| VS
    
    VS -->|5. Проверка прав доступа| RBAC[RBAC Check]
    RBAC -->|6. Доступ разрешён?| Decision{Доступ?}
    Decision -->|Нет| Error[403 Forbidden]
    Decision -->|Да| VS
    
    VS -->|7. Получение метаданных| D1[(PostgreSQL)]
    D1 -->|8. Видео данные| VS
    VS -->|9. Метаданные видео| UI
    
    UI -->|10. Инициализация плеера| VP[Video Player]
    VP -->|11. GET /signed-url| VS
    
    VS -->|12. Проверка доступа| AS
    AS -->|13. Доступ подтверждён| VS
    
    VS -->|14. Генерация Presigned URL| MinIO[MinIO]
    MinIO -->|15. Signed URL| VS
    VS -->|16. Signed URL| VP
    
    VP -->|17. Запрос HLS плейлиста| Nginx[Nginx VOD Module]
    Nginx -->|18. Проверка в кэше| Cache[Redis Cache]
    
    Cache -->|19. Чанк в кэше?| CacheDecision{В кэше?}
    CacheDecision -->|Да| Nginx
    CacheDecision -->|Нет| MinIO
    
    MinIO -->|20. HLS чанк| Nginx
    Nginx -->|21. Сохранение в кэш| Cache
    
    Nginx -->|22. HLS поток| VP
    VP -->|23. Воспроизведение| User
    
    VP -->|24. Отправка статистики| VS
    VS -->|25. Запись в video_views| D1
    
    VP -->|26. Обновление прогресса| D1
    
    subgraph Кэширование
        Cache[Redis Cache]
    end
    
    style VS fill:#e1f5ff
    style VP fill:#e1f5ff
    style D1 fill:#fff4e1
    style MinIO fill:#fff4e1
    style Cache fill:#fff4e1
```

## DFD Уровень 2: Детальный процесс стриминга

```mermaid
graph TD
    Streamer[Стример] -->|1. Настройка OBS| OBS[OBS Studio]
    OBS -->|2. RTMP поток| NginxRTMP[Nginx RTMP Module]
    
    NginxRTMP -->|3. Проверка stream_key| SS[Streaming Service]
    SS -->|4. Валидация ключа| D1[(PostgreSQL)]
    D1 -->|5. Ключ валиден| SS
    
    SS -->|6. Создание записи стрима| D1
    D1 -->|7. stream_id, rtmp_key| SS
    
    NginxRTMP -->|8. Запуск FFmpeg| FFmpeg[FFmpeg]
    
    subgraph Транскодирование в реальном времени
        FFmpeg -->|9. Низкое качество| HLS1[HLS Low]
        FFmpeg -->|10. Среднее качество| HLS2[HLS Medium]
        FFmpeg -->|11. Высокое качество| HLS3[HLS High]
    end
    
    HLS1 -->|12. DVR буфер| Temp[Temp Storage]
    HLS2 -->|12| Temp
    HLS3 -->|12| Temp
    
    Temp -->|13. Накопительный плейлист| NginxRTMP
    NginxRTMP -->|14. HLS URL| SS
    SS -->|15. Обновление статуса: live| D1
    
    Viewer[Зритель] -->|16. Запрос стрима| UI[Frontend]
    UI -->|"17. GET /streams/{id}"| SS
    SS -->|18. Метаданные стрима| D1
    D1 -->|19. Данные стрима| SS
    SS -->|20. HLS URL| UI
    
    UI -->|21. HLS плеер| VP[HLS Player]
    VP -->|22. Запрос плейлиста| NginxRTMP
    NginxRTMP -->|23. DVR плейлист| VP
    VP -->|24. Воспроизведение| Viewer
    
    VP -->|25. Управление DVR| NginxRTMP
    NginxRTMP -->|26. Перемотка| Temp
    
    SS -->|27. Уведомление о начале| NS[Notification Service]
    NS -->|28. Email| SMTP[SMTP]
    NS -->|29. WebSocket| UI
    
    Streamer -->|30. Остановка стрима| SS
    SS -->|31. Статус: ended| D1
    
    SS -->|32. Задача на архивацию| RQ[RabbitMQ]
    RQ -->|33. archive_stream| CW[Celery Worker]
    
    CW -->|34. Объединение сегментов| FFmpeg
    FFmpeg -->|35. Видео файл| CW
    
    CW -->|36. Загрузка архива| MinIO[MinIO]
    MinIO -->|37. Архив загружен| CW
    
    CW -->|38. Создание записи видео| D1
    CW -->|39. Связь stream -> video| D1
    
    CW -->|40. Уведомление об архиве| NS
    NS -->|41. Email архив| SMTP
    NS -->|42| UI
    
    style SS fill:#e1f5ff
    style CW fill:#e1f5ff
    style NS fill:#e1f5ff
    style D1 fill:#fff4e1
    style MinIO fill:#fff4e1
    style Temp fill:#fff4e1
```

## DFD Уровень 2: Детальный процесс поиска

```mermaid
graph TD
    User[Пользователь] -->|1. Поисковый запрос| UI[Frontend]
    UI -->|2. GET /search?q=query| SS[Search Service]
    
    SS -->|3. Построение Elasticsearch запроса| ESQuery[Query Builder]
    ESQuery -->|4. Multi-match запрос| ES[Elasticsearch]
    
    subgraph Поля поиска
        ESQuery -->|title| Title[Название]
        ESQuery -->|description| Desc[Описание]
        ESQuery -->|subtitles| Sub[Субтитры]
        ESQuery -->|tags| Tags[Теги]
    end
    
    ES -->|5. Поиск по индексу| Index[Search Index]
    Index -->|6. Результаты с релевантностью| ES
    ES -->|7. Результаты поиска| SS
    
    SS -->|8. Получение метаданных| D1[(PostgreSQL)]
    D1 -->|9. Полные данные видео| SS
    
    SS -->|10. Применение фильтров доступа| RBAC[RBAC Filter]
    RBAC -->|11. Фильтрованные результаты| SS
    
    SS -->|12. Формирование ответа| Response[Response Formatter]
    Response -->|13. JSON с результатами| UI
    
    UI -->|14. Отображение результатов| User
    
    User -->|15. Клик по результату| UI
    UI -->|16. Переход к видео| VP[Video Player]
    
    subgraph Поиск по субтитрам
        User -->|17. Поиск в субтитрах| UI
        UI -->|"18. GET /videos/{id}/subtitles/search"| SS
        SS -->|19. Поиск по WebVTT| SubSearch[Subtitle Search]
        SubSearch -->|20. Таймкоды совпадений| SS
        SS -->|21. Результаты с таймкодами| UI
        UI -->|22. Переход к моменту| VP
    end
    
    style SS fill:#e1f5ff
    style ES fill:#e1f5ff
    style D1 fill:#fff4e1
```

## DFD Уровень 2: Детальный процесс уведомлений

```mermaid
graph TD
    Event[Событие системы] -->|1. Триггер уведомления| NS[Notification Service]
    
    subgraph Типы событий
        Event -->|video_ready| VR[Видео готово]
        Event -->|stream_start| SS[Стрим начат]
        Event -->|stream_end| SE[Стрим завершён]
        Event -->|transcoding_progress| TP[Прогресс транскодирования]
    end
    
    NS -->|2. Определение получателей| D1[(PostgreSQL)]
    D1 -->|3. Список пользователей| NS
    
    NS -->|4. Создание записей уведомлений| D1
    D1 -->|5. notification_id| NS
    
    NS -->|6. Формирование Email| EmailFormatter[Email Formatter]
    EmailFormatter -->|7. HTML шаблон| NS
    
    NS -->|8. Отправка Email| SMTP[SMTP Server]
    SMTP -->|9. Статус отправки| NS
    
    NS -->|10. Обновление статуса| D1
    
    NS -->|11. WebSocket broadcast| WSS[WebSocket Server]
    
    subgraph Подключенные клиенты
        WSS -->|12| Client1[Client 1]
        WSS -->|13| Client2[Client 2]
        WSS -->|14| Client3[Client 3]
    end
    
    Client1 -->|15| UI1[Frontend 1]
    Client2 -->|16| UI2[Frontend 2]
    Client3 -->|17| UI3[Frontend 3]
    
    UI1 -->|18| User1[Пользователь 1]
    UI2 -->|19| User2[Пользователь 2]
    UI3 -->|20| User3[Пользователь 3]
    
    User1 -->|21. Отметить как прочитанное| UI1
    UI1 -->|"22. PUT /notifications/{id}/read"| NS
    NS -->|23. Обновление is_read| D1
    
    subgraph Очередь email
        NS -->|24| RQ[RabbitMQ]
        RQ -->|25| EmailWorker[Email Worker]
        EmailWorker -->|26| SMTP
    end
    
    style NS fill:#e1f5ff
    style WSS fill:#e1f5ff
    style D1 fill:#fff4e1
    style SMTP fill:#ffe1e1
```

## DFD Уровень 2: Детальный процесс мониторинга

```mermaid
graph TD
    Services[Микросервисы] -->|1. Метрики| P[Prometheus]
    
    subgraph Источники метрик
        Services -->|HTTP запросы| AS[Auth Service]
        Services -->|Транскодирование| VS[Video Service]
        Services -->|Стриминг| SS[Streaming Service]
        Services -->|Поиск| SES[Search Service]
        Services -->|Уведомления| NS[Notification Service]
    end
    
    AS -->|2. prometheus-client| P
    VS -->|2| P
    SS -->|2| P
    SES -->|2| P
    NS -->|2| P
    
    Infrastructure[Инфраструктура] -->|3. Системные метрики| NE[Node Exporter]
    
    subgraph Системные метрики
        Infrastructure -->|CPU| CPU[CPU Usage]
        Infrastructure -->|Memory| MEM[Memory Usage]
        Infrastructure -->|Disk| DISK[Disk I/O]
        Infrastructure -->|Network| NET[Network I/O]
    end
    
    NE -->|4| P
    
    Databases[Базы данных] -->|5. Метрики БД| P
    
    subgraph Метрики БД
        Databases -->|Connections| PGConn[PG Connections]
        Databases -->|Query time| PGTime[PG Query Time]
        Databases -->|Index usage| PGIndex[PG Index Usage]
        Databases -->|Queue size| RQSize[RabbitMQ Queue]
        Databases -->|Cache hit| RedisHit[Redis Hit Rate]
    end
    
    P -->|6| TSDB[Time Series DB]
    
    G[Grafana] -->|7. Запрос метрик| P
    P -->|8. Данные метрик| G
    
    G -->|9| Dashboard[Дашборды]
    Dashboard -->|10| Admin[Администратор]
    
    P -->|11| AlertManager[Alert Manager]
    
    subgraph Алерты
        AlertManager -->|CPU > 80%| CPUAlert[CPU Alert]
        AlertManager -->|Memory > 85%| MemAlert[Memory Alert]
        AlertManager -->|Disk > 90%| DiskAlert[Disk Alert]
        AlertManager -->|Service Down| ServiceAlert[Service Alert]
        AlertManager -->|Queue > 100| QueueAlert[Queue Alert]
    end
    
    CPUAlert -->|12| Telegram[Telegram Bot]
    MemAlert -->|12| Telegram
    DiskAlert -->|12| Telegram
    ServiceAlert -->|12| Telegram
    QueueAlert -->|12| Telegram
    
    Telegram -->|13| DevOps[DevOps команда]
    
    style P fill:#e1f5ff
    style G fill:#e1f5ff
    style TSDB fill:#fff4e1
    style AlertManager fill:#ffe1e1
```

## DFD Уровень 3: Внутренняя логика Video Service

```mermaid
graph TD
    Request[HTTP Request] -->|1| API[FastAPI Router]
    
    API -->|2| Auth[Auth Middleware]
    Auth -->|3| ValidateToken[Token Validation]
    ValidateToken -->|4| AuthService[Auth Service Call]
    AuthService -->|5: UserID - Auth| End(( ))
    
    Auth -->|6| RBAC[RBAC Check]
    RBAC -->|7| PC["Permission Check"]
    PC --> D1[(PostgreSQL)]
    D1 -->|8 Permissions| RBAC
    RBAC -->|9 Access Granted| API
    
    API -->|10| Controller[Controller Layer]
    
    subgraph Endpoints
        Controller -->|POST /upload/init| UploadInit[Upload Init]
        Controller -->|POST /complete| UploadComplete[Upload Complete]
        Controller -->|GET /videos| ListVideos[List Videos]
        Controller -->|"GET /videos/{id}"| GetVideo[Get Video]
        Controller -->|GET /signed-url| SignedURL[Signed URL]
    end
    
    UploadInit -->|11| Service[Service Layer]
    Service -->|12| CreateVideo[Create Video Record]
    CreateVideo -->|13 Insert| D1
    D1 -->|14 Video ID| Service
    
    Service -->|15| MinIOClient[MinIO Client]
    MinIOClient -->|16 Presigned URL| MinIO[MinIO]
    MinIO -->|17 URL| MinIOClient
    MinIOClient -->|18 Upload URL| Service
    
    Service -->|19 Response| API
    API -->|20 JSON Response| Client[Client]
    
    UploadComplete -->|21| Service
    Service -->|22| UpdateStatus[Update Status]
    UpdateStatus -->|23 Update| D1
    
    Service -->|24| CeleryTask[Celery Task]
    CeleryTask -->|25 Send Task| RQ[RabbitMQ]
    
    ListVideos -->|26| Service
    Service -->|27| QueryVideos[Query Videos]
    QueryVideos -->|28 Select| D1
    D1 -->|29 Videos List| Service
    Service -->|30 Response| API
    
    GetVideo -->|31| Service
    Service -->|32| GetVideoByID[Get Video by ID]
    GetVideoByID -->|33 Select| D1
    D1 -->|34 Video Data| Service
    Service -->|35| CheckAccess[Check Access]
    CheckAccess -->|36 RBAC| Service
    Service -->|37 Response| API
    
    SignedURL -->|38| Service
    Service -->|39| GenerateSignedURL[Generate Signed URL]
    GenerateSignedURL -->|40 Presigned| MinIO
    MinIO -->|41 Signed URL| Service
    Service -->|42 Response| API
    
    style API fill:#e1f5ff
    style Service fill:#e1f5ff
    style D1 fill:#fff4e1
    style MinIO fill:#fff4e1
    style RQ fill:#ffe1e1
```

## DFD Уровень 3: Внутренняя логика Celery Worker

```mermaid
graph TD
    RQ[RabbitMQ] -->|1. Получение задачи| CW[Celery Worker]
    
    CW -->|2. Task Router| Router[Task Router]
    
    subgraph Типы задач
        Router -->|transcode_video| Transcode[Transcode Video]
        Router -->|generate_thumbnails| Thumbnails[Generate Thumbnails]
        Router -->|generate_watermark| Watermark[Apply Watermark]
        Router -->|archive_stream| Archive[Archive Stream]
    end
    
    Transcode -->|3. Download Video| MinIO[MinIO]
    MinIO -->|4. Video File| Transcode
    
    Transcode -->|5. FFprobe Analysis| FFprobe[FFprobe]
    FFprobe -->|6. Metadata| Transcode
    
    Transcode -->|7. Update Metadata| D1[(PostgreSQL)]
    D1 -->|8| Transcode
    
    Transcode -->|9. FFmpeg Transcode| FFmpeg[FFmpeg]
    
    subgraph Качества
        FFmpeg -->|180p| Q1[Quality 180p]
        FFmpeg -->|360p| Q2[Quality 360p]
        FFmpeg -->|480p| Q3[Quality 480p]
        FFmpeg -->|720p| Q4[Quality 720p]
        FFmpeg -->|1080p| Q5[Quality 1080p]
    end
    
    Q1 -->|10. Upload HLS| MinIO
    Q2 -->|10| MinIO
    Q3 -->|10| MinIO
    Q4 -->|10| MinIO
    Q5 -->|10| MinIO
    
    Transcode -->|11. Generate Master Playlist| FFmpeg
    FFmpeg -->|12. master.m3u8| MinIO
    
    Transcode -->|13. Update Status: ready| D1
    Transcode -->|14. Update HLS URL| D1
    
    Transcode -->|15. Trigger Subtitle Task| RQ2[Redis Queue]
    
    Thumbnails -->|16. Extract Frames| FFmpeg
    FFmpeg -->|17. Thumbnail Images| MinIO
    Thumbnails -->|18. Update Thumbnails| D1
    
    Watermark -->|19. Apply Watermark Filter| FFmpeg
    FFmpeg -->|20. Watermarked Video| MinIO
    
    Archive -->|21. Download Segments| Temp[Temp Storage]
    Temp -->|22. Segments| Archive
    
    Archive -->|23. Concatenate Segments| FFmpeg
    FFmpeg -->|24. Full Video| Archive
    
    Archive -->|25. Upload Archive| MinIO
    Archive -->|26. Create Video Record| D1
    Archive -->|27. Link Stream to Video| D1
    
    CW -->|28. Task Complete| RQ
    CW -->|29. Update Task Status| Redis[(Redis)]
    
    style CW fill:#e1f5ff
    style D1 fill:#fff4e1
    style MinIO fill:#fff4e1
    style RQ fill:#ffe1e1
    style Redis fill:#fff4e1
```

## DFD Уровень 3: Внутренняя логика Search Service

```mermaid
graph TD
    Request[HTTP Request] -->|1| API[FastAPI Router]
    API -->|2| Controller[Controller Layer]
    
    subgraph Endpoints
        Controller -->|GET /search| Search[Search]
        Controller -->|POST /index| Index[Index Video]
        Controller -->|DELETE /index| DeleteIndex[Delete from Index]
        Controller -->|GET /subtitles| Subtitles[Get Subtitles]
    end
    
    Search -->|3| Service[Service Layer]
    Service -->|4| BuildQuery[Build Elasticsearch Query]
    
    subgraph Параметры поиска
        BuildQuery -->|q| QueryText[Search Text]
        BuildQuery -->|tags| TagsFilter[Tags Filter]
        BuildQuery -->|date_range| DateFilter[Date Range]
        BuildQuery -->|duration| DurationFilter[Duration Filter]
    end
    
    BuildQuery -->|5| ESQuery[Elasticsearch Query]
    ESQuery -->|6| ES[Elasticsearch]
    
    ES -->|7 Search Index| Index[Search Index]
    Index -->|8 Results| ES
    ES -->|9 Hits with Scores| Service
    
    Service -->|10| FilterByAccess[Filter by Access]
    FilterByAccess -->|11 Get User Permissions| AS[Auth Service]
    AS -->|12 Permissions| FilterByAccess
    FilterByAccess -->|13 Filtered Results| Service
    
    Service -->|14| GetVideoMetadata[Get Metadata]
    GetVideoMetadata -->|15 Query| D1[(PostgreSQL)]
    D1 -->|16 Video Data| Service
    
    Service -->|17| FormatResponse[Format Response]
    FormatResponse -->|18 JSON| API
    API -->|19 Response| Client[Client]
    
    Index -->|20| Service
    Service -->|21 GetVideoData| D1
    D1 -->|22 Video Data| Service
    
    Service -->|23 GetSubtitles| D1
    D1 -->|24 Subtitles| Service
    
    Service -->|25| BuildDocument[Build ES Document]
    BuildDocument -->|26 Index Document| ES
    ES -->|27 Indexed| Service
    
    Subtitles -->|28| Service
    Service -->|29 GetSubtitles| D1
    D1 -->|30 WebVTT| Service
    Service -->|31| ParseWebVTT[Parse WebVTT]
    ParseWebVTT -->|32 Subtitle Entries| Service
    Service -->|33 Response| API
    
    DeleteIndex -->|34| Service
    Service -->|35 Delete Document| ES
    ES -->|36 Deleted| Service
    
    style API fill:#e1f5ff
    style Service fill:#e1f5ff
    style ES fill:#e1f5ff
    style D1 fill:#fff4e1
```
