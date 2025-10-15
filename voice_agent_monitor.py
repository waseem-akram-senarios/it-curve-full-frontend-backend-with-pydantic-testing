#!/usr/bin/env python3
"""
Voice Agent Monitor and Auto-Recovery System
Monitors the voice agent for connection issues and automatically restarts when needed
"""

import asyncio
import subprocess
import time
import logging
import json
import requests
from datetime import datetime
import os
import signal
import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/senarios/VoiceAgent5withFeNew/logs/voice_agent_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class VoiceAgentMonitor:
    def __init__(self):
        self.agent_process = None
        self.validation_api_process = None
        self.frontend_process = None
        self.restart_count = 0
        self.max_restarts = 5
        self.restart_delay = 30  # seconds
        self.check_interval = 60  # seconds
        self.last_successful_check = None
        
    def is_port_in_use(self, port):
        """Check if a port is in use"""
        try:
            result = subprocess.run(['fuser', f'{port}/tcp'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    def kill_process_on_port(self, port):
        """Kill process running on a specific port"""
        try:
            subprocess.run(['fuser', '-k', f'{port}/tcp'], 
                          capture_output=True, text=True)
            logger.info(f"🛑 Killed process on port {port}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to kill process on port {port}: {e}")
            return False
    
    def check_validation_api(self):
        """Check if validation API is responding"""
        try:
            response = requests.get('http://localhost:8000/docs', timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def check_frontend(self):
        """Check if frontend is responding"""
        try:
            response = requests.get('http://localhost:3000', timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def check_voice_agent_logs(self):
        """Check voice agent logs for errors"""
        log_file = '/home/senarios/VoiceAgent5withFeNew/logs/voice_agent_dev.log'
        try:
            if os.path.exists(log_file):
                # Read last 50 lines
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    recent_lines = lines[-50:] if len(lines) > 50 else lines
                
                # Check for critical errors
                error_indicators = [
                    'APIConnectionError',
                    'RuntimeError.*AgentSession is closing',
                    'AttributeError.*NoneType',
                    'Connection error',
                    'NetworkError',
                    'Task exception was never retrieved'
                ]
                
                for line in recent_lines:
                    for indicator in error_indicators:
                        if indicator.lower() in line.lower():
                            logger.warning(f"⚠️ Found error indicator in logs: {indicator}")
                            return False
                
                return True
            else:
                logger.warning("⚠️ Voice agent log file not found")
                return False
        except Exception as e:
            logger.error(f"❌ Error checking voice agent logs: {e}")
            return False
    
    def start_validation_api(self):
        """Start the validation API"""
        try:
            logger.info("🚀 Starting Validation API...")
            cmd = [
                'python3', '-m', 'uvicorn', 
                'app.main:app', 
                '--host', '0.0.0.0', 
                '--port', '8000', 
                '--log-level', 'warning'
            ]
            
            self.validation_api_process = subprocess.Popen(
                cmd,
                cwd='/home/senarios/VoiceAgent5withFeNew',
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Wait for API to start
            for i in range(10):
                time.sleep(2)
                if self.check_validation_api():
                    logger.info("✅ Validation API started successfully")
                    return True
                logger.info(f"⏳ Waiting for Validation API to start... ({i+1}/10)")
            
            logger.error("❌ Validation API failed to start")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error starting Validation API: {e}")
            return False
    
    def start_voice_agent(self):
        """Start the voice agent"""
        try:
            logger.info("🎤 Starting Voice Agent...")
            
            # Set environment variables
            env = os.environ.copy()
            env.update({
                'LIVEKIT_CACHE_DIR': '/home/senarios/.cache/livekit',
                'LIVEKIT_AGENTS_ENABLE_TURN_DETECTOR': 'true',
                'LIVEKIT_AGENTS_ENABLE_VAD': 'true',
                'LIVEKIT_AGENTS_ENABLE_NOISE_CANCELLATION': 'true',
                'LIVEKIT_AUDIO_SAMPLE_RATE': '16000',
                'LIVEKIT_AUDIO_CHANNELS': '1',
                'LIVEKIT_AUDIO_BIT_DEPTH': '16',
                'LIVEKIT_LOG_LEVEL': 'WARNING',
                'PYTHONOPTIMIZE': '1',
                'PYTHONDONTWRITEBYTECODE': '1'
            })
            
            # Load additional env vars from .env file
            env_file = '/home/senarios/VoiceAgent5withFeNew/.env'
            if os.path.exists(env_file):
                with open(env_file, 'r') as f:
                    for line in f:
                        if line.strip() and not line.startswith('#'):
                            key, value = line.strip().split('=', 1)
                            env[key] = value
            
            cmd = ['python3', 'main.py', 'dev']
            
            self.agent_process = subprocess.Popen(
                cmd,
                cwd='/home/senarios/VoiceAgent5withFeNew/VoiceAgent3/IT_Curves_Bot',
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Wait for agent to start
            for i in range(15):
                time.sleep(3)
                if self.check_voice_agent_logs():
                    logger.info("✅ Voice Agent started successfully")
                    return True
                logger.info(f"⏳ Waiting for Voice Agent to start... ({i+1}/15)")
            
            logger.error("❌ Voice Agent failed to start")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error starting Voice Agent: {e}")
            return False
    
    def start_frontend(self):
        """Start the frontend"""
        try:
            logger.info("🌐 Starting Frontend...")
            
            # Set environment variables
            env = os.environ.copy()
            env['NEXT_PUBLIC_LIVEKIT_URL'] = 'wss://itcurvedev-8eikcg0z.livekit.cloud'
            
            cmd = ['npm', 'run', 'dev']
            
            self.frontend_process = subprocess.Popen(
                cmd,
                cwd='/home/senarios/VoiceAgent5withFeNew/ncs_pvt-virtual-agent-frontend-2c4b49def913',
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Wait for frontend to start
            for i in range(10):
                time.sleep(3)
                if self.check_frontend():
                    logger.info("✅ Frontend started successfully")
                    return True
                logger.info(f"⏳ Waiting for Frontend to start... ({i+1}/10)")
            
            logger.error("❌ Frontend failed to start")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error starting Frontend: {e}")
            return False
    
    def stop_all_services(self):
        """Stop all services"""
        logger.info("🛑 Stopping all services...")
        
        # Kill processes on specific ports
        ports = [8000, 3000, 11000]
        for port in ports:
            if self.is_port_in_use(port):
                self.kill_process_on_port(port)
        
        # Kill specific processes
        processes_to_kill = [
            self.agent_process,
            self.validation_api_process,
            self.frontend_process
        ]
        
        for process in processes_to_kill:
            if process and process.poll() is None:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except:
                    try:
                        process.kill()
                    except:
                        pass
        
        time.sleep(3)
        logger.info("✅ All services stopped")
    
    def restart_all_services(self):
        """Restart all services"""
        logger.info("🔄 Restarting all services...")
        
        # Stop all services first
        self.stop_all_services()
        
        # Wait before restarting
        time.sleep(5)
        
        # Start services in order
        success = True
        
        if not self.start_validation_api():
            success = False
        
        time.sleep(3)
        
        if not self.start_voice_agent():
            success = False
        
        time.sleep(5)
        
        if not self.start_frontend():
            success = False
        
        if success:
            logger.info("✅ All services restarted successfully")
            self.restart_count = 0
            self.last_successful_check = datetime.now()
        else:
            logger.error("❌ Some services failed to restart")
            self.restart_count += 1
        
        return success
    
    def check_all_services(self):
        """Check all services and restart if needed"""
        logger.info("🔍 Checking all services...")
        
        issues = []
        
        # Check validation API
        if not self.check_validation_api():
            issues.append("Validation API not responding")
        
        # Check frontend
        if not self.check_frontend():
            issues.append("Frontend not responding")
        
        # Check voice agent logs
        if not self.check_voice_agent_logs():
            issues.append("Voice agent has errors")
        
        if issues:
            logger.warning(f"⚠️ Issues found: {', '.join(issues)}")
            
            if self.restart_count < self.max_restarts:
                logger.info(f"🔄 Attempting restart ({self.restart_count + 1}/{self.max_restarts})...")
                if self.restart_all_services():
                    logger.info("✅ Services recovered successfully")
                else:
                    logger.error("❌ Service recovery failed")
            else:
                logger.error(f"❌ Maximum restart attempts ({self.max_restarts}) reached")
                logger.error("🆘 Manual intervention required")
        else:
            logger.info("✅ All services are healthy")
            self.restart_count = 0
            self.last_successful_check = datetime.now()
    
    def run_monitor(self):
        """Run the monitoring loop"""
        logger.info("🚀 Starting Voice Agent Monitor...")
        
        # Initial startup
        self.restart_all_services()
        
        try:
            while True:
                self.check_all_services()
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            logger.info("🛑 Monitor stopped by user")
        except Exception as e:
            logger.error(f"❌ Monitor error: {e}")
        finally:
            self.stop_all_services()

if __name__ == "__main__":
    monitor = VoiceAgentMonitor()
    monitor.run_monitor()
