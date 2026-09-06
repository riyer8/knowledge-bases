const TOOLBAR_ID = "context-save-toolbar";
const TOAST_ID = "context-clip-toast";
const NOTE_POPOVER_ID = "context-highlight-note";
const MIN_SELECTION = 4;
const SKIP_CLOSEST = `script, style, noscript, textarea, input, select, #${TOOLBAR_ID}, #${NOTE_POPOVER_ID}`;

let toolbar = null;
let noteInput = null;
let pendingText = "";
let paintedKeys = new Set();
let unpaintedQuotes = [];
let panelOpen = false;
let painting = false;
let retryTimer = 0;
let paintObserver = null;
let notePopover = null;
let toastTimer = 0;
let toolbarTimer = 0;
let pointerSelecting = false;
let saveInFlight = false;

/** Fire-and-forget; swallows invalidated-context / missing-receiver errors. */
function runtimeSend(message) {
  if (!chrome.runtime?.id) return;
  try {
    const result = chrome.runtime.sendMessage(message);
    if (result && typeof result.catch === "function") result.catch(() => {});
  } catch (_) {
    /* extension context invalidated */
  }
}

function runtimeAlive() {
  return Boolean(chrome.runtime?.id);
}

function isStaleExtensionError(err) {
  const message = String(err?.message || err || "").toLowerCase();
  return (
    message.includes("extension context invalidated") ||
    message.includes("receiving end does not exist") ||
    message.includes("message port closed")
  );
}

function friendlyRuntimeError(err) {
  if (!runtimeAlive() || isStaleExtensionError(err)) {
    return "Extension updated — refreshing this page…";
  }
  return err?.message || "Save failed";
}

let listenersAttached = false;

function teardownListeners() {
  if (!listenersAttached) return;
  listenersAttached = false;
  document.removeEventListener("mousedown", onDocumentMouseDown, true);
  document.removeEventListener("mouseup", onPointerReleased, true);
  document.removeEventListener("touchend", onPointerReleased, true);
  document.removeEventListener("keyup", onPointerReleased, true);
  document.removeEventListener("selectionchange", onSelectionChange);
  document.removeEventListener("scroll", onViewportChange, true);
  window.removeEventListener("resize", onViewportChange);
  document.removeEventListener("click", onHighlightClick, true);
  document.removeEventListener("keydown", onPageKeydown, true);
  window.clearTimeout(toolbarTimer);
  window.clearTimeout(retryTimer);
  window.clearTimeout(toastTimer);
  paintObserver?.disconnect();
  paintObserver = null;
  hideToolbar();
  hideNotePopover();
}

function guardStaleHandler() {
  if (runtimeAlive()) return false;
  teardownListeners();
  return true;
}

function refreshPageForStaleExtension() {
  const key = "__ctx_stale_reload";
  try {
    if (sessionStorage.getItem(key)) return;
    sessionStorage.setItem(key, "1");
  } catch {
    /* private mode / blocked storage */
  }
  window.setTimeout(() => {
    try {
      location.reload();
    } catch {
      /* ignore */
    }
  }, 450);
}

function attachListeners() {
  if (listenersAttached) return;
  listenersAttached = true;
  document.addEventListener("mousedown", onDocumentMouseDown, true);
  document.addEventListener("mouseup", onPointerReleased, true);
  document.addEventListener("touchend", onPointerReleased, true);
  document.addEventListener("keyup", onPointerReleased, true);
  document.addEventListener("selectionchange", onSelectionChange);
  document.addEventListener("scroll", onViewportChange, true);
  window.addEventListener("resize", onViewportChange);
  document.addEventListener("click", onHighlightClick, true);
  document.addEventListener("keydown", onPageKeydown, true);
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (!runtimeAlive()) return false;
  if (message?.type === "PANEL_OPENED") {
    setPanelOpenFlag(true);
    scheduleToolbarUpdate(0);
    sendResponse({ ok: true });
    return false;
  }
  if (message?.type === "PANEL_CLOSED") {
    setPanelOpenFlag(false);
    sendResponse({ ok: true });
    return false;
  }
  if (message?.type === "REPAINT_HIGHLIGHTS") {
    const incoming = Array.isArray(message.quotes) ? message.quotes : null;
    loadAndPaintHighlights(incoming).then(() => sendResponse({ ok: true }));
    return true;
  }
  if (message?.type === "CLEAR_HIGHLIGHTS") {
    clearPaintedHighlights();
    sendResponse({ ok: true });
    return false;
  }
  if (message?.type === "SCROLL_TO_QUOTE") {
    void revealQuote(message.quoteId, message.text);
    sendResponse({ ok: true });
    return false;
  }
  if (message?.type === "HIGHLIGHT_SELECTION") {
    void highlightCurrentSelection().then((ok) => sendResponse({ ok }));
    return true;
  }
  return false;
});

if (typeof globalThis.__ctxHighlightsTeardown === "function") {
  try {
    globalThis.__ctxHighlightsTeardown();
  } catch {
    /* previous content-script generation */
  }
}
globalThis.__ctxHighlightsTeardown = teardownListeners;

if (runtimeAlive()) {
  chrome.runtime.sendMessage({ type: "GET_PANEL_STATE" }, (response) => {
    if (chrome.runtime.lastError) return;
    if (response && "open" in response) setPanelOpenFlag(response.open);
  });

  chrome.storage.session.get("panelOpen", (data) => {
    if (chrome.runtime.lastError) return;
    if (data?.panelOpen) setPanelOpenFlag(true);
  });

  chrome.storage.onChanged.addListener((changes, area) => {
    if (area === "session" && changes.panelOpen) {
      setPanelOpenFlag(changes.panelOpen.newValue);
    }
  });

  attachListeners();

  trackClientNavigation(() => {
    paintedKeys = new Set();
    hideNotePopover();
    loadAndPaintHighlights();
  });

  loadAndPaintHighlights();
}

function setPanelOpenFlag(open) {
  panelOpen = Boolean(open);
}

function isOurUiTarget(target) {
  if (!target) return false;
  if (toolbar && toolbar.contains(target)) return true;
  if (notePopover && notePopover.contains(target)) return true;
  return false;
}

function toolbarHasFocus() {
  const active = document.activeElement;
  return Boolean(active && toolbar && !toolbar.hidden && toolbar.contains(active));
}

function onDocumentMouseDown(event) {
  if (guardStaleHandler()) return;
  if (isOurUiTarget(event.target)) return;
  pointerSelecting = true;
  hideToolbar();
  hideNotePopover();
}

function onPointerReleased(event) {
  if (guardStaleHandler()) return;
  if (isOurUiTarget(event.target)) return;
  pointerSelecting = false;
  scheduleToolbarUpdate(30);
}

function onSelectionChange() {
  if (guardStaleHandler()) return;
  // While dragging, wait for mouseup/touchend so the range can settle.
  if (pointerSelecting) return;
  scheduleToolbarUpdate(60);
}

function onViewportChange() {
  if (guardStaleHandler()) return;
  if (!toolbar || toolbar.hidden) return;
  scheduleToolbarUpdate(0);
}

function scheduleToolbarUpdate(delayMs = 40) {
  window.clearTimeout(toolbarTimer);
  toolbarTimer = window.setTimeout(updateToolbarForSelection, delayMs);
}

function updateToolbarForSelection() {
  if (guardStaleHandler()) return;
  if (toolbarHasFocus()) return;

  const selection = window.getSelection();
  const text = normalizeSelection(selection?.toString() || "");
  if (!isSaveableSelection(text)) {
    hideToolbar();
    runtimeSend({ type: "SELECTION_CHANGED", selected: "" });
    return;
  }

  const anchor = selection?.anchorNode;
  if (anchor && isOurUiTarget(anchor)) return;

  const range = selection?.rangeCount ? selection.getRangeAt(0) : null;
  if (!range || range.collapsed) {
    hideToolbar();
    return;
  }

  pendingText = text;
  runtimeSend({ type: "SELECTION_CHANGED", selected: text });
  showToolbar(range.getBoundingClientRect());
}

function onPageKeydown(event) {
  if (guardStaleHandler()) return;
  // Prefer the extension command (background → HIGHLIGHT_SELECTION). This
  // handler is a fallback when the page has focus and the command is slow;
  // saveInFlight dedupes if both fire.
  if (!(event.altKey && !event.metaKey && !event.ctrlKey && !event.shiftKey)) return;
  if (event.key.toLowerCase() !== "h") return;
  const tag = event.target?.tagName?.toLowerCase();
  if (tag === "input" || tag === "textarea" || event.target?.isContentEditable) return;
  event.preventDefault();
  void highlightCurrentSelection();
}

function normalizeSelection(text) {
  return (text || "").replace(/\s+/g, " ").trim();
}

function quoteKey(text, quoteId = "") {
  const id = String(quoteId || "").trim();
  if (id) return `id:${id}`;
  return `text:${normalizeSelection(text)}`;
}

function isSaveableSelection(text) {
  return normalizeSelection(text).length >= MIN_SELECTION;
}

function ensureToolbar() {
  if (toolbar?.isConnected) return toolbar;
  const existing = document.getElementById(TOOLBAR_ID);
  if (existing) existing.remove();

  toolbar = document.createElement("div");
  toolbar.id = TOOLBAR_ID;
  toolbar.hidden = true;

  const saveBtn = document.createElement("button");
  saveBtn.type = "button";
  saveBtn.dataset.action = "save";
  saveBtn.textContent = "Highlight";
  saveBtn.title = "Save highlight (Alt+H)";

  noteInput = document.createElement("input");
  noteInput.type = "text";
  noteInput.className = "ctx-note-input";
  noteInput.placeholder = "Add a note…";
  noteInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      event.stopPropagation();
      void quickSaveQuote(pendingText, noteInput.value || "");
    }
    if (event.key === "Escape") {
      event.preventDefault();
      hideToolbar();
    }
  });

  const hint = document.createElement("span");
  hint.className = "ctx-hotkey-hint";
  hint.textContent = "⌥H";

  toolbar.append(saveBtn, noteInput, hint);

  // Keep selection on Highlight; allow the note input to focus normally.
  // Do not use capture-phase stopPropagation on click (that blocked the button).
  toolbar.addEventListener("mousedown", (event) => {
    event.stopPropagation();
    if (event.target === noteInput) return;
    event.preventDefault();
  });
  toolbar.addEventListener("mouseup", (event) => {
    event.stopPropagation();
  });
  toolbar.addEventListener("click", (event) => {
    event.stopPropagation();
    const save = event.target.closest?.('[data-action="save"]');
    if (save) {
      event.preventDefault();
      void quickSaveQuote(pendingText, noteInput?.value || "");
    }
  });

  document.documentElement.appendChild(toolbar);
  return toolbar;
}

function showToolbar(rect) {
  if (!rect || (rect.width === 0 && rect.height === 0)) return;
  hideNotePopover();
  const bar = ensureToolbar();
  const top = Math.max(8, Math.min(window.innerHeight - 52, rect.top - 48));
  const left = Math.min(window.innerWidth - 24, Math.max(8, rect.left + rect.width / 2));
  bar.style.top = `${top}px`;
  bar.style.left = `${left}px`;
  bar.style.transform = "translateX(-50%)";
  bar.hidden = false;
  const saveBtn = bar.querySelector('[data-action="save"]');
  if (saveBtn && !saveInFlight) {
    saveBtn.disabled = false;
    saveBtn.textContent = "Highlight";
  }
}

function hideToolbar() {
  if (!toolbar) return;
  toolbar.hidden = true;
  if (noteInput && document.activeElement !== noteInput) noteInput.value = "";
}

async function highlightCurrentSelection() {
  const selection = window.getSelection();
  const text = normalizeSelection(selection?.toString() || pendingText || "");
  if (!isSaveableSelection(text)) {
    showToast("Select text to highlight");
    return false;
  }
  pendingText = text;
  return quickSaveQuote(text, noteInput?.value || "");
}

async function quickSaveQuote(text, note = "") {
  const normalized = normalizeSelection(text);
  if (!isSaveableSelection(normalized)) return false;
  if (saveInFlight) return false;
  if (!runtimeAlive()) {
    showToast(friendlyRuntimeError(), true);
    refreshPageForStaleExtension();
    return false;
  }
  saveInFlight = true;

  const saveBtn = toolbar?.querySelector('[data-action="save"]');
  if (saveBtn) {
    saveBtn.disabled = true;
    saveBtn.textContent = "Saving…";
  }

  try {
    const response = await chrome.runtime.sendMessage({
      type: "QUICK_SAVE_QUOTE",
      text: normalized,
      note: (note || "").trim(),
      page_url: location.href,
      page_title: document.title || "",
    });
    if (!response?.ok) {
      throw new Error(response?.error || "Save failed");
    }
    paintHighlight(normalized, note, response.quote?.id);
    hideToolbar();
    window.getSelection()?.removeAllRanges();
    showToast(note?.trim() ? "Highlighted with note" : "Highlighted");
    return true;
  } catch (err) {
    if (saveBtn) {
      saveBtn.disabled = false;
      saveBtn.textContent = "Highlight";
    }
    const stale = !runtimeAlive() || isStaleExtensionError(err);
    const message = friendlyRuntimeError(err);
    showToast(message, true);
    if (stale) {
      teardownListeners();
      refreshPageForStaleExtension();
    } else {
      runtimeSend({ type: "QUOTE_SAVE_FAILED", error: message });
      console.warn("Context quote save failed:", err);
    }
    return false;
  } finally {
    saveInFlight = false;
  }
}

function showToast(message, isError = false) {
  let toast = document.getElementById(TOAST_ID);
  if (!toast) {
    toast = document.createElement("div");
    toast.id = TOAST_ID;
    document.documentElement.appendChild(toast);
  }
  toast.textContent = message;
  toast.classList.toggle("ctx-toast-error", Boolean(isError));
  toast.hidden = false;
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => {
    toast.hidden = true;
  }, 2200);
}

function clearPaintedHighlights() {
  painting = true;
  document.querySelectorAll("mark.ctx-highlight").forEach((node) => {
    const parent = node.parentNode;
    if (!parent) return;
    parent.replaceChild(document.createTextNode(node.textContent || ""), node);
    parent.normalize();
  });
  paintedKeys = new Set();
  unpaintedQuotes = [];
  painting = false;
  hideNotePopover();
}

async function loadAndPaintHighlights(quotesOverride = null) {
  try {
    let quotes = quotesOverride;
    if (!Array.isArray(quotes)) {
      const response = await chrome.runtime.sendMessage({
        type: "GET_PAGE_QUOTES",
        page_url: location.href,
      });
      if (!response?.ok) return;
      quotes = response.quotes || [];
    }
    clearPaintedHighlights();
    quotes = (quotes || []).slice().sort(
      (a, b) => normalizeSelection(b.text).length - normalizeSelection(a.text).length
    );
    unpaintedQuotes = [];
    for (const quote of quotes) {
      if (!paintHighlight(quote.text, quote.note, quote.id)) {
        unpaintedQuotes.push(quote);
      }
    }
    watchForUnpainted();
  } catch {
    // Extension context may be unavailable on some restricted pages.
  }
}

function collectTextNodes(root, nodes = []) {
  if (!root) return nodes;
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      if (!node.nodeValue) return NodeFilter.FILTER_REJECT;
      const parent = node.parentElement;
      if (!parent) return NodeFilter.FILTER_REJECT;
      if (parent.closest(SKIP_CLOSEST)) return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT;
    },
  });
  let node;
  while ((node = walker.nextNode())) nodes.push(node);
  const elements = root.querySelectorAll ? root.querySelectorAll("*") : [];
  for (const el of elements) {
    if (el.shadowRoot) collectTextNodes(el.shadowRoot, nodes);
  }
  return nodes;
}

function buildNormalizedIndex(nodes) {
  let normalized = "";
  const map = [];
  let lastWasSpace = true;
  for (const node of nodes) {
    const value = node.nodeValue || "";
    for (let i = 0; i < value.length; i += 1) {
      const isSpace = /\s/.test(value[i]);
      if (isSpace) {
        if (!lastWasSpace && normalized.length) {
          normalized += " ";
          map.push({ node, offset: i });
          lastWasSpace = true;
        }
        continue;
      }
      normalized += value[i];
      map.push({ node, offset: i });
      lastWasSpace = false;
    }
  }
  if (normalized.endsWith(" ")) {
    normalized = normalized.slice(0, -1);
    map.pop();
  }
  return { normalized, map };
}

function findQuoteMatch(needle) {
  const root = document.body;
  if (!root || !needle) return null;
  const nodes = collectTextNodes(root);
  const { normalized, map } = buildNormalizedIndex(nodes);
  const idx = normalized.indexOf(needle);
  if (idx === -1) return null;
  const last = idx + needle.length - 1;
  if (!map[idx] || !map[last]) return null;
  return { start: map[idx], end: map[last] };
}

function createMark(note, quoteId) {
  const mark = document.createElement("mark");
  mark.className = "ctx-highlight";
  if (note) {
    mark.classList.add("ctx-has-note");
    mark.title = note;
  }
  if (quoteId) mark.dataset.quoteId = quoteId;
  mark.dataset.ctxHighlight = "1";
  return mark;
}

function wrapNodeSlice(node, from, to, note, quoteId) {
  if (!node?.parentNode || to <= from) return false;
  if (node.parentElement?.closest("mark.ctx-highlight, script, style, textarea, input")) {
    return false;
  }
  const value = node.nodeValue || "";
  if (from < 0 || to > value.length) return false;
  const mark = createMark(note, quoteId);
  mark.textContent = value.slice(from, to);
  const fragment = document.createDocumentFragment();
  if (from > 0) fragment.appendChild(document.createTextNode(value.slice(0, from)));
  fragment.appendChild(mark);
  if (to < value.length) fragment.appendChild(document.createTextNode(value.slice(to)));
  node.parentNode.replaceChild(fragment, node);
  return true;
}

function paintMatch(match, note, quoteId) {
  const { start, end } = match;
  if (start.node === end.node) {
    return wrapNodeSlice(start.node, start.offset, end.offset + 1, note, quoteId);
  }

  const nodes = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let collecting = false;
  let node;
  while ((node = walker.nextNode())) {
    if (node === start.node) collecting = true;
    if (collecting) nodes.push(node);
    if (node === end.node) break;
  }
  if (!nodes.length) return false;

  painting = true;
  let ok = true;
  for (let i = nodes.length - 1; i >= 0; i -= 1) {
    const current = nodes[i];
    const value = current.nodeValue || "";
    let from = 0;
    let to = value.length;
    if (current === start.node) from = start.offset;
    if (current === end.node) to = end.offset + 1;
    if (!wrapNodeSlice(current, from, to, note, quoteId)) ok = false;
  }
  painting = false;
  return ok;
}

function paintHighlight(text, note = "", quoteId = "") {
  const needle = normalizeSelection(text);
  if (!needle) return false;
  const key = quoteKey(needle, quoteId);
  if (paintedKeys.has(key) || paintedKeys.has(quoteKey(needle))) return true;
  const match = findQuoteMatch(needle);
  if (!match) return false;
  const painted = paintMatch(match, note, quoteId);
  if (painted) {
    paintedKeys.add(key);
    paintedKeys.add(quoteKey(needle));
  }
  return painted;
}

function marksForQuote(quoteId, text) {
  const id = String(quoteId || "").trim();
  if (id) {
    const byId = Array.from(document.querySelectorAll(`mark.ctx-highlight[data-quote-id="${CSS.escape(id)}"]`));
    if (byId.length) return byId;
  }
  const needle = normalizeSelection(text);
  if (!needle) return [];
  return Array.from(document.querySelectorAll("mark.ctx-highlight")).filter(
    (mark) => normalizeSelection(mark.textContent) === needle
  );
}

function onHighlightClick(event) {
  if (guardStaleHandler()) return;
  const mark = event.target?.closest?.("mark.ctx-highlight");
  if (!mark) return;
  event.preventDefault();
  event.stopPropagation();
  showNotePopover(mark);
}

function ensureNotePopover() {
  if (notePopover) return notePopover;
  notePopover = document.createElement("div");
  notePopover.id = NOTE_POPOVER_ID;
  notePopover.hidden = true;
  notePopover.innerHTML = `
    <p class="ctx-note-label">Note</p>
    <p class="ctx-note-body"></p>
    <button type="button" class="ctx-note-open">Open in Notes</button>
  `;
  notePopover.addEventListener("mousedown", (event) => event.stopPropagation(), true);
  notePopover.querySelector(".ctx-note-open")?.addEventListener("click", () => {
    runtimeSend({ type: "OPEN_NOTES_PANEL" });
    hideNotePopover();
  });
  document.documentElement.appendChild(notePopover);
  return notePopover;
}

function showNotePopover(mark) {
  hideToolbar();
  const pop = ensureNotePopover();
  const note = mark.title || "";
  const body = pop.querySelector(".ctx-note-body");
  if (body) {
    body.textContent = note || "No note yet — open Notes to add one.";
    body.classList.toggle("ctx-note-empty", !note);
  }
  const rect = mark.getBoundingClientRect();
  pop.style.top = `${Math.min(window.innerHeight - 12, rect.bottom + 8)}px`;
  pop.style.left = `${Math.min(window.innerWidth - 24, Math.max(8, rect.left))}px`;
  pop.hidden = false;
}

function hideNotePopover() {
  if (!notePopover) return;
  notePopover.hidden = true;
}

function watchForUnpainted() {
  if (!unpaintedQuotes.length) {
    paintObserver?.disconnect();
    paintObserver = null;
    return;
  }
  if (!paintObserver && document.documentElement) {
    paintObserver = new MutationObserver(() => {
      if (painting) return;
      window.clearTimeout(retryTimer);
      retryTimer = window.setTimeout(retryUnpainted, 220);
    });
    paintObserver.observe(document.documentElement, {
      childList: true,
      subtree: true,
      characterData: true,
    });
  }
  window.clearTimeout(retryTimer);
  retryTimer = window.setTimeout(retryUnpainted, 400);
}

function retryUnpainted() {
  if (!unpaintedQuotes.length) return;
  const still = [];
  for (const quote of unpaintedQuotes) {
    if (!paintHighlight(quote.text, quote.note, quote.id)) still.push(quote);
  }
  unpaintedQuotes = still;
  if (!unpaintedQuotes.length) {
    paintObserver?.disconnect();
    paintObserver = null;
  }
}

async function revealQuote(quoteId, text) {
  const normalized = normalizeSelection(text || "");
  let marks = marksForQuote(quoteId, normalized);
  if (!marks.length && normalized) {
    paintHighlight(normalized, "", quoteId);
    marks = marksForQuote(quoteId, normalized);
  }
  const target = marks[0];
  if (!target) return false;
  target.scrollIntoView({ behavior: "smooth", block: "center", inline: "nearest" });
  for (const mark of marks) {
    mark.classList.add("ctx-highlight-focus");
  }
  window.setTimeout(() => {
    for (const mark of marks) mark.classList.remove("ctx-highlight-focus");
  }, 1600);
  return true;
}

function trackClientNavigation(onNavigate) {
  let lastUrl = location.href;

  const notify = () => {
    if (location.href === lastUrl) return;
    lastUrl = location.href;
    runtimeSend({
      type: "PAGE_NAVIGATED",
      url: location.href,
      title: document.title || "",
    });
    onNavigate?.();
  };

  const wrapHistory = (method) => {
    const original = history[method];
    history[method] = function wrappedHistoryMethod(...args) {
      const result = original.apply(this, args);
      window.dispatchEvent(new Event("locationchange"));
      return result;
    };
  };

  wrapHistory("pushState");
  wrapHistory("replaceState");
  window.addEventListener("popstate", () => window.dispatchEvent(new Event("locationchange")));
  window.addEventListener("locationchange", notify);
}
