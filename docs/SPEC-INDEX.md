# Specification Index

Quick navigation to all specification documents.

---

## Global Specifications

| Document | Description | Status |
|----------|-------------|--------|
| [memory-model.md](specs/global/memory-model.md) | Memory management, ownership semantics, resource cleanup | v1.2 |
| [threading.md](specs/global/threading.md) | Thread architecture, signal/slot connections, thread safety | v1.1 |
| [error-handling.md](specs/global/error-handling.md) | Error categories, logging, recovery strategies | v1.0 |
| [color-palette.md](specs/global/color-palette.md) | Comprehensive color system, naming conventions, accessibility | v1.0 |

---

## Feature Specifications

| Document | Description | Status |
|----------|-------------|--------|
| [category-alphabetical-sorting.md](specs/features/category-alphabetical-sorting.md) | Alphabetical sorting of categories at each nesting level | v1.0 |
| [category-checkbox-behavior.md](specs/features/category-checkbox-behavior.md) | Category panel checkbox cascade rules and visibility logic | v1.2 |
| [category-panel-styles.md](specs/features/category-panel-styles.md) | Category panel visual styles, typography, colors, states | v1.0 |
| [category-tree-row-unification.md](specs/features/category-tree-row-unification.md) | Unified tree/table row styles, zero padding, Unicode checkboxes | READY |
| [filter-engine.md](specs/features/filter-engine.md) | Filter compilation, types, combination logic | v1.1 |
| [category-tree.md](specs/features/category-tree.md) | Tree structure, operations | v1.3 |
| [file-management.md](specs/features/file-management.md) | LogDocument, FileController, IndexWorker | v1.2 |
| [file-association.md](specs/features/file-association.md) | "Open with..." file association for macOS and Windows | v1.0 |
| [main-controller.md](specs/features/main-controller.md) | Central coordinator, responsibilities, signal flow | v1.0 |
| [ui-components.md](specs/features/ui-components.md) | MainWindow, LogTableView, CategoryPanel, widgets | v1.6 |
| [ui-design-system.md](specs/features/ui-design-system.md) | Visual style, colors, typography, components, accessibility, animations | v1.13 |
| [typography-system.md](specs/features/typography-system.md) | Unified font system, type scale, platform-specific sizes | v2.2 |
| [table-column-alignment.md](specs/features/table-column-alignment.md) | LogTableView column text alignment, horizontal/vertical positioning | v1.2 |
| [table-cell-text-overflow.md](specs/features/table-cell-text-overflow.md) | Table cell text overflow, clipping, no-wrap behavior | v1.1 |
| [table-unified-styles.md](specs/features/table-unified-styles.md) | Unified table styles, header/row consistency, zero padding | v1.7 |
| [table-column-auto-size.md](specs/features/table-column-auto-size.md) | Automatic column sizing based on content for Time, Type, Category columns | DRAFT |
| [filter-controller.md](specs/features/filter-controller.md) | Filter state management, coordination, signals | v1.0 |
| [settings-manager.md](specs/features/settings-manager.md) | Persistent settings, QSettings wrapper | v1.0 |
| [highlight-service.md](specs/features/highlight-service.md) | Highlight patterns, engine coordination | v1.0 |
| [highlight-panel.md](specs/features/highlight-panel.md) | Highlight panel UI, pattern management, enable/disable | v1.0 |
| [log-level-text-color.md](specs/features/log-level-text-color.md) | Log level text color highlighting (foreground instead of background) | v1.0 |
| [saved-filters.md](specs/features/saved-filters.md) | Saved filter presets, enable/disable, OR combination | READY |
| [selection-preservation.md](specs/features/selection-preservation.md) | Row selection preservation during filter/category changes | v1.4 |
| [native-checkbox-unification.md](specs/features/native-checkbox-unification.md) | Native Qt checkboxes across Categories, Filters, Highlights tabs | v1.0 |
| [panel-content-unified-styles.md](specs/features/panel-content-unified-styles.md) | Unified styles for Categories, Filters, Highlights panel content | PROPOSED |
| [panel-toggle-button.md](specs/features/panel-toggle-button.md) | Status bar button to hide/show all auxiliary panels | v1.1 |
| [category-tree-click-target-spacing.md](specs/features/category-tree-click-target-spacing.md) | Branch-to-checkbox spacing following Material Design standards | PROPOSED |
| [category-tree-expand-collapse.md](specs/features/category-tree-expand-collapse.md) | Expand/collapse toggle button for Category Tree | v1.0 |
| [log-entry-optimization.md](specs/features/log-entry-optimization.md) | LogEntry memory optimization, string interning, field removal | DRAFT |
| [timestamp-unix-epoch.md](specs/features/timestamp-unix-epoch.md) | Unix Epoch timestamp storage, H:M:S.MS display, date tooltip | DRAFT |
| [application-packaging.md](specs/features/application-packaging.md) | Cross-platform packaging for macOS (.dmg) and Windows (.exe) | v1.1 |
| [windows-startup-optimization.md](specs/features/windows-startup-optimization.md) | Windows startup optimization: switch from --onefile to --onedir + installer | READY |
| [multi-window-instance.md](specs/features/multi-window-instance.md) | True multi-instance behavior (separate processes) for macOS and Windows | DRAFT |
| [file-open-dialog.md](specs/features/file-open-dialog.md) | Dialog for opening log files when a file is already open | DRAFT |

---

## API Specifications

| Document | Description | Status |
|----------|-------------|--------|
| [engine-api.yaml](specs/api/engine-api.yaml) | Public API for all components (Models, Core, Controllers, Views, Services) | v1.0 |

---

## Global Rules & Schemas

| Document | Description | Status |
|----------|-------------|--------|
| *(none yet)* | | |

---

## Audit Reports

| Document | Description | Status |
|----------|-------------|--------|
| *(none yet)* | | |

---

## Quick Links

### By Component

- **Models**
  - LogEntry: [engine-api.yaml](specs/api/engine-api.yaml) §2.1, [log-entry-optimization.md](specs/features/log-entry-optimization.md), [timestamp-unix-epoch.md](specs/features/timestamp-unix-epoch.md)
  - LogLevel: [engine-api.yaml](specs/api/engine-api.yaml) §2.2
  - LogDocument: [engine-api.yaml](specs/api/engine-api.yaml) §2.3
  - CategoryDisplayNode: [engine-api.yaml](specs/api/engine-api.yaml) §2.4

- **Core**
  - FilterEngine: [filter-engine.md](specs/features/filter-engine.md), [engine-api.yaml](specs/api/engine-api.yaml) §3.1
  - CategoryTree: [category-tree.md](specs/features/category-tree.md), [engine-api.yaml](specs/api/engine-api.yaml) §3.2
  - HighlightEngine: [highlight-service.md](specs/features/highlight-service.md), [engine-api.yaml](specs/api/engine-api.yaml) §3.3
  - SimpleQueryParser: [filter-engine.md](specs/features/filter-engine.md) §5, [engine-api.yaml](specs/api/engine-api.yaml) §3.4

- **Controllers**
  - MainController: [main-controller.md](specs/features/main-controller.md), [engine-api.yaml](specs/api/engine-api.yaml) §4.1
  - FilterController: [filter-controller.md](specs/features/filter-controller.md), [engine-api.yaml](specs/api/engine-api.yaml) §4.2
  - FileController: [file-management.md](specs/features/file-management.md), [engine-api.yaml](specs/api/engine-api.yaml) §4.3

- **Views**
  - MainWindow: [ui-components.md](specs/features/ui-components.md) §3, [engine-api.yaml](specs/api/engine-api.yaml) §5.1
  - LogTableView: [ui-components.md](specs/features/ui-components.md) §4, [engine-api.yaml](specs/api/engine-api.yaml) §5.2
  - CategoryPanel: [ui-components.md](specs/features/ui-components.md) §5, [category-panel-styles.md](specs/features/category-panel-styles.md), [engine-api.yaml](specs/api/engine-api.yaml) §5.3

- **Services**
  - StatisticsService: [engine-api.yaml](specs/api/engine-api.yaml) §6.1
  - HighlightService: [highlight-service.md](specs/features/highlight-service.md), [engine-api.yaml](specs/api/engine-api.yaml) §6.2

- **Utilities**
  - SettingsManager: [settings-manager.md](specs/features/settings-manager.md), [engine-api.yaml](specs/api/engine-api.yaml) §7.1

### By Topic

- **Memory Management**: [memory-model.md](specs/global/memory-model.md)
- **Threading**: [threading.md](specs/global/threading.md)
- **Error Handling**: [error-handling.md](specs/global/error-handling.md)
- **Color System**: [color-palette.md](specs/global/color-palette.md)
- **Filter System**: [filter-engine.md](specs/features/filter-engine.md), [filter-controller.md](specs/features/filter-controller.md)
- **Category System**: [category-tree.md](specs/features/category-tree.md), [category-checkbox-behavior.md](specs/features/category-checkbox-behavior.md), [category-tree-row-unification.md](specs/features/category-tree-row-unification.md), [category-alphabetical-sorting.md](specs/features/category-alphabetical-sorting.md), [category-tree-click-target-spacing.md](specs/features/category-tree-click-target-spacing.md), [category-tree-expand-collapse.md](specs/features/category-tree-expand-collapse.md)
- **File Handling**: [file-management.md](specs/features/file-management.md), [file-association.md](specs/features/file-association.md), [multi-window-instance.md](specs/features/multi-window-instance.md), [file-open-dialog.md](specs/features/file-open-dialog.md)
- **Timestamp Handling**: [timestamp-unix-epoch.md](specs/features/timestamp-unix-epoch.md)
- **UI Components**: [ui-components.md](specs/features/ui-components.md)
- **UI Design System**: [ui-design-system.md](specs/features/ui-design-system.md)
- **Typography**: [typography-system.md](specs/features/typography-system.md)
- **Table Rendering**: [table-column-alignment.md](specs/features/table-column-alignment.md), [table-cell-text-overflow.md](specs/features/table-cell-text-overflow.md), [table-unified-styles.md](specs/features/table-unified-styles.md), [table-column-auto-size.md](specs/features/table-column-auto-size.md), [category-tree-row-unification.md](specs/features/category-tree-row-unification.md)
- **Settings**: [settings-manager.md](specs/features/settings-manager.md)
- **Highlighting**: [highlight-service.md](specs/features/highlight-service.md), [highlight-panel.md](specs/features/highlight-panel.md), [log-level-text-color.md](specs/features/log-level-text-color.md)
- **Selection**: [selection-preservation.md](specs/features/selection-preservation.md)
- **Panel Styling**: [panel-content-unified-styles.md](specs/features/panel-content-unified-styles.md), [native-checkbox-unification.md](specs/features/native-checkbox-unification.md)
- **Packaging**: [application-packaging.md](specs/features/application-packaging.md), [windows-startup-optimization.md](specs/features/windows-startup-optimization.md)

---

## Document Status Legend

| Status | Description |
|--------|-------------|
| DRAFT | Work in progress, subject to change |
| READY | Approved for implementation, ready for spec-orchestrator |
| v1.0 | Approved, implemented |
| v1.1+ | Updated version with changes |

---

## Master Specification

See [SPEC.md](SPEC.md) for the master specification file with project overview and global rules.