#!/usr/bin/env node
/**
 * Context launcher — small HTTP helper that starts the Python backend on demand.
 * The Chrome extension POSTs here when it opens (same pattern as apt-hunter).
 */
import { spawn } from "node:child_process";
import { openSync, mkdirSync } from "node:fs";
import { createServer } from "node:http";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const startScript = join(root, "scripts", "start_backend.sh");
const PORT = Number(process.env.CONTEXT_LAUNCHER_PORT) || 8798;
const API_URL = process.env.KB_API_URL || "http://127.0.0.1:8765";
const LOG_DIR = join(homedir(), "Library", "Logs", "Context");

let starting = false;

function log(...args) {
  console.log("[context launcher]", ...args);
}

async function apiHealthy() {
  try {
    const response = await fetch(`${API_URL}/health`, { signal: AbortSignal.timeout(800) });
    if (!response.ok) return false;
    const body = await response.json();
    return body.ok === true;
  } catch {
    return false;
  }
}

function startBackend() {
  if (starting) return;
  starting = true;
  log("Starting Python backend…");

  const detached = !process.stdout.isTTY;
  let stdio = "inherit";

  if (detached) {
    mkdirSync(LOG_DIR, { recursive: true });
    const out = openSync(join(LOG_DIR, "backend.log"), "a");
    const err = openSync(join(LOG_DIR, "backend-error.log"), "a");
    stdio = ["ignore", out, err];
  }

  const child = spawn("bash", [startScript], {
    cwd: root,
    detached,
    stdio,
    env: {
      ...process.env,
      PATH: ["/opt/homebrew/bin", "/usr/local/bin", process.env.PATH].filter(Boolean).join(":"),
    },
  });

  child.on("error", (error) => {
    log(`backend failed to start: ${error.message}`);
    starting = false;
  });

  child.on("exit", () => {
    starting = false;
  });

  if (detached) {
    child.unref();
  }
}

function sendJson(res, status, body) {
  res.writeHead(status, {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  });
  res.end(JSON.stringify(body));
}

const server = createServer(async (req, res) => {
  if (req.method === "OPTIONS") {
    sendJson(res, 204, {});
    return;
  }

  const path = req.url?.split("?")[0];

  if (req.method === "GET" && path === "/status") {
    sendJson(res, 200, {
      ok: true,
      api: await apiHealthy(),
      starting,
      repo: root,
    });
    return;
  }

  if (req.method === "POST" && path === "/start") {
    if (await apiHealthy()) {
      sendJson(res, 200, { ok: true, api: true, started: false });
      return;
    }

    startBackend();
    sendJson(res, 202, { ok: true, api: false, started: true, starting: true });
    return;
  }

  sendJson(res, 404, { error: "Not found" });
});

server.listen(PORT, "127.0.0.1", () => {
  log(`listening on http://127.0.0.1:${PORT}`);
  log(`backend API: ${API_URL}`);
});

process.on("SIGINT", () => server.close(() => process.exit(0)));
process.on("SIGTERM", () => server.close(() => process.exit(0)));
