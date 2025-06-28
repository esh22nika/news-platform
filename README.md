# Personalized News Feed Platform

## Project Overview

The **Personalized News Feed Platform** is a cloud-native application that delivers real-time, AI-powered news feeds tailored to individual user interests. It also captures and analyzes engagement metrics (like clicks, likes, reading time) to continuously improve recommendations.

This project uses multiple GCP services to demonstrate scalable microservices, real-time data pipelines, serverless compute, and cloud-native storage.

**Live Demo**: [https://storage.googleapis.com/your-bucket-name/index.html](https://storage.googleapis.com/your-bucket-name/index.html)

This project satisfies all the Cloud Computing project guidelines: it uses 4+ services, has detailed documentation, and is hosted on a public GitHub repository.

---

## GCP Services Used

| Service | Role |
|--------|------|
| Cloud Storage | Host user profile data, news images, and the frontend |
| Pub/Sub | Stream engagement events (clicks, likes, reading time) |
| Cloud Run | Deploy the `user-service` and `news-service` |
| Firestore (Native Mode) | Store user profiles and article metadata |
| BigQuery | Analyze user behavior for trends and engagement |
| Cloud Functions | Process and insert events into BigQuery |
| (Optional) Dataflow | Future expansion for batch ML training |

---

## Visual GCP Setup (Console-Based)

### Step 1: Create a New GCP Project
1. Go to [https://console.cloud.google.com/](https://console.cloud.google.com/)
2. Click the project dropdown → "New Project"
3. Name your project (e.g., `news-platform-demo`) and create it.

---

### Step 2: Enable APIs
1. Go to **APIs & Services > Library**
2. Enable the following:
   - Cloud Run
   - Cloud Functions
   - Firestore
   - Cloud Pub/Sub
   - BigQuery
   - Cloud Storage
   - Cloud Build

---

### Step 3: Create a Service Account
1. Go to **IAM & Admin > Service Accounts**
2. Create a new service account (e.g., `news-platform-dev`)
3. Assign roles:
   - Editor
   - Cloud Run Admin
   - Pub/Sub Publisher
   - BigQuery Data Editor
   - Cloud Functions Developer
4. Generate and download a key (JSON format)

---

### Step 4: Create Cloud Storage Buckets
1. Go to **Cloud Storage > Buckets**
2. Create:
   - `news-platform-demo-storage` (for user profiles & news images)
   - `news-platform-demo-frontend` (for static website hosting)
3. Inside `news-platform-demo-storage`, create folders:
   - `user-profiles/`
   - `news-content/images/`
4. Make `news-content/images/` public for image access.
5. Configure `news-platform-demo-frontend` as a static website:
   - Main page: `index.html`
   - Error page: `404.html`

---

### Step 5: Initialize Firestore (Native Mode)
1. Go to **Firestore > Create Database**
2. Select Native Mode
3. Choose a region (e.g., `us-central1`) and finish setup.

---

### Step 6: Set Up BigQuery
1. Go to **BigQuery**
2. Create dataset: `news_platform_demo`
3. Create tables:
   - `user_engagement`
   - `articles`
   - `user_profiles`
4. Use schema fields as defined in the implementation.

---

### Step 7: Setup Pub/Sub Topics
1. Go to **Pub/Sub > Topics**
2. Create the following:
   - `user-clicks`
   - `user-likes`
   - `user-shares`
   - `user-reading-time`
3. For each topic, create a matching subscription (e.g., `clicks-processor`)

---

### Step 8: Deploy Cloud Run Services
Go to **Cloud Run > Deploy Service** and deploy the following services visually:

**user-service**
- Source: Upload zip or connect repo
- Runtime: Python
- Region: `us-central1`
- Memory: 512Mi
- Allow unauthenticated access

**news-service**
- Same steps as above, different service name

Take note of both service URLs for testing and frontend integration.

---

### Step 9: Deploy Cloud Functions
1. Go to **Cloud Functions > Create Function**
2. Create `process-engagement`:
   - Runtime: Python 3.9
   - Trigger: Pub/Sub → `user-clicks`
   - Source: Upload `main.py` and `requirements.txt`
3. Repeat for:
   - `process-likes` → `user-likes`
   - `process-shares` → `user-shares`

---

### Step 10: Deploy Frontend to Cloud Storage
1. Prepare your `index.html`
2. Upload it to the bucket `news-platform-demo-frontend`
3. Make the file public
4. Set the bucket to host a website under **Website Configuration**
5. Your live URL will be:
https://storage.googleapis.com/news-platform-demo-frontend/index.html

---

## Testing Checklist

- [x] User API: Create, get, update users via Cloud Run
- [x] News API: Fetch and display categorized news
- [x] Frontend: Dynamic feed with engagement tracking
- [x] Pub/Sub: Stream and observe real-time user events
- [x] BigQuery: Track event counts and patterns
- [x] Cloud Function: Logs show real-time inserts to BigQuery

---

## Analytics Dashboard (BigQuery)

Create views in BigQuery like:

```sql
-- Daily User Activity
SELECT DATE(timestamp) AS date, COUNT(DISTINCT user_id) AS users
FROM `news_platform_demo.user_engagement`
GROUP BY date
ORDER BY date DESC;

#project structure

news-platform/
├── services/
│   ├── user-service/
│   └── news-service/
├── functions/
│   └── engagement-function/
├── frontend/
│   └── index.html
├── README.md
└── .gitignore
