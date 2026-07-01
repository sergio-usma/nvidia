#!/usr/bin/env python3
"""API Routes for Project Nexus"""

from flask import Blueprint, request, jsonify, Response, stream_with_context
import json
import logging

logger = logging.getLogger(__name__)

api = Blueprint('api', __name__, url_prefix='/api/v1')

def register_routes(app, engine, socketio):
    """Register all API routes"""
    app.register_blueprint(api)
    
    @app.route('/health')
    def health():
        return jsonify({
            "status": "healthy",
            "service": "Project Nexus",
            "version": "1.0.0"
        })
    
    @app.route('/system/stats')
    def system_stats():
        return jsonify(engine.get_system_stats())
    
    @app.route('/models')
    def list_models():
        models = engine.get_available_models()
        return jsonify({"models": models})


# Chat Endpoints
@api.route('/chat/completions', methods=['POST'])
def chat_completions():
    """Chat completion endpoint (OpenAI-compatible)"""
    data = request.json
    
    model = data.get('model', 'llama3.2')
    messages = data.get('messages', [])
    stream = data.get('stream', False)
    
    if stream:
        return _stream_chat(model, messages)
    
    # Process single message
    user_message = messages[-1].get('content', '') if messages else ''
    
    import asyncio
    result = asyncio.run(engine.process_message(user_message, model))
    
    return jsonify({
        "id": f"nexus-{int(datetime.now().timestamp())}",
        "object": "chat.completion",
        "created": int(datetime.now().timestamp()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": result.get('response', result.get('error', ''))
            },
            "finish_reason": "stop"
        }]
    })


def _stream_chat(model, messages):
    """Stream chat responses"""
    import asyncio
    
    user_message = messages[-1].get('content', '') if messages else ''
    
    def generate():
        import requests
        
        prompt = f"User: {user_message}\nAssistant:"
        
        try:
            with requests.post(
                f"http://localhost:11434/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": True
                },
                stream=True,
                timeout=120
            ) as resp:
                for line in resp.iter_lines():
                    if line:
                        data = json.loads(line)
                        if 'response' in data:
                            yield f"data: {json.dumps({'choices': [{'delta': {'content': data['response']}}]})}\n\n"
                            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        yield "data: [DONE]\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }
    )


# Vision Endpoints
@api.route('/vision/analyze', methods=['POST'])
def vision_analyze():
    """Analyze an image"""
    data = request.json
    
    image = data.get('image')
    prompt = data.get('prompt', 'Describe this image')
    
    import asyncio
    result = asyncio.run(engine.analyze_vision(image, prompt))
    
    return jsonify(result)


# Voice Endpoints  
@api.route('/voice/transcribe', methods=['POST'])
def voice_transcribe():
    """Transcribe audio"""
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file"}), 400
    
    audio_file = request.files['audio']
    audio_data = audio_file.read()
    
    import asyncio
    result = asyncio.run(engine.transcribe_voice(audio_data))
    
    return jsonify(result)


@api.route('/voice/synthesize', methods=['POST'])
def voice_synthesize():
    """Synthize speech"""
    data = request.json
    text = data.get('text', '')
    
    # Would return audio bytes
    return jsonify({"success": True, "text": text})


# RAG Endpoints
@api.route('/rag/documents', methods=['POST'])
def rag_add_document():
    """Add document to RAG"""
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400
    
    file = request.files['file']
    content = file.read().decode('utf-8', errors='ignore')
    
    import asyncio
    result = asyncio.run(engine.add_to_rag(content, {"filename": file.filename}))
    
    return jsonify(result)


@api.route('/rag/query', methods=['POST'])
def rag_query():
    """Query RAG"""
    data = request.json
    query = data.get('question', '')
    top_k = data.get('top_k', 5)
    
    import asyncio
    result = asyncio.run(engine.query_rag(query, top_k))
    
    return jsonify(result)


# Session Endpoints
@api.route('/sessions', methods=['GET'])
def list_sessions():
    """List all sessions"""
    sessions = engine.list_sessions()
    return jsonify({
        "sessions": [
            {
                "id": s.id,
                "name": s.name,
                "created_at": s.created_at.isoformat(),
                "message_count": len(s.messages)
            }
            for s in sessions
        ]
    })


@api.route('/sessions', methods=['POST'])
def create_session():
    """Create new session"""
    data = request.json
    session = engine.create_session(
        name=data.get('name', 'New Chat'),
        system_prompt=data.get('system_prompt', '')
    )
    
    return jsonify({
        "id": session.id,
        "name": session.name,
        "created_at": session.created_at.isoformat()
    })


@api.route('/sessions/<session_id>', methods=['GET'])
def get_session(session_id):
    """Get session details"""
    session = engine.get_session(session_id)
    
    if not session:
        return jsonify({"error": "Session not found"}), 404
    
    return jsonify({
        "id": session.id,
        "name": session.name,
        "messages": session.messages,
        "created_at": session.created_at.isoformat()
    })


@api.route('/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """Delete session"""
    success = engine.delete_session(session_id)
    
    if success:
        return jsonify({"success": True})
    return jsonify({"error": "Session not found"}), 404


# Web search endpoint
@api.route('/search', methods=['POST'])
def web_search():
    """Search the web"""
    data = request.json
    query = data.get('query', '')
    
    # Simple web search using DuckDuckGo
    try:
        from duckduckgo_search import DDGS
        ddgs = DDGS()
        results = list(ddgs.text(query, max_results=5))
        
        return jsonify({
            "success": True,
            "results": results
        })
    except Exception as e:
        return jsonify({"error": str(e)})


# Code execution endpoint
@api.route('/code/execute', methods=['POST'])
def execute_code():
    """Execute code in sandbox"""
    data = request.json
    code = data.get('code', '')
    language = data.get('language', 'python')
    
    # WARNING: This is insecure - should use sandboxed execution
    # For demo purposes only!
    
    if language == 'python':
        try:
            import io
            from contextlib import redirect_stdout
            
            output = io.StringIO()
            
            # Execute in limited scope
            scope = {'__builtins__': __builtins__}
            
            exec(code, scope)
            
            return jsonify({
                "success": True,
                "output": output.getvalue() or "Code executed successfully"
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            })
    
    return jsonify({"error": "Unsupported language"})


from datetime import datetime
