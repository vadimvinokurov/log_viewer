# Multi-Instance Behavior

## Overview

Log Viewer supports multiple independent process instances, allowing you to:

- Open multiple log files simultaneously in separate windows
- Compare logs from different files side-by-side
- Work with multiple log files without interference

## How It Works

When you:

- **Click the app icon**: Launches a NEW process instance
- **Use "Open with..."**: Launches a NEW process instance for each file
- **Close one instance**: Other instances remain running

## Memory Considerations

Each instance uses approximately 80-120 MB of memory:

- 1 instance: ~80-120 MB
- 5 instances: ~400-600 MB
- 10 instances: ~800-1200 MB

## Platform Behavior

### macOS

- Multiple instances allowed via `LSMultipleInstances: True` in Info.plist
- Each "Open with..." launches a new process

### Windows

- Multiple instances allowed by default
- Each "Open with..." launches a new process

## Troubleshooting

**Q: Why can't I see all my log files in one window?**

A: Log Viewer uses separate process instances for each file. This provides better isolation and prevents one file from affecting others.

**Q: How do I close all instances at once?**

A: On macOS, use ⌘+Q to quit the current instance. On Windows, use Alt+F4. Each instance must be closed individually.

**Q: Can I share filters between instances?**

A: No, each instance is completely independent. Filters, highlights, and settings are not shared between instances.

## Benefits of Multi-Instance

1. **Isolation**: Each log file runs in its own process space
2. **Stability**: A crash in one instance doesn't affect others
3. **Performance**: No resource contention between files
4. **Flexibility**: Work with different log files simultaneously

## Implementation Details

For technical details about the multi-instance implementation, see:

- [Multi-Window Instance Spec](specs/features/multi-window-instance.md)
- [File Association Spec](specs/features/file-association.md)