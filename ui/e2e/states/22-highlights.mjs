// exx.2 states: §9 highlights (exx.2 bead, goldens list).
// Each state loads through the headless console against the base stub
// (which now mirrors the RAW highlight commands + byte-offset spans) and
// puts the panel on the Highlights tab where the tab participates.
import { STUB } from "./base.mjs";

const WAIT_FONTS = (page) =>
  page.evaluate(() => document.fonts.ready).then(() => page.waitForTimeout(150));

const openHighlightsTab = async (page) => {
  await page.evaluate(() => window.__headless.setPanelTab("highlights"));
  await page.waitForFunction(() => window.__headless.state().panel.tab === "highlights");
};

export default [
  {
    // Two overlapping rules on the visible rows: the Message column shows
    // the stacked translucent tints (§9), the panel lists both rules.
    name: "22-highlights-overlap",
    async setup(page) {
      await page.evaluate(STUB);
      await page.evaluate(() => window.__headless.load("/tmp/synthetic.log"));
      await page.waitForFunction(() => window.__headless.state().visibility !== null);
      await page.evaluate(() => window.__headless.addHighlight("plain", "message 12"));
      await page.evaluate(() => window.__headless.addHighlight("plain", "12"));
      await page.waitForFunction(
        () => window.__headless.state().visibility?.highlights.length === 2,
      );
      await openHighlightsTab(page);
      await page.evaluate(() => window.__headless.scrollToRow(1213));
      await page.waitForTimeout(200);
      await WAIT_FONTS(page);
    },
  },
  {
    // A disabled rule: dimmed in the tab and NO spans painted anywhere; an
    // enabled rule beside it keeps its tint (§9).
    name: "23-highlights-disabled",
    async setup(page) {
      await page.evaluate(STUB);
      await page.evaluate(() => window.__headless.load("/tmp/synthetic.log"));
      await page.waitForFunction(() => window.__headless.state().visibility !== null);
      await page.evaluate(() => window.__headless.addHighlight("plain", "harness"));
      await page.evaluate(() => window.__headless.addHighlight("plain", "deterministic"));
      await page.evaluate(() => window.__headless.setHighlightEnabled(0, false));
      await page.waitForFunction(
        () => window.__headless.state().visibility?.highlights.length === 2,
      );
      await openHighlightsTab(page);
      await page.waitForTimeout(200);
      await WAIT_FONTS(page);
    },
  },
  {
    // A user-picked color: set_highlight_color override — the dot in the tab
    // and the span tint in the Message column both use the picked hex; the
    // pattern crosses the em-dash, exercising the byte-offset conversion.
    name: "24-highlights-color-picked",
    async setup(page) {
      await page.evaluate(STUB);
      await page.evaluate(() => window.__headless.load("/tmp/synthetic.log"));
      await page.waitForFunction(() => window.__headless.state().visibility !== null);
      await page.evaluate(() => window.__headless.addHighlight("plain", "— deterministic"));
      await page.waitForFunction(
        () => window.__headless.state().visibility?.highlights.length === 1,
      );
      await page.evaluate(() => window.__headless.setHighlightColor(0, "#ff00aa"));
      await page.waitForFunction(
        () => window.__headless.state().visibility?.highlights[0]?.overrideColor === "#ff00aa",
      );
      await openHighlightsTab(page);
      await page.waitForTimeout(200);
      await WAIT_FONTS(page);
    },
  },
  {
    // The :hn whole-line case: a lineno rule tints the ENTIRE message of its
    // row (the viewport centers line 31 through the scroll RPC).
    name: "25-highlights-lineno",
    async setup(page) {
      await page.evaluate(STUB);
      await page.evaluate(() => window.__headless.load("/tmp/synthetic.log"));
      await page.waitForFunction(() => window.__headless.state().visibility !== null);
      await page.evaluate(() => window.__headless.addHighlight("lineno", "31"));
      await page.waitForFunction(
        () => window.__headless.state().visibility?.highlights.length === 1,
      );
      await openHighlightsTab(page);
      await page.evaluate(() => window.__headless.scrollToRow(31));
      await page.waitForTimeout(200);
      await WAIT_FONTS(page);
    },
  },
];
