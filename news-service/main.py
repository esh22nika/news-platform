import os
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from google.cloud import firestore
import logging
from datetime import datetime, timedelta
import uuid
import time

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
logging.basicConfig(level=logging.INFO)

# Initialize Firestore
db = firestore.Client()

# News API key
NEWS_API_KEY = 'ae5d578c6235410d864d5be2af511cce'

# Placeholder image URL for missing or blocked images
PLACEHOLDER_IMAGE = 'https://placehold.co/400x200/3b82f6/ffffff/png?text=News'

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "service": "news-service"}), 200

@app.route('/news/fetch', methods=['POST'])
def fetch_news():
    """Fetch news from NewsAPI and store in Firestore"""
    try:
        categories = ['technology', 'business', 'sports', 'entertainment', 'science']
        
        articles_stored = 0
        articles_attempted = 0
        
        for category in categories:
            try:
                url = 'https://newsapi.org/v2/top-headlines'
                params = {
                    'category': category,
                    'language': 'en',
                    'pageSize': 30,
                    'apiKey': NEWS_API_KEY
                }
                
                logging.info(f"Fetching {category} articles from NewsAPI...")
                response = requests.get(url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    articles = data.get('articles', [])
                    
                    logging.info(f"Received {len(articles)} articles for {category}")
                    
                    stored = store_articles(articles, category)
                    articles_stored += stored
                    articles_attempted += len(articles)
                    
                    logging.info(f"Category {category}: stored {stored}/{len(articles)} articles")
                else:
                    logging.error(f"NewsAPI error for {category}: {response.status_code} - {response.text}")
                
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                logging.error(f"Error fetching {category}: {str(e)}")
        
        return jsonify({
            "message": f"Successfully stored {articles_stored} articles",
            "articles_stored": articles_stored,
            "articles_attempted": articles_attempted
        }), 200
        
    except Exception as e:
        logging.error(f"Error in fetch_news: {str(e)}")
        return jsonify({"error": str(e)}), 500

def store_articles(articles, category):
    """Store articles in Firestore with deduplication"""
    stored_count = 0
    
    for article in articles:
        try:
            # Skip invalid articles
            title = article.get('title', '')
            description = article.get('description', '')
            
            if not title or title == '[Removed]':
                continue
            if not description or description == '[Removed]':
                continue
            
            url = article.get('url', '')
            if not url:
                continue
            
            # Check for duplicates by URL
            existing_query = db.collection('articles').where('url', '==', url).limit(1)
            existing_docs = list(existing_query.stream())
            
            if len(existing_docs) > 0:
                logging.info(f"Skipping duplicate: {title[:50]}")
                continue
            
            # Generate unique article ID
            article_id = str(uuid.uuid4())
            
            # Handle image URL - use placeholder for blocked images
            image_url = article.get('urlToImage', '')
            if not image_url or 'wsj.com' in image_url.lower():
                image_url = PLACEHOLDER_IMAGE
            
            # Create article document
            article_data = {
                'article_id': article_id,
                'title': title.strip(),
                'content': description.strip(),
                'category': category.lower(),
                'publish_date': datetime.now(),
                'source': article.get('source', {}).get('name', 'Unknown'),
                'image_url': image_url,
                'url': url,
                'author': article.get('author', ''),
                'created_at': firestore.SERVER_TIMESTAMP
            }
            
            # Store in Firestore
            db.collection('articles').document(article_id).set(article_data)
            stored_count += 1
            
            logging.info(f"Stored: [{category}] {title[:50]}")
            
        except Exception as e:
            logging.error(f"Error storing article: {str(e)}")
            continue
    
    return stored_count

@app.route('/news', methods=['GET'])
def get_news():
    """Get news articles with optional category filter"""
    try:
        category = request.args.get('category', '').lower()
        limit = int(request.args.get('limit', 30))
        
        logging.info(f"GET /news - category: '{category}', limit: {limit}")
        
        # Build query
        articles_ref = db.collection('articles')
        
        # Apply category filter if provided
        if category and category != 'all' and category != '':
            logging.info(f"Filtering by category: {category}")
            query = articles_ref.where('category', '==', category)
        else:
            logging.info("No category filter - fetching all articles")
            query = articles_ref
        
        # Order by publish date and limit
        query = query.order_by('publish_date', direction=firestore.Query.DESCENDING).limit(limit)
        
        # Execute query
        articles_stream = query.stream()
        articles_list = list(articles_stream)
        
        logging.info(f"Query returned {len(articles_list)} articles")
        
        # Convert to dictionary
        result = []
        for doc in articles_list:
            article_data = doc.to_dict()
            
            # Ensure article_id is present
            if 'article_id' not in article_data:
                article_data['article_id'] = doc.id
            
            # Ensure image_url has fallback
            image_url = article_data.get('image_url', '')
            if not image_url:
                article_data['image_url'] = PLACEHOLDER_IMAGE
            
            result.append(article_data)
        
        logging.info(f"Returning {len(result)} articles")
        
        return jsonify({
            "articles": result,
            "count": len(result),
            "category": category if category else "all"
        }), 200
        
    except Exception as e:
        logging.error(f"Error in get_news: {str(e)}", exc_info=True)
        # Return empty array instead of error to prevent frontend crash
        return jsonify({
            "articles": [],
            "count": 0,
            "error": str(e)
        }), 200

@app.route('/news/count', methods=['GET'])
def count_articles():
    """Get count of articles by category"""
    try:
        categories = ['technology', 'business', 'sports', 'entertainment', 'science']
        counts = {}
        
        for category in categories:
            query = db.collection('articles').where('category', '==', category)
            docs = list(query.stream())
            counts[category] = len(docs)
        
        # Total count
        all_docs = list(db.collection('articles').stream())
        counts['total'] = len(all_docs)
        
        logging.info(f"Article counts: {counts}")
        
        return jsonify(counts), 200
        
    except Exception as e:
        logging.error(f"Error counting articles: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/news/debug', methods=['GET'])
def debug_articles():
    """Debug endpoint to see all articles"""
    try:
        articles = list(db.collection('articles').limit(5).stream())
        
        result = []
        for doc in articles:
            data = doc.to_dict()
            # Ensure image_url fallback in debug too
            image_url = data.get('image_url', PLACEHOLDER_IMAGE)
            result.append({
                'id': doc.id,
                'title': data.get('title', '')[:50],
                'category': data.get('category', ''),
                'source': data.get('source', ''),
                'image_url': image_url
            })
        
        total = len(list(db.collection('articles').stream()))
        
        return jsonify({
            "total_articles": total,
            "sample_articles": result
        }), 200
        
    except Exception as e:
        logging.error(f"Error in debug: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
