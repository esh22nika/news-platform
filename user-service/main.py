# user-service/main.py
import os
import json
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from google.cloud import firestore, pubsub_v1
from flask_cors import CORS
import jwt
import bcrypt

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "PUT", "OPTIONS"], "allow_headers": ["Content-Type", "Authorization"]}})
logging.basicConfig(level=logging.INFO)

# Initialize Firestore
db = firestore.Client()

# Update with YOUR project ID
PROJECT_ID = os.environ.get('GCP_PROJECT', 'news-platform-474717')

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

def generate_token(user_id, email, username):
    """Generate JWT token"""
    payload = {
        'user_id': user_id,
        'email': email,
        'username': username,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def verify_token(token):
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def require_auth(f):
    """Decorator to require authentication"""
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({"error": "No token provided"}), 401
        
        token = auth_header.replace('Bearer ', '')
        payload = verify_token(token)
        
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401
        
        # Add user info to request context
        request.user_id = payload['user_id']
        request.user_email = payload.get('email')
        request.username = payload.get('username')
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
        "service": "user-service",
        "features": ["auth", "recommendations", "engagement"]
    }), 200

#######################################
# User Registration
#######################################

@app.route('/auth/register', methods=['POST', 'OPTIONS'])
def register():
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.get_json()
        
        required_fields = ['username', 'email', 'password', 'interests']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing field: {field}"}), 400

        email = data['email'].lower().strip()
        username = data['username'].strip()
        
        # Check if user already exists
        existing_users = db.collection('users').where('email', '==', email).limit(1).stream()
        if len(list(existing_users)) > 0:
            return jsonify({"error": "User with this email already exists"}), 409

        # Hash password
        hashed_password = hash_password(data['password'])
        
        # Create user document
        user_ref = db.collection('users').document()
        user_data = {
            'username': username,
            'email': email,
            'password': hashed_password,
            'interests': data['interests'] if isinstance(data['interests'], list) else [i.strip() for i in data['interests'].split(',')],
            'created_at': firestore.SERVER_TIMESTAMP,
            'last_active': firestore.SERVER_TIMESTAMP
        }

        user_ref.set(user_data)
        
        # Generate JWT token
        token = generate_token(user_ref.id, email, username)

        logging.info(f"User registered: {email}")

        return jsonify({
            "user_id": user_ref.id,
            "username": username,
            "token": token,
            "message": "User registered successfully"
        }), 201

    except Exception as e:
        logging.error(f"Error registering user: {str(e)}")
        return jsonify({"error": "Registration failed"}), 500

#######################################
# User Login
#######################################

@app.route('/auth/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return '', 204
    
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
        token = generate_token(user_doc.id, email, user_data['username'])

        logging.info(f"User logged in: {email}")

        return jsonify({
            "user_id": user_doc.id,
            "username": user_data['username'],
            "token": token,
            "interests": user_data.get('interests', []),
            "message": "Login successful"
        }), 200

    except Exception as e:
        logging.error(f"Error logging in: {str(e)}")
        return jsonify({"error": "Login failed"}), 500

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
        return jsonify({"error": "Failed to get user profile"}), 500

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
        return jsonify({"error": "Failed to update profile"}), 500

#######################################
# Engagement route → publishes to Pub/Sub (Protected)
#######################################

@app.route('/engagement', methods=['POST', 'OPTIONS'])
@require_auth
def handle_engagement():
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.get_json()
        
        # Ensure user_id matches authenticated user
        data['user_id'] = request.user_id
        
        # Add timestamp if not present
        if 'timestamp' not in data:
            data['timestamp'] = datetime.utcnow().isoformat()

        # Publish JSON data to Pub/Sub topic
        message_data = json.dumps(data).encode("utf-8")
        future = publisher.publish(topic_path, message_data)
        message_id = future.result()

        logging.info(f"Published engagement event: {data['event_type']} by user {request.user_id}")
        
        # Update user preferences based on engagement
        update_user_preferences(request.user_id, data)

        return jsonify({
            "message": "Engagement tracked successfully",
            "messageId": message_id
        }), 200

    except Exception as e:
        logging.error(f"Error publishing engagement event: {str(e)}")
        return jsonify({"error": "Failed to track engagement"}), 500

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
                'viewed_articles': [],
                'category_scores': {},
                'last_updated': firestore.SERVER_TIMESTAMP
            }
        
        # Track liked/shared/viewed articles
        if event_type == 'like' and article_id not in prefs.get('liked_articles', []):
            prefs.setdefault('liked_articles', []).append(article_id)
        elif event_type == 'share' and article_id not in prefs.get('shared_articles', []):
            prefs.setdefault('shared_articles', []).append(article_id)
        elif event_type == 'view' and article_id not in prefs.get('viewed_articles', []):
            prefs.setdefault('viewed_articles', []).append(article_id)
        
        # Update category scores (fetch article category from Firestore)
        try:
            article_ref = db.collection('articles').document(article_id)
            article = article_ref.get()
            
            if article.exists:
                category = article.to_dict().get('category')
                if category:
                    category_scores = prefs.get('category_scores', {})
                    # Different weights for different actions
                    score_increment = 3 if event_type == 'like' else (2 if event_type == 'share' else 1)
                    category_scores[category] = category_scores.get(category, 0) + score_increment
                    prefs['category_scores'] = category_scores
        except Exception as e:
            logging.error(f"Error fetching article for preference update: {str(e)}")
        
        prefs['last_updated'] = firestore.SERVER_TIMESTAMP
        pref_ref.set(prefs)
        
        logging.info(f"Updated preferences for user {user_id}")
        
    except Exception as e:
        logging.error(f"Error updating preferences: {str(e)}")

#######################################
# Get User Recommendations (Protected)
#######################################

@app.route('/users/me/recommendations', methods=['GET'])
@require_auth
def get_recommendations():
    """Get personalized recommendations for user - ENHANCED"""
    try:
        # Get user profile for interests
        user_ref = db.collection('users').document(request.user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            return get_popular_articles()
        
        user_data = user_doc.to_dict()
        user_interests = [i.lower().strip() for i in user_data.get('interests', [])]
        
        # Get user preferences (engagement history)
        pref_ref = db.collection('user_preferences').document(request.user_id)
        pref_doc = pref_ref.get()
        
        # Build category scores from both interests and engagement
        category_scores = {}
        
        # 1. Add base scores from registration interests (weight: 5)
        for interest in user_interests:
            category_scores[interest] = category_scores.get(interest, 0) + 5
        
        # 2. Add scores from engagement (likes, shares)
        if pref_doc.exists:
            prefs = pref_doc.to_dict()
            engagement_scores = prefs.get('category_scores', {})
            
            for category, score in engagement_scores.items():
                category_scores[category] = category_scores.get(category, 0) + score
        
        if not category_scores:
            return get_popular_articles()
        
        # Get top categories sorted by score
        top_categories = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Track which articles to exclude
        liked_articles = []
        viewed_articles = []
        if pref_doc.exists:
            prefs = pref_doc.to_dict()
            liked_articles = prefs.get('liked_articles', [])
            viewed_articles = prefs.get('viewed_articles', [])
        
        # Fetch recommended articles
        recommended_articles = []
        seen_article_ids = set()
        
        # Prioritize: 1) Liked articles, 2) Top scored categories, 3) Other interests
        
        # STEP 1: Include LIKED articles first (user clearly likes these)
        if liked_articles:
            for article_id in liked_articles[:10]:  # Show up to 10 liked articles
                try:
                    article_ref = db.collection('articles').document(article_id)
                    article_doc = article_ref.get()
                    
                    if article_doc.exists:
                        article_data = article_doc.to_dict()
                        if 'article_id' not in article_data:
                            article_data['article_id'] = article_id
                        article_data['recommendation_score'] = 1000  # Highest priority
                        article_data['recommendation_reason'] = "You liked this"
                        article_data['is_liked'] = True
                        recommended_articles.append(article_data)
                        seen_article_ids.add(article_id)
                except Exception as e:
                    logging.error(f"Error fetching liked article {article_id}: {str(e)}")
        
        # STEP 2: Fetch new articles from top categories
        for category, score in top_categories[:5]:  # Top 5 categories
            try:
                articles = db.collection('articles')\
                    .where('category', '==', category)\
                    .order_by('publish_date', direction=firestore.Query.DESCENDING)\
                    .limit(20)\
                    .stream()
                
                for article in articles:
                    article_data = article.to_dict()
                    article_id = article.id
                    
                    # Skip already seen articles
                    if article_id in seen_article_ids:
                        continue
                    
                    if 'article_id' not in article_data:
                        article_data['article_id'] = article_id
                    
                    article_data['recommendation_score'] = score
                    article_data['recommendation_reason'] = f"Based on your interest in {category}"
                    article_data['is_liked'] = article_id in liked_articles
                    
                    recommended_articles.append(article_data)
                    seen_article_ids.add(article_id)
                    
            except Exception as e:
                logging.error(f"Error fetching articles for category {category}: {str(e)}")
        
        # Sort by recommendation score (liked first, then by engagement score)
        recommended_articles.sort(
            key=lambda x: x.get('recommendation_score', 0),
            reverse=True
        )
        
        logging.info(f"Generated {len(recommended_articles)} recommendations for user {request.user_id}")
        
        return jsonify({
            "articles": recommended_articles[:30],  # Return more articles
            "count": len(recommended_articles[:30]),
            "based_on": [cat for cat, score in top_categories[:5]]
        }), 200
        
    except Exception as e:
        logging.error(f"Error getting recommendations: {str(e)}")
        return get_popular_articles()

def get_articles_by_interests(interests):
    """Get articles based on user interests"""
    try:
        articles = []
        for interest in interests[:3]:  # Top 3 interests
            interest_lower = interest.lower().strip()
            category_articles = db.collection('articles')\
                .where('category', '==', interest_lower)\
                .order_by('publish_date', direction=firestore.Query.DESCENDING)\
                .limit(10)\
                .stream()
            
            for article in category_articles:
                article_data = article.to_dict()
                if 'article_id' not in article_data:
                    article_data['article_id'] = article.id
                articles.append(article_data)
        
        return jsonify({
            "articles": articles[:20],
            "count": len(articles[:20]),
            "based_on": interests
        }), 200
    except Exception as e:
        logging.error(f"Error getting articles by interests: {str(e)}")
        return get_popular_articles()

def get_popular_articles():
    """Fallback: return popular articles"""
    try:
        articles = db.collection('articles')\
            .order_by('publish_date', direction=firestore.Query.DESCENDING)\
            .limit(20)\
            .stream()
        
        result = []
        for article in articles:
            article_data = article.to_dict()
            if 'article_id' not in article_data:
                article_data['article_id'] = article.id
            result.append(article_data)
        
        return jsonify({
            "articles": result,
            "count": len(result),
            "based_on": ["popular"]
        }), 200
    except Exception as e:
        logging.error(f"Error getting popular articles: {str(e)}")
        return jsonify({
            "articles": [],
            "count": 0,
            "based_on": [],
            "error": "Failed to fetch articles"
        }), 500

#######################################
# Flask app startup
#######################################

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
