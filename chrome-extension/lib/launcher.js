export const LAUNCHER_URL = "http://127.0.0.1:8798";

export async function requestLauncherStart() {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 2500);
    const response = await fetch(`${LAUNCHER_URL}/start`, {
      method: "POST",
      signal: controller.signal,
    });
    clearTimeout(timeout);
    return response.ok;
  } catch {
    return false;
  }
}

export async function launcherStatus() {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 800);
    const response = await fetch(`${LAUNCHER_URL}/status`, { signal: controller.signal });
    clearTimeout(timeout);
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}
