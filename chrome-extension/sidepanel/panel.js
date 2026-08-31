const BACKEND = "http://127.0.0.1:8765";

const state = {
  page: null,
  savedPageId: null,
  selection: "",
  history: [],
  quotes: [],
  busy: false,
  view: "chat",
  savedPages: [],
  selectedSavedId: null,
  pendingQuoteText: "",
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
  savePageBtnSide: document.getElementById("save-page-btn-side"),
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

  const backendReady = await ensureBackendReady();
  if (backendReady) {
    await refreshPage();
  }
}

function bindEvents() {
  els.form.addEventListener("submit", async (event) => {
    event.preventDefault();
    await askQuestion();
  });

  els.savePageBtn.addEventListener("click", saveCurrentPage);
  els.savePageBtnSide.addEventListener("click", saveCurrentPage);
  els.saveQuoteBtn.addEventListener("click", openQuoteCompose);
  els.saveQuoteConfirm.addEventListener("click", confirmSaveQuote);
  els.saveQuoteCancel.addEventListener("click", closeQuoteCompose);
  els.exploreBtn.addEventListener("click", loadExploreSuggestions);
  els.savedBack.addEventListener("click", showSavedList);
  els.deletePageBtn.addEventListener("click", deleteCurrentSavedPage);
  els.refreshGraphBtn.addEventListener("click", renderGraph);
  els.clearAllBtn.addEventListener("click", clearAllData);

  els.nav.addEventListener("click", (event) => {
    const button = event.target.closest(".nav-btn");
    if (!button) return;
    switchView(button.dataset.view);
  });

  els.exploreSuggestions.addEventListener("click", (event) => {
    const chip = event.target.closest(".suggestion");
    if (!chip) return;
    els.question.value = chip.dataset.question || "";
    els.question.focus();
    els.explorePanel.hidden = true;
  });
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
  if (view === "chat") loadPageQuotes();
}

function updateSelection(selected) {
  state.selection = selected || "";
  if (state.page) state.page.selected_text = state.selection;
  if (state.selection.length >= 8) {
    els.selectionBar.hidden = false;
    els.selectionPreview.textContent =
      state.selection.slice(0, 180) + (state.selection.length > 180 ? "…" : "");
  } else {
    els.selectionBar.hidden = true;
    els.selectionPreview.textContent = "";
  }
}

function openQuoteCompose() {
  const text = state.selection || state.page?.selected_text || "";
  if (!text) {
    setStatus("Highlight text on the page first", true);
    return;
  }
  state.pendingQuoteText = text;
  els.quotePreview.textContent = text;
  els.quoteNote.value = "";
  els.quoteCompose.hidden = false;
  els.saveQuoteBtn.hidden = true;
  els.quoteNote.focus();
}

function closeQuoteCompose() {
  state.pendingQuoteText = "";
  els.quoteCompose.hidden = true;
  els.saveQuoteBtn.hidden = false;
}

async function confirmSaveQuote() {
  const text = state.pendingQuoteText || state.selection || "";
  if (!text) {
    closeQuoteCompose();
    return;
  }
  await saveQuote(text, els.quoteNote.value.trim());
  closeQuoteCompose();
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
    setStatus("Quote saved");
    await loadPageQuotes();
  } catch (err) {
    setStatus(err.message, true);
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
  setStatus("Starting backend…");
  const result = await sendRuntimeMessage({ type: "ENSURE_BACKEND" });
  if (!result?.ok) {
    setStatus(result?.error || "Could not start backend", true);
    return false;
  }

  try {
    const res = await fetch(`${BACKEND}/health`);
    const health = await res.json();
    if (!res.ok) throw new Error("Backend health check failed");
    if (health.api_version !== 2) {
      setStatus("Restarting backend for latest features…");
      await sendRuntimeMessage({ type: "ENSURE_BACKEND" });
    }
    const provider = health.llm_provider || "unknown";
    if (provider === "ollama" && !health.openai_configured) {
      setStatus("Ready (using Ollama — set OPENAI_API_KEY in .env for OpenAI)");
    } else {
      setStatus(`Ready (${provider})`);
    }
    return true;
  } catch (err) {
    setStatus(err.message, true);
    return false;
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
      els.messages.innerHTML = "";
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
    const params = new URLSearchParams({ page_url: state.page.url });
    if (state.savedPageId) params.set("page_id", state.savedPageId);
    const res = await fetch(`${BACKEND}/library/quotes?${params}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Failed to load quotes");
    state.quotes = data.quotes || [];
    renderPageQuotes();
  } catch (err) {
    els.pageQuotes.innerHTML = `<p class="error">${escapeHtml(err.message)}</p>`;
  }
}

function renderPageQuotes() {
  els.pageQuotes.innerHTML = "";
  if (!state.quotes.length) {
    els.pageQuotes.innerHTML = '<p class="muted empty-hint">No quotes yet — highlight text and click Save selection as quote.</p>';
    return;
  }
  for (const quote of state.quotes) {
    const card = document.createElement("div");
    card.className = "quote-card";
    card.innerHTML = `
      <blockquote>${escapeHtml(quote.text)}</blockquote>
      ${quote.note ? `<div class="quote-note-text">${escapeHtml(quote.note)}</div>` : ""}
    `;
    els.pageQuotes.appendChild(card);
  }
}

function markPageSaved(saved) {
  els.saveBadge.hidden = !saved;
  const label = saved ? "Update saved page" : "Save page";
  els.savePageBtn.textContent = label;
  els.savePageBtnSide.textContent = label;
  els.savePageBtn.classList.toggle("saved", saved);
  els.savePageBtnSide.classList.toggle("saved", saved);
}

function renderChatHistory(history) {
  els.messages.innerHTML = "";
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

  state.busy = true;
  els.askBtn.disabled = true;
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
    for (const quote of page.quotes || []) {
      const li = document.createElement("li");
      li.textContent = `"${quote.text}"${quote.note ? ` — ${quote.note}` : ""}`;
      els.savedQuotes.appendChild(li);
    }
    if (!page.quotes?.length) {
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
    els.messages.innerHTML = "";
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
  const node = document.createElement("div");
  node.className = `message ${role}`;
  node.textContent = text;
  els.messages.appendChild(node);
  els.messages.scrollTop = els.messages.scrollHeight;
  return node;
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
