import json
from pathlib import Path
from src.utils.logger import logger

# Cache for orders database
_ORDERS_CACHE = None
_ORDERS_CACHE_PATH = None


def get_orders_file_path():
    """Get the path to the orders.json file"""
    # Get the project root directory (parent of src/)
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent
    orders_path = project_root / "data" / "orders.json"
    
    # Fallback: try relative path from current working directory
    if not orders_path.exists():
        orders_path = Path("data/orders.json")
    
    return orders_path


def load_orders_database(force_reload=False):
    """
    Load orders from JSON file with caching.
    
    Args:
        force_reload: If True, reload from file even if cached
    
    Returns:
        Dictionary of orders
    """
    global _ORDERS_CACHE, _ORDERS_CACHE_PATH
    
    orders_path = get_orders_file_path()
    
    # Return cached data if available and file hasn't changed
    if not force_reload and _ORDERS_CACHE is not None:
        if _ORDERS_CACHE_PATH == str(orders_path):
            return _ORDERS_CACHE
    
    if not orders_path.exists():
        error_msg = f"Orders file not found at: {orders_path}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    
    try:
        with open(orders_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Cache the data
            _ORDERS_CACHE = data
            _ORDERS_CACHE_PATH = str(orders_path)
            logger.info(f"✅ Orders database loaded from: {orders_path}")
            logger.info(f"✅ Loaded {len(data)} orders")
            return data
    except json.JSONDecodeError as e:
        error_msg = f"Error parsing JSON file {orders_path}: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e
    except Exception as e:
        error_msg = f"Error loading orders database from {orders_path}: {e}"
        logger.error(error_msg)
        raise


def search_order(order_number: str = None, phone: str = None):
    """
    Search for an order by order number or phone number.
    
    Args:
        order_number: Order number to search for
        phone: Phone number to search for
    
    Returns:
        Order data dictionary if found, None otherwise
    """
    try:
        ORDERS_DATABASE = load_orders_database()
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Failed to load orders database: {e}")
        return None
   
    # Search by order number
    if order_number:
        order_number_clean = order_number.strip().upper()
        if order_number_clean in ORDERS_DATABASE:
            logger.info(f"✓ Order found: {order_number_clean}")
            return ORDERS_DATABASE[order_number_clean]
        else:
            logger.warning(f"✗ Order number not found: {order_number_clean}")
    
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
                logger.info(f"✓ Order found by phone: {phone_clean} -> {order_num}")
                return order_data
        
        logger.warning(f"✗ Order not found for phone: {phone_clean}")
    
    logger.warning("✗ Order not found - no order number or phone provided")
    return None

