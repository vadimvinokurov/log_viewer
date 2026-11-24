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
  // The stub approximates filter semantics with a plain substring check on
  // the message; mode-specific matching is backend logic (§7).
  const passesFilters = (n) =>
    filters.every((f) => !f.enabled || messageOf(n).includes(f.pattern));
  const visible = (n) => levelEnabled[levelOf(n)] && passesFilters(n);
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
    async setLevelEnabled(level, on) { levelEnabled[level] = on; return null; },
    async setCategoryEnabled() { return null; },
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
