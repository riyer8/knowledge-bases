const BACKEND = "http://127.0.0.1:8765";
const backendReadyCache = { ok: false, checkedAt: 0, ttlMs: 5000 };

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
  clearLibraryBtn: document.getElementById("clear-library-btn"),
  clearAllBtn: document.getElementById("clear-all-btn"),
  setupPanel: document.getElementById("setup-panel"),
  extensionId: document.getElementById("extension-id"),
  installCommand: document.getElementById("install-command"),
  retryBackendBtn: document.getElementById("retry-backend-btn"),
  retryStatusBtn: document.getElementById("retry-status-btn"),
  pageSubnav: document.getElementById("page-subnav"),
  chatEmptyHint: document.getElementById("chat-empty-hint"),
  lifeSummary: document.getElementById("life-summary"),
  lifeEvents: document.getElementById("life-events"),
  pageTypeHint: document.getElementById("page-type-hint"),
  metaAuthor: document.getElementById("meta-author"),
  metaDate: document.getElementById("meta-date"),
  metaCustomFields: document.getElementById("meta-custom-fields"),
  metaAddField: document.getElementById("meta-add-field"),
  header: document.querySelector(".header"),
  openSettingsBtn: document.getElementById("open-settings-btn"),
  settingsBackendStatus: document.getElementById("settings-backend-status"),
  settingsProviderSummary: document.getElementById("settings-provider-summary"),
  settingsRetryBtn: document.getElementById("settings-retry-btn"),
  settingsLlmProvider: document.getElementById("settings-llm-provider"),
  settingsOpenaiKey: document.getElementById("settings-openai-key"),
  settingsAnthropicKey: document.getElementById("settings-anthropic-key"),
  settingsOpenaiHint: document.getElementById("settings-openai-hint"),
  settingsAnthropicHint: document.getElementById("settings-anthropic-hint"),
  settingsOpenaiModel: document.getElementById("settings-openai-model"),
  settingsChatModel: document.getElementById("settings-chat-model"),
  settingsSaveBtn: document.getElementById("settings-save-btn"),
  settingsSaveStatus: document.getElementById("settings-save-status"),
  settingsTheme: document.getElementById("settings-theme"),
  settingsInstallCommand: document.getElementById("settings-install-command"),
  settingsEnvPath: document.getElementById("settings-env-path"),
  settingsSetupNotes: document.getElementById("settings-setup-notes"),
  refreshLifeBtn: document.getElementById("refresh-life-btn"),
  wikiStatus: document.getElementById("wiki-status"),
  wikiArticles: document.getElementById("wiki-articles"),
  wikiEmpty: document.getElementById("wiki-empty"),
  wikiCompileBtn: document.getElementById("wiki-compile-btn"),
  wikiRefreshBtn: document.getElementById("wiki-refresh-btn"),
  wikiAskInput: document.getElementById("wiki-ask-input"),
  wikiAskBtn: document.getElementById("wiki-ask-btn"),
  wikiAskReply: document.getElementById("wiki-ask-reply"),
  addToWikiBtn: document.getElementById("add-to-wiki-btn"),
  addPageToWikiBtn: document.getElementById("add-page-to-wiki-btn"),
  confirmOverlay: document.getElementById("confirm-overlay"),
  confirmTitle: document.getElementById("confirm-title"),
  confirmMessage: document.getElementById("confirm-message"),
  confirmOk: document.getElementById("confirm-ok"),
  confirmCancel: document.getElementById("confirm-cancel"),
};

let activeConfirmFinish = null;

function showConfirmDialog({
  title,
  message,
  confirmText = "Confirm",
  cancelText = "Cancel",
  danger = false,
}) {
  return new Promise((resolve) => {
    if (activeConfirmFinish) {
      activeConfirmFinish(false);
    }

    const finish = (value) => {
      if (!activeConfirmFinish) return;
      activeConfirmFinish = null;
      if (els.confirmOverlay) els.confirmOverlay.hidden = true;
      resolve(Boolean(value));
    };
    activeConfirmFinish = finish;

    if (els.confirmTitle) els.confirmTitle.textContent = title;
    if (els.confirmMessage) {
      const lines = String(message || "")
        .split(/\n\s*\n/)
        .map((part) => part.trim())
        .filter(Boolean);
      els.confirmMessage.innerHTML = lines
        .map((part) => `<p>${escapeHtml(part)}</p>`)
        .join("");
    }
    if (els.confirmOk) {
      els.confirmOk.textContent = confirmText;
      els.confirmOk.classList.toggle("danger-btn", danger);
      els.confirmOk.classList.toggle("primary", !danger);
    }
    if (els.confirmCancel) els.confirmCancel.textContent = cancelText;

    const onConfirm = (event) => {
      event.preventDefault();
      event.stopPropagation();
      finish(true);
    };
    const onCancel = (event) => {
      event.preventDefault();
      event.stopPropagation();
      finish(false);
    };
    const onBackdrop = (event) => {
      if (event.target === els.confirmOverlay) finish(false);
    };

    els.confirmOk?.addEventListener("click", onConfirm, { once: true });
    els.confirmCancel?.addEventListener("click", onCancel, { once: true });
    els.confirmOverlay?.addEventListener("click", onBackdrop, { once: true });

    if (els.confirmOverlay) els.confirmOverlay.hidden = false;
    els.confirmCancel?.focus();
  });
}

function on(el, eventName, handler) {
  if (!el) return;
  el.addEventListener(eventName, handler);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}

async function init() {
  try {
    bindEvents();
  } catch (err) {
    console.error("Failed to bind extension UI events", err);
    setStatus("UI failed to initialize — reload the extension", true);
    return;
  }
  chrome.storage.onChanged.addListener((changes, area) => {
    if (area === "session" && changes.latestSelection) {
      updateSelection(changes.latestSelection.newValue || "");
    }
    if (area === "session" && changes.quoteSavedAt) {
      void Promise.all([loadPageQuotes(), syncHighlightsToPage()]);
    }
    if (area === "session" && changes.activeTabUrl) {
      const nextUrl = changes.activeTabUrl.newValue || "";
      if (nextUrl && nextUrl !== state.page?.url) {
        refreshPage();
      }
    }
  });
  chrome.storage.session.get(["latestSelection", "activeTabUrl"], (data) => {
    updateSelection(data.latestSelection || "");
    if (data.activeTabUrl && data.activeTabUrl !== state.page?.url) {
      refreshPage();
    }
  });
  chrome.runtime.onMessage.addListener((message) => {
    if (message?.type === "QUOTE_SAVED") {
      void Promise.all([loadPageQuotes(), syncHighlightsToPage()]);
    }
    if (message?.type === "TAB_CHANGED" && message.url && message.url !== state.page?.url) {
      refreshPage();
    }
  });

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
      refreshSelectionFromPage();
    }
  });

  const backendReady = await Promise.all([
    refreshPageContext(),
    ensureBackendReady(),
  ]).then(([, ready]) => ready);

  await syncPageLibraryState();
  if (!backendReady) {
    showSetupHelp();
  } else {
    hideSetupHelp();
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
    await syncPageLibraryState();
    if (state.view === "settings") loadSettingsView();
  }
}

function bindEvents() {
  on(els.form, "submit", async (event) => {
    event.preventDefault();
    await askQuestion();
  });

  on(els.question, "keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!els.askBtn?.disabled && els.question?.value.trim()) {
        els.form?.requestSubmit();
      }
    }
  });

  on(els.savePageBtn, "click", () => {
    saveCurrentPage().catch((err) => {
      console.error(err);
      setStatus(err.message || "Save failed", true);
    });
  });
  on(els.saveQuoteBtn, "click", openQuoteCompose);
  on(els.saveQuoteConfirm, "click", confirmSaveQuote);
  on(els.saveQuoteCancel, "click", () => closeQuoteCompose({ keepSelection: true }));
  on(els.exploreBtn, "click", loadExploreSuggestions);
  on(els.savedBack, "click", showSavedList);
  on(els.deletePageBtn, "click", () => deleteSavedPage(state.selectedSavedId));
  els.savedList?.addEventListener("click", (event) => {
    const deleteBtn = event.target.closest("[data-delete-page]");
    if (deleteBtn) {
      event.preventDefault();
      event.stopPropagation();
      void deleteSavedPage(deleteBtn.dataset.deletePage);
      return;
    }
    const card = event.target.closest(".saved-card");
    if (card?.dataset.pageId) openSavedPage(card.dataset.pageId);
  });
  on(els.refreshGraphBtn, "click", renderGraph);
  on(els.refreshLifeBtn, "click", loadLifeView);
  on(els.wikiCompileBtn, "click", compileWiki);
  on(els.wikiRefreshBtn, "click", loadWikiView);
  on(els.wikiAskBtn, "click", askWikiQuestion);
  on(els.addToWikiBtn, "click", addSelectedPageToWiki);
  on(els.addPageToWikiBtn, "click", addCurrentPageToWiki);
  on(els.clearLibraryBtn, "click", clearSavedLibrary);
  on(els.clearAllBtn, "click", clearAllData);
  on(els.openSettingsBtn, "click", () => switchView("settings"));
  on(els.settingsSaveBtn, "click", saveSettingsFromForm);
  on(els.settingsRetryBtn, "click", retryBackendConnection);
  on(els.settingsTheme, "change", (event) => {
    ContextTheme.setTheme(event.target.value);
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && activeConfirmFinish) {
      event.preventDefault();
      activeConfirmFinish(false);
    }
  });
  on(els.retryBackendBtn, "click", retryBackendConnection);
  on(els.retryStatusBtn, "click", retryBackendConnection);
  els.title?.addEventListener("input", () => {
    resizeTitleField();
    schedulePageDraftSave();
  });
  els.title?.addEventListener("blur", savePageDetails);
  els.title?.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
      event.preventDefault();
      els.title.blur();
    }
  });
  els.metaAuthor?.addEventListener("blur", savePageDetails);
  els.metaDate?.addEventListener("blur", savePageDetails);
  els.metaAuthor?.addEventListener("input", schedulePageDraftSave);
  els.metaDate?.addEventListener("input", schedulePageDraftSave);
  els.metaAddField?.addEventListener("click", () => {
    addCustomMetaField("", "");
    schedulePageDraftSave();
  });
  els.metaCustomFields?.addEventListener("input", schedulePageDraftSave);
  els.metaCustomFields?.addEventListener("click", (event) => {
    const removeBtn = event.target.closest("[data-remove-meta]");
    if (!removeBtn) return;
    removeBtn.closest(".meta-custom-row")?.remove();
    schedulePageDraftSave();
    savePageDetails();
  });
  els.pageQuotes?.addEventListener("click", handlePageQuoteAction);

  on(els.nav, "click", (event) => {
    const button = event.target.closest(".nav-btn");
    if (!button) return;
    switchView(button.dataset.view);
  });

  on(els.pageSubnav, "click", (event) => {
    const button = event.target.closest(".page-tab");
    if (!button) return;
    switchPageTab(button.dataset.pageTab);
  });

  on(els.exploreSuggestions, "click", (event) => {
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
    el.classList.toggle("active", view !== "settings" && el.dataset.view === view);
  });
  document.querySelectorAll(".view").forEach((el) => {
    el.classList.toggle("active", el.id === `view-${view}`);
  });
  els.header?.classList.toggle("page-context-hidden", view !== "chat");
  els.openSettingsBtn?.classList.toggle("active", view === "settings");
  if (view === "saved") loadSavedPages();
  if (view === "graph") renderGraph();
  if (view === "life") loadLifeView();
  if (view === "wiki") loadWikiView();
  if (view === "settings") loadSettingsView();
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

  els.saveQuoteBtn.hidden = false;
  closeQuoteCompose({ keepSelection: true });
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
      await syncHighlightsToPage();
    }
  } finally {
    els.saveQuoteConfirm.disabled = false;
    els.saveQuoteConfirm.textContent = "Save quote";
  }
}

async function saveQuote(text, note = "") {
  const optimistic = {
    id: `local-${Date.now()}`,
    text,
    note,
    saved_at: new Date().toISOString(),
  };
  state.quotes = [optimistic, ...state.quotes.filter((q) => q.text !== text)];
  renderPageQuotes();

  try {
    const res = await fetch(`${BACKEND}/library/quotes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text,
        page_id: state.savedPageId || "",
        page_url: state.page?.url || "",
        page_title: getDisplayTitle(),
        note,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Save quote failed");
    if (data.quote) {
      state.quotes = [
        data.quote,
        ...state.quotes.filter((q) => q.id !== optimistic.id && q.text !== text),
      ];
      renderPageQuotes();
    }
    return true;
  } catch (err) {
    state.quotes = state.quotes.filter((q) => q.id !== optimistic.id);
    renderPageQuotes();
    setStatus(err.message, true);
    return false;
  }
}

function getDisplayTitle() {
  return (els.title?.value || state.page?.title || "").trim() || "Untitled page";
}

function resizeTitleField() {
  const field = els.title;
  if (!field) return;
  field.style.height = "auto";
  field.style.height = `${field.scrollHeight}px`;
}

function emptyMetadata() {
  return { author: "", date: "", custom: [] };
}

function normalizeMetadata(raw) {
  const meta = emptyMetadata();
  if (!raw) return meta;
  meta.author = String(raw.author || "").trim();
  meta.date = String(raw.date || "").trim();
  meta.custom = Array.isArray(raw.custom)
    ? raw.custom
        .map((item) => ({
          key: String(item?.key || "").trim(),
          value: String(item?.value || "").trim(),
        }))
        .filter((item) => item.key)
        .slice(0, 30)
    : [];
  return meta;
}

function mergeMetadata(preferred, fallback) {
  const base = normalizeMetadata(fallback);
  const chosen = normalizeMetadata(preferred);
  return {
    author: chosen.author || base.author,
    date: chosen.date || base.date,
    custom: chosen.custom.length ? chosen.custom : base.custom,
  };
}

function collectMetadataFromForm() {
  const custom = [];
  els.metaCustomFields?.querySelectorAll(".meta-custom-row").forEach((row) => {
    const key = row.querySelector("[data-meta-key]")?.value?.trim() || "";
    const value = row.querySelector("[data-meta-value]")?.value?.trim() || "";
    if (key) custom.push({ key, value });
  });
  return normalizeMetadata({
    author: els.metaAuthor?.value || "",
    date: els.metaDate?.value || "",
    custom,
  });
}

function applyMetadataToForm(metadata) {
  const meta = normalizeMetadata(metadata);
  if (els.metaAuthor) els.metaAuthor.value = meta.author;
  if (els.metaDate) els.metaDate.value = meta.date;
  renderCustomMetaFields(meta.custom);
}

function renderCustomMetaFields(custom) {
  if (!els.metaCustomFields) return;
  els.metaCustomFields.innerHTML = "";
  (custom || []).forEach((field) => addCustomMetaField(field.key, field.value));
}

function addCustomMetaField(key = "", value = "") {
  if (!els.metaCustomFields) return;
  const row = document.createElement("div");
  row.className = "meta-custom-row";
  row.innerHTML = `
    <input type="text" data-meta-key placeholder="Label" value="${escapeAttr(key)}" />
    <input type="text" data-meta-value placeholder="Value" value="${escapeAttr(value)}" />
    <button type="button" class="text-btn" data-remove-meta title="Remove field">Remove</button>
  `;
  els.metaCustomFields.appendChild(row);
}

function escapeAttr(text) {
  return String(text || "")
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;");
}

let pageDraftTimer = null;
function schedulePageDraftSave() {
  clearTimeout(pageDraftTimer);
  pageDraftTimer = setTimeout(() => {
    persistPageDraft();
  }, 400);
}

async function loadPageDraft(url) {
  if (!url) return null;
  return new Promise((resolve) => {
    chrome.storage.local.get(`pageDraft:${url}`, (data) => {
      resolve(data[`pageDraft:${url}`] || null);
    });
  });
}

async function persistPageDraft() {
  if (!state.page?.url) return;
  const draft = {
    title: getDisplayTitle(),
    metadata: collectMetadataFromForm(),
  };
  await chrome.storage.local.set({ [`pageDraft:${state.page.url}`]: draft });
}

async function savePageDetails() {
  if (!state.page?.url) return;
  const title = getDisplayTitle();
  const metadata = collectMetadataFromForm();
  state.page.title = title;
  state.page.metadata = metadata;
  await persistPageDraft();

  if (state.savedPageId) {
    try {
      const res = await fetch(`${BACKEND}/library/pages/${state.savedPageId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, metadata }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || "Could not update page details");
      }
      setStatus("Details updated");
    } catch (err) {
      setStatus(err.message, true);
    }
  }
}

async function syncHighlightsToPage() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab?.id) {
      await chrome.tabs.sendMessage(tab.id, { type: "REPAINT_HIGHLIGHTS" });
    }
  } catch {
    // Restricted pages (e.g. chrome://) cannot host highlights.
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

async function ensureBackendReady({ quiet = false } = {}) {
  const now = Date.now();
  if (backendReadyCache.ok && now - backendReadyCache.checkedAt < backendReadyCache.ttlMs) {
    if (!quiet) {
      setStatus("Ready");
      hideSetupHelp();
    }
    return true;
  }

  if (await checkBackendHealth()) {
    backendReadyCache.ok = true;
    backendReadyCache.checkedAt = now;
    if (!quiet) {
      setStatus("Ready");
      hideSetupHelp();
    }
    return true;
  }
  backendReadyCache.ok = false;

  if (!quiet) setStatus("Starting backend…");
  const result = await sendRuntimeMessage({ type: "ENSURE_BACKEND" });
  if (await checkBackendHealth()) {
    backendReadyCache.ok = true;
    backendReadyCache.checkedAt = Date.now();
    const provider = await getBackendProvider();
    if (!quiet) setStatus(provider ? `Ready (${provider})` : "Ready");
    hideSetupHelp();
    return true;
  }
  backendReadyCache.ok = false;

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
  await refreshPageContext();
  if (await checkBackendHealth()) {
    await syncPageLibraryState();
  }
}

async function refreshPageContext() {
  const previousUrl = state.page?.url || "";
  setStatus("Reading page…");
  const page = await getActivePageContext();
  if (!page) {
    setStatus("Could not read page context", true);
    return;
  }

  const isNewPage = Boolean(previousUrl && page.url !== previousUrl);
  state.page = page;
  if (isNewPage) {
    state.history = [];
    state.quotes = [];
    els.messages.innerHTML = "";
    removeChatEmptyHint();
    els.question.value = "";
    closeQuoteCompose({ keepSelection: true });
    els.explorePanel.hidden = true;
  }
  state.lastSavedSelection = "";
  updateSelection(page.selected_text || state.selection);

  const suggestedTitle = page.title || "Untitled page";
  const suggestedMetadata = normalizeMetadata(page.metadata);
  const draft = await loadPageDraft(page.url);

  els.site.textContent = page.site || page.url || "";
  if (els.pageTypeHint) {
    if (page.page_type === "pdf") {
      els.pageTypeHint.hidden = false;
      els.pageTypeHint.textContent = "PDF document — text extracted for chat and quotes";
    } else {
      els.pageTypeHint.hidden = true;
      els.pageTypeHint.textContent = "";
    }
  }

  els.title.value = draft?.title || suggestedTitle;
  applyMetadataToForm(mergeMetadata(draft?.metadata, suggestedMetadata));
  resizeTitleField();
  state.page.title = getDisplayTitle();
  state.page.metadata = collectMetadataFromForm();

  if (await checkBackendHealth()) {
    setStatus(isNewPage ? "New page loaded" : "Ready — chat or save quotes from this page");
  }
}

async function syncPageLibraryState() {
  if (!state.page?.url) return;
  const previousUrl = state.page.url;
  const suggestedTitle = state.page.title || "Untitled page";
  const suggestedMetadata = normalizeMetadata(state.page.metadata);
  const draft = await loadPageDraft(previousUrl);

  try {
    const res = await fetch(`${BACKEND}/library/by-url?url=${encodeURIComponent(previousUrl)}`);
    const data = await res.json();
    if (data.page) {
      state.savedPageId = data.page.id;
      state.history = data.page.chat_history || [];
      renderChatHistory(state.history);
      markPageSaved(true);
      els.title.value = data.page.title || draft?.title || suggestedTitle;
      applyMetadataToForm(
        mergeMetadata(draft?.metadata || data.page.metadata, suggestedMetadata)
      );
    } else {
      state.savedPageId = null;
      state.history = [];
      renderChatHistory([]);
      markPageSaved(false);
    }
    resizeTitleField();
    state.page.title = getDisplayTitle();
    state.page.metadata = collectMetadataFromForm();
    await Promise.all([loadPageQuotes(), syncHighlightsToPage()]);
    const provider = await getBackendProvider();
    setStatus(provider ? `Ready (${provider})` : "Ready");
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
    const quoteId = quote.id || "";
    const when = formatQuoteTime(quote.saved_at);
    card.innerHTML = `
      <div class="quote-card-head">
        <span class="quote-index">Quote ${state.quotes.length - index}</span>
        ${when ? `<time class="quote-time muted">${escapeHtml(when)}</time>` : ""}
      </div>
      <blockquote>${escapeHtml(quote.text)}</blockquote>
      ${quote.note ? `<div class="quote-note-text">${escapeHtml(quote.note)}</div>` : ""}
      <div class="quote-card-actions">
        <button type="button" class="text-btn" data-quote-edit data-quote-id="${escapeAttr(quoteId)}">Edit</button>
        <button type="button" class="text-btn danger-text" data-quote-delete data-quote-id="${escapeAttr(quoteId)}">Delete</button>
      </div>
    `;
    card.dataset.quoteId = quoteId;
    card.dataset.quoteIndex = String(index);
    els.pageQuotes.appendChild(card);
  });
}

function quoteApiPath(quoteId) {
  return `${BACKEND}/library/quotes/${encodeURIComponent(String(quoteId || "").trim())}`;
}

function handlePageQuoteAction(event) {
  const deleteBtn = event.target.closest("[data-quote-delete]");
  if (deleteBtn) {
    event.preventDefault();
    event.stopPropagation();
    const card = deleteBtn.closest(".quote-card");
    const quote = findQuoteById(
      deleteBtn.dataset.quoteId || card?.dataset.quoteId,
      Number(card?.dataset.quoteIndex)
    );
    if (quote) void deleteQuote(quote);
    return;
  }

  const editBtn = event.target.closest("[data-quote-edit]");
  if (editBtn) {
    event.preventDefault();
    event.stopPropagation();
    const card = editBtn.closest(".quote-card");
    const quote = findQuoteById(
      editBtn.dataset.quoteId || card?.dataset.quoteId,
      Number(card?.dataset.quoteIndex)
    );
    if (quote && card) startQuoteEdit(card, quote);
    return;
  }

  handleQuoteEditAction(event);
}

function findQuoteById(quoteId, quoteIndex) {
  const normalizedId = String(quoteId || "").trim();
  if (normalizedId) {
    const match = state.quotes.find((q) => String(q.id || "").trim() === normalizedId);
    if (match) return match;
  }
  if (quoteIndex >= 0 && quoteIndex < state.quotes.length) {
    return state.quotes[quoteIndex];
  }
  return null;
}

function handleQuoteEditAction(event) {
  const saveBtn = event.target.closest("[data-quote-save]");
  const cancelBtn = event.target.closest("[data-quote-cancel-edit]");
  if (!saveBtn && !cancelBtn) return;

  const card = event.target.closest(".quote-card");
  if (!card) return;

  event.preventDefault();
  event.stopPropagation();

  const quote = findQuoteById(card.dataset.quoteId, Number(card.dataset.quoteIndex));
  if (!quote) {
    setStatus("Could not find that quote — try refreshing", true);
    return;
  }

  if (saveBtn) {
    void saveQuoteEdit(card, quote);
    return;
  }
  if (cancelBtn) {
    renderPageQuotes();
  }
}

function startQuoteEdit(card, quote) {
  card.classList.add("editing");
  const form = document.createElement("div");
  form.className = "quote-edit-form";
  form.innerHTML = `
    <textarea rows="4" data-quote-edit-text></textarea>
    <input type="text" data-quote-edit-note placeholder="Optional note…" />
    <div class="quote-edit-actions">
      <button type="button" class="toolbar-btn primary" data-quote-save>Save changes</button>
      <button type="button" class="text-btn" data-quote-cancel-edit>Close</button>
    </div>
  `;
  form.querySelector("[data-quote-edit-text]").value = quote.text || "";
  form.querySelector("[data-quote-edit-note]").value = quote.note || "";
  card.querySelector(".quote-card-actions")?.replaceWith(form);
}

async function saveQuoteEdit(card, quote) {
  const text = card.querySelector("[data-quote-edit-text]")?.value?.trim() || "";
  const note = card.querySelector("[data-quote-edit-note]")?.value?.trim() || "";
  if (!text) {
    setStatus("Quote text cannot be empty", true);
    return;
  }
  if (!quote.id || quote.id.startsWith("local-")) {
    quote.text = text;
    quote.note = note;
    renderPageQuotes();
    return;
  }
  try {
    const res = await fetch(quoteApiPath(quote.id), {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, note }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Could not update quote");
    const idx = state.quotes.findIndex((q) => q.id === quote.id);
    if (idx >= 0) state.quotes[idx] = data.quote;
    renderPageQuotes();
    await syncHighlightsToPage();
    setStatus("Quote updated");
  } catch (err) {
    setStatus(err.message, true);
  }
}

async function deleteQuote(quote) {
  const quoteId = String(quote?.id || "").trim();
  const confirmed = await showConfirmDialog({
    title: "Delete quote?",
    message: "Remove this quote from your library?",
    confirmText: "Delete",
    cancelText: "Keep",
    danger: true,
  });
  if (!confirmed) return;

  const current = findQuoteById(quoteId, -1) || quote;
  const id = String(current?.id || quoteId).trim();

  if (!id || id.startsWith("local-")) {
    state.quotes = state.quotes.filter((q) => String(q.id || "").trim() !== id);
    renderPageQuotes();
    void syncHighlightsToPage();
    setStatus("Quote deleted");
    return;
  }

  const previousQuotes = state.quotes.slice();
  state.quotes = state.quotes.filter((q) => String(q.id || "").trim() !== id);
  renderPageQuotes();
  void syncHighlightsToPage();

  try {
    const ready = await ensureBackendReady({ quiet: true });
    if (!ready) throw new Error("Backend not connected");

    const res = await fetch(quoteApiPath(id), { method: "DELETE" });
    if (res.status === 404) {
      setStatus("Quote deleted");
      return;
    }
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.error || `Could not delete quote (${res.status})`);
    }
    setStatus("Quote deleted");
  } catch (err) {
    state.quotes = previousQuotes;
    renderPageQuotes();
    setStatus(err.message, true);
    void loadPageQuotes();
  }
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
  if (!state.page?.url) {
    setStatus("Can't save this page — try a normal website (not chrome:// or the new tab page)", true);
    return;
  }
  const ready = await ensureBackendReady();
  if (!ready) {
    setStatus("Backend not connected — check Settings", true);
    showSetupHelp();
    return;
  }
  setStatus("Saving page…");
  try {
    state.page.title = getDisplayTitle();
    state.page.metadata = collectMetadataFromForm();
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
    assistantNode.classList.add("markdown-body");
    assistantNode.innerHTML = renderMarkdown(answer);
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
      card.dataset.pageId = page.id;
      const summaryPreview = (page.summary || "").replace(/\s+/g, " ").trim();
      card.innerHTML = `
        <div class="saved-card-main">
          <h3>${escapeHtml(page.title || "Untitled")}</h3>
          <p class="muted">${escapeHtml(page.site || "")}</p>
          <p class="saved-card-summary">${escapeHtml(summaryPreview.slice(0, 140))}${summaryPreview.length > 140 ? "…" : ""}</p>
        </div>
        <button type="button" class="text-btn danger-text saved-card-delete" data-delete-page="${escapeAttr(page.id)}">Delete</button>
      `;
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
    els.savedSummary.innerHTML = renderMarkdown(page.summary || "_No summary._");

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
      if (turn.role === "assistant") {
        node.classList.add("markdown-body");
        node.innerHTML = renderMarkdown(turn.content);
      } else {
        node.textContent = turn.content;
      }
      els.savedChat.appendChild(node);
    }
    if (!page.chat_history?.length) {
      els.savedChat.innerHTML = '<p class="muted">No chat history yet.</p>';
    }
  } catch (err) {
    setStatus(err.message, true);
  }
}

async function deleteSavedPage(pageId) {
  const id = String(pageId || state.selectedSavedId || "").trim();
  if (!id) return;
  const confirmed = await showConfirmDialog({
    title: "Delete page?",
    message: "Removes this saved page, its quotes, and chat history. This cannot be undone.",
    confirmText: "Delete",
    cancelText: "Cancel",
    danger: true,
  });
  if (!confirmed) return;
  try {
    const res = await fetch(`${BACKEND}/library/pages/${encodeURIComponent(id)}`, { method: "DELETE" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Delete failed");
    if (state.savedPageId === id) {
      state.savedPageId = null;
      markPageSaved(false);
    }
    if (state.selectedSavedId === id) {
      state.selectedSavedId = null;
    }
    setStatus("Page deleted");
    showSavedList();
    loadSavedPages();
    if (state.view === "graph") renderGraph();
  } catch (err) {
    setStatus(err.message, true);
  }
}

async function renderGraph() {
  els.graphSvg.innerHTML = "";
  try {
    const res = await fetch(`${BACKEND}/library/graph`);
    const data = await res.json();
    const nodes = (data.nodes || []).filter((node) => node.type === "page");
    const edges = data.edges || [];
    if (!nodes.length) {
      els.graphEmpty.hidden = false;
      els.graphEmpty.textContent = "Save pages to see how they connect.";
      return;
    }
    els.graphEmpty.hidden = true;

    const width = 600;
    const height = Math.max(400, nodes.length * 70);
    els.graphSvg.setAttribute("viewBox", `0 0 ${width} ${height}`);

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
      group.setAttribute("class", "graph-node page");
      group.setAttribute("transform", `translate(${pos.x}, ${pos.y})`);

      const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      circle.setAttribute("r", 12);
      group.appendChild(circle);

      const labelWidth = 150;
      const fo = document.createElementNS("http://www.w3.org/2000/svg", "foreignObject");
      fo.setAttribute("x", String(-labelWidth / 2));
      fo.setAttribute("y", "16");
      fo.setAttribute("width", String(labelWidth));
      fo.setAttribute("height", "72");
      const label = document.createElement("div");
      label.className = "graph-node-label";
      const title = document.createElement("div");
      title.className = "graph-node-title";
      title.textContent = node.label || "Page";
      label.appendChild(title);
      if (node.quote_count) {
        const count = document.createElement("div");
        count.className = "graph-node-meta";
        count.textContent = `${node.quote_count} quote${node.quote_count === 1 ? "" : "s"}`;
        label.appendChild(count);
      }
      fo.appendChild(label);
      group.appendChild(fo);

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

async function clearSavedLibrary() {
  const confirmed = await showConfirmDialog({
    title: "Clear saved pages?",
    message:
      "Removes saved pages, quotes, and per-page chats.\n\nCaptured events, Life buckets, and integrations will stay.",
    confirmText: "Clear saved pages",
    cancelText: "Cancel",
  });
  if (!confirmed) return;
  try {
    const res = await fetch(`${BACKEND}/library/clear`, { method: "POST" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Clear failed");
    state.savedPageId = null;
    state.savedPages = [];
    state.selectedSavedId = null;
    state.quotes = [];
    markPageSaved(false);
    renderPageQuotes();
    setStatus("Saved pages cleared");
    if (state.view === "chat") void loadPageQuotes();
    if (state.view === "saved") loadSavedPages();
    if (state.view === "graph") renderGraph();
    if (state.view === "settings") loadSettingsView();
  } catch (err) {
    setStatus(err.message, true);
  }
}

async function clearAllData() {
  const confirmed = await showConfirmDialog({
    title: "Delete all data?",
    message:
      "Wipes everything in ~/.kb/ — events, memory, relationships, integrations, and your saved library.\n\nThis cannot be undone.",
    confirmText: "Delete everything",
    cancelText: "Cancel",
    danger: true,
  });
  if (!confirmed) return;
  try {
    const res = await fetch(`${BACKEND}/delete-all`, { method: "POST" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Delete failed");
    resetExtensionClientState();
    setStatus("All data deleted");
    if (state.view === "saved") loadSavedPages();
    if (state.view === "graph") renderGraph();
    if (state.view === "life") loadLifeView();
    if (state.view === "settings") loadSettingsView();
  } catch (err) {
    setStatus(err.message, true);
  }
}

function applySettingsToForm(settings) {
  if (!settings) return;
  if (els.settingsLlmProvider) {
    els.settingsLlmProvider.value = settings.llm_provider_setting || "auto";
  }
  if (els.settingsOpenaiModel) els.settingsOpenaiModel.value = settings.openai_model || "";
  if (els.settingsChatModel) els.settingsChatModel.value = settings.chat_model || "";
  if (els.settingsOpenaiKey) els.settingsOpenaiKey.value = "";
  if (els.settingsAnthropicKey) els.settingsAnthropicKey.value = "";
  if (els.settingsOpenaiHint) {
    els.settingsOpenaiHint.textContent = settings.openai_configured
      ? `Configured (${settings.openai_key_hint}) — leave blank to keep current key`
      : "Not set — paste your key from platform.openai.com";
  }
  if (els.settingsAnthropicHint) {
    els.settingsAnthropicHint.textContent = settings.anthropic_configured
      ? `Configured (${settings.anthropic_key_hint}) — leave blank to keep current key`
      : "Optional — for Anthropic provider";
  }
  if (els.settingsEnvPath) els.settingsEnvPath.textContent = settings.env_path || ".env";
  if (els.settingsInstallCommand) {
    els.settingsInstallCommand.textContent = "node scripts/install-launcher.mjs";
  }
  if (els.settingsSetupNotes) {
    els.settingsSetupNotes.innerHTML = "";
    for (const note of settings.setup_notes || []) {
      const item = document.createElement("li");
      item.textContent = note;
      els.settingsSetupNotes.appendChild(item);
    }
  }
  if (els.settingsProviderSummary) {
    const bits = [
      `Active provider: ${settings.llm_provider || "unknown"}`,
      settings.ollama_required ? `Ollama model: ${settings.chat_model}` : `Model: ${settings.openai_model || settings.chat_model}`,
    ];
    els.settingsProviderSummary.textContent = bits.join(" · ");
  }
}

function updateSettingsBackendStatus(ok, message = "") {
  if (!els.settingsBackendStatus) return;
  els.settingsBackendStatus.classList.remove("ok", "warn", "error");
  if (ok) {
    els.settingsBackendStatus.textContent = message || "Connected to local backend";
    els.settingsBackendStatus.classList.add("ok");
    els.settingsRetryBtn.hidden = true;
  } else {
    els.settingsBackendStatus.textContent = message || "Backend not connected";
    els.settingsBackendStatus.classList.add("error");
    els.settingsRetryBtn.hidden = false;
  }
}

async function loadSettingsView() {
  ContextTheme.syncThemeSelect(els.settingsTheme);
  const backendOk = await checkBackendHealth();
  updateSettingsBackendStatus(backendOk);
  if (!backendOk) {
    if (els.settingsProviderSummary) {
      els.settingsProviderSummary.textContent = "Start the backend to save API keys from here, or edit .env manually.";
    }
    return;
  }
  try {
    const res = await fetch(`${BACKEND}/settings`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Could not load settings");
    applySettingsToForm(data);
    const provider = data.llm_provider || "";
    updateSettingsBackendStatus(true, provider ? `Connected · using ${provider}` : "Connected");
  } catch (err) {
    updateSettingsBackendStatus(false, err.message);
  }
}

async function saveSettingsFromForm() {
  if (!els.settingsSaveBtn) return;
  els.settingsSaveBtn.disabled = true;
  if (els.settingsSaveStatus) els.settingsSaveStatus.textContent = "Saving…";
  try {
    const ready = await ensureBackendReady();
    if (!ready) throw new Error("Backend not connected");

    const payload = {
      llm_provider: els.settingsLlmProvider?.value || "auto",
      openai_model: els.settingsOpenaiModel?.value?.trim() || "",
      chat_model: els.settingsChatModel?.value?.trim() || "",
    };
    const openaiKey = els.settingsOpenaiKey?.value?.trim() || "";
    const anthropicKey = els.settingsAnthropicKey?.value?.trim() || "";
    if (openaiKey) payload.openai_api_key = openaiKey;
    if (anthropicKey) payload.anthropic_api_key = anthropicKey;

    const res = await fetch(`${BACKEND}/settings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Save failed");
    applySettingsToForm(data.settings);
    if (els.settingsSaveStatus) els.settingsSaveStatus.textContent = "Saved — changes apply immediately";
    setStatus("Settings saved");
  } catch (err) {
    if (els.settingsSaveStatus) els.settingsSaveStatus.textContent = err.message;
    setStatus(err.message, true);
  } finally {
    els.settingsSaveBtn.disabled = false;
  }
}

function resetExtensionClientState() {
  state.savedPageId = null;
  state.history = [];
  state.quotes = [];
  state.savedPages = [];
  state.selectedSavedId = null;
  state.lifeEvents = [];
  state.bucketLeaves = [];
  renderChatHistory([]);
  markPageSaved(false);
  renderPageQuotes();
  if (els.lifeSummary) els.lifeSummary.innerHTML = "";
  if (els.lifeEvents) {
    els.lifeEvents.innerHTML =
      '<p class="muted empty-hint">Captured events will appear here for bucket review.</p>';
  }
}

function appendMessage(role, text) {
  removeChatEmptyHint();
  const node = document.createElement("div");
  node.className = `message ${role}`;
  if (role === "assistant") {
    node.classList.add("markdown-body");
    node.innerHTML = renderMarkdown(text);
  } else {
    node.textContent = text;
  }
  els.messages.appendChild(node);
  els.messages.scrollTop = els.messages.scrollHeight;
  return node;
}

function removeChatEmptyHint() {
  const hint = document.getElementById("chat-empty-hint");
  if (hint) hint.remove();
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

async function addCurrentPageToWiki() {
  const ready = await ensureBackendReady();
  if (!ready) {
    setStatus("Backend not connected", true);
    return;
  }
  if (!state.page) {
    setStatus("No page loaded", true);
    return;
  }
  setStatus("Adding to wiki…");
  try {
    if (!state.savedPageId) {
      await saveCurrentPage();
    }
    const pageId = state.savedPageId;
    if (!pageId) throw new Error("Save the page first");
    const res = await fetch(`${BACKEND}/wiki/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ page_id: pageId }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Wiki ingest failed");
    setStatus("Added to wiki — run Compile to update articles");
  } catch (err) {
    setStatus(err.message, true);
  }
}

async function addSelectedPageToWiki() {
  if (!state.selectedSavedId) return;
  const ready = await ensureBackendReady();
  if (!ready) {
    setStatus("Backend not connected", true);
    return;
  }
  setStatus("Adding to wiki…");
  try {
    const res = await fetch(`${BACKEND}/wiki/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ page_id: state.selectedSavedId }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Wiki ingest failed");
    setStatus("Added to wiki");
  } catch (err) {
    setStatus(err.message, true);
  }
}

async function loadWikiView() {
  if (!els.wikiArticles) return;
  els.wikiArticles.innerHTML = "";
  try {
    const [statusRes, articlesRes] = await Promise.all([
      fetch(`${BACKEND}/wiki/status`),
      fetch(`${BACKEND}/wiki/articles`),
    ]);
    const status = await statusRes.json();
    const articlesData = await articlesRes.json();
    if (!statusRes.ok) throw new Error(status.error || "Could not load wiki status");
    if (els.wikiStatus) {
      els.wikiStatus.textContent = `${status.raw_count} raw · ${status.article_count} articles · ${status.uncompiled_count} pending compile`;
    }
    const articles = articlesData.articles || [];
    if (els.wikiEmpty) els.wikiEmpty.hidden = articles.length > 0;
    for (const article of articles.slice(0, 12)) {
      const card = document.createElement("button");
      card.type = "button";
      card.className = "wiki-card";
      card.innerHTML = `<strong>${escapeHtml(article.title)}</strong><span class="muted">${escapeHtml(article.excerpt || "")}</span>`;
      card.addEventListener("click", () => {
        window.open(`${BACKEND}/app/#article-${encodeURIComponent(article.slug)}`, "_blank");
      });
      els.wikiArticles.appendChild(card);
    }
  } catch (err) {
    if (els.wikiStatus) els.wikiStatus.textContent = err.message;
  }
}

async function askWikiQuestion() {
  const question = els.wikiAskInput?.value.trim();
  if (!question || !els.wikiAskBtn) return;
  const ready = await ensureBackendReady();
  if (!ready) {
    setStatus("Backend not connected", true);
    return;
  }
  els.wikiAskBtn.disabled = true;
  els.wikiAskBtn.textContent = "…";
  if (els.wikiAskReply) {
    els.wikiAskReply.hidden = false;
    els.wikiAskReply.textContent = "Loading…";
  }
  try {
    const res = await fetch(`${BACKEND}/wiki/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Ask failed");
    if (els.wikiAskReply) {
      els.wikiAskReply.classList.add("markdown-body");
      els.wikiAskReply.innerHTML = renderMarkdown(data.reply || "");
    }
    if (data.sources?.length) {
      setStatus(`Sources: ${data.sources.join(", ")}`);
    }
  } catch (err) {
    if (els.wikiAskReply) els.wikiAskReply.textContent = err.message;
    setStatus(err.message, true);
  } finally {
    els.wikiAskBtn.disabled = false;
    els.wikiAskBtn.textContent = "Ask";
  }
}

async function compileWiki() {
  if (!els.wikiCompileBtn) return;
  els.wikiCompileBtn.disabled = true;
  els.wikiCompileBtn.textContent = "Compiling…";
  try {
    const ready = await ensureBackendReady();
    if (!ready) throw new Error("Backend not connected");
    const res = await fetch(`${BACKEND}/wiki/compile`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ max_sources: 3 }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Compile failed");
    setStatus(data.message || "Wiki compiled");
    await loadWikiView();
  } catch (err) {
    setStatus(err.message, true);
  } finally {
    els.wikiCompileBtn.disabled = false;
    els.wikiCompileBtn.textContent = "Compile";
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
