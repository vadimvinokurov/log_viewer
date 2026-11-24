//! Pure update state machine (plan 2026-11-25, GitHub Release builds +
//! in-app auto-update). The updater is the app's ONLY network call (a
//! deliberate exception to FUNCTIONAL_SPEC §1 «no networking»); the design
//! doc's resilience constraint holds here: this module is deterministic and
//! records failures source-honestly — the AUTO failure silence lives in the
//! console wiring, never in this reducer.

/** Lifecycle of the update flow. `idle` → `checking` → `available` →
 *  `downloading` → `installed` (restart); `failed` and `uptodate` are
 *  terminal states the user leaves via a re-check or a dismissal. */
export type UpdatePhase =
  | "idle"
  | "checking"
  | "available"
  | "downloading"
  | "installed"
  | "uptodate"
  | "failed";

/** Who asked for the check: the constructor's automatic startup probe or an
 *  explicit user command (`check-updates` / the banner's Retry). */
export type UpdateSource = "auto" | "manual";

export interface UpdateState {
  phase: UpdatePhase;
  source: UpdateSource;
  /** The published version the updater offered; null unless seen. */
  availableVersion: string | null;
  /** The failure message for the failed banner; null otherwise. */
  error: string | null;
}

export function initialUpdateState(): UpdateState {
  return { phase: "idle", source: "auto", availableVersion: null, error: null };
}

export type UpdateEvent =
  | { kind: "update-check-start"; source: UpdateSource }
  | { kind: "update-available"; version: string }
  | { kind: "update-none" }
  | { kind: "update-download-start" }
  | { kind: "update-installed" }
  | { kind: "update-failed"; error: string }
  | { kind: "update-dismiss" };

/** Guard rules (pinned by updates.test.ts):
 *  - `update-check-start` applies from `idle` / `failed` / `uptodate` and
 *    ALSO from `checking` (the constructor's auto probe races the first
 *    user command: a manual check must never be locked out by the startup
 *    probe — both probe the same endpoint, so a re-arm from `checking` is a
 *    clean restart with the new source; available/downloading stay locked);
 *    it resets error/availableVersion;
 *  - `update-available` applies only while `checking`;
 *  - `update-download-start` only from `available`;
 *  - `update-installed` only from `downloading`;
 *  - `update-none` from `checking`: auto → `idle` (silent), manual →
 *    `uptodate` (the only quiet success the user chose to learn about);
 *  - `update-failed` applies from `checking` / `downloading`. */
export function reduceUpdate(state: UpdateState, event: UpdateEvent): UpdateState {
  switch (event.kind) {
    case "update-check-start": {
      if (state.phase !== "idle" && state.phase !== "failed" && state.phase !== "uptodate" && state.phase !== "checking") {
        return state;
      }
      return { phase: "checking", source: event.source, availableVersion: null, error: null };
    }
    case "update-available":
      if (state.phase !== "checking") {
        return state;
      }
      return { ...state, phase: "available", availableVersion: event.version };
    case "update-none":
      if (state.phase !== "checking") {
        return state;
      }
      return state.source === "auto"
        ? initialUpdateState()
        : { ...state, phase: "uptodate" };
    case "update-download-start":
      if (state.phase !== "available") {
        return state;
      }
      return { ...state, phase: "downloading" };
    case "update-installed":
      if (state.phase !== "downloading") {
        return state;
      }
      return { ...state, phase: "installed", error: null };
    case "update-failed":
      if (state.phase !== "checking" && state.phase !== "downloading") {
        return state;
      }
      return { ...state, phase: "failed", error: event.error };
    case "update-dismiss":
      return initialUpdateState();
  }
}

/** Three-component semver compare: numeric per segment, missing segments
 *  count as 0; a release outranks its own prerelease suffix. Returns −1/0/1
 *  for a<b / a==b / a>b. Malformed input degrades to lexicographic-safe 0
 *  segments (defensive — the plugin already picked the release). */
export function compareVersions(a: string, b: string): number {
  const split = (v: string): { core: number[]; pre: boolean } => {
    const minus = v.indexOf("-");
    const core = (minus === -1 ? v : v.slice(0, minus))
      .split(".")
      .map((part) => {
        const n = Number(part);
        return Number.isInteger(n) && n >= 0 ? n : 0;
      });
    return { core, pre: minus !== -1 };
  };
  const A = split(a);
  const B = split(b);
  const len = Math.max(A.core.length, B.core.length);
  for (let i = 0; i < len; i++) {
    const diff = (A.core[i] ?? 0) - (B.core[i] ?? 0);
    if (diff !== 0) {
      return diff < 0 ? -1 : 1;
    }
  }
  // Equal cores: a prerelease string is older than its own release.
  if (A.pre !== B.pre) {
    return B.pre ? 1 : -1;
  }
  return 0;
}

/** The banner is a floating chip: the user asked to learn something (a
 *  manual check result, an offer, a failure). The idle state and the
 *  automatic startup probe's checking phase stay invisible. */
export function bannerVisible(state: UpdateState): boolean {
  return (
    state.phase === "available" ||
    state.phase === "downloading" ||
    state.phase === "installed" ||
    state.phase === "uptodate" ||
    state.phase === "failed"
  );
}
