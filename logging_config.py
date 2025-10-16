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

# Global variable to store current call logger
_current_call_logger = None

class SessionContextFilter(logging.Filter):
    """Filter to add session context to log records."""
    
    def filter(self, record):
        # Add session_id to the log record if available
        session_id = getattr(_local, 'session_id', 'no-session')
        record.session_id = session_id
        
        # Add x_call_id to the log record if available
        x_call_id = getattr(_local, 'x_call_id', None)
        record.x_call_id = x_call_id
        
        # Add transfer_status to the log record if available
        transfer_status = getattr(_local, 'transfer_status', None)
        record.transfer_status = transfer_status
        return True

class CallSpecificHandler(logging.Handler):
    """Handler that routes logs to call-specific files based on current call context."""
    
    def __init__(self, logs_dir):
        super().__init__()
        self.logs_dir = Path(logs_dir)
        self.call_handlers = {}
        self.setLevel(logging.DEBUG)
        
        # Create formatter for call logs
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.setFormatter(formatter)
    
    def emit(self, record):
        """Emit a record to the appropriate call-specific file."""
        global _current_call_logger
        
        # Only log to call-specific file if there's a current call logger set
        if _current_call_logger is None:
            return
            
        # Get the call ID from the current call logger name
        call_id = None
        if hasattr(_current_call_logger, 'name'):
            # Extract call_id from logger name like 'ivr_bot.call_chat-123'
            parts = _current_call_logger.name.split('.')
            if len(parts) > 1 and parts[1].startswith('call_'):
                call_id = parts[1][5:]  # Remove 'call_' prefix
        
        if call_id is None:
            return
            
        # Create or get handler for this call
        if call_id not in self.call_handlers:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            call_log_file = self.logs_dir / f'call_{call_id}_{timestamp}.log'
            
            handler = logging.FileHandler(call_log_file, mode='w')
            handler.setLevel(logging.DEBUG)
            handler.setFormatter(self.formatter)
            
            self.call_handlers[call_id] = handler
            
            # Log call start
            start_record = logging.LogRecord(
                name='call_logger',
                level=logging.INFO,
                pathname='',
                lineno=0,
                msg=f"=== Call {call_id} started at {datetime.now()} ===",
                args=(),
                exc_info=None
            )
            handler.emit(start_record)
        
        # Emit the record to the call-specific handler
        self.call_handlers[call_id].emit(record)
    
    def cleanup_call(self, call_id):
        """Clean up handler for a specific call."""
        if call_id in self.call_handlers:
            handler = self.call_handlers[call_id]
            
            # Log call end
            end_record = logging.LogRecord(
                name='call_logger',
                level=logging.INFO,
                pathname='',
                lineno=0,
                msg=f"=== Call {call_id} ended at {datetime.now()} ===",
                args=(),
                exc_info=None
            )
            handler.emit(end_record)
            
            handler.close()
            del self.call_handlers[call_id]

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
        
        # Create formatter with X-Call-ID and Transfer Status support
        def format_with_context(record):
            x_call_id_part = f" | X-Call-ID: {record.x_call_id}" if getattr(record, 'x_call_id', None) else ""
            
            # Add transfer status indicator
            transfer_status = getattr(record, 'transfer_status', None)
            if transfer_status == 'ENABLED':
                transfer_part = " | 🟢 TRANSFER-ON"
            elif transfer_status == 'DISABLED':
                transfer_part = " | 🔴 TRANSFER-OFF"
            else:
                transfer_part = ""
            
            return f"{record.asctime} - {record.name} - {record.levelname} - [{record.session_id}]{x_call_id_part}{transfer_part} - {record.getMessage()}"
        
        class CustomFormatter(logging.Formatter):
            def format(self, record):
                record.asctime = self.formatTime(record, self.datefmt)
                return format_with_context(record)
        
        formatter = CustomFormatter(datefmt='%Y-%m-%d %H:%M:%S')
        
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
        
        # Call-specific handler
        self.call_handler = CallSpecificHandler(self.logs_dir)
        
        # Add handlers to logger
        self.main_logger.addHandler(main_handler)
        self.main_logger.addHandler(error_handler)
        self.main_logger.addHandler(console_handler)
        self.main_logger.addHandler(self.call_handler)
        
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
    
    def set_x_call_id(self, x_call_id: Optional[str] = None):
        """Set the X-Call-ID for the current thread."""
        _local.x_call_id = x_call_id
        return x_call_id
    
    def get_x_call_id(self) -> Optional[str]:
        """Get the current X-Call-ID."""
        return getattr(_local, 'x_call_id', None)
    
    def set_transfer_status(self, status: Optional[str] = None):
        """Set the transfer status for the current thread."""
        _local.transfer_status = status
        return status
    
    def get_transfer_status(self) -> Optional[str]:
        """Get the current transfer status."""
        return getattr(_local, 'transfer_status', None)
    
    def create_call_logger(self, call_id: str) -> logging.Logger:
        """Create a dedicated logger for a specific call."""
        logger_name = f'call_{call_id}'
        
        if logger_name in self._loggers:
            return self._loggers[logger_name]
        
        # Create call-specific logger as child of main logger
        call_logger = logging.getLogger(f'ivr_bot.{logger_name}')
        call_logger.setLevel(logging.DEBUG)
        
        # Set parent to main logger so it inherits all handlers (including CallSpecificHandler)
        call_logger.parent = self.main_logger
        call_logger.propagate = True
        
        # Store logger reference
        self._loggers[logger_name] = call_logger
        
        return call_logger
    
    def set_current_call_logger(self, call_logger: logging.Logger):
        """Set the current call logger to be used by get_logger calls."""
        global _current_call_logger
        _current_call_logger = call_logger
    
    def get_current_call_logger(self) -> Optional[logging.Logger]:
        """Get the current call logger if set."""
        global _current_call_logger
        return _current_call_logger
    
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
    
    def set_current_call_logger(self, call_logger: logging.Logger):
        """Set the current call logger to be used by get_logger calls."""
        global _current_call_logger
        _current_call_logger = call_logger
    
    def get_current_call_logger(self) -> Optional[logging.Logger]:
        """Get the current call logger if set."""
        global _current_call_logger
        return _current_call_logger
    
    def cleanup_call_logger(self, call_id: str):
        """Clean up resources for a call logger."""
        logger_name = f'call_{call_id}'
        if logger_name in self._loggers:
            # Clean up the call-specific handler
            self.call_handler.cleanup_call(call_id)
            
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

def set_x_call_id(x_call_id: Optional[str] = None) -> Optional[str]:
    """Convenience function to set X-Call-ID."""
    return get_logger_instance().set_x_call_id(x_call_id)

def get_x_call_id() -> Optional[str]:
    """Convenience function to get current X-Call-ID."""
    return get_logger_instance().get_x_call_id()

def set_transfer_status(status: Optional[str] = None) -> Optional[str]:
    """Convenience function to set transfer status."""
    return get_logger_instance().set_transfer_status(status)

def get_transfer_status() -> Optional[str]:
    """Convenience function to get current transfer status."""
    return get_logger_instance().get_transfer_status()

def create_call_logger(call_id: str) -> logging.Logger:
    """Convenience function to create a call logger."""
    return get_logger_instance().create_call_logger(call_id)

def cleanup_call_logger(call_id: str):
    """Convenience function to cleanup a call logger."""
    get_logger_instance().cleanup_call_logger(call_id)

def set_current_call_logger(call_logger: logging.Logger):
    """Convenience function to set the current call logger."""
    get_logger_instance().set_current_call_logger(call_logger)

def get_current_call_logger() -> Optional[logging.Logger]:
    """Convenience function to get the current call logger."""
    return get_logger_instance().get_current_call_logger()
