/**
 * Showcase entries for the LevelBar (?show=levels): three variants for the
 * visual harness - the mock counts with every level on, the same with two
 * levels toggled off (dimmed, strikethrough count), and all-zero counts
 * (§11: count 0 means no count is shown). The toggling behavior itself is
 * covered by unit tests, so the gallery stays stateless.
 */
import { LevelBar } from "../LevelBar.tsx";
import type { EnabledLevels, Level, LevelCounts } from "../levelBar";

const MIXED_COUNTS: LevelCounts = {
  critical: 3,
  error: 172,
  warning: 2041,
  msg: 4_200_000,
  debug: 681_000,
  trace: 96_000,
};

const ALL_ENABLED: EnabledLevels = {
  critical: true,
  error: true,
  warning: true,
  msg: true,
  debug: true,
  trace: true,
};

/* §2.1 preview: two levels toggled off; wiring to the store is a later bead. */
const withOff = (off: Level[]): EnabledLevels => {
  const enabled = { ...ALL_ENABLED };
  for (const level of off) {
    enabled[level] = false;
  }
  return enabled;
};

// The showcase is a static gallery; toggling is a no-op here.
const noToggle = (_level: Level): void => {};

export const levelsShowcase: Record<string, React.ReactNode> = {
  // The canonical mock state (UI_DESIGN "Main window"): WARNING toggled off -
  // dimmed with a strikethrough count; the design oracle compares this one.
  "warning-off": <LevelBar counts={MIXED_COUNTS} enabled={withOff(["warning"])} onToggle={noToggle} />,
  default: <LevelBar counts={MIXED_COUNTS} enabled={ALL_ENABLED} onToggle={noToggle} />,
  off: (
    <LevelBar counts={MIXED_COUNTS} enabled={withOff(["warning", "debug"])} onToggle={noToggle} />
  ),
  zeros: (
    <LevelBar
      counts={{ critical: 0, error: 0, warning: 0, msg: 0, debug: 0, trace: 0 }}
      enabled={ALL_ENABLED}
      onToggle={noToggle}
    />
  ),
};
