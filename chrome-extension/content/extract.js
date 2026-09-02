// Selection + navigation are handled in highlights.js (floating toolbar + on-page marks).
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

function buildPageContext() {
  const selected = window.getSelection()?.toString()?.trim() || "";
  const metadata = extractMetadataFromDom();
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
  if (/\.pdf($|[?#])/i.test(window.location.href)) pageType = "pdf";
  else if (hostname.includes("arxiv.org")) pageType = "research_paper";
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
    metadata,
  };
}

function extractMetadataFromDom() {
  const author =
    metaContent("author") ||
    metaContent("article:author") ||
    metaContent("dc.creator") ||
    metaContent("citation_author") ||
    bylineText();
  const date =
    metaContent("article:published_time") ||
    metaContent("date") ||
    metaContent("dc.date") ||
    metaContent("citation_publication_date") ||
    timeDatetime();
  const custom = [];
  const journal = metaContent("citation_journal_title");
  if (journal) custom.push({ key: "Journal", value: journal });
  const keywords = metaContent("keywords");
  if (keywords) custom.push({ key: "Keywords", value: keywords.slice(0, 200) });
  return { author: author || "", date: date || "", custom };
}

function metaContent(name) {
  const byName = document.querySelector(`meta[name="${CSS.escape(name)}"]`);
  if (byName?.content) return byName.content.trim();
  const byProp = document.querySelector(`meta[property="${CSS.escape(name)}"]`);
  return byProp?.content?.trim() || "";
}

function bylineText() {
  const el = document.querySelector(
    '[rel="author"], .author, .byline, [itemprop="author"]'
  );
  return el?.textContent?.trim().slice(0, 120) || "";
}

function timeDatetime() {
  const el = document.querySelector("time[datetime]");
  return el?.getAttribute("datetime")?.trim() || el?.textContent?.trim() || "";
}
