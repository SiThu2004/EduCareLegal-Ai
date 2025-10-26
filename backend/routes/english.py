
from flask import Blueprint, request, jsonify, session, redirect, url_for
from chains.english_chain import english_chain
from flask import render_template
import os
import datetime
import uuid
from pymongo import MongoClient
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for

english_bp = Blueprint('english_bp', __name__)

# MongoDB connection
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = MongoClient(mongo_uri)
db = client['chatbotDB']
chats_collection = db['chats']

@english_bp.route('/english')
def english_page():
    """English chat page"""
    # if 'email' not in session:
    #     return redirect(url_for('home'))
    return render_template('englishTr.html')

@english_bp.route('/englishcall')
def english_call_page():  
    """English call page"""
    if 'email' not in session:
        return redirect(url_for('home'))
    return render_template('englishcall.html')

@english_bp.route('/chat', methods=['POST'])
def english_chat():
    """Handle chat messages"""
    print(" CHAT ENDPOINT HIT")
    
    # Check if user is logged in
    if 'email' not in session:
        print(" No user in session")
        return jsonify({"reply": "Please login first."}), 401
    
    # Get JSON data
    data = request.get_json()
    print(f" Received data: {data}")
    
    if not data:
        print(" No JSON data received")
        return jsonify({"reply": "Invalid JSON data."}), 400
        
    user_text = data.get("message", "").strip()
    if not user_text:
        print(" Empty message")
        return jsonify({"reply": "Please send a message."})

    # Process chat message
    try:
        print(f" Processing message: {user_text}")
        result = english_chain.invoke({"text": user_text})
        bot_reply = result.content
        print(f" Bot reply: {bot_reply[:50]}...")
    except Exception as e:
        print(f" Chain error: {e}")
        bot_reply = "I'm sorry, I encountered an error processing your message."

    # Save to database
    try:
        user_email = session.get('email')
        session_id = session.get('session_id', str(uuid.uuid4()))
        
        print(f" Attempting to save - User: {user_email}")
        
        chat_data = {
            "user_email": user_email,
            "character": "english_teacher",
            "user_message": user_text,
            "bot_reply": bot_reply,
            "timestamp": datetime.datetime.now(),
            "session_id": session_id
        }
        
        result = chats_collection.insert_one(chat_data)
        print(f" SUCCESS: Chat saved for user: {user_email}, ID: {result.inserted_id}")
    except Exception as e:
        print(f" DATABASE SAVE ERROR: {e}")

    return jsonify({"reply": bot_reply})

@english_bp.route('/chat-history-api')
def chat_history_api():
    """API to get chat history for the current user"""
    print(" CHAT HISTORY API CALLED")
    
    if 'email' not in session:
        print(" No user in session for chat history")
        return jsonify({"error": "Please login first"}), 401
    
    user_email = session['email']
    print(f" Loading chat history for: {user_email}")
    
    try:
        # Get chat history for this user and english_teacher character
        chats = list(chats_collection.find(
            {
                "user_email": user_email,
                "character": "english_teacher"
            }
        ).sort("timestamp", 1))  # Sort by timestamp ascending to show in order
        
        print(f" Found {len(chats)} chats in database")
        
        # Convert ObjectId to string for JSON serialization
        chat_list = []
        for chat in chats:
            chat_list.append({
                "user_message": chat.get('user_message', ''),
                "bot_reply": chat.get('bot_reply', ''),
                "timestamp": chat.get('timestamp', datetime.datetime.now()).isoformat(),
                "character": chat.get('character', 'english_teacher')
            })
        
        print(f" Successfully loaded {len(chat_list)} chat messages")
        return jsonify({
            "success": True,
            "chats": chat_list,
            "count": len(chat_list)
        })
        
    except Exception as e:
        print(f" Error loading chat history: {e}")
        return jsonify({
            "success": False, 
            "error": str(e)
        }), 500

@english_bp.route('/clean-audio', methods=['POST'])
def clean_audio():
    """Clean audio files"""
    try:
        audio_dir = os.path.join('frontend', 'static', 'audio')
        if os.path.exists(audio_dir):
            for file in os.listdir(audio_dir):
                if file.endswith('.mp3'):
                    os.remove(os.path.join(audio_dir, file))
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# Debug route to check user's chats
@english_bp.route('/debug-my-chats')
def debug_my_chats():
    """Debug route to see user's chats"""
    if 'email' not in session:
        return "Please login first"
    
    user_email = session['email']
    chats = list(chats_collection.find({"user_email": user_email}).sort("timestamp", -1))
    
    result = f"<h1>Your Chats ({len(chats)})</h1>"
    for chat in chats:
        result += f"""
        <div style="border:1px solid #ccc; margin:10px; padding:10px;">
            <strong>Time:</strong> {chat.get('timestamp')}<br>
            <strong>Character:</strong> {chat.get('character')}<br>
            <strong>You:</strong> {chat.get('user_message')}<br>
            <strong>Bot:</strong> {chat.get('bot_reply')}<br>
        </div>
        """
    
    return result