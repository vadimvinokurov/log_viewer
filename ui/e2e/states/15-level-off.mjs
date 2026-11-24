// dsq.3 state: a disabled level (§11). The stub's set_level_enabled turns
// trace off, so the golden shows the dimmed/strikethrough TRACE button in
// the footer and the table refilled with the visible sequence (trace rows
// gone, visible_count 52500 - §11 counts stay, level toggles are ignored).
import { loadThroughConsole } from "./base.mjs";

export default [
  {
    name: "loaded-level-off",
    async setup(page) {
      await loadThroughConsole(page);
      await page.waitForFunction(() => window.__headless.state().visibility !== null);
      await page.evaluate(() => window.__headless.setLevel("trace", false));
      await page.waitForFunction(() => {
        const snap = window.__headless.state();
        const trace = snap.visibility?.levels.find((l) => l.level === "trace");
        return trace?.enabled === false && snap.visibility?.visibleCount === 52500;
      });
      await page.evaluate(() => document.fonts.ready);
      await page.waitForTimeout(250);
    },
  },
];

// Wait for the §11 counts: §11 counter semantics keep trace's count at 7500
// (level toggles are ignored), so the dimmed button still shows "7 500".
