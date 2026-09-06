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
assert.ok(fromEditor.includes("notes: `\n:::quote\nHello **bold** quote\n:::"));
assert.ok(fromEditor.includes(":::quote\nSecond quote\n:::"));
assert.ok(fromEditor.includes("Commentary with *italic*."));
assert.ok(!fromEditor.includes("> Hello"));

// Exporter must fence even when raw editor markdown uses > blockquotes.
const rawEditorNotes = [
  "> Hardware is bound by compute, bandwidth, and memory",
  "",
  "My commentary.",
  "",
  "> Arithmetic intensity is FLOPs per byte",
].join("\n");
const fencedExport = ContextBookshelf.format(
  ContextBookshelf.buildEntry({
    title: "Rooflines",
    url: "https://example.com/roofline",
    dateAdded: "2026-09-05",
    notes: rawEditorNotes,
  })
);
assert.ok(fencedExport.includes(":::quote\nHardware is bound by compute, bandwidth, and memory\n:::"));
assert.ok(fencedExport.includes(":::quote\nArithmetic intensity is FLOPs per byte\n:::"));
assert.ok(fencedExport.includes("My commentary."));
assert.ok(!/^>/m.test(fencedExport.split("notes:")[1] || ""), "exported notes must not keep raw > quotes");
assert.strictEqual(
  ContextBookshelf.toExportNotes(rawEditorNotes),
  ContextNotes.markdownBlockquotesToFences(rawEditorNotes)
);

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

// Bookshelf export: blockquotes become :::quote fences; commentary stays plain.
const exportRoot = mockEl("div", [
  mockEl("blockquote", [
    mockEl("p", [mockText("Hardware is bound by compute")]),
    mockEl("button", [mockText("×")], { "data-delete-quote": "1" }),
  ]),
  mockEl("p", [mockText("My independent commentary.")]),
  mockEl("blockquote", [
    mockEl("p", [mockText("Arithmetic intensity is FLOPs per byte")]),
  ]),
]);
const exportNotes = ContextNotes.domToExportNotes(exportRoot);
assert.strictEqual(
  exportNotes,
  [
    ":::quote",
    "Hardware is bound by compute",
    ":::",
    "",
    "My independent commentary.",
    "",
    ":::quote",
    "Arithmetic intensity is FLOPs per byte",
    ":::",
  ].join("\n")
);
const pasteReady = ContextBookshelf.format(
  ContextBookshelf.buildEntry({
    title: "Rooflines",
    url: "https://example.com/roofline",
    dateAdded: "2026-09-05",
    notes: exportNotes,
  })
);
assert.ok(pasteReady.includes("notes: `\n:::quote\nHardware is bound by compute\n:::"));
assert.ok(pasteReady.includes("My independent commentary."));
assert.ok(!pasteReady.includes("> Hardware"));

// Site-style: do not re-fence `>` lines that already sit inside :::quote.
const siteMixed = [
  ":::quote",
  "Outer quote body",
  "> nested markdown quote left alone",
  ":::",
  "",
  "My commentary.",
  "",
  "> bare editor quote becomes a fence",
].join("\n");
const siteFenced = ContextNotes.markdownBlockquotesToFences(siteMixed);
assert.ok(siteFenced.includes(":::quote\nOuter quote body\n> nested markdown quote left alone\n:::"));
assert.ok(siteFenced.includes(":::quote\nbare editor quote becomes a fence\n:::"));
assert.ok(siteFenced.includes("My commentary."));

// Multi-line > quotes load as multiple <p>s and round-trip.
const multiQuoteMd = ["> First line", "> Second line", "", "Commentary."].join("\n");
const multiQuoteHtml = ContextNotes.markdownToHtml(multiQuoteMd);
assert.ok(multiQuoteHtml.includes("<blockquote class=\"custom-quote\"><p>First line</p><p>Second line</p></blockquote>"));
assert.ok(multiQuoteHtml.includes("<p>Commentary.</p>"));
assert.ok(
  ContextNotes.markdownBlockquotesToFences(multiQuoteMd).includes(
    ":::quote\nFirst line\nSecond line\n:::"
  )
);

// Headings and lists round-trip through markdownToHtml.
const structuredMd = [
  "## Section",
  "",
  "- item one",
  "- item two",
  "",
  "1. first",
  "2. second",
].join("\n");
const structuredHtml = ContextNotes.markdownToHtml(structuredMd);
assert.ok(structuredHtml.includes("<h2>Section</h2>"));
assert.ok(structuredHtml.includes("<ul><li>item one</li><li>item two</li></ul>"));
assert.ok(structuredHtml.includes("<ol><li>first</li><li>second</li></ol>"));

// Manual quotes (in notes only) do not paint; linked library quotes do.
const mixedNotes = [
  "> Linked highlight quote",
  "",
  "thoughts",
  "",
  "> Manual only quote",
].join("\n");
const linkedOnlyPaint = ContextNotes.quotesForHighlights(mixedNotes, [
  { id: "q1", text: "Linked highlight quote", note: "" },
]);
assert.strictEqual(linkedOnlyPaint.length, 1);
assert.strictEqual(linkedOnlyPaint[0].id, "q1");
assert.ok(!linkedOnlyPaint.some((item) => /Manual/.test(item.text)));

// Title normalize collapses newlines / excess whitespace.
const ContextPageDrafts = require(path.join(__dirname, "../chrome-extension/sidepanel/page-drafts.js"));
assert.strictEqual(
  ContextPageDrafts.normalizeTitle("Hello\n\n  world\t title"),
  "Hello world title"
);

// Notes are the source of truth for page highlights — orphan library quotes do not paint.
const partialNotes = "> Older quote only";
const notesScopedHighlights = ContextNotes.quotesForHighlights(partialNotes, [
  { id: "old", text: "Older quote only", note: "" },
  { id: "new", text: "Newest quote on page", note: "keep me" },
]);
assert.strictEqual(notesScopedHighlights.length, 1);
assert.strictEqual(notesScopedHighlights[0].id, "old");
assert.ok(!notesScopedHighlights.some((item) => item.id === "new"));

// After removing a quote from notes, highlights payload must drop it too.
const syncedNotes = [
  "> Keep this quote",
  "",
  "commentary",
  "",
  "> Delete this quote",
].join("\n");
const records = [
  { id: "keep", text: "Keep this quote", note: "" },
  { id: "drop", text: "Delete this quote", note: "" },
];
assert.strictEqual(ContextNotes.quotesForHighlights(syncedNotes, records).length, 2);
const afterDrop = ContextNotes.removeQuoteFromNotes(syncedNotes, { text: "Delete this quote" });
const remaining = ContextNotes.quotesForHighlights(afterDrop, records);
assert.strictEqual(remaining.length, 1);
assert.strictEqual(remaining[0].id, "keep");

// Deleting one quote must keep siblings and freeform commentary.
const multiQuotes = [
  "> First quote about FLOPs",
  "",
  "Thoughts on first.",
  "",
  "> Second quote about bandwidth",
  "",
  "attached note",
  "",
  "> Third quote",
  "",
  "Closing thoughts.",
].join("\n");
const afterMiddle = ContextNotes.removeQuoteFromNotes(multiQuotes, {
  text: "Second quote about bandwidth",
  note: "attached note",
});
assert.ok(afterMiddle.includes("> First quote about FLOPs"));
assert.ok(afterMiddle.includes("Thoughts on first."));
assert.ok(afterMiddle.includes("> Third quote"));
assert.ok(afterMiddle.includes("Closing thoughts."));
assert.ok(!afterMiddle.includes("Second quote about bandwidth"));
assert.ok(!afterMiddle.includes("attached note"));

const afterFirst = ContextNotes.removeQuoteFromNotes(multiQuotes, {
  text: "First quote about FLOPs",
  note: "",
});
assert.ok(afterFirst.includes("Thoughts on first."));
assert.ok(afterFirst.includes("> Second quote about bandwidth"));
assert.ok(afterFirst.includes("attached note"));
assert.ok(afterFirst.includes("> Third quote"));

// Note must not be consumed when it is only a prefix of the next paragraph.
const prefixTrap = [
  "> First",
  "",
  "More thoughts remain here.",
  "",
  "> Second",
].join("\n");
const afterPrefix = ContextNotes.removeQuoteFromNotes(prefixTrap, {
  text: "First",
  note: "More",
});
assert.ok(afterPrefix.includes("More thoughts remain here."));
assert.ok(afterPrefix.includes("> Second"));

console.log("notes export round-trip ok");
