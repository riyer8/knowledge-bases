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

const fromEditor = ContextBookshelf.format(
  ContextBookshelf.buildEntry({
    title: "T",
    url: "https://example.com",
    dateAdded: "2026-09-05",
    notes: [
      "> Hello **bold** quote",
      "",
      "Commentary with *italic*.",
      "",
      "> Second quote",
    ].join("\n"),
  })
);
assert.ok(fromEditor.includes("notes: `:::quote\nHello **bold** quote\n:::"));
assert.ok(fromEditor.includes(":::quote\nSecond quote\n:::"));
assert.ok(fromEditor.includes("Commentary with *italic*."));
assert.ok(!fromEditor.includes("> Hello"));

const appended = ContextNotes.appendQuoteToNotes("", {
  text: "Self-attention allows parallel training",
  note: "key idea",
});
assert.ok(ContextNotes.notesContainsQuote(appended, "Self-attention allows parallel training"));
assert.strictEqual(appended, ContextNotes.appendQuoteToNotes(appended, {
  text: "Self-attention allows parallel training",
}));

// Bold / italic / punctuation in the notes quote must not break identity or page paint text.
const formattedQuoteNotes = [
  "> Self-attention **allows** parallel training!",
  "",
  "my note",
].join("\n");
assert.ok(
  ContextNotes.notesContainsQuote(formattedQuoteNotes, "Self-attention allows parallel training")
);
assert.strictEqual(
  ContextNotes.quoteMatchKey("Self-attention **allows** parallel training!"),
  ContextNotes.quoteMatchKey("Self-attention allows parallel training")
);
const highlightPayload = ContextNotes.quotesForHighlights(formattedQuoteNotes, [
  {
    id: "q1",
    text: "Self-attention allows parallel training",
    note: "key idea",
  },
]);
assert.strictEqual(highlightPayload.length, 1);
assert.strictEqual(highlightPayload[0].id, "q1");
assert.strictEqual(highlightPayload[0].text, "Self-attention allows parallel training");
assert.strictEqual(highlightPayload[0].note, "key idea");
assert.strictEqual(
  ContextNotes.plainQuoteText("Self-attention **allows** parallel training!"),
  "Self-attention allows parallel training!"
);

// Multi-paragraph blockquotes must serialize with newlines (Enter inside a quote).
function mockText(value) {
  return { nodeType: 3, nodeValue: value };
}
function mockEl(tag, children = [], attrs = {}) {
  return {
    nodeType: 1,
    tagName: String(tag).toUpperCase(),
    childNodes: children,
    hasAttribute: (name) => Object.prototype.hasOwnProperty.call(attrs, name),
    getAttribute: (name) => (Object.prototype.hasOwnProperty.call(attrs, name) ? attrs[name] : null),
  };
}
const multiRoot = mockEl("div", [
  mockEl("blockquote", [
    mockEl("p", [mockText("First line")]),
    mockEl("p", [mockText("Second line")]),
    mockEl("button", [mockText("×")], { "data-delete-quote": "1" }),
  ]),
]);
const multiMd = ContextNotes.htmlToMarkdown(multiRoot);
assert.ok(multiMd.includes("> First line"));
assert.ok(multiMd.includes("> Second line"));
assert.ok(!multiMd.includes("First lineSecond line"));

// Saved quotes still paint when notes temporarily omit the last blockquote body.
const partialNotes = "> Older quote only";
const unionHighlights = ContextNotes.quotesForHighlights(partialNotes, [
  { id: "old", text: "Older quote only", note: "" },
  { id: "new", text: "Newest quote on page", note: "keep me" },
]);
assert.strictEqual(unionHighlights.length, 2);
assert.ok(unionHighlights.some((item) => item.id === "new" && item.text === "Newest quote on page"));

console.log("notes export round-trip ok");
