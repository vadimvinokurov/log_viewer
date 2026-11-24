// 2wu.1 state: the §8 search panel. Open with a query (counter + the
// selected match row), the regex tumbler, search scoped to visible rows
// (a hidden level never matches), and cyclic wrap. All behavior checks are
// numbers through window.__headless (search slice + viewport), never DOM.
// Deterministic synthetic data only (never test_logs contents).
import { loadThroughConsole } from "./base.mjs";

/** Waits until the search recompute settles, the scroll (if the match
 *  centering moved it) stops changing, and fonts render. */
async function settleSearch(page, total) {
  await page.waitForFunction((expected) => {
    const search = window.__headless.state().search;
    return search.open && search.total === expected;
  }, total, { timeout: 15000 });
  for (let i = 0; i < 40; i++) {
    const stable = await page.evaluate(() => {
      const vp = window.__headless.viewport();
      return (vp?.anchor ?? null) !== null ? vp.scrollTop : -1;
    });
    await page.waitForTimeout(150);
    const settled = await page.evaluate(() => {
      const vp = window.__headless.viewport();
      return vp === null ? -1 : vp.scrollTop;
    });
    if (stable === settled && settled >= 0) {
      break;
    }
  }
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(250);
}

/** Reads the search slice + selection and throws on any mismatch. */
async function assertSlice(page, expected) {
  return page.evaluate((expected) => {
    const snap = window.__headless.state();
    const s = snap.search;
    const fail = (what) => {
      throw new Error(what + " (search=" + JSON.stringify(s) + ", selection=" + JSON.stringify(snap.selection.selected) + ")");
    };
    if (expected.open !== undefined && s.open !== expected.open) fail("search.open");
    if (expected.mode !== undefined && s.mode !== expected.mode) fail("search.mode");
    if (expected.query !== undefined && s.query !== expected.query) fail("search.query");
    if (expected.total !== undefined && s.total !== expected.total) fail("search.total");
    if (expected.currentRank !== undefined && s.currentRank !== expected.currentRank) {
      fail("search.currentRank");
    }
    if (
      expected.currentVisibleIndex !== undefined &&
      s.currentVisibleIndex !== expected.currentVisibleIndex
    ) {
      fail("search.currentVisibleIndex");
    }
    if (
      expected.selected !== undefined &&
      JSON.stringify(snap.selection.selected) !== JSON.stringify(expected.selected)
    ) {
      fail("selection");
    }
    return "ok";
  }, expected);
}

export default [
  {
    // Panel open with a query: counter «1 / 1», the match row selected and
    // centered. The start rule: the only match (visible index 11) sits
    // above the selection (500), so the cyclic read wraps to it.
    name: "search-open",
    async setup(page) {
      await loadThroughConsole(page);
      await page.waitForFunction(() => window.__headless.state().visibility !== null);
      await page.evaluate(() => window.__headless.select(500, "click"));
      await page.evaluate(() => window.__headless.openSearch());
      // "message 12 " (trailing space) is contained only in line 12's text.
      await page.evaluate(() => window.__headless.setSearchQuery("message 12 "));
      await settleSearch(page, 1);
      await assertSlice(page, {
        open: true,
        query: "message 12 ",
        total: 1,
        currentRank: 1,
        currentVisibleIndex: 11,
        selected: [11],
      });
    },
  },
  {
    // Regex tumbler on: the anchored regex matches exactly line 42; plain
    // substring of the same text would match none (the tumblers really do
    // change the mode).
    name: "search-regex",
    async setup(page) {
      await loadThroughConsole(page);
      await page.waitForFunction(() => window.__headless.state().visibility !== null);
      await page.evaluate(() => window.__headless.openSearch());
      await page.evaluate(() => window.__headless.setSearchMode("regex"));
      await page.evaluate(() => window.__headless.setSearchQuery("message 42\\b"));
      await settleSearch(page, 1);
      await assertSlice(page, {
        open: true,
        mode: "regex",
        query: "message 42\\b",
        total: 1,
        currentRank: 1,
        currentVisibleIndex: 41,
        selected: [41],
      });
    },
  },
  {
    // Scope: every "msg"-level row hidden — the search counts VISIBLE rows
    // only (60000 - 22500 = 37500) and the current match is the selection
    // itself (every visible row contains the word).
    name: "search-hidden-scope",
    async setup(page) {
      await loadThroughConsole(page);
      await page.waitForFunction(() => window.__headless.state().visibility !== null);
      await page.evaluate(() => window.__headless.setLevel("msg", false));
      await page.waitForFunction(() => window.__headless.state().visibility?.visibleCount === 37500);
      await page.evaluate(() => {
        window.__headless.select(37400, "click");
        window.__headless.openSearch();
        window.__headless.setSearchQuery("deterministic");
      });
      await settleSearch(page, 37500);
      await assertSlice(page, {
        total: 37500,
        currentRank: 37401,
        currentVisibleIndex: 37400,
        selected: [37400],
      });
    },
  },
  {
    // Cyclic wrap from the top: Up from the first match wraps to the last
    // visible row («60000 / 60000»), Down wraps back to the first.
    name: "search-cyclic-wrap",
    async setup(page) {
      await loadThroughConsole(page);
      await page.waitForFunction(() => window.__headless.state().visibility !== null);
      await page.evaluate(() => {
        window.__headless.openSearch();
        window.__headless.setSearchQuery("deterministic");
      });
      await settleSearch(page, 60000);
      await assertSlice(page, {
        total: 60000,
        currentRank: 1,
        currentVisibleIndex: 0,
        selected: [0],
      });
      await page.evaluate(() => window.__headless.nextMatch(-1));
      await page.waitForFunction(
        () => window.__headless.state().search.currentVisibleIndex === 59999,
        undefined,
        { timeout: 15000 },
      );
      await settleSearch(page, 60000);
      await assertSlice(page, {
        total: 60000,
        currentRank: 60000,
        currentVisibleIndex: 59999,
        selected: [59999],
      });
      await page.evaluate(() => window.__headless.nextMatch(1));
      await page.waitForFunction(
        () => window.__headless.state().search.currentVisibleIndex === 0,
        undefined,
        { timeout: 15000 },
      );
      await assertSlice(page, {
        currentRank: 1,
        currentVisibleIndex: 0,
        selected: [0],
      });
    },
  },
];
