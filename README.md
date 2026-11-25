# logviewer

A local log-viewer desktop app for two plain-text log formats (Tauri 2 + Rust
core + React). Reads large files fast, never writes to them. See `docs/`
for the functional specification and internals.

## Install

Grab the installer for your platform from the
[latest release](https://github.com/vadimvinokurov/log_viewer/releases/latest):

- **macOS** — `logviewer_*_universal.dmg` (Apple Silicon and Intel, one build)
- **Windows** — `logviewer_*_x64-setup.exe` (NSIS installer)

The builds are **unsigned**, so the first install needs one manual step:

- **macOS:** when Gatekeeper refuses to open the app, open **System Settings →
  Privacy & Security**, scroll to the Security section and click **Open
  Anyway**. This is needed once per install.
- **Windows:** SmartScreen shows "Windows protected your PC" — click **More
  info → Run anyway**.

## Updates

The app checks for updates automatically at startup (a silent probe to this
repository's GitHub releases — the only network activity it ever makes). When
a new version is found, a banner offers one-click install; the app downloads,
installs and restarts itself. You can also check manually with the
`check-updates` command in the command line. Updates install silently — the
unsigned-install walkthrough above applies only to the initial download.

## Building from source

```bash
npm --prefix ui ci
npm --prefix ui run build
cargo tauri build          # in src-tauri/ context: `cargo tauri build`
```

Tests: `cargo test --workspace` (Rust core + shell), `npm --prefix ui test`
(unit logic) — see `docs/PIPELINE.md` for the gates.
