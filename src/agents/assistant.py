import asyncio
import json
import aiohttp
import yaml
from pathlib import Path
from livekit import agents, rtc, api
from livekit.agents import Agent, RunContext, function_tool
from livekit.agents import get_job_context
from src.models.state import MyState
from src.utils.logger import logger
from src.utils.order_search import search_order
from src.utils.call_utils import hangup_call
from config.settings import BACKEND_API_URL
from src.api.app import get_active_sessions


def load_instructions():
    """Load agent instructions from YAML file"""
    # Get the project root directory (parent of src/)
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent
    instructions_path = project_root / "instructions" / "agent_instructions.yml"
    
    # Fallback: try relative path from current working directory
    if not instructions_path.exists():
        instructions_path = Path("instructions/agent_instructions.yml")
    
    if not instructions_path.exists():
        error_msg = f"Instructions file not found at: {instructions_path}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    
    try:
        with open(instructions_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if not data or "instructions" not in data:
                error_msg = f"Invalid YAML format: 'instructions' key not found in {instructions_path}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            instructions = data.get("instructions", "").strip()
            if not instructions:
                error_msg = f"Instructions are empty in {instructions_path}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            logger.info(f"✅ Instructions loaded from: {instructions_path}")
            return instructions
    except yaml.YAMLError as e:
        error_msg = f"Error parsing YAML file {instructions_path}: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e
    except Exception as e:
        error_msg = f"Error loading instructions from {instructions_path}: {e}"
        logger.error(error_msg)
        raise


class Assistant(Agent):
    def __init__(self, room_name: str):
        instructions = load_instructions()
        super().__init__(instructions=instructions)
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
    #     # Note: When uncommenting this, also uncomment and import:
    #     # from src.utils.firebase import search_order_from_firebase
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

