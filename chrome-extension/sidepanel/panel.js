const BACKEND = "http://127.0.0.1:8765";
const backendReadyCache = { ok: false, checkedAt: 0, ttlMs: 5000 };

const state = {
  page: null,
  savedPageId: null,
  selection: "",
  lastSavedSelection: "",
  history: [],
  quotes: [],
  dateAdded: "",
  tags: [],
  lastNoteQuoteBodies: [],
  busy: false,
  saving: false,
  view: "chat",
  pageTab: "details",
  savedPages: [],
  selectedSavedId: null,
  savedDetailPage: null,
  bucketLeaves: [],
  bucketTree: {},
  lifeCategory: "all",
  lifeSummary: [],
  lifeEvents: [],
  wikiSelectedSlug: null,
  wikiArticles: [],
  exploreCache: {},
};

const els = {
  title: document.getElementById("page-title"),
  site: document.getElementById("page-site"),
  status: document.getElementById("status"),
  messages: document.getElementById("messages"),
  form: document.getElementById("ask-form"),
  question: document.getElementById("question"),
  askBtn: document.getElementById("ask-btn"),
  savePageBtn: document.getElementById("save-page-btn"),
  notesShell: document.querySelector(".notes-shell"),
  notesBold: document.getElementById("notes-bold"),
  notesItalic: document.getElementById("notes-italic"),
  clearNotesBtn: document.getElementById("clear-notes-btn"),
  exploreBtn: document.getElementById("explore-btn"),
  nav: document.getElementById("nav"),
  savedList: document.getElementById("saved-list"),
  savedDetail: document.getElementById("saved-detail"),
  savedBack: document.getElementById("saved-back"),
  savedDetailTitle: document.getElementById("saved-detail-title"),
  savedDetailUrl: document.getElementById("saved-detail-url"),
  savedSummary: document.getElementById("saved-summary"),
  savedNotes: document.getElementById("saved-notes"),
  savedCopyJsonBtn: document.getElementById("saved-copy-json"),
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
  metaCategory: document.getElementById("meta-category"),
  metaMedium: document.getElementById("meta-medium"),
  metaTldr: document.getElementById("meta-tldr"),
  metaThoughts: document.getElementById("meta-thoughts"),
  metaNotes: document.getElementById("meta-notes"),
  metaTagEditor: document.getElementById("meta-tag-editor"),
  metaTagChips: document.getElementById("meta-tag-chips"),
  metaTagInput: document.getElementById("meta-tag-input"),
  metaCustomFields: document.getElementById("meta-custom-fields"),
  metaAddField: document.getElementById("meta-add-field"),
  copyExportJsonBtn: document.getElementById("copy-export-json"),
  copyNotesJsonBtn: document.getElementById("copy-notes-json"),
  exportJsonPreview: document.getElementById("export-json-preview"),
  header: document.querySelector(".header"),
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
  wikiStatsRow: document.getElementById("wiki-stats-row"),
  wikiPendingBanner: document.getElementById("wiki-pending-banner"),
  wikiPendingText: document.getElementById("wiki-pending-text"),
  wikiListPanel: document.getElementById("wiki-list-panel"),
  wikiReader: document.getElementById("wiki-reader"),
  wikiReaderBack: document.getElementById("wiki-reader-back"),
  wikiReaderOpen: document.getElementById("wiki-reader-open"),
  wikiReaderTitle: document.getElementById("wiki-reader-title"),
  wikiReaderBody: document.getElementById("wiki-reader-body"),
  wikiArticles: document.getElementById("wiki-articles"),
  wikiEmpty: document.getElementById("wiki-empty"),
  wikiCompileBtn: document.getElementById("wiki-compile-btn"),
  wikiRefreshBtn: document.getElementById("wiki-refresh-btn"),
  wikiAskInput: document.getElementById("wiki-ask-input"),
  wikiAskBtn: document.getElementById("wiki-ask-btn"),
  wikiAskReply: document.getElementById("wiki-ask-reply"),
  wikiAskSources: document.getElementById("wiki-ask-sources"),
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

let panelUnloading = false;
window.addEventListener("pagehide", () => {
  panelUnloading = true;
  flushPageDraftNow();
});
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "hidden") {
    flushPageDraftNow();
  }
});

function connectSidePanelPort() {
  if (panelUnloading) return;
  try {
    const port = chrome.runtime.connect({ name: "sidepanel" });
    port.onDisconnect.addListener(() => {
      if (panelUnloading || document.visibilityState === "hidden") return;
      window.setTimeout(connectSidePanelPort, 200);
    });
  } catch {
    if (panelUnloading) return;
    window.setTimeout(connectSidePanelPort, 500);
  }
}

async function init() {
  try {
    connectSidePanelPort();
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
    // Quote inserts come only from QUOTE_SAVED — do not also react to
    // quoteSavedAt or the same highlight is appended twice (race).
    if (area === "session" && changes.activeTabUrl) {
      const nextUrl = changes.activeTabUrl.newValue || "";
      if (nextUrl && nextUrl !== state.page?.url) {
        refreshPage();
      }
    }
  });
  chrome.storage.session.get(["latestSelection", "activeTabUrl", "openToNotes"], (data) => {
    updateSelection(data.latestSelection || "");
    if (data.activeTabUrl && data.activeTabUrl !== state.page?.url) {
      refreshPage();
    }
    if (data.openToNotes) {
      switchView("chat");
      switchPageTab("notes");
      chrome.storage.session.remove("openToNotes");
    }
  });
  chrome.runtime.onMessage.addListener((message) => {
    if (message?.type === "QUOTE_SAVED") {
      void handleExternalQuoteSaved(message.quote);
    }
    if (message?.type === "QUOTE_SAVE_FAILED") {
      setStatus(message.error || "Could not save quote", true);
    }
    if (message?.type === "OPEN_NOTES_TAB") {
      switchView("chat");
      switchPageTab("notes");
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
    const action = state.savedPageId ? unsaveCurrentPage() : saveCurrentPage();
    action.catch((err) => {
      console.error(err);
      setStatus(err.message || (state.savedPageId ? "Remove failed" : "Save failed"), true);
    });
  });
  on(els.notesBold, "mousedown", (event) => event.preventDefault());
  on(els.notesItalic, "mousedown", (event) => event.preventDefault());
  on(els.notesBold, "click", () => applyNotesFormat("bold"));
  on(els.notesItalic, "click", () => applyNotesFormat("italic"));
  on(els.clearNotesBtn, "click", clearAllNotes);
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
  on(els.wikiReaderBack, "click", closeWikiReader);
  on(els.addToWikiBtn, "click", addSelectedPageToWiki);
  on(els.addPageToWikiBtn, "click", addCurrentPageToWiki);
  on(els.clearLibraryBtn, "click", clearSavedLibrary);
  on(els.clearAllBtn, "click", clearAllData);
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
    refreshExportJsonPreview();
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
  els.metaCategory?.addEventListener("change", () => {
    schedulePageDraftSave();
    refreshExportJsonPreview();
    savePageDetails();
  });
  els.metaMedium?.addEventListener("change", () => {
    schedulePageDraftSave();
    refreshExportJsonPreview();
    savePageDetails();
  });
  els.metaAuthor?.addEventListener("input", () => {
    schedulePageDraftSave();
    refreshExportJsonPreview();
  });
  els.metaDate?.addEventListener("input", schedulePageDraftSave);
  els.metaTldr?.addEventListener("input", () => {
    schedulePageDraftSave();
    refreshExportJsonPreview();
  });
  els.metaThoughts?.addEventListener("input", () => {
    schedulePageDraftSave();
    refreshExportJsonPreview();
  });
  els.metaNotes?.addEventListener("input", () => {
    if (notesStructuralUpdate) return;
    stabilizeNotesQuotes();
    repairBrokenNoteQuotes();
    decorateNoteQuoteControls();
    updateNotesEmptyState();
    pruneQuotesRemovedFromNotes();
    schedulePageDraftSave();
    refreshExportJsonPreview();
    void syncHighlightsToPage();
  });
  els.metaNotes?.addEventListener("keydown", handleNotesKeydown);
  els.metaNotes?.addEventListener("mousedown", handleNotesMouseDown);
  els.metaNotes?.addEventListener("click", handleNotesQuoteClick);
  els.metaNotes?.addEventListener("paste", handleNotesPaste);
  els.metaTldr?.addEventListener("blur", savePageDetails);
  els.metaThoughts?.addEventListener("blur", savePageDetails);
  els.metaNotes?.addEventListener("blur", savePageDetails);
  els.metaTagInput?.addEventListener("keydown", handleTagInputKeydown);
  els.metaTagInput?.addEventListener("blur", () => {
    commitTagFromInput();
    savePageDetails();
  });
  els.metaTagChips?.addEventListener("click", (event) => {
    const removeBtn = event.target.closest("[data-remove-tag]");
    if (!removeBtn) return;
    event.preventDefault();
    removeTag(removeBtn.dataset.removeTag);
  });
  els.metaTagEditor?.addEventListener("click", (event) => {
    if (event.target.closest("button, input")) return;
    els.metaTagInput?.focus();
  });
  on(els.copyExportJsonBtn, "click", copyBookshelfJson);
  on(els.copyNotesJsonBtn, "click", copyBookshelfJson);
  on(els.savedCopyJsonBtn, "click", copySavedBookshelfJson);
  els.metaAddField?.addEventListener("click", () => {
    const wrap = document.getElementById("details-custom");
    if (wrap) wrap.open = true;
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

  on(els.nav, "click", (event) => {
    const button = event.target.closest(".nav-btn");
    if (!button) return;
    switchView(button.dataset.view);
  });

  on(document.getElementById("brand-home"), "click", () => switchView("chat"));

  on(els.pageSubnav, "click", (event) => {
    const button = event.target.closest(".page-tab");
    if (!button) return;
    switchPageTab(button.dataset.pageTab);
  });
  on(els.messages, "click", (event) => {
    const card = event.target.closest(".explore-chat-card");
    const url = card?.dataset?.url;
    if (!url) return;
    event.preventDefault();
    chrome.tabs.create({ url });
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
  if (tab === "notes") {
    els.metaNotes?.focus();
  }
  if (tab === "chat") {
    els.question.focus();
  }
}

function switchView(view) {
  // Life and Wiki are archived from the nav; keep their views in the DOM for a later revival.
  if (view === "life" || view === "wiki") return;
  state.view = view;
  document.querySelectorAll(".nav-btn").forEach((el) => {
    el.classList.toggle("active", el.dataset.view === view);
  });
  document.querySelectorAll(".view").forEach((el) => {
    el.classList.toggle("active", el.id === `view-${view}`);
  });
  els.header?.classList.toggle("page-context-hidden", view !== "chat");
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

function pageUrlsMatch(left, right) {
  if (typeof ContextPageDrafts !== "undefined" && ContextPageDrafts.pageUrlsMatch) {
    return ContextPageDrafts.pageUrlsMatch(left, right);
  }
  const canon = (url) =>
    String(url || "")
      .trim()
      .replace(/#.*$/, "")
      .replace(/\/+$/, "");
  const a = canon(left);
  const b = canon(right);
  return Boolean(a && b && a === b);
}

function formatUserError(message) {
  const text = String(message || "");
  if (/rate.?limit|429/i.test(text)) {
    const match = text.match(/try again in (\d+)s/i);
    const wait = match ? `${match[1]}s` : "a few seconds";
    return `OpenAI rate limit — wait ${wait} and try again, or switch to Ollama in Settings.`;
  }
  return text;
}

function updateSelection(selected) {
  const normalized = normalizeSelection(selected);
  state.selection = normalized;
  if (state.page) state.page.selected_text = normalized;
}

async function refreshSelectionFromPage() {
  const page = await getActivePageContext();
  if (page?.selected_text !== undefined) {
    updateSelection(page.selected_text);
  }
}

let lastExternalQuoteKey = "";
let lastExternalQuoteAt = 0;
let externalQuoteHandling = null;

async function handleExternalQuoteSaved(quoteFromMessage) {
  const run = (async () => {
    let quote = quoteFromMessage;
    if (!quote?.text) {
      const data = await chrome.storage.session.get(["lastSavedQuote"]);
      quote = data.lastSavedQuote;
    }
    const text = ContextNotes.normalizeSelection(quote?.text);
    if (!text) return;
    const key = `${String(quote?.id || "").trim()}::${text}`;
    const now = Date.now();
    if (key === lastExternalQuoteKey && now - lastExternalQuoteAt < 2500) {
      return;
    }
    lastExternalQuoteKey = key;
    lastExternalQuoteAt = now;

    await loadPageQuotes();
    if (quote?.page_url && state.page?.url && !pageUrlsMatch(quote.page_url, state.page.url)) {
      await syncHighlightsToPage();
      return;
    }
    addQuoteToNotes(quote);
    rememberNoteQuoteBodies();
    await flushPageDraft(state.page?.url);
    await syncHighlightsToPage();
    switchPageTab("notes");
    els.metaNotes?.focus();
  })();

  externalQuoteHandling = run;
  try {
    await run;
  } finally {
    if (externalQuoteHandling === run) externalQuoteHandling = null;
  }
}

function addQuoteToNotes(quote, { switchTab = true } = {}) {
  const text = ContextNotes.normalizeSelection(quote?.text);
  if (!text) return false;
  if (ContextNotes.notesContainsQuote(getNotesMarkdown(), text)) return false;
  insertQuoteHtmlAtCaret(quote);
  rememberNoteQuoteBodies();
  if (switchTab) switchPageTab("notes");
  void savePageDetails({ quiet: true });
  setStatus("Quote added to notes");
  return true;
}

function insertQuoteHtmlAtCaret(quote) {
  const html = ContextNotes.markdownToHtml(ContextNotes.quoteNotesSnippet(quote));
  const wrapper = document.createElement("div");
  wrapper.innerHTML = html;
  const nodes = Array.from(wrapper.childNodes);
  if (!nodes.length || !els.metaNotes) {
    setNotesMarkdown(ContextNotes.appendQuoteToNotes(getNotesMarkdown(), quote));
    return;
  }

  const quoteEl = notesCaretQuote();
  if (quoteEl) {
    let last = quoteEl;
    nodes.forEach((node) => {
      last.after(node);
      last = node;
    });
  } else {
    const range = notesCaretRange();
    if (range && els.metaNotes.contains(range.commonAncestorContainer)) {
      range.deleteContents();
      const fragment = document.createDocumentFragment();
      nodes.forEach((node) => fragment.appendChild(node));
      range.insertNode(fragment);
    } else {
      nodes.forEach((node) => els.metaNotes.appendChild(node));
    }
  }

  const paragraph = ensureNotesWritableParagraph();
  placeNotesCaret(paragraph, true);
  if (els.metaNotes) els.metaNotes.scrollTop = els.metaNotes.scrollHeight;
  stabilizeNotesQuotes();
  decorateNoteQuoteControls();
  updateNotesEmptyState();
  refreshExportJsonPreview();
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
  return {
    author: "",
    date: "",
    category: "",
    medium: "",
    tldr: "",
    thoughts: "",
    notes: "",
    dateAdded: "",
    tags: [],
    custom: [],
  };
}

function normalizeMetadata(raw) {
  const meta = emptyMetadata();
  if (!raw) return meta;
  meta.author = String(raw.author || "").trim();
  meta.date = String(raw.date || "").trim();
  meta.category = String(raw.category || "").trim();
  meta.medium = String(raw.medium || "").trim();
  meta.tldr = String(raw.tldr || "").trim();
  meta.thoughts = String(raw.thoughts || "").trim();
  meta.notes = String(raw.notes || "").trim();
  meta.dateAdded = String(raw.dateAdded || raw.date_added || "").trim();
  meta.tags = ContextBookshelf.normalizeTags(raw.tags);
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

function mergeMetadata(preferred, fallback, options = {}) {
  const base = normalizeMetadata(fallback);
  const chosen = normalizeMetadata(preferred);
  const preferredAt = Number(options.preferredUpdatedAt || 0);
  const fallbackAt = Number(options.fallbackUpdatedAt || 0);
  // Newer draft wins for notes even when empty (intentional clear).
  let notes = chosen.notes || base.notes;
  if (preferred && Object.prototype.hasOwnProperty.call(preferred, "notes")) {
    if (preferredAt >= fallbackAt) notes = chosen.notes;
    else notes = base.notes || chosen.notes;
  }
  return {
    author: chosen.author || base.author,
    date: chosen.date || base.date,
    category: chosen.category || base.category,
    medium: chosen.medium || base.medium,
    tldr: chosen.tldr || base.tldr,
    thoughts: chosen.thoughts || base.thoughts,
    notes,
    dateAdded: chosen.dateAdded || base.dateAdded,
    tags: chosen.tags.length ? chosen.tags : base.tags,
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
    category: els.metaCategory?.value || "",
    medium: els.metaMedium?.value || "",
    tldr: els.metaTldr?.value || "",
    thoughts: els.metaThoughts?.value || "",
    notes: getNotesMarkdown(),
    dateAdded: state.dateAdded || "",
    tags: state.tags,
    custom,
  });
}

function setSelectValue(select, value) {
  if (!select) return;
  const next = String(value || "");
  if (next && !Array.from(select.options).some((option) => option.value === next)) {
    const option = document.createElement("option");
    option.value = next;
    option.textContent = next;
    select.appendChild(option);
  }
  select.value = next;
}

function applyMetadataToForm(metadata) {
  const meta = normalizeMetadata(metadata);
  if (els.metaAuthor) els.metaAuthor.value = meta.author;
  if (els.metaDate) els.metaDate.value = meta.date;
  setSelectValue(els.metaCategory, meta.category);
  setSelectValue(els.metaMedium, meta.medium || suggestMedium(state.page));
  if (els.metaTldr) els.metaTldr.value = meta.tldr;
  if (els.metaThoughts) els.metaThoughts.value = meta.thoughts;
  setNotesMarkdown(meta.notes);
  state.dateAdded = meta.dateAdded;
  state.tags = meta.tags.slice();
  renderTagChips();
  renderCustomMetaFields(meta.custom);
  refreshExportJsonPreview();
}

function renderTagChips() {
  if (!els.metaTagChips) return;
  els.metaTagChips.innerHTML = "";
  for (const tag of state.tags) {
    const chip = document.createElement("span");
    chip.className = "tag-chip";
    chip.innerHTML = `
      <span>${escapeHtml(tag)}</span>
      <button type="button" class="tag-chip-remove" data-remove-tag="${escapeAttr(tag)}" title="Remove tag" aria-label="Remove ${escapeAttr(tag)}">×</button>
    `;
    els.metaTagChips.appendChild(chip);
  }
}

function addTag(raw) {
  const tag = String(raw || "").trim().replace(/^,|,$/g, "");
  if (!tag) return false;
  if (state.tags.some((existing) => existing.toLowerCase() === tag.toLowerCase())) {
    if (els.metaTagInput) els.metaTagInput.value = "";
    return false;
  }
  state.tags.push(tag);
  if (els.metaTagInput) els.metaTagInput.value = "";
  renderTagChips();
  schedulePageDraftSave();
  refreshExportJsonPreview();
  return true;
}

function removeTag(tag) {
  const target = String(tag || "").trim().toLowerCase();
  state.tags = state.tags.filter((item) => item.toLowerCase() !== target);
  renderTagChips();
  schedulePageDraftSave();
  refreshExportJsonPreview();
  savePageDetails();
}

function commitTagFromInput() {
  const value = els.metaTagInput?.value || "";
  if (!value.trim()) return;
  addTag(value);
}

function handleTagInputKeydown(event) {
  if (event.key === "Enter" || event.key === ",") {
    event.preventDefault();
    commitTagFromInput();
    return;
  }
  if (event.key === "Backspace" && !(els.metaTagInput?.value || "") && state.tags.length) {
    event.preventDefault();
    removeTag(state.tags[state.tags.length - 1]);
  }
}

function suggestMedium(page) {
  const url = String(page?.url || "").toLowerCase();
  const type = String(page?.page_type || "").toLowerCase();
  if (/\byoutube\.com|\byoutu\.be|\bvimeo\.com|\bted\.com\b/.test(url) || type === "video") {
    return "video";
  }
  if (/\barxiv\.org\b|\bpubmed\b|\bnih\.gov\b/.test(url) || type === "research_paper") {
    return "research paper";
  }
  if (/\bgoodreads\.com\b/.test(url) || type === "book") {
    return "book";
  }
  return "essay";
}

function getNotesMarkdown() {
  return ContextNotes.htmlToMarkdown(els.metaNotes);
}

/** Ignore contenteditable "input" while we surgically change notes DOM. */
let notesStructuralUpdate = false;

function withNotesStructuralUpdate(fn) {
  notesStructuralUpdate = true;
  try {
    return fn();
  } finally {
    window.setTimeout(() => {
      notesStructuralUpdate = false;
    }, 0);
  }
}

function setNotesMarkdown(value) {
  if (!els.metaNotes) return;
  withNotesStructuralUpdate(() => {
    els.metaNotes.innerHTML = ContextNotes.markdownToHtml(value);
    stabilizeNotesQuotes();
    decorateNoteQuoteControls();
    rememberNoteQuoteBodies();
    updateNotesEmptyState();
    refreshExportJsonPreview();
  });
}

function decorateNoteQuoteControls() {
  if (!els.metaNotes) return;
  els.metaNotes.querySelectorAll("blockquote").forEach((quoteEl) => {
    if (quoteEl.querySelector("[data-delete-quote]")) return;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "note-quote-delete";
    btn.dataset.deleteQuote = "1";
    btn.title = "Remove quote";
    btn.setAttribute("aria-label", "Remove quote");
    btn.contentEditable = "false";
    btn.tabIndex = -1;
    btn.textContent = "×";
    quoteEl.appendChild(btn);
  });
}

function quoteTextFromBlockquote(quoteEl) {
  if (!quoteEl) return "";
  const parts = Array.from(quoteEl.querySelectorAll("p")).map((p) => p.innerText || "");
  if (parts.length) return ContextNotes.normalizeSelection(parts.join("\n"));
  const clone = quoteEl.cloneNode(true);
  clone.querySelectorAll("button, [data-delete-quote]").forEach((el) => el.remove());
  return ContextNotes.normalizeSelection(clone.innerText || "");
}

/**
 * Remove one quote from the editor by deleting its DOM nodes only.
 * Avoids markdown round-trip, which can wipe the whole document if serialization
 * races with contenteditable during the × click.
 */
function removeQuoteElementsFromEditor(quoteEl, note = "") {
  if (!quoteEl || !els.metaNotes?.contains(quoteEl)) return;

  const victims = new Set([quoteEl]);
  let el = quoteEl.nextElementSibling;
  while (el && isBlankParagraph(el)) {
    victims.add(el);
    el = el.nextElementSibling;
  }

  const noteText = ContextNotes.normalizeSelection(note);
  if (noteText && el && el.tagName.toLowerCase() === "p") {
    const paraText = ContextNotes.normalizeSelection(el.innerText || "");
    if (paraText === noteText) {
      victims.add(el);
    }
  }

  for (const node of victims) node.remove();
  ensureNotesWritableParagraph();
}

function removeNoteQuoteBlock(quoteEl) {
  if (!quoteEl || !els.metaNotes?.contains(quoteEl)) return;

  const text = quoteTextFromBlockquote(quoteEl);
  const matchKey = ContextNotes.quoteMatchKey(text);
  const match = (state.quotes || []).find(
    (quote) => ContextNotes.quoteMatchKey(quote.text) === matchKey
  );

  withNotesStructuralUpdate(() => {
    // Prefer library note when present; otherwise keep neighboring freeform paragraphs.
    removeQuoteElementsFromEditor(quoteEl, match?.note || "");
    stabilizeNotesQuotes();
    decorateNoteQuoteControls();
    rememberNoteQuoteBodies();
    updateNotesEmptyState();
    refreshExportJsonPreview();
  });

  // Drop the library record (if any) and always repaint so the page mark disappears.
  if (match) {
    void deleteQuoteRecord(match, { silent: true });
  } else {
    if (matchKey) {
      state.quotes = (state.quotes || []).filter(
        (item) => ContextNotes.quoteMatchKey(item.text) !== matchKey
      );
    }
    void syncHighlightsToPage();
  }
  schedulePageDraftSave();
  void savePageDetails({ quiet: true });
  setStatus("Quote removed");
}

function clearAllNotes() {
  if (!els.metaNotes || notesDocumentIsEmpty()) return;
  if (!window.confirm("Clear all notes for this page?")) return;
  const bodies = ContextNotes.markdownQuoteBodies(getNotesMarkdown()).map((body) =>
    ContextNotes.quoteMatchKey(body)
  );
  const toDelete = (state.quotes || []).filter((quote) =>
    bodies.includes(ContextNotes.quoteMatchKey(quote.text))
  );
  setNotesMarkdown("");
  for (const quote of toDelete) {
    void deleteQuoteRecord(quote, { silent: true });
  }
  state.quotes = (state.quotes || []).filter(
    (quote) => !bodies.includes(ContextNotes.quoteMatchKey(quote.text))
  );
  void syncHighlightsToPage();
  schedulePageDraftSave();
  void savePageDetails({ quiet: true });
  setStatus("Notes cleared");
}

function notesDocumentIsEmpty() {
  const text = (els.metaNotes?.innerText || "").replace(/\u00a0/g, " ").trim();
  return !text;
}

function updateNotesEmptyState() {
  els.metaNotes?.classList.toggle("is-empty", notesDocumentIsEmpty());
}

function rememberNoteQuoteBodies() {
  state.lastNoteQuoteBodies = ContextNotes.markdownQuoteBodies(getNotesMarkdown()).map(
    (body) => ContextNotes.normalizeSelection(body)
  );
}

function pruneQuotesRemovedFromNotes() {
  const currentBodies = ContextNotes.markdownQuoteBodies(getNotesMarkdown());
  const currentKeys = new Set(
    currentBodies.map((body) => ContextNotes.quoteMatchKey(body)).filter(Boolean)
  );
  // Treat bold/italic/punctuation-only edits as the same quote, not a deletion.
  const removed = state.lastNoteQuoteBodies.filter((body) => {
    const key = ContextNotes.quoteMatchKey(body);
    return key && !currentKeys.has(key);
  });
  state.lastNoteQuoteBodies = currentBodies.map((body) =>
    ContextNotes.normalizeSelection(body)
  );
  let changed = false;
  for (const text of removed) {
    // If the quote text is still visible in the editor (e.g. last blockquote
    // temporarily unwrapped), keep the library quote and page highlight.
    if (notesEditorStillHasQuote(text)) continue;
    const quote = (state.quotes || []).find(
      (item) => ContextNotes.quoteMatchKey(item.text) === ContextNotes.quoteMatchKey(text)
    );
    if (!quote) {
      changed = true;
      continue;
    }
    // Drop locally first so a concurrent repaint cannot revive a deleted highlight.
    state.quotes = state.quotes.filter((item) => item !== quote);
    changed = true;
    if (quote?.id && !String(quote.id).startsWith("local-")) {
      void deleteQuoteRecord(quote, { silent: true, skipStateFilter: true });
    }
  }
  if (changed) void syncHighlightsToPage();
}

function notesEditorStillHasQuote(text) {
  const key = ContextNotes.quoteMatchKey(text);
  if (!key || !els.metaNotes) return false;
  for (const quoteEl of els.metaNotes.querySelectorAll("blockquote")) {
    if (ContextNotes.quoteMatchKey(quoteTextFromBlockquote(quoteEl)) === key) return true;
  }
  for (const paragraph of els.metaNotes.querySelectorAll(":scope > p")) {
    if (ContextNotes.quoteMatchKey(paragraph.innerText || "") === key) return true;
  }
  return false;
}

function quoteContentParagraphs(quoteEl) {
  if (!quoteEl) return [];
  return Array.from(quoteEl.children).filter((el) => {
    if (el.tagName.toLowerCase() !== "p") return false;
    if (el.hasAttribute("data-delete-quote")) return false;
    return true;
  });
}

function stabilizeNotesQuotes() {
  if (!els.metaNotes) return;
  els.metaNotes.querySelectorAll("blockquote").forEach((quoteEl) => {
    // Contenteditable often leaves blank trailing paragraphs inside the last quote.
    let guard = 0;
    while (guard < 8) {
      guard += 1;
      const paragraphs = quoteContentParagraphs(quoteEl);
      const last = paragraphs[paragraphs.length - 1];
      if (!last || !isBlankParagraph(last)) break;
      quoteEl.after(last);
    }
    const btn = quoteEl.querySelector("[data-delete-quote]");
    if (btn) quoteEl.appendChild(btn);
  });
  ensureNotesWritableParagraph();
}

function repairBrokenNoteQuotes() {
  if (!els.metaNotes) return;
  const wrappedKeys = new Set(
    Array.from(els.metaNotes.querySelectorAll("blockquote")).map((quoteEl) =>
      ContextNotes.quoteMatchKey(quoteTextFromBlockquote(quoteEl))
    ).filter(Boolean)
  );
  for (const quote of state.quotes || []) {
    const key = ContextNotes.quoteMatchKey(quote?.text);
    if (!key || wrappedKeys.has(key)) continue;
    const match = Array.from(els.metaNotes.querySelectorAll(":scope > p")).find(
      (paragraph) => ContextNotes.quoteMatchKey(paragraph.innerText || "") === key
    );
    if (!match) continue;
    const blockquote = document.createElement("blockquote");
    blockquote.className = "custom-quote";
    match.replaceWith(blockquote);
    blockquote.appendChild(match);
    wrappedKeys.add(key);
  }
}

function handleNotesMouseDown(event) {
  const deleteBtn = event.target.closest?.("[data-delete-quote]");
  if (deleteBtn && els.metaNotes?.contains(deleteBtn)) {
    // Stop contenteditable from treating × as an edit (can nuke the document).
    event.preventDefault();
    event.stopPropagation();
    return;
  }
  handleNotesBlankClick(event);
}

function handleNotesQuoteClick(event) {
  const deleteBtn = event.target.closest("[data-delete-quote]");
  if (deleteBtn && els.metaNotes?.contains(deleteBtn)) {
    event.preventDefault();
    event.stopPropagation();
    removeNoteQuoteBlock(deleteBtn.closest("blockquote"));
    return;
  }
  const quoteEl = event.target.closest("blockquote");
  if (!quoteEl || !els.metaNotes?.contains(quoteEl)) return;
  if (window.getSelection()?.toString()) return;
  const text = quoteTextFromBlockquote(quoteEl);
  if (!text) return;
  const match = (state.quotes || []).find(
    (quote) => ContextNotes.quoteMatchKey(quote.text) === ContextNotes.quoteMatchKey(text)
  );
  void revealQuoteOnPage(match || { text });
}

function isBlankParagraph(el) {
  return Boolean(el) && !(el.innerText || "").replace(/\u00a0/g, " ").trim();
}

function ensureNotesWritableParagraph() {
  const editor = els.metaNotes;
  if (!editor) return null;
  const last = editor.lastElementChild;
  if (
    last
    && last.matches("p")
    && last.parentElement === editor
    && isBlankParagraph(last)
  ) {
    return last;
  }
  const paragraph = document.createElement("p");
  paragraph.appendChild(document.createElement("br"));
  editor.appendChild(paragraph);
  return paragraph;
}

function placeNotesCaret(node, atEnd = true) {
  if (!node) return;
  const range = document.createRange();
  range.selectNodeContents(node);
  range.collapse(!atEnd);
  const selection = window.getSelection();
  selection.removeAllRanges();
  selection.addRange(range);
  els.metaNotes?.focus();
}

function handleNotesBlankClick(event) {
  if (event.target !== els.metaNotes) return;
  event.preventDefault();
  const paragraph = ensureNotesWritableParagraph();
  placeNotesCaret(paragraph, true);
}

function notesCaretRange() {
  const selection = window.getSelection();
  if (!selection?.rangeCount) return null;
  const range = selection.getRangeAt(0);
  if (!els.metaNotes?.contains(range.commonAncestorContainer)) return null;
  return range;
}

function notesCaretQuote() {
  const range = notesCaretRange();
  if (!range) return null;
  const node = range.startContainer;
  const el = node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement;
  return el?.closest("blockquote") || null;
}

function notesCaretBlock() {
  const range = notesCaretRange();
  if (!range) return null;
  const node = range.startContainer;
  const el = node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement;
  return el?.closest("p, div") || null;
}

function isNotesCaretAtEnd(node) {
  const range = notesCaretRange();
  if (!range?.collapsed || !node) return false;
  const tail = range.cloneRange();
  tail.selectNodeContents(node);
  tail.setStart(range.endContainer, range.endOffset);
  return !tail.toString().replace(/\u00a0/g, " ").trim();
}

function isNotesCaretAtEndOfQuote(quote) {
  if (!quote) return false;
  const block = notesCaretBlock();
  if (!block || !quote.contains(block) || block.tagName.toLowerCase() !== "p") return false;
  if (!isNotesCaretAtEnd(block)) return false;
  const paragraphs = quoteContentParagraphs(quote);
  return paragraphs.length > 0 && paragraphs[paragraphs.length - 1] === block;
}

function exitNotesQuote() {
  const quote = notesCaretQuote();
  if (!quote) return false;
  const block = notesCaretBlock();
  if (block && isBlankParagraph(block) && quote.contains(block) && block !== quote) {
    block.remove();
  }
  const paragraph = document.createElement("p");
  paragraph.appendChild(document.createElement("br"));
  quote.after(paragraph);
  placeNotesCaret(paragraph, true);
  stabilizeNotesQuotes();
  updateNotesEmptyState();
  schedulePageDraftSave();
  return true;
}

function applyNotesFormat(command) {
  els.metaNotes?.focus();
  document.execCommand(command, false, null);
  stabilizeNotesQuotes();
  repairBrokenNoteQuotes();
  decorateNoteQuoteControls();
  updateNotesEmptyState();
  rememberNoteQuoteBodies();
  schedulePageDraftSave();
  refreshExportJsonPreview();
  void syncHighlightsToPage();
}

function handleNotesKeydown(event) {
  if (event.key === "Enter" && !event.shiftKey && !event.metaKey && !event.ctrlKey) {
    const quote = notesCaretQuote();
    if (quote && (isBlankParagraph(notesCaretBlock()) || isNotesCaretAtEndOfQuote(quote))) {
      event.preventDefault();
      exitNotesQuote();
      return;
    }
  }
  if (!(event.metaKey || event.ctrlKey)) return;
  const key = event.key.toLowerCase();
  if (key === "b") {
    event.preventDefault();
    applyNotesFormat("bold");
  } else if (key === "i") {
    event.preventDefault();
    applyNotesFormat("italic");
  }
}

function handleNotesPaste(event) {
  event.preventDefault();
  const text = event.clipboardData?.getData("text/plain") || "";
  document.execCommand("insertText", false, text);
}

function buildBookshelfEntry(overrides = {}) {
  const meta = overrides.metadata || collectMetadataFromForm();
  // Export reads quote <blockquote>s from the Notes DOM as :::quote fences.
  // Commentary paragraphs stay plain. Notes tab editing format is unchanged.
  let notes;
  if (Object.prototype.hasOwnProperty.call(overrides, "notes")) {
    notes = overrides.notes;
  } else if (overrides.metadata) {
    notes = meta.notes;
  } else if (els.metaNotes && typeof ContextNotes.domToExportNotes === "function") {
    notes = ContextNotes.domToExportNotes(els.metaNotes);
  } else {
    notes = meta.notes;
  }
  return ContextBookshelf.buildEntry({
    title: overrides.title || getDisplayTitle(),
    url: overrides.url || state.page?.url || "",
    author: meta.author,
    dateAdded: meta.dateAdded,
    category: meta.category,
    medium: meta.medium,
    tldr: meta.tldr,
    thoughts: meta.thoughts,
    tags: meta.tags,
    notes,
  });
}

function refreshExportJsonPreview() {
  if (!els.exportJsonPreview) return;
  const text = ContextBookshelf.format(buildBookshelfEntry());
  els.exportJsonPreview.textContent = text;
}

async function copyBookshelfJson() {
  const text = ContextBookshelf.format(buildBookshelfEntry());
  refreshExportJsonPreview();
  const copied = await copyTextToClipboard(text);
  if (copied) {
    for (const button of [els.copyExportJsonBtn, els.copyNotesJsonBtn]) {
      if (!button) continue;
      const previous = button.textContent;
      button.textContent = "Copied";
      window.setTimeout(() => {
        if (button.textContent === "Copied") button.textContent = previous;
      }, 1600);
    }
    setStatus("JSON copied");
    return;
  }
  const preview = els.exportJsonPreview;
  if (preview) {
    const range = document.createRange();
    range.selectNodeContents(preview);
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
  }
  setStatus("Select the JSON and copy it", true);
}

async function copyTextToClipboard(text) {
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

function renderCustomMetaFields(custom) {
  if (!els.metaCustomFields) return;
  els.metaCustomFields.innerHTML = "";
  (custom || []).forEach((field) => addCustomMetaField(field.key, field.value));
  const wrap = document.getElementById("details-custom");
  if (wrap) wrap.open = Boolean(custom?.length);
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
    void persistPageDraft();
    if (state.savedPageId) void savePageDetails({ quiet: true });
  }, 150);
}

/** Fire-and-forget flush for pagehide/visibility (must not await). */
function flushPageDraftNow(url = state.page?.url) {
  clearTimeout(pageDraftTimer);
  pageDraftTimer = null;
  if (!url || !state.page?.url) return;
  if (!pageUrlsMatch(url, state.page.url)) return;
  const key =
    typeof ContextPageDrafts !== "undefined"
      ? ContextPageDrafts.pageDraftKey(url)
      : `pageDraft:${url}`;
  if (!key) return;
  const draft = {
    title: getDisplayTitle(),
    metadata: collectMetadataFromForm(),
    updatedAt: Date.now(),
  };
  try {
    chrome.storage.local.set({ [key]: draft });
  } catch {
    // Best-effort on unload.
  }
}

async function flushPageDraft(url = state.page?.url) {
  clearTimeout(pageDraftTimer);
  pageDraftTimer = null;
  if (!url) return;
  if (state.page?.url && pageUrlsMatch(url, state.page.url)) {
    await persistPageDraft(url);
  }
}

async function loadPageDraft(url) {
  if (!url) return null;
  if (typeof ContextPageDrafts !== "undefined") {
    return ContextPageDrafts.loadPageDraft(url);
  }
  return new Promise((resolve) => {
    chrome.storage.local.get(`pageDraft:${url}`, (data) => {
      resolve(data[`pageDraft:${url}`] || null);
    });
  });
}

async function persistPageDraft(url = state.page?.url) {
  if (!url) return;
  const draft = {
    title: getDisplayTitle(),
    metadata: collectMetadataFromForm(),
  };
  if (typeof ContextPageDrafts !== "undefined") {
    await ContextPageDrafts.savePageDraft(url, draft);
    return;
  }
  await chrome.storage.local.set({
    [`pageDraft:${url}`]: { ...draft, updatedAt: Date.now() },
  });
}

async function clearLocalPageDrafts() {
  clearTimeout(pageDraftTimer);
  pageDraftTimer = null;
  const local = await chrome.storage.local.get(null);
  const prefix =
    typeof ContextPageDrafts !== "undefined"
      ? ContextPageDrafts.DRAFT_PREFIX
      : "pageDraft:";
  const localKeys = Object.keys(local).filter(
    (key) => key.startsWith(prefix) || key.startsWith("customTitle:")
  );
  if (localKeys.length) await chrome.storage.local.remove(localKeys);

  const session = await chrome.storage.session.get(null);
  const sessionKeys = Object.keys(session).filter(
    (key) =>
      key.startsWith("explore:") ||
      key === "lastSavedQuote" ||
      key === "latestSelection" ||
      key === "quoteSavedAt"
  );
  if (sessionKeys.length) await chrome.storage.session.remove(sessionKeys);

  state.exploreCache = {};
  state.quotes = [];
  state.dateAdded = "";
  state.tags = [];
  state.lastSavedSelection = "";
  applyMetadataToForm(emptyMetadata());
  await clearAllPageHighlights();
}

async function clearAllPageHighlights() {
  try {
    const tabs = await chrome.tabs.query({});
    await Promise.all(
      tabs.map((tab) => {
        if (!tab.id) return Promise.resolve();
        return chrome.tabs.sendMessage(tab.id, { type: "CLEAR_HIGHLIGHTS" }).catch(() => {});
      })
    );
  } catch {
    // Restricted pages cannot host highlights.
  }
}

async function savePageDetails({ quiet = false } = {}) {
  if (!state.page?.url) return;
  const title = getDisplayTitle();
  const metadata = collectMetadataFromForm();
  if (!metadata.dateAdded) {
    metadata.dateAdded = ContextBookshelf.todayDateAdded();
    state.dateAdded = metadata.dateAdded;
  }
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
      if (!quiet) setStatus("Details updated");
    } catch (err) {
      setStatus(err.message, true);
    }
  }
}

async function syncHighlightsToPage() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id) return;
    await chrome.tabs.sendMessage(tab.id, {
      type: "REPAINT_HIGHLIGHTS",
      quotes: quotesForPageHighlights(),
    }).catch(() => {});
  } catch {
    // Restricted pages (e.g. chrome://) cannot host highlights.
  }
}

function quotesForPageHighlights() {
  return ContextNotes.quotesForHighlights(getNotesMarkdown(), state.quotes);
}

async function revealQuoteOnPage(quote) {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id) return;
    await chrome.tabs.sendMessage(tab.id, {
      type: "SCROLL_TO_QUOTE",
      quoteId: quote?.id || "",
      text: quote?.text || "",
    });
  } catch {
    setStatus("Could not find that quote on the page", true);
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
  // Persist the current editor before swapping pages — do not rely on debounce.
  if (previousUrl) {
    await flushPageDraft(previousUrl);
  }
  setStatus("Reading page…");
  const page = await getActivePageContext();
  if (!page) {
    setStatus("Could not read page context", true);
    return;
  }

  const isNewPage = Boolean(previousUrl && !pageUrlsMatch(previousUrl, page.url));
  state.page = page;
  if (isNewPage) {
    state.history = [];
    state.quotes = [];
    els.messages.innerHTML = "";
    removeChatEmptyHint();
    els.question.value = "";
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
  applyMetadataToForm(
    mergeMetadata(draft?.metadata, suggestedMetadata, {
      preferredUpdatedAt: Number(draft?.updatedAt || 0),
      fallbackUpdatedAt: 0,
    })
  );
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
  const draftUpdatedAt = Number(draft?.updatedAt || 0);

  try {
    const res = await fetch(`${BACKEND}/library/by-url?url=${encodeURIComponent(previousUrl)}`);
    const data = await res.json();
    if (data.page) {
      state.savedPageId = data.page.id;
      state.history = data.page.chat_history || [];
      renderChatHistory(state.history);
      markPageSaved(true);
      els.title.value = draft?.title || data.page.title || suggestedTitle;
      const libraryUpdatedAt =
        Date.parse(String(data.page.updated_at || data.page.saved_at || "")) || 0;
      // Local draft is the working store; prefer it when newer or when library has no stamp.
      const preferredIsDraft = !libraryUpdatedAt || draftUpdatedAt >= libraryUpdatedAt;
      applyMetadataToForm(
        mergeMetadata(
          preferredIsDraft ? draft?.metadata : data.page.metadata,
          preferredIsDraft ? data.page.metadata : draft?.metadata,
          {
            preferredUpdatedAt: preferredIsDraft ? draftUpdatedAt : libraryUpdatedAt,
            fallbackUpdatedAt: preferredIsDraft ? libraryUpdatedAt : draftUpdatedAt,
          }
        )
      );
      // Fill any empty detail fields from suggestions last.
      applyMetadataToForm(
        mergeMetadata(collectMetadataFromForm(), suggestedMetadata, {
          preferredUpdatedAt: Date.now(),
          fallbackUpdatedAt: 0,
        })
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
    await loadPageQuotes();
    await syncHighlightsToPage();
    const provider = await getBackendProvider();
    setStatus(provider ? `Ready (${provider})` : "Ready");
  } catch (err) {
    setStatus(err.message, true);
  }
}

async function loadPageQuotes() {
  if (!state.page?.url) {
    state.quotes = [];
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
    rememberNoteQuoteBodies();
    refreshExportJsonPreview();
  } catch (err) {
    setStatus(err.message, true);
  }
}

async function deleteQuoteRecord(quote, { silent = false, skipStateFilter = false } = {}) {
  const id = String(quote?.id || "").trim();
  if (id && !id.startsWith("local-")) {
    try {
      const res = await fetch(`${BACKEND}/library/quotes/${encodeURIComponent(id)}`, { method: "DELETE" });
      if (!res.ok && res.status !== 404) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || `Could not delete quote (${res.status})`);
      }
    } catch (err) {
      if (!silent) setStatus(err.message, true);
    }
  }
  if (!skipStateFilter) {
    state.quotes = (state.quotes || []).filter((item) => String(item.id || "").trim() !== id);
  }
  void syncHighlightsToPage();
}

function markPageSaved(saved) {
  const label = saved ? "Saved" : "+ Save";
  els.savePageBtn.textContent = label;
  els.savePageBtn.classList.toggle("primary", !saved);
  els.savePageBtn.classList.toggle("saved", saved);
  els.savePageBtn.title = saved
    ? "Click to remove from saved pages"
    : "Save this page with summary and quotes";
}

async function unsaveCurrentPage() {
  if (!state.savedPageId) return;
  const ready = await ensureBackendReady();
  if (!ready) {
    setStatus("Backend not connected — check Settings", true);
    return;
  }
  const pageId = state.savedPageId;
  setStatus("Removing saved page…");
  try {
    const res = await fetch(`${BACKEND}/library/pages/${encodeURIComponent(pageId)}`, {
      method: "DELETE",
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Remove failed");
    state.savedPageId = null;
    markPageSaved(false);
    await loadPageQuotes();
    setStatus("Removed from saved pages");
    if (state.view === "graph") renderGraph();
    if (state.view === "life") loadLifeView();
  } catch (err) {
    setStatus(err.message, true);
  }
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
  for (let i = 0; i < history.length; i += 1) {
    const turn = history[i];
    const prev = history[i - 1];
    if (turn.role === "assistant" && prev && isExploreQuestion(prev.content)) {
      const node = appendMessage("assistant", turn.content);
      const items = parseExploreItemsFromMarkdown(turn.content);
      if (items.length) {
        const intro = String(turn.content).split("### Articles to open next")[0].trim();
        node.classList.add("explore-answer");
        node.innerHTML = `${intro ? renderMarkdown(intro) : ""}${renderExploreCardsHtml(items)}`;
      }
      continue;
    }
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
  if (state.saving) return;
  const ready = await ensureBackendReady({ quiet: true });
  if (!ready) {
    setStatus("Backend not connected — check Settings", true);
    showSetupHelp();
    return;
  }
  state.saving = true;
  if (els.savePageBtn) els.savePageBtn.disabled = true;
  setStatus("Saving page…");
  try {
    // Flush local notes first so Save promotes the latest draft into the library.
    await flushPageDraft(state.page.url);
    state.page.title = getDisplayTitle();
    state.page.metadata = collectMetadataFromForm();
    if (!state.page.metadata.dateAdded) {
      state.page.metadata.dateAdded = ContextBookshelf.todayDateAdded();
      state.dateAdded = state.page.metadata.dateAdded;
    }
    const res = await fetch(`${BACKEND}/library/save-page`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ page: state.page, history: state.history }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Save failed");
    state.savedPageId = data.page.id;
    markPageSaved(true);
    await persistPageDraft(state.page.url);
    setStatus("Page saved");
    void loadPageQuotes();
  } catch (err) {
    setStatus(formatUserError(err.message), true);
  } finally {
    state.saving = false;
    if (els.savePageBtn) els.savePageBtn.disabled = false;
  }
}

async function loadExploreSuggestions() {
  if (!state.page || state.busy) return;
  const title = getDisplayTitle();
  const question = `Explore more articles related to ${title}`;

  switchPageTab("chat");
  state.busy = true;
  els.askBtn.disabled = true;
  removeChatEmptyHint();
  appendMessage("user", question);
  const assistantNode = appendMessage("assistant", "_Finding related articles…_");
  setStatus("Finding related articles…");

  try {
    const items = await fetchExploreItems();
    if (!items.length) {
      assistantNode.innerHTML = renderMarkdown(
        "I couldn't find related links right now. Try again in a moment."
      );
      setStatus("No suggestions", true);
      return;
    }
    const intro = `Here are related articles you might want to open next, based on **${title}**.`;
    const extraMd = formatExploreMarkdown(items);
    assistantNode.classList.add("explore-answer");
    assistantNode.classList.remove("error");
    assistantNode.innerHTML = `${renderMarkdown(intro)}${renderExploreCardsHtml(items)}`;
    state.history.push({ role: "user", content: question });
    state.history.push({
      role: "assistant",
      content: [intro, extraMd].filter(Boolean).join("\n\n").trim(),
    });
    setStatus("Explore ready");
  } catch (err) {
    assistantNode.textContent = formatUserError(err.message);
    assistantNode.classList.add("error");
    setStatus(formatUserError(err.message), true);
  } finally {
    state.busy = false;
    els.askBtn.disabled = false;
  }
}

async function fetchExploreItems() {
  const pageUrl = state.page?.url || "";
  const cached = await readExploreCache(pageUrl);
  if (cached?.length) return cached;
  const ready = await ensureBackendReady({ quiet: true });
  if (!ready) throw new Error("Backend not connected");
  const res = await fetch(`${BACKEND}/library/explore`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ page: state.page }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Explore failed");
  const items = normalizeExploreItems(data.suggestions || []);
  await writeExploreCache(pageUrl, items);
  return items;
}

function exploreCacheKey(url) {
  return `explore:${url}`;
}

async function readExploreCache(url) {
  if (!url) return null;
  if (state.exploreCache[url]?.length) return state.exploreCache[url];
  return new Promise((resolve) => {
    chrome.storage.session.get(exploreCacheKey(url), (data) => {
      const items = data[exploreCacheKey(url)] || null;
      if (items?.length) state.exploreCache[url] = items;
      resolve(items);
    });
  });
}

async function writeExploreCache(url, items) {
  if (!url) return;
  state.exploreCache[url] = items;
  await chrome.storage.session.set({ [exploreCacheKey(url)]: items });
}

function normalizeExploreItems(raw) {
  const items = [];
  for (const entry of raw || []) {
    if (typeof entry === "string") {
      const match = entry.match(/https?:\/\/\S+/);
      const url = match ? match[0].replace(/[),.:;]+$/, "") : "";
      if (!url) continue;
      const title = entry.replace(url, "").replace(/[—-]/g, " ").trim() || url;
      items.push({ title, url });
      continue;
    }
    const url = String(entry?.url || entry?.href || "").trim();
    if (!url.startsWith("http")) continue;
    const why = String(entry?.why || entry?.blurb || "").trim();
    items.push({
      title: String(entry?.title || url).trim(),
      url,
      ...(why ? { why } : {}),
    });
  }
  return items.slice(0, 10);
}

function hostnameFromUrl(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

function isExploreQuestion(text) {
  return /^Explore more articles related to /i.test(String(text || "").trim());
}

function formatExploreMarkdown(items) {
  if (!items?.length) return "";
  const lines = items.map((item) => {
    const why = String(item.why || "").trim();
    const host = hostnameFromUrl(item.url);
    return why
      ? `- **[${item.title}](${item.url})** — ${host}\n  ${why}`
      : `- **[${item.title}](${item.url})** — ${host}`;
  });
  return `### Articles to open next\n\n${lines.join("\n")}`;
}

function renderExploreCardsHtml(items) {
  if (!items?.length) return "";
  const cards = items.map((item) => {
    const why = String(item.why || "").trim();
    return `<button type="button" class="explore-chat-card" data-url="${escapeAttr(item.url)}">
      <span class="explore-chat-title">${escapeHtml(item.title)}</span>
      <span class="explore-chat-url">${escapeHtml(hostnameFromUrl(item.url))}</span>
      ${why ? `<span class="explore-chat-why">${escapeHtml(why)}</span>` : ""}
    </button>`;
  }).join("");
  return `<div class="explore-chat-list">${cards}</div>`;
}

function parseExploreItemsFromMarkdown(text) {
  const items = [];
  const re = /\[([^\]]+)\]\((https?:\/\/[^)]+)\)(?:[^\n]*—\s*([^\n]+))?(?:\n\s+([^\n-].+))?/g;
  let match;
  while ((match = re.exec(String(text || "")))) {
    items.push({
      title: match[1].trim(),
      url: match[2].trim(),
      ...(match[4] ? { why: match[4].trim() } : {}),
    });
  }
  return items;
}

async function askQuestion(presetQuestion) {
  const fromInput = presetQuestion == null;
  const question = String(presetQuestion ?? els.question.value).trim();
  if (!question || state.busy || !state.page) return null;

  switchPageTab("chat");
  state.busy = true;
  els.askBtn.disabled = true;
  removeChatEmptyHint();
  appendMessage("user", question);
  if (fromInput) els.question.value = "";

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
    let renderTimer = 0;

    const paintAnswer = (final = false) => {
      if (final) {
        window.clearTimeout(renderTimer);
        setAssistantMarkdown(assistantNode, answer);
        return;
      }
      window.clearTimeout(renderTimer);
      renderTimer = window.setTimeout(() => {
        setAssistantMarkdown(assistantNode, answer);
        els.messages.scrollTop = els.messages.scrollHeight;
      }, 80);
    };

    const ingestSse = (chunk) => {
      buffer += chunk;
      const parts = buffer.split("\n\n");
      buffer = parts.pop() || "";
      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith("data:")) continue;
        const payload = JSON.parse(line.slice(5).trim());
        if (payload.error) throw new Error(payload.error);
        if (payload.token) {
          answer += payload.token;
          paintAnswer(false);
        }
      }
    };

    while (true) {
      const { value, done } = await reader.read();
      if (value) ingestSse(decoder.decode(value, { stream: !done }));
      if (done) {
        ingestSse(decoder.decode());
        // Flush a trailing event that never got a final blank separator.
        if (buffer.trim()) ingestSse("\n\n");
        break;
      }
    }

    state.history.push({ role: "user", content: question });
    state.history.push({ role: "assistant", content: answer });
    paintAnswer(true);
    setStatus("Answer ready");
    return { answer, assistantNode };
  } catch (err) {
    assistantNode.textContent = formatUserError(err.message);
    assistantNode.classList.add("error");
    setStatus(formatUserError(err.message), true);
    return { answer: "", assistantNode };
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
      const quoteCount = Number(page.quote_count || 0);
      const savedWhen = formatTimestamp(page.saved_at);
      card.innerHTML = `
        <div class="saved-card-main">
          <h3>${escapeHtml(page.title || "Untitled")}</h3>
          <div class="saved-card-meta">
            <span class="muted">${escapeHtml(page.site || "")}</span>
            ${quoteCount ? `<span class="saved-card-pill">${quoteCount} quote${quoteCount === 1 ? "" : "s"}</span>` : ""}
            ${savedWhen ? `<span class="saved-card-pill">${escapeHtml(savedWhen)}</span>` : ""}
          </div>
          ${summaryPreview ? `<p class="saved-card-summary">${escapeHtml(summaryPreview.slice(0, 140))}${summaryPreview.length > 140 ? "…" : ""}</p>` : ""}
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
  state.savedDetailPage = null;
  els.savedList.hidden = false;
  els.savedDetail.hidden = true;
}

async function copySavedBookshelfJson() {
  const page = state.savedDetailPage;
  if (!page) {
    setStatus("Open a saved page first", true);
    return;
  }
  const entry = ContextBookshelf.buildEntry({
    title: page.title,
    url: page.url,
    ...(page.metadata || {}),
  });
  const copied = await copyTextToClipboard(ContextBookshelf.format(entry));
  setStatus(copied ? "JSON copied" : "Select the JSON and copy it", !copied);
}

async function openSavedPage(pageId) {
  try {
    const res = await fetch(`${BACKEND}/library/pages/${pageId}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Failed to load page");
    const page = data.page;
    const meta = normalizeMetadata(page.metadata);
    state.selectedSavedId = pageId;
    state.savedDetailPage = page;
    els.savedList.hidden = true;
    els.savedDetail.hidden = false;
    els.savedDetailTitle.textContent = page.title || "Untitled";
    els.savedDetailUrl.textContent = page.url || "";
    els.savedSummary.innerHTML = renderMarkdown(page.summary || "_No summary._");

    const notes = meta.notes || "";
    if (els.savedNotes) {
      els.savedNotes.innerHTML = notes
        ? ContextNotes.markdownToHtml(notes)
        : '<p class="muted">No notes saved for this page.</p>';
    }

    els.savedChat.innerHTML = "";
    for (const turn of page.chat_history || []) {
      const node = document.createElement("div");
      node.className = `message ${turn.role}`;
      if (turn.role === "assistant") {
        setAssistantMarkdown(node, turn.content);
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
    if (state.view === "life") loadLifeView();
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
      "Removes saved pages, quotes, notes drafts, per-page chats, and those items from Life.\n\nCalendar, messages, and other captured events stay.",
    confirmText: "Clear saved pages",
    cancelText: "Cancel",
  });
  if (!confirmed) return;
  try {
    const res = await fetch(`${BACKEND}/library/clear`, { method: "POST" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Clear failed");
    await clearLocalPageDrafts();
    state.savedPageId = null;
    state.savedPages = [];
    state.selectedSavedId = null;
    state.quotes = [];
    markPageSaved(false);
    refreshExportJsonPreview();
    setStatus("Saved pages cleared");
    if (state.view === "chat") void refreshPage();
    if (state.view === "saved") loadSavedPages();
    if (state.view === "graph") renderGraph();
    if (state.view === "life") loadLifeView();
    if (state.view === "settings") loadSettingsView();
  } catch (err) {
    setStatus(err.message, true);
  }
}

async function clearAllData() {
  const confirmed = await showConfirmDialog({
    title: "Delete all data?",
    message:
      "Wipes everything in ~/.kb/ and local notes drafts in the extension — events, memory, relationships, integrations, saved library, and Quotes notes.\n\nThis cannot be undone.",
    confirmText: "Delete everything",
    cancelText: "Cancel",
    danger: true,
  });
  if (!confirmed) return;
  try {
    const res = await fetch(`${BACKEND}/delete-all`, { method: "POST" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Delete failed");
    await clearLocalPageDrafts();
    resetExtensionClientState();
    setStatus("All data deleted");
    if (state.view === "chat") void refreshPage();
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
  state.dateAdded = "";
  state.tags = [];
  state.savedPages = [];
  state.selectedSavedId = null;
  state.lifeEvents = [];
  state.lifeSummary = [];
  state.lifeCategory = "all";
  state.bucketLeaves = [];
  state.bucketTree = {};
  renderChatHistory([]);
  markPageSaved(false);
  refreshExportJsonPreview();
  if (els.lifeSummary) els.lifeSummary.innerHTML = "";
  if (els.lifeEvents) {
    els.lifeEvents.innerHTML =
      '<p class="muted empty-hint">Save a page to see it here.</p>';
  }
}

function appendMessage(role, text) {
  removeChatEmptyHint();
  const node = document.createElement("div");
  node.className = `message ${role}`;
  if (role === "assistant") {
    setAssistantMarkdown(node, text);
  } else {
    node.textContent = text;
  }
  els.messages.appendChild(node);
  els.messages.scrollTop = els.messages.scrollHeight;
  return node;
}

/** Always prefer rendered markdown; never leave raw ** / ### in the bubble. */
function setAssistantMarkdown(node, text) {
  if (!node) return;
  node.classList.add("markdown-body");
  const source = String(text || "");
  try {
    if (typeof renderMarkdown === "function") {
      node.innerHTML = renderMarkdown(source);
      return;
    }
  } catch (err) {
    console.warn("Context markdown render failed:", err);
  }
  node.textContent = source;
}

function removeChatEmptyHint() {
  const hint = document.getElementById("chat-empty-hint");
  if (hint) hint.remove();
}

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
      const option = document.createElement("option");
      option.value = leaf;
      option.textContent = leaf;
      option.selected = leaf === selected;
      select.appendChild(option);
    }
    return;
  }
  for (const parent of parents) {
    const children = tree[parent] || [];
    if (!children.length) {
      const option = document.createElement("option");
      option.value = parent;
      option.textContent = parent;
      option.selected = parent === selected;
      select.appendChild(option);
      continue;
    }
    const group = document.createElement("optgroup");
    group.label = parent;
    for (const child of children) {
      const option = document.createElement("option");
      option.value = `${parent}/${child}`;
      option.textContent = child;
      option.selected = `${parent}/${child}` === selected;
      group.appendChild(option);
    }
    select.appendChild(group);
  }
}

function renderLifeChips() {
  if (!els.lifeSummary) return;
  els.lifeSummary.innerHTML = "";
  const topLevel = state.lifeSummary || [];
  const allBtn = document.createElement("button");
  allBtn.type = "button";
  allBtn.className = `life-chip${state.lifeCategory === "all" ? " active" : ""}`;
  allBtn.textContent = "All";
  allBtn.addEventListener("click", () => {
    state.lifeCategory = "all";
    renderLifeChips();
    renderLifeEvents();
  });
  els.lifeSummary.appendChild(allBtn);
  for (const item of topLevel) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = `life-chip${state.lifeCategory === item.category ? " active" : ""}`;
    chip.innerHTML = `<strong>${escapeHtml(item.category)}</strong> ${escapeHtml(String(item.percent))}%`;
    chip.addEventListener("click", () => {
      state.lifeCategory = item.category;
      renderLifeChips();
      renderLifeEvents();
    });
    els.lifeSummary.appendChild(chip);
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
    state.bucketTree = taxonomy.tree || {};
    state.lifeEvents = eventsData.events || [];
    state.lifeSummary = summary.by_top_level || [];
    if (state.lifeCategory !== "all" && !state.lifeSummary.some((item) => item.category === state.lifeCategory)) {
      state.lifeCategory = "all";
    }

    renderLifeChips();
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

  const filter = state.lifeCategory || "all";
  const events = (state.lifeEvents || []).filter(
    (event) => filter === "all" || parentBucket(event.bucket) === filter
  );

  if (!events.length) {
    els.lifeEvents.innerHTML =
      '<p class="muted empty-hint">Save a page to see it categorized here.</p>';
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
    els.lifeEvents.appendChild(heading);

    for (const event of byParent[parent]) {
      const card = document.createElement("article");
      card.className = "life-event";
      if (event.user_overridden) card.classList.add("user-overridden");

      const meta = document.createElement("div");
      meta.className = "life-event-meta";
      meta.innerHTML = `
        <span>${escapeHtml(lifeSourceLabel(event.source))}</span>
        <span class="muted">${escapeHtml(formatTimestamp(event.timestamp))}</span>
      `;

      if (event.title) {
        const title = document.createElement("h4");
        title.className = "life-event-title";
        title.textContent = event.title;
        card.append(meta, title);
      } else {
        card.append(meta);
      }

      const preview = document.createElement("p");
      preview.className = "life-event-preview";
      preview.textContent = event.text_preview || "(no preview)";

      const actions = document.createElement("div");
      actions.className = "life-event-actions";

      const select = document.createElement("select");
      select.dataset.eventId = event.event_id;
      fillBucketSelect(select, event.bucket);

      const saveBtn = document.createElement("button");
      saveBtn.type = "button";
      saveBtn.textContent = "Save";
      saveBtn.disabled = select.value === event.bucket;
      select.addEventListener("change", () => {
        saveBtn.disabled = select.value === event.bucket;
      });
      saveBtn.addEventListener("click", () => overrideEventBucket(event.event_id, select.value, saveBtn));

      actions.append(select, saveBtn);
      card.append(preview, actions);
      els.lifeEvents.appendChild(card);
    }
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
  closeWikiReader();
  els.wikiArticles.innerHTML = "";
  try {
    const [statusRes, articlesRes] = await Promise.all([
      fetch(`${BACKEND}/wiki/status`),
      fetch(`${BACKEND}/wiki/articles`),
    ]);
    const status = await statusRes.json();
    const articlesData = await articlesRes.json();
    if (!statusRes.ok) throw new Error(status.error || "Could not load wiki status");

    renderWikiStats(status);
    const pending = Number(status.uncompiled_count || 0);
    if (els.wikiPendingBanner && els.wikiPendingText) {
      if (pending > 0) {
        els.wikiPendingBanner.hidden = false;
        els.wikiPendingText.textContent =
          `${pending} source${pending === 1 ? "" : "s"} waiting to compile — tap Compile to update articles.`;
      } else {
        els.wikiPendingBanner.hidden = true;
      }
    }

    const articles = articlesData.articles || [];
    if (els.wikiEmpty) els.wikiEmpty.hidden = articles.length > 0;
    state.wikiArticles = articles;

    for (const article of articles) {
      const card = document.createElement("button");
      card.type = "button";
      card.className = "wiki-card";
      card.dataset.slug = article.slug || "";
      const excerpt = (article.excerpt || "").trim();
      card.innerHTML = `
        <span class="wiki-card-mark">◇</span>
        <div class="wiki-card-body">
          <strong>${escapeHtml(article.title || article.slug || "Untitled")}</strong>
          ${excerpt ? `<span class="wiki-card-excerpt">${escapeHtml(excerpt)}</span>` : ""}
        </div>
      `;
      card.addEventListener("click", () => openWikiArticle(article.slug));
      els.wikiArticles.appendChild(card);
    }
  } catch (err) {
    if (els.wikiStatsRow) {
      els.wikiStatsRow.hidden = true;
    }
    if (els.wikiEmpty) {
      els.wikiEmpty.hidden = false;
      els.wikiEmpty.textContent = err.message;
    }
  }
}

function renderWikiStats(status) {
  if (!els.wikiStatsRow) return;
  const raw = Number(status.raw_count || 0);
  const articles = Number(status.article_count || 0);
  const pending = Number(status.uncompiled_count || 0);
  els.wikiStatsRow.hidden = false;
  els.wikiStatsRow.innerHTML = `
    <div class="wiki-stat"><strong>${raw}</strong><span>Raw</span></div>
    <div class="wiki-stat"><strong>${articles}</strong><span>Articles</span></div>
    <div class="wiki-stat${pending > 0 ? " wiki-stat-warn" : ""}"><strong>${pending}</strong><span>Pending</span></div>
  `;
}

function closeWikiReader() {
  state.wikiSelectedSlug = null;
  if (els.wikiReader) els.wikiReader.hidden = true;
  if (els.wikiListPanel) els.wikiListPanel.hidden = false;
  document.querySelectorAll(".wiki-card").forEach((el) => el.classList.remove("active"));
}

async function openWikiArticle(slug) {
  if (!slug || !els.wikiReader) return;
  state.wikiSelectedSlug = slug;
  document.querySelectorAll(".wiki-card").forEach((el) => {
    el.classList.toggle("active", el.dataset.slug === slug);
  });
  if (els.wikiListPanel) els.wikiListPanel.hidden = true;
  els.wikiReader.hidden = false;
  if (els.wikiReaderTitle) els.wikiReaderTitle.textContent = "Loading…";
  if (els.wikiReaderBody) els.wikiReaderBody.innerHTML = "";
  if (els.wikiReaderOpen) {
    els.wikiReaderOpen.href = `${BACKEND}/app/#article-${encodeURIComponent(slug)}`;
  }
  try {
    const res = await fetch(`${BACKEND}/wiki/articles/${encodeURIComponent(slug)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Could not load article");
    const article = data.article;
    if (els.wikiReaderTitle) els.wikiReaderTitle.textContent = article.title || slug;
    if (els.wikiReaderBody) {
      els.wikiReaderBody.innerHTML = renderMarkdown(article.content || "_Empty article._");
    }
  } catch (err) {
    if (els.wikiReaderBody) els.wikiReaderBody.textContent = err.message;
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
  if (els.wikiAskSources) els.wikiAskSources.hidden = true;
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
    if (els.wikiAskSources) {
      if (data.sources?.length) {
        els.wikiAskSources.hidden = false;
        els.wikiAskSources.textContent = `Sources: ${data.sources.join(" · ")}`;
      } else {
        els.wikiAskSources.hidden = true;
      }
    }
  } catch (err) {
    if (els.wikiAskReply) els.wikiAskReply.textContent = formatUserError(err.message);
    setStatus(formatUserError(err.message), true);
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
