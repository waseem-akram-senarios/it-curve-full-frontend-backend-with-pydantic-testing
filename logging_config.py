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
from timezone_utils import now_eastern, format_file_timestamp

# Thread-local storage for session context
_local = threading.local()

class SessionContextFilter(logging.Filter):
    """Filter to add session context to log records."""
    
    def filter(self, record):
        # Add session_id to the log record if available
        session_id = getattr(_local, 'session_id', 'no-session')
        record.session_id = session_id
        
        # Add call_sid to the log record if available
        call_sid = getattr(_local, 'call_sid', None)
        record.call_sid = call_sid
        
        # Add x_call_id to the log record if available
        x_call_id = getattr(_local, 'x_call_id', None)
        record.x_call_id = x_call_id
        
        # Add transfer_status to the log record if available
        transfer_status = getattr(_local, 'transfer_status', None)
        record.transfer_status = transfer_status
        return True

class CallSpecificHandler(logging.Handler):
    """Handler that automatically routes logs to call-specific files based on call_sid in log records."""
    
    def __init__(self, logs_dir):
        super().__init__()
        self.logs_dir = Path(logs_dir)
        self.calls_dir = self.logs_dir / "calls"
        self.calls_dir.mkdir(parents=True, exist_ok=True)  # Ensure calls directory exists
        self.call_handlers = {}
        self.call_start_times = {}
        self.setLevel(logging.DEBUG)
        
        # Create formatter for call logs
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.setFormatter(formatter)
    
    def emit(self, record):
        """Emit a record to the appropriate call-specific file based on call_sid."""
        # Get call_sid from the record
        call_sid = getattr(record, 'call_sid', None)
        
        # Only create call-specific logs if call_sid is present
        if call_sid is None:
            return
            
        # Create or get handler for this call
        if call_sid not in self.call_handlers:
            timestamp = format_file_timestamp()
            
            # Try to get X-Call-ID for better file naming
            x_call_id = getattr(record, 'x_call_id', None)
            if x_call_id:
                # Include both call_sid and x_call_id in filename
                call_log_file = self.calls_dir / f'call_{call_sid}_{x_call_id}_{timestamp}.log'
            else:
                call_log_file = self.calls_dir / f'call_{call_sid}_{timestamp}.log'
            
            handler = logging.FileHandler(call_log_file, mode='w')
            handler.setLevel(logging.DEBUG)
            handler.setFormatter(self.formatter)
            
            self.call_handlers[call_sid] = handler
            self.call_start_times[call_sid] = now_eastern()
            
            # Log call start
            start_record = logging.LogRecord(
                name='call_logger',
                level=logging.INFO,
                pathname='',
                lineno=0,
                msg=f"=== Call {call_sid} started at {now_eastern()} ===",
                args=(),
                exc_info=None
            )
            handler.emit(start_record)
            
            # Log X-Call-ID if available
            if x_call_id:
                xcall_record = logging.LogRecord(
                    name='call_logger',
                    level=logging.INFO,
                    pathname='',
                    lineno=0,
                    msg=f"=== X-Call-ID: {x_call_id} ===",
                    args=(),
                    exc_info=None
                )
                handler.emit(xcall_record)
        
        # Emit the record to the call-specific handler
        self.call_handlers[call_sid].emit(record)
    
    def cleanup_call(self, call_sid):
        """Clean up handler for a specific call."""
        if call_sid in self.call_handlers:
            handler = self.call_handlers[call_sid]
            
            # Calculate call duration
            start_time = self.call_start_times.get(call_sid, now_eastern())
            duration = now_eastern() - start_time
            
            # Log call end
            end_record = logging.LogRecord(
                name='call_logger',
                level=logging.INFO,
                pathname='',
                lineno=0,
                msg=f"=== Call {call_sid} ended at {now_eastern()} (Duration: {duration}) ===",
                args=(),
                exc_info=None
            )
            handler.emit(end_record)
            
            handler.close()
            del self.call_handlers[call_sid]
            if call_sid in self.call_start_times:
                del self.call_start_times[call_sid]

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
        
        # Create formatter with Call SID, X-Call-ID and Transfer Status support
        def format_with_context(record):
            call_sid_part = f" | Call-SID: {record.call_sid}" if getattr(record, 'call_sid', None) else ""
            x_call_id_part = f" | X-Call-ID: {record.x_call_id}" if getattr(record, 'x_call_id', None) else ""
            
            # Add transfer status indicator
            transfer_status = getattr(record, 'transfer_status', None)
            if transfer_status == 'ENABLED':
                transfer_part = " | 🟢 TRANSFER-ON"
            elif transfer_status == 'DISABLED':
                transfer_part = " | 🔴 TRANSFER-OFF"
            else:
                transfer_part = ""
            
            return f"{record.asctime} - {record.name} - {record.levelname} - [{record.session_id}]{call_sid_part}{x_call_id_part}{transfer_part} - {record.getMessage()}"
        
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
        self.call_handler.addFilter(session_filter)  # Add session filter to get call_sid
        
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
    
    def set_call_sid(self, call_sid: Optional[str] = None):
        """Set the call_sid for the current thread."""
        _local.call_sid = call_sid
        return call_sid
    
    def get_call_sid(self) -> Optional[str]:
        """Get the current call_sid."""
        return getattr(_local, 'call_sid', None)
    
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
    
    def cleanup_call_logs(self, call_sid: str):
        """Clean up call-specific log files for a call."""
        self.call_handler.cleanup_call(call_sid)
    
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

def set_call_sid(call_sid: Optional[str] = None) -> Optional[str]:
    """Convenience function to set call_sid."""
    return get_logger_instance().set_call_sid(call_sid)

def get_call_sid() -> Optional[str]:
    """Convenience function to get current call_sid."""
    return get_logger_instance().get_call_sid()

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

def cleanup_call_logs(call_sid: str):
    """Convenience function to cleanup call-specific logs."""
    get_logger_instance().cleanup_call_logs(call_sid)
