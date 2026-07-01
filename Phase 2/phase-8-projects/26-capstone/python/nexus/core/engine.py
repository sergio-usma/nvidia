#!/usr/bin/env python3
"""Nexus Core Engine - Main processing engine for Project Nexus"""

import asyncio
import json
import hashlib
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

@dataclass
class Session:
    """Chat session"""
    id: str
    name: str
    created_at: datetime
    messages: List[Dict] = field(default_factory=list)
    system_prompt: str = ""
    model: str = "llama3.2"
    metadata: Dict = field(default_factory=dict)

@dataclass
class Message:
    """Chat message"""
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)

class Config:
    """Configuration management"""
    
    def __init__(self, config_path: str = None):
        self.ollama_base_url = "http://localhost:11434"
        self.default_model = "llama3.2"
        self.embedding_model = "nomic-embed-text"
        self.vision_model = "llava"
        self.whisper_model = "base"
        self.rag_enabled = True
        self.vision_enabled = True
        self.voice_enabled = True
        self.max_context = 8192
        self.temperature = 0.7
        
        if config_path and Path(config_path).exists():
            self._load_from_file(config_path)
    
    def _load_from_file(self, path: str):
        """Load configuration from YAML file"""
        import yaml
        with open(path) as f:
            config = yaml.safe_load(f)
        
        if 'ollama' in config:
            self.ollama_base_url = config['ollama'].get('base_url', self.ollama_base_url)
            self.default_model = config['ollama'].get('default_model', self.default_model)
            self.embedding_model = config['ollama'].get('embedding_model', self.embedding_model)
            self.vision_model = config['ollama'].get('vision_model', self.vision_model)
        
        if 'whisper' in config:
            self.whisper_model = config['whisper'].get('model', self.whisper_model)
        
        if 'rag' in config:
            self.rag_enabled = config['rag'].get('enabled', True)


class NexusEngine:
    """Main Nexus Engine - coordinates all AI services"""
    
    def __init__(self, config: Config):
        self.config = config
        self.sessions: Dict[str, Session] = {}
        self.ollama_client = None
        self.vector_store = None
        self.whisper_client = None
        self.tts_client = None
        
        self._initialize()
    
    def _initialize(self):
        """Initialize all components"""
        logger.info("Initializing Nexus Engine components...")
        
        # Initialize Ollama client
        try:
            import requests
            self.ollama_client = requests
            logger.info("✓ Ollama client initialized")
        except Exception as e:
            logger.warning(f"Could not initialize Ollama: {e}")
        
        # Initialize vector store
        if self.config.rag_enabled:
            self._init_vector_store()
        
        # Initialize voice services
        if self.config.voice_enabled:
            self._init_voice_services()
        
        # Create default session
        self.create_session("Main Chat")
        
        logger.info("Nexus Engine initialization complete!")
    
    def _init_vector_store(self):
        """Initialize vector store for RAG"""
        try:
            from langchain_community.vectorstores import Chroma
            from langchain_ollama import OllamaEmbeddings
            
            embeddings = OllamaEmbeddings(
                model=self.config.embedding_model,
                base_url=self.config.ollama_base_url
            )
            
            self.vector_store = Chroma(
                persist_directory="./data/chroma",
                embedding_function=embeddings
            )
            logger.info("✓ Vector store initialized")
        except Exception as e:
            logger.warning(f"Vector store init failed: {e}")
    
    def _init_voice_services(self):
        """Initialize voice services"""
        try:
            import whisper
            self.whisper_model = whisper.load_model(
                self.config.whisper_model,
                device="cuda"
            )
            logger.info("✓ Whisper initialized")
        except Exception as e:
            logger.warning(f"Whisper init failed: {e}")
    
    # ==================== Session Management ====================
    
    def create_session(self, name: str = "New Chat", system_prompt: str = "") -> Session:
        """Create a new chat session"""
        session = Session(
            id=str(uuid.uuid4()),
            name=name,
            created_at=datetime.now(),
            system_prompt=system_prompt or "You are Nexus, a helpful AI assistant."
        )
        self.sessions[session.id] = session
        logger.info(f"Created session: {session.id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        return self.sessions.get(session_id)
    
    def list_sessions(self) -> List[Session]:
        """List all sessions"""
        return list(self.sessions.values())
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    # ==================== Chat Processing ====================
    
    async def process_message(
        self, 
        message: str, 
        model: str = None,
        session_id: str = None
    ) -> Dict[str, Any]:
        """Process a chat message and return response"""
        
        model = model or self.config.default_model
        session = self.get_session(session_id) if session_id else list(self.sessions.values())[0]
        
        if not session:
            session = self.create_session()
        
        # Add user message
        session.messages.append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Build prompt
        prompt = self._build_prompt(session, message)
        
        # Call Ollama
        try:
            response = self._call_ollama(prompt, model)
            
            # Add assistant response
            session.messages.append({
                "role": "assistant",
                "content": response,
                "timestamp": datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "response": response,
                "session_id": session.id,
                "model": model
            }
            
        except Exception as e:
            logger.error(f"Chat error: {e}")
            return {
                "success": False,
                "error": str(e),
                "session_id": session.id
            }
    
    async def stream_message(self, message: str, model: str = None):
        """Stream a chat message response"""
        
        model = model or self.config.default_model
        session = list(self.sessions.values())[0]
        
        prompt = self._build_prompt(session, message)
        
        try:
            import requests
            
            with requests.post(
                f"{self.config.ollama_base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": True
                },
                stream=True,
                timeout=120
            ) as resp:
                
                full_response = ""
                
                for line in resp.iter_lines():
                    if line:
                        data = json.loads(line)
                        if 'response' in data:
                            chunk = data['response']
                            full_response += chunk
                            yield {"token": chunk, "done": False}
                
                # Save to session
                session.messages.append({
                    "role": "user",
                    "content": message
                })
                session.messages.append({
                    "role": "assistant",
                    "content": full_response
                })
                
                yield {"token": "", "done": True}
                
        except Exception as e:
            yield {"error": str(e), "done": True}
    
    def _build_prompt(self, session: Session, message: str) -> str:
        """Build prompt from session history"""
        
        prompt = f"System: {session.system_prompt}\n\n"
        
        for msg in session.messages[-10:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            prompt += f"{role.capitalize()}: {content}\n"
        
        prompt += f"User: {message}\nAssistant:"
        
        return prompt
    
    def _call_ollama(self, prompt: str, model: str) -> str:
        """Call Ollama API"""
        import requests
        
        response = requests.post(
            f"{self.config.ollama_base_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.config.temperature,
                    "num_predict": self.config.max_context
                }
            },
            timeout=120
        )
        
        if response.status_code == 200:
            return response.json().get("response", "")
        else:
            raise Exception(f"Ollama error: {response.status_code}")
    
    # ==================== Vision Processing ====================
    
    async def analyze_vision(self, image_data: str, prompt: str = None) -> Dict:
        """Analyze an image"""
        
        if not self.config.vision_enabled:
            return {"error": "Vision not enabled"}
        
        prompt = prompt or "Describe this image in detail."
        
        try:
            # For now, return placeholder - would integrate with vision model
            return {
                "success": True,
                "description": f"[Vision analysis would appear here]\nPrompt: {prompt}",
                "model": self.config.vision_model
            }
        except Exception as e:
            return {"error": str(e)}
    
    # ==================== Voice Processing ====================
    
    async def transcribe_voice(self, audio_data: bytes) -> Dict:
        """Transcribe voice audio"""
        
        if not self.config.voice_enabled:
            return {"error": "Voice not enabled"}
        
        try:
            # Save temp audio
            temp_path = f"/tmp/voice_{uuid.uuid4()}.wav"
            with open(temp_path, 'wb') as f:
                f.write(audio_data)
            
            # Transcribe
            result = self.whisper_model.transcribe(temp_path)
            
            # Cleanup
            Path(temp_path).unlink()
            
            return {
                "success": True,
                "text": result["text"],
                "language": result.get("language", "unknown")
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def synthesize_speech(self, text: str) -> bytes:
        """Synthesize speech from text"""
        
        # Would integrate with Piper TTS
        return b""
    
    # ==================== RAG ====================
    
    async def add_to_rag(self, text: str, metadata: Dict = None) -> Dict:
        """Add document to RAG system"""
        
        if not self.vector_store:
            return {"error": "RAG not initialized"}
        
        try:
            self.vector_store.add_texts(
                texts=[text],
                metadatas=[metadata or {}]
            )
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}
    
    async def query_rag(self, query: str, top_k: int = 5) -> Dict:
        """Query RAG system"""
        
        if not self.vector_store:
            return {"error": "RAG not initialized"}
        
        try:
            docs = self.vector_store.similarity_search(query, k=top_k)
            
            return {
                "success": True,
                "results": [
                    {"content": doc.page_content, "metadata": doc.metadata}
                    for doc in docs
                ]
            }
        except Exception as e:
            return {"error": str(e)}
    
    # ==================== System ====================
    
    def get_system_stats(self) -> Dict:
        """Get system statistics"""
        
        import psutil
        import pynvml
        
        stats = {
            "cpu": {
                "percent": psutil.cpu_percent(),
                "count": psutil.cpu_count()
            },
            "memory": {
                "total": psutil.virtual_memory().total,
                "used": psutil.virtual_memory().used,
                "percent": psutil.virtual_memory().percent
            },
            "disk": {
                "total": psutil.disk_usage('/').total,
                "used": psutil.disk_usage('/').used,
                "percent": psutil.disk_usage('/').percent
            },
            "sessions": len(self.sessions),
            "timestamp": datetime.now().isoformat()
        }
        
        # GPU stats
        try:
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            
            stats["gpu"] = {
                "utilization": util.gpu,
                "memory_used": mem.used,
                "memory_total": mem.total,
                "temperature": temp
            }
        except:
            pass
        
        return stats
    
    def get_available_models(self) -> List[Dict]:
        """Get available models from Ollama"""
        
        try:
            import requests
            resp = requests.get(f"{self.config.ollama_base_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                return resp.json().get("models", [])
        except:
            pass
        
        return []


# Create default instance
engine = None

def get_engine():
    """Get or create engine instance"""
    global engine
    if engine is None:
        engine = NexusEngine(Config())
    return engine
