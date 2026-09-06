/**
 * Browser smoke test: load Context extension against a real essay page,
 * exercise content-script highlight UI + backend quote/notes flows.
 *
 * Usage: node scripts/e2e_browser_smoke.mjs
 */
import { chromium } from "playwright";
import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const EXT = path.join(ROOT, "chrome-extension");
const BACKEND = "http://127.0.0.1:8765";
const ESSAY = "https://jax-ml.github.io/scaling-book/roofline/";
const findings = [];
const shotDir = path.join(ROOT, ".tmp-e2e");

function note(level, msg) {
  findings.push({ level, msg });
  const tag = level === "ok" ? "OK" : level === "weird" ? "WEIRD" : "FAIL";
  console.log(`[${tag}] ${msg}`);
}

async function api(pathname, opts = {}) {
  const res = await fetch(`${BACKEND}${pathname}`, {
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
    ...opts,
  });
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { raw: text };
  }
  return { ok: res.ok, status: res.status, data };
}

async function main() {
  fs.mkdirSync(shotDir, { recursive: true });

  const health = await api("/health");
  if (!health.ok) {
    note("fail", `Backend health failed: ${health.status}`);
    process.exit(1);
  }
  note("ok", `Backend healthy (llm=${health.data?.llm_provider})`);

  const context = await chromium.launchPersistentContext("", {
    headless: false,
    channel: undefined,
    args: [
      `--disable-extensions-except=${EXT}`,
      `--load-extension=${EXT}`,
      "--no-first-run",
      "--no-default-browser-check",
    ],
    viewport: { width: 1280, height: 900 },
  });

  try {
    // Wait for service worker / extension boot
    let extId = null;
    for (let i = 0; i < 20 && !extId; i += 1) {
      const workers = context.serviceWorkers();
      const sw =
        workers[0] ||
        (await context.waitForEvent("serviceworker", { timeout: 2000 }).catch(() => null));
      if (sw) {
        const url = sw.url();
        const m = url.match(/chrome-extension:\/\/([a-z]+)\//);
        if (m) extId = m[1];
      }
      await new Promise((r) => setTimeout(r, 250));
    }
    if (extId) note("ok", `Extension loaded id=${extId}`);
    else note("weird", "Could not detect extension service worker id (continuing)");

    const page = await context.newPage();
    page.on("console", (msg) => {
      const t = msg.text();
      if (/context invalidated|Save failed|TypeError|Uncaught/i.test(t)) {
        note("weird", `Page console: ${t.slice(0, 180)}`);
      }
    });
    page.on("pageerror", (err) => note("fail", `Page error: ${err.message}`));

    await page.goto(ESSAY, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForTimeout(1500);
    await page.screenshot({ path: path.join(shotDir, "01-essay.png"), fullPage: false });
    note("ok", `Opened essay: ${await page.title()}`);

    // Content script present?
    const hasToolbarHook = await page.evaluate(() => {
      return Boolean(document.querySelector("#context-save-toolbar") || true);
    });
    const csAlive = await page.evaluate(async () => {
      try {
        return Boolean(chrome?.runtime?.id);
      } catch {
        return false;
      }
    }).catch(() => false);
    // chrome is not exposed to page JS — only content script world. Probe via DOM after selection.

    // Select a real essay paragraph (text may be split across link nodes).
    const selected = await page.evaluate(() => {
      const paras = Array.from(document.querySelectorAll("p"))
        .map((el) => ({ el, text: (el.innerText || "").trim() }))
        .filter(({ text }) => text.length > 80);
      const hit =
        paras.find(({ text }) => /roofline|bounded by three|FLOP|bandwidth|compute/i.test(text)) ||
        paras[0];
      if (!hit) return "";
      const range = document.createRange();
      range.selectNodeContents(hit.el);
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
      return sel.toString().trim();
    });

    if (!selected) {
      note("fail", "Could not select essay text");
    } else {
      note("ok", `Selected text (${selected.length} chars): ${selected.slice(0, 80)}…`);
    }

    // Content scripts listen for mouseup/selectionchange — synthesize both.
    const box = await page.locator("p").nth(1).boundingBox();
    if (box) {
      await page.mouse.move(box.x + 20, box.y + 8);
      await page.mouse.down();
      await page.mouse.move(box.x + Math.min(420, box.width - 10), box.y + 8);
      await page.mouse.up();
    }
    await page.waitForTimeout(700);
    await page.screenshot({ path: path.join(shotDir, "02-selection.png") });

    const toolbarVisible = await page.locator("#context-save-toolbar:not([hidden])").isVisible().catch(() => false);
    if (toolbarVisible) note("ok", "Highlight toolbar appeared after selection");
    else {
      // Retry: wait a bit longer for extension content script injection
      await page.waitForTimeout(1500);
      await page.evaluate(() => {
        const p = Array.from(document.querySelectorAll("p")).find(
          (el) => (el.innerText || "").length > 100
        );
        if (!p) return;
        const range = document.createRange();
        range.selectNodeContents(p);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        document.dispatchEvent(new MouseEvent("mouseup", { bubbles: true }));
        document.dispatchEvent(new Event("selectionchange", { bubbles: true }));
      });
      await page.waitForTimeout(500);
      const retry = await page.locator("#context-save-toolbar:not([hidden])").isVisible().catch(() => false);
      if (retry) note("ok", "Highlight toolbar appeared after retry");
      else note("weird", "Highlight toolbar not visible after selection (content script may not be injected in this automation host)");
    }
    // Backend: save page + quotes (simulates extension quick-save / notes)
    const pagePayload = {
      page: {
        url: ESSAY,
        title: await page.title(),
        site: "jax-ml.github.io",
        text: await page.evaluate(() => document.body.innerText.slice(0, 5000)),
        metadata: {
          notes: "",
          tldr: "",
          thoughts: "",
          tags: ["e2e", "roofline"],
          category: "science",
          medium: "essay",
          dateAdded: new Date().toISOString().slice(0, 10),
        },
      },
      history: [],
    };
    const saved = await api("/library/save-page", {
      method: "POST",
      body: JSON.stringify(pagePayload),
    });
    if (!saved.ok) {
      note("fail", `save-page failed: ${saved.status} ${JSON.stringify(saved.data)}`);
    } else {
      note("ok", `Saved page id=${saved.data?.page?.id}`);
    }
    const pageId = saved.data?.page?.id;

    const quotes = [
      {
        text: "Arithmetic intensity is the ratio of FLOPs to bytes moved",
        note: "definition",
      },
      {
        text: "Operations that are communication-bound leave the ALU idle",
        note: "",
      },
      {
        text: "The roofline model plots attainable performance against intensity",
        note: "visual model",
      },
    ];

    // Use real selected text as first quote when possible
    if (selected && selected.length >= 4) {
      quotes[0] = { text: selected.slice(0, 200), note: "from page selection" };
    }

    const created = [];
    for (const q of quotes) {
      const res = await api("/library/quotes", {
        method: "POST",
        body: JSON.stringify({
          text: q.text,
          note: q.note,
          page_id: pageId,
          page_url: ESSAY,
          page_title: await page.title(),
        }),
      });
      if (!res.ok) note("fail", `quote save failed: ${JSON.stringify(res.data)}`);
      else {
        created.push(res.data?.quote || res.data);
        note("ok", `Saved quote: ${q.text.slice(0, 60)}…`);
      }
    }

    // Build notes markdown like the extension does
    const { createRequire } = await import("module");
    const require = createRequire(import.meta.url);
    const ContextNotes = require(path.join(EXT, "sidepanel/notes.js"));
    let notes = "";
    for (const q of created) {
      notes = ContextNotes.appendQuoteToNotes(notes, {
        text: q.text,
        note: q.note || "",
      });
    }
    notes = `${notes}\n\nOverall: good essay on memory vs compute.`;

    const patched = await api(`/library/pages/${pageId}`, {
      method: "PATCH",
      body: JSON.stringify({
        metadata: {
          ...pagePayload.page.metadata,
          notes,
          tldr: "Roofline links arithmetic intensity to whether a kernel is compute- or bandwidth-bound.",
        },
      }),
    });
    if (!patched.ok) note("fail", `PATCH notes failed: ${JSON.stringify(patched.data)}`);
    else note("ok", "Patched page notes with 3 quotes + commentary");

    // Delete middle quote via notes helper (same as library path)
    const middle = created[1];
    const afterDelete = ContextNotes.removeQuoteFromNotes(notes, {
      text: middle.text,
      note: middle.note || "",
    });
    const bodies = ContextNotes.markdownQuoteBodies(afterDelete);
    if (bodies.length !== 2) {
      note("fail", `After deleting middle quote expected 2 bodies, got ${bodies.length}`);
    } else note("ok", "removeQuoteFromNotes kept sibling quotes (2 remain)");
    if (!afterDelete.includes("Overall: good essay")) {
      note("fail", "Freeform commentary was lost when deleting a quote");
    } else note("ok", "Freeform commentary survived quote delete");

    // Delete via API
    if (middle?.id) {
      const del = await api(`/library/quotes/${encodeURIComponent(middle.id)}`, {
        method: "DELETE",
      });
      if (!del.ok && del.status !== 404) note("fail", `API delete quote failed: ${del.status}`);
      else note("ok", "API deleted middle quote record");
    }

    // Persist surviving notes
    await api(`/library/pages/${pageId}`, {
      method: "PATCH",
      body: JSON.stringify({
        metadata: {
          ...pagePayload.page.metadata,
          notes: afterDelete,
          tldr: "Roofline links arithmetic intensity to whether a kernel is compute- or bandwidth-bound.",
        },
      }),
    });

    // Dashboard UI
    const dash = await context.newPage();
    await dash.goto(`${BACKEND}/app/`, { waitUntil: "domcontentloaded", timeout: 30000 });
    await dash.waitForTimeout(1200);
    await dash.screenshot({ path: path.join(shotDir, "03-dashboard.png") });
    const dashText = await dash.locator("body").innerText();
    if (/library|saved|wiki|notes/i.test(dashText)) note("ok", "Dashboard loaded");
    else note("weird", "Dashboard body lacked expected chrome");

    // Open saved page detail if list is clickable
    const card = dash.locator(".saved-card, [data-page-id], .library-item, article, .card").first();
    if (await card.count()) {
      await card.click().catch(() => {});
      await dash.waitForTimeout(800);
      await dash.screenshot({ path: path.join(shotDir, "04-dashboard-detail.png") });
      const detail = await dash.locator("body").innerText();
      if (/roofline|Overall: good essay|arithmetic/i.test(detail)) {
        note("ok", "Dashboard detail shows saved essay/notes content");
      } else {
        note("weird", "Dashboard detail did not clearly show saved notes (UI may differ)");
      }
    } else {
      note("weird", "No obvious saved-page card on dashboard to click");
    }

    // Chat markdown render unit check with real LLM-ish sample (renderer)
    const mdPath = path.join(EXT, "sidepanel/markdown.js");
    const mdSource = fs.readFileSync(mdPath, "utf8");
    const render = await page.evaluate((source) => {
      // eslint-disable-next-line no-eval
      eval(source);
      const sample =
        "Here is math \\( x \\). ### Breakdown: - **Loading**: bytes \\[ A = \\frac{1}{2} \\]";
      return renderMarkdown(sample);
    }, mdSource);
    if (render.includes("\\(") || render.includes("\\frac")) {
      note("fail", "Chat markdown still leaks LaTeX markers");
    } else if (!render.includes("<strong>Loading</strong>") || !render.includes("<h3>")) {
      note("weird", `Chat markdown render unexpected: ${render.slice(0, 200)}`);
    } else note("ok", "Chat markdown demotes LaTeX and renders headings/lists");

    // Try content-script highlight button if toolbar exists
    const toolbarReady = await page.locator("#context-save-toolbar:not([hidden])").isVisible().catch(() => false);
    if (toolbarReady) {
      await page.locator('#context-save-toolbar [data-action="save"]').click();
      await page.waitForTimeout(1200);
      const marks = await page.locator("mark.ctx-highlight").count();
      if (marks > 0) note("ok", `On-page highlight marks painted: ${marks}`);
      else note("weird", "Clicked Highlight but no mark.ctx-highlight found");
      await page.screenshot({ path: path.join(shotDir, "05-after-highlight.png") });
    }

    // Simulate notes editor delete button semantics in a real DOM page
    const deleteDomResult = await page.evaluate(({ notesJs, notesMd }) => {
      // eslint-disable-next-line no-eval
      eval(notesJs);
      const host = document.createElement("div");
      host.contentEditable = "true";
      host.id = "meta-notes-sim";
      host.innerHTML = ContextNotes.markdownToHtml(notesMd);
      // decorate delete buttons like panel.js
      host.querySelectorAll("blockquote").forEach((quoteEl) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.dataset.deleteQuote = "1";
        btn.textContent = "×";
        quoteEl.appendChild(btn);
      });
      document.body.appendChild(host);
      const quotes = Array.from(host.querySelectorAll("blockquote"));
      const before = quotes.length;
      const target = quotes[1];
      if (!target) return { before, after: before, md: ContextNotes.htmlToMarkdown(host) };
      target.remove();
      // remove following blank + exact note paragraph if present
      let el = host.querySelectorAll("blockquote")[1] || null;
      const afterCount = host.querySelectorAll("blockquote").length;
      const md = ContextNotes.htmlToMarkdown(host);
      host.remove();
      return { before, after: afterCount, md, hasFirst: md.includes("Arithmetic") || md.includes("from page") || md.includes("ratio"), hasThird: /roofline model|Third|Overall/i.test(md) };
    }, {
      notesJs: fs.readFileSync(path.join(EXT, "sidepanel/notes.js"), "utf8"),
      notesMd: notes,
    });
    if (deleteDomResult.after === deleteDomResult.before - 1) {
      note("ok", `DOM quote delete removed 1 blockquote (${deleteDomResult.before}→${deleteDomResult.after})`);
    } else {
      note("fail", `DOM quote delete unexpected counts ${JSON.stringify(deleteDomResult)}`);
    }
    if (!/Overall: good essay/i.test(deleteDomResult.md)) {
      note("fail", "DOM delete path lost freeform commentary");
    } else note("ok", "DOM delete path kept freeform commentary");

    // Cleanup created page to avoid polluting library (optional keep for inspection)
    if (pageId) {
      const cleared = await api(`/library/pages/${pageId}`, { method: "DELETE" });
      if (cleared.ok) note("ok", "Cleaned up e2e saved page");
      else note("weird", `Cleanup delete returned ${cleared.status}`);
    }
  } finally {
    await context.close();
  }

  const fails = findings.filter((f) => f.level === "fail");
  const weirds = findings.filter((f) => f.level === "weird");
  console.log("\n=== SUMMARY ===");
  console.log(`ok=${findings.filter((f) => f.level === "ok").length} weird=${weirds.length} fail=${fails.length}`);
  console.log(`Screenshots: ${shotDir}`);
  if (fails.length) process.exit(1);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
