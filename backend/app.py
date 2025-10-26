# v3
from flask import Flask
from dotenv import load_dotenv
from routes.english import english_bp
from routes.englishcall import english_call_bp  
from routes.vocabulary import vocabulary_bp
from routes.doctorcall import doctor_call_bp  
from routes.doctor import doctor_bp
from routes.setting import setting_bp
from routes.admin import admin_bp
from routes.lawyer import lawyer_bp
from routes.lawyercall import lawyer_call_bp
from routes.translate import translate_bp
from routes.home import home_bp
from flask import Flask, send_from_directory  
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from pymongo import MongoClient
import bcrypt
import os
import datetime
import uuid
from bson import ObjectId

load_dotenv()

app = Flask(
    __name__,
    static_folder=os.path.join(os.path.dirname(__file__), '../frontend/static'),
    template_folder=os.path.join(os.path.dirname(__file__), '../frontend/templates')
)

app.secret_key = os.getenv("SECRET_KEY", "supersecret")


app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=1)  
app.config['SESSION_COOKIE_SECURE'] = False  
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'


mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = MongoClient(mongo_uri)
db = client['chatbotDB']
users_collection = db['users']
chats_collection = db['chats']


def save_chat_message(user_email, character, user_message, bot_reply):
    """Chat message ကို database ထဲသိမ်းမယ်"""
    try:
        chat_data = {
            "user_email": user_email,
            "character": character,
            "user_message": user_message,
            "bot_reply": bot_reply,
            "timestamp": datetime.datetime.now(),
            "session_id": session.get('session_id', str(uuid.uuid4()))
        }
        
        result = chats_collection.insert_one(chat_data)
        print(f" APP.PY SAVE - User: {user_email}, Message: {user_message[:30]}..., ID: {result.inserted_id}")
        return True
    except Exception as e:
        print(f" APP.PY SAVE ERROR: {e}")
        return False


@app.route('/english/chat-history-api')
def english_chat_history_api():
    """API to get chat history for the current user"""
    print(" CHAT HISTORY API CALLED from app.py")
    
    if 'email' not in session:
        return jsonify({"error": "Please login first"}), 401
    
    user_email = session['email']
    
    try:
       
        chats = list(chats_collection.find(
            {
                "user_email": user_email,
                "character": "english_teacher"
            }
        ).sort("timestamp", 1))
        
        print(f" Found {len(chats)} chats for {user_email}")
        
       
        chat_list = []
        for chat in chats:
            chat_list.append({
                "user_message": chat.get('user_message', ''),
                "bot_reply": chat.get('bot_reply', ''),
                "timestamp": chat.get('timestamp', datetime.datetime.now()).isoformat()
            })
        
        return jsonify({
            "success": True,
            "chats": chat_list,
            "count": len(chat_list)
        })
        
    except Exception as e:
        print(f" Error loading chat history: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/test-chat-save')
def test_chat_save():
    """Test if chat saving works"""
    if 'email' not in session:
        return "Please login first"
    
    
    test_data = {
        "user_email": session['email'],
        "character": "english_teacher", 
        "user_message": "Test message at " + datetime.datetime.now().strftime("%H:%M:%S"),
        "bot_reply": "Test reply at " + datetime.datetime.now().strftime("%H:%M:%S"),
        "timestamp": datetime.datetime.now(),
        "session_id": session.get('session_id', 'test')
    }
    
    try:
        result = chats_collection.insert_one(test_data)
        return f"Test chat saved! ID: {result.inserted_id}"
    except Exception as e:
        return f"Error: {e}"


@app.route('/debug-all-chats')
def debug_all_chats():
    """Debug route to see all chats in database"""
    if 'email' not in session:
        return "Please login first"
    
    all_chats = list(chats_collection.find().sort("timestamp", -1).limit(20))
    
    result = f"<h1>Total Chats: {chats_collection.count_documents({})}</h1>"
    result += f"<h2>Your Chats: {chats_collection.count_documents({'user_email': session['email']})}</h2>"
    
    for chat in all_chats:
        result += f"""
        <div style="border:1px solid #ccc; margin:10px; padding:10px;">
            <strong>User:</strong> {chat.get('user_email', 'N/A')}<br>
            <strong>Character:</strong> {chat.get('character', 'N/A')}<br>
            <strong>User Message:</strong> {chat.get('user_message', 'N/A')}<br>
            <strong>Bot Reply:</strong> {chat.get('bot_reply', 'N/A')}<br>
            <strong>Time:</strong> {chat.get('timestamp', 'N/A')}<br>
        </div>
        """
    
    return result

# --- Login/Signup Page ---
@app.route('/')
def home():
    # If user is already logged in, redirect to dashboard
    if 'email' in session:
        return render_template('dashboard.html') 
    return render_template('login.html')

@app.route('/signup', methods=['POST'])
def signup():
    email = request.form['email']
    password = request.form['password']

    # Email already exists check - FIXED
    existing_user = users_collection.find_one({"email": email})
    if existing_user:
        flash("Email already exists! Please use a different email.", "error")
        return redirect(url_for('home'))

    # If email doesn't exist, create new user
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    users_collection.insert_one({
        "email": email, 
        "password": hashed_pw,
        "created_at": datetime.datetime.now()
    })
    flash("Account created successfully!", "success")
    return redirect(url_for('home'))

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']

    user = users_collection.find_one({"email": email})
    if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
        # Set session variables properly
        session['email'] = email
        session['session_id'] = str(uuid.uuid4())
        session.permanent = True  # Make session permanent
        
        print(f" LOGIN SUCCESS: {email}, Session ID: {session['session_id']}")
        flash("Login successful!", "success")
        return redirect(url_for('dashboard'))  # Redirect to dashboard
    else:
        print(f" LOGIN FAILED: {email}")
        flash("Invalid email or password!", "error")
        return redirect(url_for('home'))


@app.route('/dashboard')
def dashboard():
    if 'email' not in session:
        print(" DASHBOARD: No session, redirecting to login")
        flash("Please login first!", "error")
        return redirect(url_for('home'))
    
    print(f" DASHBOARD: User {session['email']} accessing dashboard")
    # Render the proper dashboard template
    return render_template('dashboard.html')

@app.route('/debug-session')
def debug_session():
    """Debug route to check session status"""
    session_info = {
        'has_email': 'email' in session,
        'email': session.get('email', 'NOT FOUND'),
        'session_id': session.get('session_id', 'NOT FOUND'),
        'all_session_keys': list(session.keys())
    }
    return jsonify(session_info)

@app.route('/logout')
def logout():
    session.pop('email', None)
    session.pop('session_id', None)
    flash("Logged out successfully!", "success")
    return redirect(url_for('home'))

# --- Chat History Route ---
@app.route('/chat-history')
def chat_history():
    if 'email' not in session:
        return redirect(url_for('home'))
    
    user_email = session['email']
    

    chats = list(chats_collection.find(
        {"user_email": user_email}
    ).sort("timestamp", -1).limit(50))
    
    return render_template('chat_history.html', chats=chats)

# --- Recent Chats API for Dashboard ---

@app.route('/api/recent-chats')
def get_recent_chats():
    """Get recent chats for dashboard - show one of each bot"""
    print(" RECENT CHATS API CALLED")
    
    if 'email' not in session:
        print(" No user in session")
        return jsonify({"error": "Please login first"}), 401
    
    user_email = session['email']
    print(f" Loading recent chats for: {user_email}")
    
    try:
        # Get the latest chat for each character type
        characters = ['english_teacher', 'doctor', 'lawyer']
        chat_list = []
        
        for character in characters:
            # Find the most recent chat for this character
            latest_chat = chats_collection.find_one(
                {
                    "user_email": user_email,
                    "character": character
                },
                sort=[("timestamp", -1)]  # Get the most recent one
            )
            
            if latest_chat:
                # Real chat found
                character_name = ""
                if character == "english_teacher":
                    character_name = "English Tutor"
                elif character == "doctor":
                    character_name = "Medical Doctor" 
                elif character == "lawyer":
                    character_name = "Legal Advisor"
                
                bot_reply = latest_chat.get('bot_reply', '')
                display_message = bot_reply
                
                # If bot reply is too long, truncate it
                if len(display_message) > 60:
                    display_message = display_message[:60] + "..."
                
                chat_list.append({
                    "character": character,
                    "character_name": character_name,
                    "user_message": latest_chat.get('user_message', ''),
                    "bot_reply": bot_reply,
                    "display_message": display_message,
                    "timestamp": latest_chat.get('timestamp', datetime.datetime.now()),
                    "time_ago": get_time_ago(latest_chat.get('timestamp', datetime.datetime.now())),
                    "is_real": True
                })
            else:
                # No chat found for this character, create demo
                character_name = ""
                demo_message = ""
                
                if character == "english_teacher":
                    character_name = "English Tutor"
                    demo_message = "Hello! I'm here to help you improve your English skills. What would you like to practice today?"
                elif character == "doctor":
                    character_name = "Medical Doctor"
                    demo_message = "Hi there! I'm Dr. Smith. How can I assist you with your health concerns today?"
                elif character == "lawyer":
                    character_name = "Legal Advisor"
                    demo_message = "Good day! I'm here to provide legal guidance. What legal matter can I help you with?"
                
                chat_list.append({
                    "character": character,
                    "character_name": character_name,
                    "display_message": demo_message,
                    "time_ago": "Just now",
                    "is_real": False
                })
        
        # Sort by timestamp if available, otherwise keep the order
        real_chats = [chat for chat in chat_list if chat.get('is_real', False)]
        demo_chats = [chat for chat in chat_list if not chat.get('is_real', False)]
        
        # Sort real chats by timestamp (newest first)
        real_chats.sort(key=lambda x: x.get('timestamp', datetime.datetime.min), reverse=True)
        
        # Combine: real chats first, then demo chats
        sorted_chat_list = real_chats + demo_chats
        
        print(f" Successfully loaded chats: {[chat['character'] for chat in sorted_chat_list]}")
        return jsonify({
            "success": True,
            "chats": sorted_chat_list
        })
        
    except Exception as e:
        print(f" Error getting recent chats: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    

def get_time_ago(timestamp):
    """Calculate time ago string"""
    now = datetime.datetime.now()
    diff = now - timestamp
    
    if diff.days > 0:
        return f"{diff.days}d ago"
    elif diff.seconds >= 3600:
        hours = diff.seconds // 3600
        return f"{hours}h ago"
    elif diff.seconds >= 60:
        minutes = diff.seconds // 60
        return f"{minutes}m ago"
    else:
        return "Just now"

# --- Register Blueprints ---
app.register_blueprint(english_bp)
app.register_blueprint(english_call_bp)  
app.register_blueprint(doctor_bp)
app.register_blueprint(doctor_call_bp)
app.register_blueprint(lawyer_bp, url_prefix='/lawyer')
app.register_blueprint(translate_bp)
app.register_blueprint(home_bp)
app.register_blueprint(lawyer_call_bp, url_prefix='/lawyer-call')
app.register_blueprint(vocabulary_bp)
app.register_blueprint(setting_bp)
app.register_blueprint(admin_bp)

@app.route('/frontend/static/audio/<path:filename>')
def serve_audio(filename):
    audio_dir = os.path.join(app.static_folder, 'audio')
    return send_from_directory(audio_dir, filename)

@app.route('/image/<path:filename>')
def serve_image(filename):
    return send_from_directory(os.path.join(app.static_folder, 'image'), filename)

if __name__ == "__main__":
    # Create indexes for better performance
    try:
        chats_collection.create_index([("user_email", 1), ("timestamp", -1)])
        chats_collection.create_index([("timestamp", -1)])
        print(" Database indexes created!")
    except Exception as e:
        print(f" Index creation error: {e}")
    
    print(" Server starting...")
    app.run(debug=True)