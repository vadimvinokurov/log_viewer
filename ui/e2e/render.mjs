//! Visual acceptance harness (docs/PIPELINE.md §5; building-testable-apps
//! rules 6/7): the page renders its states through a system Chrome
//! (headless), driven by the app's own text interface (window.__headless);
//! every state is screenshotted to a PNG and compared against the committed
//! golden file. Run: npm run e2e [-- --update-goldens]
//!
//! Externals (dialog, Tauri IPC) are stubbed per state; log content is
//! synthetic and deterministic - the goldens are stable artifacts.

import { chromium } from "playwright-core";
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import pixelmatch from "pixelmatch";
import { PNG } from "pngjs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const DIST = path.join(HERE, "..", "dist");
const GOLDENS = path.join(HERE, "goldens");
const MIME = {
  ".html": "text/html",
  ".js": "text/javascript",
  ".css": "text/css",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".woff2": "font/woff2",
};

/** Serve the built app deterministically (the harness owns its server). */
async function startServer() {
  const server = http.createServer((req, res) => {
    const url = new URL(req.url, "http://localhost");
    let file = path.join(DIST, url.pathname === "/" ? "index.html" : url.pathname);
    if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) {
      file = path.join(DIST, "index.html"); // SPA fallback
    }
    res.setHeader("Content-Type", MIME[path.extname(file)] ?? "application/octet-stream");
    res.end(fs.readFileSync(file));
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const port = server.address().port;
  return { url: `http://127.0.0.1:${port}/`, close: () => server.close() };
}
const UPDATE = process.argv.includes("--update-goldens");
const STUB = `(function () {
  const levels = ["msg", "error", "warning", "debug", "trace", "critical", "msg", "msg"];
  window.__ipcStub = {
    async pickFile() { return "/tmp/synthetic.log"; },
    async loadFile() {
      return { format: "plain", line_count: 60000, categories: [], levels: [], load_ms: 3 };
    },
    async getRows(offset, limit) {
      const rows = [];
      for (let i = offset; i < Math.min(offset + limit, 60000); i++) {
        const n = i + 1;
        rows.push({
          line_no: n,
          time_display: "10:00:0" + (n % 10) + "." + String(n % 1000).padStart(3, "0"),
          category: "app/harness/db",
          level: levels[n % levels.length],
          message: "Synthetic message " + n + " — deterministic harness text.",
          raw: "raw " + n,
        });
      }
      return rows;
    },
  };
  return "stub ready";
})()`;

// States live in e2e/states/*.mjs (each UI task adds its own file).
function diffPercent(golden, actual) {
  const a = PNG.sync.read(golden);
  const b = PNG.sync.read(actual);
  if (a.width !== b.width || a.height !== b.height) {
    return 100; // size change means re-baseline intentionally
  }
  const delta = pixelmatch(
    new Uint8Array(a.data),
    new Uint8Array(b.data),
    null,
    a.width,
    a.height,
    { threshold: 0.1 },
  );
  return (delta / (a.width * a.height)) * 100;
}

const browser = await chromium.launch({
  channel: "chrome",
  headless: true,
});
const server = await startServer();
const page = await browser.newPage({
  viewport: { width: 1400, height: 900 },
  colorScheme: "dark",
});
await page.goto(server.url);

let failures = 0;
fs.mkdirSync(GOLDENS, { recursive: true });

const stateFiles = fs
  .readdirSync(path.join(HERE, "states"))
  .filter((f) => f.endsWith(".mjs") && f !== "base.mjs")
  .sort();
const STATES = (
  await Promise.all(
    stateFiles.map((f) => import(path.join(HERE, "states", f)).then((m) => m.default)),
  )
).flat();

for (const state of STATES) {
  try {
    // Every state reloads the page so it cannot depend on earlier states;
    // goto resolves before React effects, so wait for the console first.
    await page.goto(state.url ?? server.url);
    await page.waitForFunction(() => typeof window.__headless === "object" && window.__headless !== null);
    await state.setup(page);
    const shot = await page.screenshot({ type: "png" });
    const goldenPath = path.join(GOLDENS, `${state.name}.png`);
    if (UPDATE || !fs.existsSync(goldenPath)) {
      fs.writeFileSync(goldenPath, shot);
      console.log(`golden saved: ${state.name} (${shot.length} bytes)`);
      continue;
    }
    const golden = fs.readFileSync(goldenPath);
    const diff = diffPercent(golden, shot);
    if (diff > 0.5) {
      fs.writeFileSync(path.join(HERE, `actual-${state.name}.png`), shot);
      console.error(`FAIL ${state.name}: ${diff.toFixed(2)}% pixels differ (threshold 0.5%)`);
      failures++;
    } else {
      console.log(`ok ${state.name}: ${diff.toFixed(3)}%`);
    }
  } catch (e) {
    console.error(`FAIL ${state.name}: ${e.message}`);
    failures++;
  }
}

await browser.close();
server.close();
if (failures > 0) {
  console.error(`${failures} visual state(s) mismatch`);
  process.exit(1);
}
console.log("all visual states match goldens");
