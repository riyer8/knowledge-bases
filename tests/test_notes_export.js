const assert = require("assert");
const path = require("path");
const notesPath = path.join(__dirname, "../chrome-extension/sidepanel/notes.js");
const exportPath = path.join(__dirname, "../chrome-extension/sidepanel/bookshelf-export.js");
const ContextNotes = require(notesPath);
const ContextBookshelf = require(exportPath);

const markdown = [
  "> Self-attention allows parallel training",
  "",
  "Worth **rereading** this *claim* and see [the paper](https://example.com/p).",
  "",
  "> Another passage",
].join("\n");

const fenced = ContextNotes.markdownBlockquotesToFences(markdown);
assert.ok(fenced.includes(":::quote\nSelf-attention allows parallel training\n:::"));
assert.ok(fenced.includes("Worth **rereading** this *claim*"));
assert.ok(fenced.includes(":::quote\nAnother passage\n:::"));
assert.strictEqual(
  ContextNotes.fencesToMarkdown(fenced).replace(/\n{3,}/g, "\n\n").trim(),
  markdown.replace(/\n{3,}/g, "\n\n").trim()
);

const html = ContextNotes.markdownToHtml(markdown);
assert.ok(html.includes("custom-quote"));
assert.ok(html.includes("<strong>rereading</strong>"));
assert.ok(html.includes("<em>claim</em>"));
assert.ok(html.includes('href="https://example.com/p"'));

const entry = ContextBookshelf.buildEntry({
  title: "Attention Is All You Need",
  url: "https://example.com/paper",
  author: "Vaswani et al.",
  dateAdded: "2026-09-01",
  category: "science",
  medium: "research paper",
  tldr: "Transformers beat RNNs via self-attention.",
  thoughts: "Still the default architecture.",
  tags: ["ml", "nlp"],
  notes: markdown,
});
assert.strictEqual(entry.notes, fenced);
assert.strictEqual(entry.dateAdded, "2026-09-01");

const formatted = ContextBookshelf.format(entry);
assert.ok(formatted.includes('dateAdded: "2026-09-01"'));
assert.ok(formatted.includes(":::quote"));
assert.ok(formatted.includes("notes: `"));
assert.strictEqual(entry.notes, ContextNotes.markdownBlockquotesToFences(markdown.trim()));

const appended = ContextNotes.appendQuoteToNotes("", {
  text: "Self-attention allows parallel training",
  note: "key idea",
});
assert.ok(ContextNotes.notesContainsQuote(appended, "Self-attention allows parallel training"));
assert.strictEqual(appended, ContextNotes.appendQuoteToNotes(appended, {
  text: "Self-attention allows parallel training",
}));

console.log("notes export round-trip ok");
