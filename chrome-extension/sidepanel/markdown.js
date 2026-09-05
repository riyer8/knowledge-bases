/** Lightweight markdown → HTML (escape-first, no external deps). */
(function (global) {
  function escapeHtml(text) {
    return String(text || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function inlineMarkdown(text) {
    let html = text;
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
    html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/\*([^*]+)\*/g, "<em>$1</em>");
    html = html.replace(
      /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
    );
    html = html.replace(
      /\[\[([^\]]+)\]\]/g,
      '<a href="#" data-wikilink="$1">$1</a>'
    );
    return html;
  }

  /** Split mid-paragraph "1. **Title** … 2. **Title**" into real list lines. */
  function normalizeLooseLists(text) {
    return String(text || "")
      .replace(/\r\n/g, "\n")
      .replace(/\s+(\d{1,2})\.\s+(?=\*\*|\[|"|“|‘)/g, "\n$1. ");
  }

  function renderMarkdown(text) {
    if (!text) return "";
    const codeBlocks = [];
    let src = normalizeLooseLists(text);

    src = src.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
      const idx = codeBlocks.length;
      const langClass = lang ? ` class="language-${escapeHtml(lang)}"` : "";
      codeBlocks.push(`<pre><code${langClass}>${escapeHtml(code.trim())}</code></pre>`);
      return `\x00CODE${idx}\x00`;
    });

    src = escapeHtml(src);
    const lines = src.split("\n");
    const blocks = [];
    let paragraph = [];
    let listItems = [];
    let listType = null;
    let inBlockquote = false;
    let quoteLines = [];

    function flushParagraph() {
      if (!paragraph.length) return;
      blocks.push(`<p>${inlineMarkdown(paragraph.join("<br>"))}</p>`);
      paragraph = [];
    }

    function flushList() {
      if (!listItems.length) return;
      const tag = listType === "ol" ? "ol" : "ul";
      blocks.push(`<${tag}>${listItems.map((li) => `<li>${inlineMarkdown(li)}</li>`).join("")}</${tag}>`);
      listItems = [];
      listType = null;
    }

    function flushBlockquote() {
      if (!quoteLines.length) return;
      blocks.push(`<blockquote>${inlineMarkdown(quoteLines.join("<br>"))}</blockquote>`);
      quoteLines = [];
      inBlockquote = false;
    }

    function pushListItem(type, body) {
      flushParagraph();
      flushBlockquote();
      if (listType && listType !== type) flushList();
      listType = type;
      listItems.push(body);
    }

    for (const rawLine of lines) {
      const line = rawLine.trimEnd();
      const trimmed = line.trim();

      if (!trimmed) {
        flushParagraph();
        flushList();
        flushBlockquote();
        continue;
      }

      if (/^\x00CODE\d+\x00$/.test(trimmed)) {
        flushParagraph();
        flushList();
        flushBlockquote();
        blocks.push(trimmed);
        continue;
      }

      const heading = trimmed.match(/^(#{1,3})\s+(.+)$/);
      if (heading) {
        flushParagraph();
        flushList();
        flushBlockquote();
        const level = heading[1].length;
        blocks.push(`<h${level}>${inlineMarkdown(heading[2])}</h${level}>`);
        continue;
      }

      if (trimmed.startsWith("&gt; ")) {
        flushParagraph();
        flushList();
        inBlockquote = true;
        quoteLines.push(trimmed.slice(5));
        continue;
      }

      if (inBlockquote && !trimmed.startsWith("&gt; ")) {
        flushBlockquote();
      }

      const unordered = trimmed.match(/^[-*]\s+(.+)$/);
      if (unordered) {
        pushListItem("ul", unordered[1]);
        continue;
      }

      const ordered = trimmed.match(/^\d{1,3}\.\s+(.+)$/);
      if (ordered) {
        pushListItem("ol", ordered[1]);
        continue;
      }

      flushList();
      paragraph.push(trimmed);
    }

    flushParagraph();
    flushList();
    flushBlockquote();

    let html = blocks.join("\n");
    html = html.replace(/\x00CODE(\d+)\x00/g, (_, idx) => codeBlocks[Number(idx)] || "");
    return html;
  }

  global.escapeHtml = escapeHtml;
  global.renderMarkdown = renderMarkdown;
})(typeof window !== "undefined" ? window : globalThis);
