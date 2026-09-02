const TOOLBAR_ID = "context-save-toolbar";
const MIN_SELECTION = 8;

let toolbar = null;
let noteInput = null;
let pendingText = "";
let paintedTexts = new Set();

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === "REPAINT_HIGHLIGHTS") {
    loadAndPaintHighlights().then(() => sendResponse({ ok: true }));
    return true;
  }
  if (message?.type === "CLEAR_HIGHLIGHTS") {
    clearPaintedHighlights();
    sendResponse({ ok: true });
    return false;
  }
  return false;
});

document.addEventListener("mouseup", onPointerUp, true);
document.addEventListener("keyup", onPointerUp, true);
document.addEventListener("mousedown", onDocumentMouseDown, true);
document.addEventListener("scroll", hideToolbar, true);

trackClientNavigation(() => {
  paintedTexts = new Set();
  loadAndPaintHighlights();
});

loadAndPaintHighlights();

function onDocumentMouseDown(event) {
  if (toolbar && toolbar.contains(event.target)) return;
  hideToolbar();
}

function onPointerUp(event) {
  if (toolbar && toolbar.contains(event.target)) return;
  window.setTimeout(() => {
    const selection = window.getSelection();
    const text = normalizeSelection(selection?.toString() || "");
    if (!isSaveableSelection(text)) {
      hideToolbar();
      chrome.runtime.sendMessage({ type: "SELECTION_CHANGED", selected: "" });
      return;
    }
    pendingText = text;
    const range = selection.getRangeAt(0);
    const rect = range.getBoundingClientRect();
    showToolbar(rect);
    chrome.runtime.sendMessage({ type: "SELECTION_CHANGED", selected: text });
  }, 12);
}

function normalizeSelection(text) {
  return (text || "").replace(/\s+/g, " ").trim();
}

function isSaveableSelection(text) {
  return normalizeSelection(text).length >= MIN_SELECTION;
}

function ensureToolbar() {
  if (toolbar) return toolbar;

  toolbar = document.createElement("div");
  toolbar.id = TOOLBAR_ID;
  toolbar.hidden = true;

  const saveBtn = document.createElement("button");
  saveBtn.type = "button";
  saveBtn.dataset.action = "save";
  saveBtn.textContent = "Save quote";
  saveBtn.addEventListener("click", () => quickSaveQuote(pendingText, noteInput?.value || ""));

  noteInput = document.createElement("input");
  noteInput.type = "text";
  noteInput.className = "ctx-note-input";
  noteInput.placeholder = "Note (optional)";
  noteInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      quickSaveQuote(pendingText, noteInput.value || "");
    }
  });

  toolbar.append(saveBtn, noteInput);
  document.documentElement.appendChild(toolbar);
  return toolbar;
}

function showToolbar(rect) {
  const bar = ensureToolbar();
  const top = window.scrollY + rect.top - 48;
  const left = window.scrollX + rect.left + rect.width / 2;
  bar.style.top = `${Math.max(8, top)}px`;
  bar.style.left = `${Math.max(8, left)}px`;
  bar.style.transform = "translateX(-50%)";
  bar.hidden = false;
  bar.querySelector('[data-action="save"]').disabled = false;
  bar.querySelector('[data-action="save"]').textContent = "Save quote";
}

function hideToolbar() {
  if (!toolbar) return;
  toolbar.hidden = true;
  if (noteInput) noteInput.value = "";
}

async function quickSaveQuote(text, note = "") {
  const normalized = normalizeSelection(text);
  if (!isSaveableSelection(normalized)) return;

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
  } catch (err) {
    if (saveBtn) {
      saveBtn.disabled = false;
      saveBtn.textContent = "Save quote";
    }
    console.warn("Context quote save failed:", err);
  }
}

function clearPaintedHighlights() {
  document.querySelectorAll("mark.ctx-highlight").forEach((node) => {
    const parent = node.parentNode;
    if (!parent) return;
    parent.replaceChild(document.createTextNode(node.textContent || ""), node);
    parent.normalize();
  });
  paintedTexts = new Set();
}

async function loadAndPaintHighlights() {
  try {
    const response = await chrome.runtime.sendMessage({
      type: "GET_PAGE_QUOTES",
      page_url: location.href,
    });
    if (!response?.ok) return;
    for (const quote of response.quotes || []) {
      paintHighlight(quote.text, quote.note, quote.id);
    }
  } catch {
    // Extension context may be unavailable on some restricted pages.
  }
}

function paintHighlight(text, note = "", quoteId = "") {
  const normalized = normalizeSelection(text);
  if (!normalized || paintedTexts.has(normalized)) return;

  const root = document.body;
  if (!root) return;

  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = walker.nextNode())) {
    if (!node.nodeValue || !node.parentElement) continue;
    if (node.parentElement.closest(`#${TOOLBAR_ID}, mark.ctx-highlight`)) continue;
    const idx = node.nodeValue.indexOf(normalized);
    if (idx === -1) continue;

    const range = document.createRange();
    range.setStart(node, idx);
    range.setEnd(node, idx + normalized.length);
    const mark = document.createElement("mark");
    mark.className = "ctx-highlight";
    if (note) {
      mark.classList.add("ctx-has-note");
      mark.title = note;
    }
    if (quoteId) mark.dataset.quoteId = quoteId;
    try {
      range.surroundContents(mark);
      paintedTexts.add(normalized);
      return;
    } catch {
      continue;
    }
  }
}

function trackClientNavigation(onNavigate) {
  let lastUrl = location.href;

  const notify = () => {
    if (location.href === lastUrl) return;
    lastUrl = location.href;
    chrome.runtime.sendMessage({
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
