// qt7.3 state: the viewport anchors on a refilter (§4 last bullet). The stub
// is loaded and scrolled deep into the file, then the trace level is toggled
// off through the text RPC; the anchor row must keep its identity and its
// captured viewport offset (numbers via window.__headless.viewport(), never
// DOM), and the horizontal position must not move (§4). Deterministic
// synthetic data only.
import { loadThroughConsole } from "./base.mjs";

/** Scrolls to `lineNo` and waits until the live anchor reflects the layout. */
async function scrollAndSettle(page, lineNo) {
  await page.evaluate((l) => window.__headless.scrollToRow(l), lineNo);
  await page.waitForFunction(
    () => {
      const vp = window.__headless.viewport();
      return vp !== null && vp.anchor !== null && vp.anchor.line !== null;
    },
    { timeout: 15000 },
  );
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(250);
}

export default [
  {
    name: "anchor-scrolled-refilter",
    async setup(page) {
      await loadThroughConsole(page);
      await page.waitForFunction(() => window.__headless.state().visibility !== null);
      await scrollAndSettle(page, 30000);

      const before = await page.evaluate(() => {
        const vp = window.__headless.viewport();
        return {
          line: vp.anchor.line,
          offsetPx: vp.anchorOffsetPx,
          scrollLeft: vp.scrollLeft,
          scrollTop: vp.scrollTop,
        };
      });

      await page.evaluate(() => window.__headless.setLevel("trace", false));
      // The snapshot refetch + chunk refill settle (stub: 60000 lines, trace
      // every 8th line -> 52500 visible).
      await page.waitForFunction(() => {
        const snap = window.__headless.state();
        const trace = snap.visibility?.levels.find((l) => l.level === "trace");
        return trace?.enabled === false && snap.visibility?.visibleCount === 52500;
      });

      // The anchor step resolves over 1-row probes and repositions; wait
      // until the anchored identity is back (line unchanged, offset
      // unchanged) - a mismatch here throws on the evaluate below.
      await page.waitForFunction(
        (expected) => {
          const vp = window.__headless.viewport();
          if (!vp || vp.anchor === null) return false;
          return (
            vp.anchor.line === expected.line &&
            vp.anchorOffsetPx === expected.offsetPx &&
            vp.scrollLeft === expected.scrollLeft
          );
        },
        before,
        { timeout: 20000 },
      );
      await page.evaluate(() => document.fonts.ready);
      await page.waitForTimeout(250);

      await page.evaluate((expected) => {
        const vp = window.__headless.viewport();
        if (vp === null || vp.anchor === null) {
          throw new Error("no anchor after refilter");
        }
        if (vp.anchor.line !== expected.line) {
          throw new Error(
            "anchor line jumped: " + vp.anchor.line + " != " + expected.line,
          );
        }
        if (vp.anchorOffsetPx !== expected.offsetPx) {
          throw new Error(
            "anchor offset moved: " + vp.anchorOffsetPx + " != " + expected.offsetPx,
          );
        }
        if (vp.scrollLeft !== expected.scrollLeft) {
          throw new Error("horizontal position drifted (§4)");
        }
        const snap = window.__headless.state();
        if (snap.selection.selected.length !== 0) {
          throw new Error("empty selection did not stay empty");
        }
      }, before);
    },
  },
];
