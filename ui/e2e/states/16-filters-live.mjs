// dsq.3 states: FiltersTab consuming the live console state (?show=filters-
// live, WiredFiltersTab) - no demo data, the same store + actions the app
// shell uses. The stub mirrors the RAW visibility bridge shapes, so panel
// rows come from the real snapshot events.
//
// empty  : no file loaded, no snapshot - "(no filters)" placeholder.
// mixed  : two filters added through the headless RPC ("plain harness"
//          matching every synthetic row, regex "^retry" matching none);
//          the second one is toggled off and renders dimmed (§10.1).
import { gotoShow, loadThroughConsole } from "./base.mjs";

export default [
  {
    name: "filters-live-empty",
    async setup(page) {
      await gotoShow(page, "filters-live");
    },
  },
  {
    name: "filters-live-mixed",
    async setup(page) {
      await gotoShow(page, "filters-live");
      await loadThroughConsole(page);
      await page.waitForFunction(() => window.__headless.state().visibility !== null);
      await page.evaluate(() => window.__headless.addFilter("plain", "harness"));
      await page.evaluate(() => window.__headless.addFilter("regex", "^retry"));
      await page.evaluate(() => window.__headless.toggleFilter(1, false));
      await page.waitForFunction(() => {
        const filters = window.__headless.state().visibility?.filters;
        return filters?.length === 2 && filters[1]?.enabled === false;
      });
      await page.evaluate(() => document.fonts.ready);
      await page.waitForTimeout(150);
    },
  },
];
