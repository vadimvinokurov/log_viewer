---
name: release-flow
description: The complete release procedure for this repo — version bump, local gates, tag shape, push, and the traps that bit real releases (v0.2.0 CI typecheck failure, v0.3.1 windows version gate). Use before any release-tag work or when the owner asks for a release/push.
---

# Release flow (log_viewer)

Owner-facing rule: a release is published by the script, never by memory.
`bash release_gates.sh` is the only evidence a tag push is legitimate.

## Steps, in order

1. **Bump `src-tauri/tauri.conf.json` `version` to the tag's version** (e.g.
   `0.3.1` for tag `v0.3.1`). CI (`release.yml`, windows job) refuses a tag
   whose name differs from this field — every release commit must carry the
   bump (v0.3.1's windows build fell on exactly this in 53s).
   `src-tauri/Cargo.toml` and `ui/package.json` versions are NOT part of the
   gate; the workflow compares the tag against tauri.conf.json only.
2. **Make the release commit(s)**: any pending housekeeping (e.g. the
   `.beads/issues.jsonl` export) plus a `release: vX.Y.Z` commit carrying the
   version bump.
3. **Run the gates on the exact commit the tag will point to**:
   `bash release_gates.sh` (repo root). It runs, in CI's order:
   - `cargo test --workspace`
   - `npm --prefix ui run build` (wipes stale tsbuildinfo first — tsc -b is
     the only gate that catches TS errors)
   - `npx vitest run` (run from `ui/`)
   Evidence: `.release-gates/last-run.json` carries the commit SHA, `ok` and
   a timestamp. A run on a different commit is void — re-run after any commit.
4. **Annotated tag in the v0.3.0 shape**:
   `git tag -a vX.Y.Z -m "vX.Y.Z\n\n- change bullets\n\nGates on <sha>:
   cargo test --workspace green, npm run build green (wiped tsc caches),
   npx vitest run <N> green."`
5. **Push only on an explicit owner request** (rule 8 is committs-local;
   the push itself is a separate consent): `git push origin main vX.Y.Z`.
6. **Watch the CI run to completion** (`gh run watch`); a CI failure after
   green local gates is a local-vs-CI diff investigation, not a blind tag
   push (rebuilds are incidents, not retries).

## Traps that already bit

| Trap | Remedy |
|---|---|
| tauri.conf.json version ≠ tag | The v0.3.1 windows job gate (step 1). |
| Stale `CARGO_MANIFEST_DIR` baked into test binaries after a repo move/rename | Fixture-path test panics name the OLD path (e.g. `/Users/…/Work/log_viewer2/…`). `cargo clean -p <crate>`, then re-run the gates; do not touch the test source. |
| Gate run on a commit older than the tag | The marker's SHA must equal `git rev-parse HEAD`; otherwise re-run (step 3). |
| Local commit, no push consent, Dolt beads sync unconfigured | Local commits are free (rule 8); `git push` and `bd dolt push` wait for an explicit request — the `bd dolt remote` is NOT configured (bd prints a repair hint on every command). |
| tauri-action release race + silent upload death (v0.3.1 tag run 45651484272) | Both build jobs run in parallel; if one builds a release object while another already made one (esp. a leftover DRAFT with the same tag — drafts are invisible to tauri-action's lookup), the loser recreates the release and its asset upload can die mid-run with NO error in the log (job ends at "Uploading …" / after `npm install -g @tauri-apps/cli`). Diagnose via `gh api /releases` asset lists, not the run log; a partial published release with a missing `latest.json` breaks the updater endpoint. Remedy: re-cut as a new patch tag (v0.3.2) — never re-push the same tag; delete stale draft/partial releases only on explicit owner consent. |
