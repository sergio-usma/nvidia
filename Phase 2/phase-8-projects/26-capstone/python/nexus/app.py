#!/usr/bin/env python3
"""
Project Nexus - Core Application
The ultimate unified AI platform for Jetson AGX Orin
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime

from flask import Flask, jsonify, request, session
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Setup paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / os.getenv('DATA_DIR', 'data')
UPLOAD_DIR = DATA_DIR / 'uploads'
LOG_DIR = BASE_DIR / os.getenv('LOG_DIR', 'logs')

# Create directories
DATA_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'nexus.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import core modules
from nexus.core.engine import NexusEngine
from nexus.core.config import Config
from nexus.api import register_routes
from nexus.web import register_web_routes

# Global engine instance
engine = None

def create_app(config_path: str = None) -> Flask:
    """Create and configure the Flask application."""
    
    global engine
    
    app = Flask(__name__,
                template_folder=str(BASE_DIR / 'nexus' / 'web' / 'templates'),
                static_folder=str(BASE_DIR / 'nexus' / 'web' / 'static'))
    
    # Load configuration
    config = Config(config_path or str(BASE_DIR / 'config.yaml'))
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_REQUEST_SIZE', '100MB'))
    app.config['UPLOAD_FOLDER'] = str(UPLOAD_DIR)
    
    # Enable CORS
    CORS(app, 
         resources={r"/api/*": {"origins": "*"}},
         supports_credentials=True)
    
    # Initialize SocketIO
    socketio = SocketIO(app, 
                       cors_allowed_origins="*",
                       async_mode='threading',
                       ping_timeout=30,
                       ping_interval=10)
    
    # Initialize the core engine
    logger.info("Initializing Nexus Engine...")
    engine = NexusEngine(config)
    
    # Register API routes
    register_routes(app, engine, socketio)
    
    # Register web routes
    register_web_routes(app, engine)
    
    # SocketIO events
    register_socket_events(socketio, engine)
    
    logger.info("Project Nexus initialized successfully!")
    
    return app

def register_socket_events(socketio: SocketIO, engine: NexusEngine):
    """Register SocketIO event handlers."""
    
    @socketio.on('connect')
    def handle_connect():
        logger.info(f"Client connected: {request.sid}")
        emit('connected', {'status': 'connected', 'sid': request.sid})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        logger.info(f"Client disconnected: {request.sid}")
    
    @socketio.on('chat_message')
    def handle_chat(data):
        """Handle incoming chat messages."""
        try:
            message = data.get('message', '')
            model = data.get('model', engine.config.default_model)
            session_id = data.get('session_id')
            
            # Process message
            response = asyncio.run(
                engine.process_message(message, model, session_id)
            )
            
            emit('chat_response', response)
            
        except Exception as e:
            logger.error(f"Chat error: {e}")
            emit('error', {'message': str(e)})
    
    @socketio.on('stream_chat')
    def handle_stream_chat(data):
        """Handle streaming chat."""
        try:
            message = data.get('message', '')
            model = data.get('model', engine.config.default_model)
            
            async def generate():
                async for chunk in engine.stream_message(message, model):
                    emit('stream_chunk', chunk)
                emit('stream_done', {'status': 'done'})
            
            asyncio.run(generate())
            
        except Exception as e:
            logger.error(f"Stream error: {e}")
            emit('error', {'message': str(e)})
    
    @socketio.on('vision_analyze')
    def handle_vision(data):
        """Handle vision analysis."""
        try:
            image_data = data.get('image')
            prompt = data.get('prompt', 'Describe this image')
            
            result = asyncio.run(
                engine.analyze_vision(image_data, prompt)
            )
            
            emit('vision_result', result)
            
        except Exception as e:
            logger.error(f"Vision error: {e}")
            emit('error', {'message': str(e)})
    
    @socketio.on('voice_transcribe')
    def handle_voice(data):
        """Handle voice transcription."""
        try:
            audio_data = data.get('audio')
            
            result = asyncio.run(
                engine.transcribe_voice(audio_data)
            )
            
            emit('voice_result', result)
            
        except Exception as e:
            logger.error(f"Voice error: {e}")
            emit('error', {'message': str(e)})
    
    @socketio.on('system_stats')
    def handle_stats():
        """Send system statistics."""
        try:
            stats = engine.get_system_stats()
            emit('system_stats', stats)
        except Exception as e:
            logger.error(f"Stats error: {e}")
    
    @socketio.on('create_session')
    def handle_create_session(data):
        """Create new chat session."""
        try:
            session_data = engine.create_session(
                name=data.get('name', 'New Chat'),
                system_prompt=data.get('system_prompt')
            )
            emit('session_created', session_data)
        except Exception as e:
            emit('error', {'message': str(e)})


# Run application
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Project Nexus - Unified AI Platform')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--config', help='Path to config file')
    
    args = parser.parse_args()
    
    app = create_app(args.config)
    
    # Run with SocketIO
    from flask_socketio import run as socketio_run
    socketio_run(app, 
                 host=args.host, 
                 port=args.port, 
                 debug=args.debug,
                 allow_unsafe_werkzeug=True)
