/** Theme: system | light | dark — persisted in localStorage. */
(function (global) {
  const STORAGE_KEY = "context-theme";
  const MODES = ["system", "light", "dark"];

  function getTheme() {
    const stored = localStorage.getItem(STORAGE_KEY);
    return MODES.includes(stored) ? stored : "system";
  }

  function resolvedTheme(mode) {
    if (mode === "light" || mode === "dark") return mode;
    if (typeof global.matchMedia !== "function") return "dark";
    return global.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function applyTheme(mode) {
    const preference = mode || getTheme();
    const theme = resolvedTheme(preference);
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    return theme;
  }

  function setTheme(mode) {
    const next = MODES.includes(mode) ? mode : "system";
    localStorage.setItem(STORAGE_KEY, next);
    return applyTheme(next);
  }

  function initTheme() {
    applyTheme(getTheme());
    if (typeof global.matchMedia === "function") {
      global.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
        if (getTheme() === "system") applyTheme("system");
      });
    }
  }

  function syncThemeSelect(selectEl) {
    if (!selectEl) return;
    selectEl.value = getTheme();
  }

  global.ContextTheme = {
    MODES,
    getTheme,
    setTheme,
    applyTheme,
    initTheme,
    syncThemeSelect,
    resolvedTheme,
  };
})(window);
