# from flask import Blueprint, request, jsonify, session, redirect, url_for
# from chains.lawyer_chain import get_lawyer_response
# from flask import render_template
# import os
# import datetime
# import uuid
# import edge_tts
# from gtts import gTTS
# from langdetect import detect
# import asyncio
# from pymongo import MongoClient

# # Create blueprint with proper name
# lawyer_bp = Blueprint('lawyer_bp', __name__)

# # MongoDB connection
# mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
# client = MongoClient(mongo_uri)
# db = client['chatbotDB']
# chats_collection = db['chats']

# # Voice options for lawyer
# VOICE_OPTIONS = {
#     'myanmar': 'google-tts',
#     'default2': 'en-US-ChristopherNeural',
     
#     'male2': 'en-US-EricNeural',
#     'male3': 'en-US-GuyNeural',
#     'female2': 'en-US-AriaNeural',
#     'female3': 'en-US-JennyNeural',
# }

# # Speed options
# SPEED_OPTIONS = {
#     'slow': '-30%',
#     'normal': '+0%',
#     'fast': '+30%'
# }

# # ========== ROUTES ==========

# @lawyer_bp.route('/')
# def lawyer_page():
#     """Lawyer chat page"""
#     print("🔵 LAWYER PAGE ACCESSED")
#     if 'email' not in session:
#         return redirect(url_for('home'))
#     return render_template('lawyer.html')

# @lawyer_bp.route('/lawyercall')
# def lawyer_call_page():  
#     """Lawyer call page"""
#     print("🔵 LAWYER CALL PAGE ACCESSED")
#     if 'email' not in session:
#         return redirect(url_for('home'))
#     return render_template('lawyercall.html')

# @lawyer_bp.route('/chat', methods=['POST'])
# def lawyer_chat():
#     """Handle lawyer chat messages"""
#     print("🔵 LAWYER CHAT ENDPOINT HIT")
    
#     # Check if user is logged in
#     if 'email' not in session:
#         print("❌ No user in session")
#         return jsonify({"reply": "Please login first."}), 401
    
#     # Get JSON data
#     data = request.get_json()
#     print(f"📨 Received data: {data}")
    
#     if not data:
#         print("❌ No JSON data received")
#         return jsonify({"reply": "Invalid JSON data."}), 400
        
#     user_text = data.get("message", "").strip()
#     if not user_text:
#         print("❌ Empty message")
#         return jsonify({"reply": "Please send a message."})

#     # Process lawyer chat message
#     try:
#         print(f"🤖 Processing lawyer message: {user_text}")
        
#         # Use lawyer chain function
#         bot_reply = get_lawyer_response(user_text)
#         print(f"🤖 Lawyer reply: {bot_reply}")
        
#     except Exception as e:
#         print(f"❌ Lawyer chain error: {e}")
#         # Fallback to simple responses
#         user_text_lower = user_text.lower()
        
#         if any(word in user_text_lower for word in ['hello', 'hi', 'hey']):
#             bot_reply = "Hello! I'm U Khin Zaw. How can I assist you with your legal matters today?"
#         elif any(word in user_text_lower for word in ['contract', 'agreement']):
#             bot_reply = "Contracts are important legal documents. Could you tell me more about the type of contract you're dealing with?"
#         elif any(word in user_text_lower for word in ['divorce', 'marriage']):
#             bot_reply = "Family law matters can be complex. Are you seeking information about divorce procedures or marital issues?"
#         else:
#             bot_reply = "Thank you for your inquiry. I'm U Khin Zaw, here to provide legal guidance. Could you tell me more about your legal concern?"

#     # Save to database
#     try:
#         user_email = session.get('email')
#         session_id = session.get('session_id', str(uuid.uuid4()))
        
#         print(f"💾 Attempting to save - User: {user_email}")
        
#         chat_data = {
#             "user_email": user_email,
#             "character": "lawyer",
#             "user_message": user_text,
#             "bot_reply": bot_reply,
#             "timestamp": datetime.datetime.now(),
#             "session_id": session_id
#         }
        
#         result = chats_collection.insert_one(chat_data)
#         print(f"✅ SUCCESS: Lawyer chat saved for user: {user_email}, ID: {result.inserted_id}")
#     except Exception as e:
#         print(f"❌ LAWYER DATABASE SAVE ERROR: {e}")

#     return jsonify({"reply": bot_reply})

# @lawyer_bp.route('/chat-history-api')
# def lawyer_chat_history_api():
#     """API to get lawyer chat history for the current user"""
#     print("🔵 LAWYER CHAT HISTORY API CALLED")
    
#     if 'email' not in session:
#         print("❌ No user in session for lawyer chat history")
#         return jsonify({"error": "Please login first"}), 401
    
#     user_email = session['email']
#     print(f"📖 Loading lawyer chat history for: {user_email}")
    
#     try:
#         # Get chat history for this user and lawyer character
#         chats = list(chats_collection.find(
#             {
#                 "user_email": user_email,
#                 "character": "lawyer"
#             }
#         ).sort("timestamp", 1))
        
#         print(f"📊 Found {len(chats)} lawyer chats in database")
        
#         # Convert ObjectId to string for JSON serialization
#         chat_list = []
#         for chat in chats:
#             chat_list.append({
#                 "user_message": chat.get('user_message', ''),
#                 "bot_reply": chat.get('bot_reply', ''),
#                 "timestamp": chat.get('timestamp', datetime.datetime.now()).isoformat(),
#                 "character": chat.get('character', 'lawyer')
#             })
        
#         print(f"✅ Successfully loaded {len(chat_list)} lawyer chat messages")
#         return jsonify({
#             "success": True,
#             "chats": chat_list,
#             "count": len(chat_list)
#         })
        
#     except Exception as e:
#         print(f"❌ Error loading lawyer chat history: {e}")
#         return jsonify({
#             "success": False, 
#             "error": str(e)
#         }), 500

# @lawyer_bp.route('/call', methods=['POST'])
# def voice_chat():
#     """Handle voice chat with voice and speed options"""
#     print("🔵 LAWYER CALL ENDPOINT HIT")
    
#     data = request.get_json()
#     if not data:
#         return jsonify({"text": "No data received", "audio": None}), 400
        
#     message = data.get('message', '').strip()
#     voice_type = data.get('voice', 'default')
#     speed = data.get('speed', 'normal')
    
#     print(f"📨 Call data: message='{message}', voice='{voice_type}', speed='{speed}'")
    
#     if not message:
#         return jsonify({"text": "Please describe your legal concern.", "audio": None})
    
#     try:
#         # Use lawyer chain function with error handling
#         try:
#             bot_reply = get_lawyer_response(message)
#             print(f"🤖 Lawyer call response: {bot_reply}")
#         except Exception as e:
#             print(f"❌ Error getting lawyer response: {e}")
#             bot_reply = "I apologize, but I'm having trouble processing your legal question right now. Please try again or rephrase your question."
        
#         # Generate audio response
#         audio_url = None
#         try:
#             audio_url = asyncio.run(generate_speech(bot_reply, voice_type, speed))
#             print(f"🔊 Audio generated: {audio_url}")
#         except Exception as e:
#             print(f"❌ TTS error: {e}")
#             # Continue without audio if TTS fails
        
#         return jsonify({
#             "text": bot_reply,
#             "audio": audio_url
#         })
        
#     except Exception as e:
#         print(f"❌ Error in lawyer voice chat endpoint: {e}")
#         return jsonify({
#             "text": "Sorry, I'm having technical difficulties. Please try again.", 
#             "audio": None
#         }), 500

# async def generate_speech(text: str, voice_type: str = 'default', speed: str = 'normal') -> str:
#     """Generate speech audio file with selected voice and speed"""
#     try:            
#         if not isinstance(text, str) or not text.strip():
#             raise ValueError("Invalid text input")
            
#         # Create audio directory if it doesn't exist
#         audio_dir = os.path.join('frontend', 'static', 'audio', 'lawyer')
#         os.makedirs(audio_dir, exist_ok=True)
        
#         filename = f"lawyer_{uuid.uuid4().hex}.mp3"
#         filepath = os.path.join(audio_dir, filename)
        
#         voice = VOICE_OPTIONS.get(voice_type, VOICE_OPTIONS['default'])
#         rate = SPEED_OPTIONS.get(speed, SPEED_OPTIONS['normal'])
        
#         print(f"🔊 Generating speech: voice={voice}, speed={rate}, text_length={len(text)}")
        
#         # Add timeout for TTS generation
#         try:
#             communicate = edge_tts.Communicate(text, voice, rate=rate)
#             await asyncio.wait_for(communicate.save(filepath), timeout=15)
#             return f"/static/audio/lawyer/{filename}"
#         except asyncio.TimeoutError:
#             print("❌ TTS generation timed out")
#             return None
#         except Exception as e:
#             print(f"❌ TTS communication error: {e}")
#             return None
            
#     except Exception as e:
#         print(f"❌ Error in speech generation: {e}")
#         return None

# @lawyer_bp.route('/delete-audio', methods=['POST'])
# def delete_audio():
#     """Clean audio files for lawyer"""
#     try:
#         audio_dir = os.path.join('frontend', 'static', 'audio', 'lawyer')
#         if os.path.exists(audio_dir):
#             deleted_count = 0
#             for file in os.listdir(audio_dir):
#                 if file.endswith('.mp3'):
#                     os.remove(os.path.join(audio_dir, file))
#                     deleted_count += 1
#                     print(f"🗑️ Deleted audio file: {file}")
#             print(f"✅ Deleted {deleted_count} audio files")
#         else:
#             print("ℹ️ Audio directory doesn't exist yet")
#         return jsonify({"status": "success", "deleted_files": True})
#     except Exception as e:
#         print(f"❌ Error deleting audio: {e}")
#         return jsonify({"status": "error", "message": str(e)})

# @lawyer_bp.route('/clean-audio', methods=['POST'])
# def lawyer_clean_audio():
#     """Clean audio files for lawyer"""
#     try:
#         audio_dir = os.path.join('frontend', 'static', 'audio')
#         if os.path.exists(audio_dir):
#             for file in os.listdir(audio_dir):
#                 if file.endswith('.mp3'):
#                     os.remove(os.path.join(audio_dir, file))
#         return jsonify({"status": "success"})
#     except Exception as e:
#         return jsonify({"status": "error", "message": str(e)})

from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template
import os, datetime, uuid, asyncio
from pymongo import MongoClient
from chains.lawyer_chain import get_lawyer_response
import edge_tts
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for

# ===== Blueprint =====  
lawyer_bp = Blueprint('lawyer_bp', __name__)

# ===== MongoDB =====
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = MongoClient(mongo_uri)
db = client['chatbotDB']
chats_collection = db['chats']

# ===== Edge TTS Voice options =====
VOICE_OPTIONS = {
    'male1': 'en-US-ChristopherNeural',    # Robert
    'male2': 'en-US-EricNeural',           # James  
    'male3': 'en-US-GuyNeural',            # William
    'female1': 'en-US-AriaNeural',         # Elizabeth
    'female2': 'en-US-JennyNeural',        # Jenny
}

SPEED_OPTIONS = {
    'slow': '-30%',
    'normal': '+0%',
    'fast': '+30%'
}

# ===== Routes =====
@lawyer_bp.route('/')
def lawyer_page():
    if 'email' not in session:
        return redirect(url_for('home'))
    return render_template('lawyer.html')





@lawyer_bp.route('/lawyercall')
def lawyer_call_page():
    if 'email' not in session:
        return redirect(url_for('home'))
    return render_template('lawyercall.html')

@lawyer_bp.route('/chat', methods=['POST'])
def lawyer_chat():
    if 'email' not in session:
        return jsonify({"reply": "Please login first."}), 401
    data = request.get_json()
    if not data: return jsonify({"reply": "Invalid JSON data."}), 400

    user_text = data.get("message", "").strip()
    if not user_text: return jsonify({"reply": "Please send a message."})

    # Process response
    try:
        bot_reply = get_lawyer_response(user_text)
    except Exception as e:
        print(f"Lawyer chain error: {e}")
        bot_reply = "Hello! I'm Attorney Johnson. How can I assist you with your legal matters today?"

    # Save to DB
    try:
        chat_data = {
            "user_email": session.get('email'),
            "character": "lawyer",
            "user_message": user_text,
            "bot_reply": bot_reply,
            "timestamp": datetime.datetime.now(),
            "session_id": session.get('session_id', str(uuid.uuid4()))
        }
        chats_collection.insert_one(chat_data)
    except Exception as e:
        print(f"DB save error: {e}")

    return jsonify({"reply": bot_reply})

@lawyer_bp.route('/chat-history-api')
def lawyer_chat_history_api():
    if 'email' not in session:
        return jsonify({"error": "Please login first"}), 401
    user_email = session['email']
    try:
        chats = list(chats_collection.find({
            "user_email": user_email,
            "character": "lawyer"
        }).sort("timestamp", 1))
        chat_list = [{
            "user_message": c.get("user_message", ""), 
            "bot_reply": c.get("bot_reply", ""), 
            "timestamp": c.get("timestamp", datetime.datetime.now()).isoformat()
        } for c in chats]
        return jsonify({"success": True, "chats": chat_list, "count": len(chat_list)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@lawyer_bp.route('/call', methods=['POST'])
def voice_chat():
    data = request.get_json()
    if not data: return jsonify({"text": "No data", "audio": None}), 400

    message = data.get('message', '').strip()
    voice_type = data.get('voice', 'male1')  # Default to male1
    speed = data.get('speed', 'normal')      # Default to normal
    
    print(f"🔊 Voice settings received - Voice: {voice_type}, Speed: {speed}")
    
    if not message: 
        return jsonify({"text": "Please describe your legal concern.", "audio": None})

    try:
        # Get lawyer response
        try: 
            bot_reply = get_lawyer_response(message)
        except Exception as e:
            print(f"Lawyer chain error: {e}")
            bot_reply = "I'm having trouble processing your legal question. Please try again."

        # Generate audio using Edge TTS only
        audio_url = asyncio.run(generate_edge_speech(bot_reply, voice_type, speed))
        
        return jsonify({
            "text": bot_reply, 
            "audio": audio_url
        })
        
    except Exception as e:
        print(f"Error in lawyer voice chat: {e}")
        return jsonify({
            "text": "Technical error. Please try again.",
            "audio": None
        }), 500

async def generate_edge_speech(text: str, voice_type: str = 'male1', speed: str = 'normal') -> str:
    """Generate speech using Edge TTS only"""
    try:
        if not text or not text.strip():
            return None
            
        # Create audio directory
        audio_dir = os.path.join('frontend', 'static', 'audio', 'lawyer')
        os.makedirs(audio_dir, exist_ok=True)
        
        filename = f"lawyer_{uuid.uuid4().hex}.mp3"
        filepath = os.path.join(audio_dir, filename)
        
        # Get voice and speed settings
        voice = VOICE_OPTIONS.get(voice_type, VOICE_OPTIONS['male1'])
        rate = SPEED_OPTIONS.get(speed, SPEED_OPTIONS['normal'])
        
        print(f"🔊 Generating Edge TTS: voice={voice_type}->{voice}, speed={speed}->{rate}")
        
        # Generate speech with timeout
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        await asyncio.wait_for(communicate.save(filepath), timeout=15)
        
        return f"/static/audio/lawyer/{filename}"
        
    except asyncio.TimeoutError:
        print("❌ Edge TTS generation timed out")
        return None
    except Exception as e:
        print(f"❌ Edge TTS error: {e}")
        return None

@lawyer_bp.route('/delete-audio', methods=['POST'])
def delete_audio():
    """Clean audio files"""
    try:
        audio_dir = os.path.join('frontend', 'static', 'audio', 'lawyer')
        deleted_count = 0
        if os.path.exists(audio_dir):
            for file in os.listdir(audio_dir):
                if file.endswith('.mp3'):
                    os.remove(os.path.join(audio_dir, file))
                    deleted_count += 1
        return jsonify({"status": "success", "deleted_files": deleted_count})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@lawyer_bp.route('/clean-audio', methods=['POST'])
def clean_audio():
    """Alias for delete-audio"""
    return delete_audio()