"""
Dashboard Service - Аналитическая панель ДГИ
FastAPI application with JWT authentication and RBAC
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn
import os
import logging

from .config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Dashboard service started on port {settings.port}")
    yield
    logger.info("Dashboard service shutting down")


app = FastAPI(title="Dashboard Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3002",
        "http://localhost:3003",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str
    service: str


async def verify_token(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    token = auth_header.split(" ")[1]
    
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.auth_service_url}/users/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid token")
            
            user_data = response.json()
            dashboard_perms = user_data.get("services", {}).get("dashboard", {})
            if not dashboard_perms or not dashboard_perms.get("role"):
                raise HTTPException(status_code=403, detail="No access to dashboard")
            
            return user_data
    except ImportError:
        import requests
        response = requests.get(
            f"{settings.auth_service_url}/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid token")
        return response.json()


@app.get("/", response_class=HTMLResponse)
async def root():
    with open("src/static/index.html", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="healthy", service="dashboard")


@app.get("/api/metrics")
async def get_metrics(user: dict = Depends(verify_token)):
    role = user.get("services", {}).get("dashboard", {}).get("role")
    
    metrics = {
        "total_users": 1250,
        "active_users": 847,
        "videos_uploaded": 5420,
        "total_views": 156000,
        "storage_used_gb": 2450,
        "peak_viewers": 342
    }
    
    if role == "viewer":
        metrics = {k: v for k, v in metrics.items() if k in ["total_users", "videos_uploaded"]}
    
    return {"metrics": metrics, "role": role}


@app.get("/api/reports")
async def get_reports(user: dict = Depends(verify_token)):
    role = user.get("services", {}).get("dashboard", {}).get("role")
    
    reports = [
        {"id": "1", "name": "Видео просмотры", "type": "chart", "available": True},
        {"id": "2", "name": "Активность пользователей", "type": "table", "available": role != "viewer"},
        {"id": "3", "name": "Использование хранилища", "type": "chart", "available": True},
    ]
    
    return {"reports": [r for r in reports if r["available"]]}


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=int(os.getenv("DASHBOARD_SERVICE_PORT", 3003)),
        reload=True
    )
