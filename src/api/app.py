from fastapi import FastAPI, WebSocket
from starlette.middleware.cors import CORSMiddleware
from datetime import datetime
from src.models.schemas import AcceptTransfer
from src.utils.logger import logger
from config.settings import LIVEKIT_URL, LIVEKIT_KEY, LIVEKIT_SECRET, BACKEND_API_URL
from livekit import api

# Global state
transfers = []
connected_agents = []
active_sessions = {}

# ============================================
# FASTAPI BACKEND
# ============================================
app = FastAPI(title="AI Call Center Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "status": "running",
        "message": "AI Call Center Backend",
        "agents_online": len(connected_agents),
        "pending_transfers": len([t for t in transfers if t["status"] == "pending"])
    }


@app.websocket("/ws/agent")
async def agent_websocket(websocket: WebSocket):
    """WebSocket for real-time agent notifications"""
    await websocket.accept()
    connected_agents.append(websocket)
    logger.info(f"✅ Agent connected. Total: {len(connected_agents)}")
    
    try:
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to call center"
        })
        
        while True:
            await websocket.receive_text()
            
    except Exception as e:
        logger.info(f"Agent disconnected: {e}")
    finally:
        if websocket in connected_agents:
            connected_agents.remove(websocket)


@app.get("/api/transfers")
async def get_transfers():
    """Get all pending transfers"""
    pending = [t for t in transfers if t["status"] == "pending"]
    return {"transfers": pending, "count": len(pending)}


@app.post("/api/accept-transfer")
async def accept_transfer(request: AcceptTransfer):
    """Accept a transfer and get LiveKit token"""
    transfer = next((t for t in transfers if t["id"] == request.transfer_id), None)
    if not transfer:
        return {"error": "Transfer not found"}
    
    if transfer["status"] != "pending":
        return {"error": "Transfer already handled"}
    
    transfer["status"] = "accepted"
    transfer["agent_name"] = request.agent_name
    transfer["accepted_at"] = datetime.now().isoformat()
    
    room_name = transfer["room_name"]
    
    # Signal AI to disconnect
    if room_name in active_sessions:
        active_sessions[room_name].should_disconnect = True
        logger.info(f"🚪 Signaling AI to leave room {room_name}")
    
    token = api.AccessToken(LIVEKIT_KEY, LIVEKIT_SECRET)
    token.with_identity(f"agent_{request.agent_name}")
    token.with_name(request.agent_name)
    token.with_grants(api.VideoGrants(
        room_join=True,
        room=room_name,
        can_publish=True,
        can_subscribe=True
    ))
    
    jwt_token = token.to_jwt()
    logger.info(f"✅ Transfer accepted by {request.agent_name} for room {room_name}")
    
    for agent_ws in connected_agents:
        try:
            await agent_ws.send_json({
                "type": "transfer_accepted",
                "transfer_id": request.transfer_id
            })
        except:
            pass
    
    return {
        "success": True,
        "token": jwt_token,
        "room_name": room_name,
        "livekit_url": LIVEKIT_URL,
        "caller_info": transfer
    }


@app.post("/api/create-transfer")
async def create_transfer(room_name: str, reason: str = "Customer request"):
    """Create new transfer request"""
    transfer = {
        "id": f"transfer_{len(transfers)}_{datetime.now().strftime('%H%M%S')}",
        "room_name": room_name,
        "reason": reason,
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }
    transfers.append(transfer)
    
    logger.info(f"📞 New transfer created: {transfer['id']}")
    
    for agent_ws in connected_agents:
        try:
            await agent_ws.send_json({
                "type": "incoming_call",
                "transfer": transfer
            })
        except:
            pass
    
    return {"success": True, "transfer": transfer}


@app.post("/api/end-transfer/{transfer_id}")
async def end_transfer(transfer_id: str):
    """Mark transfer as completed"""
    transfer = next((t for t in transfers if t["id"] == transfer_id), None)
    if transfer:
        transfer["status"] = "completed"
        transfer["completed_at"] = datetime.now().isoformat()
        logger.info(f"✅ Transfer completed: {transfer_id}")
    return {"success": True}


# Export global state for use in other modules
def get_transfers_list():
    return transfers


def get_connected_agents():
    return connected_agents


def get_active_sessions():
    return active_sessions

