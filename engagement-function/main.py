# engagement-function/main.py
import base64
import json
import logging
from google.cloud import bigquery
import functions_framework

# Initialize BigQuery client
client = bigquery.Client()
table_id = "news_platform_new.user_engagement"

@functions_framework.cloud_event
def process_engagement(cloud_event):
    """Process user engagement events from Pub/Sub"""
    try:
        # Decode the Pub/Sub message
        pubsub_message = base64.b64decode(cloud_event.data["message"]["data"]).decode()
        event_data = json.loads(pubsub_message)
        
        logging.info(f"Processing engagement event: {event_data}")
        
        # Prepare data for BigQuery
        rows_to_insert = [{
            "user_id": event_data.get("user_id"),
            "article_id": event_data.get("article_id"),
            "event_type": event_data.get("event_type"),
            "timestamp": event_data.get("timestamp"),
            "session_id": event_data.get("session_id"),
            "device_type": event_data.get("device_type", "web"),
            "reading_time_seconds": event_data.get("reading_time_seconds", 0),
            "scroll_depth": event_data.get("scroll_depth", 0.0)
        }]
        
        # Insert into BigQuery
        errors = client.insert_rows_json(table_id, rows_to_insert)
        
        if errors:
            logging.error(f"BigQuery insert errors: {errors}")
            return f"Error inserting data: {errors}", 500
        
        logging.info(f"Successfully processed engagement event for user {event_data.get('user_id')}")
        return "OK", 200
        
    except Exception as e:
        logging.error(f"Error processing engagement: {str(e)}")
        return f"Error: {str(e)}", 500
