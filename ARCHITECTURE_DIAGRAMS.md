# Архитектурные диаграммы для дипломной работы

## Диаграмма 1: Общая архитектура микросервисной системы

```mermaid
graph TB
    subgraph "Клиентский уровень"
        Web[Web Browser]
        Mobile[Mobile App]
    end
    
    subgraph "Уровень доступа"
        Nginx[Nginx Reverse Proxy<br/>SSL/TLS Termination<br/>Load Balancing]
    end
    
    subgraph "Уровень микросервисов"
        Auth[Auth Service<br/>:8000<br/>FastAPI]
        Video[Video Service<br/>:8001<br/>FastAPI]
        Streaming[Streaming Service<br/>:8002<br/>FastAPI]
        Notification[Notification Service<br/>:8003<br/>FastAPI]
        Search[Search Service<br/>:8004<br/>FastAPI]
        WebSocket[WebSocket Service<br/>:8005<br/>Socket.io]
    end
    
    subgraph "Уровень обработки"
        Celery[Celery Workers<br/>FFmpeg Transcoding]
        Subtitle[Subtitle Workers<br/>Vosk STT]
    end
    
    subgraph "Уровень очередей"
        RabbitMQ[RabbitMQ<br/>Message Broker]
        Redis[Redis<br/>Cache & Queue]
    end
    
    subgraph "Уровень хранения данных"
        PostgreSQL[(PostgreSQL<br/>Relational DB)]
        MinIO[MinIO<br/>Object Storage]
        Elasticsearch[Elasticsearch<br/>Search Engine]
    end
    
    subgraph "Уровень мониторинга"
        Prometheus[Prometheus<br/>Metrics Collection]
        Grafana[Grafana<br/>Visualization]
        AlertManager[AlertManager<br/>Alerting]
    end
    
    subgraph "Внешние системы"
        AD[Active Directory<br/>LDAP]
        ESIA[ЕСИА<br/>OAuth 2.0]
        SMTP[SMTP Server<br/>Email]
    end
    
    Web -->|HTTPS| Nginx
    Mobile -->|HTTPS| Nginx
    
    Nginx -->|/api/auth| Auth
    Nginx -->|/api/video| Video
    Nginx -->|/api/streaming| Streaming
    Nginx -->|/api/notifications| Notification
    Nginx -->|/api/search| Search
    Nginx -->|/ws| WebSocket
    
    Auth -->|JDBC| PostgreSQL
    Video -->|JDBC| PostgreSQL
    Streaming -->|JDBC| PostgreSQL
    Notification -->|JDBC| PostgreSQL
    Search -->|JDBC| PostgreSQL
    
    Video -->|S3 API| MinIO
    Streaming -->|S3 API| MinIO
    Celery -->|S3 API| MinIO
    
    Search -->|HTTP| Elasticsearch
    
    Video -->|AMQP| RabbitMQ
    Streaming -->|AMQP| RabbitMQ
    Notification -->|AMQP| RabbitMQ
    
    Celery -->|AMQP| RabbitMQ
    Subtitle -->|Redis| Redis
    
    Auth -->|Redis| Redis
    Video -->|Redis| Redis
    Streaming -->|Redis| Redis
    
    Auth -->|LDAP| AD
    Auth -->|OAuth 2.0| ESIA
    Notification -->|SMTP| SMTP
    
    Auth -->|Metrics| Prometheus
    Video -->|Metrics| Prometheus
    Streaming -->|Metrics| Prometheus
    Notification -->|Metrics| Prometheus
    Search -->|Metrics| Prometheus
    
    Prometheus -->|Alerts| AlertManager
    Prometheus -->|Data| Grafana
    
    style Nginx fill:#e1f5ff
    style Auth fill:#e1f5ff
    style Video fill:#e1f5ff
    style Streaming fill:#e1f5ff
    style Notification fill:#e1f5ff
    style Search fill:#e1f5ff
    style WebSocket fill:#e1f5ff
    style PostgreSQL fill:#fff4e1
    style MinIO fill:#fff4e1
    style Elasticsearch fill:#fff4e1
    style RabbitMQ fill:#ffe1e1
    style Redis fill:#ffe1e1
    style Prometheus fill:#e1ffe1
    style Grafana fill:#e1ffe1
```

## Диаграмма 2: Схема развертывания инфраструктуры

```mermaid
graph TB
    subgraph "Интернет"
        User[Пользователи]
        Cloudflare[Cloudflare CDN<br/>DDoS Protection]
    end
    
    subgraph "Выделенный сервер<br/>Selectel"
        subgraph "ОС: Ubuntu 22.04 LTS"
            subgraph "Docker Engine"
                subgraph "Сеть: video_network"
                    subgraph "Микросервисы"
                        AuthC[auth-service<br/>:8000]
                        VideoC[video-service<br/>:8001]
                        StreamingC[streaming-service<br/>:8002]
                        NotifC[notification-service<br/>:8003]
                        SearchC[search-service<br/>:8004]
                        WSC[websocket-service<br/>:8005]
                    end
                    
                    subgraph "Фоновые задачи"
                        CW[celery-worker<br/>Transcoding]
                        SW[subtitle-worker<br/>STT]
                    end
                    
                    subgraph "Инфраструктурные сервисы"
                        DB[postgres:15<br/>:5432]
                        RedisC[redis:7<br/>:6379]
                        RabbitC[rabbitmq:4<br/>:5672]
                        MinIOC[minio<br/>:9000]
                        ESC[elasticsearch:8<br/>:9200]
                    end
                    
                    subgraph "Reverse Proxy"
                        NginxC[nginx:alpine<br/>:80, :443, :1935]
                    end
                    
                    subgraph "Мониторинг"
                        PromC[prometheus<br/>:9090]
                        GrafanaC[grafana<br/>:3000]
                        NodeC[node-exporter<br/>:9100]
                    end
                end
                
                subgraph "Docker Volumes"
                    PGVol[postgres_data]
                    RedisVol[redis_data]
                    RabbitVol[rabbitmq_data]
                    MinIOVol[minio_data]
                    ESVol[elasticsearch_data]
                    NginxVol[nginx_cache]
                    PromVol[prometheus_data]
                    GrafanaVol[grafana_data]
                end
            end
            
            subgraph "RAID 1 Массив"
                Disk1[NVMe 960GB #1]
                Disk2[NVMe 960GB #2]
            end
        end
    end
    
    subgraph "Внешние сервисы"
        AD[Active Directory<br/>dgi.mos.ru]
        REG[REG.RU<br/>DNS]
        SMTP[SMTP Server]
    end
    
    User -->|HTTPS| Cloudflare
    Cloudflare -->|HTTPS| NginxC
    
    NginxC -->|Routing| AuthC
    NginxC -->|Routing| VideoC
    NginxC -->|Routing| StreamingC
    NginxC -->|Routing| NotifC
    NginxC -->|Routing| SearchC
    NginxC -->|Routing| WSC
    
    AuthC -->|Data| DB
    VideoC -->|Data| DB
    StreamingC -->|Data| DB
    NotifC -->|Data| DB
    SearchC -->|Data| DB
    
    VideoC -->|Storage| MinIOC
    StreamingC -->|Storage| MinIOC
    CW -->|Storage| MinIOC
    
    SearchC -->|Index| ESC
    
    VideoC -->|Queue| RabbitC
    CW -->|Queue| RabbitC
    
    AuthC -->|Cache| RedisC
    VideoC -->|Cache| RedisC
    SW -->|Queue| RedisC
    
    AuthC -->|LDAP| AD
    NotifC -->|Email| SMTP
    
    AuthC -->|Metrics| PromC
    VideoC -->|Metrics| PromC
    StreamingC -->|Metrics| PromC
    NotifC -->|Metrics| PromC
    SearchC -->|Metrics| PromC
    NodeC -->|Metrics| PromC
    
    PromC -->|Data| GrafanaC
    
    DB -->|Storage| PGVol
    RedisC -->|Storage| RedisVol
    RabbitC -->|Storage| RabbitVol
    MinIOC -->|Storage| MinIOVol
    ESC -->|Storage| ESVol
    NginxC -->|Storage| NginxVol
    PromC -->|Storage| PromVol
    GrafanaC -->|Storage| GrafanaVol
    
    PGVol -->|RAID 1| Disk1
    PGVol -->|RAID 1| Disk2
    MinIOVol -->|RAID 1| Disk1
    MinIOVol -->|RAID 1| Disk2
    
    User -->|DNS Query| REG
    REG -->|A Record| Cloudflare
    
    style Cloudflare fill:#e1f5ff
    style NginxC fill:#e1f5ff
    style AuthC fill:#e1f5ff
    style VideoC fill:#e1f5ff
    style StreamingC fill:#e1f5ff
    style NotifC fill:#e1f5ff
    style SearchC fill:#e1f5ff
    style WSC fill:#e1f5ff
    style DB fill:#fff4e1
    style MinIOC fill:#fff4e1
    style ESC fill:#fff4e1
    style RedisC fill:#ffe1e1
    style RabbitC fill:#ffe1e1
    style PromC fill:#e1ffe1
    style GrafanaC fill:#e1ffe1
```

## Диаграмма 3: Архитектура безопасности

```mermaid
graph TB
    subgraph "Слои безопасности"
        subgraph "Сетевой уровень"
            Firewall[UFW Firewall<br/>Порты: 22, 80, 443, 1935]
            Cloudflare[Cloudflare<br/>DDoS Protection<br/>WAF]
        end
        
        subgraph "Транспортный уровень"
            SSL[SSL/TLS<br/>Let's Encrypt<br/>TLS 1.3]
        end
        
        subgraph "Уровень приложений"
            JWT[JWT Authentication<br/>Access Token: 15min<br/>Refresh Token: 7days]
            RBAC[RBAC<br/>Role-Based Access Control]
            RateLimit[Rate Limiting<br/>100 req/min]
            InputVal[Input Validation<br/>Pydantic Models]
        end
        
        subgraph "Уровень данных"
            Encryption[Encryption at Rest<br/>AES-256]
            Hashing[Password Hashing<br/>bcrypt]
            SignedURL[Signed URLs<br/>MinIO Presigned]
            Audit[Audit Logging<br/>Все действия]
        end
    end
    
    subgraph "Внешние угрозы"
        DDoS[DDoS атаки]
        SQLi[SQL Injection]
        XSS[XSS атаки]
        CSRF[CSRF атаки]
        AuthBypass[Authentication Bypass]
    end
    
    DDoS -->|Блокируется| Cloudflare
    SQLi -->|Предотвращается| InputVal
    XSS -->|Предотвращается| InputVal
    CSRF -->|Предотвращается| JWT
    AuthBypass -->|Предотвращается| RBAC
    
    Cloudflare -->|Защищённый трафик| Firewall
    Firewall -->|Фильтрованный трафик| SSL
    SSL -->|Зашифрованный трафик| JWT
    JWT -->|Аутентифицированный запрос| RBAC
    RBAC -->|Авторизованный запрос| RateLimit
    RateLimit -->|Валидированный запрос| InputVal
    InputVal -->|Безопасные данные| Encryption
    Encryption -->|Зашифрованные данные| Hashing
    Hashing -->|Хешированные пароли| Audit
    Audit -->|Логи безопасности| SignedURL
    
    style Cloudflare fill:#e1f5ff
    style Firewall fill:#e1f5ff
    style SSL fill:#e1f5ff
    style JWT fill:#e1f5ff
    style RBAC fill:#e1f5ff
    style RateLimit fill:#e1f5ff
    style InputVal fill:#e1f5ff
    style Encryption fill:#fff4e1
    style Hashing fill:#fff4e1
    style Audit fill:#fff4e1
    style SignedURL fill:#fff4e1
```

## Диаграмма 4: CI/CD Pipeline

```mermaid
graph LR
    subgraph "Разработка"
        Dev[Разработчик]
        Git[GitHub Repository]
    end
    
    subgraph "Continuous Integration"
        Push[Push to develop]
        Trigger[GitHub Actions Trigger]
        Lint[Linting<br/>flake8, black]
        TypeCheck[Type Checking<br/>mypy]
        UnitTests[Unit Tests<br/>pytest<br/>Coverage > 80%]
        IntegrationTests[Integration Tests<br/>Testcontainers]
        LoadTests[Load Tests<br/>Locust]
        SecurityScan[Security Scan<br/>Bandit]
    end
    
    subgraph "Build"
        DockerBuild[Build Docker Images]
        DockerPush[Push to Registry]
    end
    
    subgraph "Continuous Deployment"
        DeployStaging[Deploy to Staging<br/>docker-compose]
        SmokeTests[Smoke Tests]
        ManualApproval[Manual Approval<br/>Create Release]
        DeployProd[Deploy to Production<br/>docker-compose]
        HealthCheck[Health Check]
        Rollback[Rollback if Failed]
    end
    
    subgraph "Monitoring"
        Alerts[Alerts<br/>Telegram]
        Logs[Logs<br/>ELK Stack]
    end
    
    Dev -->|Commit| Git
    Git -->|Push| Push
    Push -->|Trigger| Trigger
    
    Trigger --> Lint
    Lint --> TypeCheck
    TypeCheck --> UnitTests
    UnitTests --> IntegrationTests
    IntegrationTests --> LoadTests
    LoadTests --> SecurityScan
    
    SecurityScan -->|Success| DockerBuild
    SecurityScan -->|Failure| NotifyDev[Notify Developer]
    
    DockerBuild --> DockerPush
    DockerPush --> DeployStaging
    
    DeployStaging --> SmokeTests
    SmokeTests -->|Success| ManualApproval
    SmokeTests -->|Failure| Rollback
    
    ManualApproval --> DeployProd
    DeployProd --> HealthCheck
    
    HealthCheck -->|Success| Alerts
    HealthCheck -->|Failure| Rollback
    
    Rollback --> DeployProd
    
    Alerts --> Logs
    
    style Push fill:#e1f5ff
    style Lint fill:#e1f5ff
    style TypeCheck fill:#e1f5ff
    style UnitTests fill:#e1f5ff
    style IntegrationTests fill:#e1f5ff
    style LoadTests fill:#e1f5ff
    style SecurityScan fill:#e1f5ff
    style DockerBuild fill:#fff4e1
    style DockerPush fill:#fff4e1
    style DeployStaging fill:#ffe1e1
    style DeployProd fill:#ffe1e1
```

## Диаграмма 5: Жизненный цикл видео

```mermaid
stateDiagram-v2
    [*] --> Upload: Пользователь загружает видео
    
    state Upload {
        [*] --> InitUpload: POST /upload/init
        InitUpload --> ChunkUpload: Presigned URL
        ChunkUpload --> ChunkUpload: Загрузка чанков
        ChunkUpload --> Complete: POST /complete
    }
    
    Upload --> Uploaded: Загрузка завершена
    
    Uploaded --> Transcoding: Задача в RabbitMQ
    
    state Transcoding {
        [*] --> Download: Скачать из MinIO
        Download --> Analyze: FFprobe анализ
        Analyze --> Transcode: FFmpeg транскодирование
        Transcode --> GenerateHLS: Генерация HLS
        GenerateHLS --> UploadHLS: Загрузка в MinIO
        UploadHLS --> [*]
    }
    
    Transcoding --> SubtitleGeneration: Транскодирование завершено
    
    state SubtitleGeneration {
        [*] --> ExtractAudio: Извлечь аудио
        ExtractAudio --> Recognize: Vosk STT
        Recognize --> GenerateWebVTT: WebVTT формат
        GenerateWebVTT --> [*]
    }
    
    SubtitleGeneration --> Indexing: Субтитры готовы
    
    state Indexing {
        [*] --> BuildDoc: Построить документ
        BuildDoc --> IndexES: Индексация в ES
        IndexES --> [*]
    }
    
    Indexing --> Ready: Видео готово
    
    Ready --> Playing: Пользователь смотрит
    Playing --> Viewing: Статистика просмотра
    
    Viewing --> Ready: Продолжение просмотра
    Viewing --> [*]: Просмотр завершён
    
    Ready --> Deleted: Удаление видео
    
    state Deleted {
        [*] --> DeleteFromDB: Удалить из PostgreSQL
        DeleteFromDB --> DeleteFromES: Удалить из Elasticsearch
        DeleteFromES --> DeleteFromMinIO: Удалить из MinIO
        DeleteFromMinIO --> [*]
    }
    
    Deleted --> [*]
```

## Диаграмма 6: Архитектура стриминга

```mermaid
graph TB
    subgraph "Источник"
        Streamer[Стример]
        OBS[OBS Studio]
    end
    
    subgraph "Приём потока"
        RTMP[Nginx RTMP Module<br/>:1935]
        AuthKey[Проверка stream_key]
    end
    
    subgraph "Транскодирование в реальном времени"
        FFmpeg[FFmpeg Real-time]
        Low[Low Quality<br/>480p]
        Medium[Medium Quality<br/>720p]
        High[High Quality<br/>1080p]
    end
    
    subgraph "HLS Генерация"
        Segments[HLS Segments<br/>2 sec]
        Playlist[Master Playlist]
    end
    
    subgraph "DVR Функционал"
        Buffer[DVR Buffer<br/>24 hours]
        Temp[Temp Storage]
    end
    
    subgraph "Раздача"
        HLS_Server[HLS Server]
        CDN[CDN Nginx Cache]
    end
    
    subgraph "Зрители"
        Viewer1[Зритель 1]
        Viewer2[Зритель 2]
        Viewer3[Зритель N]
    end
    
    subgraph "Архивация"
        ArchiveTask[Archive Task<br/>Celery]
        Concat[Concatenate Segments]
        ArchiveVideo[Archive Video]
        MinIO[MinIO Storage]
    end
    
    Streamer -->|RTMP| OBS
    OBS -->|rtmp://server/live/key| RTMP
    
    RTMP --> AuthKey
    AuthKey -->|Valid| FFmpeg
    
    FFmpeg --> Low
    FFmpeg --> Medium
    FFmpeg --> High
    
    Low --> Segments
    Medium --> Segments
    High --> Segments
    
    Segments --> Buffer
    Buffer --> Temp
    Temp --> Playlist
    
    Playlist --> HLS_Server
    HLS_Server --> CDN
    
    CDN --> Viewer1
    CDN --> Viewer2
    CDN --> Viewer3
    
    Viewer1 -->|DVR Control| HLS_Server
    Viewer2 -->|DVR Control| HLS_Server
    
    RTMP -->|Stream Ended| ArchiveTask
    ArchiveTask --> Concat
    Concat --> Temp
    Temp --> ArchiveVideo
    ArchiveVideo --> MinIO
    
    style RTMP fill:#e1f5ff
    style FFmpeg fill:#e1f5ff
    style HLS_Server fill:#e1f5ff
    style CDN fill:#e1f5ff
    style Buffer fill:#fff4e1
    style Temp fill:#fff4e1
    style MinIO fill:#fff4e1
```

## Диаграмма 7: Архитектура поиска

```mermaid
graph TB
    subgraph "Источники данных"
        VideoDB[(PostgreSQL<br/>videos table)]
        SubtitleDB[(PostgreSQL<br/>subtitles table)]
        TagsDB[(PostgreSQL<br/>tags array)]
    end
    
    subgraph "Индексация"
        IndexTrigger[Trigger<br/>on video update]
        CeleryTask[Celery Task]
        Extractor[Data Extractor]
        TextProcessor[Text Processor<br/>Russian Stemmer]
    end
    
    subgraph "Elasticsearch"
        ESIndex[Videos Index]
        TitleField[title<br/>text]
        DescField[description<br/>text]
        SubtitleField[subtitles<br/>text]
        TagsField[tags<br/>keyword]
        MetaField[metadata<br/>nested]
    end
    
    subgraph "Поиск"
        SearchAPI[Search API]
        QueryBuilder[Query Builder]
        MultiMatch[Multi-match Query]
        Filter[Filter Context]
        Sort[Sort<br/>relevance, date]
        Highlight[Highlight<br/>snippets]
    end
    
    subgraph "Контроль доступа"
        RBAC[RBAC Filter]
        UserPerms[User Permissions]
    end
    
    subgraph "Результаты"
        Results[Search Results]
        Score[Relevance Score]
        Snippets[Highlighted Snippets]
        Timecodes[Subtitle Timecodes]
    end
    
    VideoDB --> IndexTrigger
    SubtitleDB --> IndexTrigger
    TagsDB --> IndexTrigger
    
    IndexTrigger --> CeleryTask
    CeleryTask --> Extractor
    Extractor --> TextProcessor
    TextProcessor --> ESIndex
    
    ESIndex --> TitleField
    ESIndex --> DescField
    ESIndex --> SubtitleField
    ESIndex --> TagsField
    ESIndex --> MetaField
    
    SearchAPI --> QueryBuilder
    QueryBuilder --> MultiMatch
    MultiMatch --> ESIndex
    
    ESIndex --> Filter
    Filter --> RBAC
    RBAC --> UserPerms
    
    Filter --> Sort
    Sort --> Highlight
    Highlight --> Results
    
    Results --> Score
    Results --> Snippets
    Results --> Timecodes
    
    style ESIndex fill:#e1f5ff
    style SearchAPI fill:#e1f5ff
    style QueryBuilder fill:#e1f5ff
    style RBAC fill:#fff4e1
    style Results fill:#fff4e1
```

## Диаграмма 8: Архитектура уведомлений

```mermaid
graph TB
    subgraph "Источники событий"
        VideoReady[Video Ready]
        StreamStart[Stream Started]
        StreamEnd[Stream Ended]
        TranscodeProgress[Transcoding Progress]
        Comment[New Comment]
    end
    
    subgraph "Сервис уведомлений"
        EventListener[Event Listener]
        NotificationDB[(PostgreSQL<br/>notifications)]
        Router[Notification Router]
    end
    
    subgraph "Каналы доставки"
        EmailChannel[Email Channel]
        WSChannel[WebSocket Channel]
        PushChannel[Push Channel<br/>Future]
    end
    
    subgraph "Email канал"
        Template[Email Template]
        SMTP[SMTP Server]
        Queue[Email Queue<br/>RabbitMQ]
        Worker[Email Worker]
    end
    
    subgraph "WebSocket канал"
        WSServer[WebSocket Server]
        Connections[Active Connections]
        Broadcaster[Broadcaster]
    end
    
    subgraph "Клиенты"
        WebClient[Web Client]
        MobileClient[Mobile Client]
    end
    
    subgraph "Отслеживание"
        ReadStatus[Read Status]
        DeliveryStatus[Delivery Status]
    end
    
    VideoReady --> EventListener
    StreamStart --> EventListener
    StreamEnd --> EventListener
    TranscodeProgress --> EventListener
    Comment --> EventListener
    
    EventListener --> NotificationDB
    EventListener --> Router
    
    Router --> EmailChannel
    Router --> WSChannel
    Router --> PushChannel
    
    EmailChannel --> Template
    Template --> Queue
    Queue --> Worker
    Worker --> SMTP
    
    WSChannel --> WSServer
    WSServer --> Connections
    Connections --> Broadcaster
    Broadcaster --> WebClient
    Broadcaster --> MobileClient
    
    WebClient --> ReadStatus
    MobileClient --> ReadStatus
    ReadStatus --> NotificationDB
    
    SMTP --> DeliveryStatus
    DeliveryStatus --> NotificationDB
    
    style EventListener fill:#e1f5ff
    style Router fill:#e1f5ff
    style WSServer fill:#e1f5ff
    style NotificationDB fill:#fff4e1
    style Queue fill:#ffe1e1
```

## Диаграмма 9: Схема базы данных (ERD)

```mermaid
erDiagram
    roles ||--o{ users : "has"
    roles ||--o{ role_permissions : "has"
    permissions ||--o{ role_permissions : "belongs to"
    users ||--o{ videos : "uploads"
    users ||--o{ streams : "creates"
    users ||--o{ video_views : "watches"
    users ||--o{ notifications : "receives"
    users ||--o{ audit_logs : "performs"
    videos ||--o{ subtitles : "has"
    videos ||--o{ search_index : "indexed in"
    videos ||--o{ video_views : "viewed"
    streams ||--|| videos : "archived as"
    
    roles {
        uuid id PK
        varchar name UK
        text description
        uuid parent_id FK
        timestamp created_at
    }
    
    permissions {
        uuid id PK
        varchar name UK
        text description
        timestamp created_at
    }
    
    role_permissions {
        uuid role_id PK,FK
        uuid permission_id PK,FK
    }
    
    users {
        uuid id PK
        varchar username UK
        varchar email UK
        varchar password_hash
        varchar ldap_dn
        varchar esia_id
        uuid role_id FK
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }
    
    videos {
        uuid id PK
        varchar title
        text description
        uuid user_id FK
        interval duration
        varchar resolution
        integer bitrate
        bigint file_size
        varchar minio_key UK
        varchar hls_playlist_url
        varchar status
        boolean is_private
        text[] tags
        timestamp created_at
        timestamp updated_at
    }
    
    streams {
        uuid id PK
        varchar title
        text description
        uuid user_id FK
        varchar rtmp_key UK
        varchar hls_url
        boolean is_live
        timestamp start_time
        timestamp end_time
        uuid archived_video_id FK
        timestamp created_at
    }
    
    video_views {
        uuid id PK
        uuid video_id FK
        uuid user_id FK
        inet ip_address
        text user_agent
        interval watched_duration
        timestamp viewed_at
    }
    
    subtitles {
        uuid id PK
        uuid video_id FK
        varchar language
        text content
        timestamp created_at
    }
    
    search_index {
        uuid id PK
        uuid video_id FK
        tsvector title_vector
        tsvector description_vector
        tsvector subtitles_vector
        tsvector tags_vector
        timestamp updated_at
    }
    
    notifications {
        uuid id PK
        uuid user_id FK
        varchar type
        text message
        boolean is_read
        timestamp created_at
    }
    
    audit_logs {
        uuid id PK
        uuid user_id FK
        varchar action
        varchar resource_type
        uuid resource_id
        jsonb details
        inet ip_address
        text user_agent
        timestamp created_at
    }
```

## Диаграмма 10: Технологический стек

```mermaid
graph TB
    subgraph "Frontend"
        React[React 18]
        NextJS[Next.js 14]
        TypeScript[TypeScript]
        Tailwind[TailwindCSS]
        Shadcn[shadcn/ui]
        HLSjs[HLS.js]
        SocketIO[Socket.io Client]
        ReactQuery[React Query]
    end
    
    subgraph "Backend"
        FastAPI[FastAPI]
        Python[Python 3.11]
        SQLAlchemy[SQLAlchemy]
        Pydantic[Pydantic]
        Celery[Celery]
    end
    
    subgraph "Infrastructure"
        Docker[Docker]
        DockerCompose[Docker Compose]
        Nginx[Nginx]
        Ubuntu[Ubuntu 22.04]
    end
    
    subgraph "Databases"
        PostgreSQL[PostgreSQL 15]
        Redis[Redis 7]
        RabbitMQ[RabbitMQ 4]
        MinIO[MinIO]
        Elasticsearch[Elasticsearch 8]
    end
    
    subgraph "Media Processing"
        FFmpeg[FFmpeg 6]
        Vosk[Vosk STT]
    end
    
    subgraph "Monitoring"
        Prometheus[Prometheus]
        Grafana[Grafana]
        ELK[ELK Stack]
    end
    
    subgraph "DevOps"
        GitHub[GitHub Actions]
        Certbot[Certbot]
        Cloudflare[Cloudflare]
    end
    
    React --> NextJS
    NextJS --> TypeScript
    NextJS --> Tailwind
    Tailwind --> Shadcn
    NextJS --> HLSjs
    NextJS --> SocketIO
    NextJS --> ReactQuery
    
    FastAPI --> Python
    FastAPI --> SQLAlchemy
    FastAPI --> Pydantic
    FastAPI --> Celery
    
    Docker --> DockerCompose
    DockerCompose --> Nginx
    Nginx --> Ubuntu
    
    SQLAlchemy --> PostgreSQL
    Celery --> Redis
    Celery --> RabbitMQ
    FastAPI --> MinIO
    FastAPI --> Elasticsearch
    
    FFmpeg --> Vosk
    
    Prometheus --> Grafana
    Grafana --> ELK
    

    Certbot --> Nginx

    
    style React fill:#e1f5ff
    style FastAPI fill:#e1f5ff
    style Docker fill:#e1f5ff
    style PostgreSQL fill:#fff4e1
    style FFmpeg fill:#ffe1e1
    style Prometheus fill:#e1ffe1
    style GitHub fill:#ffe1e1
```
