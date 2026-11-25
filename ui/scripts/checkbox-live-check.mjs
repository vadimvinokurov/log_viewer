//! Live-cycle probe for the category-checkbox paint bug (2026-11-25).
//!
//! Drives the dev-server page in a real WebKit engine (Tauri on macOS is
//! WKWebView; playwright-webkit is the closest real WebKit). Loads a
//! synthetic file through the raw IPC stub, opens the categories tree,
//! scrolls it, and samples the center pixels of every fully-visible checked
//! checkbox. Contract: checked = accent-blue WITHOUT hover; "grey until
//! hover" is the owner-reported bug. Numbers only, no eyeballed PNGs.
//!
//! Fresh pipeline (owner, 2026-11-25): written from scratch; the retired
//! scripts/live_check pipeline is not reused or recreated.
//!
//! Run from ui/: node scripts/checkbox-live-check.mjs [webkit|chromium]
//! Gate: exit 0 = all fully-visible checked boxes blue after scroll; exit 1
//! = a grey checked box (bug) or harness failure.

import { spawn } from "node:child_process";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { webkit, chromium } from "playwright";
import { PNG } from "pngjs";

const ENGINE = process.argv[2] === "chromium" ? "chromium" : "webkit";
const PORT = 5199;
const BASE = "http://localhost:5199/";
const SHOT_DIR = process.env.SHOT_DIR ?? mkdtempSync(join(tmpdir(), "cb-check-"));

// Synthetic IPC stub mirroring the raw IPC shapes (snake_case).
const TOPS = Array.from({ length: 8 }, (_, i) => `top${i}`);
const MODS = Array.from({ length: 40 }, (_, i) => `app/mod${i}`);

const STUB_INIT = `(() => {
  const cats = [...${JSON.stringify(TOPS)}.map(t => ({path: t})), ...${JSON.stringify(MODS)}.map(m => ({path: m}))];
  const enabled = ${JSON.stringify([...TOPS, "app", ...MODS])};
  window.__ipcStub = {
    pickFile: async () => null,
    loadFile: async () => ({
      format: "plain", line_count: 128, size_bytes: 4096,
      categories: cats, levels: [{level: "msg", count: 128}], load_ms: 1
    }),
    getRows: async (offset, limit) => Array.from({length: limit}, (_, i) => ({
      line_no: offset + i + 1,
      time_display: "10:00:00.000",
      category: "app/mod1",
      level: "msg",
      message: "line " + (offset + i + 1),
      raw: "raw " + (offset + i + 1),
      spans: []
    })),
    visibilitySnapshot: async () => ({
      visible_count: 128,
      levels: [{level: "msg", enabled: true, count: 128}],
      filters: [], pins: [], highlights: [],
      categories_enabled: enabled
    }),
    setLevelEnabled: async () => null,
    setCategoryEnabled: async () => null,
    searchVisible: async () => ({total: 0, positions: []})
  };
})();`;

/** blue = accent-dominant sample (b - r >= 100 && r < 120). */
function isBlue(p) {
  return p.b - p.r >= 100 && p.r < 120;
}

/** Sample the inner top-left corner (5,5 off the box corner) of every
 *  fully-visible checked checkbox — inside the fill, away from the white
 *  checkmark glyph and the antialiased edge. */
async function sampleCheckedBoxes(page) {
  const boxes = await page.evaluate(() => {
    const tree = document.querySelector(".tree");
    const t = tree.getBoundingClientRect();
    return [...document.querySelectorAll(".tree input.cb")]
      .map((el) => { const r = el.getBoundingClientRect(); return { el, r }; })
      .filter(({ el, r }) => (el.checked || el.indeterminate) && r.top >= (t.top + 2) && r.bottom <= (t.bottom - 2))
      .map(({ el, r }) => ({
        path: el.closest(".row").dataset.path,
        cx: r.x + 5.5, cy: r.y + 5.5,
      }));
  });
  const shot = await page.screenshot();
  const png = PNG.sync.read(shot);
  const verdicts = boxes.map((b) => {
    const m = sampleMean(png, Math.round(b.cx), Math.round(b.cy));
    return { ...b, ...m, blue: isBlue(m) };
  });
  return verdicts;
}

function sampleMean(png, x, y) {
  let r = 0, g = 0, b = 0, n = 0;
  for (let dy = -1; dy <= 1; dy++) {
    for (let dx = -1; dx <= 1; dx++) {
      const idx = ((y + dy) * png.width + (x + dx)) * 4;
      r += png.data[idx]; g += png.data[idx + 1]; b += png.data[idx + 2]; n++;
    }
  }
  return { r: r / n, g: g / n, b: b / n };
}

async function main() {
  const server = spawn("node_modules/.bin/vite", ["--port", String(PORT), "--strictPort"], { stdio: "ignore" });
  try {
    for (let i = 0; i < 100; i++) {
      try { if ((await fetch(BASE)).ok) break; } catch {}
      await sleep(100);
    }
    const engine = ENGINE === "chromium" ? chromium : webkit;
    const browser = await engine.launch({ headless: true });
    const context = await browser.newContext({
      viewport: { width: 1280, height: 900 },
      colorScheme: "light",
      deviceScaleFactor: 1,
    });
    const page = await context.newPage();
    await page.addInitScript(STUB_INIT);
    await page.goto(BASE);
    await page.waitForFunction(() => typeof __headless === "object", null, { timeout: 15000 });
    await page.evaluate("__headless.load('synthetic.log')");
    await page.waitForFunction(() => __headless.state().screen === "loaded");
    // panel defaults open (state.ts:208); togglePanel would close it
    await page.evaluate("__headless.setPanelTab('categories')");
    await page.evaluate("__headless.expandAllCategories(true)");
    if (process.env.DEBUG_SNAPSHOT) {
      const snap = await page.evaluate("__headless.state()");
      console.log("DEBUG state:", JSON.stringify(snap).slice(0, 1200));
      const counts = await page.evaluate(() => {
        const boxes = [...document.querySelectorAll(".tree input.cb")];
        return {
          rows: document.querySelectorAll(".tree .row").length,
          boxes: boxes.length,
          checked: boxes.filter((b) => b.checked).length,
        };
      });
      console.log("DEBUG counts:", JSON.stringify(counts));
    }
    await page.waitForSelector(".tree input.cb");
    const initial = await sampleCheckedBoxes(page);
    await page.evaluate(() => { document.querySelector(".tree").scrollTop = 300; });
    await sleep(150);
    const scrolled = await sampleCheckedBoxes(page);
    const greyPaths = scrolled.filter((v) => !v.blue).map((v) => v.path);
    if (greyPaths.length > 0) {
      const first = scrolled.find((v) => !v.blue);
      await page.mouse.move(first.cx, first.cy);
      await sleep(150);
      const afterHover = await sampleCheckedBoxes(page);
      const hovered = afterHover.find((v) => v.path === first.path);
      console.log("hover signature:", JSON.stringify(hovered));
    }
    console.log(JSON.stringify({
      engine: ENGINE,
      initial: { total: initial.length, grey: initial.filter(v => !v.blue).map(v => v.path) },
      scrolled: { total: scrolled.length, grey: greyPaths },
      shotDir: SHOT_DIR,
    }));
    const BUG = greyPaths.length > 0;
    console.log(BUG ? "BUG present: grey checked boxes after scroll (no hover)" : "clean: checked boxes blue without hover");
    await browser.close();
    process.exitCode = BUG ? 1 : 0;
  } finally {
    server.kill();
  }
}

await main();
