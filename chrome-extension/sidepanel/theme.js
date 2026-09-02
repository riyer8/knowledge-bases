/** Theme: system | light | dark — persisted in localStorage. */
(function (global) {
  const STORAGE_KEY = "context-theme";
  const MODES = ["system", "light", "dark"];

  function getTheme() {
    const stored = localStorage.getItem(STORAGE_KEY);
    return MODES.includes(stored) ? stored : "system";
  }

  function resolvedTheme(mode) {
    const preference = mode || getTheme();
    if (preference === "light" || preference === "dark") return preference;
    if (typeof global.matchMedia !== "function") return "light";
    return global.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function syncColorScheme(preference) {
    const scheme =
      preference === "system" ? resolvedTheme("system") : preference;
    document.documentElement.style.colorScheme = scheme;
  }

  function applyTheme(mode) {
    const preference = MODES.includes(mode) ? mode : getTheme();
    document.documentElement.dataset.themePreference = preference;
    syncColorScheme(preference);
    return resolvedTheme(preference);
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
        if (getTheme() === "system") syncColorScheme("system");
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
