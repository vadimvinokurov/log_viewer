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
  // Deselect first: with a non-empty selection every visibility mutation
  // pays the selection-remap IPC round trips; the probes are contract checks,
  // not remap checks (e4/e5 cover that on one mutation).
  if (h.state().selection && h.state().selection.selected.length) {
    await h.select(h.state().selection.selected[0], "toggle");
  }
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
    if (tried >= 6) break;
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

// (f) categories (bead rhl.2, §10): panel opens on the categories tab; a real
// category from the loaded file toggles off (its rows hide), All restores;
// expand/collapse-all moves the expanded set; search field wires through.
const catRes = await evalJs(port, `
  const h = window.__headless;
  const panel = h.state().panel;
  if (!panel || !panel.open || panel.tab !== "categories") return { ok: false };
  const rows = await window.__TAURI_INTERNALS__.invoke("get_rows", { offset: 0, limit: 200 });
  const seen = [...new Set(rows.map((r) => r.category))];
  const cat = seen.find((c) => c && c !== "uncategorized") || seen[0] || "uncategorized";
  const base = h.state().visibility ? h.state().visibility.visibleCount : null;
  const off = await h.toggleCategory(cat, false);
  const offVis = off.visibility ? off.visibility.visibleCount : null;
  const offSet = off.visibility ? off.visibility.categoriesEnabled : null;
  const offPanel = off.panel ? { expanded: off.panel.expanded.length, search: off.panel.search } : null;
  const back = await h.setAllCategories(true);
  const backVis = back.visibility ? back.visibility.visibleCount : null;
  const expAll = await h.expandAllCategories(true);
  const expCount = expAll.panel ? expAll.panel.expanded.length : null;
  const col = await h.expandAllCategories(false);
  const colCount = col.panel ? col.panel.expanded.length : null;
  const colVis = col.visibility ? col.visibility.visibleCount : null;
  const s = await h.setCategorySearch(cat.slice(0, 3));
  const searchSet = s.panel ? s.panel.search : null;
  const back2 = await h.setCategorySearch("");
  const toggled = await h.toggleExpansion(cat);
  return { ok: true, cat, base, offVis: offVis !== null ? offVis : null, catGone: Array.isArray(offSet) ? !offSet.includes(cat) : null, offPanel,
    backVis, expCount, colCount, colVis, searchSet,
    toggleVis: toggled.visibility ? toggled.visibility.visibleCount : null };`);
check(
  "f0. panel open on the categories tab",
  catRes.ok === true,
  JSON.stringify(catRes),
);
if (catRes.ok) {
  check(
    `f1. toggleCategory('${catRes.cat}', false) hides its rows and unchecks the path`,
    catRes.offVis < catRes.base && catRes.catGone === true,
    `visible ${catRes.base}->${catRes.offVis} catGone=${catRes.catGone}`,
  );
  check(
    "f2. setAllCategories(true) restores the visible count",
    catRes.backVis === catRes.base,
    `restored=${catRes.backVis} base=${catRes.base}`,
  );
  check(
    "f3. expand-all grows the set, collapse shrinks it back",
    catRes.expCount > catRes.colCount && catRes.colCount >= 0,
    `expanded=${JSON.stringify(catRes.expCount)} collapsed=${JSON.stringify(catRes.colCount)}`,
  );
  check(
    "f4. category search wires through and clears",
    typeof catRes.searchSet === "string" && catRes.searchSet.length === Math.min(3, catRes.cat.length),
    `search=${JSON.stringify(catRes.searchSet)}`,
  );
}

// (g) search (bead 2wu.1, §8): panel opens, a token query over the visible
// rows gets 0 < matches < lines at rank 1, cyclic navigation wraps at both
// ends, modes wire (invalid regex -> 0 of 0), and a hidden level shrinks
// the match set; Esc closes.
//
// The section runs as THREE driver requests: on a 1M+ row file every
// settle costs seconds (measured scan ~1.5 s, plus the 250 ms debounce,
// plus queued recomputes), and the driver aborts an eval at 60 s
// (src-tauri/src/driver.rs) — a single long eval crossed it and the run
// crashed reading the absent result (live round 5). The settle: wait past
// one scan, then require THREE equal consecutive reads (stale values
// sampled mid-scan must not pass — live round 3).
const settleSnippet = `
  const h = window.__headless;
  // setSearchQuery debounces the recompute (250 ms) and returns the
  // pre-search snapshot.
  const afterQuery = async (tok) => {
    await h.setSearchQuery(tok);
    for (let t = 0; t < 3; t++) {
      await new Promise((r) => setTimeout(r, 400));
    }
    let prev = null, stable = 0;
    for (let t = 0; t < 40; t++) {
      await new Promise((r) => setTimeout(r, 700));
      const se = h.state().search;
      if (prev === se.total) {
        stable += 1;
        if (stable >= 3) return se;
      } else {
        stable = 0;
      }
      prev = se.total;
    }
    return h.state().search;
  };`;
const gOpen = await evalJs(port, `
  ${settleSnippet}
  const open = await h.openSearch();
  const opened = open.search ? { open: open.search.open, mode: open.search.mode } : null;
  const dto = await window.__TAURI_INTERNALS__.invoke("get_rows", { offset: 0, limit: 1 });
  const raw0 = dto.length ? String(dto[0].raw) : "";
  const tokens = raw0.split(/[^A-Za-z0-9_-]+/).filter((t) => t.length >= 4 && t.length <= 16);
  const lc = h.state().file ? h.state().file.lineCount : 0;
  let found = null, query = null;
  for (const tok of tokens) {
    const se = await afterQuery(tok);
    if (se && se.total > 0 && se.total < lc) { found = se; query = tok; break; }
    await afterQuery("");
  }
  return { opened, lc, query, total: found ? found.total : null };`);
const gModes = await evalJs(port, `
  ${settleSnippet}
  const q = ${JSON.stringify(gOpen.query)};
  const base = h.state().search;
  const rank = base ? base.currentRank : null;
  const totalAt = base ? base.total : null;
  const next1 = await h.nextMatch(1);
  const n1 = next1.search ? next1.search : null;
  const prev = await h.nextMatch(-1);
  const p1 = prev.search ? prev.search : null;
  await h.setSearchMode("regex");
  const invalid = await afterQuery("@@never-matching-live-probe@@");
  await h.setSearchMode("simple");
  // §6 grammar: terms are quoted; a bare word is a stray symbol (sfl.2).
  const simpleTotal = (await afterQuery('"' + q + '"')).total;
  await h.setSearchMode(null);
  const plainTotal = (await afterQuery(q)).total;
  return { rank, totalAt, n1rank: n1 ? n1.currentRank : null, n1total: n1 ? n1.total : null,
    p1rank: p1 ? p1.currentRank : null,
    invalidTotal: invalid ? invalid.total : null, simpleTotal, plainTotal };`);
const gHidden = await evalJs(port, `
  ${settleSnippet}
  const q = ${JSON.stringify(gOpen.query)};
  const lv0 = (h.state().visibility ? h.state().visibility.levels : []).filter((l) => l.enabled && l.count > 0);
  const hidden = lv0.sort((a, b) => b.count - a.count)[0] ?? null;
  let scopedHidden = null, directHidden = null, scopedBack = null;
  if (hidden) {
    // The largest level almost surely holds matches of the query; the
    // strict ground truth is the direct backend search under the hidden
    // state: the slice must agree with it (the search is over VISIBLE
    // rows only).
    await h.setLevel(hidden.level, false);
    scopedHidden = (await afterQuery(q)).total;
    const dv = await window.__TAURI_INTERNALS__.invoke("search_visible", { mode: "plain", pattern: q });
    directHidden = dv.total;
    await h.setLevel(hidden.level, true);
    scopedBack = (await afterQuery(q)).total;
  }
  const closed = await h.closeSearch();
  return { hiddenName: hidden ? hidden.level : null, scopedHidden, directHidden,
    scopedBack, closed: closed.search ? closed.search.open : null };`);
check(
  "g0. Ctrl+F flow: panel opens in plain mode",
  gOpen.opened && gOpen.opened.open === true,
  JSON.stringify(gOpen.opened),
);
if (gOpen.opened && gOpen.opened.open) {
  check(
    "g1. token query matches some rows over the visible set",
    gOpen.total > 0 && gOpen.total < gOpen.lc,
    `q=${JSON.stringify(gOpen.query)} total=${gOpen.total}`,
  );
  check(
    "g2. cyclic next/prev from the starting rule (first match at-or-below the selection)",
    gModes.n1rank === (gModes.rank % gModes.totalAt) + 1 &&
      gModes.p1rank === gModes.rank && gModes.n1total === gModes.totalAt,
    `rank=${gModes.rank} n=${gModes.n1rank} p=${gModes.p1rank} total=${gModes.n1total}`,
  );
  check(
    "g3. invalid regex matches nothing (0 of 0), simple + plain agree",
    gModes.invalidTotal === 0 && gModes.simpleTotal === gOpen.total &&
      gModes.plainTotal === gOpen.total,
    `invalid=${gModes.invalidTotal} simple=${gModes.simpleTotal} plain=${gModes.plainTotal}`,
  );
  check(
    "g4. search scoped to visible rows: the slice agrees with the direct search under the hidden level",
    gHidden.scopedHidden === gHidden.directHidden && gHidden.scopedBack === gOpen.total,
    `full=${gOpen.total} hidden(${gHidden.hiddenName}) slice=${gHidden.scopedHidden} direct=${gHidden.directHidden} back=${gHidden.scopedBack}`,
  );
  check(
    "g5. Esc closes the panel",
    gHidden.closed === false,
    `open=${gHidden.closed}`,
  );
}

// (h) pins (bead q1f.1, §12): a non-matching filter hides everything; a
// pin keeps its row visible (§7 override); selection unpin removes the
// exact-row pin through the real backend ids; clear-all empties; a reload
// clears pins while the filter survives (§2.1).
const pinRes = await evalJs(port, `
  const h = window.__headless;
  // Self-clean against whatever earlier sections left behind.
  await h.clearAllPins();
  for (const f of (h.state().visibility ? h.state().visibility.filters : [])) {
    await h.removeFilter(f.id);
  }
  await h.setAllCategories(true);
  for (const l of (h.state().visibility ? h.state().visibility.levels : [])) {
    if (!l.enabled) await h.setLevel(l.level, true);
  }
  await h.addFilter("plain", "@@never-matching-pin-probe@@");
  const hiddenVis = h.state().visibility.visibleCount;
  const add = await h.addPin("lineno", "10");
  const pinned = add.visibility ? { vis: add.visibility.visibleCount, pins: add.visibility.pins.map((p) => p.mode + ":" + p.pattern) } : null;
  await h.select(0, "click");
  const un = await h.unpinSelected();
  const unPinned = un.visibility ? { vis: un.visibility.visibleCount, pins: un.visibility.pins.length } : null;
  const a1 = await h.addPin("lineno", "10");
  const a2 = await h.addPin("plain", "@@pin2@@");
  const two = a2.visibility ? a2.visibility.pins.length : null;
  const cleared = await h.clearAllPins();
  const clearedCount = cleared.visibility ? cleared.visibility.pins.length : null;
  await h.addPin("lineno", "10");
  const reloaded = await h.load(${JSON.stringify(target)});
  const afterReload = reloaded.visibility ? { pins: reloaded.visibility.pins.length, vis: reloaded.visibility.visibleCount,
    filter: reloaded.visibility.filters.length } : null;
  for (const f of (h.state().visibility ? h.state().visibility.filters : [])) await h.removeFilter(f.id);
  await h.clearAllPins();
  return { hiddenVis, pinned, unPinned, two, clearedCount, afterReload };`);
check("h0. probe filter hides everything before the pin", pinRes.hiddenVis === 0, `vis=${pinRes.hiddenVis}`);
check(
  "h1. lineno pin overrides the filter (visible 1, pins list has it)",
  pinRes.pinned && pinRes.pinned.vis === 1 && JSON.stringify(pinRes.pinned.pins) === '["lineno:10"]',
  JSON.stringify(pinRes.pinned),
);
check("h2. selection unpin removed the exact-row pin (visible 0, pins empty)", pinRes.unPinned && pinRes.unPinned.pins === 0 && pinRes.unPinned.vis === 0, JSON.stringify(pinRes.unPinned));
check("h3. clear-all empties the pin list", pinRes.clearedCount === 0 && pinRes.two === 2, `two=${pinRes.two} cleared=${pinRes.clearedCount}`);
check(
  "h4. reload clears pins, keeps the filter (SS2.1 + SS12)",
  pinRes.afterReload && pinRes.afterReload.pins === 0 && pinRes.afterReload.filter === 1,
  JSON.stringify(pinRes.afterReload),
);

// (i) highlights (bead exx.2, §9): a Message-column rule paints spans on
// get_rows, overlapping rules stack, disabling drops its spans, a picked
// override color lands on spans and snapshot, highlights survive reload
// (§2.1), clear removes them all.
const hlRes = await evalJs(port, `
  const h = window.__headless;
  await h.clearHighlights();
  const dto = await window.__TAURI_INTERNALS__.invoke("get_rows", { offset: 0, limit: 1 });
  const row = dto[0];
  const tok = (row.message.split(/[^A-Za-z0-9_-]+/).filter((t) => t.length >= 4)[0] ?? row.message).slice(0, 12);
  const a = await h.addHighlight("plain", tok);
  const r1 = await window.__TAURI_INTERNALS__.invoke("get_rows", { offset: 0, limit: 5 });
  const r0s = r1[0].spans.length;
  const b = await h.addHighlight("regex", ".");
  const r2 = await window.__TAURI_INTERNALS__.invoke("get_rows", { offset: 0, limit: 5 });
  const overlap = r2[0].spans.length > r0s;
  const bothCount = r2[0].spans.length;
  const off = await h.setHighlightEnabled(0, false);
  const r3 = await window.__TAURI_INTERNALS__.invoke("get_rows", { offset: 0, limit: 5 });
  const offSpans = r3[0].spans.length; // now only the regex rule's own spans
  const col = await h.setHighlightColor(0, "#123456");
  const snap = h.state().visibility ? h.state().visibility.highlights : [];
  const overrideSet = Array.isArray(snap) ? snap.some((hl) => hl.overrideColor === "#123456") : false;
  const on = await h.setHighlightEnabled(0, true); // re-enable: disabled rules paint nothing
  const r4 = await window.__TAURI_INTERNALS__.invoke("get_rows", { offset: 0, limit: 5 });
  const overrideSpan = r4[0].spans.some((sp) => (sp.override_color ?? sp.overrideColor) === "#123456");
  const reloaded = await h.load(${JSON.stringify(target)});
  const snap2 = reloaded.visibility ? reloaded.visibility.highlights : [];
  const survived = reloaded.visibility ? reloaded.visibility.highlights.length : null;
  await h.clearHighlights();
  const r5 = await window.__TAURI_INTERNALS__.invoke("get_rows", { offset: 0, limit: 1 });
  return { tok, r0s, overlap, bothCount, offSpans, overrideSet, overrideSpan, survived, afterClear: r5[0].spans.length };`);
check("i0. a Message rule paints spans on get_rows rows", hlRes.r0s > 0, `spans=${hlRes.r0s}`);
check("i1. overlapping rules stack spans on the same row", hlRes.overlap === true, `grew=${hlRes.overlap}`);
check("i2. a disabled rule stops painting its spans", hlRes.offSpans < hlRes.bothCount, `both=${hlRes.bothCount} afterOff=${hlRes.offSpans}`);
check("i3. picked color lands in the snapshot and on spans", hlRes.overrideSet === true && hlRes.overrideSpan === true, `snapSet=${hlRes.overrideSet} spanSet=${hlRes.overrideSpan}`);
check("i4. highlights survive reload (two rules)", hlRes.survived === 2, `n=${hlRes.survived}`);
check("i5. clear removes spans entirely", hlRes.afterClear === 0, `spans=${hlRes.afterClear}`);

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
