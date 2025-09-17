import time
import logging
import os
import pickle

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cache-manager")

# Define constants first - important to avoid NameError
DEFAULT_CACHE_TTL = 3600  # 1 hour cache duration

# File paths for persistent cache storage
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
AFFILIATE_CACHE_FILE = os.path.join(CACHE_DIR, 'affiliate_cache.pkl')
CLIENT_CACHE_FILE = os.path.join(CACHE_DIR, 'client_cache.pkl')

# Ensure cache directory exists
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)
    logger.info(f"Created cache directory: {CACHE_DIR}")

# Cache dictionaries
affiliate_cache = {}
client_info_cache = {}


# Load caches from disk if they exist
def load_caches():
    """Load cached data from disk files"""
    global affiliate_cache, client_info_cache
    try:
        if os.path.exists(AFFILIATE_CACHE_FILE):
            with open(AFFILIATE_CACHE_FILE, 'rb') as f:
                affiliate_cache = pickle.load(f)
                logger.info(f"Loaded affiliate cache with {len(affiliate_cache)} entries")
                
        if os.path.exists(CLIENT_CACHE_FILE):
            with open(CLIENT_CACHE_FILE, 'rb') as f:
                client_info_cache = pickle.load(f)
                logger.info(f"Loaded client cache with {len(client_info_cache)} entries")
    except Exception as e:
        logger.error(f"Error loading cache files: {e}")
        # If there was an error loading, use empty dictionaries
        affiliate_cache = {}
        client_info_cache = {}


# Clean expired entries
def clean_expired_entries():
    """Remove expired entries from both caches"""
    current_time = time.time()
    affiliate_removed = 0
    client_removed = 0
    
    # Clean expired affiliate entries
    keys_to_remove = []
    for key, (data, timestamp) in affiliate_cache.items():
        if current_time - timestamp > DEFAULT_CACHE_TTL:
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        del affiliate_cache[key]
        affiliate_removed += 1
    
    # Clean expired client entries
    keys_to_remove = []
    for key, (data, timestamp) in client_info_cache.items():
        if current_time - timestamp > DEFAULT_CACHE_TTL:
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        del client_info_cache[key]
        client_removed += 1
    
    if affiliate_removed > 0 or client_removed > 0:
        logger.info(f"Cleaned {affiliate_removed} expired affiliate entries and {client_removed} expired client entries")


# Save caches to disk
def save_caches():
    """Save caches to disk and clean expired entries"""
    clean_expired_entries()
    
    try:
        with open(AFFILIATE_CACHE_FILE, 'wb') as f:
            pickle.dump(affiliate_cache, f)
            
        with open(CLIENT_CACHE_FILE, 'wb') as f:
            pickle.dump(client_info_cache, f)
            
        logger.info(f"Saved caches to disk: {len(affiliate_cache)} affiliate entries, {len(client_info_cache)} client entries")
    except Exception as e:
        logger.error(f"Error saving cache files: {e}")


# Get affiliate from cache
def get_affiliate_from_cache(phone_number, ttl=DEFAULT_CACHE_TTL):
    """
    Get affiliate information from cache if it exists and isn't expired
    Args:
        phone_number (str): The phone number used as cache key
        ttl (int): Time to live in seconds
    Returns:
        dict or None: Cached affiliate information or None if not found/expired
    """
    # Normalize phone number to string
    phone_number = str(phone_number).strip()
    
    # Try direct lookup first
    if phone_number in affiliate_cache:
        data, timestamp = affiliate_cache[phone_number]
        age = time.time() - timestamp
        if age < ttl:
            logger.info(f"Cache HIT for affiliate: {phone_number}")
            return data
        else:
            logger.info(f"Cache EXPIRED for affiliate: {phone_number}")
            return None
            
    # Check for special format keys (like 'ids:1:21')
    if phone_number.startswith('ids:'):
        # For ids: format keys, only do exact matching
        logger.info(f"Cache MISS for affiliate with ID format: {phone_number}")
        return None
    
    # Try to match phone number by digits
    for key in affiliate_cache.keys():
        # Skip keys that use the ids: format
        if key.startswith('ids:'):
            continue
            
        # Check if phone numbers match after stripping all non-digits
        key_digits = ''.join(filter(str.isdigit, key))
        phone_digits = ''.join(filter(str.isdigit, phone_number))
        
        # Check if the last 10 digits match
        if key_digits and phone_digits and (key_digits[-10:] == phone_digits[-10:] or key_digits == phone_digits):
            data, timestamp = affiliate_cache[key]
            age = time.time() - timestamp
            
            if age < ttl:
                logger.info(f"Cache HIT for affiliate with phone number match: {phone_number} ↔ {key}")
                return data
            
    logger.info(f"Cache MISS for affiliate: {phone_number}")
    return None


# Store affiliate in cache
def store_affiliate_in_cache(phone_number, affiliate_data):
    """
    Store affiliate information in cache with timestamp
    Args:
        phone_number (str): The phone number to use as cache key
        affiliate_data (dict): The affiliate data to cache
    """
    # Normalize phone number unless it's using the special 'ids:' format
    phone_number = str(phone_number).strip()
    
    # Store with current timestamp
    current_time = time.time()
    affiliate_cache[phone_number] = (affiliate_data, current_time)
    
    # Save cache to disk for persistence between calls
    save_caches()
    
    logger.info(f"Stored affiliate in cache: {phone_number}")
    
    # For phone numbers (not special formats), also store a normalized version
    if not phone_number.startswith('ids:'):
        # Store a normalized version with only digits
        normalized_key = ''.join(filter(str.isdigit, phone_number))
        if normalized_key and normalized_key != phone_number:
            # Only store if it's different from the original key
            affiliate_cache[normalized_key] = (affiliate_data, current_time)
            logger.info(f"Also stored normalized affiliate key: {normalized_key}")
            save_caches()


# Get client from cache
def get_client_from_cache(phone_number, affiliate_id, family_id, ttl=DEFAULT_CACHE_TTL):
    """
    Get client information from cache if it exists and isn't expired
    Args:
        phone_number (str): The client's phone number
        affiliate_id (str): The affiliate ID
        family_id (str): The family ID
        ttl (int): Time to live in seconds
    Returns:
        dict or None: Cached client information or None if not found/expired
    """
    # Normalize inputs
    phone_number = str(phone_number).strip()
    affiliate_id = str(affiliate_id).strip()
    family_id = str(family_id).strip()
    
    # Create the standard cache key
    cache_key = f"{phone_number}:{affiliate_id}:{family_id}"
    
    # Try direct lookup first
    if cache_key in client_info_cache:
        data, timestamp = client_info_cache[cache_key]
        age = time.time() - timestamp
        if age < ttl:
            logger.info(f"Cache HIT for client: {cache_key}")
            return data
        else:
            logger.info(f"Cache EXPIRED for client: {cache_key}")
            return None
    
    # Try to match by phone number digits
    for key in client_info_cache.keys():
        try:
            cached_phone, cached_affiliate, cached_family = key.split(':')
            
            # Check if affiliate and family IDs match
            if cached_affiliate == affiliate_id and cached_family == family_id:
                # Check if phone numbers match after stripping all non-digits
                cached_phone_digits = ''.join(filter(str.isdigit, cached_phone))
                search_phone_digits = ''.join(filter(str.isdigit, phone_number))
                
                # Check if the last 10 digits match
                if cached_phone_digits[-10:] == search_phone_digits[-10:] or cached_phone_digits == search_phone_digits:
                    data, timestamp = client_info_cache[key]
                    age = time.time() - timestamp
                    
                    if age < ttl:
                        logger.info(f"Cache HIT for client with phone number match: {phone_number} ↔ {cached_phone}")
                        return data
                    
        except (ValueError, IndexError):
            # Skip keys that don't have the expected format
            continue
    
    logger.info(f"Cache MISS for client: {cache_key}")
    return None


# Store client in cache
def store_client_in_cache(phone_number, affiliate_id, family_id, client_data):
    """
    Store client information in cache with timestamp
    Args:
        phone_number (str): The client's phone number
        affiliate_id (str): The affiliate ID
        family_id (str): The family ID
        client_data (dict): The client data to cache
    """
    # Normalize inputs
    phone_number = str(phone_number).strip()
    affiliate_id = str(affiliate_id).strip()
    family_id = str(family_id).strip()
    
    # Create the standard cache key
    cache_key = f"{phone_number}:{affiliate_id}:{family_id}"
    
    # Store with current timestamp
    current_time = time.time()
    client_info_cache[cache_key] = (client_data, current_time)
    
    # Save cache to disk for persistence between calls
    save_caches()
    
    logger.info(f"Stored client in cache: {cache_key}")
    
    # Also store a normalized version with digits-only phone number
    normalized_phone = ''.join(filter(str.isdigit, phone_number))
    if normalized_phone and normalized_phone != phone_number:
        normalized_key = f"{normalized_phone}:{affiliate_id}:{family_id}"
        client_info_cache[normalized_key] = (client_data, current_time)
        logger.info(f"Also stored normalized client key: {normalized_key}")
        save_caches()


# Clear all caches
def clear_cache():
    """Clear all caches and delete cache files"""
    # Clear in-memory caches
    affiliate_cache.clear()
    client_info_cache.clear()
    
    # Delete cache files
    try:
        if os.path.exists(AFFILIATE_CACHE_FILE):
            os.remove(AFFILIATE_CACHE_FILE)
        if os.path.exists(CLIENT_CACHE_FILE):
            os.remove(CLIENT_CACHE_FILE)
        logger.info("Cleared all caches and removed cache files")
    except Exception as e:
        logger.error(f"Error deleting cache files: {e}")


# Load caches at initialization
load_caches()
logger.info(f"Loaded client cache keys: {list(client_info_cache.keys())}")
logger.info(f"Loaded affiliate cache keys: {list(affiliate_cache.keys())}")
