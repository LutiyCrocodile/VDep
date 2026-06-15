# Support Service Dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies directly
RUN pip install --no-cache-dir \
    fastapi==0.135.1 \
    uvicorn[standard]==0.35.0 \
    gunicorn==23.0.0 \
    SQLAlchemy==2.0.43 \
    asyncpg==0.29.0 \
    PyMySQL==1.1.1 \
    python-dotenv==1.1.1 \
    passlib[bcrypt]==1.7.4 \
    python-multipart==0.0.20 \
    jinja2==3.1.6 \
    itsdangerous==2.2.0 \
    httpx==0.27.2 \
    python-jose[cryptography]==3.3.0 \
    ldap3==2.9.1 \
    requests==2.32.3 \
    psutil==5.9.8 \
    prometheus-client==0.21.0

COPY app /app/app

EXPOSE 3004

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3004"]
