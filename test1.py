import asyncio
import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
import uvicorn
from threading import Thread

from livekit import agents, api, rtc
from livekit.agents import Agent, AgentSession, RoomInputOptions, JobContext, function_tool, RunContext, WorkerOptions, cli
from livekit.plugins import google as google_livekit, noise_cancellation
from livekit.agents import get_job_context
import firebase_admin
from firebase_admin import credentials, firestore

from fastapi import FastAPI, WebSocket
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Load environment
load_dotenv(".env")

# Initialize Firebase
cred = credentials.Certificate("credentials.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Setup logging
logger = logging.getLogger("agent")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

# Configuration
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "wss://your-livekit-url")
LIVEKIT_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_SECRET = os.getenv("LIVEKIT_API_SECRET")
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")

# Sample Orders Database
ORDERS_DATABASE = {
    "VN-20251018-9473": {
        "orderNumber": "VN-20251018-9473",
        "orderDate": "2025-10-18T15:22:00+05:30",
        "customer": {
            "name": "Mukul Oli",
            "email": "mukul@example.com",
            "phone": "9643774764",
        },
        "items": [
            {
                "sku": "TSHIRT-BL-XL",
                "name": "Men's Cotton T-Shirt (Black, XL)",
                "quantity": 1,
                "unitPrice": 599.00,
                "currency": "INR",
            },
            {
                "sku": "WIRELESS-EARBUDS-01",
                "name": "Wireless Earbuds Model A1",
                "quantity": 1,
                "unitPrice": 1499.00,
                "currency": "INR",
            },
        ],
        "payment": {
            "method": "UPI",
            "transactionId": "TXN-785412309",
            "amountPaid": 2098.00,
            "currency": "INR",
            "status": "Paid",
        },
        "shipping": {
            "address": {
                "line1": "12/A MG Road",
                "line2": "Near City Mall",
                "city": "Gurgaon",
                "state": "Haryana",
                "postalCode": "122001",
                "country": "India",
            },
            "carrier": "FastShip Courier",
            "trackingNumber": "FSIN1234567890",
            "trackingUrl": "https://fastship.example/track/FSIN1234567890",
            "status": "In Transit",
            "currentLocation": "Delhi Sorting Center",
            "lastUpdated": "2025-10-21T09:45:00+05:30",
            "estimatedDelivery": "2025-10-28T18:00:00+05:30",
            "deliveryInstructions": "Leave with security if recipient unavailable",
            "delayReason": "Regional flooding due to heavy rainfall",
            "priority_update_requested": False,
        },
        "history": [
            {
                "timestamp": "2025-10-18T16:00:00+05:30",
                "status": "Order Confirmed",
                "note": "Payment received and order confirmed by seller",
            },
            {
                "timestamp": "2025-10-19T10:30:00+05:30",
                "status": "Packed",
                "note": "Warehouse packed the items",
            },
            {
                "timestamp": "2025-10-20T08:15:00+05:30",
                "status": "Shipped",
                "note": "Handover to courier - AWB created",
            },
            {
                "timestamp": "2025-10-21T09:45:00+05:30",
                "status": "In Transit",
                "note": "Arrived at Delhi Sorting Center",
            },
        ],
        "support": {
            "sellerContact": {
                "email": "support@shop-example.com",
                "phone": "+91-11-40001234",
                "hours": "Mon-Sat 09:00-18:00 IST",
            },
            "refundPolicySummary": "Return within 7 days of delivery for eligible items. Refund processed after inspection within 5 working days.",
        },
    },
    "SE12345": {
        "orderNumber": "SE12345",
        "orderDate": "2025-10-15T14:35:00+05:30",
        "customer": {
            "name": "Aarti Singh",
            "phone": "+91-9876543210",
            "email": "aarti.singh@example.com",
        },
        "items": [
            {
                "sku": "SMRTWTCH-AIRPRO",
                "name": "Smartwatch AirPro (Black)",
                "quantity": 1,
                "unitPrice": 4999.00,
                "currency": "INR",
            }
        ],
        "payment": {
            "method": "Credit Card",
            "transactionId": "TXN-987654321",
            "amountPaid": 4999.00,
            "currency": "INR",
            "status": "Paid",
        },
        "shipping": {
            "carrier": "BlueDart",
            "trackingNumber": "BDIN9988776655",
            "status": "Delayed",
            "delayReason": "Heavy rainfall in customer region",
            "originalDeliveryDate": "2025-10-21T18:00:00+05:30",
            "estimatedDelivery": "2025-10-24T18:00:00+05:30",
            "lastUpdated": "2025-10-21T09:45:00+05:30",
            "currentLocation": "Delhi Distribution Center",
            "effectiveEtaWindow": "Before Oct 24, 6 PM IST",
        },
        "delivery": {
            "type": "Express Shipping",
            "charge": 199.00,
            "refundEligibility": "Partial refund applicable for delay over 3 days",
        },
        "statusTimeline": [
            {
                "date": "2025-10-15T16:00:00+05:30",
                "status": "Order Confirmed",
            },
            {
                "date": "2025-10-16T10:30:00+05:30",
                "status": "Packed",
            },
            {
                "date": "2025-10-17T08:15:00+05:30",
                "status": "Shipped",
            },
            {
                "date": "2025-10-21T09:45:00+05:30",
                "status": "Delayed - Weather Impact",
            },
        ],
        "support": {
            "assignedAgent": "Priya (Escalation Team)",
            "followUpDeadline": "2025-10-22T10:30:00+05:30",
            "notes": "Customer expects delivery before weekend. Escalated for priority handling.",
        },
        "service": {
            "express_shipping": True,
            "has_partial_refund_offer": True,
            "escalation_contact": {
                "name": "Priya",
                "role": "Senior Support Specialist",
                "commitment": "Call back within 30 minutes with a delivery update",
            },
        },
    },
}



COMPANY_INFO = {
    "name": "ShopEase Support",
    "support_phone": "+91-11-40001234",
    "email": "support@shop-example.com",
    "working_hours": "Mon-Sat 09:00-18:00 IST",
    "refund_policy": "Return within 7 days of delivery for eligible items. Refund processed after inspection within 5 working days."
}

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

class AcceptTransfer(BaseModel):
    transfer_id: str
    agent_name: str

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

# ============================================
# FIREBASE UTILITIES
# ============================================
# async def search_order_from_firebase(order_number: str = None, phone: str = None):
#     try:
#         orders_ref = db.collection('orders')
        
#         if order_number:
#             order_number_clean = order_number.strip().upper()
#             logger.info(f"🔍 Searching by order number: {order_number_clean}")
            
#             doc = orders_ref.document(order_number_clean).get()
#             if doc.exists:
#                 logger.info(f"✓ Order found: {order_number_clean}")
#                 return doc.to_dict()
            
#             query = orders_ref.where('orderNumber', '==', order_number_clean).limit(1)
#             docs = query.stream()
#             for doc in docs:
#                 logger.info(f"✓ Order found: {order_number_clean}")
#                 return doc.to_dict()
        
#         if phone:
#             phone_clean = phone.replace("+91", "").replace("+", "").replace("-", "").replace(" ", "").strip()
#             logger.info(f"🔍 Searching by phone: {phone_clean}")
            
#             query = orders_ref.where('customer.phone', '==', phone_clean).limit(1)
#             docs = query.stream()
            
#             for doc in docs:
#                 logger.info(f"✓ Order found by phone: {phone_clean}")
#                 return doc.to_dict()
            
#             query = orders_ref.where('customer.phone', '==', f"+91{phone_clean}").limit(1)
#             docs = query.stream()
            
#             for doc in docs:
#                 logger.info(f"✓ Order found by phone: +91{phone_clean}")
#                 return doc.to_dict()
        
#         logger.warning("✗ Order not found in Firebase")
#         return None
        
#     except Exception as e:
#         logger.error(f"Firebase search error: {e}")

#         return None

def search_order(order_number: str = None, phone: str = None):
   
    # Search by order number
    if order_number:
        order_number_clean = order_number.strip().upper()
        if order_number_clean in ORDERS_DATABASE:
            print(f"✓ Order found: {order_number_clean}")
            return ORDERS_DATABASE[order_number_clean]
    
    # Search by phone number
    if phone:
        # Normalize phone number (remove +91, +, -, spaces)
        phone_clean = phone.replace("+91", "").replace("+", "").replace("-", "").replace(" ", "").strip()
        
        # Search through all orders for matching phone
        for order_num, order_data in ORDERS_DATABASE.items():
            customer_phone = order_data.get("customer", {}).get("phone", "")
            # Normalize customer phone the same way
            customer_phone_clean = customer_phone.replace("+91", "").replace("+", "").replace("-", "").replace(" ", "").strip()
            
            if phone_clean == customer_phone_clean:
                print(f"✓ Order found by phone: {phone_clean} -> {order_num}")
                return order_data
    
    print(f"✗ Order not found")
    return None

async def hangup_call():
    ctx = get_job_context()
    if ctx is None:
        return
    await ctx.api.room.delete_room(api.DeleteRoomRequest(room=ctx.room.name))

# ============================================
# AI AGENT STATE & ASSISTANT
# ============================================
class MyState:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.order_data = None
        self.customer_phone = None
        self.customer_order_number = None
        self.transfer_initiated = False
        self.should_disconnect = False

class Assistant(Agent):
    def __init__(self, room_name: str):
        super().__init__(instructions="""
You are a Voice AI Customer Support Assistant for an e-commerce company called ShopEase.

Your goal:
→ Handle customer calls naturally, like a real human support agent.  
→ Detect the customer's sentiment (frustrated, calm, confused, neutral, angry, happy).  
→ Adapt your tone and words instantly based on the sentiment.  
→ Try to resolve the issue first; escalate only when absolutely necessary.  
→ Be confident, concise, and emotionally intelligent.  

CONTEXT:
The AI assistant must detect emotion, attempt to de-escalate frustration, provide clarity, and offer solutions. If the issue cannot be resolved directly, politely escalate to a human support agent.

### SENTIMENT GUIDELINES

**1. Frustrated / Angry**
- Tone: Calm, firm, and reassuring.  
- Acknowledge emotion quickly and move to action.  
- Example phrases:  
  - “I understand this is really inconvenient. Let me check your order right away.”  
  - “I can imagine how that feels. Let’s get this fixed.”  
  - *Avoid repeating apologies.* Focus on solutions.

**2. Calm / Neutral**
- Tone: Friendly and conversational.  
- Example phrases:  
  - “Sure, I can help you with that.”  
  - “Let me check your order status quickly.”

**3. Confused**
- Tone: Clear, patient, step-by-step.  
- Example phrases:  
  - “No worries, I’ll guide you through it.”  
  - “Let’s go one step at a time.”

**4. Happy / Relieved**
- Tone: Cheerful and appreciative.  
- Example phrases:  
  - “I’m really glad to hear that!”  
  - “Happy to help anytime.”

### CONVERSATION FLOW EXAMPLE

**AI:** “Thank you for calling ShopEase Support. This is your virtual assistant. How can I help you today?”  
→ *Detect sentiment from tone and choice of words.*

**Customer:** “Hi, I ordered a smartwatch last week, and it was supposed to arrive yesterday. It’s still not here!”  
→ *Sentiment detected: Frustrated.*

**AI:** “I completely understand how frustrating that must be. Let me quickly check the delivery status for you. May I have your order ID or registered phone number?”  

**If tracking info shows delay:**  
→ “Thanks for waiting. I see the courier has reported a 1-day delay due to weather. It’s expected to arrive by tomorrow. I’ll also notify you by text once it’s out for delivery.”

**If customer remains upset:**  
→ “I can escalate this to our delivery team right now to prioritize your shipment. Would you like me to connect you with them?”


### ESCALATION RULE
Escalate only when:
- The customer explicitly demands to speak to a human, or  
- Sentiment stays strongly negative after two de-escalation attempts.
- appologize that you didnt solve the problem before escalating.

When escalating:
→ “I understand, and I’m connecting you to a senior agent right away who can assist further.”


### STYLE NOTES
✓ Speak like a helpful friend, not a robot.  
✓ Keep responses under 3 sentences.  
✓ Focus on clarity, empathy, and speed.  
✓ Always sound confident that you can solve the issue.  
✓ Use the customer’s sentiment as a live signal to adjust tone and pace.
"""
        )
        self.room_name = room_name

    
    @function_tool
    async def get_order_info(self, ctx: RunContext, order_number: str = None, phone: str = None) -> str:
        """
        Fetch complete order information from database.
        Call this when user provides order number or phone number.
        """
        state: MyState = ctx.session.userdata
        
        # Normalize phone
        if phone:
            phone = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
            if phone.startswith("+91"):
                phone = phone[3:]
            elif phone.startswith("91") and len(phone) == 12:
                phone = phone[2:]
            state.customer_phone = phone
        
        if order_number:
            state.customer_order_number = order_number
        
        # Search database
        logger.info(f"🔍 Searching - Order: {order_number}, Phone: {phone}")
        order_data = search_order(order_number=order_number, phone=phone)
        
        if not order_data:
            return "Order not found. Please check your order number or phone number and try again."
        
        # Store in state
        state.order_data = order_data
        
        # Return complete order info as JSON string for agent to use
        return json.dumps(order_data, indent=2)

    # @function_tool
    # async def get_order_info(self, ctx: RunContext, order_number: str = None, phone: str = None) -> str:
    #     """
    #     Fetch complete order information from Firebase database.
    #     Call this when user provides order number or phone number.
    #     """
    #     state: MyState = ctx.session.userdata
        
    #     # Normalize phone
    #     if phone:
    #         phone = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    #         if phone.startswith("+91"):
    #             phone = phone[3:]
    #         elif phone.startswith("91") and len(phone) == 12:
    #             phone = phone[2:]
    #         state.customer_phone = phone
        
    #     if order_number:
    #         state.customer_order_number = order_number
        
    #     # Search Firebase database
    #     logger.info(f"🔍 Searching Firebase - Order: {order_number}, Phone: {phone}")
    #     order_data = await search_order_from_firebase(order_number=order_number, phone=phone)
        
    #     if not order_data:
    #         return "Order not found in our system. Please check your order number or phone number and try again."
        
    #     # Store in state
    #     state.order_data = order_data
        
    #     # Return complete order info as JSON string for agent to use
    #     return json.dumps(order_data, indent=2)

    @function_tool
    async def transfer_to_human(self, ctx: RunContext, reason: str = "Customer request") -> str:
        """
        Transfer call to human agent via browser (web-based transfer)
        This creates a transfer request that appears in the agent dashboard
        """
        state: MyState = ctx.session.userdata
        
        if state.transfer_initiated:
            return "Transfer already in progress."
        
        state.transfer_initiated = True
        logger.info(f"🔄 Creating browser-based transfer | Reason: {reason}")
        
        try:
            job_ctx = get_job_context()
            room_name = job_ctx.room.name
            
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{BACKEND_API_URL}/api/create-transfer",
                    params={"room_name": room_name, "reason": reason}
                ) as response:
                    data = await response.json()
                    if data.get("success"):
                        transfer_id = data['transfer']['id']
                        logger.info(f"✅ Browser transfer created: {transfer_id}")
                        
                        state.should_disconnect = True
                        
                        return "I'm transferring you to our support specialist now. Please hold for just a moment while they join the call..."
                    else:
                        raise Exception("Failed to create transfer")
                        
        except Exception as e:
            logger.error(f"Browser transfer failed: {e}")
            state.transfer_initiated = False
            return "I apologize for the trouble. Let me try to help you directly instead."
        
    # @function_tool
    # async def transfer_to_human(self, ctx: RunContext, reason: str = "Customer request") -> str:
    #     """Transfer call to human agent"""
    #     state: MyState = ctx.session.userdata
        
    #     if state.transfer_initiated:
    #         return "Transfer already in progress."
        
    #     state.transfer_initiated = True
    #     logger.info(f"🔄 Escalating call | Reason: {reason}")
        
    #     try:
    #         job_ctx = get_job_context()
    #         participant = next((p.identity for p in job_ctx.room.remote_participants.values()), None)
            
    #         if not participant:
    #             logger.error("No participant found for transfer")
    #             return "Unable to transfer at this moment. Please call us at +91-11-40001234."

    #         # Play hold music
    #         try:
    #             hold_music_url = "https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3"
    #             audio_source = rtc.AudioSource(24000, 1)
    #             track = rtc.LocalAudioTrack.create_audio_track("hold_music", audio_source)
    #             await job_ctx.room.local_participant.publish_track(track)
    #             logger.info("🎵 Hold music playing...")
    #             await asyncio.sleep(1)
    #         except Exception as e:
    #             logger.warning(f"Hold music failed: {e}")

    #         await job_ctx.api.sip.transfer_sip_participant(
    #             api.TransferSIPParticipantRequest(
    #                 room_name=job_ctx.room.name,
    #                 participant_identity=participant,
    #                 transfer_to="tel:+917451835976",
    #                 play_dialtone=True
    #             )
    #         )
    #         logger.info(f"✅ Call transferred successfully | Reason: {reason}")
    #         return "Transferring you to our support specialist now. Please stay on the line."
    #     except Exception as e:
    #         logger.error(f"Transfer failed: {e}")
    #         return "I apologize for the trouble. Our specialist will call you back shortly. Thank you for your patience."


    @function_tool
    async def end_call(self, ctx: RunContext) -> str:
        """
        End the call gracefully.
        Call this when:
        - Customer says goodbye/bye/thanks
        - Conversation is complete
        """
        logger.info("📞 Ending call")
        
        goodbye_message = "Thank you for contacting ShopEase Support. Have a great day!"
        
        await asyncio.sleep(1)
        await hangup_call()
        
        return goodbye_message

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
    import time
    time.sleep(2)
    
    # Start AI agent in main thread
    start_ai_agent()