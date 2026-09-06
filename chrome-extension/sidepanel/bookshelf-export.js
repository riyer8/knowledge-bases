(function (root) {
  function todayDateAdded(now = new Date()) {
    const date = now instanceof Date ? now : new Date(now);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  function normalizeTags(raw) {
    const tags = [];
    const source = Array.isArray(raw) ? raw : [];
    for (const item of source) {
      const tag = String(item || "").trim();
      if (tag && !tags.some((existing) => existing.toLowerCase() === tag.toLowerCase())) {
        tags.push(tag);
      }
    }
    return tags.slice(0, 40);
  }

  function escapeTemplateLiteral(text) {
    return String(text || "")
      .replace(/\\/g, "\\\\")
      .replace(/`/g, "\\`")
      .replace(/\$\{/g, "\\${");
  }

  function formatNotesLiteral(notes) {
    if (!notes) return "``";
    return `\`${escapeTemplateLiteral(notes)}\``;
  }

  function formatTagsLiteral(tags) {
    const list = normalizeTags(tags);
    if (!list.length) return "['']";
    return `[${list
      .map((tag) => `'${String(tag).replace(/\\/g, "\\\\").replace(/'/g, "\\'")}'`)
      .join(", ")}]`;
  }

  /** Fallback if ContextNotes is unavailable (stale panel / load-order race). */
  function blockquotesToFencesFallback(notes) {
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

  function getNotesApi() {
    if (root.ContextNotes) return root.ContextNotes;
    if (typeof require === "function") {
      try {
        return require("./notes.js");
      } catch {
        return null;
      }
    }
    return null;
  }

  function toExportNotes(rawNotes) {
    const trimmed = String(rawNotes || "").trim();
    if (!trimmed) return "";
    const Notes = getNotesApi();
    if (Notes?.markdownBlockquotesToFences) {
      return Notes.markdownBlockquotesToFences(trimmed);
    }
    return blockquotesToFencesFallback(trimmed);
  }

  function buildEntry(fields) {
    return {
      title: String(fields?.title || "").trim(),
      url: String(fields?.url || "").trim(),
      author: String(fields?.author || "").trim(),
      dateAdded: String(fields?.dateAdded || "").trim() || todayDateAdded(),
      category: String(fields?.category || "").trim(),
      medium: String(fields?.medium || "").trim(),
      tldr: String(fields?.tldr || "").trim(),
      thoughts: String(fields?.thoughts || "").trim(),
      tags: normalizeTags(fields?.tags),
      notes: toExportNotes(fields?.notes),
    };
  }

  function format(entry) {
    // Normalize through buildEntry so notes always use :::quote fences.
    const value = buildEntry(entry && typeof entry === "object" ? entry : {});
    return `{
    title: ${JSON.stringify(value.title || "")},
    url: ${JSON.stringify(value.url || "")},
    author: ${JSON.stringify(value.author || "")},
    dateAdded: ${JSON.stringify(value.dateAdded || todayDateAdded())},
    category: ${JSON.stringify(value.category || "")},
    medium: ${JSON.stringify(value.medium || "")},
    tldr: ${JSON.stringify(value.tldr || "")},
    thoughts: ${JSON.stringify(value.thoughts || "")},
    tags: ${formatTagsLiteral(value.tags || [])},
    notes: ${formatNotesLiteral(value.notes || "")}
  }`;
  }

  const ContextBookshelf = {
    todayDateAdded,
    normalizeTags,
    buildEntry,
    format,
    toExportNotes,
  };

  root.ContextBookshelf = ContextBookshelf;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = ContextBookshelf;
  }
})(typeof globalThis !== "undefined" ? globalThis : self);
