// Showcase state for the LevelBar (?show=levels) - no IPC stub needed, the
// showcase does not touch app state. The base render already waited for the
// console, so setup only navigates to the showcase URL and waits for the
// component: the harness serves a random port, so the state cannot pin the
// URL itself and derives the origin from the page it was loaded on.
export default [
  {
    name: "levels-showcase",
    async setup(page) {
      const origin = new URL(page.url()).origin;
      await page.goto(origin + "/?show=levels");
      await page.waitForSelector('[data-variant="default"]');
      // Let the data mono webfont (IBM Plex Mono) finish loading so the
      // golden does not race between fallback and real glyphs.
      await page.evaluate(() => document.fonts.ready);
      await page.waitForTimeout(150);
    },
  },
];
