let categories = [];
let currentCategory = null;
let loading = false;

async function init() {
  try {
    const res = await fetch("/api/categories");
    categories = await res.json();
    renderTabs();
    if (categories.length > 0) selectCategory(categories[0].id);
  } catch (e) {
    document.getElementById("articles").innerHTML =
      `<div class="state-box"><span class="state-icon">⚠️</span><p class="error-msg">サーバーに接続できません。</p></div>`;
  }
}

function renderTabs() {
  const nav = document.getElementById("tab-nav");
  nav.innerHTML = categories.map(cat => `
    <button class="tab-btn" id="tab-${cssId(cat.id)}" onclick="selectCategory('${esc(cat.id)}')">
      <span class="tab-icon">${cat.icon}</span>
      <span>${cat.id}</span>
    </button>
  `).join("");
}

function selectCategory(id) {
  if (loading && id === currentCategory) return;
  currentCategory = id;

  document.querySelectorAll(".tab-btn").forEach(b => {
    b.classList.remove("active");
    b.style.borderBottomColor = "transparent";
  });
  const tab = document.getElementById(`tab-${cssId(id)}`);
  const cat = categories.find(c => c.id === id);
  if (tab && cat) {
    tab.classList.add("active");
    tab.style.borderBottomColor = cat.color;
  }

  loadArticles(id, false);
}

async function loadArticles(category, refresh) {
  loading = true;
  const container = document.getElementById("articles");
  const refreshBtn = document.getElementById("refresh-btn");
  const refreshIcon = document.getElementById("refresh-icon");
  const countEl = document.getElementById("article-count");

  container.innerHTML = `<div class="state-box"><div class="spinner"></div><p>読み込み中…</p></div>`;
  countEl.textContent = "";
  refreshBtn.disabled = true;
  if (refresh) refreshIcon.classList.add("spinning");

  try {
    const url = `/api/news/${encodeURIComponent(category)}${refresh ? "?refresh=true" : ""}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    const cat = categories.find(c => c.id === category);
    renderArticles(data.articles, cat);

    countEl.textContent = `${data.articles.length} 件`;
    const ft = new Date(data.fetched_at * 1000);
    document.getElementById("cache-info").textContent =
      `最終更新 ${ft.toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit" })}`;
  } catch (e) {
    container.innerHTML = `<div class="state-box"><span class="state-icon">😓</span><p class="error-msg">読み込みに失敗しました。<br><small>${esc(e.message)}</small></p></div>`;
  } finally {
    loading = false;
    refreshBtn.disabled = false;
    refreshIcon.classList.remove("spinning");
  }
}

function renderArticles(articles, cat) {
  const container = document.getElementById("articles");
  if (!articles || articles.length === 0) {
    container.innerHTML = `<div class="state-box"><span class="state-icon">📭</span><p>記事が見つかりませんでした</p></div>`;
    return;
  }

  const catIcon = cat ? cat.icon : "📰";

  const divider = `<hr class="divider" style="background:${esc(cat ? cat.color : "#fff")}">`;

  const cards = articles.map(a => {
    const thumbHtml = a.image
      ? `<img class="card-thumb" src="${esc(a.image)}" alt="" loading="lazy" onerror="this.replaceWith(makePlaceholder('${esc(catIcon)}'))">`
      : `<div class="card-thumb-placeholder">${catIcon}</div>`;

    return `
      <a class="card" href="${esc(a.url)}" target="_blank" rel="noopener noreferrer">
        <div class="card-body">
          <div class="card-title">${esc(a.title)}</div>
          ${a.summary ? `<div class="card-summary">${esc(a.summary)}</div>` : ""}
          <div class="card-date">${formatDate(a.date)}</div>
        </div>
        ${thumbHtml}
      </a>
    `;
  });

  container.innerHTML = cards.join(divider);
}

function makePlaceholder(icon) {
  const d = document.createElement("div");
  d.className = "card-thumb-placeholder";
  d.textContent = icon;
  return d;
}

function refreshCurrent() {
  if (currentCategory && !loading) loadArticles(currentCategory, true);
}

function formatDate(str) {
  if (!str) return "";
  try {
    const d = new Date(str);
    if (isNaN(d)) return str;
    return d.toLocaleDateString("ja-JP", {
      year: "numeric", month: "long", day: "numeric",
      hour: "2-digit", minute: "2-digit"
    });
  } catch { return str; }
}

function esc(s) {
  return String(s || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function cssId(s) {
  return encodeURIComponent(s).replace(/%/g, "_");
}

init();
