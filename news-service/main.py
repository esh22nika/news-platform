# news-service/main.py
import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from google.cloud import firestore, storage
import logging
from datetime import datetime, timedelta
import uuid
import time

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
logging.basicConfig(level=logging.INFO)

# Initialize clients
db = firestore.Client()
storage_client = storage.Client()

# News API key
NEWS_API_KEY = 'ae5d578c6235410d864d5be2af511cce'

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "service": "news-service"}), 200

@app.route('/news/fetch', methods=['POST'])
def fetch_news():
    """Fetch news from external APIs and store in Firestore - Enhanced version"""
    try:
        # Define categories with specific search queries for better results
        category_queries = {
            'technology': ['tech', 'technology', 'AI', 'software', 'Apple', 'Google', 'Microsoft'],
            'business': ['business', 'finance', 'stocks', 'economy', 'startup', 'investment'],
            'health': ['health', 'medical', 'wellness', 'healthcare'],
            'sports': ['sports', 'football', 'basketball', 'cricket', 'tennis'],
            'entertainment': ['entertainment', 'movies', 'music', 'celebrity', 'hollywood'],
            'science': ['science', 'research', 'space', 'NASA', 'climate']
        }
        
        articles_stored = 0
        articles_attempted = 0
        
        # Method 1: Top headlines by category
        for category in category_queries.keys():
            try:
                url = 'https://newsapi.org/v2/top-headlines'
                params = {
                    'category': category,
                    'language': 'en',
                    'pageSize': 20,  # Increased from 10
                    'apiKey': NEWS_API_KEY
                }
                
                response = requests.get(url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    stored = store_articles(data.get('articles', []), category)
                    articles_stored += stored
                    articles_attempted += len(data.get('articles', []))
                    logging.info(f"Category {category}: stored {stored} articles")
                else:
                    logging.error(f"NewsAPI error for {category}: {response.status_code}")
                
                time.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                logging.error(f"Error fetching {category}: {str(e)}")
        
        # Method 2: Search for specific tech and business keywords
        priority_searches = {
            'technology': ['artificial intelligence', 'machine learning', 'cryptocurrency', 'blockchain', 'cybersecurity'],
            'business': ['stock market', 'IPO', 'merger', 'earnings', 'venture capital']
        }
        
        for category, keywords in priority_searches.items():
            for keyword in keywords:
                try:
                    url = 'https://newsapi.org/v2/everything'
                    params = {
                        'q': keyword,
                        'language': 'en',
                        'sortBy': 'publishedAt',
                        'pageSize': 10,
                        'from': (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d'),
                        'apiKey': NEWS_API_KEY
                    }
                    
                    response = requests.get(url, params=params, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        stored = store_articles(data.get('articles', []), category)
                        articles_stored += stored
                        articles_attempted += len(data.get('articles', []))
                        logging.info(f"Keyword '{keyword}': stored {stored} articles")
                    
                    time.sleep(0.5)  # Rate limiting
                    
                except Exception as e:
                    logging.error(f"Error fetching keyword {keyword}: {str(e)}")
        
        # Method 3: Top sources for tech and business
        tech_sources = 'techcrunch,the-verge,wired,ars-technica,hacker-news'
        business_sources = 'bloomberg,financial-times,the-wall-street-journal,business-insider'
        
        for sources, category in [(tech_sources, 'technology'), (business_sources, 'business')]:
            try:
                url = 'https://newsapi.org/v2/top-headlines'
                params = {
                    'sources': sources,
                    'language': 'en',
                    'pageSize': 20,
                    'apiKey': NEWS_API_KEY
                }
                
                response = requests.get(url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    stored = store_articles(data.get('articles', []), category)
                    articles_stored += stored
                    articles_attempted += len(data.get('articles', []))
                    logging.info(f"Sources for {category}: stored {stored} articles")
                
                time.sleep(0.5)
                
            except Exception as e:
                logging.error(f"Error fetching from sources: {str(e)}")
        
        return jsonify({
            "message": f"Successfully stored {articles_stored} articles out of {articles_attempted} attempted",
            "articles_stored": articles_stored,
            "articles_attempted": articles_attempted
        }), 200
        
    except Exception as e:
        logging.error(f"Error in fetch_news: {str(e)}")
        return jsonify({"error": str(e)}), 500

def store_articles(articles, category):
    """Helper function to store articles in Firestore"""
    stored_count = 0
    
    for article in articles:
        try:
            # Skip articles without titles or removed content
            if not article.get('title') or article.get('title') == '[Removed]':
                continue
            
            if not article.get('description') or article.get('description') == '[Removed]':
                continue
            
            # Check if article already exists (by URL)
            url = article.get('url', '')
            if url:
                existing = db.collection('articles').where('url', '==', url).limit(1).stream()
                if len(list(existing)) > 0:
                    continue  # Skip duplicate
            
            article_id = str(uuid.uuid4())
            
            # Store article in Firestore
            article_data = {
                'article_id': article_id,
                'title': article.get('title', '').strip(),
                'content': article.get('description', '').strip(),
                'category': category,
                'publish_date': datetime.now(),
                'source': article.get('source', {}).get('name', ''),
                'image_url': article.get('urlToImage', ''),
                'url': url,
                'author': article.get('author', ''),
                'created_at': firestore.SERVER_TIMESTAMP
            }
            
            db.collection('articles').document(article_id).set(article_data)
            stored_count += 1
            
        except Exception as e:
            logging.error(f"Error storing individual article: {str(e)}")
            continue
    
    return stored_count

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
            # Ensure article_id is present
            if 'article_id' not in article_data:
                article_data['article_id'] = article.id
            result.append(article_data)
        
        logging.info(f"Returning {len(result)} articles for category: {category or 'all'}")
        
        return jsonify({
            "articles": result,
            "count": len(result)
        }), 200
        
    except Exception as e:
        logging.error(f"Error getting news: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/news/count', methods=['GET'])
def count_articles():
    """Get count of articles by category"""
    try:
        categories = ['technology', 'business', 'health', 'sports', 'entertainment', 'science']
        counts = {}
        
        for category in categories:
            articles = db.collection('articles').where('category', '==', category).stream()
            counts[category] = len(list(articles))
        
        total = sum(counts.values())
        counts['total'] = total
        
        return jsonify(counts), 200
        
    except Exception as e:
        logging.error(f"Error counting articles: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/news/clear', methods=['POST'])
def clear_old_articles():
    """Clear articles older than 7 days (optional maintenance endpoint)"""
    try:
        cutoff_date = datetime.now() - timedelta(days=7)
        
        articles = db.collection('articles').where('publish_date', '<', cutoff_date).stream()
        
        deleted_count = 0
        for article in articles:
            article.reference.delete()
            deleted_count += 1
        
        return jsonify({
            "message": f"Deleted {deleted_count} old articles",
            "deleted_count": deleted_count
        }), 200
        
    except Exception as e:
        logging.error(f"Error clearing articles: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
