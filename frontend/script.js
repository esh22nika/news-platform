// CONFIG - put your real URLs here
const NEWS_API_URL = "https://news-service-625238064074.asia-south1.run.app/news";
const USER_SERVICE_URL = "https://user-service-625238064074.asia-south1.run.app/users";
const ENGAGEMENT_URL = "https://user-service-625238064074.asia-south1.run.app/engagement";

let currentUserId = null;

// ---- SIGNUP LOGIC ----

document.addEventListener("DOMContentLoaded", () => {
  // Attach signup handler
  const signupForm = document.getElementById("signup-form");
  if (signupForm) {
    signupForm.addEventListener("submit", (e) => {
      e.preventDefault();

      const username = document.getElementById("username").value.trim();
      const email = document.getElementById("email").value.trim();
      const interests = document
        .getElementById("interests")
        .value.split(",")
        .map((i) => i.trim())
        .filter((i) => i.length > 0);

      if (!username || !email || interests.length === 0) {
        alert("Please fill all fields correctly.");
        return;
      }

      const payload = {
        username,
        email,
        interests,
      };

      fetch(USER_SERVICE_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      })
        .then((res) => {
          if (!res.ok) throw new Error("Signup failed");
          return res.json();
        })
        .then((data) => {
          console.log("User created:", data);

          // Save user_id for engagement events
          currentUserId = data.user_id;

          document.getElementById("signup-success").style.display = "block";
          document.getElementById("signup-form").reset();

          // Show news UI, hide signup UI
          document.getElementById("signup-section").style.display = "none";
          document.getElementById("news-header").style.display = "";
          document.getElementById("news-container").style.display = "";
          document.getElementById("backToTopBtn").style.display = "";

          loadArticles("all");
        })
        .catch((err) => {
          console.error(err);
          alert("Error during signup.");
        });
    });
  }

  // Wire up filters, search etc. initially hidden
  document.querySelectorAll(".filter-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document
        .querySelectorAll(".filter-btn")
        .forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const category = btn.dataset.category;
      loadArticles(category === "all" ? null : category);
    });
  });

  const searchInput = document.getElementById("searchInput");
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      const query = e.target.value.toLowerCase();
      filterArticles(query);
    });
  }
});

function loadArticles(category) {
  document.getElementById("loading").style.display = "block";
  document.getElementById("news-container").innerHTML = "";

  let url = NEWS_API_URL;
  if (category) {
    url += `?category=${category}`;
  }

  fetch(url)
    .then((res) => res.json())
    .then((data) => {
      renderArticles(data.articles);
      document.getElementById("loading").style.display = "none";
    })
    .catch((err) => {
      console.error(err);
      document.getElementById("loading").style.display = "none";
      document.getElementById("error").textContent = "Failed to load news.";
      document.getElementById("error").style.display = "block";
    });
}

function renderArticles(articles) {
  const container = document.getElementById("news-container");
  articles.forEach((article) => {
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

  document.querySelectorAll(".btn-like").forEach((btn) => {
    btn.addEventListener("click", () => {
      const articleId = btn.dataset.articleId;
      publishEngagement("like", articleId);
      btn.classList.add("liked");
      showToast("You liked this article!");
    });
  });

  document.querySelectorAll(".btn-share").forEach((btn) => {
    btn.addEventListener("click", () => {
      const articleId = btn.dataset.articleId;
      publishEngagement("share", articleId);
      showToast("Link copied to clipboard!");
    });
  });
}

function filterArticles(query) {
  const articles = document.querySelectorAll(".news-article");
  articles.forEach((article) => {
    const title = article
      .querySelector(".article-title")
      .textContent.toLowerCase();
    const summary = article
      .querySelector(".article-summary")
      .textContent.toLowerCase();
    if (title.includes(query) || summary.includes(query)) {
      article.style.display = "";
    } else {
      article.style.display = "none";
    }
  });
}

function publishEngagement(type, articleId) {
  if (!currentUserId) {
    alert("Please sign up first!");
    return;
  }

  const payload = {
    user_id: currentUserId,
    article_id: articleId,
    event_type: type,
    timestamp: new Date().toISOString(),
    session_id: "session_abc123",
    device_type: "web",
    reading_time_seconds: 0,
    scroll_depth: 0,
  };

  fetch(ENGAGEMENT_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  })
    .then((res) => {
      console.log("Event sent:", type);
    })
    .catch((err) => {
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
