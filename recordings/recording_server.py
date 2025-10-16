#!/usr/bin/env python3
"""
🎵 IVR Recording Server - Beautiful API for Call Recordings
Serves call recordings via HTTP with comprehensive Swagger documentation
"""

import os
import sys
import glob
from flask import Flask, send_file, request
from flask_restx import Api, Resource, fields, Namespace
from werkzeug.utils import secure_filename
import logging
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration
RECORDINGS_BASE_PATH = "/mnt"
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8080
BASE_URL = "http://localhost:8080"  # Change this to your actual domain/IP

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__)
app.config['RESTX_MASK_SWAGGER'] = False

# API setup with beautiful documentation
api = Api(
    app,
    version='1.0',
    title='🎵 IVR Recording Server API',
    description='''
    <div style="text-align: center; margin: 20px 0;">
        <h2>🎵 Call Recording Management System</h2>
        <p><strong>Secure access to IVR call recordings with comprehensive metadata</strong></p>
    </div>
    
    ## 📋 Overview
    This API provides secure access to call recordings stored in the IVR system. All recordings are stored in GSM format and can be accessed via unique X-Call-ID identifiers.
    
    ## 🔐 Recording Format
    - **File Format**: GSM (Global System for Mobile communications)
    - **File Naming**: `CALLIN-{x_call_id}-{caller}.gsm`
    - **Storage Path**: `/mnt/recordings-{recipient}/`
    
    ## 🎯 Use Cases
    - **Customer Support**: Access call recordings for quality assurance
    - **Compliance**: Retrieve recordings for regulatory requirements  
    - **Analytics**: Download recordings for speech analysis
    - **Integration**: Embed recording URLs in external systems
    
    ## 🚀 Quick Start
    1. Use `/api/v1/recordings/list` to browse available recordings
    2. Get recording info with `/api/v1/recordings/info/{x_call_id}`
    3. Download recordings via `/api/v1/recordings/download/{x_call_id}`
    ''',
    doc='/docs/',
    prefix='/api/v1'
)

# Namespaces for better organization
recordings_ns = Namespace('recordings', description='📁 Recording Management Operations')
health_ns = Namespace('health', description='🏥 System Health & Status')

api.add_namespace(recordings_ns, path='/recordings')
api.add_namespace(health_ns, path='/health')

# 📋 Swagger Models for beautiful documentation
recording_info_model = api.model('RecordingInfo', {
    'x_call_id': fields.String(required=True, description='Unique X-Call-ID identifier', example='1760537340.12727'),
    'caller': fields.String(required=True, description='Caller phone number', example='3854156545'),
    'recipient': fields.String(required=True, description='Recipient/called number', example='2403270505'),
    'filename': fields.String(required=True, description='Recording filename', example='CALLIN-1760537340.12727-3854156545.gsm'),
    'file_size_bytes': fields.Integer(required=True, description='File size in bytes', example=763818),
    'file_size_mb': fields.Float(required=True, description='File size in megabytes', example=0.73),
    'created_time': fields.Float(required=True, description='Unix timestamp when file was created', example=1760537822.401634),
    'modified_time': fields.Float(required=True, description='Unix timestamp when file was last modified', example=1760537822.401634),
    'download_url': fields.String(required=True, description='Direct download URL', example='http://localhost:8080/api/v1/recordings/download/1760537340.12727'),
    'download_url_with_caller': fields.String(required=True, description='Download URL with caller specification', example='http://localhost:8080/api/v1/recordings/download/1760537340.12727/3854156545')
})

recordings_list_model = api.model('RecordingsList', {
    'total_recordings': fields.Integer(required=True, description='Total number of recordings found', example=43),
    'recordings': fields.List(fields.Nested(recording_info_model), description='List of recording information')
})

health_model = api.model('HealthStatus', {
    'status': fields.String(required=True, description='Service health status', example='healthy'),
    'service': fields.String(required=True, description='Service name', example='recording-server'),
    'recordings_base_path': fields.String(required=True, description='Base path for recordings storage', example='/mnt'),
    'total_recordings': fields.Integer(description='Total recordings available', example=43),
    'uptime': fields.String(description='Service uptime', example='2 hours, 15 minutes'),
    'version': fields.String(description='API version', example='1.0')
})

error_model = api.model('Error', {
    'error': fields.String(required=True, description='Error type', example='Not Found'),
    'message': fields.String(required=True, description='Error message', example='Recording not found for X-Call-ID: 1234567890')
})

# 🔧 Helper Functions
def find_recording_file(x_call_id, caller=None):
    """Find recording file by x_call_id and optionally caller"""
    recording_dirs = glob.glob(f"{RECORDINGS_BASE_PATH}/recordings-*")
    
    for recording_dir in recording_dirs:
        recipient = recording_dir.split("/recordings-")[-1]
        
        if caller:
            pattern = f"{recording_dir}/CALLIN-{x_call_id}-{caller}.gsm"
            files = glob.glob(pattern)
        else:
            pattern = f"{recording_dir}/CALLIN-{x_call_id}-*.gsm"
            files = glob.glob(pattern)
        
        if files:
            return files[0], recipient
    
    return None, None

def get_recording_metadata(file_path, x_call_id, recipient):
    """Get comprehensive recording metadata"""
    filename = os.path.basename(file_path)
    file_stats = os.stat(file_path)
    
    # Extract caller from filename
    caller = filename.split('-')[-1].replace('.gsm', '') if '-' in filename else 'unknown'
    
    return {
        "x_call_id": x_call_id,
        "caller": caller,
        "recipient": recipient,
        "filename": filename,
        "file_size_bytes": file_stats.st_size,
        "file_size_mb": round(file_stats.st_size / (1024 * 1024), 2),
        "created_time": file_stats.st_ctime,
        "modified_time": file_stats.st_mtime,
        "download_url": f"{BASE_URL}/api/v1/recordings/download/{x_call_id}",
        "download_url_with_caller": f"{BASE_URL}/api/v1/recordings/download/{x_call_id}/{caller}"
    }

# 🏥 Health Check Endpoints
@health_ns.route('/status')
class HealthCheck(Resource):
    @api.doc('health_check')
    @api.marshal_with(health_model)
    @api.response(200, 'Service is healthy')
    def get(self):
        """🏥 Get service health status and statistics"""
        try:
            # Count total recordings
            total_recordings = 0
            recording_dirs = glob.glob(f"{RECORDINGS_BASE_PATH}/recordings-*")
            for recording_dir in recording_dirs:
                gsm_files = glob.glob(f"{recording_dir}/*.gsm")
                total_recordings += len([f for f in gsm_files if 'CALLIN-' in os.path.basename(f)])
            
            return {
                "status": "healthy",
                "service": "recording-server",
                "recordings_base_path": RECORDINGS_BASE_PATH,
                "total_recordings": total_recordings,
                "uptime": "Service is running",
                "version": "1.0"
            }
        except Exception as e:
            logger.error(f"Health check error: {e}")
            api.abort(500, f"Health check failed: {str(e)}")

# 📁 Recording Management Endpoints
@recordings_ns.route('/list')
class RecordingsList(Resource):
    @api.doc('list_recordings')
    @api.marshal_with(recordings_list_model)
    @api.response(200, 'Successfully retrieved recordings list')
    @api.response(500, 'Internal server error')
    def get(self):
        """📋 List all available call recordings with metadata"""
        try:
            recordings = []
            recording_dirs = glob.glob(f"{RECORDINGS_BASE_PATH}/recordings-*")
            
            for recording_dir in recording_dirs:
                recipient = recording_dir.split("/recordings-")[-1]
                gsm_files = glob.glob(f"{recording_dir}/*.gsm")
                
                for file_path in gsm_files:
                    filename = os.path.basename(file_path)
                    if filename.startswith("CALLIN-"):
                        # Parse filename: CALLIN-{x_call_id}-{caller}.gsm
                        parts = filename.replace("CALLIN-", "").replace(".gsm", "").split("-")
                        if len(parts) >= 2:
                            x_call_id = parts[0]
                            recordings.append(get_recording_metadata(file_path, x_call_id, recipient))
            
            return {
                "total_recordings": len(recordings),
                "recordings": recordings
            }
            
        except Exception as e:
            logger.error(f"Error listing recordings: {e}")
            api.abort(500, f"Failed to list recordings: {str(e)}")

@recordings_ns.route('/info/<string:x_call_id>')
class RecordingInfo(Resource):
    @api.doc('get_recording_info')
    @api.marshal_with(recording_info_model)
    @api.response(200, 'Recording information retrieved successfully')
    @api.response(404, 'Recording not found', error_model)
    @api.response(500, 'Internal server error', error_model)
    def get(self, x_call_id):
        """📄 Get detailed recording information without downloading
        
        Retrieve comprehensive metadata about a specific recording including file size, 
        timestamps, and download URLs without actually downloading the file.
        """
        file_path, recipient = find_recording_file(x_call_id)
        
        if not file_path:
            logger.warning(f"Recording not found for X-Call-ID: {x_call_id}")
            api.abort(404, f"Recording not found for X-Call-ID: {x_call_id}")
        
        if not os.path.exists(file_path):
            logger.error(f"Recording file does not exist: {file_path}")
            api.abort(404, "Recording file not found on disk")
        
        try:
            logger.info(f"Retrieved info for recording: {file_path}")
            return get_recording_metadata(file_path, x_call_id, recipient)
        except Exception as e:
            logger.error(f"Error getting recording metadata for X-Call-ID {x_call_id}: {e}")
            api.abort(500, f"Failed to get recording metadata: {str(e)}")

@recordings_ns.route('/download/<string:x_call_id>')
class RecordingDownload(Resource):
    @api.doc('download_recording')
    @api.response(200, 'Recording file downloaded successfully')
    @api.response(404, 'Recording not found', error_model)
    @api.response(500, 'Internal server error', error_model)
    @api.produces(['audio/gsm'])
    def get(self, x_call_id):
        """⬇️ Download call recording by X-Call-ID
        
        Download the GSM audio file for the specified X-Call-ID. The file will be 
        sent as an attachment with the original filename.
        """
        try:
            file_path, recipient = find_recording_file(x_call_id)
            
            if not file_path:
                logger.warning(f"Recording not found for X-Call-ID: {x_call_id}")
                api.abort(404, f"Recording not found for X-Call-ID: {x_call_id}")
            
            if not os.path.exists(file_path):
                logger.error(f"Recording file does not exist: {file_path}")
                api.abort(404, "Recording file not found on disk")
            
            logger.info(f"Serving recording: {file_path} for X-Call-ID: {x_call_id}")
            
            filename = os.path.basename(file_path)
            return send_file(
                file_path,
                as_attachment=True,
                download_name=filename,
                mimetype='audio/gsm'
            )
            
        except Exception as e:
            logger.error(f"Error serving recording for X-Call-ID {x_call_id}: {e}")
            api.abort(500, f"Failed to serve recording: {str(e)}")

@recordings_ns.route('/download/<string:x_call_id>/<string:caller>')
class RecordingDownloadWithCaller(Resource):
    @api.doc('download_recording_with_caller')
    @api.response(200, 'Recording file downloaded successfully')
    @api.response(404, 'Recording not found', error_model)
    @api.response(500, 'Internal server error', error_model)
    @api.produces(['audio/gsm'])
    def get(self, x_call_id, caller):
        """⬇️ Download call recording by X-Call-ID and caller number
        
        Download the GSM audio file for the specified X-Call-ID and caller combination.
        This provides more precise matching when multiple recordings exist for the same X-Call-ID.
        """
        try:
            file_path, recipient = find_recording_file(x_call_id, caller)
            
            if not file_path:
                logger.warning(f"Recording not found for X-Call-ID: {x_call_id}, Caller: {caller}")
                api.abort(404, f"Recording not found for X-Call-ID: {x_call_id} and caller: {caller}")
            
            if not os.path.exists(file_path):
                logger.error(f"Recording file does not exist: {file_path}")
                api.abort(404, "Recording file not found on disk")
            
            logger.info(f"Serving recording: {file_path} for X-Call-ID: {x_call_id}, Caller: {caller}")
            
            filename = os.path.basename(file_path)
            return send_file(
                file_path,
                as_attachment=True,
                download_name=filename,
                mimetype='audio/gsm'
            )
            
        except Exception as e:
            logger.error(f"Error serving recording for X-Call-ID {x_call_id}, Caller {caller}: {e}")
            api.abort(500, f"Failed to serve recording: {str(e)}")

# 🎨 Custom Error Handlers
@app.errorhandler(404)
def not_found(error):
    return {'error': 'Not Found', 'message': str(error.description)}, 404

@app.errorhandler(500)
def internal_error(error):
    return {'error': 'Internal Server Error', 'message': str(error.description)}, 500

# 🚀 Main Application Entry Point
if __name__ == '__main__':
    logger.info(f"🎵 Starting IVR Recording Server on {SERVER_HOST}:{SERVER_PORT}")
    logger.info(f"📁 Serving recordings from: {RECORDINGS_BASE_PATH}")
    logger.info(f"🌐 Base URL: {BASE_URL}")
    logger.info(f"📚 Swagger Documentation: {BASE_URL}/docs/")
    
    app.run(
        host=SERVER_HOST,
        port=SERVER_PORT,
        debug=False,
        threaded=True
    )
