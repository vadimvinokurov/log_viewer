// qt7.2 selection state: loaded table, rows selected through the text RPC
// (click + toggle + shift-range), goldens capture the accent-tint rows.
import { STUB } from "./base.mjs";

export default [
  {
    name: "13-selection",
    async setup(page) {
      await page.evaluate(STUB);
      await page.evaluate(() => window.__headless.load("/tmp/synthetic.log"));
      await page.waitForFunction(() => window.__headless.state().screen === "loaded");
      await page.evaluate(() => window.__headless.select(30, "click"));
      await page.evaluate(() => window.__headless.select(31, "toggle"));
      await page.evaluate(() => window.__headless.select(34, "range"));
      await page.evaluate(() => document.fonts.ready);
      await page.waitForTimeout(150);
    },
  },
];
