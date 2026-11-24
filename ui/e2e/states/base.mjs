// Shared fixtures for e2e states. Every state module under e2e/states/
// exports default [{ name, url?, setup(page) }]; render.mjs loads them all.
// Deterministic synthetic data only (never test_logs contents).

// The IPC stub mirrors the RAW shapes of the visibility bridge contract
// (docs/notes/visibility-bridge.md): snake_case commands/payloads, an
// in-memory visibility model, and get_rows serving the visible sequence.
export const STUB = `(function () {
  const LEVEL_CYCLE = ["msg", "error", "warning", "debug", "trace", "critical", "msg", "msg"];
  const LINE_COUNT = 60000;
  const levelEnabled = { critical: true, error: true, warning: true, msg: true, debug: true, trace: true };
  const filters = [];
  const pins = [];
  const levelOf = (n) => LEVEL_CYCLE[n % LEVEL_CYCLE.length];
  const messageOf = (n) => "Synthetic message " + n + " \\u2014 deterministic harness text.";
  const row = (n) => ({
    line_no: n,
    time_display: "10:00:0" + (n % 10) + "." + String(n % 1000).padStart(3, "0"),
    category: "app/harness/db",
    level: levelOf(n),
    message: messageOf(n),
    raw: "raw " + n,
  });
  // The stub approximates filter semantics per mode: plain/simple as a
  // case-insensitive substring on the message, regex as an anchored JS
  // regex (a broken pattern matches nothing, the backend contract); exact
  // matching is backend logic (§7).
  const filterMatches = (f, n) => {
    if (!f.enabled) return true;
    const m = messageOf(n);
    if (f.mode === "regex") {
      try { return new RegExp(f.pattern, "i").test(m); } catch { return false; }
    }
    return m.toLowerCase().includes(String(f.pattern).toLowerCase());
  };
  const passesFilters = (n) => filters.every((f) => filterMatches(f, n));
  // §12: pins are rules (p/pr/ps/pn N); pinned rows stay visible overriding
  // filters/levels/categories (§7). Broad pins match the raw line text;
  // simple pins are the Rust-side engine - not approximated (q1f1-design).
  const rawOf = (n) => "raw " + n;
  const pinCovers = (n) =>
    pins.some((p) => {
      if (!p.enabled) return false;
      if (p.mode === "lineno") return String(p.pattern).trim() === String(n);
      if (p.mode === "plain") return rawOf(n).includes(p.pattern);
      if (p.mode === "regex") {
        try { return new RegExp(p.pattern).test(rawOf(n)); } catch { return false; }
      }
      return false;
    });
  const visible = (n) => pinCovers(n) || (levelEnabled[levelOf(n)] && passesFilters(n));
  const countVisible = () => {
    let c = 0;
    for (let n = 1; n <= LINE_COUNT; n++) if (visible(n)) c++;
    return c;
  };
  const countOf = (level) => {
    // §11 semantics: rows passing filters/categories if the level were
    // enabled - the level toggles are ignored (levelEnabled not read here).
    let c = 0;
    for (let n = 1; n <= LINE_COUNT; n++) {
      if (levelOf(n) === level && passesFilters(n)) c++;
    }
    return c;
  };
  window.__ipcStub = {
    async pickFile() { return "/tmp/synthetic.log"; },
    async loadFile() {
      pins.length = 0; // §2.1: a reload clears ALL pins
      return { format: "plain", line_count: LINE_COUNT, categories: [], levels: [], load_ms: 3 };
    },
    async getRows(offset, limit) {
      const rows = [];
      for (let n = 1; n <= LINE_COUNT && rows.length < limit; n++) {
        if (!visible(n)) continue;
        if (offset > 0) { offset--; continue; }
        rows.push(row(n));
      }
      return rows;
    },
    async addFilter(mode, pattern) { filters.push({ mode, pattern, enabled: true }); return null; },
    async setFilterEnabled(id, on) {
      const f = filters[id];
      if (!f) throw new Error("no such filter");
      f.enabled = on;
      return null;
    },
    async removeFilter(id) {
      if (!filters[id]) throw new Error("no such filter");
      filters.splice(id, 1);
      return null;
    },
    async addPin(mode, pattern) { pins.push({ mode, pattern, enabled: true }); return null; },
    async setPinEnabled(id, on) {
      const p = pins[id];
      if (!p) throw new Error("no such pin");
      p.enabled = on;
      return null;
    },
    async removePin(id) {
      if (!pins[id]) throw new Error("no such pin");
      pins.splice(id, 1);
      return null;
    },
    async clearPins() { pins.length = 0; return null; },
    async setLevelEnabled(level, on) { levelEnabled[level] = on; return null; },
    async setCategoryEnabled() { return null; },
    // §8 search (2wu.1): over the VISIBLE sequence only. Mode semantics are
    // backend logic; the stub approximates with a case-insensitive
    // substring (plain/simple) or an anchored JS regex, and a broken
    // pattern matches nothing (backend contract).
    async searchVisible(mode, pattern) {
      if (!pattern) return { total: 0, positions: [] };
      let matcher;
      if (mode === "regex") {
        try {
          const re = new RegExp(pattern, "i");
          matcher = (m) => re.test(m);
        } catch {
          return { total: 0, positions: [] };
        }
      } else {
        const needle = pattern.toLowerCase();
        matcher = (m) => m.toLowerCase().includes(needle);
      }
      const positions = [];
      let idx = 0;
      for (let n = 1; n <= LINE_COUNT; n++) {
        if (!visible(n)) continue;
        if (matcher(messageOf(n))) positions.push(idx);
        idx++;
      }
      return { total: positions.length, positions };
    },
    async visibilitySnapshot() {
      return {
        visible_count: countVisible(),
        levels: ["critical", "error", "warning", "msg", "debug", "trace"].map((level) => ({
          level,
          enabled: levelEnabled[level],
          count: countOf(level),
        })),
        filters: filters.map((f, id) => ({ id, mode: f.mode, pattern: f.pattern, enabled: f.enabled })),
        pins: pins.map((p, id) => ({ id, mode: p.mode, pattern: p.pattern, enabled: p.enabled })),
        categories_enabled: ["app/harness/db"],
      };
    },
  };
  return "stub ready";
})()`;

export const waitConsole = (page) =>
  page.waitForFunction(() =>
    typeof window.__headless === "object" && window.__headless !== null,
  );

/** Navigate to a ?show=<name> showcase state (the harness URL is the app). */
export const gotoShow = async (page, name) => {
  const url = new URL(page.url());
  url.search = "?show=" + name;
  await page.goto(url.href);
  await waitConsole(page);
};

/** Standard open+load through the headless console against the stub. */
export const loadThroughConsole = async (page) => {
  await page.evaluate(STUB);
  await page.evaluate(() => window.__headless.load("/tmp/synthetic.log"));
  await page.waitForFunction(() => window.__headless.state().file !== null);
};
