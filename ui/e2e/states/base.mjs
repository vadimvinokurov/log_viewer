// Shared fixtures for e2e states. Every state module under e2e/states/
// exports default [{ name, url?, setup(page) }]; render.mjs loads them all.
// Deterministic synthetic data only (never test_logs contents).

export const STUB = `(function () {
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
          message: "Synthetic message " + n + " \\u2014 deterministic harness text.",
          raw: "raw " + n,
        });
      }
      return rows;
    },
  };
  return "stub ready";
})()`;

export const waitConsole = (page) =>
  page.waitForFunction(() =>
    typeof window.__headless === "object" && window.__headless !== null,
  );
