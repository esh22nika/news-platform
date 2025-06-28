// CONFIG - put your real URLs here
const NEWS_API_URL = "";
const USER_SERVICE_URL = "";
const ENGAGEMENT_URL = "";

document.addEventListener("DOMContentLoaded", () => {
  loadArticles("all");

  document.querySelectorAll(".filter-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const category = btn.dataset.category;
      loadArticles(category === "all" ? null : category);
    });
  });

  document.getElementById("searchInput").addEventListener("input", (e) => {
    const query = e.target.value.toLowerCase();
    filterArticles(query);
  });
});

function loadArticles(category) {
  document.getElementById("loading").style.display = "block";
  document.getElementById("news-container").innerHTML = "";

  let url = NEWS_API_URL;
  if (category) {
    url += `?category=${category}`;
  }

  fetch(url)
    .then(res => res.json())
    .then(data => {
      renderArticles(data.articles);
      document.getElementById("loading").style.display = "none";
    })
    .catch(err => {
      console.error(err);
      document.getElementById("loading").style.display = "none";
      document.getElementById("error").textContent = "Failed to load news.";
      document.getElementById("error").style.display = "block";
    });
}

function renderArticles(articles) {
  const container = document.getElementById("news-container");
  articles.forEach(article => {
    const div = document.createElement("div");
    div.className = "news-article";
    div.innerHTML = `
      <div class="article-image" style="background-image: url('${article.image_url || ""}')"></div>
      <div class="article-content">
        <span class="article-category">${article.category || ""}</span>
        <h3 class="article-title">${article.title || "No Title"}</h3>
        <div class="article-meta">
          <span>${article.source || ""}</span>
          <span>${new Date(article.publish_date).toLocaleDateString()}</span>
        </div>
        <p class="article-summary">${article.content || ""}</p>
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

  document.querySelectorAll(".btn-like").forEach(btn => {
    btn.addEventListener("click", () => {
      const articleId = btn.dataset.articleId;
      publishEngagement("like", articleId);
      btn.classList.add("liked");
      showToast("You liked this article!");
    });
  });

  document.querySelectorAll(".btn-share").forEach(btn => {
    btn.addEventListener("click", () => {
      const articleId = btn.dataset.articleId;
      publishEngagement("share", articleId);
      showToast("Link copied to clipboard!");
    });
  });
}

function filterArticles(query) {
  const articles = document.querySelectorAll(".news-article");
  articles.forEach(article => {
    const title = article.querySelector(".article-title").textContent.toLowerCase();
    const summary = article.querySelector(".article-summary").textContent.toLowerCase();
    if (title.includes(query) || summary.includes(query)) {
      article.style.display = "";
    } else {
      article.style.display = "none";
    }
  });
}

function publishEngagement(type, articleId) {
  const payload = {
    user_id: "demo_user_1",
    article_id: articleId,
    event_type: type,
    timestamp: new Date().toISOString(),
    session_id: "session_abc123",
    device_type: "web",
    reading_time_seconds: 0,
    scroll_depth: 0
  };

  fetch(ENGAGEMENT_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  }).then(res => {
    console.log("Event sent:", type);
  }).catch(err => {
    console.error("Error sending engagement event:", err);
  });
}

function showToast(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.add("show");
  setTimeout(() => {
    toast.classList.remove("show");
  }, 3000);
}

function scrollToTop() {
  window.scrollTo({ top: 0, behavior: "smooth" });
}
