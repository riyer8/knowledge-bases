const API = window.location.origin;

const VIEW_META = {
  home: { title: "Overview", subtitle: "Everything in your knowledge base at a glance." },
  library: { title: "Library", subtitle: "Saved pages with notes, summaries, and chat history." },
  graph: { title: "Graph", subtitle: "How your saved pages connect through shared topics." },
  life: { title: "Life", subtitle: "Saved reading, grouped by category." },
  wiki: { title: "Wiki", subtitle: "LLM-compiled articles from your reading." },
  settings: { title: "Settings", subtitle: "Backend status and connected clients." },
};

const state = {
  view: "home",
  pages: [],
  selectedPageId: null,
  bucketLeaves: [],
  bucketTree: {},
  lifeCategory: "all",
  lifeEvents: [],
  lifeSummary: [],
  wikiPane: "index",
  wikiArticles: [],
  wikiRaw: [],
  wikiSelectedKey: null,
};

const $ = (id) => document.getElementById(id);

function formatShortDate(raw) {
  if (!raw) return "";
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function toast(msg) {
  const el = $("toast");
  el.textContent = msg;
  el.hidden = false;
  setTimeout(() => { el.hidden = true; }, 3200);
}

async function apiDelete(path) {
  const res = await fetch(`${API}${path}`, { method: "DELETE" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

async function apiGet(path) {
  const res = await fetch(`${API}${path}`);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

async function apiPost(path, body = {}) {
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

function setConn(ok, label) {
  $("conn-dot").className = `conn-dot ${ok ? "ok" : "err"}`;
  $("conn-label").textContent = label;
}

function switchView(view) {
  // Life and Wiki are archived from the nav; keep their views in the DOM for a later revival.
  if (view === "life" || view === "wiki") view = "home";
  state.view = view;
  document.querySelectorAll(".side-link").forEach((el) => {
    el.classList.toggle("active", el.dataset.view === view);
  });
  document.querySelectorAll(".view").forEach((el) => {
    el.classList.toggle("active", el.id === `view-${view}`);
  });
  const meta = VIEW_META[view] || VIEW_META.home;
  $("view-title").textContent = meta.title;
  $("view-subtitle").textContent = meta.subtitle;
  if (view === "library") loadLibrary();
  if (view === "graph") renderGraph();
  if (view === "life") loadLife();
  if (view === "wiki") loadWiki();
  if (view === "settings") loadSettings();
  if (view === "home") loadHome();
}

// --- Overview ---

async function loadHome() {
  try {
    const [health, pages] = await Promise.all([
      apiGet("/health"),
      apiGet("/library/pages?limit=20"),
    ]);

    const pageList = pages.pages || [];

    $("home-stats").innerHTML = `
      <div class="stat-card"><strong>${pageList.length}</strong><span>Saved pages</span></div>
      <div class="stat-card"><strong>${health.llm_provider || "—"}</strong><span>LLM provider</span></div>
    `;

    const recent = $("home-recent-pages");
    recent.innerHTML = "";
    if (!pageList.length) {
      recent.innerHTML = "<li class='muted'>No saved pages yet — use the Chrome extension.</li>";
    } else {
      for (const page of pageList.slice(0, 5)) {
        const li = document.createElement("li");
        const btn = document.createElement("button");
        btn.textContent = page.title || "Untitled";
        btn.addEventListener("click", () => {
          switchView("library");
          openPage(page.id);
        });
        li.appendChild(btn);
        recent.appendChild(li);
      }
    }

    setConn(true, health.llm_provider ? `Ready · ${health.llm_provider}` : "Connected");
  } catch (err) {
    setConn(false, "Backend offline");
    $("home-stats").innerHTML = `<p class="empty-state">Start the backend with <code>python3 main.py</code></p>`;
  }
}

// --- Library ---

async function loadLibrary() {
  const list = $("library-list");
  list.innerHTML = "<p class='empty muted'>Loading…</p>";
  try {
    const data = await apiGet("/library/pages?limit=100");
    state.pages = data.pages || [];
    list.innerHTML = "";
    if (!state.pages.length) {
      list.innerHTML = "<p class='empty-state'>No saved pages yet.<br>Save from the Chrome extension while browsing.</p>";
      return;
    }
    for (const page of state.pages) {
      const card = document.createElement("div");
      card.className = `lib-card${page.id === state.selectedPageId ? " active" : ""}`;
      card.dataset.pageId = page.id;
      const summaryPreview = (page.summary || "").replace(/\s+/g, " ").trim();
      const quoteCount = Number(page.quote_count || 0);
      const savedWhen = formatShortDate(page.saved_at);
      card.innerHTML = `
        <h4>${escapeHtml(page.title || "Untitled")}</h4>
        <div class="lib-card-meta">
          <span>${escapeHtml(page.site || "")}</span>
          ${quoteCount ? `<span class="lib-pill">${quoteCount} quote${quoteCount === 1 ? "" : "s"}</span>` : ""}
          ${savedWhen ? `<span class="lib-pill">${escapeHtml(savedWhen)}</span>` : ""}
        </div>
        ${summaryPreview ? `<p class="lib-card-summary">${escapeHtml(summaryPreview.slice(0, 100))}${summaryPreview.length > 100 ? "…" : ""}</p>` : ""}
      `;
      card.addEventListener("click", () => openPage(page.id));
      list.appendChild(card);
    }
    if (state.selectedPageId) openPage(state.selectedPageId);
  } catch (err) {
    list.innerHTML = `<p class='empty error'>${escapeHtml(err.message)}</p>`;
  }
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    document.body.appendChild(textarea);
    textarea.select();
    try {
      return document.execCommand("copy");
    } catch {
      return false;
    } finally {
      textarea.remove();
    }
  }
}

async function openPage(pageId) {
  state.selectedPageId = pageId;
  document.querySelectorAll(".lib-card").forEach((el) => {
    el.classList.toggle("active", el.dataset.pageId === pageId);
  });
  const detail = $("library-detail");
  detail.innerHTML = "<p class='muted'>Loading…</p>";
  try {
    const data = await apiGet(`/library/pages/${encodeURIComponent(pageId)}`);
    const page = data.page;
    const meta = page.metadata || {};
    const notes = String(meta.notes || "").trim();
    const chat = page.chat_history || [];
    const tags = Array.isArray(meta.tags) ? meta.tags.filter(Boolean) : [];
    const entry = ContextBookshelf.buildEntry({
      title: page.title,
      url: page.url,
      ...meta,
    });

    detail.innerHTML = `
      <div class="detail-head">
        <div>
          <h3>${escapeHtml(page.title || "Untitled")}</h3>
          <p class="muted"><a href="${escapeHtml(page.url)}" target="_blank" rel="noopener">${escapeHtml(page.url || "")}</a></p>
        </div>
        <div class="detail-actions">
          <button type="button" class="btn ghost" id="library-copy-json">Copy JSON</button>
          <button type="button" class="btn ghost danger-outline" id="library-delete-btn">Delete page</button>
        </div>
      </div>
      ${meta.tldr ? `<p class="lib-tldr">${escapeHtml(meta.tldr)}</p>` : ""}
      ${tags.length ? `<p class="lib-tags">${tags.map((tag) => `<span class="lib-pill">${escapeHtml(tag)}</span>`).join("")}</p>` : ""}
      <div class="detail-block">
        <h4>Notes</h4>
        <div class="notes-document markdown-body">${notes ? ContextNotes.markdownToHtml(notes) : "<p class='muted'>No notes saved for this page.</p>"}</div>
      </div>
      <div class="detail-block">
        <h4>Summary</h4>
        <div class="markdown-body">${renderMarkdown(page.summary || "_No summary._")}</div>
      </div>
      <div class="detail-block">
        <h4>Chat (${chat.length} messages)</h4>
        <div id="detail-chat"></div>
      </div>
    `;

    $("library-delete-btn")?.addEventListener("click", () => deleteLibraryPage(pageId));
    $("library-copy-json")?.addEventListener("click", async () => {
      const copied = await copyText(ContextBookshelf.format(entry));
      toast(copied ? "JSON copied" : "Could not copy JSON");
    });

    const chatEl = $("detail-chat");
    if (!chat.length) {
      chatEl.innerHTML = "<p class='muted'>No chat history.</p>";
    } else {
      for (const turn of chat) {
        const node = document.createElement("div");
        node.className = `chat-turn ${turn.role}`;
        if (turn.role === "assistant") {
          node.classList.add("markdown-body");
          node.innerHTML = renderMarkdown(turn.content);
        } else {
          node.textContent = turn.content;
        }
        chatEl.appendChild(node);
      }
    }
  } catch (err) {
    detail.innerHTML = `<p class='error'>${escapeHtml(err.message)}</p>`;
  }
}

async function deleteLibraryPage(pageId) {
  if (!pageId) return;
  const page = state.pages.find((p) => p.id === pageId);
  const title = page?.title || "this page";
  if (!window.confirm(`Delete "${title}"?\n\nThis removes the saved page, quotes, and chat history.`)) {
    return;
  }
  try {
    await apiDelete(`/library/pages/${encodeURIComponent(pageId)}`);
    if (state.selectedPageId === pageId) {
      state.selectedPageId = null;
      $("library-detail").innerHTML =
        '<p class="empty-state">Select a saved page to read its notes, summary, and chat history.</p>';
    }
    toast("Page deleted");
    await loadLibrary();
    if (state.view === "graph") renderGraph();
    if (state.view === "home") loadHome();
  } catch (err) {
    toast(err.message);
  }
}

// --- Graph ---

function layoutNodes(nodes, width, height) {
  const positions = {};
  const cx = width / 2;
  const cy = height / 2;
  const radius = Math.min(width, height) * 0.34;
  nodes.forEach((node, index) => {
    const angle = (index / nodes.length) * Math.PI * 2 - Math.PI / 2;
    positions[node.id] = {
      x: cx + Math.cos(angle) * radius,
      y: cy + Math.sin(angle) * radius,
    };
  });
  return positions;
}

async function renderGraph() {
  const svg = $("graph-svg");
  const empty = $("graph-empty");
  svg.innerHTML = "";
  try {
    const data = await apiGet("/library/graph");
    const nodes = (data.nodes || []).filter((n) => n.type === "page");
    const edges = data.edges || [];
    if (!nodes.length) {
      empty.hidden = false;
      return;
    }
    empty.hidden = true;
    const width = 800;
    const height = Math.max(500, nodes.length * 80);
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    const positions = layoutNodes(nodes, width, height);
    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");

    for (const edge of edges) {
      const from = positions[edge.source];
      const to = positions[edge.target];
      if (!from || !to) continue;
      const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.setAttribute("x1", from.x);
      line.setAttribute("y1", from.y);
      line.setAttribute("x2", to.x);
      line.setAttribute("y2", to.y);
      line.setAttribute("class", "graph-edge");
      g.appendChild(line);
    }

    for (const node of nodes) {
      const pos = positions[node.id];
      if (!pos) continue;
      const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
      group.style.cursor = "pointer";
      group.addEventListener("click", () => {
        const id = node.id.replace(/^page:/, "");
        switchView("library");
        openPage(id);
      });
      const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      circle.setAttribute("r", "14");
      circle.setAttribute("cx", pos.x);
      circle.setAttribute("cy", pos.y);
      circle.setAttribute("class", "graph-node");
      group.appendChild(circle);
      const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
      text.setAttribute("x", pos.x);
      text.setAttribute("y", pos.y + 28);
      text.setAttribute("text-anchor", "middle");
      text.setAttribute("class", "graph-node-label");
      text.textContent = (node.label || "Page").slice(0, 24);
      group.appendChild(text);
      g.appendChild(group);
    }
    svg.appendChild(g);
  } catch (err) {
    empty.hidden = false;
    empty.textContent = err.message;
  }
}

// --- Life ---

function parentBucket(bucket) {
  return String(bucket || "Other").split("/")[0];
}

function lifeSourceLabel(source) {
  const labels = {
    saved_page: "Saved page",
    saved_quote: "Quote",
    browser_remember: "Quote",
    gcal: "Calendar",
    gmail: "Email",
    imessage: "Messages",
    screen_capture: "Capture",
    manual_text: "Note",
  };
  return labels[source] || source || "unknown";
}

function fillBucketSelect(select, selected) {
  const tree = state.bucketTree || {};
  select.innerHTML = "";
  const parents = Object.keys(tree);
  const leaves = state.bucketLeaves || [];
  if (!parents.length) {
    for (const leaf of leaves) {
      const opt = document.createElement("option");
      opt.value = leaf;
      opt.textContent = leaf;
      opt.selected = leaf === selected;
      select.appendChild(opt);
    }
    return;
  }
  for (const parent of parents) {
    const children = tree[parent] || [];
    if (!children.length) {
      const opt = document.createElement("option");
      opt.value = parent;
      opt.textContent = parent;
      opt.selected = parent === selected;
      select.appendChild(opt);
      continue;
    }
    const group = document.createElement("optgroup");
    group.label = parent;
    for (const child of children) {
      const opt = document.createElement("option");
      opt.value = `${parent}/${child}`;
      opt.textContent = child;
      opt.selected = `${parent}/${child}` === selected;
      group.appendChild(opt);
    }
    select.appendChild(group);
  }
}

function renderLifeChips() {
  const chips = $("life-chips");
  chips.innerHTML = "";
  const topLevel = state.lifeSummary || [];
  const allBtn = document.createElement("button");
  allBtn.type = "button";
  allBtn.className = `chip${state.lifeCategory === "all" ? " active" : ""}`;
  allBtn.textContent = "All";
  allBtn.addEventListener("click", () => {
    state.lifeCategory = "all";
    renderLifeChips();
    renderLifeEvents();
  });
  chips.appendChild(allBtn);
  for (const item of topLevel) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = `chip${state.lifeCategory === item.category ? " active" : ""}`;
    chip.innerHTML = `<strong>${escapeHtml(item.category)}</strong> ${escapeHtml(String(item.percent))}%`;
    chip.addEventListener("click", () => {
      state.lifeCategory = item.category;
      renderLifeChips();
      renderLifeEvents();
    });
    chips.appendChild(chip);
  }
}

async function loadLife() {
  $("life-chips").innerHTML = "<span class='muted'>Loading…</span>";
  $("life-events").innerHTML = "";
  try {
    const [summary, events, taxonomy] = await Promise.all([
      apiGet("/dashboard/time?days=7"),
      apiGet("/buckets/recent?days=7&limit=30"),
      apiGet("/buckets/taxonomy"),
    ]);
    state.bucketLeaves = taxonomy.leaves || [];
    state.bucketTree = taxonomy.tree || {};
    state.lifeEvents = events.events || [];
    state.lifeSummary = summary.by_top_level || [];
    if (state.lifeCategory !== "all" && !state.lifeSummary.some((item) => item.category === state.lifeCategory)) {
      state.lifeCategory = "all";
    }
    renderLifeChips();
    renderLifeEvents();
  } catch (err) {
    $("life-events").innerHTML = `<p class='empty-state'>${escapeHtml(err.message)}</p>`;
  }
}

function renderLifeEvents() {
  const container = $("life-events");
  container.innerHTML = "";
  const filter = state.lifeCategory || "all";
  const events = (state.lifeEvents || []).filter(
    (event) => filter === "all" || parentBucket(event.bucket) === filter
  );
  if (!events.length) {
    container.innerHTML = "<p class='empty-state'>Save a page to see it categorized here.</p>";
    return;
  }
  const groups = [];
  const byParent = {};
  for (const event of events) {
    const parent = parentBucket(event.bucket);
    if (!byParent[parent]) {
      byParent[parent] = [];
      groups.push(parent);
    }
    byParent[parent].push(event);
  }
  for (const parent of groups) {
    const heading = document.createElement("h3");
    heading.className = "life-group-title";
    heading.textContent = parent;
    container.appendChild(heading);
    for (const event of byParent[parent]) {
      const card = document.createElement("article");
      card.className = "event-card";
      const title = event.title ? `<h4 class="event-title">${escapeHtml(event.title)}</h4>` : "";
      card.innerHTML = `
        <div class="event-meta">
          <span>${escapeHtml(lifeSourceLabel(event.source))}</span>
          <span>${escapeHtml(formatShortDate(event.timestamp) || event.timestamp || "")}</span>
        </div>
        ${title}
        <p class="event-preview">${escapeHtml(event.text_preview || "(no preview)")}</p>
        <div class="event-actions">
          <select data-event-id="${escapeHtml(event.event_id)}"></select>
          <button type="button" class="btn ghost save-bucket">Save</button>
        </div>
      `;
      const select = card.querySelector("select");
      fillBucketSelect(select, event.bucket);
      const saveBtn = card.querySelector(".save-bucket");
      saveBtn.disabled = true;
      select.addEventListener("change", () => {
        saveBtn.disabled = select.value === event.bucket;
      });
      saveBtn.addEventListener("click", async () => {
        saveBtn.disabled = true;
        try {
          await apiPost("/buckets/override", { event_id: event.event_id, bucket: select.value });
          toast(`Moved to ${select.value}`);
          loadLife();
        } catch (err) {
          toast(err.message);
          saveBtn.disabled = false;
        }
      });
      container.appendChild(card);
    }
  }
}

// --- Wiki ---

async function loadWikiStatus() {
  const data = await apiGet("/wiki/status");
  const pending = Number(data.uncompiled_count || 0);
  $("wiki-stats").innerHTML = `
    <div class="wiki-stat"><strong>${data.raw_count}</strong><span>Raw</span></div>
    <div class="wiki-stat"><strong>${data.article_count}</strong><span>Articles</span></div>
    <div class="wiki-stat${pending > 0 ? " wiki-stat-warn" : ""}"><strong>${pending}</strong><span>Pending</span></div>
  `;
}

async function loadWikiIndex() {
  state.wikiPane = "index";
  state.wikiSelectedKey = null;
  document.querySelectorAll(".wiki-tab").forEach((el) => {
    el.classList.toggle("active", el.dataset.wikiPane === "index");
  });
  const data = await apiGet("/wiki/index");
  $("wiki-title").textContent = "Index";
  $("wiki-meta").textContent = "Auto-maintained table of contents";
  $("wiki-body").innerHTML = renderMarkdown(data.index);
  $("wiki-items").innerHTML = "";
  $("wiki-health-panel").hidden = true;
}

async function loadWikiArticles() {
  state.wikiPane = "articles";
  document.querySelectorAll(".wiki-tab").forEach((el) => {
    el.classList.toggle("active", el.dataset.wikiPane === "articles");
  });
  const data = await apiGet("/wiki/articles");
  state.wikiArticles = data.articles || [];
  renderWikiItems();
  if (state.wikiArticles[0]) loadWikiArticle(state.wikiArticles[0].slug);
}

async function loadWikiRawList() {
  state.wikiPane = "raw";
  document.querySelectorAll(".wiki-tab").forEach((el) => {
    el.classList.toggle("active", el.dataset.wikiPane === "raw");
  });
  const data = await apiGet("/wiki/raw");
  state.wikiRaw = data.raw || [];
  renderWikiItems();
  if (state.wikiRaw[0]) loadWikiRawItem(state.wikiRaw[0].id);
}

function renderWikiItems() {
  const list = $("wiki-items");
  list.innerHTML = "";
  const items = state.wikiPane === "raw" ? state.wikiRaw : state.wikiArticles;
  if (!items.length) {
    const empty = document.createElement("li");
    empty.className = "wiki-items-empty muted";
    empty.textContent = state.wikiPane === "raw"
      ? "No raw sources yet."
      : "No articles yet — compile your wiki.";
    list.appendChild(empty);
    return;
  }
  for (const item of items) {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    const key = state.wikiPane === "raw" ? item.id : item.slug;
    btn.textContent = item.title || item.slug || item.id;
    btn.classList.toggle("selected", key === state.wikiSelectedKey);
    btn.addEventListener("click", () => {
      if (state.wikiPane === "raw") loadWikiRawItem(item.id);
      else loadWikiArticle(item.slug);
    });
    li.appendChild(btn);
    list.appendChild(li);
  }
}

async function loadWikiArticle(slug) {
  state.wikiSelectedKey = slug;
  renderWikiItems();
  const data = await apiGet(`/wiki/articles/${encodeURIComponent(slug)}`);
  const article = data.article;
  $("wiki-title").textContent = article.title;
  $("wiki-meta").textContent = article.backlinks?.length
    ? `Links: ${article.backlinks.join(", ")}`
    : "";
  $("wiki-body").innerHTML = renderMarkdown(article.content);
  $("wiki-health-panel").hidden = true;
}

async function loadWikiRawItem(rawId) {
  state.wikiSelectedKey = rawId;
  renderWikiItems();
  const data = await apiGet(`/wiki/raw/${encodeURIComponent(rawId)}`);
  const raw = data.raw;
  $("wiki-title").textContent = raw.title;
  $("wiki-meta").textContent = raw.url || "";
  $("wiki-body").innerHTML = renderMarkdown(raw.content);
  $("wiki-health-panel").hidden = true;
}

async function loadWiki() {
  try {
    await loadWikiStatus();
    if (state.wikiPane === "articles") await loadWikiArticles();
    else if (state.wikiPane === "raw") await loadWikiRawList();
    else await loadWikiIndex();
  } catch (err) {
    $("wiki-body").innerHTML = `<p class='empty-state'>${escapeHtml(err.message)}</p>`;
  }
}

// --- Settings ---

async function loadSettings() {
  ContextTheme.syncThemeSelect($("settings-theme"));
  try {
    const [health, settings] = await Promise.all([
      apiGet("/health"),
      apiGet("/settings"),
    ]);
    $("settings-backend").textContent = `Connected · API v${health.api_version}`;
    $("settings-storage").textContent = `Storage: ${health.kb_root}`;
    $("settings-provider").textContent =
      `Provider: ${settings.llm_provider_setting || "auto"} · Active: ${health.llm_provider || "—"}`;
    setConn(true, "Connected");
  } catch (err) {
    $("settings-backend").textContent = "Backend offline — run python3 main.py";
    setConn(false, "Offline");
  }
}

// --- Init ---

document.querySelectorAll(".side-link").forEach((link) => {
  link.addEventListener("click", (e) => {
    e.preventDefault();
    switchView(link.dataset.view);
    history.replaceState(null, "", `#${link.dataset.view}`);
  });
});

document.querySelectorAll("[data-goto]").forEach((btn) => {
  btn.addEventListener("click", () => {
    switchView(btn.dataset.goto);
    history.replaceState(null, "", `#${btn.dataset.goto}`);
  });
});

$("graph-refresh")?.addEventListener("click", renderGraph);
$("life-refresh")?.addEventListener("click", loadLife);

document.querySelectorAll(".wiki-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    const pane = tab.dataset.wikiPane;
    if (pane === "index") loadWikiIndex();
    else if (pane === "raw") loadWikiRawList();
    else loadWikiArticles();
  });
});

$("wiki-compile")?.addEventListener("click", async () => {
  const btn = $("wiki-compile");
  btn.disabled = true;
  btn.textContent = "Compiling…";
  try {
    const result = await apiPost("/wiki/compile", { max_sources: 3 });
    toast(result.message || "Compiled");
    await loadWiki();
  } catch (err) {
    toast(err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Compile";
  }
});

$("wiki-health")?.addEventListener("click", async () => {
  try {
    const result = await apiPost("/wiki/health-check");
    const panel = $("wiki-health-panel");
    panel.hidden = false;
    panel.innerHTML = `
      <strong>Health check</strong>
      <ul>${(result.issues || []).map((i) => `<li>${escapeHtml(i.severity)}: ${escapeHtml(i.message)}</li>`).join("") || "<li>No issues</li>"}</ul>
    `;
    toast("Health check complete");
  } catch (err) {
    toast(err.message);
  }
});

$("wiki-ask-btn")?.addEventListener("click", async () => {
  const question = $("wiki-ask-input")?.value.trim();
  if (!question) return;
  const btn = $("wiki-ask-btn");
  const reply = $("wiki-ask-reply");
  btn.disabled = true;
  reply.hidden = false;
  reply.innerHTML = "<p class='muted'>Thinking…</p>";
  try {
    const result = await apiPost("/wiki/ask", { question });
    reply.innerHTML = renderMarkdown(result.reply || "");
    $("wiki-ask-sources").textContent = (result.sources || []).length
      ? `Sources: ${result.sources.join(" · ")}`
      : "";
  } catch (err) {
    reply.textContent = err.message;
  } finally {
    btn.disabled = false;
  }
});

$("wiki-search")?.addEventListener("keydown", async (e) => {
  if (e.key !== "Enter") return;
  const q = e.target.value.trim();
  if (!q) return;
  try {
    const data = await apiGet(`/wiki/search?q=${encodeURIComponent(q)}`);
    state.wikiPane = "articles";
    state.wikiArticles = (data.results || []).map((r) => ({
      slug: r.slug,
      title: r.title,
    }));
    document.querySelectorAll(".wiki-tab").forEach((el) => {
      el.classList.toggle("active", el.dataset.wikiPane === "articles");
    });
    renderWikiItems();
    if (state.wikiArticles[0]) loadWikiArticle(state.wikiArticles[0].slug);
  } catch (err) {
    toast(err.message);
  }
});

$("wiki-body")?.addEventListener("click", (e) => {
  const link = e.target.closest("[data-wikilink]");
  if (!link) return;
  e.preventDefault();
  const slug = link.dataset.wikilink.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  loadWikiArticle(slug);
});

const initialView = (location.hash || "#home").slice(1) || "home";
switchView(VIEW_META[initialView] ? initialView : "home");
loadHome();

$("settings-theme")?.addEventListener("change", (event) => {
  ContextTheme.setTheme(event.target.value);
});

window.addEventListener("hashchange", () => {
  const view = (location.hash || "#home").slice(1);
  if (VIEW_META[view]) switchView(view);
});
