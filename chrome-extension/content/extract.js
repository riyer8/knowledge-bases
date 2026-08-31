chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === "PAGE_CONTEXT") {
    sendResponse({ page: buildPageContext() });
    return true;
  }
  if (message?.type === "GET_SELECTION") {
    sendResponse({ selected: window.getSelection()?.toString()?.trim() || "" });
    return true;
  }
  return false;
});

// Track selection for the side panel only — no on-page save UI.
document.addEventListener("mouseup", () => {
  window.setTimeout(notifySelection, 10);
});

document.addEventListener("keyup", () => {
  window.setTimeout(notifySelection, 10);
});

function notifySelection() {
  const selected = window.getSelection()?.toString()?.trim() || "";
  chrome.runtime.sendMessage({ type: "SELECTION_CHANGED", selected });
}

function buildPageContext() {
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
    .filter(Boolean)
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
