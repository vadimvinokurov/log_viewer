# Specification Index

Quick navigation to all specification documents.

---

## Global Specifications

| Document | Description | Status |
|----------|-------------|--------|
| [memory-model.md](specs/global/memory-model.md) | Memory management, ownership semantics, resource cleanup | v1.0 |
| [threading.md](specs/global/threading.md) | Thread architecture, signal/slot connections, thread safety | v1.0 |
| [error-handling.md](specs/global/error-handling.md) | Error categories, logging, recovery strategies | v1.0 |

---

## Feature Specifications

| Document | Description | Status |
|----------|-------------|--------|
| [category-checkbox-behavior.md](specs/features/category-checkbox-behavior.md) | Category panel checkbox cascade rules and visibility logic | v1.0 |
| [filter-engine.md](specs/features/filter-engine.md) | Filter compilation, types, combination logic | v1.0 |
| [category-tree.md](specs/features/category-tree.md) | Tree structure, operations, custom categories | v1.0 |
| [file-management.md](specs/features/file-management.md) | LogDocument, FileController, IndexWorker | v1.0 |
| [main-controller.md](specs/features/main-controller.md) | Central coordinator, responsibilities, signal flow | v1.0 |
| [ui-components.md](specs/features/ui-components.md) | MainWindow, LogTableView, CategoryPanel, widgets | v1.0 |
| [filter-controller.md](specs/features/filter-controller.md) | Filter state management, coordination, signals | v1.0 |
| [settings-manager.md](specs/features/settings-manager.md) | Persistent settings, QSettings wrapper | v1.0 |
| [highlight-service.md](specs/features/highlight-service.md) | Highlight patterns, engine coordination | v1.0 |

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
  - LogEntry: [engine-api.yaml](specs/api/engine-api.yaml) §2.1
  - LogLevel: [engine-api.yaml](specs/api/engine-api.yaml) §2.2
  - LogDocument: [engine-api.yaml](specs/api/engine-api.yaml) §2.3
  - SystemNode: [engine-api.yaml](specs/api/engine-api.yaml) §2.4

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
  - CategoryPanel: [ui-components.md](specs/features/ui-components.md) §5, [engine-api.yaml](specs/api/engine-api.yaml) §5.3

- **Services**
  - StatisticsService: [engine-api.yaml](specs/api/engine-api.yaml) §6.1
  - HighlightService: [highlight-service.md](specs/features/highlight-service.md), [engine-api.yaml](specs/api/engine-api.yaml) §6.2

- **Utilities**
  - SettingsManager: [settings-manager.md](specs/features/settings-manager.md), [engine-api.yaml](specs/api/engine-api.yaml) §7.1

### By Topic

- **Memory Management**: [memory-model.md](specs/global/memory-model.md)
- **Threading**: [threading.md](specs/global/threading.md)
- **Error Handling**: [error-handling.md](specs/global/error-handling.md)
- **Filter System**: [filter-engine.md](specs/features/filter-engine.md), [filter-controller.md](specs/features/filter-controller.md)
- **Category System**: [category-tree.md](specs/features/category-tree.md), [category-checkbox-behavior.md](specs/features/category-checkbox-behavior.md)
- **File Handling**: [file-management.md](specs/features/file-management.md)
- **UI Components**: [ui-components.md](specs/features/ui-components.md)
- **Settings**: [settings-manager.md](specs/features/settings-manager.md)
- **Highlighting**: [highlight-service.md](specs/features/highlight-service.md)

---

## Document Status Legend

| Status | Description |
|--------|-------------|
| DRAFT | Work in progress, subject to change |
| v1.0 | Approved, implemented |
| v1.1+ | Updated version with changes |

---

## Master Specification

See [SPEC.md](SPEC.md) for the master specification file with project overview and global rules.