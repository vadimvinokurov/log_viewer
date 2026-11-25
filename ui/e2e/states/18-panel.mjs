// rhl.2 states: side panel with the categories tree (§10, full shell: the
// panel docks beside the real LogTable). The stub below mirrors the RAW IPC
// shapes and the engine's category semantics (row visible = exact path AND
// every prefix enabled) with a deterministic category assignment: n % 4
// cycles four exact paths, 250 rows each.
//
// panel-categories : file loaded, panel open, tree from the stub (roots
//                    expanded, children collapsed).
// panel-uncheck    : toggleCategory("app", false) propagated - app rows drop
//                    out of the visible sequence; the subtree renders dimmed.
// panel-tree-search: tree search "db" - only matching branches, fully
//                    expanded, matched text highlighted.
import { waitConsole } from "./base.mjs";

const STUB = `(function () {
  const CATEGORIES = [
    { path: "app" },
    { path: "app/main" },
    { path: "app/main/db" },
    { path: "app/main/api" },
    { path: "db" },
    { path: "db/pool" },
    { path: "uncategorized" },
  ];
  const LINE_COUNT = 1000;
  const CYCLE = ["app/main/db", "app/main/api", "db/pool", "uncategorized"];
  const LEVEL_CYCLE = ["msg", "error", "warning", "debug", "trace", "critical", "msg", "msg"];
  const enabled = new Set(CATEGORIES.map((c) => c.path));
  const categoryOf = (n) => CYCLE[n % CYCLE.length];
  const allowed = (cat) => {
    if (!enabled.has(cat)) return false;
    const seg = cat.split("/");
    for (let i = 1; i < seg.length; i++) if (!enabled.has(seg.slice(0, i).join("/"))) return false;
    return true;
  };
  const row = (n) => ({
    line_no: n,
    time_display: "10:00:0" + (n % 10) + "." + String(n % 1000).padStart(3, "0"),
    category: categoryOf(n),
    level: LEVEL_CYCLE[n % LEVEL_CYCLE.length],
    message: "Synthetic message " + n + " \\u2014 deterministic harness text.",
    raw: "raw " + n,
    spans: [],
  });
  const visibleRows = () => {
    const rows = [];
    for (let n = 1; n <= LINE_COUNT; n++) if (allowed(categoryOf(n))) rows.push(row(n));
    return rows;
  };
  window.__ipcStub = {
    async pickFile() { return "/tmp/synthetic.log"; },
    async loadFile() {
      return { format: "plain", line_count: LINE_COUNT, categories: CATEGORIES, levels: [], load_ms: 3 };
    },
    async getRows(offset, limit) {
      return visibleRows().slice(offset, offset + limit);
    },
    async addFilter() { return null; },
    async setFilterEnabled() { return null; },
    async removeFilter() { return null; },
    async addPin() { return null; },
    async setPinEnabled() { return null; },
    async removePin() { return null; },
    async setLevelEnabled() { return null; },
    async setCategoryEnabled(path, on) {
      if (on) enabled.add(path); else enabled.delete(path);
      return null;
    },
    async setCategoriesBulk(disable, enable) {
      for (const p of disable) enabled.delete(p);
      for (const p of enable) enabled.add(p);
      return null;
    },
    async visibilitySnapshot() {
      const byPath = new Map(CATEGORIES.map((c) => [c.path, 0]));
      let visible = 0;
      for (let n = 1; n <= LINE_COUNT; n++) {
        if (allowed(categoryOf(n))) visible++;
        byPath.set(categoryOf(n), (byPath.get(categoryOf(n)) ?? 0) + 1);
      }
      return {
        visible_count: visible,
        levels: ["critical", "error", "warning", "msg", "debug", "trace"].map((level) => ({
          level, enabled: true, count: 1,
        })),
        filters: [],
        pins: [],
        highlights: [],
        categories_enabled: [...enabled].sort(),
      };
    },
  };
  return "panel stub ready";
})()`;

/** The stub + full load through the console (page is already at server.url;
 *  render.mjs waits for the console before setup). */
const loadPanel = async (page) => {
  await waitConsole(page);
  await page.evaluate(STUB);
  await page.evaluate(() => window.__headless.load("/tmp/synthetic.log"));
  await page.waitForFunction(() => window.__headless.state().visibility !== null);
  await page.waitForFunction(() => window.__headless.state().panel.open === true);
};

export default [
  {
    name: "panel-categories",
    async setup(page) {
      await loadPanel(page);
      await page.waitForTimeout(150);
    },
  },
  {
    name: "panel-uncheck",
    async setup(page) {
      await loadPanel(page);
      await page.evaluate(() => window.__headless.toggleCategory("app", false));
      await page.waitForFunction(
        () =>
          !window.__headless.state().visibility?.categoriesEnabled.includes("app/main/db") &&
          window.__headless.state().visibility?.visibleCount === 500,
      );
      await page.waitForTimeout(150);
    },
  },
  {
    name: "panel-tree-search",
    async setup(page) {
      await loadPanel(page);
      await page.evaluate(() => window.__headless.setCategorySearch("db"));
      await page.waitForFunction(() => window.__headless.state().panel.search === "db");
      await page.waitForTimeout(150);
    },
  },
];
