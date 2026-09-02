const BACKEND = "http://127.0.0.1:8765";

const state = {
  page: null,
  savedPageId: null,
  selection: "",
  lastSavedSelection: "",
  history: [],
  quotes: [],
  busy: false,
  view: "chat",
  pageTab: "quotes",
  savedPages: [],
  selectedSavedId: null,
  pendingQuoteText: "",
  bucketLeaves: [],
  lifeEvents: [],
};

const els = {
  title: document.getElementById("page-title"),
  site: document.getElementById("page-site"),
  saveBadge: document.getElementById("save-badge"),
  status: document.getElementById("status"),
  messages: document.getElementById("messages"),
  form: document.getElementById("ask-form"),
  question: document.getElementById("question"),
  askBtn: document.getElementById("ask-btn"),
  savePageBtn: document.getElementById("save-page-btn"),
  saveQuoteBtn: document.getElementById("save-quote-btn"),
  quoteCompose: document.getElementById("quote-compose"),
  quotePreview: document.getElementById("quote-preview"),
  quoteNote: document.getElementById("quote-note"),
  saveQuoteConfirm: document.getElementById("save-quote-confirm"),
  saveQuoteCancel: document.getElementById("save-quote-cancel"),
  pageQuotes: document.getElementById("page-quotes"),
  exploreBtn: document.getElementById("explore-btn"),
  explorePanel: document.getElementById("explore-panel"),
  exploreSuggestions: document.getElementById("explore-suggestions"),
  selectionBar: document.getElementById("selection-bar"),
  selectionPreview: document.getElementById("selection-preview"),
  nav: document.getElementById("nav"),
  savedList: document.getElementById("saved-list"),
  savedDetail: document.getElementById("saved-detail"),
  savedBack: document.getElementById("saved-back"),
  savedDetailTitle: document.getElementById("saved-detail-title"),
  savedDetailUrl: document.getElementById("saved-detail-url"),
  savedSummary: document.getElementById("saved-summary"),
  savedQuotes: document.getElementById("saved-quotes"),
  savedChat: document.getElementById("saved-chat"),
  deletePageBtn: document.getElementById("delete-page-btn"),
  graphSvg: document.getElementById("graph-svg"),
  graphEmpty: document.getElementById("graph-empty"),
  refreshGraphBtn: document.getElementById("refresh-graph-btn"),
  clearAllBtn: document.getElementById("clear-all-btn"),
  setupPanel: document.getElementById("setup-panel"),
  extensionId: document.getElementById("extension-id"),
  installCommand: document.getElementById("install-command"),
  retryBackendBtn: document.getElementById("retry-backend-btn"),
  retryStatusBtn: document.getElementById("retry-status-btn"),
  pageSubnav: document.getElementById("page-subnav"),
  chatEmptyHint: document.getElementById("chat-empty-hint"),
  proactiveBanner: document.getElementById("proactive-banner"),
  proactiveTitle: document.getElementById("proactive-title"),
  proactiveBody: document.getElementById("proactive-body"),
  proactiveDismiss: document.getElementById("proactive-dismiss"),
  lifeSummary: document.getElementById("life-summary"),
  lifeEvents: document.getElementById("life-events"),
  refreshLifeBtn: document.getElementById("refresh-life-btn"),
};

init();

async function init() {
  bindEvents();
  chrome.storage.onChanged.addListener((changes, area) => {
    if (area === "session" && changes.latestSelection) {
      updateSelection(changes.latestSelection.newValue || "");
    }
    if (area === "session" && changes.quoteSavedAt) {
      loadPageQuotes();
    }
  });
  chrome.storage.session.get("latestSelection", (data) => {
    updateSelection(data.latestSelection || "");
  });
  chrome.runtime.onMessage.addListener((message) => {
    if (message?.type === "QUOTE_SAVED") {
      loadPageQuotes();
    }
  });

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
      refreshSelectionFromPage();
    }
  });

  const backendReady = await ensureBackendReady();
  await refreshPage();
  if (!backendReady) {
    showSetupHelp();
  } else {
    loadProactiveInsights();
    setInterval(loadProactiveInsights, 20 * 60 * 1000);
  }
}

function showSetupHelp(result = {}) {
  els.extensionId.textContent = result.extensionId || chrome.runtime.id || "—";
  els.installCommand.textContent = "node scripts/install-launcher.mjs";
  els.setupPanel.hidden = false;
  els.retryStatusBtn.hidden = false;
}

function hideSetupHelp() {
  els.setupPanel.hidden = true;
  els.retryStatusBtn.hidden = true;
}

async function retryBackendConnection() {
  const ok = await ensureBackendReady();
  if (ok) {
    hideSetupHelp();
    await refreshPage();
    await loadPageQuotes();
  }
}

function bindEvents() {
  els.form.addEventListener("submit", async (event) => {
    event.preventDefault();
    await askQuestion();
  });

  els.question.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!els.askBtn.disabled && els.question.value.trim()) {
        els.form.requestSubmit();
      }
    }
  });

  els.savePageBtn.addEventListener("click", saveCurrentPage);
  els.saveQuoteBtn.addEventListener("click", openQuoteCompose);
  els.saveQuoteConfirm.addEventListener("click", confirmSaveQuote);
  els.saveQuoteCancel.addEventListener("click", () => closeQuoteCompose({ keepSelection: true }));
  els.exploreBtn.addEventListener("click", loadExploreSuggestions);
  els.savedBack.addEventListener("click", showSavedList);
  els.deletePageBtn.addEventListener("click", deleteCurrentSavedPage);
  els.refreshGraphBtn.addEventListener("click", renderGraph);
  els.refreshLifeBtn?.addEventListener("click", loadLifeView);
  els.clearAllBtn.addEventListener("click", clearAllData);
  els.retryBackendBtn.addEventListener("click", retryBackendConnection);
  els.retryStatusBtn.addEventListener("click", retryBackendConnection);
  els.proactiveDismiss?.addEventListener("click", () => {
    els.proactiveBanner.hidden = true;
  });

  els.nav.addEventListener("click", (event) => {
    const button = event.target.closest(".nav-btn");
    if (!button) return;
    switchView(button.dataset.view);
  });

  els.pageSubnav.addEventListener("click", (event) => {
    const button = event.target.closest(".page-tab");
    if (!button) return;
    switchPageTab(button.dataset.pageTab);
  });

  els.exploreSuggestions.addEventListener("click", (event) => {
    const chip = event.target.closest(".suggestion");
    if (!chip) return;
    switchPageTab("chat");
    els.question.value = chip.dataset.question || "";
    els.question.focus();
    els.explorePanel.hidden = true;
  });
}

function switchPageTab(tab) {
  if (!tab) return;
  const changed = tab !== state.pageTab;
  state.pageTab = tab;
  if (changed) {
    document.querySelectorAll(".page-tab").forEach((el) => {
      el.classList.toggle("active", el.dataset.pageTab === tab);
    });
    document.querySelectorAll(".page-panel").forEach((el) => {
      el.classList.toggle("active", el.id === `page-panel-${tab}`);
    });
  }
  if (tab === "chat") {
    els.question.focus();
  }
}

function switchView(view) {
  state.view = view;
  document.querySelectorAll(".nav-btn").forEach((el) => {
    el.classList.toggle("active", el.dataset.view === view);
  });
  document.querySelectorAll(".view").forEach((el) => {
    el.classList.toggle("active", el.id === `view-${view}`);
  });
  if (view === "saved") loadSavedPages();
  if (view === "graph") renderGraph();
  if (view === "life") loadLifeView();
  if (view === "chat") {
    loadPageQuotes();
    refreshSelectionFromPage();
  }
}

function normalizeSelection(text) {
  return (text || "").replace(/\s+/g, " ").trim();
}

function isSaveableSelection(text) {
  return normalizeSelection(text).length >= 8;
}

function updateSelection(selected) {
  const normalized = normalizeSelection(selected);
  const previous = state.selection;
  state.selection = normalized;
  if (state.page) state.page.selected_text = normalized;

  const selectionChanged = normalized !== normalizeSelection(previous);

  if (!isSaveableSelection(normalized)) {
    els.selectionBar.hidden = true;
    els.selectionPreview.textContent = "";
    els.saveQuoteBtn.hidden = true;
    closeQuoteCompose({ keepSelection: true });
    return;
  }

  els.selectionBar.hidden = false;
  els.selectionPreview.textContent =
    normalized.slice(0, 180) + (normalized.length > 180 ? "…" : "");

  const alreadySaved = normalized === state.lastSavedSelection;
  els.selectionBar.classList.toggle("saved", alreadySaved);

  if (alreadySaved) {
    els.saveQuoteBtn.hidden = true;
    closeQuoteCompose({ keepSelection: true });
    return;
  }

  if (selectionChanged) {
    closeQuoteCompose({ keepSelection: true });
    switchPageTab("quotes");
    openQuoteCompose({ auto: true });
  } else if (els.quoteCompose.hidden) {
    els.saveQuoteBtn.hidden = false;
  }
}

async function refreshSelectionFromPage() {
  const page = await getActivePageContext();
  if (page?.selected_text !== undefined) {
    updateSelection(page.selected_text);
  }
}

function openQuoteCompose({ auto = false } = {}) {
  const text = normalizeSelection(state.selection);
  if (!isSaveableSelection(text)) {
    setStatus("Highlight text on the page first", true);
    return;
  }
  if (text === state.lastSavedSelection) {
    return;
  }

  state.pendingQuoteText = text;
  els.quotePreview.textContent = text;
  els.quoteNote.value = "";
  els.quoteCompose.hidden = false;
  els.saveQuoteBtn.hidden = true;
  if (!auto) {
    els.quoteNote.focus();
  }
}

function closeQuoteCompose({ keepSelection = false } = {}) {
  state.pendingQuoteText = "";
  els.quoteCompose.hidden = true;
  if (!keepSelection) {
    state.selection = "";
    state.lastSavedSelection = "";
    els.selectionBar.hidden = true;
    els.selectionPreview.textContent = "";
  }
  const canPromptAgain =
    isSaveableSelection(state.selection) &&
    normalizeSelection(state.selection) !== state.lastSavedSelection;
  els.saveQuoteBtn.hidden = !canPromptAgain;
}

async function confirmSaveQuote() {
  const text = normalizeSelection(state.pendingQuoteText || state.selection);
  if (!text) {
    closeQuoteCompose({ keepSelection: true });
    return;
  }
  els.saveQuoteConfirm.disabled = true;
  els.saveQuoteConfirm.textContent = "Saving…";
  try {
    const ready = await ensureBackendReady();
    if (!ready) {
      setStatus("Backend not connected — fix setup below, then retry", true);
      showSetupHelp();
      return;
    }
    const saved = await saveQuote(text, els.quoteNote.value.trim());
    if (saved) {
      state.lastSavedSelection = text;
      closeQuoteCompose({ keepSelection: true });
      els.saveQuoteBtn.hidden = true;
      els.selectionBar.classList.add("saved");
      setStatus("Quote saved");
      hideSetupHelp();
      switchPageTab("quotes");
      await loadPageQuotes();
    }
  } finally {
    els.saveQuoteConfirm.disabled = false;
    els.saveQuoteConfirm.textContent = "Save quote";
  }
}

async function saveQuote(text, note = "") {
  try {
    const res = await fetch(`${BACKEND}/library/quotes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text,
        page_id: state.savedPageId || "",
        page_url: state.page?.url || "",
        page_title: state.page?.title || "",
        note,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Save quote failed");
    await loadPageQuotes();
    return true;
  } catch (err) {
    setStatus(err.message, true);
    return false;
  }
}

function sendRuntimeMessage(message) {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage(message, (response) => {
      if (chrome.runtime.lastError) {
        resolve({ ok: false, error: chrome.runtime.lastError.message });
        return;
      }
      resolve(response || { ok: false, error: "No response from extension background" });
    });
  });
}

async function ensureBackendReady() {
  if (await checkBackendHealth()) {
    setStatus("Ready");
    hideSetupHelp();
    return true;
  }

  setStatus("Starting backend…");
  const result = await sendRuntimeMessage({ type: "ENSURE_BACKEND" });
  if (await checkBackendHealth()) {
    const provider = await getBackendProvider();
    setStatus(provider ? `Ready (${provider})` : "Ready");
    hideSetupHelp();
    return true;
  }

  if (!result?.ok) {
    if (result?.error === "launcher_missing") {
      setStatus("Launcher not installed — run setup below (one time)", true);
    } else if (result?.error === "native_host_forbidden" || String(result?.error || "").includes("forbidden")) {
      setStatus("Backend auto-start not configured — see setup below", true);
    } else {
      setStatus(result?.hint || result?.manual || result?.error || "Could not start backend", true);
    }
    showSetupHelp(result);
    return false;
  }

  setStatus("Backend did not start in time — try Retry or python3 main.py", true);
  showSetupHelp(result);
  return false;
}

async function checkBackendHealth() {
  try {
    const res = await fetch(`${BACKEND}/health`, { cache: "no-store" });
    if (!res.ok) return false;
    const health = await res.json();
    return health.ok === true;
  } catch {
    return false;
  }
}

async function getBackendProvider() {
  try {
    const res = await fetch(`${BACKEND}/health`, { cache: "no-store" });
    const health = await res.json();
    return health.llm_provider || "";
  } catch {
    return "";
  }
}

async function refreshPage() {
  setStatus("Reading current page…");
  const page = await getActivePageContext();
  if (!page) {
    setStatus("Could not read page context", true);
    return;
  }

  state.page = page;
  state.lastSavedSelection = "";
  updateSelection(page.selected_text || state.selection);
  els.title.textContent = page.title || "Untitled page";
  els.site.textContent = page.site || page.url || "";

  try {
    const res = await fetch(`${BACKEND}/library/by-url?url=${encodeURIComponent(page.url)}`);
    const data = await res.json();
    if (data.page) {
      state.savedPageId = data.page.id;
      state.history = data.page.chat_history || [];
      renderChatHistory(state.history);
      markPageSaved(true);
    } else {
      state.savedPageId = null;
      state.history = [];
      renderChatHistory([]);
      markPageSaved(false);
    }
    await loadPageQuotes();
    setStatus("Ready — chat or save quotes from this page");
  } catch (err) {
    setStatus(err.message, true);
  }
}

async function loadPageQuotes() {
  if (!state.page?.url) {
    els.pageQuotes.innerHTML = '<p class="muted empty-hint">Quotes you save from this page appear here.</p>';
    return;
  }
  try {
    const params = new URLSearchParams();
    if (state.savedPageId) params.set("page_id", state.savedPageId);
    if (state.page.url) params.set("page_url", state.page.url);
    const res = await fetch(`${BACKEND}/library/quotes?${params}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Failed to load quotes");
    state.quotes = (data.quotes || []).sort(
      (a, b) => String(b.saved_at || "").localeCompare(String(a.saved_at || ""))
    );
    renderPageQuotes();
  } catch (err) {
    els.pageQuotes.innerHTML = `<p class="error">${escapeHtml(err.message)}</p>`;
  }
}

function formatQuoteTime(savedAt) {
  if (!savedAt) return "";
  const date = new Date(savedAt);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function renderPageQuotes() {
  els.pageQuotes.innerHTML = "";
  if (!state.quotes.length) {
    els.pageQuotes.innerHTML =
      '<p class="muted empty-hint">Highlight text on the page, then save it as a quote here.</p>';
    return;
  }
  state.quotes.forEach((quote, index) => {
    const card = document.createElement("article");
    card.className = "quote-card";
    const when = formatQuoteTime(quote.saved_at);
    card.innerHTML = `
      <div class="quote-card-head">
        <span class="quote-index">Quote ${state.quotes.length - index}</span>
        ${when ? `<time class="quote-time muted">${escapeHtml(when)}</time>` : ""}
      </div>
      <blockquote>${escapeHtml(quote.text)}</blockquote>
      ${quote.note ? `<div class="quote-note-text">${escapeHtml(quote.note)}</div>` : ""}
    `;
    els.pageQuotes.appendChild(card);
  });
}

function markPageSaved(saved) {
  els.saveBadge.hidden = !saved;
  const label = saved ? "Update saved page" : "Save page";
  els.savePageBtn.textContent = label;
  els.savePageBtn.classList.toggle("saved", saved);
}

function renderChatHistory(history) {
  els.messages.innerHTML = "";
  if (!history.length) {
    const hint = document.createElement("p");
    hint.className = "muted empty-hint";
    hint.id = "chat-empty-hint";
    hint.textContent = "Ask a question about this page.";
    els.messages.appendChild(hint);
    return;
  }
  for (const turn of history) {
    appendMessage(turn.role, turn.content);
  }
}

async function getActivePageContext() {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage({ type: "GET_PAGE_CONTEXT" }, (response) => {
      if (chrome.runtime.lastError) {
        resolve(null);
        return;
      }
      resolve(response?.page || null);
    });
  });
}

async function saveCurrentPage() {
  if (!state.page) return;
  setStatus("Saving page…");
  try {
    const res = await fetch(`${BACKEND}/library/save-page`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ page: state.page, history: state.history }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Save failed");
    state.savedPageId = data.page.id;
    markPageSaved(true);
    await loadPageQuotes();
    setStatus("Page saved");
  } catch (err) {
    setStatus(err.message, true);
  }
}

async function loadExploreSuggestions() {
  if (!state.page) return;
  els.explorePanel.hidden = !els.explorePanel.hidden;
  if (els.explorePanel.hidden) return;

  els.exploreSuggestions.innerHTML = '<p class="muted">Loading suggestions…</p>';
  try {
    const res = await fetch(`${BACKEND}/library/explore`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ page: state.page }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Explore failed");
    els.exploreSuggestions.innerHTML = "";
    const items = data.suggestions || [];
    if (!items.length) {
      els.exploreSuggestions.innerHTML = '<p class="muted">No suggestions right now.</p>';
      return;
    }
    for (const suggestion of items) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "suggestion";
      button.dataset.question = suggestion;
      button.textContent = suggestion;
      els.exploreSuggestions.appendChild(button);
    }
  } catch (err) {
    els.exploreSuggestions.innerHTML = `<p class="error">${escapeHtml(err.message)}</p>`;
  }
}

async function askQuestion() {
  const question = els.question.value.trim();
  if (!question || state.busy || !state.page) return;

  switchPageTab("chat");
  state.busy = true;
  els.askBtn.disabled = true;
  removeChatEmptyHint();
  appendMessage("user", question);
  els.question.value = "";

  const assistantNode = appendMessage("assistant", "");
  try {
    const res = await fetch(`${BACKEND}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        page: state.page,
        saved_page_id: state.savedPageId || "",
        history: state.history,
        stream: true,
      }),
    });

    if (!res.ok) {
      let errMsg = "Ask failed";
      try {
        const err = await res.json();
        errMsg = err.error || errMsg;
      } catch {
        errMsg = `HTTP ${res.status}`;
      }
      throw new Error(errMsg);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let answer = "";
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() || "";
      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith("data:")) continue;
        const payload = JSON.parse(line.slice(5).trim());
        if (payload.error) throw new Error(payload.error);
        if (payload.token) {
          answer += payload.token;
          assistantNode.textContent = answer;
        }
      }
    }

    state.history.push({ role: "user", content: question });
    state.history.push({ role: "assistant", content: answer });
    setStatus("Answer ready");
  } catch (err) {
    assistantNode.textContent = `Error: ${err.message}`;
    assistantNode.classList.add("error");
    setStatus(err.message, true);
  } finally {
    state.busy = false;
    els.askBtn.disabled = false;
  }
}

async function loadSavedPages() {
  els.savedList.hidden = false;
  els.savedDetail.hidden = true;
  els.savedList.innerHTML = '<p class="muted">Loading…</p>';
  try {
    const res = await fetch(`${BACKEND}/library/pages`);
    const data = await res.json();
    state.savedPages = data.pages || [];
    els.savedList.innerHTML = "";
    if (!state.savedPages.length) {
      els.savedList.innerHTML = '<p class="empty-state">No saved pages yet.<br>Save a page from the Page tab.</p>';
      return;
    }
    for (const page of state.savedPages) {
      const card = document.createElement("div");
      card.className = "saved-card";
      card.innerHTML = `
        <h3>${escapeHtml(page.title || "Untitled")}</h3>
        <p class="muted">${escapeHtml(page.site || "")}</p>
        <p>${escapeHtml((page.summary || "").slice(0, 120))}…</p>
      `;
      card.addEventListener("click", () => openSavedPage(page.id));
      els.savedList.appendChild(card);
    }
  } catch (err) {
    els.savedList.innerHTML = `<p class="error">${escapeHtml(err.message)}</p>`;
  }
}

function showSavedList() {
  state.selectedSavedId = null;
  els.savedList.hidden = false;
  els.savedDetail.hidden = true;
}

async function openSavedPage(pageId) {
  try {
    const res = await fetch(`${BACKEND}/library/pages/${pageId}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Failed to load page");
    const page = data.page;
    state.selectedSavedId = pageId;
    els.savedList.hidden = true;
    els.savedDetail.hidden = false;
    els.savedDetailTitle.textContent = page.title || "Untitled";
    els.savedDetailUrl.textContent = page.url || "";
    els.savedSummary.textContent = page.summary || "";

    els.savedQuotes.innerHTML = "";
    const quotes = (page.quotes || []).slice().sort(
      (a, b) => String(b.saved_at || "").localeCompare(String(a.saved_at || ""))
    );
    for (const quote of quotes) {
      const item = document.createElement("li");
      item.className = "quote-list-item";
      const when = formatQuoteTime(quote.saved_at);
      item.innerHTML = `
        <blockquote>${escapeHtml(quote.text)}</blockquote>
        ${quote.note ? `<div class="quote-note-text">${escapeHtml(quote.note)}</div>` : ""}
        ${when ? `<time class="quote-time muted">${escapeHtml(when)}</time>` : ""}
      `;
      els.savedQuotes.appendChild(item);
    }
    if (!quotes.length) {
      els.savedQuotes.innerHTML = '<li class="muted">No quotes saved for this page.</li>';
    }

    els.savedChat.innerHTML = "";
    for (const turn of page.chat_history || []) {
      const node = document.createElement("div");
      node.className = `message ${turn.role}`;
      node.textContent = turn.content;
      els.savedChat.appendChild(node);
    }
    if (!page.chat_history?.length) {
      els.savedChat.innerHTML = '<p class="muted">No chat history yet.</p>';
    }
  } catch (err) {
    setStatus(err.message, true);
  }
}

async function deleteCurrentSavedPage() {
  if (!state.selectedSavedId) return;
  if (!window.confirm("Clear all memory for this page? This cannot be undone.")) return;
  try {
    const res = await fetch(`${BACKEND}/library/pages/${state.selectedSavedId}`, { method: "DELETE" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Delete failed");
    if (state.savedPageId === state.selectedSavedId) {
      state.savedPageId = null;
      markPageSaved(false);
    }
    setStatus("Page memory cleared");
    showSavedList();
    loadSavedPages();
  } catch (err) {
    setStatus(err.message, true);
  }
}

async function renderGraph() {
  els.graphSvg.innerHTML = "";
  try {
    const res = await fetch(`${BACKEND}/library/graph`);
    const data = await res.json();
    const nodes = data.nodes || [];
    const edges = data.edges || [];
    if (!nodes.length) {
      els.graphEmpty.hidden = false;
      return;
    }
    els.graphEmpty.hidden = true;

    const positions = layoutNodes(nodes, 600, 400);
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
      group.setAttribute("class", `graph-node ${node.type || "concept"}`);
      group.setAttribute("transform", `translate(${pos.x}, ${pos.y})`);

      const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      circle.setAttribute("r", node.type === "page" ? 14 : 10);
      group.appendChild(circle);

      const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
      label.setAttribute("y", 24);
      label.setAttribute("text-anchor", "middle");
      label.setAttribute("fill", "#9ca3af");
      label.setAttribute("font-size", "10");
      label.textContent = (node.label || "").slice(0, 24);
      group.appendChild(label);

      g.appendChild(group);
    }
    els.graphSvg.appendChild(g);
  } catch (err) {
    els.graphEmpty.hidden = false;
    els.graphEmpty.textContent = err.message;
  }
}

function layoutNodes(nodes, width, height) {
  const positions = {};
  const cx = width / 2;
  const cy = height / 2;
  const radius = Math.min(width, height) * 0.35;
  nodes.forEach((node, index) => {
    const angle = (index / nodes.length) * Math.PI * 2;
    positions[node.id] = {
      x: cx + Math.cos(angle) * radius,
      y: cy + Math.sin(angle) * radius,
    };
  });
  return positions;
}

async function clearAllData() {
  if (!window.confirm("Clear ALL saved pages, quotes, chat history, and memory? This cannot be undone.")) return;
  try {
    const res = await fetch(`${BACKEND}/library/clear`, { method: "POST" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Clear failed");
    state.savedPageId = null;
    state.history = [];
    state.quotes = [];
    state.savedPages = [];
    renderChatHistory([]);
    markPageSaved(false);
    renderPageQuotes();
    setStatus("All data cleared");
    if (state.view === "saved") loadSavedPages();
    if (state.view === "graph") renderGraph();
  } catch (err) {
    setStatus(err.message, true);
  }
}

function appendMessage(role, text) {
  removeChatEmptyHint();
  const node = document.createElement("div");
  node.className = `message ${role}`;
  node.textContent = text;
  els.messages.appendChild(node);
  els.messages.scrollTop = els.messages.scrollHeight;
  return node;
}

function removeChatEmptyHint() {
  const hint = document.getElementById("chat-empty-hint");
  if (hint) hint.remove();
}

async function loadProactiveInsights() {
  if (!els.proactiveBanner) return;
  try {
    const res = await fetch(`${BACKEND}/proactive`);
    if (!res.ok) return;
    const data = await res.json();
    const insights = data.insights || [];
    if (!insights.length) {
      els.proactiveBanner.hidden = true;
      return;
    }
    const top = insights[0];
    els.proactiveTitle.textContent = top.title || "Insight";
    els.proactiveBody.textContent = top.body || "";
    els.proactiveBanner.hidden = false;
  } catch {
    // Backend may be offline; banner stays hidden
  }
}

async function loadLifeView() {
  if (!els.lifeSummary || !els.lifeEvents) return;
  els.lifeSummary.innerHTML = '<span class="muted">Loading…</span>';
  els.lifeEvents.innerHTML = "";

  try {
    const [summaryRes, eventsRes, taxonomyRes] = await Promise.all([
      fetch(`${BACKEND}/dashboard/time?days=7`),
      fetch(`${BACKEND}/buckets/recent?days=7&limit=25`),
      fetch(`${BACKEND}/buckets/taxonomy`),
    ]);

    const summary = await summaryRes.json();
    const eventsData = await eventsRes.json();
    const taxonomy = await taxonomyRes.json();

    if (!summaryRes.ok) throw new Error(summary.error || "Failed to load summary");
    if (!eventsRes.ok) throw new Error(eventsData.error || "Failed to load events");
    if (!taxonomyRes.ok) throw new Error(taxonomy.error || "Failed to load taxonomy");

    state.bucketLeaves = taxonomy.leaves || [];
    state.lifeEvents = eventsData.events || [];

    els.lifeSummary.innerHTML = "";
    const topLevel = summary.by_top_level || [];
    if (!topLevel.length) {
      els.lifeSummary.innerHTML = '<span class="muted">No classified activity yet.</span>';
    } else {
      for (const item of topLevel) {
        const chip = document.createElement("span");
        chip.className = "life-chip";
        chip.textContent = `${item.category}: ${item.percent}%`;
        els.lifeSummary.appendChild(chip);
      }
    }

    renderLifeEvents();
    setStatus("Life view updated");
  } catch (err) {
    els.lifeSummary.innerHTML = "";
    els.lifeEvents.innerHTML = `<p class="error">${escapeHtml(err.message)}</p>`;
    setStatus(err.message, true);
  }
}

function renderLifeEvents() {
  if (!els.lifeEvents) return;
  els.lifeEvents.innerHTML = "";

  if (!state.lifeEvents.length) {
    els.lifeEvents.innerHTML =
      '<p class="muted empty-hint">Captured events will appear here for bucket review.</p>';
    return;
  }

  for (const event of state.lifeEvents) {
    const card = document.createElement("article");
    card.className = "life-event";
    if (event.user_overridden) card.classList.add("user-overridden");

    const meta = document.createElement("div");
    meta.className = "life-event-meta";
    meta.innerHTML = `
      <span>${escapeHtml(event.source || "unknown")}</span>
      <span class="muted">${escapeHtml(formatTimestamp(event.timestamp))}</span>
    `;

    const preview = document.createElement("p");
    preview.className = "life-event-preview";
    preview.textContent = event.text_preview || "(no preview)";

    const actions = document.createElement("div");
    actions.className = "life-event-actions";

    const select = document.createElement("select");
    select.dataset.eventId = event.event_id;
    for (const leaf of state.bucketLeaves) {
      const option = document.createElement("option");
      option.value = leaf;
      option.textContent = leaf;
      option.selected = leaf === event.bucket;
      select.appendChild(option);
    }

    const saveBtn = document.createElement("button");
    saveBtn.type = "button";
    saveBtn.textContent = "Save";
    saveBtn.disabled = select.value === event.bucket;
    select.addEventListener("change", () => {
      saveBtn.disabled = select.value === event.bucket;
    });
    saveBtn.addEventListener("click", () => overrideEventBucket(event.event_id, select.value, saveBtn));

    actions.append(select, saveBtn);
    card.append(meta, preview, actions);
    els.lifeEvents.appendChild(card);
  }
}

async function overrideEventBucket(eventId, bucket, button) {
  button.disabled = true;
  try {
    const res = await fetch(`${BACKEND}/buckets/override`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event_id: eventId, bucket }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Override failed");
    setStatus(`Moved to ${bucket}`);
    await loadLifeView();
  } catch (err) {
    setStatus(err.message, true);
    button.disabled = false;
  }
}

function formatTimestamp(raw) {
  if (!raw) return "";
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return raw;
  return date.toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

function setStatus(text, isError = false) {
  els.status.textContent = text;
  els.status.classList.toggle("error", isError);
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}
