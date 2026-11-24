// bead 7rf.1 states: §13 command line (registry flow, error channel,
// history recall). Each state loads through the headless console against
// the base stub and drives the commands via window.__headless (text RPC);
// the field's rendered text comes from the console slice.
import { STUB } from "./base.mjs";

const WAIT_FONTS = (page) =>
  page.evaluate(() => document.fonts.ready).then(() => page.waitForTimeout(150));

const load = async (page) => {
  await page.evaluate(STUB);
  await page.evaluate(() => window.__headless.load("/tmp/synthetic.log"));
  await page.waitForFunction(() => window.__headless.state().visibility !== null);
};

export default [
  {
    // The §11.1 flat input in the bottom bar, activated by ':' over the
    // table: the field is focused and pre-filled with ':' (activation text).
    name: "26-cmdline-visible",
    async setup(page) {
      await load(page);
      await page.evaluate(() => window.__headless.activateCmdline());
      await page.waitForFunction(
        () => window.__headless.cmdline().value === ":" &&
          window.__headless.cmdline().focusTick === 1,
      );
      await page.waitForTimeout(200);
      await WAIT_FONTS(page);
    },
  },
  {
    // An executed command: :f narrows the visible sequence (the footer
    // status count drops), the field is empty again after Enter.
    name: "27-cmdline-filter-executed",
    async setup(page) {
      await load(page);
      await page.evaluate(() => window.__headless.executeCommand(":f message 12"));
      await page.waitForFunction(() => {
        const v = window.__headless.state().visibility;
        return v !== null && v.filters.length === 1 && v.visibleCount < 60000;
      });
      await page.waitForTimeout(200);
      await WAIT_FONTS(page);
    },
  },
  {
    // The §13.1 error channel: an unknown command shows «Unknown command»
    // in the footer status area and nothing is executed.
    name: "28-cmdline-error",
    async setup(page) {
      await load(page);
      await page.evaluate(() => window.__headless.executeCommand(":unknown value"));
      await page.waitForFunction(() => window.__headless.state().error === "Unknown command");
      await page.waitForTimeout(200);
      await WAIT_FONTS(page);
    },
  },
  {
    // The §13.2 in-session recall: ↑ in the field pulls the last submitted
    // command back into the field (history built by two executed commands).
    name: "29-cmdline-history",
    async setup(page) {
      await load(page);
      await page.evaluate(() => window.__headless.executeCommand(":f message 12"));
      await page.evaluate(() => window.__headless.executeCommand(":h message 31"));
      await page.waitForFunction(
        () => window.__headless.state().visibility?.highlights.length === 1,
      );
      await page.evaluate(() => window.__headless.activateCmdline());
      await page.evaluate(() => window.__headless.recallCommandHistory(-1));
      await page.waitForFunction(
        () =>
          window.__headless.cmdline().value === ":h message 31" &&
          window.__headless.cmdline().history.length === 2,
      );
      await page.waitForTimeout(200);
      await WAIT_FONTS(page);
    },
  },
];
