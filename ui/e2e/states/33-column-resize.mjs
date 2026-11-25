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
  {
    name: "column-dragged",
    async setup(page) {
      await loadColumn(page);
      // Review Focus 1, pinned for real: a genuine mouse drag on a header
      // resizer must live-resize and stop when the button releases. The
      // anchor is the VISIBLE (effective) handle — review finding 2: the
      // Message dead-zone from anchoring on the hidden user width.
      const start = await page.evaluate(() => {
        const r = document.querySelector('[data-col-resizer="category"]').getBoundingClientRect();
        return { x: Math.round(r.left) + 5, y: Math.round(r.top) + 10 };
      });
      await page.mouse.move(start.x, start.y);
      await page.mouse.down();
      for (let i = 1; i <= 6; i++) await page.mouse.move(start.x + i * 10, start.y);
      await page.mouse.up();
      await page.waitForFunction(
        () => window.__headless.state().columnWidths.category === 210,
      );
      await page.waitForFunction(() => {
        const v = document.querySelector(".table-scroll");
        return v && v.scrollWidth <= v.clientWidth;
      });
      // The Message handle: parked below the remainder (user width 30),
      // then dragged RIGHT from its visible position. The new width must
      // exceed the remainder and open the horizontal overflow — anchoring
      // on the hidden user width would make this a no-op. 1120 = the
      // table viewport beside the 280-px panel; 1120 - 370 = 750 + 40.
      await page.evaluate(() => window.__headless.setColumnWidth("message", 30));
      const msg = await page.evaluate(() => {
        const r = document.querySelector('[data-col-resizer="message"]').getBoundingClientRect();
        return { x: Math.round(r.left) + 5, y: Math.round(r.top) + 10 };
      });
      await page.mouse.move(msg.x, msg.y);
      await page.mouse.down();
      for (let i = 1; i <= 4; i++) await page.mouse.move(msg.x + i * 10, msg.y);
      await page.mouse.up();
      await page.waitForFunction(() => {
        const w = window.__headless.state().columnWidths;
        const v = document.querySelector(".table-scroll");
        return w.message === 790 && v && v.scrollWidth > v.clientWidth;
      });
      // Review Focus 1: mouseup ends the drag — widths freeze without a
      // button down, and the release committed the widths.
      await page.waitForFunction(
        () =>
          window.__columnCalls.length >= 1 &&
          JSON.stringify(window.__columnCalls[window.__columnCalls.length - 1]) ===
            JSON.stringify([50, 110, 210, 790]),
      );
      await page.waitForTimeout(150);
    },
  },
];
