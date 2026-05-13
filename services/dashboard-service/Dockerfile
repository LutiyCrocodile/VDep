# Dashboard Service Dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies directly
RUN pip install --no-cache-dir \
    fastapi==0.115.0 \
    uvicorn[standard]==0.32.0 \
    sqlalchemy==2.0.36 \
    asyncpg==0.29.0 \
    pydantic==2.9.2 \
    pydantic-settings==2.6.0 \
    httpx==0.27.2 \
    bcrypt==4.2.0 \
    python-jose[cryptography]==3.3.0 \
    ldap3==2.9.1 \
    requests==2.32.3 \
    psutil==5.9.8 \
    prometheus-client==0.21.0

COPY src/ ./src/

EXPOSE 3003

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "3003"]
