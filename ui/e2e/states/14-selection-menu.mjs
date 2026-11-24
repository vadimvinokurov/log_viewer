// qt7.2 context menu state: a selection on the table, then a real right
// click on a selected row - the §4 menu stands over the rows (Copy/Copy
// Message live, Pin/Unpin/Highlight dim until those epics land).
import { STUB } from "./base.mjs";

export default [
  {
    name: "14-selection-menu",
    async setup(page) {
      await page.evaluate(STUB);
      await page.evaluate(() => window.__headless.load("/tmp/synthetic.log"));
      await page.waitForFunction(() => window.__headless.state().screen === "loaded");
      await page.evaluate(() => window.__headless.select(30, "click"));
      await page.evaluate(() => window.__headless.select(34, "range"));
      // Right-click the selected row 34 (0-based 33): menu at the cursor.
      const row = page.getByText("Synthetic message 34").first();
      await row.click({ button: "right" });
      await page.waitForSelector('[data-menu-root]');
      await page.evaluate(() => document.fonts.ready);
      await page.waitForTimeout(150);
    },
  },
];
