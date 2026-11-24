// q1f.1 state: the Pinned tab (§10.1) on live console state - two pin rules
// (`:pn 31`, a plain rule) through the headless RPC, one of them toggled off
// so the tab shows a dimmed entry; the panel switches to the Pinned tab.
import { STUB } from "./base.mjs";

export default [
  {
    name: "20-pins-panel",
    async setup(page) {
      await page.evaluate(STUB);
      await page.evaluate(() => window.__headless.load("/tmp/synthetic.log"));
      await page.waitForFunction(() => window.__headless.state().visibility !== null);
      // Two pin rules, the second disabled (§10.1 checkbox semantics).
      await page.evaluate(() => window.__headless.addPin("lineno", "31"));
      await page.evaluate(() => window.__headless.addPin("plain", "raw 45"));
      await page.evaluate(() => window.__headless.setPinEnabled(1, false));
      await page.waitForFunction(
        () => window.__headless.state().visibility?.pins.length === 2,
      );
      await page.evaluate(() => window.__headless.setPanelTab("pinned"));
      await page.waitForFunction(() => window.__headless.state().panel.tab === "pinned");
      await page.evaluate(() => document.fonts.ready);
      await page.waitForTimeout(150);
    },
  },
];
