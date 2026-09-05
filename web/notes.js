(function (root) {
  function escapeHtml(text) {
    return String(text || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function normalizeSelection(text) {
    return String(text || "").replace(/\s+/g, " ").trim();
  }

  function toMarkdownBlockquote(text) {
    const body = String(text || "").trim();
    if (!body) return "";
    return body.split("\n").map((line) => (line.length ? `> ${line}` : ">")).join("\n");
  }

  function fencesToMarkdown(notes) {
    return String(notes || "").replace(
      /:::(quote|sidenote)\s*\n?([\s\S]*?)\s*:::/g,
      (_, _kind, body) => toMarkdownBlockquote(body)
    );
  }

  function markdownBlockquotesToFences(notes) {
    const lines = String(notes || "").split("\n");
    const out = [];
    let quote = [];
    const flush = () => {
      if (!quote.length) return;
      const body = quote.map((line) => line.replace(/^>\s?/, "")).join("\n").trim();
      out.push(`:::quote\n${body}\n:::`);
      quote = [];
    };
    for (const line of lines) {
      if (/^>/.test(line)) quote.push(line);
      else {
        flush();
        out.push(line);
      }
    }
    flush();
    return out.join("\n").replace(/\n{3,}/g, "\n\n").trim();
  }

  function quoteNotesSnippet(quote) {
    const block = toMarkdownBlockquote(quote?.text);
    const note = String(quote?.note || "").trim();
    return note ? `${block}\n\n${note}` : block;
  }

  function renderNotesInline(text) {
    let html = escapeHtml(String(text || ""));
    html = html.replace(
      /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g,
      '<a href="$2">$1</a>'
    );
    html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>");
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
    return html.replace(/\n/g, "<br>");
  }

  function markdownToHtml(markdown) {
    const source = fencesToMarkdown(String(markdown || "")).replace(/\r\n/g, "\n");
    if (!source.trim()) return "";
    const parts = [];
    let paragraph = [];
    let quote = [];
    const flushParagraph = () => {
      const text = paragraph.join("\n").trim();
      paragraph = [];
      if (text) parts.push(`<p>${renderNotesInline(text)}</p>`);
    };
    const flushQuote = () => {
      const text = quote.join("\n").trim();
      quote = [];
      if (text) {
        parts.push(`<blockquote class="custom-quote"><p>${renderNotesInline(text)}</p></blockquote>`);
      }
    };
    for (const line of source.split("\n")) {
      if (/^>/.test(line)) {
        flushParagraph();
        quote.push(line.replace(/^>\s?/, ""));
        continue;
      }
      if (!line.trim()) {
        flushQuote();
        flushParagraph();
        continue;
      }
      flushQuote();
      paragraph.push(line);
    }
    flushQuote();
    flushParagraph();
    return parts.join("");
  }

  function serializeNotesInline(node) {
    if (!node) return "";
    if (node.nodeType === 3) {
      return String(node.nodeValue || "").replace(/\u00a0/g, " ");
    }
    if (node.nodeType !== 1) return "";
    const tag = node.tagName.toLowerCase();
    if (tag === "br") return "\n";
    if (tag === "button" || node.hasAttribute("data-delete-quote")) return "";
    const inner = Array.from(node.childNodes).map(serializeNotesInline).join("");
    if (tag === "strong" || tag === "b") return inner ? `**${inner}**` : "";
    if (tag === "em" || tag === "i") return inner ? `*${inner}*` : "";
    if (tag === "code") return inner ? `\`${inner}\`` : "";
    if (tag === "a") {
      const href = node.getAttribute("href") || "";
      return href && inner ? `[${inner}](${href})` : inner;
    }
    return inner;
  }

  function htmlToMarkdown(root) {
    if (!root) return "";
    const blocks = [];
    const walk = (node) => {
      if (node.nodeType === 3) {
        const text = String(node.nodeValue || "").replace(/\u00a0/g, " ").trim();
        if (text) blocks.push(text);
        return;
      }
      if (node.nodeType !== 1) return;
      const tag = node.tagName.toLowerCase();
      if (tag === "blockquote") {
        const text = serializeNotesInline(node).replace(/\n{2,}/g, "\n").trim();
        if (text) blocks.push(toMarkdownBlockquote(text));
        return;
      }
      if (tag === "ul" || tag === "ol") {
        const items = Array.from(node.children)
          .filter((el) => el.tagName.toLowerCase() === "li")
          .map((li) => `- ${serializeNotesInline(li).trim()}`)
          .filter((item) => item !== "-");
        if (items.length) blocks.push(items.join("\n"));
        return;
      }
      if (/^h[1-3]$/.test(tag)) {
        const text = serializeNotesInline(node).trim();
        if (text) blocks.push(`${"#".repeat(Number(tag[1]))} ${text}`);
        return;
      }
      if (tag === "p") {
        const text = serializeNotesInline(node).trim();
        if (text) blocks.push(text);
        return;
      }
      if (tag === "div") {
        const hasBlock = Array.from(node.children).some((el) =>
          /^(p|div|blockquote|ul|ol|h1|h2|h3|pre)$/i.test(el.tagName)
        );
        if (hasBlock) Array.from(node.childNodes).forEach(walk);
        else {
          const text = serializeNotesInline(node).trim();
          if (text) blocks.push(text);
        }
        return;
      }
      Array.from(node.childNodes).forEach(walk);
    };
    Array.from(root.childNodes).forEach(walk);
    return blocks.join("\n\n").replace(/\n{3,}/g, "\n\n").trim();
  }

  function markdownQuoteBodies(notes) {
    const bodies = [];
    const lines = fencesToMarkdown(String(notes || "")).split("\n");
    let body = [];
    const flush = () => {
      if (!body.length) return;
      bodies.push(body.join("\n"));
      body = [];
    };
    for (const line of lines) {
      if (/^>/.test(line)) body.push(line.replace(/^>\s?/, ""));
      else flush();
    }
    flush();
    return bodies;
  }

  function notesContainsQuote(notes, text) {
    const needle = normalizeSelection(text);
    if (!needle) return false;
    return markdownQuoteBodies(notes).some((body) => normalizeSelection(body) === needle);
  }

  function quoteBlockRange(notes, text) {
    const needle = normalizeSelection(text);
    if (!needle) return null;
    const re = /:::(?:quote|sidenote)\s*\n?([\s\S]*?)\s*:::/g;
    let match;
    while ((match = re.exec(String(notes || "")))) {
      if (normalizeSelection(match[1]) !== needle) continue;
      return { start: match.index, end: match.index + match[0].length };
    }
    const source = String(notes || "");
    const lines = source.split("\n");
    let idx = 0;
    let startIdx = -1;
    let body = [];
    for (let i = 0; i <= lines.length; i += 1) {
      const line = i < lines.length ? lines[i] : null;
      const isQuote = line !== null && /^>/.test(line);
      if (isQuote) {
        if (startIdx < 0) startIdx = idx;
        body.push(line.replace(/^>\s?/, ""));
      } else if (startIdx >= 0) {
        if (normalizeSelection(body.join("\n")) === needle) {
          return { start: startIdx, end: idx };
        }
        startIdx = -1;
        body = [];
      }
      if (line !== null) idx += line.length + 1;
    }
    return null;
  }

  function consumeFollowingNote(notes, fenceEnd, note) {
    const trimmedNote = String(note || "").trim();
    if (!trimmedNote) return fenceEnd;
    const after = notes.slice(fenceEnd);
    const lead = after.match(/^\s*/)?.[0].length || 0;
    const rest = after.slice(lead);
    if (!rest.startsWith(trimmedNote)) return fenceEnd;
    const trailing = rest.slice(trimmedNote.length);
    if (trailing && !trailing.startsWith("\n")) return fenceEnd;
    return fenceEnd + lead + trimmedNote.length;
  }

  function appendQuoteToNotes(notes, quote) {
    if (notesContainsQuote(notes, quote?.text)) return notes;
    const snippet = quoteNotesSnippet(quote);
    return String(notes || "").trim() ? `${String(notes).trim()}\n\n${snippet}` : snippet;
  }

  function removeQuoteFromNotes(notes, quote) {
    const range = quoteBlockRange(notes, quote?.text);
    if (!range) return notes;
    const end = consumeFollowingNote(notes, range.end, quote?.note);
    return `${notes.slice(0, range.start)}${notes.slice(end)}`
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  }

  function replaceQuoteInNotes(notes, previous, next) {
    const range = quoteBlockRange(notes, previous?.text);
    if (!range) return next ? appendQuoteToNotes(notes, next) : notes;
    const end = consumeFollowingNote(notes, range.end, previous?.note);
    const replacement = next ? quoteNotesSnippet(next) : "";
    const before = notes.slice(0, range.start).trimEnd();
    const after = notes.slice(end).trimStart();
    return [before, replacement, after].filter(Boolean).join("\n\n").replace(/\n{3,}/g, "\n\n").trim();
  }

  function quotesForHighlights(notes, records) {
    const byText = new Map();
    for (const quote of records || []) {
      const text = normalizeSelection(quote?.text);
      if (!text) continue;
      byText.set(text, quote);
    }
    const bodies = markdownQuoteBodies(notes);
    if (!bodies.length) {
      return (records || []).map((quote) => ({
        id: quote.id || "",
        text: quote.text,
        note: quote.note || "",
      }));
    }
    return bodies.map((body) => {
      const text = normalizeSelection(body);
      const rec = byText.get(text);
      return {
        id: rec?.id || "",
        text: rec?.text || body.trim(),
        note: rec?.note || "",
      };
    });
  }

  const ContextNotes = {
    escapeHtml,
    normalizeSelection,
    toMarkdownBlockquote,
    fencesToMarkdown,
    markdownBlockquotesToFences,
    quoteNotesSnippet,
    renderNotesInline,
    markdownToHtml,
    htmlToMarkdown,
    markdownQuoteBodies,
    notesContainsQuote,
    quoteBlockRange,
    appendQuoteToNotes,
    removeQuoteFromNotes,
    replaceQuoteInNotes,
    quotesForHighlights,
  };

  root.ContextNotes = ContextNotes;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = ContextNotes;
  }
})(typeof globalThis !== "undefined" ? globalThis : self);
