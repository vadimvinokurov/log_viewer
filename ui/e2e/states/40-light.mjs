// Light-theme acceptance (bead fe6, 2026-11-25 restyle): the OS default in
// the harness is dark, so the restyled light palette (--table-bg, native
// checkboxes, 32px bar) needed its own rendered states. Each state reuses
// an existing state's setup verbatim — only the scheme differs.
import shell from "./00-shell.mjs";
import panel from "./18-panel.mjs";

const source = (states, name) => states.find((s) => s.name === name);

export default [
  { ...source(shell, "empty"), name: "light-empty", colorScheme: "light" },
  { ...source(shell, "loaded"), name: "light-loaded", colorScheme: "light" },
  {
    ...source(panel, "panel-categories"),
    name: "light-panel-categories",
    colorScheme: "light",
  },
];
