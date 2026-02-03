from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import uuid
from typing import Optional, List, Dict

app = FastAPI(
    title="PhantomNet VPN API",
    description="Backend controller for PhantomNet VPN",
    version="1.1.0"
)

# -------------------- CORS --------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- Models --------------------
class ConnectRequest(BaseModel):
    device_id: str
    server_id: str

class DisconnectRequest(BaseModel):
    device_id: str

class StatusResponse(BaseModel):
    connected: bool
    server: Optional[str]
    connected_at: Optional[datetime]
    encryption_level: int

class Server(BaseModel):
    id: str
    name: str
    latency: str

# -------------------- In-memory state (DEV) --------------------
ACTIVE_SESSIONS: Dict[str, Dict] = {}

SERVERS: List[Server] = [
    {"id": "1", "name": "Singapore Nexus", "latency": "32 ms"},
    {"id": "2", "name": "Japan Nexus", "latency": "48 ms"},
    {"id": "3", "name": "United States Nexus", "latency": "120 ms"},
]

# -------------------- Health Check --------------------
@app.get("/")
def health_check():
    return {
        "status": "online",
        "service": "PhantomNet VPN",
        "timestamp": datetime.utcnow()
    }

# -------------------- List Servers --------------------
@app.get("/servers")
def get_servers():
    return {
        "count": len(SERVERS),
        "servers": SERVERS
    }

# -------------------- Connect VPN --------------------
@app.post("/connect")
def connect_vpn(payload: ConnectRequest):
    session_id = str(uuid.uuid4())
    encryption_level = 85  # Default encryption level

    ACTIVE_SESSIONS[payload.device_id] = {
        "session_id": session_id,
        "server_id": payload.server_id,
        "connected_at": datetime.utcnow(),
        "encryption_level": encryption_level,
    }

    return {
        "message": "VPN connected successfully",
        "session_id": session_id,
        "server_id": payload.server_id,
        "encryption_level": encryption_level,
    }

# -------------------- Disconnect VPN --------------------
@app.post("/disconnect")
def disconnect_vpn(payload: DisconnectRequest):
    if payload.device_id not in ACTIVE_SESSIONS:
        raise HTTPException(status_code=400, detail="Device not connected")

    del ACTIVE_SESSIONS[payload.device_id]

    return {
        "message": "VPN disconnected"
    }

# -------------------- VPN Status --------------------
@app.get("/status/{device_id}", response_model=StatusResponse)
def vpn_status(device_id: str):
    session = ACTIVE_SESSIONS.get(device_id)

    if not session:
        return StatusResponse(
            connected=False,
            server=None,
            connected_at=None,
            encryption_level=0,
        )

    server_name = next(
        (s["name"] for s in SERVERS if s["id"] == session["server_id"]),
        None
    )

    return StatusResponse(
        connected=True,
        server=server_name,
        connected_at=session["connected_at"],
        encryption_level=session["encryption_level"],
    )

# -------------------- Select Server --------------------
@app.post("/select_server")
def select_server(payload: ConnectRequest):
    """
    Dynamically select a server.
    If the device is not connected, auto-connect it.
    """
    session = ACTIVE_SESSIONS.get(payload.device_id)

    if not session:
        # Auto-connect device
        session_id = str(uuid.uuid4())
        encryption_level = 85
        ACTIVE_SESSIONS[payload.device_id] = {
            "session_id": session_id,
            "server_id": payload.server_id,
            "connected_at": datetime.utcnow(),
            "encryption_level": encryption_level,
        }
        return {
            "message": f"Device auto-connected and assigned to server {payload.server_id}",
            "session_id": session_id,
            "server_id": payload.server_id,
            "encryption_level": encryption_level,
        }

    # Update server for existing session
    session["server_id"] = payload.server_id
    session["connected_at"] = datetime.utcnow()

    return {
        "message": f"Server updated to {payload.server_id} for device {payload.device_id}"
    }
