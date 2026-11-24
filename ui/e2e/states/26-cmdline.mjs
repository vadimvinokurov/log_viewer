// bead 7rf.1 states: §13 command line (registry flow, error channel,
// history recall); 30 extends the set for bead 7rf.2 (the persistent
// history's recall). Each state loads through the headless console against
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
  {
    // The §13.2 persistent history (bead 7rf.2): the history STORE (~
    // .logviewer/history.json equivalent) is seeded through an init script
    // (installed before the app boots, so the console constructor's single
    // history_get reads it), and ↑ recalls the store's newest entry. No
    // session submissions happen here — the loaded list alone backs the
    // cycle; the recalled field text renders as in state 29 (the table
    // band differs: nothing was executed in this state).
    name: "30-cmdline-history-persistent",
    async setup(page) {
      const url = page.url();
      await page.addInitScript(`
        window.__ipcStub = {
          async historyGet() { return [":f message 12", ":h message 31"]; },
          async historyPush() { return null; },
        };
      `);
      await page.goto(url);
      await page.waitForFunction(
        () => typeof window.__headless === "object" && window.__headless !== null,
      );
      await page.evaluate(STUB); // the visibility model (the store was already read at boot)
      await page.evaluate(() => window.__headless.load("/tmp/synthetic.log"));
      await page.waitForFunction(() => window.__headless.state().visibility !== null);
      await page.waitForFunction(() => window.__headless.cmdline().history.length === 2);
      await page.evaluate(() => window.__headless.activateCmdline());
      await page.evaluate(() => window.__headless.recallCommandHistory(-1));
      await page.waitForFunction(
        () =>
          window.__headless.cmdline().value === ":h message 31" &&
          window.__headless.commandHistory().length === 2,
      );
      await page.waitForTimeout(200);
      await WAIT_FONTS(page);
    },
  },
];
