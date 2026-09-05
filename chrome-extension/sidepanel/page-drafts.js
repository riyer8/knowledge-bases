/**
 * Persistent local page drafts (chrome.storage.local).
 * Notes stay here until + Save promotes them into the library.
 */
(function (root) {
  const DRAFT_PREFIX = "pageDraft:";
  const MAX_DRAFTS = 200;

  /** Match core.library_service._canonical_page_url */
  function canonicalPageUrl(url) {
    let value = String(url || "").trim();
    if (!value) return "";
    value = value.split("#", 1)[0];
    if (value.endsWith("/") && (value.match(/\//g) || []).length > 2) {
      value = value.replace(/\/+$/, "");
    }
    return value;
  }

  function pageDraftKey(url) {
    const canonical = canonicalPageUrl(url);
    return canonical ? `${DRAFT_PREFIX}${canonical}` : "";
  }

  function draftLookupKeys(url) {
    const raw = String(url || "").trim();
    const canonical = canonicalPageUrl(url);
    const keys = [];
    if (canonical) keys.push(`${DRAFT_PREFIX}${canonical}`);
    if (raw && raw !== canonical) keys.push(`${DRAFT_PREFIX}${raw}`);
    return keys;
  }

  function storageGet(keys) {
    return new Promise((resolve) => {
      chrome.storage.local.get(keys, (data) => resolve(data || {}));
    });
  }

  function storageSet(obj) {
    return new Promise((resolve) => {
      chrome.storage.local.set(obj, () => resolve());
    });
  }

  function storageRemove(keys) {
    return new Promise((resolve) => {
      if (!keys?.length) {
        resolve();
        return;
      }
      chrome.storage.local.remove(keys, () => resolve());
    });
  }

  async function loadPageDraft(url) {
    const keys = draftLookupKeys(url);
    if (!keys.length) return null;
    const data = await storageGet(keys);
    const canonicalKey = pageDraftKey(url);
    let draft = canonicalKey ? data[canonicalKey] || null : null;
    if (!draft) {
      for (const key of keys) {
        if (key === canonicalKey) continue;
        if (data[key]) {
          draft = data[key];
          break;
        }
      }
      if (draft && canonicalKey) {
        const migrated = { ...draft, updatedAt: Number(draft.updatedAt || Date.now()) };
        await storageSet({ [canonicalKey]: migrated });
        const stale = keys.filter((key) => key !== canonicalKey && data[key]);
        if (stale.length) await storageRemove(stale);
        return migrated;
      }
    }
    return draft || null;
  }

  async function savePageDraft(url, draft) {
    const key = pageDraftKey(url);
    if (!key) return null;
    const payload = {
      title: String(draft?.title || "").trim(),
      metadata: draft?.metadata && typeof draft.metadata === "object" ? draft.metadata : {},
      updatedAt: Date.now(),
    };
    await storageSet({ [key]: payload });
    const raw = String(url || "").trim();
    const legacyKey = raw ? `${DRAFT_PREFIX}${raw}` : "";
    if (legacyKey && legacyKey !== key) {
      await storageRemove([legacyKey]);
    }
    await gcPageDrafts(MAX_DRAFTS);
    return payload;
  }

  async function gcPageDrafts(maxKeep = MAX_DRAFTS) {
    const all = await storageGet(null);
    const entries = Object.entries(all)
      .filter(([storageKey]) => storageKey.startsWith(DRAFT_PREFIX))
      .map(([storageKey, value]) => ({
        key: storageKey,
        updatedAt: Number(value?.updatedAt || 0),
      }));
    if (entries.length <= maxKeep) return;
    entries.sort((a, b) => b.updatedAt - a.updatedAt);
    const drop = entries.slice(maxKeep).map((entry) => entry.key);
    if (drop.length) await storageRemove(drop);
  }

  function pageUrlsMatch(left, right) {
    const a = canonicalPageUrl(left);
    const b = canonicalPageUrl(right);
    return Boolean(a && b && a === b);
  }

  const ContextPageDrafts = {
    DRAFT_PREFIX,
    MAX_DRAFTS,
    canonicalPageUrl,
    pageDraftKey,
    draftLookupKeys,
    loadPageDraft,
    savePageDraft,
    gcPageDrafts,
    pageUrlsMatch,
  };

  root.ContextPageDrafts = ContextPageDrafts;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = ContextPageDrafts;
  }
})(typeof globalThis !== "undefined" ? globalThis : self);
