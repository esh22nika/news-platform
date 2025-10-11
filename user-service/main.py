# user-service/main.py
# user-service/main.py (Enhanced with Authentication)

import os
import json
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from google.cloud import firestore
from google.cloud import pubsub_v1
from flask_cors import CORS
import jwt
import bcrypt

# Initialize Flask app
app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

# Initialize Firestore
db = firestore.Client()

# Set your NEW GCP Project ID
PROJECT_ID = "news-platform-474717"  # UPDATE THIS

# JWT Secret - In production, use Secret Manager
JWT_SECRET = os.environ.get('JWT_SECRET', '8d5310675409c83dae0f321b3eb5bcb2a65387e581f4e80bef62b7cd91feee0d')
JWT_EXPIRATION_HOURS = 240

# Create Pub/Sub client
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, "engagement-topic")

#######################################
# Helper Functions
#######################################

def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, hashed):
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def generate_token(user_id, email):
    """Generate JWT token"""
    payload = {
        'user_id': user_id,
        'email': email,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def verify_token(token):
    """Verify JWT token and return user_id"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def require_auth(f):
    """Decorator to require authentication"""
    def wrapper(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({"error": "No token provided"}), 401
        
        user_id = verify_token(token)
        if not user_id:
            return jsonify({"error": "Invalid or expired token"}), 401
        
        # Add user_id to request context
        request.user_id = user_id
        return f(*args, **kwargs)
    
    wrapper.__name__ = f.__name__
    return wrapper

#######################################
# Health check route
#######################################

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "user-service-v2",
        "features": ["auth", "recommendations"]
    }), 200

#######################################
# User Registration
#######################################

@app.route('/auth/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        
        required_fields = ['username', 'email', 'password', 'interests']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing field: {field}"}), 400

        email = data['email'].lower().strip()
        
        # Check if user already exists
        existing_users = db.collection('users').where('email', '==', email).limit(1).stream()
        if len(list(existing_users)) > 0:
            return jsonify({"error": "User with this email already exists"}), 409

        # Hash password
        hashed_password = hash_password(data['password'])
        
        # Create user document
        user_ref = db.collection('users').document()
        user_data = {
            'username': data['username'],
            'email': email,
            'password': hashed_password,
            'interests': data['interests'],
            'created_at': firestore.SERVER_TIMESTAMP,
            'last_active': firestore.SERVER_TIMESTAMP
        }

        user_ref.set(user_data)
        
        # Generate JWT token
        token = generate_token(user_ref.id, email)

        return jsonify({
            "user_id": user_ref.id,
            "token": token,
            "message": "User registered successfully"
        }), 201

    except Exception as e:
        logging.error(f"Error registering user: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

#######################################
# User Login
#######################################

@app.route('/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        
        if 'email' not in data or 'password' not in data:
            return jsonify({"error": "Email and password required"}), 400

        email = data['email'].lower().strip()
        
        # Find user by email
        users = db.collection('users').where('email', '==', email).limit(1).stream()
        users_list = list(users)
        
        if len(users_list) == 0:
            return jsonify({"error": "Invalid credentials"}), 401
        
        user_doc = users_list[0]
        user_data = user_doc.to_dict()
        
        # Verify password
        if not verify_password(data['password'], user_data['password']):
            return jsonify({"error": "Invalid credentials"}), 401
        
        # Update last active
        db.collection('users').document(user_doc.id).update({
            'last_active': firestore.SERVER_TIMESTAMP
        })
        
        # Generate token
        token = generate_token(user_doc.id, email)

        return jsonify({
            "user_id": user_doc.id,
            "token": token,
            "username": user_data['username'],
            "interests": user_data['interests'],
            "message": "Login successful"
        }), 200

    except Exception as e:
        logging.error(f"Error logging in: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

#######################################
# Get Current User Profile (Protected)
#######################################

@app.route('/users/me', methods=['GET'])
@require_auth
def get_current_user():
    try:
        user_ref = db.collection('users').document(request.user_id)
        user = user_ref.get()

        if not user.exists:
            return jsonify({"error": "User not found"}), 404

        user_data = user.to_dict()
        # Remove password from response
        user_data.pop('password', None)
        user_data['user_id'] = request.user_id

        return jsonify(user_data), 200

    except Exception as e:
        logging.error(f"Error getting user: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

#######################################
# Update User Profile (Protected)
#######################################

@app.route('/users/me', methods=['PUT'])
@require_auth
def update_current_user():
    try:
        data = request.get_json()

        user_ref = db.collection('users').document(request.user_id)
        user = user_ref.get()

        if not user.exists:
            return jsonify({"error": "User not found"}), 404

        update_data = {}
        allowed_fields = ['username', 'interests']
        for field in allowed_fields:
            if field in data:
                update_data[field] = data[field]

        if update_data:
            update_data['last_active'] = firestore.SERVER_TIMESTAMP
            user_ref.update(update_data)

        return jsonify({"message": "Profile updated successfully"}), 200

    except Exception as e:
        logging.error(f"Error updating user: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

#######################################
# Engagement route → publishes to Pub/Sub (Protected)
#######################################

@app.route('/engagement', methods=['POST'])
@require_auth
def handle_engagement():
    try:
        data = request.get_json()
        
        # Ensure user_id matches authenticated user
        data['user_id'] = request.user_id
        
        # Add timestamp if not present
        if 'timestamp' not in data:
            data['timestamp'] = datetime.utcnow().isoformat()

        # Publish JSON data to Pub/Sub topic
        future = publisher.publish(
            topic_path,
            json.dumps(data).encode("utf-8")
        )
        message_id = future.result()

        logging.info(f"Published engagement event with message ID: {message_id}")
        
        # Update user preferences based on engagement
        update_user_preferences(request.user_id, data)

        return jsonify({
            "message": "Event published",
            "messageId": message_id
        }), 200

    except Exception as e:
        logging.error(f"Error publishing engagement event: {str(e)}")
        return jsonify({"error": str(e)}), 500

#######################################
# Update User Preferences for Recommendations
#######################################

def update_user_preferences(user_id, engagement_data):
    """Update user preferences based on engagement"""
    try:
        pref_ref = db.collection('user_preferences').document(user_id)
        pref_doc = pref_ref.get()
        
        article_id = engagement_data.get('article_id')
        event_type = engagement_data.get('event_type')
        
        if pref_doc.exists:
            prefs = pref_doc.to_dict()
        else:
            prefs = {
                'user_id': user_id,
                'liked_articles': [],
                'shared_articles': [],
                'category_scores': {},
                'last_updated': firestore.SERVER_TIMESTAMP
            }
        
        # Track liked/shared articles
        if event_type == 'like' and article_id not in prefs.get('liked_articles', []):
            prefs.setdefault('liked_articles', []).append(article_id)
        elif event_type == 'share' and article_id not in prefs.get('shared_articles', []):
            prefs.setdefault('shared_articles', []).append(article_id)
        
        # Update category scores (fetch article category from Firestore)
        article_ref = db.collection('articles').document(article_id)
        article = article_ref.get()
        
        if article.exists:
            category = article.to_dict().get('category')
            if category:
                category_scores = prefs.get('category_scores', {})
                score_increment = 2 if event_type == 'like' else 1
                category_scores[category] = category_scores.get(category, 0) + score_increment
                prefs['category_scores'] = category_scores
        
        prefs['last_updated'] = firestore.SERVER_TIMESTAMP
        pref_ref.set(prefs)
        
    except Exception as e:
        logging.error(f"Error updating preferences: {str(e)}")

#######################################
# Get User Recommendations (Protected)
#######################################

@app.route('/users/me/recommendations', methods=['GET'])
@require_auth
def get_recommendations():
    """Get personalized recommendations for user"""
    try:
        # Get user preferences
        pref_ref = db.collection('user_preferences').document(request.user_id)
        pref_doc = pref_ref.get()
        
        if not pref_doc.exists:
            # No preferences yet, return popular articles
            return get_popular_articles()
        
        prefs = pref_doc.to_dict()
        category_scores = prefs.get('category_scores', {})
        liked_articles = prefs.get('liked_articles', [])
        
        # Get top 3 categories
        top_categories = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)[:3]
        
        recommended_articles = []
        
        # Fetch articles from top categories
        for category, score in top_categories:
            articles = db.collection('articles')\
                .where('category', '==', category)\
                .order_by('publish_date', direction=firestore.Query.DESCENDING)\
                .limit(10)\
                .stream()
            
            for article in articles:
                article_data = article.to_dict()
                article_id = article.id
                
                # Skip already liked articles
                if article_id not in liked_articles:
                    article_data['recommendation_score'] = score
                    recommended_articles.append(article_data)
        
        # Sort by score and recency
        recommended_articles.sort(
            key=lambda x: (x['recommendation_score'], x['publish_date']),
            reverse=True
        )
        
        return jsonify({
            "articles": recommended_articles[:20],
            "count": len(recommended_articles[:20]),
            "based_on": list(dict(top_categories).keys())
        }), 200
        
    except Exception as e:
        logging.error(f"Error getting recommendations: {str(e)}")
        return jsonify({"error": "Failed to get recommendations"}), 500

def get_popular_articles():
    """Fallback: return popular articles"""
    articles = db.collection('articles')\
        .order_by('publish_date', direction=firestore.Query.DESCENDING)\
        .limit(20)\
        .stream()
    
    result = [article.to_dict() for article in articles]
    return jsonify({
        "articles": result,
        "count": len(result),
        "based_on": ["popular"]
    }), 200

#######################################
# Flask app startup
#######################################

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

