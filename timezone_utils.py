"""
Timezone utilities for IVR Bot - Centralizes Eastern Time handling across the application
"""
import pytz
from datetime import datetime
from typing import Optional


# Define Eastern timezone constant
EASTERN_TZ = pytz.timezone('US/Eastern')


def now_eastern() -> datetime:
    """
    Get current datetime in Eastern Time
    
    Returns:
        datetime: Current datetime in US/Eastern timezone
    """
    return datetime.now(pytz.utc).astimezone(EASTERN_TZ)


def to_eastern(dt: datetime) -> datetime:
    """
    Convert a datetime to Eastern Time
    
    Args:
        dt: datetime object (can be naive or timezone-aware)
        
    Returns:
        datetime: datetime converted to US/Eastern timezone
    """
    if dt.tzinfo is None:
        # Assume naive datetime is UTC
        dt = pytz.utc.localize(dt)
    return dt.astimezone(EASTERN_TZ)


def format_eastern_timestamp(dt: Optional[datetime] = None, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format datetime as Eastern Time string
    
    Args:
        dt: datetime object (defaults to current time if None)
        format_str: strftime format string
        
    Returns:
        str: Formatted datetime string in Eastern Time
    """
    if dt is None:
        dt = now_eastern()
    elif dt.tzinfo is None:
        # Assume naive datetime is UTC
        dt = pytz.utc.localize(dt).astimezone(EASTERN_TZ)
    else:
        dt = dt.astimezone(EASTERN_TZ)
    
    return dt.strftime(format_str)


def format_eastern_date(dt: Optional[datetime] = None) -> str:
    """
    Format date as Eastern Time string (YYYY-MM-DD)
    
    Args:
        dt: datetime object (defaults to current time if None)
        
    Returns:
        str: Formatted date string in Eastern Time
    """
    return format_eastern_timestamp(dt, "%Y-%m-%d")


def format_eastern_time_12h(dt: Optional[datetime] = None) -> str:
    """
    Format time as Eastern Time string in 12-hour format (HH:MM AM/PM)
    
    Args:
        dt: datetime object (defaults to current time if None)
        
    Returns:
        str: Formatted time string in Eastern Time (12-hour format)
    """
    return format_eastern_timestamp(dt, "%I:%M %p")


def format_eastern_datetime_iso(dt: Optional[datetime] = None) -> str:
    """
    Format datetime as Eastern Time ISO string
    
    Args:
        dt: datetime object (defaults to current time if None)
        
    Returns:
        str: ISO formatted datetime string in Eastern Time
    """
    if dt is None:
        dt = now_eastern()
    elif dt.tzinfo is None:
        # Assume naive datetime is UTC
        dt = pytz.utc.localize(dt).astimezone(EASTERN_TZ)
    else:
        dt = dt.astimezone(EASTERN_TZ)
    
    return dt.isoformat()


def format_file_timestamp(dt: Optional[datetime] = None) -> str:
    """
    Format datetime for use in filenames (YYYYMMDD_HHMMSS)
    
    Args:
        dt: datetime object (defaults to current time if None)
        
    Returns:
        str: Filename-safe timestamp string in Eastern Time
    """
    return format_eastern_timestamp(dt, "%Y%m%d_%H%M%S")


def parse_eastern_datetime(datetime_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """
    Parse a datetime string as Eastern Time
    
    Args:
        datetime_str: datetime string to parse
        format_str: strftime format string used to parse
        
    Returns:
        datetime: Parsed datetime in Eastern timezone
    """
    naive_dt = datetime.strptime(datetime_str, format_str)
    return EASTERN_TZ.localize(naive_dt)


def get_eastern_timezone() -> pytz.BaseTzInfo:
    """
    Get the Eastern timezone object
    
    Returns:
        pytz.BaseTzInfo: US/Eastern timezone object
    """
    return EASTERN_TZ


# Convenience functions for common use cases
def eastern_now_str() -> str:
    """Get current datetime as Eastern Time string (YYYY-MM-DD HH:MM:SS)"""
    return format_eastern_timestamp()


def eastern_today_str() -> str:
    """Get current date as Eastern Time string (YYYY-MM-DD)"""
    return format_eastern_date()


def eastern_time_str() -> str:
    """Get current time as Eastern Time string (HH:MM AM/PM)"""
    return format_eastern_time_12h()
