#!/usr/bin/env python3
"""Web Routes for Project Nexus"""

from flask import Blueprint, render_template, redirect, url_for, session, request
import logging

logger = logging.getLogger(__name__)

web = Blueprint('web', __name__)

def register_web_routes(app, engine):
    """Register web routes"""
    
    @web.route('/')
    def index():
        """Main dashboard"""
        return render_template('index.html')
    
    @web.route('/chat')
    def chat():
        """Chat interface"""
        return render_template('chat.html')
    
    @web.route('/vision')
    def vision():
        """Vision interface"""
        return render_template('vision.html')
    
    @web.route('/voice')
    def voice():
        """Voice interface"""
        return render_template('voice.html')
    
    @web.route('/rag')
    def rag():
        """RAG interface"""
        return render_template('rag.html')
    
    @web.route('/settings')
    def settings():
        """Settings page"""
        return render_template('settings.html')
    
    @web.route('/sessions')
    def sessions_page():
        """Sessions management"""
        return render_template('sessions.html')
    
    @web.route('/monitor')
    def monitor():
        """System monitor"""
        return render_template('monitor.html')
