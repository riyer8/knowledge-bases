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

  /** Strip emphasis/code/link markup so notes formatting does not change quote identity. */
  function stripInlineMarkdown(text) {
    let s = String(text || "");
    s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, "$1");
    s = s.replace(/\*\*([^*]+)\*\*/g, "$1");
    s = s.replace(/__([^_]+)__/g, "$1");
    s = s.replace(/(^|[^*])\*([^*]+)\*/g, "$1$2");
    s = s.replace(/(^|[^_])_([^_]+)_/g, "$1$2");
    s = s.replace(/`([^`]+)`/g, "$1");
    return s;
  }

  function plainQuoteText(text) {
    return normalizeSelection(stripInlineMarkdown(text));
  }

  /** Identity key for a quote: ignores markdown, case, and punctuation. */
  function quoteMatchKey(text) {
    return plainQuoteText(text)
      .toLowerCase()
      .replace(/[^\p{L}\p{N}\s]+/gu, "")
      .replace(/\s+/g, " ")
      .trim();
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
    // Convert editor `>` quotes to site fences (`:::quote` … `:::`).
    // Do not rewrite lines already inside a :::quote / :::sidenote region
    // (site data sometimes nests `>` inside a fence).
    const lines = String(notes || "").split("\n");
    const out = [];
    let quote = [];
    let fenceKind = null;
    const flush = () => {
      if (!quote.length) return;
      const body = quote.map((line) => line.replace(/^>\s?/, "")).join("\n").trim();
      out.push(`:::quote\n${body}\n:::`);
      quote = [];
    };
    for (const line of lines) {
      const open = line.match(/^:::(quote|sidenote)\s*$/);
      if (open) {
        flush();
        fenceKind = open[1];
        out.push(line);
        continue;
      }
      if (fenceKind && /^:::\s*$/.test(line)) {
        fenceKind = null;
        out.push(line);
        continue;
      }
      if (fenceKind) {
        out.push(line);
        continue;
      }
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
    // Bold before italic so **…** is not eaten by single-star rules.
    html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/__([^_]+)__/g, "<strong>$1</strong>");
    html = html.replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>");
    html = html.replace(/(^|[^_])_([^_]+)_/g, "$1<em>$2</em>");
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
        const parts = [];
        for (const child of Array.from(node.childNodes)) {
          if (child.nodeType === 1) {
            const childTag = child.tagName.toLowerCase();
            if (childTag === "button" || child.hasAttribute("data-delete-quote")) continue;
            if (childTag === "p") {
              const text = serializeNotesInline(child).trim();
              if (text) parts.push(text);
              continue;
            }
          }
          const text = serializeNotesInline(child).replace(/\n{2,}/g, "\n").trim();
          if (text) parts.push(text);
        }
        const text = parts.join("\n").replace(/\n{2,}/g, "\n").trim();
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

  function toQuoteFence(text) {
    const body = String(text || "").trim();
    if (!body) return "";
    return `:::quote\n${body}\n:::`;
  }

  /**
   * Bookshelf export only: blockquotes → :::quote fences, commentary stays plain.
   * Does not change the Notes editor document format.
   */
  function domToExportNotes(root) {
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
      if (tag === "blockquote" || node.classList?.contains?.("custom-quote")) {
        const parts = [];
        for (const child of Array.from(node.childNodes)) {
          if (child.nodeType === 1) {
            const childTag = child.tagName.toLowerCase();
            if (childTag === "button" || child.hasAttribute("data-delete-quote")) continue;
            if (childTag === "p") {
              const text = serializeNotesInline(child).trim();
              if (text) parts.push(text);
              continue;
            }
          }
          const text = serializeNotesInline(child).replace(/\n{2,}/g, "\n").trim();
          if (text) parts.push(text);
        }
        const text = parts.join("\n").replace(/\n{2,}/g, "\n").trim();
        const fence = toQuoteFence(text);
        if (fence) blocks.push(fence);
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
          /^(p|div|blockquote|ul|ol|h1|h2|h3|pre)$/i.test(el.tagName) ||
          el.classList?.contains?.("custom-quote")
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
    const needle = quoteMatchKey(text);
    if (!needle) return false;
    return markdownQuoteBodies(notes).some((body) => quoteMatchKey(body) === needle);
  }

  function quoteBlockRange(notes, text) {
    const needle = quoteMatchKey(text);
    if (!needle) return null;
    const re = /:::(?:quote|sidenote)\s*\n?([\s\S]*?)\s*:::/g;
    let match;
    while ((match = re.exec(String(notes || "")))) {
      if (quoteMatchKey(match[1]) !== needle) continue;
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
        if (quoteMatchKey(body.join("\n")) === needle) {
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
    // Only consume when the note is its own paragraph (end or newline), never a prefix.
    if (trailing && !trailing.startsWith("\n")) return fenceEnd;
    const firstLine = rest.split(/\r?\n/, 1)[0];
    if (firstLine !== trimmedNote) return fenceEnd;
    return fenceEnd + lead + trimmedNote.length;
  }

  function appendQuoteToNotes(notes, quote) {
    if (notesContainsQuote(notes, quote?.text)) return notes;
    const snippet = quoteNotesSnippet(quote);
    return String(notes || "").trim() ? `${String(notes).trim()}\n\n${snippet}` : snippet;
  }

  function removeQuoteFromNotes(notes, quote) {
    const source = String(notes || "");
    if (!source.trim()) return source;
    const range = quoteBlockRange(source, quote?.text);
    if (!range) return source;
    const end = consumeFollowingNote(source, range.end, quote?.note);
    return `${source.slice(0, range.start)}${source.slice(end)}`
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
    const byKey = new Map();
    for (const quote of records || []) {
      const key = quoteMatchKey(quote?.text);
      if (!key) continue;
      byKey.set(key, quote);
    }
    const bodies = markdownQuoteBodies(notes);
    const seen = new Set();
    const out = [];
    for (const body of bodies) {
      const key = quoteMatchKey(body);
      if (!key || seen.has(key)) continue;
      seen.add(key);
      const rec = byKey.get(key);
      out.push({
        id: rec?.id || "",
        // Prefer the library quote (page selection). Notes may add bold/italic
        // or punctuation that is not present on the webpage.
        text: rec?.text || plainQuoteText(body),
        note: rec?.note || "",
      });
    }
    // Notes are the source of truth: quotes removed from notes are not painted.
    return out;
  }

  const ContextNotes = {
    escapeHtml,
    normalizeSelection,
    stripInlineMarkdown,
    plainQuoteText,
    quoteMatchKey,
    toMarkdownBlockquote,
    fencesToMarkdown,
    markdownBlockquotesToFences,
    quoteNotesSnippet,
    renderNotesInline,
    markdownToHtml,
    htmlToMarkdown,
    domToExportNotes,
    toQuoteFence,
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
