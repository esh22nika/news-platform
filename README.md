
# Personalized News Feed Platform

## Overview

This is a **cloud-native news delivery application** that allows users to sign up with their **name, email, and interests**, view trending news, and interact via **likes and shares**. All engagement is tracked in real time using Google Cloud services.

🔗 **Live Frontend**:  
[https://storage.googleapis.com/news-platform-demo-frontend/index.html](https://storage.googleapis.com/news-platform-demo-frontend/index.html)

---

## 🔧 GCP Services Used

| GCP Service       | Purpose                                                                 |
|-------------------|-------------------------------------------------------------------------|
| **Cloud Run**      | Hosts `user-service` and `news-service` as REST APIs                    |
| **Cloud Functions**| Processes `engagement` Pub/Sub events and writes to BigQuery            |
| **Pub/Sub**        | Streams engagement data (like/share events)                             |
| **Firestore**      | Stores user profiles with interests, name, and email                    |
| **BigQuery**       | Stores and analyzes engagement events                                   |
| **Cloud Storage**  | Hosts the frontend as a static website and stores images                |



---

## Project Architecture

```

User Signup (HTML)
↓
User Service (Cloud Run) → Firestore (users)
↓
News Service (Cloud Run) → Firestore (news articles)
↓
Frontend fetches news
↓
Engagement (Like/Share) → Pub/Sub → Cloud Function → BigQuery

```

---

##  Project Structure

```

news-platform/
├── frontend/
│   ├── index.html
│   ├── script.js
│   └── styles.css
├── user-service/
│   ├── main.py
│   └── requirements.txt
├── news-service/
│   ├── main.py
│   └── requirements.txt
├── engagement-function/
│   ├── main.py
│   └── requirements.txt
└── README.md

````

---

## 🔨 Deployment Steps

### 1. **Enable Required APIs**

Enable these in your GCP project:

- Cloud Run  
- Cloud Functions  
- Firestore  
- Pub/Sub  
- BigQuery  
- Cloud Storage  
- Cloud Build

---

### 2. **Firestore Setup**

- Go to **Firestore → Create database**
- Select **Native mode**
- Region: `asia-south1`

Collections used:

- `users` → for user profiles
- `articles` → news articles fetched via News API

---

### 3. **BigQuery Setup**

- Dataset name: `news_platform_demo`
- Table: `user_engagement`

Schema:

```plaintext
user_id: STRING  
article_id: STRING  
event_type: STRING  
timestamp: TIMESTAMP  
session_id: STRING  
device_type: STRING  
reading_time_seconds: INTEGER  
scroll_depth: FLOAT  
````

---

### 4. **Pub/Sub Setup**

* Create topic: `engagement-topic`

---

### 5. **Deploy Cloud Run Services**

#### 🟦 user-service

```bash
gcloud run deploy user-service \
  --source . \
  --region asia-south1 \
  --platform managed \
  --allow-unauthenticated
```

✅ Handles `/users` creation + `/engagement` publishing to Pub/Sub
💡 Add CORS headers using `flask-cors` to allow frontend access.

---

#### 🟨 news-service

```bash
gcloud run deploy news-service \
  --source . \
  --region asia-south1 \
  --platform managed \
  --allow-unauthenticated
```

✅ Handles `/news` and `/news/fetch`
🗞️ News articles are pulled from [NewsData.io](https://newsdata.io/) and stored in Firestore.

---

### 6. **Deploy Cloud Function**

```bash
gcloud functions deploy process_engagement \
  --gen2 \
  --runtime python312 \
  --trigger-topic engagement-topic \
  --region asia-south1 \
  --entry-point process_engagement \
  --allow-unauthenticated
```

✅ Inserts Pub/Sub events into BigQuery.

---

### 7. **Deploy Frontend**

```bash
# Create bucket
gsutil mb -l asia-south1 gs://news-platform-demo-frontend/

# Upload frontend files
gsutil cp index.html styles.css script.js gs://news-platform-demo-frontend/

# Make public
gsutil iam ch allUsers:objectViewer gs://news-platform-demo-frontend/

# Set static website config
gsutil web set -m index.html -e 404.html gs://news-platform-demo-frontend/
```

Frontend will be live at:
📍 `https://storage.googleapis.com/news-platform-demo-frontend/index.html`

---

## ✅ Features Completed

| Feature                                 | Status |
| --------------------------------------- | ------ |
| User signup with name, email, interests | ✅      |
| Store users in Firestore                | ✅      |
| Fetch real news via API and show it     | ✅      |
| Like and Share buttons on each article  | ✅      |
| Engagement stored via Pub/Sub           | ✅      |
| Real-time insert into BigQuery          | ✅      |
| Hosted frontend on Cloud Storage        | ✅      |
| Use of 4+ GCP services                  | ✅      |

---

## 🧪 Testing Tips

* Sign up → data should be visible in Firestore
* Like/Share → data should flow into BigQuery
* Check logs via:

```bash
gcloud functions logs read process_engagement --region asia-south1
```

---

## 🔍 Example Queries in BigQuery

```sql
-- Total likes and shares
SELECT event_type, COUNT(*) AS total
FROM `news_platform_demo.user_engagement`
GROUP BY event_type;

-- Most engaged articles
SELECT article_id, COUNT(*) AS events
FROM `news_platform_demo.user_engagement`
GROUP BY article_id
ORDER BY events DESC
LIMIT 10;
```

---


**Eshanika **
[GitHub Repo Link)](https://github.com/esh22nika/news-platform)



