const BACKEND = "http://127.0.0.1:8765";
const NATIVE_HOST = "com.context.backend";

chrome.runtime.onInstalled.addListener(() => {
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });
});

chrome.tabs.onUpdated.addListener(async (tabId, info, tab) => {
  if (!tab.url || info.status !== "complete") return;
  if (tab.url.startsWith("chrome://") || tab.url.startsWith("edge://")) return;
  await chrome.sidePanel.setOptions({ tabId, path: "sidepanel/index.html", enabled: true });
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

  if (message?.type === "GET_PAGE_CONTEXT") {
    chrome.tabs.query({ active: true, currentWindow: true }, async (tabs) => {
      const tab = tabs[0];
      if (!tab?.id) {
        sendResponse({ error: "No active tab" });
        return;
      }
      try {
        const [result] = await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          func: extractPageContext,
        });
        sendResponse({ page: result?.result || null });
      } catch (err) {
        sendResponse({ error: String(err) });
      }
    });
    return true;
  }

  if (message?.type === "SELECTION_CHANGED") {
    chrome.storage.session.set({ latestSelection: message.selected || "" });
    return false;
  }

  return false;
});

async function ensureBackend() {
  if (await isBackendHealthy()) {
    return { ok: true, status: "already_running" };
  }

  const nativeResult = await startViaNativeHost();
  if (nativeResult.ok) {
    for (let attempt = 0; attempt < 20; attempt += 1) {
      if (await isBackendHealthy()) {
        return { ok: true, status: nativeResult.status || "started" };
      }
      await sleep(500);
    }
    return {
      ok: false,
      error: "Backend started but did not respond. Check .kb_backend.log in the repo.",
    };
  }

  if (await isBackendHealthy()) {
    return { ok: true, status: "already_running" };
  }

  const extId = chrome.runtime.id;
  if (String(nativeResult.error || "").toLowerCase().includes("forbidden")) {
    return {
      ok: false,
      error: "native_host_forbidden",
      extensionId: extId,
      hint: `Run: bash chrome-extension/install-native-host.sh ${extId}`,
      manual: "Or start the backend manually: python3 main.py",
    };
  }

  return {
    ...nativeResult,
    extensionId: extId,
    hint: `Run: bash chrome-extension/install-native-host.sh ${extId}`,
    manual: "Or start the backend manually: python3 main.py",
  };
}

async function isBackendHealthy() {
  try {
    const res = await fetch(`${BACKEND}/health`, { cache: "no-store" });
    if (!res.ok) return false;
    const health = await res.json();
    return health.ok === true || health.api_version >= 1;
  } catch {
    return false;
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
