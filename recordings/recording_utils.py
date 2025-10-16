#!/usr/bin/env python3
"""
Recording utilities for generating URLs and managing recording access
"""

import os
import sys
import glob
import logging
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('recording_utils')

# Configuration - Load from environment variables
RECORDING_API_BASE_URL = os.getenv("RECORDING_API_BASE_URL")
RECORDINGS_BASE_PATH = os.getenv("RECORDINGS_BASE_PATH")

# Log the loaded configuration
logger.info(f"Recording API Base URL loaded from environment: {RECORDING_API_BASE_URL}")
logger.info(f"Recording Base Path loaded from environment: {RECORDINGS_BASE_PATH}")

def generate_reording_path(x_call_id, caller):
    """
    Generate recording path for a given X-Call-ID and optional caller
    
    Args:
        x_call_id (str): The X-Call-ID from the call
        caller (str, optional): The caller phone number
        
    Returns:
        str: Recording path or None if recording not found
    """
    try:
        # First check if recording exists
        if recording_exists(x_call_id, caller):
            path = f"{RECORDINGS_BASE_PATH}/recordings-{caller}/CALLIN-{x_call_id}-{caller}.gsm"
            logger.info(f"Generated recording path: {path} for X-Call-ID: {x_call_id}")
            return path
        else:
            logger.warning(f"Recording not found for X-Call-ID: {x_call_id}, Caller: {caller}")
            return None
            
    except Exception as e:
        logger.error(f"Error generating recording path for X-Call-ID {x_call_id}: {e}")
        return None

def generate_recording_url(x_call_id, caller):
    """
    Generate recording URL for a given X-Call-ID and optional caller
    
    Args:
        x_call_id (str): The X-Call-ID from the call
        caller (str, optional): The caller phone number
        
    Returns:
        str: Recording URL or None if recording not found
    """
    try:
        # First check if recording exists
        if recording_exists(x_call_id, caller):
            url = f"{RECORDING_API_BASE_URL}/recordings-{caller}/CALLIN-{x_call_id}-{caller}.gsm"
            logger.info(f"Generated recording URL: {url} for X-Call-ID: {x_call_id}")
            return url
        else:
            logger.warning(f"Recording not found for X-Call-ID: {x_call_id}, Caller: {caller}")
            return None
            
    except Exception as e:
        logger.error(f"Error generating recording URL for X-Call-ID {x_call_id}: {e}")
        return None

def recording_exists(x_call_id, caller):
    """
    Check if recording file exists for given X-Call-ID and optional caller
    
    Args:
        x_call_id (str): The X-Call-ID from the call
        caller (str, optional): The caller phone number
        
    Returns:
        bool: True if recording exists, False otherwise
    """
    try:
        # Search in all recordings-* directories
        recording_dirs = glob.glob(f"{RECORDINGS_BASE_PATH}/recordings-*")
        
        for recording_dir in recording_dirs:
            if caller:
                pattern = f"{recording_dir}/CALLIN-{x_call_id}-{caller}.gsm"
                files = glob.glob(pattern)
            else:
                pattern = f"{recording_dir}/CALLIN-{x_call_id}-*.gsm"
                files = glob.glob(pattern)
            
            if files and os.path.exists(files[0]):
                logger.debug(f"Recording found: {files[0]} for X-Call-ID: {x_call_id}")
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking recording existence for X-Call-ID {x_call_id}: {e}")
        return False

def get_recording_info(x_call_id, caller):
    """
    Get detailed recording information
    
    Args:
        x_call_id (str): The X-Call-ID from the call
        caller (str, optional): The caller phone number
        
    Returns:
        dict: Recording information or None if not found
    """
    try:
        # Search in all recordings-* directories
        recording_dirs = glob.glob(f"{RECORDINGS_BASE_PATH}/recordings-*")
        
        for recording_dir in recording_dirs:
            recipient = recording_dir.split("/recordings-")[-1]
            
            if caller:
                pattern = f"{recording_dir}/CALLIN-{x_call_id}-{caller}.gsm"
                files = glob.glob(pattern)
            else:
                pattern = f"{recording_dir}/CALLIN-{x_call_id}-*.gsm"
                files = glob.glob(pattern)
            
            if files and os.path.exists(files[0]):
                file_path = files[0]
                filename = os.path.basename(file_path)
                file_stats = os.stat(file_path)
                
                # Extract caller from filename if not provided
                if not caller:
                    caller = filename.split('-')[-1].replace('.gsm', '') if '-' in filename else 'unknown'
                
                info = {
                    "x_call_id": x_call_id,
                    "caller": caller,
                    "recipient": recipient,
                    "filename": filename,
                    "file_path": file_path,
                    "file_size_bytes": file_stats.st_size,
                    "file_size_mb": round(file_stats.st_size / (1024 * 1024), 2),
                    "created_time": file_stats.st_ctime,
                    "modified_time": file_stats.st_mtime,
                    "recording_url": generate_recording_url(x_call_id, caller)
                }
                
                logger.debug(f"Recording info retrieved for X-Call-ID: {x_call_id}")
                return info
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting recording info for X-Call-ID {x_call_id}: {e}")
        return None

def get_expected_recording_filename(x_call_id, caller):
    """
    Generate expected recording filename based on the pattern
    
    Args:
        x_call_id (str): The X-Call-ID from the call
        caller (str): The caller phone number
        
    Returns:
        str: Expected filename
    """
    return f"CALLIN-{x_call_id}-{caller}.gsm"

def get_expected_recording_path(x_call_id, caller, recipient):
    """
    Generate expected recording file path
    
    Args:
        x_call_id (str): The X-Call-ID from the call
        caller (str): The caller phone number
        recipient (str): The recipient/called number
        
    Returns:
        str: Expected file path
    """
    filename = get_expected_recording_filename(x_call_id, caller)
    return f"{RECORDINGS_BASE_PATH}/recordings-{recipient}/{filename}"
