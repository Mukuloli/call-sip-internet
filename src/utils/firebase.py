import firebase_admin
from firebase_admin import credentials, firestore
from src.utils.logger import logger
import os

# Initialize Firebase (only if credentials file exists)
db = None
try:
    if os.path.exists("credentials.json"):
        cred = credentials.Certificate("credentials.json")
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        logger.info("✅ Firebase initialized successfully")
    else:
        logger.warning("⚠️ Firebase credentials.json not found. Firebase features disabled.")
except Exception as e:
    logger.warning(f"⚠️ Firebase initialization failed: {e}. Firebase features disabled.")

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

