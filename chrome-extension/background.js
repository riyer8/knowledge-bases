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

  if (message?.type === "REMEMBER_SELECTION") {
    saveQuoteFromPage(message.page, message.selected_text, message.note || "")
      .then(sendResponse)
      .catch((err) => sendResponse({ ok: false, error: String(err) }));
    return true;
  }
  return false;
});

async function ensureBackend() {
  if (await isBackendHealthy()) {
    return { ok: true, status: "already_running" };
  }

  const nativeResult = await startViaNativeHost();
  if (!nativeResult.ok) {
    return nativeResult;
  }

  for (let attempt = 0; attempt < 20; attempt += 1) {
    if (await isBackendHealthy()) {
      return { ok: true, status: nativeResult.status || "started" };
    }
    await sleep(500);
  }

  return {
    ok: false,
    error: "Backend did not become ready. Check .kb_backend.log in the repo.",
  };
}

async function isBackendHealthy() {
  try {
    const res = await fetch(`${BACKEND}/health`, { cache: "no-store" });
    return res.ok;
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
        finish({
          ok: false,
          error: `${message}. Run: bash chrome-extension/install-native-host.sh <extension-id>`,
        });
      });
      port.postMessage({ action: "start" });
    } catch (err) {
      finish({
        ok: false,
        error: `${err}. Run: bash chrome-extension/install-native-host.sh <extension-id>`,
      });
    }
  });
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function saveQuoteFromPage(page, selectedText, note = "") {
  const ready = await ensureBackend();
  if (!ready.ok) return ready;

  let pageId = "";
  if (page?.url) {
    const lookup = await fetch(`${BACKEND}/library/by-url?url=${encodeURIComponent(page.url)}`);
    const lookupData = await lookup.json();
    pageId = lookupData.page?.id || "";
  }

  const quoteRes = await fetch(`${BACKEND}/library/quotes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text: selectedText,
      page_id: pageId,
      page_url: page?.url || "",
      page_title: page?.title || "",
      note,
    }),
  });
  const quoteData = await quoteRes.json();
  if (!quoteRes.ok) throw new Error(quoteData.error || "Save quote failed");
  chrome.storage.session.set({ quoteSavedAt: Date.now() });
  chrome.runtime.sendMessage({ type: "QUOTE_SAVED" }).catch(() => {});
  return { ok: true, quote: quoteData.quote };
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
