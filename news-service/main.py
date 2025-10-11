# news-service/main.py
import os
import requests
from flask import Flask, request, jsonify
from google.cloud import firestore, storage
import logging
from datetime import datetime
import uuid

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Initialize clients
db = firestore.Client()
storage_client = storage.Client()
bucket = storage_client.bucket('news-platform-assets-new')

# news api key is hardcoded for now cuz env var not working
NEWS_API_KEY = 'ae5d578c6235410d864d5be2af511cce'

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "service": "news-service"}), 200

@app.route('/news/fetch', methods=['POST'])
def fetch_news():
    """Fetch news from external APIs and store in Firestore"""
    try:
        # Sample categories
        categories = ['technology', 'business', 'health', 'sports', 'entertainment']
        
        articles_stored = 0
        
        for category in categories:
            # Using NewsAPI (free tier: 1000 requests/month)
            url = f'https://newsapi.org/v2/top-headlines'
            params = {
                'category': category,
                'language': 'en',
                'pageSize': 5,  # Limit to save API calls
                'apiKey': NEWS_API_KEY
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                for article in data.get('articles', []):
                    article_id = str(uuid.uuid4())
                    
                    # Store article in Firestore
                    article_data = {
                        'article_id': article_id,
                        'title': article.get('title', ''),
                        'content': article.get('description', ''),
                        'category': category,
                        'publish_date': datetime.now(),
                        'source': article.get('source', {}).get('name', ''),
                        'image_url': article.get('urlToImage', ''),
                        'url': article.get('url', ''),
                        'created_at': firestore.SERVER_TIMESTAMP
                    }
                    
                    db.collection('articles').document(article_id).set(article_data)
                    articles_stored += 1
        
        return jsonify({
            "message": f"Successfully stored {articles_stored} articles",
            "articles_count": articles_stored
        }), 200
        
    except Exception as e:
        logging.error(f"Error fetching news: {str(e)}")
        return jsonify({"error": "Failed to fetch news"}), 500

@app.route('/news', methods=['GET'])
def get_news():
    """Get news articles with optional category filter"""
    try:
        category = request.args.get('category')
        limit = int(request.args.get('limit', 20))
        
        query = db.collection('articles').order_by('publish_date', direction=firestore.Query.DESCENDING)
        
        if category:
            query = query.where('category', '==', category)
        
        articles = query.limit(limit).stream()
        
        result = []
        for article in articles:
            article_data = article.to_dict()
            result.append(article_data)
        
        return jsonify({
            "articles": result,
            "count": len(result)
        }), 200
        
    except Exception as e:
        logging.error(f"Error getting news: {str(e)}")
        return jsonify({"error": "Failed to get news"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
