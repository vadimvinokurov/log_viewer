# Design: GitHub Release builds + in-app auto-update

Date: 2026-11-25. Owner decisions recorded during brainstorming.

## Intent and why

The repository (`github.com/vadimvinokurov/log_viewer`) is public. The app had no
distribution story: no tags, no CI, no installer artifacts, no update mechanism. Every
user had to build from source. Goals:

- **Tag-driven releases**: pushing a tag `vX.Y.Z` produces a GitHub Release with
  installable artifacts (macOS dmg, Windows NSIS installer) plus the Tauri updater
  manifest `latest.json`.
- **In-app auto-update**: installed builds check GitHub at startup and offer
  one-click updates; updater transport = `tauri-plugin-updater` reading `latest.json`
  from the latest release.
- **Update UX chosen by owner**: automatic check at startup (silent, non-blocking),
  an unobtrusive notification when a newer version exists ("update available →
  Install"), plus a manual "Check for updates" entry point.

## Goals

1. `.github/workflows/release.yml`: triggered on tag push `v*`; gates on the test
   suite; builds macOS universal and Windows NSIS; creates the Release and uploads
   artifacts + `latest.json`; signs updater artifacts from GitHub secrets.
2. App gains `tauri-plugin-updater` + `tauri-plugin-process` (for the post-install
   restart); update logic in a pure, vitest-tested module; UI is a thin notification
   layer.
3. Update keys: a Tauri minisign keypair generated once; public key lives in
   `tauri.conf.json`, private key + password in GitHub secrets — the app refuses
   unsigned update payloads.
4. README documents installation, including the unsigned-build caveats below.

## Non-goals

- Code signing / notarization (macOS Developer ID, Windows Authenticode) — deferred;
  the workflow is structured so certificates later drop in as secrets without
  restructuring.
- Linux builds (spec §1 bounds platforms to macOS + Windows).
- Update channels (beta/nightly), delta updates, forced/mandatory updates.
- Generic CI-on-push workflow (tests run inside the release workflow; a standalone
  push CI is separate future work if wanted).

## Constraints

- **Spec §1 "no networking"** — the updater is the single sanctioned network call
  (HTTPS to `github.com`/`objects.githubusercontent.com`); recorded as a deliberate
  owner exception to the spec.
- **Disk-error style resilience (cf. §15)**: updater failures (offline, HTTP error,
  bad signature) never abort the app and are surfaced at most as a quiet failure in
  the notification UI.
- **Unsigned builds**: no Apple Developer account. First macOS launch requires the
  "Open Anyway" path in System Settings; Windows shows a SmartScreen warning. The
  updater itself is unaffected (minisign-signed payloads, user-approved once).
- The functional specification (`FUNCTIONAL_SPEC.html`, Russian) does not yet
  describe the updater; a spec section should be added by the owner as part of close
- out (the docs note covers the behavior precisely).

## Approaches considered

| Approach | Verdict |
|---|---|
| Official `tauri-apps/tauri-action` GitHub Action | **Chosen.** Handles build orchestration, Release creation, `latest.json` generation, and updater signing (`TAURI_SIGNING_PRIVATE_KEY` secret) out of the box; most-maintained path, least bespoke code. |
| Hand-rolled workflow (`cargo tauri build` + `gh release create` + manifest script) | Rejected: reimplements what tauri-action does, more code to keep correct across OS runners. |
| Separate update host (own static JSON server) instead of GitHub Releases | Rejected: no infra to run it; GitHub Release `latest.json` is the supported free path. |

## The how, as decided with the owner

- **Audience**: public repository, strangers installing without hand-holding.
- **Signing**: none for now (no Apple Developer account); secrets-ready workflow.
- **Updater keypair**: a fresh minisign pair generated for this app (owner confirmed
  reusing the other project's key is possible but prefers isolation). Private key +
  password go into GitHub secrets; owner keeps a local backup copy.
- **Platforms**: macOS **universal** (aarch64 + x86_64 in one dmg) and Windows **NSIS
  x64** (the officially recommended updater-friendly installer).
- **Update check**: automatic at startup **and** a manual "Check for updates" entry.
- **Version single source**: `tauri.conf.json` `version` (bundled into installers and
  manifests); release workflow asserts the pushed tag equals it and fails otherwise.
- **Start-check UX**: unconditional (no toggle, no settings surface); manual check is
  a builtin command-line command (cf. §13), zero extra chrome, no §15 changes.
- **Bootstrap handoff**: agent stops after committing locally and creating the tag;
  the owner pushes `v0.1.0` (release version stays 0.1.0) and approves the first
  Actions run; secrets are set by the owner in the Settings UI or by the agent via
  `gh secret set` — only on an explicit owner go-ahead.

## Parts the builder plans from

1. **Updater plumbing**: `tauri signer generate` keypair; `bundle.createUpdaterArtifacts`
   enabled in `tauri.conf.json`; updater/process plugins registered in `lib.rs` with
   `updater:default`/`process:default` capabilities; endpoint
   `https://github.com/vadimvinokurov/log_viewer/releases/latest/download/latest.json`.
2. **Update-check module** (pure, vitest): compare current vs published version
   (semver), startup-check cadence (once per launch), state machine
   (idle → checking → available → downloading → installing / failed / up-to-date).
3. **UI**: small non-blocking notification (positioned so it cannot cover the table
   content), Install action (download + restart via `tauri-plugin-process`), manual
   check entry; headless-tested per `building-testable-apps` rules (state snapshots +
   rendered state, golden PNGs re-baselined for the new elements).
4. **Release workflow**: tag push `v*` → job gates (cargo test, vitest, e2e) →
   matrix build (macos universal: `aarch64,x86_64`; windows x64 nsis) → tauri-action
   creates Release, uploads installers + `latest.json` (updater artifacts signed via
   `TAURI_SIGNING_PRIVATE_KEY` + `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` secrets).
5. **Bootstrap release**: bump version if desired, tag `v0.1.0`; the tag must carry the
   updater config so every installed build can self-update thereafter.
6. **README**: installers link, Gatekeeper ("Open Anyway") and SmartScreen ("More
   info → Run anyway") walkthroughs, notes that updates themselves install silently.

## What is left to the builder

- Exact workflow job layout (single job vs one gate job + two build jobs) and matrix
  mechanics; runner image pins.
- Whether the update-check module lives in `ui/src` as a store-adjacent pure module or
  as a Rust-side helper behind IPC — both are acceptable under the testing rules; pick
  by what minimizes duplicated version logic (the version comparison result and its
  tests must not exist twice).
- Notification placement/visual details within `docs/UI_DESIGN.html` conventions.
- Semver comparison implementation (hand-rolled three-component compare is fine;
  semver crates only if already convenient to depend on).
