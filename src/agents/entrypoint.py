import asyncio
from datetime import datetime
from livekit import agents, rtc
from livekit.agents import AgentSession, RoomInputOptions, JobContext
from livekit.plugins import google as google_livekit, noise_cancellation
from src.agents.assistant import Assistant
from src.models.state import MyState
from src.utils.logger import logger
from src.api.app import get_active_sessions


# ============================================
# AI AGENT ENTRYPOINT
# ============================================
async def entrypoint(ctx: JobContext):
    session_id = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{ctx.room.name}"
    room_name = ctx.room.name
    
    await asyncio.sleep(0.5)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"🎯 NEW CALL - GEMINI REALTIME")
    logger.info(f"   Room: {room_name}")
    logger.info(f"   Session: {session_id}")
    logger.info(f"   Time: {datetime.now().strftime('%H:%M:%S')}")
    logger.info(f"{'='*60}\n")
    
    assistant = Assistant(room_name)
    state = MyState(session_id)
    
    # Store in active sessions
    active_sessions = get_active_sessions()
    active_sessions[room_name] = state
    
    session = AgentSession(
        llm=google_livekit.realtime.RealtimeModel(
            model="gemini-2.0-flash-exp",
            voice="Puck",
            temperature=0.7,
        ),
        userdata=state
    )

    await session.start(
        room=ctx.room,
        agent=assistant,
        room_input_options=RoomInputOptions(noise_cancellation=noise_cancellation.BVC())
    )

    logger.info(f"✓ Session Started with Gemini Realtime: {session_id}")
    logger.info("🎤 AI is now listening and will greet automatically...")
    
    @ctx.room.on("participant_connected")
    def on_participant_connected(participant: rtc.RemoteParticipant):
        if participant.identity.startswith("agent_"):
            logger.info(f"👤 Human agent joined via browser: {participant.identity}")
            logger.info(f"🚪 AI Agent disconnecting to allow human conversation...")
            
            state.should_disconnect = True
            asyncio.create_task(disconnect_ai_agent(ctx, session))
    
    try:
        while not state.should_disconnect:
            await asyncio.sleep(1)
        
        logger.info(f"✅ AI Agent successfully disconnected from {room_name}")
        
    except Exception as e:
        logger.error(f"Error in AI agent loop: {e}")
    finally:
        active_sessions = get_active_sessions()
        if room_name in active_sessions:
            del active_sessions[room_name]
        logger.info("✓ Session ended")


async def disconnect_ai_agent(ctx: JobContext, session: AgentSession):
    """Gracefully disconnect AI agent when human takes over"""
    try:
        logger.info("🔌 Disconnecting AI Agent...")
        
        await session.aclose()
        await ctx.room.disconnect()
        
        logger.info("✅ AI Agent disconnected - Human agent now active")
        
    except Exception as e:
        logger.error(f"Error disconnecting AI: {e}")

