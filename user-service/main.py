# user-service/main.py

import os
import json
import logging
from flask import Flask, request, jsonify
from google.cloud import firestore
from google.cloud import pubsub_v1
from flask_cors import CORS


# Initialize Flask app
app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

# Initialize Firestore
db = firestore.Client()

# Set your GCP Project ID
PROJECT_ID = "news-platform-474717"

# Create Pub/Sub client ONCE, not per request
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, "engagement-topic")

#######################################
# Health check route
#######################################

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "user-service"
    }), 200

#######################################
# Create user
#######################################

@app.route('/users', methods=['POST'])
def create_user():
    try:
        data = request.get_json()
        
        required_fields = ['username', 'email', 'interests']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing field: {field}"}), 400

        user_ref = db.collection('users').document()
        user_data = {
            'username': data['username'],
            'email': data['email'],
            'interests': data['interests'],
            'created_at': firestore.SERVER_TIMESTAMP,
            'last_active': firestore.SERVER_TIMESTAMP
        }

        user_ref.set(user_data)

        return jsonify({
            "user_id": user_ref.id,
            "message": "User created successfully"
        }), 201

    except Exception as e:
        logging.error(f"Error creating user: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

#######################################
# Get user by ID
#######################################

@app.route('/users/<user_id>', methods=['GET'])
def get_user(user_id):
    try:
        user_ref = db.collection('users').document(user_id)
        user = user_ref.get()

        if not user.exists:
            return jsonify({"error": "User not found"}), 404

        user_data = user.to_dict()
        user_data['user_id'] = user_id

        return jsonify(user_data), 200

    except Exception as e:
        logging.error(f"Error getting user: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

#######################################
# Update user
#######################################

@app.route('/users/<user_id>', methods=['PUT'])
def update_user(user_id):
    try:
        data = request.get_json()

        user_ref = db.collection('users').document(user_id)
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

        return jsonify({"message": "User updated successfully"}), 200

    except Exception as e:
        logging.error(f"Error updating user: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

#######################################
# Engagement route → publishes to Pub/Sub
#######################################

@app.route('/engagement', methods=['POST'])
def handle_engagement():
    try:
        data = request.get_json()

        # Publish JSON data to Pub/Sub topic
        future = publisher.publish(
            topic_path,
            json.dumps(data).encode("utf-8")
        )
        message_id = future.result()

        logging.info(f"Published engagement event with message ID: {message_id}")

        return jsonify({
            "message": "Event published",
            "messageId": message_id
        }), 200

    except Exception as e:
        logging.error(f"Error publishing engagement event: {str(e)}")
        return jsonify({"error": str(e)}), 500

#######################################
# Flask app startup
#######################################

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
