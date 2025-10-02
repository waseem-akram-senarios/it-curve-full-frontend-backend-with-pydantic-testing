"""
Centralized logging configuration for IVR Directory Bot.
Provides per-call logging with unique session IDs and structured logging.
"""

import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
import threading

# Thread-local storage for session context
_local = threading.local()

class SessionContextFilter(logging.Filter):
    """Filter to add session context to log records."""
    
    def filter(self, record):
        # Add session_id to the log record if available
        session_id = getattr(_local, 'session_id', 'no-session')
        record.session_id = session_id
        return True

class IVRLogger:
    """Centralized logger for IVR Directory Bot with per-call logging support."""
    
    def __init__(self):
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)
        self._loggers = {}
        self._setup_main_logger()
    
    def _setup_main_logger(self):
        """Set up the main application logger."""
        # Create main logger
        self.main_logger = logging.getLogger('ivr_bot')
        self.main_logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers
        self.main_logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(session_id)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Create simple formatter without session_id for main logs
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Add session context filter
        session_filter = SessionContextFilter()
        
        # Main log file handler (without session filter to capture all logs)
        main_handler = logging.FileHandler(self.logs_dir / 'ivr-bot.log', mode='a')
        main_handler.setLevel(logging.DEBUG)
        main_handler.setFormatter(simple_formatter)
        
        # Error log file handler (without session filter to capture all errors)
        error_handler = logging.FileHandler(self.logs_dir / 'ivr-bot-error.log', mode='a')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(simple_formatter)
        
        # Console handler for development
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(session_filter)
        
        # Add handlers to logger
        self.main_logger.addHandler(main_handler)
        self.main_logger.addHandler(error_handler)
        self.main_logger.addHandler(console_handler)
        
        # Suppress noisy third-party loggers
        logging.getLogger('pymongo').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
    
    def set_session_id(self, session_id: Optional[str] = None):
        """Set the session ID for the current thread."""
        if session_id is None:
            session_id = str(uuid.uuid4())[:8]  # Short UUID for readability
        _local.session_id = session_id
        return session_id
    
    def get_session_id(self) -> str:
        """Get the current session ID."""
        return getattr(_local, 'session_id', 'no-session')
    
    def create_call_logger(self, call_id: str) -> logging.Logger:
        """Create a dedicated logger for a specific call."""
        logger_name = f'call_{call_id}'
        
        if logger_name in self._loggers:
            return self._loggers[logger_name]
        
        # Create call-specific logger as child of main logger
        call_logger = logging.getLogger(f'ivr_bot.{logger_name}')
        call_logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers
        call_logger.handlers.clear()
        
        # Create formatter for call logs
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Create call-specific log file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        call_log_file = self.logs_dir / f'call_{call_id}_{timestamp}.log'
        
        # Call-specific file handler
        call_handler = logging.FileHandler(call_log_file, mode='w')
        call_handler.setLevel(logging.DEBUG)
        call_handler.setFormatter(formatter)
        
        call_logger.addHandler(call_handler)
        
        # Set parent to main logger so it also logs to main files
        call_logger.parent = self.main_logger
        call_logger.propagate = True
        
        # Store logger reference
        self._loggers[logger_name] = call_logger
        
        # Log call start
        call_logger.info(f"=== Call {call_id} started at {datetime.now()} ===")
        
        return call_logger
    
    def get_logger(self, name: str = 'ivr_bot') -> logging.Logger:
        """Get a logger instance."""
        if name == 'ivr_bot':
            return self.main_logger
        
        # Create child logger that inherits from main logger
        logger = logging.getLogger(f'ivr_bot.{name}')
        logger.setLevel(logging.DEBUG)
        
        # Set parent to main logger so all logs go to main files
        logger.parent = self.main_logger
        logger.propagate = True
        
        return logger
    
    def cleanup_call_logger(self, call_id: str):
        """Clean up resources for a call logger."""
        logger_name = f'call_{call_id}'
        if logger_name in self._loggers:
            call_logger = self._loggers[logger_name]
            call_logger.info(f"=== Call {call_id} ended at {datetime.now()} ===")
            
            # Close all handlers
            for handler in call_logger.handlers[:]:
                handler.close()
                call_logger.removeHandler(handler)
            
            # Remove from cache
            del self._loggers[logger_name]

# Global logger instance
_logger_instance = None

def get_logger_instance() -> IVRLogger:
    """Get the global logger instance."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = IVRLogger()
    return _logger_instance

def get_logger(name: str = 'ivr_bot') -> logging.Logger:
    """Convenience function to get a logger."""
    return get_logger_instance().get_logger(name)

def set_session_id(session_id: Optional[str] = None) -> str:
    """Convenience function to set session ID."""
    return get_logger_instance().set_session_id(session_id)

def get_session_id() -> str:
    """Convenience function to get current session ID."""
    return get_logger_instance().get_session_id()

def create_call_logger(call_id: str) -> logging.Logger:
    """Convenience function to create a call logger."""
    return get_logger_instance().create_call_logger(call_id)

def cleanup_call_logger(call_id: str):
    """Convenience function to cleanup a call logger."""
    get_logger_instance().cleanup_call_logger(call_id)
