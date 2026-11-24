// Showcase state for the context menu (?show=menu) - no IPC stub needed, the
// showcase does not touch app state. The base render already waited for the
// console, so setup only navigates to the showcase URL and waits for the
// component: the harness serves a random port, so the state cannot pin the
// URL itself and derives the origin from the page it was loaded on.
export default [
  {
    name: "menu-showcase",
    async setup(page) {
      const origin = new URL(page.url()).origin;
      await page.goto(origin + "/?show=menu");
      await page.waitForSelector('[data-variant="default"]');
      await page.evaluate(() => document.fonts.ready);
      await page.waitForTimeout(150);
    },
  },
];
