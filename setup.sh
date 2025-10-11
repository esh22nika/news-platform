#!/bin/bash

# Deploy all services for news-platform-474717

set -e

PROJECT_ID="news-platform-474717"
REGION="asia-south1"

echo "🚀 Deploying all services..."
echo ""

# Deploy User Service
echo "1/3 Deploying User Service..."
cd user-service
gcloud run deploy user-service \
    --source . \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --set-env-vars PROJECT_ID=$PROJECT_ID

USER_SERVICE_URL=$(gcloud run services describe user-service --region $REGION --format 'value(status.url)')
echo "✅ User Service deployed: $USER_SERVICE_URL"
echo ""

# Deploy News Service
echo "2/3 Deploying News Service..."
cd ../news-service
gcloud run deploy news-service \
    --source . \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1

NEWS_SERVICE_URL=$(gcloud run services describe news-service --region $REGION --format 'value(status.url)')
echo "✅ News Service deployed: $NEWS_SERVICE_URL"
echo ""

# Deploy Engagement Function
echo "3/3 Deploying Engagement Function..."
cd ../engagement-function
gcloud functions deploy process_engagement \
    --gen2 \
    --runtime python312 \
    --trigger-topic engagement-topic \
    --region $REGION \
    --entry-point process_engagement \
    --allow-unauthenticated \
    --memory 256Mi \
    --timeout 60s

echo "✅ Engagement Function deployed"
echo ""

# Update frontend with service URLs
echo "📝 Updating frontend configuration..."
cd ../frontend

cat > config.js << EOF
// Auto-generated configuration
const API_BASE_URL = "$USER_SERVICE_URL";
const NEWS_API_URL = "$NEWS_SERVICE_URL/news";
EOF

# Update script.js to use correct URLs
cat > script.js << 'SCRIPTJS'
// CONFIG - Auto-updated by deploy script
const API_BASE_URL = "${USER_SERVICE_URL}";
const NEWS_API_URL = "${NEWS_SERVICE_URL}/news";

let authToken = null;
let currentUserId = null;
let currentUsername = null;

function saveAuth(token, userId, username) {
    authToken = token;
    currentUserId = userId;
    currentUsername = username;
}

function clearAuth() {
    authToken = null;
    currentUserId = null;
    currentUsername = null;
}

function getAuthHeaders() {
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`
    };
}

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById('show-register')?.addEventListener('click', (e) => {
        e.preventDefault();
        document.getElementById('login-form-container').classList.remove('active');
        document.getElementById('register-form-container').classList.add('active');
    });

    document.getElementById('show-login')?.addEventListener('click', (e) => {
        e.preventDefault();
        document.getElementById('register-form-container').classList.remove('active');
        document.getElementById('login-form-container').classList.add('active');
    });

    document.getElementById('register-form')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('register-username').value;
        const email = document.getElementById('register-email').value;
        const password = document.getElementById('register-password').value;
        const interests = document.getElementById('register-interests').value.split(',').map(i => i.trim());

        try {
            const response = await fetch(`${API_BASE_URL}/auth/register`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({username, email, password, interests})
            });
            
            const data = await response.json();
            if (response.ok) {
                saveAuth(data.token, data.user_id, data.username);
                showNews();
            } else {
                showMessage(data.error, 'error');
            }
        } catch (err) {
            showMessage('Registration failed', 'error');
        }
    });

    document.getElementById('login-form')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('login-email').value;
        const password = document.getElementById('login-password').value;

        try {
            const response = await fetch(`${API_BASE_URL}/auth/login`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({email, password})
            });
            
            const data = await response.json();
            if (response.ok) {
                saveAuth(data.token, data.user_id, data.username);
                showNews();
            } else {
                showMessage(data.error, 'error');
            }
        } catch (err) {
            showMessage('Login failed', 'error');
        }
    });

    document.getElementById('logout-btn')?.addEventListener('click', () => {
        clearAuth();
        document.getElementById('auth-section').style.display = 'block';
        document.getElementById('news-section').style.display = 'none';
    });

    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const category = btn.dataset.category;
            if (category === 'recommended') {
                loadRecommendations();
            } else {
                loadArticles(category === 'all' ? null : category);
            }
        });
    });

    document.getElementById('searchInput')?.addEventListener('input', (e) => {
        filterArticles(e.target.value.toLowerCase());
    });
});

function showNews() {
    document.getElementById('auth-section').style.display = 'none';
    document.getElementById('news-section').style.display = 'block';
    document.getElementById('user-name').textContent = `Welcome, ${currentUsername}!`;
    loadArticles();
}

function showMessage(msg, type) {
    const messageDiv = document.getElementById('auth-message');
    messageDiv.textContent = msg;
    messageDiv.className = `auth-message ${type}`;
    messageDiv.style.display = 'block';
}

async function loadArticles(category) {
    document.getElementById('loading').style.display = 'block';
    document.getElementById('news-container').innerHTML = '';

    try {
        let url = NEWS_API_URL;
        if (category) url += `?category=${category}`;
        
        const response = await fetch(url);
        const data = await response.json();
        renderArticles(data.articles);
    } catch (err) {
        console.error(err);
        document.getElementById('error').textContent = 'Failed to load news';
        document.getElementById('error').style.display = 'block';
    } finally {
        document.getElementById('loading').style.display = 'none';
    }
}

async function loadRecommendations() {
    document.getElementById('loading').style.display = 'block';
    document.getElementById('news-container').innerHTML = '';

    try {
        const response = await fetch(`${API_BASE_URL}/users/me/recommendations`, {
            headers: getAuthHeaders()
        });
        const data = await response.json();
        renderArticles(data.articles);
        showToast(`Recommendations based on: ${data.based_on.join(', ')}`);
    } catch (err) {
        console.error(err);
        loadArticles();
    } finally {
        document.getElementById('loading').style.display = 'none';
    }
}

function renderArticles(articles) {
    const container = document.getElementById('news-container');
    container.innerHTML = '';
    
    articles.forEach(article => {
        const div = document.createElement('div');
        div.className = 'news-article';
        div.innerHTML = `
            <div class="article-image" style="background-image: url('${article.image_url || ''}')"></div>
            <div class="article-content">
                <span class="article-category">${article.category || ''}</span>
                <h3 class="article-title">${article.title || 'No Title'}</h3>
                <div class="article-meta">
                    <span>${article.source || ''}</span>
                    <span>${new Date(article.publish_date).toLocaleDateString()}</span>
                </div>
                <p class="article-summary">${article.content || ''}</p>
                <div class="engagement-section">
                    <div class="engagement-buttons">
                        <button class="btn btn-like" data-article-id="${article.article_id}">❤️ Like</button>
                        <button class="btn btn-share" data-article-id="${article.article_id}">🔗 Share</button>
                    </div>
                </div>
            </div>
        `;
        container.appendChild(div);
    });

    document.querySelectorAll('.btn-like').forEach(btn => {
        btn.addEventListener('click', () => {
            publishEngagement('like', btn.dataset.articleId);
            btn.classList.add('liked');
            showToast('Liked!');
        });
    });

    document.querySelectorAll('.btn-share').forEach(btn => {
        btn.addEventListener('click', () => {
            publishEngagement('share', btn.dataset.articleId);
            showToast('Shared!');
        });
    });
}

function filterArticles(query) {
    document.querySelectorAll('.news-article').forEach(article => {
        const title = article.querySelector('.article-title').textContent.toLowerCase();
        const summary = article.querySelector('.article-summary').textContent.toLowerCase();
        article.style.display = (title.includes(query) || summary.includes(query)) ? '' : 'none';
    });
}

async function publishEngagement(type, articleId) {
    try {
        await fetch(`${API_BASE_URL}/engagement`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                article_id: articleId,
                event_type: type,
                session_id: 'session_' + Date.now(),
                device_type: 'web'
            })
        });
    } catch (err) {
        console.error('Engagement error:', err);
    }
}

function showToast(message) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3000);
}

function scrollToTop() {
    window.scrollTo({top: 0, behavior: 'smooth'});
}
SCRIPTJS

# Replace placeholder URLs in script.js
sed -i "s|\${USER_SERVICE_URL}|$USER_SERVICE_URL|g" script.js
sed -i "s|\${NEWS_SERVICE_URL}|$NEWS_SERVICE_URL|g" script.js

# Upload frontend to Cloud Storage
echo "📤 Uploading frontend to Cloud Storage..."
gsutil -m cp index.html styles.css script.js gs://news-platform-frontend-new/

FRONTEND_URL="https://storage.googleapis.com/news-platform-frontend-new/index.html"

echo ""
echo "=========================================="
echo "🎉 DEPLOYMENT COMPLETE!"
echo "=========================================="
echo ""
echo "📋 Service URLs:"
echo "  User Service:   $USER_SERVICE_URL"
echo "  News Service:   $NEWS_SERVICE_URL"
echo "  Frontend:       $FRONTEND_URL"
echo ""
echo "🧪 Test the services:"
echo ""
echo "1. Health check:"
echo "   curl $USER_SERVICE_URL/health"
echo ""
echo "2. Fetch news (first time):"
echo "   curl -X POST $NEWS_SERVICE_URL/news/fetch"
echo ""
echo "3. Open frontend:"
echo "   $FRONTEND_URL"
echo ""
echo "💡 Next steps:"
echo "  1. Open the frontend URL in your browser"
echo "  2. Register a new account"
echo "  3. Browse news and test like/share"
echo "  4. Check BigQuery for engagement data"
echo ""
