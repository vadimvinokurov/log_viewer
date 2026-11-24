//! The auto-update banner (plan 2026-11-25): a floating non-blocking chip
//! over the table. The component only wires the console's update slice to
//! markup — every transition lives in updates.ts, every action in
//! uiConsole.ts (building-testable-apps rule 4/1). Copy is English per the
//! project language rule.

import { useSyncExternalStore, type ReactNode } from "react";
import { console_ } from "./uiConsole";
import { bannerVisible, type UpdateState } from "./updates";

export function UpdateBanner(): ReactNode {
  const update = useSyncExternalStore(console_.subscribe, console_.getUpdate);
  if (!bannerVisible(update)) {
    return null;
  }
  return <UpdateBannerView update={update} />;
}

function UpdateBannerView({ update }: { update: UpdateState }): ReactNode {
  const body = bannerBody(update);
  const allowDismiss =
    update.phase === "available" || update.phase === "uptodate" || update.phase === "failed";
  return (
    <div className="update-banner" role="status">
      {update.phase === "available" || update.phase === "failed" ? (
        <button
          className="update-banner-action"
          onClick={() =>
            void (update.phase === "available"
              ? console_.installUpdate()
              : console_.checkForUpdates("manual"))
          }
        >
          {update.phase === "available" ? "Install" : "Retry"}
        </button>
      ) : null}
      <span className="update-banner-text">{body}</span>
      {allowDismiss ? (
        <button
          className="update-banner-dismiss"
          aria-label="Dismiss update notification"
          onClick={() => console_.dismissUpdate()}
        >
          ×
        </button>
      ) : null}
    </div>
  );
}

function bannerBody(update: UpdateState): string {
  switch (update.phase) {
    case "available":
      return `Update ${update.availableVersion ?? "—"} available`;
    case "downloading":
      return "Downloading update…";
    case "installed":
      return "Update installed — restarting…";
    case "uptodate":
      return "You're on the latest version.";
    case "failed":
      return `Update failed: ${update.error ?? "unknown error"}`;
    default:
      return "";
  }
}
