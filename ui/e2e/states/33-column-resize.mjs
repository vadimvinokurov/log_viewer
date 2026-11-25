// Resizable table columns (design 2026-11-25-column-resize): the widths
// driven through the headless RPC (the acceptance path; a real drag is the
// same onColumnSet call), the §4 defaults seeded from a null setting.
//
// column-resized : category 250px, message 400px — the table keeps filling
//                  the window, and a scrolled viewport does not move.
// column-overflow: message 1200px — the user-sum exceeds the viewport, the
//                  horizontal scrollbar appears and commit persists the
//                  four-entry array.
import { loadThroughConsole } from "./base.mjs";

/** The base stub predates the settings seam; attach the §15 raw commands
 *  (with the new set_column_widths) so the console seeds and persists
 *  through this stub. `null` persisted widths = the §4 defaults. */
const attachSettings = `(function () {
  const calls = [];
  window.__columnCalls = calls;
  window.__ipcStub.settingsGet = async () => ({
    history_size: 20,
    last_open_dir: "",
    default_categories_enabled: true,
    column_widths: null,
  });
  window.__ipcStub.setLastOpenDir = async () => null;
  window.__ipcStub.setColumnWidths = async (w) => { calls.push(w); return null; };
  return "settings attached";
})()`;

const loadColumn = async (page) => {
  await loadThroughConsole(page);
  await page.evaluate(attachSettings);
  await page.waitForTimeout(150);
};

export default [
  {
    name: "column-resized",
    async setup(page) {
      await loadColumn(page);
      // Review Focus 4: a scroll first, then resize — the vertical scroll
      // (and the anchor's scrollTop) must not move.
      await page.evaluate(() => window.__headless.scrollToRow(30000));
      await page.waitForFunction(() => {
        const v = window.__headless.viewport();
        return v !== null && v.scrollTop > 0;
      });
      await page.evaluate(
        () => (window.__scrollBefore = window.__headless.viewport().scrollTop),
      );
      await page.evaluate(() => {
        window.__headless.setColumnWidth("category", 250);
        window.__headless.setColumnWidth("message", 400);
      });
      await page.waitForFunction(() => {
        const w = window.__headless.state().columnWidths;
        return w.category === 250 && w.message === 400;
      });
      await page.waitForFunction(
        () => window.__headless.viewport().scrollTop === window.__scrollBefore,
      );
      // The table still fills the window: no horizontal overflow at these
      // widths (50+110+250+400=810 < viewport, Message takes the remainder).
      await page.waitForFunction(() => {
        const v = document.querySelector(".table-scroll");
        return v && v.scrollWidth <= v.clientWidth;
      });
      await page.waitForTimeout(150);
    },
  },
  {
    name: "column-overflow",
    async setup(page) {
      await loadColumn(page);
      await page.evaluate(() => {
        window.__headless.setColumnWidth("category", 250);
        window.__headless.setColumnWidth("message", 1200);
        window.__headless.commitColumnWidths();
      });
      // Review Focus 5: the persisted call carries the USER widths.
      await page.waitForFunction(
        () =>
          window.__columnCalls.length === 1 &&
          JSON.stringify(window.__columnCalls[0]) ===
            JSON.stringify([50, 110, 250, 1200]),
      );
      // The horizontal scrollbar exists: content wider than the viewport.
      await page.waitForFunction(() => {
        const v = document.querySelector(".table-scroll");
        return v && v.scrollWidth > v.clientWidth;
      });
      await page.waitForTimeout(150);
    },
  },
];
