/** Lightweight markdown → HTML (escape-first, no external deps). */
(function (global) {
  function escapeHtml(text) {
    return String(text || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  const LATEX_SYMBOLS = {
    to: "→",
    rightarrow: "→",
    leftarrow: "←",
    approx: "≈",
    infty: "∞",
    times: "×",
    cdot: "·",
    dots: "…",
    ldots: "…",
    pm: "±",
    leq: "≤",
    geq: "≥",
    neq: "≠",
    alpha: "α",
    beta: "β",
    gamma: "γ",
    delta: "δ",
    theta: "θ",
    lambda: "λ",
    mu: "μ",
    pi: "π",
    sigma: "σ",
    omega: "ω",
  };

  /** Turn common LaTeX bits into readable plain text (no KaTeX dependency). */
  function simplifyLatexInner(inner) {
    let out = String(inner || "");
    // Repeat a few times for shallow nesting like \frac{\text{a}}{b}
    for (let i = 0; i < 4; i += 1) {
      const before = out;
      out = out.replace(/\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}/g, "($1)/($2)");
      out = out.replace(/\\(?:text|mathrm|mathbf|textrm|mathit|operatorname)\s*\{([^{}]*)\}/g, "$1");
      out = out.replace(/\\sqrt\s*\{([^{}]*)\}/g, "√($1)");
      if (out === before) break;
    }
    out = out.replace(
      /\\(to|rightarrow|leftarrow|approx|infty|times|cdot|dots|ldots|pm|leq|geq|neq|alpha|beta|gamma|delta|theta|lambda|mu|pi|sigma|omega)\b/g,
      (_, name) => LATEX_SYMBOLS[name] || name
    );
    out = out.replace(/\\([{}_%&#])/g, "$1");
    out = out.replace(/\\([a-zA-Z]+)\b/g, "$1");
    return out.replace(/\s+/g, " ").trim();
  }

  function demoteLatex(text) {
    let s = String(text || "");
    s = s.replace(/\\\[([\s\S]*?)\\\]/g, (_, inner) => `\n\n${simplifyLatexInner(inner)}\n\n`);
    s = s.replace(/\$\$([\s\S]*?)\$\$/g, (_, inner) => `\n\n${simplifyLatexInner(inner)}\n\n`);
    s = s.replace(/\\\(([\s\S]*?)\\\)/g, (_, inner) => simplifyLatexInner(inner));
    s = s.replace(/\$([^$\n]+?)\$/g, (_, inner) => simplifyLatexInner(inner));
    // Orphan commands outside delimiters (models sometimes emit these raw)
    s = s.replace(/\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}/g, "($1)/($2)");
    s = s.replace(/\\(?:text|mathrm|mathbf|textrm|mathit)\s*\{([^{}]*)\}/g, "$1");
    s = s.replace(
      /\\(to|rightarrow|approx|infty|times|cdot|ldots|pm|leq|geq|neq)\b/g,
      (_, name) => LATEX_SYMBOLS[name] || name
    );
    return s;
  }

  function inlineMarkdown(text) {
    let html = String(text || "");
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
    // Bold before italic; allow single * or _ inside bold spans.
    html = html.replace(/\*\*((?:[^*]|\*(?!\*))+?)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/__((?:[^_]|_(?!_))+?)__/g, "<strong>$1</strong>");
    // No lookbehind — keeps this file parseable in older Chromium builds.
    html = html.replace(/\*([^*\n]+?)\*/g, "<em>$1</em>");
    html = html.replace(/(^|[^A-Za-z0-9_])_([^_\n]+?)_($|[^A-Za-z0-9_])/g, "$1<em>$2</em>$3");
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

  /**
   * Normalize LLM-ish markdown so packed lists / headings become real lines.
   */
  function normalizeLooseLists(text) {
    return String(text || "")
      .replace(/\r\n/g, "\n")
      // Mid-paragraph headings: "... memory). ### Breakdown"
      .replace(/\s+(#{1,4})\s+/g, "\n\n$1 ")
      // Unicode / loose bullets → "- "
      .replace(/^[ \t]*[•·‣▪◦]\s+/gm, "- ")
      .replace(/\s+[•·‣▪◦]\s+/g, "\n- ")
      // "1)" / "1）" ordered markers → "1. "
      .replace(/^(\d{1,3})[\)）]\s+/gm, "$1. ")
      // Mid-paragraph numbered runs: "… 1. **Title** … 2. **Title**"
      .replace(/\s+(\d{1,2})[.)]\s+(?=\*\*|__|\[|"|“|‘|[A-Z])/g, "\n$1. ")
      // Break list items after sentence punctuation: ": - We load"
      .replace(/([.:;])\s+([-*])\s+/g, "$1\n$2 ")
      // Mid-paragraph bullets: "… - **Title** … - **Title**"
      .replace(/\s+([-*])\s+(?=\*\*|__|\[|"|“|‘|[A-Z])/g, "\n$1 ");
  }

  function renderMarkdown(text) {
    if (!text) return "";
    const codeBlocks = [];
    let src = normalizeLooseLists(demoteLatex(text));

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

      if (/^(-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
        flushParagraph();
        flushList();
        flushBlockquote();
        blocks.push("<hr>");
        continue;
      }

      const heading = trimmed.match(/^(#{1,4})\s+(.+)$/);
      if (heading) {
        flushParagraph();
        flushList();
        flushBlockquote();
        const level = Math.min(heading[1].length, 3);
        let title = heading[2];
        // "### Title: Sentence continues…" → real heading + paragraph
        const splitTitle = title.match(/^(.{1,90}?):\s+([A-Z].{12,})$/);
        if (splitTitle && !/^\*\*/.test(splitTitle[2])) {
          blocks.push(`<h${level}>${inlineMarkdown(splitTitle[1])}</h${level}>`);
          paragraph.push(splitTitle[2]);
          continue;
        }
        blocks.push(`<h${level}>${inlineMarkdown(title)}</h${level}>`);
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

      // Indented continuation of the current list item (explore "why" lines, etc.)
      if (
        listType &&
        listItems.length &&
        /^\s{2,}\S/.test(line) &&
        !/^[-*+]\s+/.test(trimmed) &&
        !/^\d{1,3}\.\s+/.test(trimmed)
      ) {
        listItems[listItems.length - 1] += ` ${trimmed}`;
        continue;
      }

      const unordered = trimmed.match(/^[-*+]\s+(.+)$/);
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
