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

let rememberButton = null;
let hideTimer = null;

document.addEventListener("mouseup", () => {
  window.setTimeout(updateSelectionUi, 10);
});

document.addEventListener("keyup", () => {
  window.setTimeout(updateSelectionUi, 10);
});

function updateSelectionUi() {
  const selected = window.getSelection()?.toString()?.trim() || "";
  chrome.runtime.sendMessage({ type: "SELECTION_CHANGED", selected });

  if (!selected || selected.length < 8) {
    hideRememberButton();
    return;
  }
  showRememberButton(selected);
}

function showRememberButton(selected) {
  const selection = window.getSelection();
  if (!selection || selection.rangeCount === 0) {
    hideRememberButton();
    return;
  }
  const range = selection.getRangeAt(0);
  const rect = range.getBoundingClientRect();
  if (!rect.width && !rect.height) {
    hideRememberButton();
    return;
  }

  if (!rememberButton) {
    rememberButton = document.createElement("button");
    rememberButton.id = "context-remember-btn";
    rememberButton.textContent = "Save quote";
    rememberButton.addEventListener("mousedown", (event) => event.preventDefault());
    rememberButton.addEventListener("click", async (event) => {
      event.stopPropagation();
      const text = window.getSelection()?.toString()?.trim() || selected;
      chrome.runtime.sendMessage({
        type: "REMEMBER_SELECTION",
        selected_text: text,
        page: buildPageContext(),
      });
      hideRememberButton();
      flashRememberButton("Quote saved ✓");
    });
    document.body.appendChild(rememberButton);
  }

  const top = window.scrollY + rect.top - 42;
  const left = window.scrollX + rect.left + rect.width / 2;
  rememberButton.style.top = `${Math.max(8, top)}px`;
  rememberButton.style.left = `${Math.max(8, left)}px`;
  rememberButton.style.display = "block";
  rememberButton.dataset.selected = selected;

  clearTimeout(hideTimer);
  hideTimer = setTimeout(hideRememberButton, 8000);
}

function hideRememberButton() {
  if (rememberButton) {
    rememberButton.style.display = "none";
  }
}

function flashRememberButton(label) {
  if (!rememberButton) return;
  rememberButton.textContent = label;
  rememberButton.style.display = "block";
  setTimeout(hideRememberButton, 1200);
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
