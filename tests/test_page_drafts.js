const assert = require("assert");
const path = require("path");
const draftsPath = path.join(__dirname, "../chrome-extension/sidepanel/page-drafts.js");
const ContextPageDrafts = require(draftsPath);

assert.strictEqual(
  ContextPageDrafts.canonicalPageUrl("https://example.com/a/#section"),
  "https://example.com/a"
);
assert.strictEqual(
  ContextPageDrafts.canonicalPageUrl("https://example.com/a/"),
  "https://example.com/a"
);
assert.strictEqual(
  ContextPageDrafts.canonicalPageUrl("https://example.com/"),
  "https://example.com"
);
assert.ok(
  ContextPageDrafts.pageUrlsMatch("https://example.com/a/", "https://example.com/a#x")
);
assert.strictEqual(
  ContextPageDrafts.pageDraftKey("https://example.com/a/#frag"),
  "pageDraft:https://example.com/a"
);
assert.deepStrictEqual(
  ContextPageDrafts.draftLookupKeys("https://example.com/a/"),
  ["pageDraft:https://example.com/a", "pageDraft:https://example.com/a/"]
);

console.log("page drafts canonicalization ok");
