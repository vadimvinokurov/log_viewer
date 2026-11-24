// q1f.1 state: §7/§12 pin override on live console state, then an §4
// context-menu Unpin step. The selected row (line 45) is pinned through the
// console batch; an anchored regex narrows visibility to lines 40 and 44 -
// the pinned line 45 stays visible by the pin override (it is not
// filter-matched); a right-click on the pinned row opens the §4 menu (Unpin
// light, Pin dim - the row is pinned) and the menu Unpin removes the
// exact-row pin, so the not-filter-matched row drops out and lines 40/44
// remain. (The first visible row rests under the in-flow sticky header -
// pre-existing table geometry - so the pinned row is picked at index 2 and
// the assertions, not the final shot, carry the intermediate states.)
import { STUB } from "./base.mjs";

export default [
  {
    name: "21-pins-survive-filter",
    async setup(page) {
      await page.evaluate(STUB);
      await page.evaluate(() => window.__headless.load("/tmp/synthetic.log"));
      await page.waitForFunction(() => window.__headless.state().visibility !== null);
      // Pin the selected row (index 44 -> line 45) through the batch path.
      await page.evaluate(() => window.__headless.select(44, "click"));
      await page.evaluate(() => window.__headless.pinSelected());
      await page.waitForFunction(
        () => window.__headless.state().visibility?.pins.length === 1,
      );
      // Narrow: lines 40 and 44 pass; the pinned line 45 survives unfiltered
      // by the §7 override.
      await page.evaluate(
        () => window.__headless.addFilter("regex", "^Synthetic message 4[04] \\u2014"),
      );
      await page.waitForFunction(() => {
        const v = window.__headless.state().visibility;
        return (v?.filters.length ?? 0) === 1 && v?.visibleCount === 3;
      });
      // The table refetches the narrowed sequence; line 45 is visible
      // index 2 - below the sticky header, right-clickable.
      await page.waitForFunction(
        () => document.querySelectorAll(".table-inner .row").length === 3,
      );
      await page.waitForTimeout(100);
      const row = page.getByText("Synthetic message 45").first();
      await row.click({ button: "right" });
      await page.waitForSelector('[data-menu-root]');
      // §4 presence: the selection is pinned -> Pin dim, Unpin light.
      await page.waitForFunction(() => {
        const pin = document.querySelector('[data-menu-item="pin"]');
        const unpin = document.querySelector('[data-menu-item="unpin"]');
        return (
          pin !== null && pin.hasAttribute("aria-disabled") &&
          unpin !== null && !unpin.hasAttribute("aria-disabled")
        );
      });
      await page.click('[data-menu-item="unpin"]');
      // Line 45 is not filter-matched: unpinning hides it, lines 40/44
      // remain (the §4 menu unpin removes ONLY the exact-row pin).
      await page.waitForFunction(() => {
        const v = window.__headless.state().visibility;
        return (v?.pins.length ?? 0) === 0 && v?.visibleCount === 2;
      });
      await page.waitForFunction(
        () => document.querySelectorAll(".table-inner .row").length === 2,
      );
      await page.evaluate(() => document.fonts.ready);
      await page.waitForTimeout(150);
    },
  },
];
