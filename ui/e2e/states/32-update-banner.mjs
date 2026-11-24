// plan 2026-11-25 states: the auto-update banner, one golden per visible
// phase (available | downloading | installed | uptodate | failed). Each
// state loads through the headless console against the base stub, extends
// window.__ipcStub with the RAW UpdaterCommands (check / downloadAndInstall
// / relaunch — the task-3 seam) and drives a manual check or an install via
// window.__headless (text RPC). The constructor's AUTO probe fires against
// the unblessed raw stub and silences itself (Review Focus 1), so no state
// races it: every assertion waits for the exact phase.
import { STUB } from "./base.mjs";

const WAIT_FONTS = (page) =>
  page.evaluate(() => document.fonts.ready).then(() => page.waitForTimeout(150));

const load = async (page) => {
  await page.evaluate(STUB);
  await page.evaluate(() => window.__headless.load("/tmp/synthetic.log"));
  await page.waitForFunction(() => window.__headless.state().visibility !== null);
};

/** Extends the loaded raw IPC stub with the three updater methods.
 *  hang = a downloadAndInstall that never resolves → the downloading gate. */
const blessUpdater = (page, opts) =>
  page.evaluate((o) => {
    const stub = (window).__ipcStub ?? ({});
    stub.check = () =>
      o.failCheck
        ? Promise.reject(new Error(o.failCheck))
        : Promise.resolve(o.update ?? null);
    stub.downloadAndInstall = () =>
      o.hang
        ? new Promise(() => {})
        : o.failInstall
          ? Promise.reject(new Error(o.failInstall))
          : Promise.resolve();
    stub.relaunch = () => Promise.resolve();
    (window).__ipcStub = stub;
  }, opts);

const phase = (page, want) =>
  page.waitForFunction(
    (w) => window.__headless.state().update !== undefined &&
      window.__headless.state().update.phase === w,
    want,
  );

export default [
  {
    name: "32-update-available",
    async setup(page) {
      await load(page);
      await blessUpdater(page, { update: { version: "0.2.0", currentVersion: "0.1.0" } });
      await page.evaluate(() => window.__headless.checkUpdates("manual"));
      await phase(page, "available");
      await WAIT_FONTS(page);
    },
  },
  {
    name: "33-update-downloading",
    async setup(page) {
      await load(page);
      await blessUpdater(page, { update: { version: "0.2.0", currentVersion: "0.1.0" }, hang: true });
      await page.evaluate(() => window.__headless.checkUpdates("manual"));
      await phase(page, "available");
      // Fire-and-forget: the download here never resolves (hang: true), so
      // awaiting the install promise would block the evaluate forever — the
      // phase gate below is the assertion, the promise is nobody's.
      await page.evaluate(() => { void window.__headless.installUpdate(); });
      await phase(page, "downloading");
      await WAIT_FONTS(page);
    },
  },
  {
    name: "34-update-installed",
    async setup(page) {
      await load(page);
      await blessUpdater(page, { update: { version: "0.2.0", currentVersion: "0.1.0" } });
      await page.evaluate(() => window.__headless.checkUpdates("manual"));
      await phase(page, "available");
      await page.evaluate(() => window.__headless.installUpdate());
      await phase(page, "installed");
      await WAIT_FONTS(page);
    },
  },
  {
    name: "35-update-uptodate",
    async setup(page) {
      await load(page);
      await blessUpdater(page, { update: null });
      await page.evaluate(() => window.__headless.checkUpdates("manual"));
      await phase(page, "uptodate");
      await WAIT_FONTS(page);
    },
  },
  {
    name: "36-update-failed",
    async setup(page) {
      await load(page);
      await blessUpdater(page, { failCheck: "connection refused" });
      await page.evaluate(() => window.__headless.checkUpdates("manual"));
      await phase(page, "failed");
      await WAIT_FONTS(page);
    },
  },
];
