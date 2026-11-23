import { STUB, waitConsole } from "./base.mjs";

export default [
  {
    name: "empty",
    async setup(page) {
      await page.evaluate(STUB);
    },
  },
  {
    name: "loaded",
    async setup(page) {
      await page.evaluate(STUB);
      await page.evaluate(() => window.__headless.load("/tmp/synthetic.log"));
      await page.waitForFunction(() => window.__headless.state().file !== null);
      await page.waitForTimeout(150);
    },
  },
  {
    name: "loaded-scrolled",
    async setup(page) {
      await page.evaluate(STUB);
      await page.evaluate(() => window.__headless.load("/tmp/synthetic.log"));
      await page.waitForFunction(() => window.__headless.state().file !== null);
      await page.waitForTimeout(150);
      await page.evaluate(() => window.__headless.scrollToRow(31000));
      await page.waitForTimeout(250);
    },
  },
  {
    name: "error",
    async setup(page) {
      await page.evaluate(
        `(function () {
          window.__ipcStub = { pickFile: async () => null, loadFile: async () => { throw new Error("boom: file unreadable"); }, getRows: async () => [] };
          return "error stub";
        })()`,
      );
      await page.evaluate(() => window.__headless.load("/missing.log"));
      await page.waitForFunction(() => window.__headless.state().error !== null);
    },
  },
];
