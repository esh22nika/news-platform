# engagement-function/main.py - FIXED FOR BIGQUERY
import base64
import json
import logging
from google.cloud import bigquery
from datetime import datetime
import functions_framework

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize BigQuery client
client = bigquery.Client()
table_id = "news-platform-474717.news_platform_new.user_engagement"

@functions_framework.cloud_event
def process_engagement(cloud_event):
    """Process user engagement events from Pub/Sub and insert into BigQuery"""
    try:
        # Log the raw event
        logger.info(f"📨 Received cloud event: {cloud_event}")
        
        # Decode the Pub/Sub message
        pubsub_message = base64.b64decode(cloud_event.data["message"]["data"]).decode()
        logger.info(f"📩 Decoded message: {pubsub_message}")
        
        event_data = json.loads(pubsub_message)
        logger.info(f"📊 Parsed event data: {event_data}")
        
        # Prepare data for BigQuery with proper field mapping
        # Make sure timestamp is in proper format
        timestamp_str = event_data.get("timestamp")
        
        # Convert ISO format to datetime if needed
        if isinstance(timestamp_str, str):
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except:
                timestamp = datetime.utcnow()
        else:
            timestamp = datetime.utcnow()
        
        rows_to_insert = [{
            "user_id": str(event_data.get("user_id", "")),
            "article_id": str(event_data.get("article_id", "")),
            "event_type": str(event_data.get("event_type", "")),
            "timestamp": timestamp.isoformat(),
            "session_id": str(event_data.get("session_id", "")),
            "device_type": str(event_data.get("device_type", "web")),
            "reading_time_seconds": int(event_data.get("reading_time_seconds", 0)),
            "scroll_depth": float(event_data.get("scroll_depth", 0.0))
        }]
        
        logger.info(f"💾 Inserting row into BigQuery: {rows_to_insert}")
        
        # Insert into BigQuery
        errors = client.insert_rows_json(table_id, rows_to_insert)
        
        if errors:
            logger.error(f"❌ BigQuery insert errors: {errors}")
            return f"Error inserting data: {errors}", 500
        
        logger.info(f"✅ Successfully processed engagement event for user {event_data.get('user_id')}")
        logger.info(f"   Event type: {event_data.get('event_type')}, Article: {event_data.get('article_id')}")
        
        return "OK", 200
        
    except KeyError as e:
        logger.error(f"❌ Missing key in event data: {str(e)}")
        logger.error(f"   Cloud event data: {cloud_event.data}")
        return f"Missing key: {str(e)}", 400
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON decode error: {str(e)}")
        logger.error(f"   Raw message: {pubsub_message}")
        return f"JSON decode error: {str(e)}", 400
        
    except Exception as e:
        logger.error(f"❌ Error processing engagement: {str(e)}", exc_info=True)
        return f"Error: {str(e)}", 500
