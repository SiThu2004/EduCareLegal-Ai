# v3
from flask import Blueprint, request, jsonify, session, redirect, url_for
from chains.doctor_chain import get_doctor_response  # Import the fixed function
from flask import render_template
import os
import datetime
import uuid
from pymongo import MongoClient
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for

doctor_bp = Blueprint('doctor_bp', __name__)

# MongoDB connection
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = MongoClient(mongo_uri)
db = client['chatbotDB']
chats_collection = db['chats']


@doctor_bp.route('/doctor')
def doctor_page():
    """Doctor chat page"""
    if 'email' not in session:
        return redirect(url_for('home'))
    return render_template('doctor.html')

@doctor_bp.route('/doctorcall')
def doctor_call_page():  
    """Doctor call page"""
    if 'email' not in session:
        return redirect(url_for('home'))
    return render_template('doctorcall.html')

@doctor_bp.route('/doctor/chat', methods=['POST'])
def doctor_chat():
    """Handle doctor chat messages"""
    print("🔵 DOCTOR CHAT ENDPOINT HIT")
    
    # Check if user is logged in
    if 'email' not in session:
        print("❌ No user in session")
        return jsonify({"reply": "Please login first."}), 401
    
    # Get JSON data
    data = request.get_json()
    print(f"📨 Received data: {data}")
    
    if not data:
        print("❌ No JSON data received")
        return jsonify({"reply": "Invalid JSON data."}), 400
        
    user_text = data.get("message", "").strip()
    if not user_text:
        print("❌ Empty message")
        return jsonify({"reply": "Please send a message."})

    # Process doctor chat message using the fixed chain
    try:
        print(f"🤖 Processing doctor message: {user_text}")
        
        # Use the fixed doctor chain function
        bot_reply = get_doctor_response(user_text)
        print(f"🤖 Doctor reply: {bot_reply[:50]}...")
        
    except Exception as e:
        print(f"❌ Doctor chain error: {e}")
        # Fallback response
        if any(word in user_text.lower() for word in ['hello', 'hi', 'hey']):
            bot_reply = "Hello! I'm Dr. Smith. How can I help you with your health concerns today?"
        else:
            bot_reply = "Thank you for your message. I'm Dr. Smith, here to discuss your health concerns. Could you tell me more about what you're experiencing?"

    # Save to database
    try:
        user_email = session.get('email')
        session_id = session.get('session_id', str(uuid.uuid4()))
        
        print(f"💾 Attempting to save - User: {user_email}")
        
        chat_data = {
            "user_email": user_email,
            "character": "doctor",
            "user_message": user_text,
            "bot_reply": bot_reply,
            "timestamp": datetime.datetime.now(),
            "session_id": session_id
        }
        
        result = chats_collection.insert_one(chat_data)
        print(f"✅ SUCCESS: Doctor chat saved for user: {user_email}, ID: {result.inserted_id}")
    except Exception as e:
        print(f"❌ DOCTOR DATABASE SAVE ERROR: {e}")

    return jsonify({"reply": bot_reply})

# ... keep the rest of your doctor.py routes the same ...
@doctor_bp.route('/doctor/chat-history-api')
def doctor_chat_history_api():
    """API to get doctor chat history for the current user"""
    print("🔵 DOCTOR CHAT HISTORY API CALLED")
    
    if 'email' not in session:
        print("❌ No user in session for doctor chat history")
        return jsonify({"error": "Please login first"}), 401
    
    user_email = session['email']
    print(f"📖 Loading doctor chat history for: {user_email}")
    
    try:
        # Get chat history for this user and doctor character
        chats = list(chats_collection.find(
            {
                "user_email": user_email,
                "character": "doctor"
            }
        ).sort("timestamp", 1))
        
        print(f"📊 Found {len(chats)} doctor chats in database")
        
        # Convert ObjectId to string for JSON serialization
        chat_list = []
        for chat in chats:
            chat_list.append({
                "user_message": chat.get('user_message', ''),
                "bot_reply": chat.get('bot_reply', ''),
                "timestamp": chat.get('timestamp', datetime.datetime.now()).isoformat(),
                "character": chat.get('character', 'doctor')
            })
        
        print(f"✅ Successfully loaded {len(chat_list)} doctor chat messages")
        return jsonify({
            "success": True,
            "chats": chat_list,
            "count": len(chat_list)
        })
        
    except Exception as e:
        print(f"❌ Error loading doctor chat history: {e}")
        return jsonify({
            "success": False, 
            "error": str(e)
        }), 500

@doctor_bp.route('/doctor/clean-audio', methods=['POST'])
def doctor_clean_audio():
    """Clean audio files for doctor"""
    try:
        audio_dir = os.path.join('frontend', 'static', 'audio')
        if os.path.exists(audio_dir):
            for file in os.listdir(audio_dir):
                if file.endswith('.mp3'):
                    os.remove(os.path.join(audio_dir, file))
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})