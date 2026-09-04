const TOOLBAR_ID = "context-save-toolbar";
const MIN_SELECTION = 8;
const SKIP_CLOSEST = `script, style, noscript, textarea, input, select, #${TOOLBAR_ID}`;

let toolbar = null;
let noteInput = null;
let pendingText = "";
let paintedKeys = new Set();
let unpaintedQuotes = [];
let panelOpen = false;
let painting = false;
let retryTimer = 0;
let paintObserver = null;

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === "PANEL_OPENED") {
    panelOpen = true;
    const selected = normalizeSelection(window.getSelection()?.toString() || "");
    if (isSaveableSelection(selected)) {
      pendingText = selected;
      chrome.runtime.sendMessage({ type: "SELECTION_CHANGED", selected });
      try {
        const range = window.getSelection().getRangeAt(0);
        showToolbar(range.getBoundingClientRect());
      } catch {
        // Selection may not have a range on this frame.
      }
    }
    sendResponse({ ok: true });
    return false;
  }
  if (message?.type === "PANEL_CLOSED") {
    panelOpen = false;
    hideToolbar();
    sendResponse({ ok: true });
    return false;
  }
  if (message?.type === "REPAINT_HIGHLIGHTS") {
    loadAndPaintHighlights().then(() => sendResponse({ ok: true }));
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
  return false;
});

chrome.runtime.sendMessage({ type: "GET_PANEL_STATE" }, (response) => {
  if (chrome.runtime.lastError) return;
  panelOpen = Boolean(response?.open);
  if (!panelOpen) hideToolbar();
});

document.addEventListener("mouseup", onPointerUp, true);
document.addEventListener("keyup", onPointerUp, true);
document.addEventListener("mousedown", onDocumentMouseDown, true);
document.addEventListener("scroll", hideToolbar, true);

trackClientNavigation(() => {
  paintedKeys = new Set();
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
    chrome.runtime.sendMessage({ type: "SELECTION_CHANGED", selected: text });
    if (!panelOpen) {
      hideToolbar();
      return;
    }
    const range = selection.rangeCount ? selection.getRangeAt(0) : null;
    if (!range) {
      hideToolbar();
      return;
    }
    showToolbar(range.getBoundingClientRect());
  }, 12);
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
  if (!panelOpen) return;
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
}

async function loadAndPaintHighlights() {
  try {
    const response = await chrome.runtime.sendMessage({
      type: "GET_PAGE_QUOTES",
      page_url: location.href,
    });
    if (!response?.ok) return;
    clearPaintedHighlights();
    const quotes = (response.quotes || []).slice().sort(
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
  return mark;
}

function wrapNodeSlice(node, from, to, note, quoteId) {
  if (!node?.parentNode || to <= from) return false;
  const range = document.createRange();
  try {
    range.setStart(node, from);
    range.setEnd(node, to);
    range.surroundContents(createMark(note, quoteId));
    return true;
  } catch {
    return false;
  }
}

function paintMatch(match, note, quoteId) {
  const { start, end } = match;
  if (start.node === end.node) {
    return wrapNodeSlice(start.node, start.offset, end.offset + 1, note, quoteId);
  }

  const nodes = collectTextNodes(document.body);
  const slice = [];
  let collecting = false;
  for (const node of nodes) {
    if (node === start.node) collecting = true;
    if (collecting) slice.push(node);
    if (node === end.node) break;
  }
  if (!slice.length) return false;

  let painted = false;
  painting = true;
  for (let i = slice.length - 1; i >= 0; i -= 1) {
    const node = slice[i];
    const from = node === start.node ? start.offset : 0;
    const to = node === end.node ? end.offset + 1 : (node.nodeValue || "").length;
    if (wrapNodeSlice(node, from, to, note, quoteId)) painted = true;
  }
  painting = false;
  return painted;
}

function paintHighlight(text, note = "", quoteId = "") {
  const normalized = normalizeSelection(text);
  const key = quoteKey(normalized, quoteId);
  if (!normalized || paintedKeys.has(key)) return Boolean(marksForQuote(quoteId, normalized).length);

  const match = findQuoteMatch(normalized);
  if (!match) return false;

  painting = true;
  const painted = paintMatch(match, note, quoteId);
  painting = false;
  if (painted) {
    paintedKeys.add(key);
    return true;
  }
  return false;
}

function marksForQuote(quoteId, text = "") {
  const id = String(quoteId || "").trim();
  if (id) {
    const escaped = (window.CSS && CSS.escape) ? CSS.escape(id) : id.replace(/"/g, "");
    const found = document.querySelectorAll(`mark.ctx-highlight[data-quote-id="${escaped}"]`);
    if (found.length) return found;
  }
  const needle = normalizeSelection(text);
  if (!needle) return [];
  return Array.from(document.querySelectorAll("mark.ctx-highlight")).filter(
    (mark) => normalizeSelection(mark.textContent || "") === needle
      || normalizeSelection(mark.textContent || "").includes(needle)
  );
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
