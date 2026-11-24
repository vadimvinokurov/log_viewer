//! Live verification against the REAL Tauri window (beads n4y.3, dsq.3;
//! CLAUDE.md rule 5). Waits for the app's driver server (debug builds), drives
//! the real webview console through the milestone scenario and asserts on
//! NUMBERS only: no raw log content is ever printed (CLAUDE.md rule 1) —
//! comparisons happen on the page side and only numbers/booleans come back.
//! Usage: node scripts/live_check.mjs <absolute-path-to-log>
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
  : path.resolve(path.dirname(new URL(import.meta.url).pathname), "../test_logs/log.txt");

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

const checks = [];
function check(name, ok, detail) {
  checks.push({ name, ok, detail: ok ? "" : String(detail ?? "") });
  console.log(`${ok ? "PASS" : "FAIL"}: ${name}${ok ? "" : ` (${detail})`}`);
  return ok;
}

/** Runs an async JS snippet against the real window's console and returns the
 *  snippet's `return` value. The snippet must only produce numbers, booleans
 *  and short enum strings — raw log content stays on the page side. */
async function evalJs(port, js) {
  const response = await request(port, "/load", { js });
  const parsed = JSON.parse(response).result;
  const result = typeof parsed === "string" ? JSON.parse(parsed) : parsed;
  if (result && typeof result === "object" && result.driverError) {
    throw new Error(`page error: ${result.driverError}`);
  }
  return result;
}

const port = await waitForApp(120_000);
const raw = await request(port, "/load", { path: target });
const parsed = JSON.parse(raw).result;
const snapshot = typeof parsed === "string" ? JSON.parse(parsed) : parsed;

if (snapshot.driverError) {
  console.error("FAIL: page reported an error");
  process.exit(1);
}
if (snapshot.screen !== "loaded" || snapshot.file === null) {
  console.error("FAIL: file did not load in the live window");
  process.exit(1);
}
console.log(
  `loaded: ${snapshot.file.name} · ${snapshot.file.format} · ${snapshot.file.lineCount} lines`,
);
const lineCount = snapshot.file.lineCount;

// (a) state() right after load: everything visible.
const s0 = await evalJs(
  port,
  `return window.__headless.state().visibility
    ? { visible: window.__headless.state().visibility.visibleCount }
    : { visible: null };`,
);
check(
  "a. load -> state(): visible count == line count",
  s0.visible === lineCount,
  `visible=${s0.visible} lineCount=${lineCount}`,
);

// (d) selection + copy BEFORE any visibility change (row 0 = row 0 of the
// full file). The raw comparison happens here: page side only.
const copyRes = await evalJs(port, `
  const h = window.__headless;
  const sel = await h.select(0, "click");
  const rawText = await h.copy("raw");
  const dto = await window.__TAURI_INTERNALS__.invoke("get_rows", { offset: 0, limit: 1 });
  const raw0 = dto.length && dto[0].raw;
  const msgText = await h.copy("message");
  return {
    selected: sel.selection ? sel.selection.selected : [],
    rawLen: rawText.length,
    hasRaw: !!raw0,
    rawEquals: !!raw0 && raw0 === rawText,
    msgLen: msgText.length,
    msgContained: !!raw0 && raw0.indexOf(msgText) !== -1,
  };`);
check(
  "d1. select(0,'click') -> selected [0]",
  JSON.stringify(copyRes.selected) === "[0]",
  `selected=${JSON.stringify(copyRes.selected)}`,
);
check(
  "d2. copy(raw) equals the raw row-0 line from get_rows",
  copyRes.hasRaw && copyRes.rawEquals,
  `rawLen=${copyRes.rawLen}`,
);
check(
  "d3. copy(message) is contained in the raw text",
  copyRes.msgContained,
  `msgLen=${copyRes.msgLen}`,
);

// (b) level toggle off -> strictly fewer visible rows, flag false; on ->
// restored.
const levelRes = await evalJs(port, `
  const h = window.__headless;
  const s = h.state();
  const cand = (s.visibility ? s.visibility.levels : []).filter(
    (l) => l.enabled && l.count > 0);
  if (cand.length === 0) return { present: false };
  const name = cand[0].level;
  const before = s.visibility ? s.visibility.visibleCount : null;
  const off = await h.setLevel(name, false);
  const entry = off.visibility
    ? off.visibility.levels.find((l) => l.level === name) : null;
  const offVis = off.visibility ? off.visibility.visibleCount : null;
  const onEnabled = entry ? entry.enabled : null;
  const back = await h.setLevel(name, true);
  const restored = back.visibility ? back.visibility.visibleCount : null;
  return { present: true, levelName: name, before, offVis, onEnabled, restored };`);
check(
  "b0. a present, enabled level found",
  levelRes.present,
  "no enabled level with count > 0 in the snapshot",
);
if (levelRes.present) {
  check(
    `b1. setLevel('${levelRes.levelName}', false) -> enabled flag false`,
    levelRes.onEnabled === false,
    `enabled=${levelRes.onEnabled}`,
  );
  check(
    "b2. level off -> visibleCount strictly < before",
    levelRes.offVis < levelRes.before,
    `off=${levelRes.offVis} before=${levelRes.before}`,
  );
  check(
    "b3. level on -> visibleCount restored",
    levelRes.restored === levelRes.before,
    `restored=${levelRes.restored} before=${levelRes.before}`,
  );
}

// (c) filters: never-matching probe first (narrowing contract), then an
// adaptive token pattern that matches SOME but not all lines — the pattern
// source stays on the page side, only counts come back.
const filterRes = await evalJs(port, `
  const h = window.__headless;
  const s0 = h.state();
  const lc = s0.file ? s0.file.lineCount : 0;
  const base = s0.visibility ? s0.visibility.visibleCount : null;

  const probe = await h.addFilter("plain", "@@never-matching-live-probe@@");
  const pf = probe.visibility ? probe.visibility.filters : [];
  const probeCount = probe.visibility ? probe.visibility.visibleCount : null;
  const probeId = pf.length === 1 ? pf[0].id : null;
  const probeEnabled = pf.length === 1 ? pf[0].enabled : null;
  const probeBack = await h.removeFilter(probeId);
  const probeRestored = probeBack.visibility ? probeBack.visibility.visibleCount : null;
  const probeFiltersEmpty = probeBack.visibility ? probeBack.visibility.filters.length === 0 : false;

  const dto = await window.__TAURI_INTERNALS__.invoke("get_rows", { offset: 0, limit: 1 });
  const raw0 = dto.length ? String(dto[0].raw) : "";
  const tokens = raw0.split(/[^A-Za-z0-9_-]+/).filter((t) => t.length >= 4);
  let found = false, tried = 0, visible = null, enabled = null;
  let toggleVisible = null, filtersEmpty = false, restored = null;
  for (const tok of tokens) {
    if (tried >= 25) break;
    tried++;
    const sn = await h.addFilter("plain", tok);
    const fs = sn.visibility ? sn.visibility.filters : [];
    const id = fs.length ? fs[fs.length - 1].id : null;
    const vc = sn.visibility ? sn.visibility.visibleCount : null;
    if (vc !== null && vc > 0 && vc < lc) {
      found = true;
      visible = vc;
      enabled = fs.length ? fs[fs.length - 1].enabled : null;
      const toff = await h.toggleFilter(id, false);
      toggleVisible = toff.visibility ? toff.visibility.visibleCount : null;
      const removed = await h.removeFilter(id);
      filtersEmpty = removed.visibility ? removed.visibility.filters.length === 0 : false;
      restored = removed.visibility ? removed.visibility.visibleCount : null;
      break;
    }
    await h.removeFilter(id);
  }
  return { lc, base, probeCount: probeId !== null ? probeCount : null,
           probeEnabled, probeFiltered: probeFiltersEmpty ? probeRestored === base : false,
           probeRestored: probeFiltersEmpty ? null : "still-set",
           tried, found, visible, filterEnabled: enabled,
           toggleVisible, filtersEmpty, restored };`);
check(
  "c0. probe filter added (enabled) -> visible 0, removed -> restored",
  filterRes.probeCount === 0 &&
    filterRes.probeEnabled === true &&
    filterRes.probeFiltered === true,
  `probeCount=${JSON.stringify(filterRes.probeCount)} probeEnabled=${filterRes.probeEnabled} restoredToBase=${filterRes.probeFiltered}`,
);
check(
  "c1. token filter found that matches some-but-not-all lines",
  filterRes.found,
  `tried=${filterRes.tried} tokens without partial coverage`,
);
if (filterRes.found) {
  check(
    "c2. filters list length 1 and enabled",
    filterRes.filterEnabled === true,
    `enabled=${filterRes.filterEnabled}`,
  );
  check(
    "c3. enabled filter -> 0 < visibleCount < lineCount",
    filterRes.visible > 0 && filterRes.visible < filterRes.lc,
    `visible=${filterRes.visible} lineCount=${filterRes.lc}`,
  );
  check(
    "c4. toggleFilter(id,false) -> visibleCount restored",
    filterRes.toggleVisible === filterRes.base,
    `toggled=${filterRes.toggleVisible} base=${filterRes.base}`,
  );
  check(
    "c5. removeFilter(id) -> filters empty, visibleCount restored",
    filterRes.filtersEmpty && filterRes.restored === filterRes.base,
    `filtersEmpty=${filterRes.filtersEmpty} restored=${filterRes.restored} base=${filterRes.base}`,
  );
}

// (e) anchor + remap (bead qt7.3): scroll deep, remember the top row's line
// and its viewport offset, toggle a level that touches NEITHER the anchor row
// nor the selected rows, and require: anchor line + offset held, scrollLeft
// untouched, both restored on level-on. Then scrollToRow to two targets: the
// anchor must land on the target line each time with the SAME centering
// offset (centering without knowing the viewport height) and no horizontal
// drift. Selection: two deep rows; after the same refilter their indexes may
// shift, but their line numbers must survive the §4 remap.
const anchorRes = await evalJs(port, `
  const h = window.__headless;
  const lc = h.state().file.lineCount;
  // Anchor resolution (epoch binary search, virtualizer relayout) is async:
  // read viewport() until it is stable (two equal reads, non-null anchor).
  const settle = async () => {
    let p;
    for (let t = 0; t < 25; t++) {
      await new Promise((r) => setTimeout(r, 120));
      const v = h.viewport();
      const k = JSON.stringify(v);
      if (p === k && v && v.anchor) return v;
      p = k;
    }
    return h.viewport();
  };
  const B = Math.floor(lc / 2);
  const iA = B, iB = B - 500;
  await h.select(iB, "click");
  h.select(iA, "toggle");
  const selPre = h.state().selection ? h.state().selection.selected : [];
  const rowI = (i) => window.__TAURI_INTERNALS__.invoke("get_rows", { offset: i, limit: 1 })
    .then((d) => (d.length ? d[0] : null));
  const preRows = await Promise.all([rowI(iA), rowI(iB)]);
  const selLevels = new Set(preRows.map((r) => (r ? r.level : null)));
  await h.scrollToRow(B + 2500);
  const pre = await settle();
  if (!pre || !pre.anchor) return { ok: false, selPre: selPre.length, haveAnchor: false };
  const anchorRow = await rowI(pre.anchor.index);
  const levels = h.state().visibility ? h.state().visibility.levels : [];
  const lv = levels.find((l) => l.enabled && l.count > 0 &&
    !selLevels.has(l.level) && l.level !== (anchorRow ? anchorRow.level : null));
  if (!lv) return { ok: false, selPre: selPre.length, noLevel: true };
  const off = await h.setLevel(lv.level, false);
  const post = await settle();
  const selOff = off.selection ? off.selection.selected : [];
  const offRows = await Promise.all(selOff.map((i) => rowI(i)));
  const back = await h.setLevel(lv.level, true);
  const rest = await settle();
  const selRest = back.selection ? back.selection.selected : [];
  const restRows = await Promise.all(selRest.map((i) => rowI(i)));
  await h.scrollToRow(B + 7777);
  const c1 = await settle();
  await h.scrollToRow(B + 12345);
  const c2 = await settle();
  const lineOf = (r) => (r ? r.line_no : null);
  return { ok: true, level: lv.level, B,
    a0: pre.anchor.line, off0: pre.anchorOffsetPx, sl0: pre.scrollLeft,
    a1: post ? (post.anchor ? post.anchor.line : null) : null,
    off1: post ? post.anchorOffsetPx : null, sl1: post ? post.scrollLeft : null,
    a2: rest ? (rest.anchor ? rest.anchor.line : null) : null,
    off2: rest ? rest.anchorOffsetPx : null,
    sel0: [lineOf(preRows[1]), lineOf(preRows[0])], selOffLine: offRows.map(lineOf), selOffN: selOff.length,
    selRestLine: restRows.map(lineOf), selRestN: selRest.length,
    c1line: c1 && c1.anchor ? c1.anchor.line : null, c1off: c1 ? c1.anchorOffsetPx : null,
    c2line: c2 && c2.anchor ? c2.anchor.line : null, c2off: c2 ? c2.anchorOffsetPx : null,
    c2sl: c2 ? c2.scrollLeft : null };`);
check(
  "e0. deep level found that misses the anchor and selected rows",
  anchorRes.ok === true,
  `selPre=${JSON.stringify(anchorRes.selPre ?? null)} ok=${JSON.stringify(anchorRes.ok)}`,
);
if (anchorRes.ok) {
  check(
    "e1. refilter holds the anchor row at the same viewport offset",
    anchorRes.a1 === anchorRes.a0 && anchorRes.off1 === anchorRes.off0,
    `line ${JSON.stringify(anchorRes.a0)}->${JSON.stringify(anchorRes.a1)} offset ${JSON.stringify(anchorRes.off0)}->${JSON.stringify(anchorRes.off1)}`,
  );
  check(
    "e2. refilter leaves scrollLeft untouched",
    anchorRes.sl1 === anchorRes.sl0,
    `scrollLeft ${JSON.stringify(anchorRes.sl0)}->${JSON.stringify(anchorRes.sl1)}`,
  );
  check(
    "e3. level-on restores the anchor and its offset",
    anchorRes.a2 === anchorRes.a0 && anchorRes.off2 === anchorRes.off0,
    `line ${JSON.stringify(anchorRes.a2)} offset ${JSON.stringify(anchorRes.off2)}`,
  );
  check(
    "e4. selection remap preserves the selected lines across the refilter",
    JSON.stringify(anchorRes.selOffLine) === JSON.stringify(anchorRes.sel0),
    `pre-lines=${JSON.stringify(anchorRes.sel0)} post-lines=${JSON.stringify(anchorRes.selOffLine)} n=${anchorRes.selOffN}`,
  );
  check(
    "e5. level-on remaps the selection back to the original indexes",
    JSON.stringify(anchorRes.selRestLine) === JSON.stringify(anchorRes.sel0),
    `lines=${JSON.stringify(anchorRes.selRestLine)} n=${anchorRes.selRestN}`,
  );
  check(
    "e6. scrollToRow centers both targets at the same row offset",
    (anchorRes.B + 7777) - anchorRes.c1line === (anchorRes.B + 12345) - anchorRes.c2line,
    `c1 delta=${anchorRes.B + 7777 - anchorRes.c1line} c2 delta=${anchorRes.B + 12345 - anchorRes.c2line}`,
  );
  check(
    "e7. scrollToRow centers with one constant offset",
    anchorRes.c1off === anchorRes.c2off,
    `c1=${JSON.stringify(anchorRes.c1off)} c2=${JSON.stringify(anchorRes.c2off)}`,
  );
  check(
    "e8. scrollToRow does not drift horizontally",
    anchorRes.c2sl === anchorRes.sl0,
    `scrollLeft ${JSON.stringify(anchorRes.sl0)}->${JSON.stringify(anchorRes.c2sl)}`,
  );
}

const failed = checks.filter((c) => !c.ok).length;
const verdict = failed === 0 ? "OK" : "FAILED (" + failed + "/" + checks.length + ")";
console.log(
  "LIVE " + verdict +
  ": lines=" + lineCount +
  " visible=" + s0.visible +
  " level=" + (levelRes.present ? levelRes.levelName : "-") +
  " offVisible=" + (levelRes.present ? levelRes.offVis : "-") +
  " probeVisible=" + JSON.stringify(filterRes.probeCount) +
  " probeProbeRestored=" + (filterRes.probeFiltered ? "yes" : "no") +
  " filterVisible=" + (filterRes.found ? filterRes.visible : "-") +
  " filterToggled=" + (filterRes.found ? filterRes.toggleVisible : "-") +
  " filtersRestored=" + (filterRes.found ? filterRes.restored : "-") +
  " copyRaw=" + (copyRes.rawEquals ? "equal" : "MISMATCH") +
  " copyMessage=" + (copyRes.msgContained ? "contained" : "MISMATCH") +
  " anchorOk=" + (anchorRes.ok && failed === 0 ? JSON.stringify(anchorRes.a0) + "@" + anchorRes.off0 + "px" : JSON.stringify(anchorRes.a1 ?? null)),
);
process.exit(failed === 0 ? 0 : 1);
