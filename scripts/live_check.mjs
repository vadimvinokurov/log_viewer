//! Live verification against the REAL Tauri window (beads n4y.3; CLAUDE.md
//! rule 5). Waits for the app's driver server (debug builds), drives the real
//! webview console to load a real file, and asserts the result. Zero manual
//! steps. Usage: node scripts/live_check.mjs <absolute-path-to-log>
//!
//! Note: the load goes through the real IPC (load_file) and the real core.
//! The native Open dialog itself stays an owner-level live check.

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import net from "node:net";

const [, , argPath] = process.argv;
const target = argPath
  ? path.resolve(argPath)
  : path.resolve(process.cwd(), "../test_logs/log.txt");

function readPort() {
  const file = path.join(os.tmpdir(), "logviewer.driver.port");
  return Number(fs.readFileSync(file, "utf8").trim());
}

function request(port, path_, body) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const socket = net.connect(port, "127.0.0.1", () => {
      socket.write(
        `POST ${path_} HTTP/1.1\r\nContent-Type: application/json\r\nContent-Length: ${Buffer.byteLength(data)}\r\nConnection: close\r\n\r\n${data}`,
      );
    });
    let raw = "";
    socket.on("data", (chunk) => (raw += chunk));
    socket.on("end", () => {
      const i = raw.indexOf("\r\n\r\n");
      resolve(raw.slice(i + 4));
    });
    socket.on("error", reject);
  });
}

async function waitForApp(timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    try {
      const port = readPort();
      await request(port, "/load", { path: target });
      return port;
    } catch {
      if (Date.now() > deadline) {
        throw new Error("app driver not reachable: run `cargo tauri dev` first");
      }
      await new Promise((r) => setTimeout(r, 500));
    }
  }
}

const port = await waitForApp(120_000);
console.log(`driver on :${port}, loading ${target}`);
const raw = await request(port, "/load", { path: target });
const parsed = JSON.parse(raw).result;
const snapshot = typeof parsed === "string" ? JSON.parse(parsed) : parsed;
console.log("snapshot:", JSON.stringify(snapshot));

if (snapshot.driverError) {
  console.error("FAIL: page reported an error");
  process.exit(1);
}
if (snapshot.screen !== "loaded" || snapshot.file === null) {
  console.error("FAIL: file did not load in the live window");
  process.exit(1);
}
console.log(
  `LIVE OK: ${snapshot.file.name} · ${snapshot.file.format} · ${snapshot.file.lineCount} lines`,
);
