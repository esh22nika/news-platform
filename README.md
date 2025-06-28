# Personalized News Feed Platform

## Project Overview
- A news app delivering personalized articles based on user interests.
- Built using GCP services:
  - Cloud Storage
  - Cloud Run
  - Pub/Sub
  - BigQuery
  - Firestore

## Services Used

### Cloud Storage
- Bucket: [your bucket name]
- Folders:
  - user-profiles/
  - news-content/images/
- Permissions: images folder public

### Firestore
- Mode: Native
- Collections:
  - users
  - articles

### BigQuery
- Dataset: news_platform_demo
- Tables:
  - user_engagement
    - user_id (INT64)
    - article_id (STRING)
    - event_type (STRING)
    - timestamp (TIMESTAMP)

### Pub/Sub
- Topics:
  - user-clicks
  - user-likes
- Subscriptions:
  - clicks-processor

### Cloud Run
- Services deployed:
  - user-service
  - news-service

## Manual Console Steps

- Enabled APIs:
  - Cloud Run
  - Firestore
  - Pub/Sub
  - BigQuery
  - Cloud Storage

- Created Cloud Storage bucket:
  - Name: [bucket name]
  - Region: us-central1

- Created Firestore database in Native mode.

- Created Pub/Sub topics:
  - user-clicks
  - user-likes

- Created BigQuery dataset and tables.

## How to Deploy

- Push code to Cloud Run
- Create Firestore collections
- Deploy frontend to Cloud Storage bucket
