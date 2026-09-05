const BACKEND = "http://127.0.0.1:8765";
const LAUNCHER_URL = "http://127.0.0.1:8798";
const NATIVE_HOST = "com.context.backend";

chrome.runtime.onInstalled.addListener(() => {
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });
  ensureBackend().catch(() => {});
});

chrome.runtime.onStartup.addListener(() => {
  ensureBackend().catch(() => {});
});

const panelPorts = new Set();

if (chrome.sidePanel?.onOpened) {
  chrome.sidePanel.onOpened.addListener(() => {
    ensureBackend().catch(() => {});
  });
}

chrome.runtime.onConnect.addListener((port) => {
  if (port.name !== "sidepanel") return;
  const wasOpen = panelPorts.size > 0;
  panelPorts.add(port);
  if (!wasOpen) {
    void setPanelOpen(true);
  }
  port.onDisconnect.addListener(() => {
    panelPorts.delete(port);
    if (panelPorts.size === 0) {
      void setPanelOpen(false);
    }
  });
});

chrome.tabs.onUpdated.addListener(async (tabId, info, tab) => {
  if (!tab.url || info.status !== "complete") return;
  if (tab.url.startsWith("chrome://") || tab.url.startsWith("edge://")) return;
  await chrome.sidePanel.setOptions({ tabId, path: "sidepanel/index.html", enabled: true });
  const [active] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (active?.id === tabId) {
    await broadcastActiveTab(tab);
  }
});

chrome.tabs.onActivated.addListener(async ({ tabId }) => {
  try {
    const tab = await chrome.tabs.get(tabId);
    await broadcastActiveTab(tab);
  } catch {
    // Tab may have closed before we read it.
  }
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === "ENSURE_BACKEND") {
    ensureBackend().then(sendResponse);
    return true;
  }

  if (message?.type === "GET_EXTENSION_ID") {
    sendResponse({ id: chrome.runtime.id });
    return false;
  }

  if (message?.type === "GET_PANEL_STATE") {
    sendResponse({ open: panelPorts.size > 0 });
    return false;
  }

  if (message?.type === "GET_PAGE_CONTEXT") {
    chrome.tabs.query({ active: true, currentWindow: true }, async (tabs) => {
      const tab = tabs[0];
      if (!tab?.id) {
        sendResponse({ error: "No active tab" });
        return;
      }
      try {
        const page = await getPageContextForTab(tab);
        sendResponse({ page });
      } catch (err) {
        sendResponse({ error: String(err) });
      }
    });
    return true;
  }

  if (message?.type === "GET_PAGE_QUOTES") {
    (async () => {
      try {
        const pageUrl = String(message.page_url || "").trim();
        if (!pageUrl) {
          sendResponse({ ok: false, error: "page_url required" });
          return;
        }
        const savedMeta = await lookupSavedPage(pageUrl);
        const params = new URLSearchParams({ page_url: pageUrl });
        if (savedMeta?.id) params.set("page_id", savedMeta.id);
        const res = await fetch(`${BACKEND}/library/quotes?${params}`);
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Failed to load quotes");
        sendResponse({ ok: true, quotes: data.quotes || [] });
      } catch (err) {
        sendResponse({ ok: false, error: String(err) });
      }
    })();
    return true;
  }

  if (message?.type === "QUICK_SAVE_QUOTE") {
    (async () => {
      try {
        const pageUrl = String(message.page_url || "").trim();
        const customTitle = await getCustomTitle(pageUrl);
        const savedMeta = await lookupSavedPage(pageUrl);
        const pageTitle = customTitle || savedMeta?.title || String(message.page_title || "").trim();
        const res = await fetch(`${BACKEND}/library/quotes`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            text: String(message.text || "").trim(),
            note: String(message.note || "").trim(),
            page_id: savedMeta?.id || "",
            page_url: pageUrl,
            page_title: pageTitle,
          }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Save quote failed");
        const quote = data.quote || {
          text: String(message.text || "").trim(),
          note: String(message.note || "").trim(),
        };
        await chrome.storage.session.set({
          quoteSavedAt: Date.now(),
          lastSavedQuote: {
            text: String(quote.text || message.text || "").trim(),
            note: String(quote.note || message.note || "").trim(),
            id: quote.id || "",
            page_url: pageUrl,
          },
        });
        sendResponse({ ok: true, quote });
      } catch (err) {
        sendResponse({ ok: false, error: String(err) });
      }
    })();
    return true;
  }

  if (message?.type === "SELECTION_CHANGED") {
    chrome.storage.session.set({ latestSelection: message.selected || "" });
    return false;
  }

  if (message?.type === "PAGE_NAVIGATED" && _sender.tab?.id) {
    chrome.tabs.query({ active: true, currentWindow: true }, async (tabs) => {
      if (tabs[0]?.id !== _sender.tab.id) return;
      await broadcastActiveTab({
        id: _sender.tab.id,
        url: message.url || _sender.tab.url || "",
        title: message.title || _sender.tab.title || "",
      });
    });
    return false;
  }

  return false;
});

async function setPanelOpen(open) {
  await chrome.storage.session.set({ panelOpen: open });
  const tabs = await chrome.tabs.query({});
  const type = open ? "PANEL_OPENED" : "PANEL_CLOSED";
  await Promise.all(tabs.map((tab) => {
    if (!tab.id || !tab.url || tab.url.startsWith("chrome://") || tab.url.startsWith("edge://")) {
      return Promise.resolve();
    }
    return chrome.tabs.sendMessage(tab.id, { type }).catch(() => {});
  }));
}

async function broadcastActiveTab(tab) {
  const url = tab?.url || "";
  if (!url || url.startsWith("chrome://") || url.startsWith("edge://")) return;
  await chrome.storage.session.set({
    activeTabUrl: url,
    activeTabId: tab.id,
    activeTabTitle: tab.title || "",
  });
  chrome.runtime.sendMessage({
    type: "TAB_CHANGED",
    url,
    tabId: tab.id,
    title: tab.title || "",
  }).catch(() => {});
}

function isPdfUrl(url = "") {
  return /\.pdf($|[?#])/i.test(url);
}

async function getCustomTitle(url) {
  if (!url) return "";
  const key = `customTitle:${url}`;
  const data = await chrome.storage.local.get(key);
  return data[key] || "";
}

async function lookupSavedPage(url) {
  if (!url) return null;
  try {
    const res = await fetch(`${BACKEND}/library/by-url?url=${encodeURIComponent(url)}`);
    const data = await res.json();
    return data.page || null;
  } catch {
    return null;
  }
}

async function getPageContextForTab(tab) {
  const url = tab.url || "";
  if (isPdfUrl(url)) {
    return getPdfPageContext(tab);
  }

  try {
    const [result] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: extractPageContext,
    });
    const page = result?.result || null;
    if (page?.visible_text?.trim()) {
      const customTitle = await getCustomTitle(url);
      if (customTitle) page.title = customTitle;
      return page;
    }
  } catch {
    // Fall through to document extraction for embedded viewers.
  }

  if (isPdfUrl(url)) {
    return getPdfPageContext(tab);
  }
  return null;
}

async function getPdfPageContext(tab) {
  const url = tab.url || "";
  const customTitle = await getCustomTitle(url);
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Could not fetch PDF (${response.status})`);
  }
  const buffer = await response.arrayBuffer();
  const contentBase64 = arrayBufferToBase64(buffer);
  const extractRes = await fetch(`${BACKEND}/library/extract-document`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      url,
      content_base64: contentBase64,
      title: customTitle || tab.title || "",
    }),
  });
  const data = await extractRes.json();
  if (!extractRes.ok) {
    throw new Error(data.error || "PDF extraction failed");
  }
  const page = data.page;
  if (customTitle) page.title = customTitle;
  return page;
}

function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  const chunkSize = 0x8000;
  let binary = "";
  for (let i = 0; i < bytes.length; i += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunkSize));
  }
  return btoa(binary);
}

ensureBackend().catch(() => {});

async function ensureBackend({ maxWaitMs = 45000 } = {}) {
  const deadline = Date.now() + maxWaitMs;
  let delay = 200;
  let attempt = 0;

  while (Date.now() < deadline) {
    if (await isBackendHealthy()) {
      return { ok: true, status: "already_running" };
    }
    await requestLauncherStart();
    await sleep(delay);
    attempt += 1;
    if (attempt < 10) {
      delay = Math.min(delay + 150, 900);
    } else {
      delay = 1000;
    }
  }

  if (await isBackendHealthy()) {
    return { ok: true, status: "already_running" };
  }

  const launcher = await launcherStatus();
  if (!launcher) {
    const nativeResult = await startViaNativeHost();
    if (nativeResult.ok) {
      for (let attempt = 0; attempt < 20; attempt += 1) {
        if (await isBackendHealthy()) {
          return { ok: true, status: nativeResult.status || "started" };
        }
        await sleep(500);
      }
    }

    return {
      ok: false,
      error: "launcher_missing",
      hint: "Run once: node scripts/install-launcher.mjs",
      manual: "Or start manually: python3 main.py",
      extensionId: chrome.runtime.id,
    };
  }

  return {
    ok: false,
    error: "backend_timeout",
    hint: "Check ~/Library/Logs/Context/ or .kb_backend.log in the repo",
    manual: "Try: python3 main.py",
    extensionId: chrome.runtime.id,
  };
}

async function isBackendHealthy() {
  try {
    const res = await fetch(`${BACKEND}/health`, { cache: "no-store" });
    if (!res.ok) return false;
    const health = await res.json();
    return health.ok === true;
  } catch {
    return false;
  }
}

async function requestLauncherStart() {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 2500);
    const response = await fetch(`${LAUNCHER_URL}/start`, {
      method: "POST",
      signal: controller.signal,
    });
    clearTimeout(timeout);
    return response.ok;
  } catch {
    return false;
  }
}

async function launcherStatus() {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 800);
    const response = await fetch(`${LAUNCHER_URL}/status`, { signal: controller.signal });
    clearTimeout(timeout);
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}

function startViaNativeHost() {
  return new Promise((resolve) => {
    let settled = false;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      resolve(result);
    };

    try {
      const port = chrome.runtime.connectNative(NATIVE_HOST);
      port.onMessage.addListener((response) => {
        port.disconnect();
        finish(response || { ok: false, error: "Empty native host response" });
      });
      port.onDisconnect.addListener(() => {
        if (settled) return;
        const message = chrome.runtime.lastError?.message || "Native host disconnected";
        finish({ ok: false, error: message });
      });
      port.postMessage({ action: "start" });
    } catch (err) {
      finish({ ok: false, error: String(err) });
    }
  });
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function extractPageContext() {
  const selected = window.getSelection()?.toString()?.trim() || "";
  const headings = Array.from(document.querySelectorAll("h1,h2,h3,h4,h5,h6"))
    .map((el) => el.textContent?.trim() || "")
    .filter(Boolean)
    .slice(0, 40);
  const paragraphs = Array.from(document.querySelectorAll("p"))
    .map((el) => el.textContent?.trim() || "")
    .filter((text) => text.length > 20)
    .slice(0, 60);
  const codeBlocks = Array.from(document.querySelectorAll("pre,code"))
    .map((el) => el.textContent?.trim() || "")
    .filter((text) => text.length > 0)
    .slice(0, 15);
  const links = Array.from(document.querySelectorAll("a[href]"))
    .map((el) => ({
      text: (el.textContent || "").trim().slice(0, 120),
      href: el.href,
    }))
    .filter((link) => link.text && link.href.startsWith("http"))
    .slice(0, 30);

  const hostname = window.location.hostname || "";
  let pageType = "webpage";
  if (hostname.includes("arxiv.org")) pageType = "research_paper";
  else if (hostname.includes("github.com")) pageType = "code_repository";
  else if (hostname.includes("wikipedia.org")) pageType = "encyclopedia";
  else if (document.querySelector("article")) pageType = "article";

  return {
    url: window.location.href,
    title: document.title || "",
    site: hostname,
    headings,
    paragraphs,
    code_blocks: codeBlocks,
    links,
    images: [],
    tables: [],
    selected_text: selected,
    page_type: pageType,
    visible_text: (document.body?.innerText || "").slice(0, 20000),
  };
}
