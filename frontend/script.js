// frontend/script.js - COMPLETE FIXED VERSION
const API_BASE_URL = "https://user-service-piqssf56ka-el.a.run.app";
const NEWS_API_URL = "https://news-service-piqssf56ka-el.a.run.app/news";

let authToken = null;
let currentUserId = null;
let currentUsername = null;
let allArticles = [];
let likedArticles = new Set();

function saveAuth(token, userId, username) {
    authToken = token;
    currentUserId = userId;
    currentUsername = username;
    console.log('✅ Auth saved:', { userId, username });
}

function clearAuth() {
    authToken = null;
    currentUserId = null;
    currentUsername = null;
    allArticles = [];
    likedArticles.clear();
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
        const interestsInput = document.getElementById('register-interests').value;
        
        let interests;
        if (typeof interestsInput === 'string') {
            interests = interestsInput.split(',').map(i => i.trim().toLowerCase());
        } else {
            interests = interestsInput;
        }

        console.log('Registering with interests:', interests);

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
                showToast('Welcome! Your personalized feed is ready 🎉');
            } else {
                showMessage(data.error, 'error');
            }
        } catch (err) {
            console.error('Registration error:', err);
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
                showToast('Welcome back! 👋');
            } else {
                showMessage(data.error, 'error');
            }
        } catch (err) {
            console.error('Login error:', err);
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
            
            console.log('Category clicked:', category);
            
            if (category === 'recommended') {
                loadRecommendations();
            } else if (category === 'all') {
                loadArticles(null);
            } else {
                loadArticles(category);
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
    
    loadRecommendations();
    
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    document.querySelector('[data-category="recommended"]')?.classList.add('active');
}

function showMessage(msg, type) {
    const messageDiv = document.getElementById('auth-message');
    messageDiv.textContent = msg;
    messageDiv.className = `auth-message ${type}`;
    messageDiv.style.display = 'block';
}

async function loadArticles(category) {
    console.log('🔄 Loading articles for category:', category || 'all');
    
    document.getElementById('loading').style.display = 'block';
    document.getElementById('news-container').innerHTML = '';
    document.getElementById('error').style.display = 'none';

    try {
        let url = NEWS_API_URL;
        if (category && category !== 'all') {
            url += `?category=${category}`;
        }
        
        console.log('Fetching from:', url);
        
        const response = await fetch(url);
        const data = await response.json();
        
        console.log('Response data:', data);
        
        // Validate response
        if (data && data.articles && Array.isArray(data.articles)) {
            if (data.articles.length > 0) {
                allArticles = data.articles;
                renderArticles(data.articles);
                console.log(`✅ Loaded ${data.articles.length} articles`);
                if (category) {
                    showToast(`Showing ${data.articles.length} ${category} articles`);
                }
            } else {
                // No articles found
                document.getElementById('news-container').innerHTML = 
                    `<div style="text-align: center; padding: 40px; color: #64748b;">
                        <p>No ${category || ''} articles found.</p>
                        <p style="margin-top: 10px; font-size: 0.9em;">Try fetching news by running:</p>
                        <code style="background: #f1f5f9; padding: 8px 12px; border-radius: 4px; display: inline-block; margin-top: 8px;">
                            curl -X POST ${NEWS_API_URL.replace('/news', '/news/fetch')}
                        </code>
                    </div>`;
                allArticles = [];
            }
        } else {
            console.error('Invalid response format:', data);
            throw new Error('Invalid response format from server');
        }
    } catch (err) {
        console.error('❌ Error loading articles:', err);
        document.getElementById('error').textContent = `Failed to load news: ${err.message}`;
        document.getElementById('error').style.display = 'block';
        allArticles = [];
    } finally {
        document.getElementById('loading').style.display = 'none';
    }
}

async function loadRecommendations() {
    console.log('🔄 Loading recommendations...');
    
    document.getElementById('loading').style.display = 'block';
    document.getElementById('news-container').innerHTML = '';
    document.getElementById('error').style.display = 'none';

    try {
        const response = await fetch(`${API_BASE_URL}/users/me/recommendations`, {
            headers: getAuthHeaders()
        });
        
        const data = await response.json();
        
        console.log('Recommendations response:', data);
        
        if (data && data.articles && Array.isArray(data.articles)) {
            if (data.articles.length > 0) {
                allArticles = data.articles;
                
                // Track liked articles
                data.articles.forEach(article => {
                    if (article.is_liked) {
                        likedArticles.add(article.article_id);
                    }
                });
                
                renderArticles(data.articles);
                console.log(`✅ Loaded ${data.articles.length} recommendations`);
                
                if (data.based_on && data.based_on.length > 0) {
                    showToast(`Personalized feed based on: ${data.based_on.join(', ')}`);
                }
            } else {
                // Fallback message
                document.getElementById('news-container').innerHTML = 
                    '<div style="text-align: center; padding: 40px; color: #64748b;">Building your personalized feed... Like some articles to improve recommendations!</div>';
                setTimeout(() => loadArticles(null), 1000);
            }
        } else {
            console.warn('No recommendations, falling back to all articles');
            loadArticles(null);
        }
    } catch (err) {
        console.error('❌ Error loading recommendations:', err);
        loadArticles(null);
    } finally {
        document.getElementById('loading').style.display = 'none';
    }
}

function renderArticles(articles) {
    const container = document.getElementById('news-container');
    container.innerHTML = '';
    
    if (!articles || !Array.isArray(articles) || articles.length === 0) {
        container.innerHTML = '<div style="text-align: center; padding: 40px; color: #64748b;">No articles available.</div>';
        return;
    }
    
    console.log(`Rendering ${articles.length} articles`);
    
    articles.forEach(article => {
        const div = document.createElement('div');
        div.className = 'news-article';
        
        const isLiked = likedArticles.has(article.article_id);
        const likedClass = isLiked ? 'liked' : '';
        const likedIcon = isLiked ? '❤️' : '🤍';
        
        const imageUrl = article.image_url || 'https://via.placeholder.com/400x200/3b82f6/ffffff?text=News+Article';
        
        div.innerHTML = `
            <div class="article-image" style="background-image: url('${imageUrl}')"></div>
            <div class="article-content">
                <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px;">
                    <span class="article-category">${article.category || 'General'}</span>
                    ${article.recommendation_reason ? `<span class="article-badge">✨ ${article.recommendation_reason}</span>` : ''}
                </div>
                <h3 class="article-title">${article.title || 'No Title'}</h3>
                <div class="article-meta">
                    <span>${article.source || 'Unknown'}</span>
                    <span>${article.publish_date ? new Date(article.publish_date.seconds * 1000 || article.publish_date).toLocaleDateString() : 'Recently'}</span>
                </div>
                <p class="article-summary">${article.content || 'No description available.'}</p>
                <div class="engagement-section">
                    <div class="engagement-buttons">
                        <button class="btn btn-like ${likedClass}" data-article-id="${article.article_id}">
                            ${likedIcon} ${isLiked ? 'Liked' : 'Like'}
                        </button>
                        <button class="btn btn-share" data-article-id="${article.article_id}">🔗 Share</button>
                    </div>
                </div>
            </div>
        `;
        container.appendChild(div);
    });

    // Add event listeners for Like buttons
    document.querySelectorAll('.btn-like').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            const articleId = btn.dataset.articleId;
            const wasLiked = likedArticles.has(articleId);
            
            console.log(`${wasLiked ? 'Unlike' : 'Like'} clicked for article:`, articleId);
            
            if (wasLiked) {
                // Unlike
                likedArticles.delete(articleId);
                btn.classList.remove('liked');
                btn.innerHTML = '🤍 Like';
                showToast('Removed from favorites');
            } else {
                // Like - publish engagement event
                const success = await publishEngagement('like', articleId);
                if (success) {
                    likedArticles.add(articleId);
                    btn.classList.add('liked');
                    btn.innerHTML = '❤️ Liked';
                    showToast('Added to favorites! Check "For You" 💖');
                } else {
                    showToast('Failed to like article. Please try again.');
                }
            }
        });
    });

    // Add event listeners for Share buttons
    document.querySelectorAll('.btn-share').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            const articleId = btn.dataset.articleId;
            console.log('Share clicked for article:', articleId);
            
            const success = await publishEngagement('share', articleId);
            if (success) {
                showToast('Shared! 🎉');
            } else {
                showToast('Failed to share. Please try again.');
            }
        });
    });
}

function filterArticles(query) {
    if (!query) {
        renderArticles(allArticles);
        return;
    }
    
    const filtered = allArticles.filter(article => {
        const title = (article.title || '').toLowerCase();
        const content = (article.content || '').toLowerCase();
        const category = (article.category || '').toLowerCase();
        
        return title.includes(query) || content.includes(query) || category.includes(query);
    });
    
    renderArticles(filtered);
    
    if (filtered.length === 0) {
        document.getElementById('news-container').innerHTML = 
            '<div style="text-align: center; padding: 40px; color: #64748b;">No articles match your search.</div>';
    }
}

async function publishEngagement(type, articleId) {
    console.log(`📤 Publishing ${type} engagement for article:`, articleId);
    
    try {
        const engagementData = {
            article_id: articleId,
            event_type: type,
            session_id: 'session_' + Date.now(),
            device_type: 'web',
            reading_time_seconds: 0,
            scroll_depth: 0.0
        };
        
        console.log('Engagement data:', engagementData);
        
        const response = await fetch(`${API_BASE_URL}/engagement`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(engagementData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            console.log('✅ Engagement published successfully:', result);
            return true;
        } else {
            console.error('❌ Engagement failed:', result);
            return false;
        }
    } catch (err) {
        console.error('❌ Engagement error:', err);
        return false;
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

window.addEventListener('scroll', () => {
    const btn = document.getElementById('backToTopBtn');
    if (window.pageYOffset > 300) {
        btn.style.display = 'block';
    } else {
        btn.style.display = 'none';
    }
});

// Expose authToken for debugging
window.getAuthToken = () => {
    console.log('Current auth token:', authToken);
    return authToken;
};
