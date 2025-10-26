from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for
from pymongo import MongoClient
import os
from bson import ObjectId
import datetime
from functools import wraps

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# MongoDB Connection
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = MongoClient(mongo_uri)
db = client['chatbotDB']
users_collection = db['users']
chats_collection = db['chats']

# Admin credentials - Hardcoded for now to fix login issues
ADMIN_USERNAME = "admin@gmail.com"
ADMIN_PASSWORD = "@Admin123"

def admin_login_required(f):
    """Decorator to check if admin is logged in"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash("Please login as admin first!", "error")
            return redirect(url_for('admin.admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        print(f"ADMIN LOGIN ATTEMPT: {username}")
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            session['admin_username'] = username
            session.permanent = True
            flash("Admin login successful!", "success")
            print("ADMIN LOGIN: SUCCESS")
            return redirect(url_for('admin.admin_dashboard'))
        else:
            flash("Invalid admin credentials!", "error")
            print("ADMIN LOGIN: FAILED")
    
    # If user is already logged in, redirect to dashboard
    if session.get('admin_logged_in'):
        return redirect(url_for('admin.admin_dashboard'))
        
    return render_template('admin/login.html')

@admin_bp.route('/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    flash("Admin logged out successfully!", "success")
    return redirect(url_for('admin.admin_login'))

@admin_bp.route('/dashboard')
@admin_login_required
def admin_dashboard():
    try:
        # Get statistics
        total_users = users_collection.count_documents({})
        total_chats = chats_collection.count_documents({})
        
        # Get recent users (last 7 days)
        seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)
        recent_users = users_collection.count_documents({
            "created_at": {"$gte": seven_days_ago}
        })
        
        # Get active users (users with at least one chat)
        active_users = len(chats_collection.distinct("user_email"))
        
        # Get chat statistics by character
        chat_stats = {
            'english_teacher': chats_collection.count_documents({"character": "english_teacher"}),
            'doctor': chats_collection.count_documents({"character": "doctor"}),
            'lawyer': chats_collection.count_documents({"character": "lawyer"})
        }
        
        # Get today's chats
        today_start = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_chats = chats_collection.count_documents({
            "timestamp": {"$gte": today_start}
        })
        
        return render_template('admin/dashboard.html',
                             total_users=total_users,
                             total_chats=total_chats,
                             recent_users=recent_users,
                             active_users=active_users,
                             today_chats=today_chats,
                             chat_stats=chat_stats)
    except Exception as e:
        flash(f"Error loading dashboard: {str(e)}", "error")
        return render_template('admin/dashboard.html',
                             total_users=0,
                             total_chats=0,
                             recent_users=0,
                             active_users=0,
                             today_chats=0,
                             chat_stats={})

@admin_bp.route('/users')
@admin_login_required
def manage_users():
    try:
        # Get search parameters
        search_email = request.args.get('search', '')
        page = int(request.args.get('page', 1))
        per_page = 20
        
        # Build query
        query = {}
        if search_email:
            query['email'] = {'$regex': search_email, '$options': 'i'}
        
        # Get total count for pagination
        total_users = users_collection.count_documents(query)
        
        # Calculate pagination
        skip = (page - 1) * per_page
        total_pages = (total_users + per_page - 1) // per_page
        
        # Get users with pagination
        users = list(users_collection.find(query)
                    .sort("created_at", -1)
                    .skip(skip)
                    .limit(per_page))
        
        # Get active users count (users with at least one chat)
        active_users = len(chats_collection.distinct("user_email"))
        
        # Pre-calculate chat counts and last activity for each user
        for user in users:
            user['chat_count'] = chats_collection.count_documents({"user_email": user['email']})
            last_chat = chats_collection.find_one(
                {"user_email": user['email']}, 
                sort=[("timestamp", -1)]
            )
            user['last_activity'] = last_chat['timestamp'] if last_chat else None
        
        return render_template('admin/users.html', 
                             users=users, 
                             page=page, 
                             total_pages=total_pages,
                             total_users=total_users,
                             active_users=active_users,
                             search_email=search_email)
    except Exception as e:
        flash(f"Error loading users: {str(e)}", "error")
        return render_template('admin/users.html', 
                             users=[], 
                             page=1, 
                             total_pages=0,
                             total_users=0,
                             active_users=0,
                             search_email='')

@admin_bp.route('/users/data')
@admin_login_required
def users_data():
    """API endpoint for users data (for AJAX)"""
    try:
        users = list(users_collection.find({}, {
            'email': 1,
            'created_at': 1,
            '_id': 1
        }).sort("created_at", -1))
        
        # Convert ObjectId and datetime for JSON
        for user in users:
            user['_id'] = str(user['_id'])
            user['created_at'] = user['created_at'].strftime("%Y-%m-%d %H:%M:%S")
            # Get user's chat count
            user['chat_count'] = chats_collection.count_documents({"user_email": user['email']})
        
        return jsonify({
            "success": True,
            "users": users,
            "total": len(users)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route('/users/add', methods=['POST'])
@admin_login_required
def add_user():
    try:
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            return jsonify({"success": False, "message": "Email and password are required!"})
        
        # Check if user already exists
        existing_user = users_collection.find_one({"email": email})
        if existing_user:
            return jsonify({"success": False, "message": "User already exists!"})
        
        # Hash password
        import bcrypt
        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        users_collection.insert_one({
            "email": email,
            "password": hashed_pw,
            "created_at": datetime.datetime.now()
        })
        
        return jsonify({"success": True, "message": "User added successfully!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@admin_bp.route('/users/delete/<user_id>', methods=['POST'])
@admin_login_required
def delete_user(user_id):
    try:
        # First get user email to delete their chats
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        if user:
            user_email = user['email']
            # Delete user's chats
            chats_collection.delete_many({"user_email": user_email})
        
        # Delete user
        result = users_collection.delete_one({"_id": ObjectId(user_id)})
        if result.deleted_count > 0:
            return jsonify({"success": True, "message": "User and their chats deleted successfully!"})
        else:
            return jsonify({"success": False, "message": "User not found!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@admin_bp.route('/users/update/<user_id>', methods=['POST'])
@admin_login_required
def update_user(user_id):
    try:
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email:
            return jsonify({"success": False, "message": "Email is required!"})
        
        update_data = {"email": email}
        
        if password:  # Only update password if provided
            import bcrypt
            hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            update_data["password"] = hashed_pw
        
        result = users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )
        
        if result.modified_count > 0 or result.matched_count > 0:
            return jsonify({"success": True, "message": "User updated successfully!"})
        else:
            return jsonify({"success": False, "message": "No changes made or user not found!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@admin_bp.route('/users/<user_id>/chats')
@admin_login_required
def user_chats(user_id):
    """View chats for a specific user"""
    try:
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            flash("User not found!", "error")
            return redirect(url_for('admin.manage_users'))
        
        user_email = user['email']
        page = int(request.args.get('page', 1))
        per_page = 20
        skip = (page - 1) * per_page
        
        total_chats = chats_collection.count_documents({"user_email": user_email})
        chats = list(chats_collection.find({"user_email": user_email})
                    .sort("timestamp", -1)
                    .skip(skip)
                    .limit(per_page))
        
        total_pages = (total_chats + per_page - 1) // per_page
        
        return render_template('admin/user_chats.html',
                             user=user,
                             chats=chats,
                             page=page,
                             total_pages=total_pages,
                             total_chats=total_chats)
    except Exception as e:
        flash(f"Error loading user chats: {str(e)}", "error")
        return redirect(url_for('admin.manage_users'))

@admin_bp.route('/chats')
@admin_login_required
def manage_chats():
    try:
        # Get filter parameters
        character_filter = request.args.get('character', '')
        search_query = request.args.get('search', '')
        page = int(request.args.get('page', 1))
        per_page = 20
        
        # Build query
        query = {}
        if character_filter:
            query['character'] = character_filter
        if search_query:
            query['$or'] = [
                {'user_message': {'$regex': search_query, '$options': 'i'}},
                {'bot_reply': {'$regex': search_query, '$options': 'i'}},
                {'user_email': {'$regex': search_query, '$options': 'i'}}
            ]
        
        # Get total count for pagination
        total_chats = chats_collection.count_documents(query)
        
        # Calculate pagination
        skip = (page - 1) * per_page
        total_pages = (total_chats + per_page - 1) // per_page
        
        # Get chats with pagination
        chats = list(chats_collection.find(query)
                    .sort("timestamp", -1)
                    .skip(skip)
                    .limit(per_page))
        
        # Get unique characters for filter dropdown
        characters = chats_collection.distinct("character")
        
        return render_template('admin/chats.html', 
                             chats=chats, 
                             page=page, 
                             total_pages=total_pages,
                             total_chats=total_chats,
                             characters=characters,
                             character_filter=character_filter,
                             search_query=search_query)
    except Exception as e:
        flash(f"Error loading chats: {str(e)}", "error")
        return render_template('admin/chats.html', 
                             chats=[], 
                             page=1, 
                             total_pages=0,
                             total_chats=0,
                             characters=[],
                             character_filter='',
                             search_query='')

@admin_bp.route('/chats/delete/<chat_id>', methods=['POST'])
@admin_login_required
def delete_chat(chat_id):
    try:
        result = chats_collection.delete_one({"_id": ObjectId(chat_id)})
        if result.deleted_count > 0:
            return jsonify({"success": True, "message": "Chat deleted successfully!"})
        else:
            return jsonify({"success": False, "message": "Chat not found!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@admin_bp.route('/chats/delete-all-user-chats/<user_email>', methods=['POST'])
@admin_login_required
def delete_all_user_chats(user_email):
    try:
        result = chats_collection.delete_many({"user_email": user_email})
        return jsonify({
            "success": True, 
            "message": f"Deleted {result.deleted_count} chats for user {user_email}!"
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@admin_bp.route('/analytics')
@admin_login_required
def analytics():
    try:
        # Daily user registration stats (last 30 days)
        thirty_days_ago = datetime.datetime.now() - datetime.timedelta(days=30)
        
        user_pipeline = [
            {
                "$match": {
                    "created_at": {"$gte": thirty_days_ago}
                }
            },
            {
                "$group": {
                    "_id": {
                        "year": {"$year": "$created_at"},
                        "month": {"$month": "$created_at"},
                        "day": {"$dayOfMonth": "$created_at"}
                    },
                    "count": {"$sum": 1},
                    "date": {"$first": "$created_at"}
                }
            },
            {"$sort": {"_id": 1}},
            {"$limit": 30}
        ]
        
        user_stats = list(users_collection.aggregate(user_pipeline))
        
        # Daily chat statistics (last 30 days)
        chat_pipeline = [
            {
                "$match": {
                    "timestamp": {"$gte": thirty_days_ago}
                }
            },
            {
                "$group": {
                    "_id": {
                        "year": {"$year": "$timestamp"},
                        "month": {"$month": "$timestamp"},
                        "day": {"$dayOfMonth": "$timestamp"}
                    },
                    "count": {"$sum": 1},
                    "date": {"$first": "$timestamp"}
                }
            },
            {"$sort": {"_id": 1}},
            {"$limit": 30}
        ]
        
        chat_stats = list(chats_collection.aggregate(chat_pipeline))
        
        # Chat statistics by character
        character_pipeline = [
            {
                "$group": {
                    "_id": "$character",
                    "count": {"$sum": 1}
                }
            }
        ]
        
        character_stats = list(chats_collection.aggregate(character_pipeline))
        
        # Top active users
        top_users_pipeline = [
            {
                "$group": {
                    "_id": "$user_email",
                    "chat_count": {"$sum": 1},
                    "last_activity": {"$max": "$timestamp"}
                }
            },
            {"$sort": {"chat_count": -1}},
            {"$limit": 10}
        ]
        
        top_users = list(chats_collection.aggregate(top_users_pipeline))
        
        return render_template('admin/analytics.html',
                             user_stats=user_stats,
                             chat_stats=chat_stats,
                             character_stats=character_stats,
                             top_users=top_users)
    except Exception as e:
        flash(f"Error loading analytics: {str(e)}", "error")
        return render_template('admin/analytics.html',
                             user_stats=[],
                             chat_stats=[],
                             character_stats=[],
                             top_users=[])

@admin_bp.route('/api/analytics/data')
@admin_login_required
def analytics_data():
    """API endpoint for analytics data"""
    try:
        # User growth data (last 7 days)
        dates = []
        user_counts = []
        chat_counts = []
        
        for i in range(6, -1, -1):
            date = datetime.datetime.now() - datetime.timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            
            # Count users created on this date
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            user_count = users_collection.count_documents({
                "created_at": {"$gte": start_of_day, "$lte": end_of_day}
            })
            
            chat_count = chats_collection.count_documents({
                "timestamp": {"$gte": start_of_day, "$lte": end_of_day}
            })
            
            dates.append(date_str)
            user_counts.append(user_count)
            chat_counts.append(chat_count)
        
        return jsonify({
            "success": True,
            "dates": dates,
            "user_counts": user_counts,
            "chat_counts": chat_counts
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route('/settings')
@admin_login_required
def admin_settings():
    """Admin settings page"""
    return render_template('admin/settings.html')

@admin_bp.route('/settings/update-credentials', methods=['POST'])
@admin_login_required
def update_admin_credentials():
    """Update admin credentials"""
    try:
        current_username = request.form.get('current_username')
        current_password = request.form.get('current_password')
        new_username = request.form.get('new_username')
        new_password = request.form.get('new_password')
        
        # Verify current credentials
        if current_username != ADMIN_USERNAME or current_password != ADMIN_PASSWORD:
            return jsonify({"success": False, "message": "Current credentials are incorrect!"})
        
        # In a real application, you would update these in a database
        # For now, we'll just return a message since these are hardcoded
        return jsonify({
            "success": True, 
            "message": "Credentials would be updated in database. Currently using hardcoded credentials."
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# Error handler for admin routes
@admin_bp.errorhandler(404)
def admin_not_found(error):
    return render_template('admin/404.html'), 404

@admin_bp.errorhandler(500)
def admin_server_error(error):
    return render_template('admin/500.html'), 500