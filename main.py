import time
from threading import Thread
import uvicorn
from src.utils.logger import logger
from src.api.app import app
from src.agents.entrypoint import entrypoint
from livekit.agents import cli, WorkerOptions
from config.settings import LIVEKIT_URL

# Initialize Firebase (if credentials exist)
try:
    from src.utils.firebase import db
except ImportError:
    pass


# ============================================
# STARTUP FUNCTIONS
# ============================================
def start_backend_server():
    """Start FastAPI backend server"""
    logger.info("\n🚀 Starting Backend Server...")
    logger.info(f"   URL: http://localhost:8000")
    logger.info(f"   WebSocket: ws://localhost:8000/ws/agent")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")


def start_ai_agent():
    """Start LiveKit AI agent"""
    logger.info("\n🤖 Starting AI Agent with Gemini Realtime...")
    logger.info(f"   LiveKit URL: {LIVEKIT_URL}")
    logger.info(f"   Model: Gemini 2.0 Flash (Realtime)")
    logger.info(f"   Voice: Puck")
    
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))


# ============================================
# MAIN ENTRY POINT
# ============================================
if __name__ == "__main__":
    logger.info("\n" + "="*60)
    logger.info("🏢 AI CALL CENTER - STARTING ALL SERVICES")
    logger.info("="*60)
    logger.info(f"   Backend: FastAPI + WebSocket")
    logger.info(f"   AI Agent: Gemini 2.0 Flash Realtime")
    logger.info(f"   Database: Firebase Firestore")
    logger.info(f"   Transfer: Browser-based (Web Dashboard)")
    logger.info("="*60 + "\n")
    
    # Start backend server in separate thread
    backend_thread = Thread(target=start_backend_server, daemon=True)
    backend_thread.start()
    
    # Give backend time to start
    time.sleep(2)
    
    # Start AI agent in main thread
    start_ai_agent()

