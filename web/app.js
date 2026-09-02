const API = `${window.location.origin}`;

const els = {
  rawCount: document.getElementById("raw-count"),
  articleCount: document.getElementById("article-count"),
  pendingCount: document.getElementById("pending-count"),
  compileBtn: document.getElementById("compile-btn"),
  healthBtn: document.getElementById("health-btn"),
  searchInput: document.getElementById("search-input"),
  itemList: document.getElementById("item-list"),
  contentTitle: document.getElementById("content-title"),
  contentMeta: document.getElementById("content-meta"),
  contentBody: document.getElementById("content-body"),
  healthPanel: document.getElementById("health-panel"),
  healthIssues: document.getElementById("health-issues"),
  healthSuggestions: document.getElementById("health-suggestions"),
  askInput: document.getElementById("ask-input"),
  askBtn: document.getElementById("ask-btn"),
  askReply: document.getElementById("ask-reply"),
  askSources: document.getElementById("ask-sources"),
  toast: document.getElementById("toast"),
};

let state = {
  pane: "index",
  articles: [],
  raw: [],
};

function showToast(message) {
  els.toast.textContent = message;
  els.toast.hidden = false;
  setTimeout(() => { els.toast.hidden = true; }, 3200);
}

async function apiGet(path) {
  const res = await fetch(`${API}${path}`);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Request failed");
  return data;
}

async function apiPost(path, body = {}) {
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Request failed");
  return data;
}

function escapeHtml(text) {
  return String(text || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function renderMarkdown(text) {
  let html = escapeHtml(text || "");
  html = html.replace(/^### (.+)$/gm, "<h3>$1</h3>");
  html = html.replace(/^## (.+)$/gm, "<h2>$1</h2>");
  html = html.replace(/^# (.+)$/gm, "<h1>$1</h1>");
  html = html.replace(/\[\[([^\]]+)\]\]/g, '<a href="#" data-wikilink="$1">$1</a>');
  html = html.replace(/^- (.+)$/gm, "<li>$1</li>");
  html = html.replace(/(<li>.*<\/li>\n?)+/g, (m) => `<ul>${m}</ul>`);
  html = html.replace(/\n\n/g, "</p><p>");
  html = `<p>${html}</p>`;
  html = html.replace(/<p><\/p>/g, "");
  return html;
}

function renderItemList() {
  els.itemList.innerHTML = "";
  const items = state.pane === "raw" ? state.raw : state.articles;
  for (const item of items) {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    const title = item.title || item.slug;
    btn.innerHTML = `${escapeHtml(title)}<span class="item-meta">${state.pane === "raw" ? (item.compiled ? "compiled" : "pending") : item.excerpt || ""}</span>`;
    btn.addEventListener("click", () => {
      if (state.pane === "raw") loadRaw(item.id);
      else loadArticle(item.slug);
    });
    li.appendChild(btn);
    els.itemList.appendChild(li);
  }
}

async function loadStatus() {
  const data = await apiGet("/wiki/status");
  els.rawCount.textContent = data.raw_count;
  els.articleCount.textContent = data.article_count;
  els.pendingCount.textContent = data.uncompiled_count;
}

async function loadIndex() {
  state.pane = "index";
  document.querySelectorAll(".nav-item").forEach((el) => {
    el.classList.toggle("active", el.dataset.pane === "index");
  });
  const data = await apiGet("/wiki/index");
  els.contentTitle.textContent = "Index";
  els.contentMeta.textContent = "Auto-maintained table of contents";
  els.contentBody.innerHTML = renderMarkdown(data.index);
  els.healthPanel.hidden = true;
  els.itemList.innerHTML = "";
}

async function loadArticles() {
  state.pane = "articles";
  document.querySelectorAll(".nav-item").forEach((el) => {
    el.classList.toggle("active", el.dataset.pane === "articles");
  });
  const data = await apiGet("/wiki/articles");
  state.articles = data.articles || [];
  renderItemList();
  if (state.articles[0]) loadArticle(state.articles[0].slug);
}

async function loadRawList() {
  state.pane = "raw";
  document.querySelectorAll(".nav-item").forEach((el) => {
    el.classList.toggle("active", el.dataset.pane === "raw");
  });
  const data = await apiGet("/wiki/raw");
  state.raw = data.raw || [];
  renderItemList();
  if (state.raw[0]) loadRaw(state.raw[0].id);
}

async function loadArticle(slug) {
  const data = await apiGet(`/wiki/articles/${encodeURIComponent(slug)}`);
  const article = data.article;
  els.contentTitle.textContent = article.title;
  els.contentMeta.textContent = article.backlinks?.length
    ? `Links: ${article.backlinks.join(", ")}`
    : "";
  els.contentBody.innerHTML = renderMarkdown(article.content);
  els.healthPanel.hidden = true;
}

async function loadRaw(rawId) {
  const data = await apiGet(`/wiki/raw/${encodeURIComponent(rawId)}`);
  const raw = data.raw;
  els.contentTitle.textContent = raw.title;
  els.contentMeta.textContent = raw.url || raw.metadata?.source_type || "";
  els.contentBody.innerHTML = renderMarkdown(raw.content);
  els.healthPanel.hidden = true;
}

async function runCompile() {
  els.compileBtn.disabled = true;
  els.compileBtn.textContent = "Compiling…";
  try {
    const result = await apiPost("/wiki/compile", { max_sources: 3 });
    showToast(result.message || "Wiki compiled");
    await refresh();
  } catch (err) {
    showToast(err.message);
  } finally {
    els.compileBtn.disabled = false;
    els.compileBtn.textContent = "Compile wiki";
  }
}

async function runAsk() {
  const question = els.askInput?.value.trim();
  if (!question || !els.askBtn) return;
  els.askBtn.disabled = true;
  els.askBtn.textContent = "…";
  if (els.askReply) {
    els.askReply.hidden = false;
    els.askReply.innerHTML = "<p class='muted'>Loading…</p>";
  }
  try {
    const result = await apiPost("/wiki/ask", { question });
    if (els.askReply) {
      els.askReply.innerHTML = renderMarkdown(result.reply || "");
    }
    if (els.askSources) {
      const sources = result.sources || [];
      els.askSources.textContent = sources.length
        ? `Sources: ${sources.join(" · ")}`
        : "";
    }
  } catch (err) {
    if (els.askReply) els.askReply.textContent = err.message;
  } finally {
    els.askBtn.disabled = false;
    els.askBtn.textContent = "Ask";
  }
}

async function runHealthCheck() {
  els.healthBtn.disabled = true;
  try {
    const result = await apiPost("/wiki/health-check");
    els.healthPanel.hidden = false;
    els.healthIssues.innerHTML = (result.issues || [])
      .map((item) => `<div class="health-item"><strong>${escapeHtml(item.severity)}</strong>: ${escapeHtml(item.message)}</div>`)
      .join("") || "<p class='muted'>No issues found.</p>";
    const suggestions = [
      ...(result.suggestions || []).map((s) => `Explore: ${s}`),
      ...(result.new_article_ideas || []).map((s) => `New article idea: ${s}`),
    ];
    els.healthSuggestions.innerHTML = suggestions.length
      ? `<ul>${suggestions.map((s) => `<li>${escapeHtml(s)}</li>`).join("")}</ul>`
      : "";
    showToast("Health check complete");
  } catch (err) {
    showToast(err.message);
  } finally {
    els.healthBtn.disabled = false;
  }
}

async function runSearch() {
  const q = els.searchInput.value.trim();
  if (!q) return;
  const data = await apiGet(`/wiki/search?q=${encodeURIComponent(q)}`);
  state.pane = "articles";
  state.articles = (data.results || []).map((r) => ({
    slug: r.slug,
    title: r.title,
    excerpt: r.excerpt,
  }));
  renderItemList();
  if (state.articles[0]) loadArticle(state.articles[0].slug);
}

async function refresh() {
  await loadStatus();
  if (state.pane === "index") await loadIndex();
  else if (state.pane === "raw") await loadRawList();
  else await loadArticles();
}

document.querySelectorAll(".nav-item").forEach((btn) => {
  btn.addEventListener("click", () => {
    const pane = btn.dataset.pane;
    if (pane === "index") loadIndex();
    else if (pane === "raw") loadRawList();
    else loadArticles();
  });
});

els.compileBtn.addEventListener("click", runCompile);
els.healthBtn.addEventListener("click", runHealthCheck);
els.askBtn?.addEventListener("click", runAsk);
els.askInput?.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    runAsk();
  }
});
els.searchInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") runSearch();
});

els.contentBody.addEventListener("click", (e) => {
  const link = e.target.closest("[data-wikilink]");
  if (!link) return;
  e.preventDefault();
  const slug = link.dataset.wikilink.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  loadArticle(slug);
});

refresh().catch((err) => {
  els.contentBody.innerHTML = `<p class="muted">Could not connect to backend. Start it with <code>python3 main.py</code> then open <code>http://127.0.0.1:8765/app/</code></p><p>${escapeHtml(err.message)}</p>`;
});
