#!/usr/bin/env node
/**
 * Install Context launcher as a macOS LaunchAgent (runs on login).
 * Uninstall: launchctl bootout gui/$UID ~/Library/LaunchAgents/com.context.launcher.plist
 */
import { execSync } from "node:child_process";
import { mkdirSync, writeFileSync, chmodSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

if (process.platform !== "darwin") {
  console.error("install-launcher is only supported on macOS.");
  process.exit(1);
}

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const launcher = join(root, "scripts", "launcher.mjs");
const node = process.execPath;
const agentsDir = join(homedir(), "Library", "LaunchAgents");
const plistPath = join(agentsDir, "com.context.launcher.plist");
const logDir = join(homedir(), "Library", "Logs", "Context");

chmodSync(launcher, 0o755);

mkdirSync(agentsDir, { recursive: true });
mkdirSync(logDir, { recursive: true });

const plist = `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.context.launcher</string>
  <key>ProgramArguments</key>
  <array>
    <string>${node}</string>
    <string>${launcher}</string>
  </array>
  <key>WorkingDirectory</key>
  <string>${root}</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${join(logDir, "launcher.log")}</string>
  <key>StandardErrorPath</key>
  <string>${join(logDir, "launcher-error.log")}</string>
</dict>
</plist>
`;

writeFileSync(plistPath, plist, "utf8");

try {
  execSync(`launchctl bootout gui/${process.getuid()} "${plistPath}"`, { stdio: "ignore" });
} catch {
  // Not loaded yet.
}

execSync(`launchctl bootstrap gui/${process.getuid()} "${plistPath}"`);

console.log("");
console.log("Context launcher installed.");
console.log(`  Plist: ${plistPath}`);
console.log(`  Logs:  ${logDir}`);
console.log("");
console.log("The extension will auto-start the backend when you open it.");
console.log("Reload the Context extension in chrome://extensions.");
console.log("");
