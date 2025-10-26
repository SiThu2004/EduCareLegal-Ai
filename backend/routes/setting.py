from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template
from pymongo import MongoClient
import os
import bcrypt
from datetime import datetime
from bson import ObjectId

setting_bp = Blueprint('setting', __name__)

# MongoDB connection
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = MongoClient(mongo_uri)
db = client['chatbotDB']
users_collection = db['users']
chats_collection = db['chats']

@setting_bp.route('/settings')
def settings():
    """Settings page route"""
    if 'email' not in session:
        return redirect(url_for('home'))
    
    user_email = session['email']
    user = users_collection.find_one({"email": user_email})
    
    if not user:
        return redirect(url_for('home'))
    
    # Get user stats for dashboard
    user_chats_count = chats_collection.count_documents({"user_email": user_email})
    
    # Calculate storage used (approximate)
    storage_used = user_chats_count * 8000  # ~8KB per chat
    
    return render_template('setting.html', 
                         user=user,
                         chats_count=user_chats_count,
                         storage_used=format_storage(storage_used))

@setting_bp.route('/api/update-profile', methods=['POST'])
def update_profile():
    """Update user profile information"""
    if 'email' not in session:
        return jsonify({"success": False, "error": "Please login first"}), 401
    
    user_email = session['email']
    data = request.get_json()
    
    try:
        update_data = {}
        
        if 'display_name' in data:
            update_data['display_name'] = data['display_name']
        
        if 'phone_number' in data:
            update_data['phone_number'] = data['phone_number']
        
        if update_data:
            update_data['updated_at'] = datetime.now()
            users_collection.update_one(
                {"email": user_email},
                {"$set": update_data}
            )
        
        return jsonify({
            "success": True,
            "message": "Profile updated successfully"
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@setting_bp.route('/api/update-spam-preferences', methods=['POST'])
def update_spam_preferences():
    """Update spam preferences"""
    if 'email' not in session:
        return jsonify({"success": False, "error": "Please login first"}), 401
    
    user_email = session['email']
    data = request.get_json()
    
    try:
        spam_preferences = {
            'enable_spam_emails': data.get('enable_spam_emails', False),
            'block_all_spam': data.get('block_all_spam', False),
            'custom_filters': data.get('custom_filters', ''),
            'updated_at': datetime.now()
        }
        
        users_collection.update_one(
            {"email": user_email},
            {"$set": {"spam_preferences": spam_preferences}}
        )
        
        return jsonify({
            "success": True,
            "message": "Spam preferences updated successfully"
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@setting_bp.route('/api/export-data', methods=['POST'])
def export_data():
    """Export user data"""
    if 'email' not in session:
        return jsonify({"success": False, "error": "Please login first"}), 401
    
    user_email = session['email']
    
    try:
        # Get user data
        user_data = users_collection.find_one({"email": user_email})
        
        # Get chat history
        user_chats = list(chats_collection.find(
            {"user_email": user_email},
            {"_id": 0, "user_email": 0}
        ).sort("timestamp", 1))
        
        # Prepare export data
        export_data = {
            "user_info": {
                "email": user_data.get('email'),
                "display_name": user_data.get('display_name', ''),
                "phone_number": user_data.get('phone_number', ''),
                "created_at": user_data.get('created_at').isoformat() if user_data.get('created_at') else None
            },
            "preferences": user_data.get('spam_preferences', {}),
            "chat_history": user_chats,
            "exported_at": datetime.now().isoformat(),
            "total_chats": len(user_chats)
        }
        
        return jsonify({
            "success": True,
            "data": export_data,
            "message": "Data exported successfully"
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@setting_bp.route('/api/clear-chat-history', methods=['POST'])
def clear_chat_history():
    """Clear user's chat history"""
    if 'email' not in session:
        return jsonify({"success": False, "error": "Please login first"}), 401
    
    user_email = session['email']
    
    try:
        result = chats_collection.delete_many({"user_email": user_email})
        
        return jsonify({
            "success": True,
            "message": f"Cleared {result.deleted_count} chat messages",
            "deleted_count": result.deleted_count
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@setting_bp.route('/api/change-password', methods=['POST'])
def change_password():
    """Change user password"""
    if 'email' not in session:
        return jsonify({"success": False, "error": "Please login first"}), 401
    
    user_email = session['email']
    data = request.get_json()
    
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    if not current_password or not new_password:
        return jsonify({"success": False, "error": "Both current and new password are required"}), 400
    
    # Validate new password strength
    password_error = validate_password_strength(new_password)
    if password_error:
        return jsonify({"success": False, "error": password_error}), 400
    
    try:
        user = users_collection.find_one({"email": user_email})
        
        if not user or not bcrypt.checkpw(current_password.encode('utf-8'), user['password']):
            return jsonify({"success": False, "error": "Current password is incorrect"}), 400
        
        # Hash new password
        hashed_new_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        
        users_collection.update_one(
            {"email": user_email},
            {"$set": {
                "password": hashed_new_password,
                "updated_at": datetime.now()
            }}
        )
        
        return jsonify({
            "success": True,
            "message": "Password changed successfully"
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

def validate_password_strength(password):
    """Validate password meets strength requirements"""
    if len(password) < 8:
        return "Password must be at least 8 characters long"
    
    if not any(c.isupper() for c in password):
        return "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return "Password must contain at least one number"
    
    special_characters = "!@#$%^&*()_+-=[]{};':\"\\|,.<>/?"
    if not any(c in special_characters for c in password):
        return "Password must contain at least one special character"
    
    return None

@setting_bp.route('/api/delete-account', methods=['POST'])
def delete_account():
    """Delete user account and all data"""
    if 'email' not in session:
        return jsonify({"success": False, "error": "Please login first"}), 401
    
    user_email = session['email']
    data = request.get_json()
    
    confirm_text = data.get('confirmation', '')
    
    if confirm_text != "DELETE MY ACCOUNT":
        return jsonify({"success": False, "error": "Confirmation text does not match"}), 400
    
    try:
        # Delete user chats
        chats_collection.delete_many({"user_email": user_email})
        
        # Delete user account
        users_collection.delete_one({"email": user_email})
        
        # Clear session
        session.clear()
        
        return jsonify({
            "success": True,
            "message": "Account deleted successfully"
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@setting_bp.route('/api/get-user-stats')
def get_user_stats():
    """Get user statistics for settings page"""
    if 'email' not in session:
        return jsonify({"success": False, "error": "Please login first"}), 401
    
    user_email = session['email']
    
    try:
        # Count chats by character
        english_chats = chats_collection.count_documents({
            "user_email": user_email,
            "character": "english_teacher"
        })
        doctor_chats = chats_collection.count_documents({
            "user_email": user_email,
            "character": "doctor"
        })
        lawyer_chats = chats_collection.count_documents({
            "user_email": user_email,
            "character": "lawyer"
        })
        
        total_chats = english_chats + doctor_chats + lawyer_chats
        
        # Calculate storage (rough estimate)
        storage_used = total_chats * 8000  # ~8KB per chat
        
        # Get user info
        user = users_collection.find_one({"email": user_email})
        
        return jsonify({
            "success": True,
            "stats": {
                "total_chats": total_chats,
                "english_chats": english_chats,
                "doctor_chats": doctor_chats,
                "lawyer_chats": lawyer_chats,
                "storage_used": format_storage(storage_used),
                "account_created": user.get('created_at').strftime("%Y-%m-%d") if user.get('created_at') else "Unknown"
            }
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

def format_storage(bytes_size):
    """Format storage size in human readable format"""
    if bytes_size >= 1024 * 1024 * 1024:  # GB
        return f"{bytes_size / (1024 * 1024 * 1024):.1f}GB"
    elif bytes_size >= 1024 * 1024:  # MB
        return f"{bytes_size / (1024 * 1024):.1f}MB"
    elif bytes_size >= 1024:  # KB
        return f"{bytes_size / 1024:.1f}KB"
    else:
        return f"{bytes_size}B"