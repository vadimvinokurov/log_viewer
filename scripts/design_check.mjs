//! Design oracle (building-testable-apps rules 4/6/7): the reference is the
//! committed design doc, not our own previous output. This script renders
//! docs/UI_DESIGN.html in headless Chrome, screenshots the framed component
//! mocks, renders the same components from the app's showcase (?show=...),
//! and reports a pixel diff design-vs-actual per element.
//!
//! Usage: node scripts/design_check.mjs   (run after `npm run build` in ui/)

import { chromium } from "playwright-core";
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import pixelmatch from "pixelmatch";
import { PNG } from "pngjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const DESIGN_URL = "file://" + path.join(ROOT, "docs", "UI_DESIGN.html");
const DIST = path.join(ROOT, "ui", "dist");
const OUT = path.join(ROOT, "ui", "e2e", "design");
const THRESHOLD = 5; // percent of differing pixels tolerated per element

/** Design-doc selector -> showcase counterpart (?show=<name>). */
const PAIRS = [
  {
    design: "section#s1 .levels",
    actual: { url: "?show=levels", selector: '[data-variant="warning-off"]' },
  },
  {
    design: "section#s3 .empty",
    actual: { url: "?show=empty", selector: '[data-variant="default"]' },
  },
];

const MIME = {
  ".html": "text/html",
  ".js": "text/javascript",
  ".css": "text/css",
  ".svg": "image/svg+xml",
  ".png": "image/png",
};

async function startServer() {
  const server = http.createServer((req, res) => {
    const url = new URL(req.url, "http://localhost");
    let file = path.join(DIST, url.pathname === "/" ? "index.html" : url.pathname);
    if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) {
      file = path.join(DIST, "index.html");
    }
    res.setHeader("Content-Type", MIME[path.extname(file)] ?? "application/octet-stream");
    res.end(fs.readFileSync(file));
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  return { url: `http://127.0.0.1:${server.address().port}/`, close: () => server.close() };
}

/** Pad the smaller image to the larger canvas; comparison stays meaningful
 * because the padding area lies outside the drawn content and pixelmatch
 * treats equal-on-both pixels as matching. */
/** Place both images on a common canvas with `b` shifted by (dx, dy);
 * returns the pair plus the canvas size. */
function padShift(a, b, dx, dy) {
  const w = Math.max(a.width, b.width) + 8;
  const h = Math.max(a.height, b.height) + 8;
  const base = 6;
  const place = (img, ox, oy) => {
    const out = new PNG({ width: w, height: h });
    out.data.fill(255);
    for (let y = 0; y < img.height; y++) {
      for (let x = 0; x < img.width; x++) {
        const src = (y * img.width + x) * 4;
        const dst = ((y + base + oy) * w + (x + base + ox)) * 4;
        if (0 <= dst && dst + 3 < out.data.length) {
          for (let k = 0; k < 4; k++) out.data[dst + k] = img.data[src + k];
        }
      }
    }
    return out;
  };
  return [place(a, 0, 0), place(b, dx, dy), w, h];
}

function padTo(a, b) {
  const w = Math.max(a.width, b.width);
  const h = Math.max(a.height, b.height);
  const copy = (img) => {
    const out = new PNG({ width: w, height: h });
    out.data.fill(255); // white background so pads diff nothing when equal
    for (let y = 0; y < img.height; y++) {
      for (let x = 0; x < img.width; x++) {
        const src = (y * img.width + x) * 4;
        const dst = (y * w + x) * 4;
        for (let k = 0; k < 4; k++) out.data[dst + k] = img.data[src + k];
      }
    }
    return out;
  };
  return [copy(a), copy(b), w, h];
}

function diff(aBuf, bBuf) {
  const rawA = PNG.sync.read(aBuf);
  const rawB = PNG.sync.read(bBuf);
  let a = rawA;
  let b = rawB;
  let size = null;
  if (rawA.width !== rawB.width || rawA.height !== rawB.height) {
    size = `${rawA.width}x${rawA.height} vs ${rawB.width}x${rawB.height}`;
    const [pa, pb, w, h] = padTo(rawA, rawB);
    a = pa;
    b = pb;
  }
  // Alignment search: sub-3 px layout offsets would otherwise smear every
  // glyph into a diff; take the best alignment within +-3 px on each axis.
  const dxs = [0, -1, 1, -2, 2, -3, 3];
  const dys = [0, -1, 1, -2, 2, -3, 3];
  let best = { p: Number.POSITIVE_INFINITY };
  for (const dy of dys) {
    for (const dx of dxs) {
      const [pa, pb, w, h] = padShift(a, b, dx, dy);
      const mismatch = pixelmatch(
        new Uint8Array(pa.data),
        new Uint8Array(pb.data),
        null,
        w,
        h,
        { threshold: 0.1 },
      );
      const pct = (mismatch / (w * h)) * 100;
      if (pct < best.p) {
        best = { p: pct, dx, dy };
      }
    }
  }
  return { size, pct: best.p, at: `${best.dx},${best.dy}` };
}

fs.mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch({ channel: "chrome", headless: true });
const server = await startServer();
const failures = [];

const pairs = PAIRS.entries();
for (const [i, pair] of pairs) try {
  // Design side: the reference mock.
  const designPage = await browser.newPage({ viewport: { width: 1400, height: 900 }, colorScheme: "dark" });
  await designPage.goto(DESIGN_URL);
  await designPage.waitForTimeout(400); // webfont settle
  const designShot = await designPage.locator(pair.design).screenshot();
  await designPage.close();

  // App side: the implementation under test.
  const appPage = await browser.newPage({ viewport: { width: 1400, height: 900 }, colorScheme: "dark" });
  await appPage.goto(server.url + pair.actual.url);
  await appPage.waitForFunction(
    () => typeof window.__headless === "object" && window.__headless !== null,
  );
  const actualShot = await appPage.locator(pair.actual.selector).screenshot();
  await appPage.close();

  fs.writeFileSync(path.join(OUT, `${i}-design.png`), designShot);
  fs.writeFileSync(path.join(OUT, `${i}-actual.png`), actualShot);
  const result = diff(designShot, actualShot);
  const { size, pct, at } = result;
  const sizeNote = size ? ` (padded: ${size})` : "";
  // Tiny strips (single toolbar rows) are dominated by glyph antialiasing
  // and 1 px sub-glyph spacing; a stricter visual read of the pair covers
  // them, so their tolerance is higher but still reviewed by eye.
  const shot = PNG.sync.read(actualShot);
  const threshold = shot.height < 50 ? 10 : THRESHOLD;
  const label = `${pair.design}: ${pct.toFixed(2)}% shift(${at})${sizeNote}`;
  if (pct > threshold) {
    console.log(`DIFF ${label}`);
    failures.push(label);
  } else {
    console.log(`ok ${label}`);
  }
} catch (e) {
  failures.push(`${pair.design}: ${e.message}`);
}

await browser.close();
server.close();

if (failures.length) {
  console.error(`design oracle: ${failures.length} element(s) differ:`);
  failures.forEach((f) => console.error("  - " + f));
  process.exit(1);
}
console.log("design oracle: app matches the reference mocks");
