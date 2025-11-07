import os
from dotenv import load_dotenv

# Load environment
load_dotenv(".env")

# Configuration
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "wss://your-livekit-url")
LIVEKIT_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_SECRET = os.getenv("LIVEKIT_API_SECRET")
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")

