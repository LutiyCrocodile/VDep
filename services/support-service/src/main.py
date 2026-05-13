"""
Support Service - Система технической поддержки ДГИ
FastAPI application with JWT authentication and RBAC
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn
import os
import logging
from datetime import datetime

from .config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Support service started on port {settings.port}")
    yield
    logger.info("Support service shutting down")


app = FastAPI(title="Support Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3002",
        "http://localhost:3004",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str
    service: str


tickets_db = {}


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
            support_perms = user_data.get("services", {}).get("support", {})
            if not support_perms or not support_perms.get("role"):
                raise HTTPException(status_code=403, detail="No access to support")
            
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
    return HealthResponse(status="healthy", service="support")


@app.post("/api/tickets")
async def create_ticket(ticket_data: dict, user: dict = Depends(verify_token)):
    from uuid import uuid4
    
    ticket_id = str(uuid4())
    ticket = {
        "id": ticket_id,
        "subject": ticket_data.get("subject", ""),
        "description": ticket_data.get("description", ""),
        "priority": ticket_data.get("priority", "medium"),
        "status": "open",
        "created_by": user["id"],
        "assigned_to": None,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    
    tickets_db[ticket_id] = ticket
    return ticket


@app.get("/api/tickets")
async def get_tickets(user: dict = Depends(verify_token)):
    role = user.get("services", {}).get("support", {}).get("role")
    user_id = user["id"]
    
    if role in ["admin", "agent"]:
        tickets = list(tickets_db.values())
    else:
        tickets = [t for t in tickets_db.values() if t.get("created_by") == user_id]
    
    return {"tickets": tickets}


@app.get("/api/tickets/{ticket_id}")
async def get_ticket(ticket_id: str, user: dict = Depends(verify_token)):
    if ticket_id not in tickets_db:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    ticket = tickets_db[ticket_id]
    role = user.get("services", {}).get("support", {}).get("role")
    user_id = user["id"]
    
    if role not in ["admin", "agent"] and ticket.get("created_by") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {"ticket": ticket}


@app.put("/api/tickets/{ticket_id}/status")
async def update_ticket_status(ticket_id: str, status: str, user: dict = Depends(verify_token)):
    role = user.get("services", {}).get("support", {}).get("role")
    if role not in ["admin", "agent"]:
        raise HTTPException(status_code=403, detail="Only support agents can update tickets")
    
    if ticket_id not in tickets_db:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    tickets_db[ticket_id]["status"] = status
    return {"status": "updated", "ticket": tickets_db[ticket_id]}


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=int(os.getenv("SUPPORT_SERVICE_PORT", 3004)),
        reload=True
    )
