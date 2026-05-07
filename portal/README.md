# DGI Portal

Единая точка входа для всех сервисов Департамента городского имущества Москвы.

## Структура

```
portal/
├── src/
│   └── app/
│       ├── layout.tsx    # Root layout
│       ├── page.tsx      # Landing page with services
│       └── globals.css   # Global styles
├── package.json
├── next.config.js        # Next.js config with rewrites
├── tailwind.config.ts    # Tailwind config
└── Dockerfile            # Production build
```

## Development

```bash
# Install dependencies
npm install

# Run dev server (port 3001)
npm run dev

# Or with Docker
cd infrastructure/docker
docker-compose -f docker-compose.dev.yml up portal-dev
```

## Services

| Service | Status | URL |
|---------|--------|-----|
| Video Hosting | Active | http://localhost:3000 |
| Messenger | Coming Soon | - |
| Dashboard | Coming Soon | - |
| Tech Support | Coming Soon | - |

## Integration

Portal redirects authenticated users to appropriate services via JWT tokens.

## Production

```bash
docker build -t dgi-portal .
docker run -p 3001:3001 dgi-portal
```
