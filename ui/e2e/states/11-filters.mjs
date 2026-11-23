// State module for the Filters tab showcase (dsq.2, §10-1 panel anatomy):
// the demo list is rendered locally by the component, so no IPC stub is
// needed - only the headless console has to be ready. The harness state URL
// must be absolute (Playwright has no baseURL), so resolve ?show=filters
// against the page URL the harness just loaded.
import { waitConsole } from "./base.mjs";

export default [
  {
    name: "filters-showcase",
    async setup(page) {
      const url = new URL(page.url());
      url.search = "?show=filters";
      await page.goto(url.href);
      await waitConsole(page);
    },
  },
];
