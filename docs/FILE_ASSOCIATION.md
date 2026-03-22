# File Association

This document explains how to use the "Open with..." functionality to open log files directly from your file manager.

## Overview

Log Viewer supports file association on both macOS and Windows, allowing you to right-click on log files and open them directly in the application. This is useful for quickly viewing log files without manually launching the application first.

**Supported File Types**:
- `.log` - Primary log file extension
- `.txt` - Plain text files (optional)

## macOS Instructions

### Using "Open With" Menu

1. Locate a `.log` or `.txt` file in Finder
2. Right-click (or Control-click) on the file
3. Select **Open With** from the context menu
4. Choose **Log Viewer** from the list of applications

If Log Viewer doesn't appear in the list:
1. Select **Other...** at the bottom of the "Open With" menu
2. Navigate to your Applications folder
3. Select **Log Viewer.app**
4. Check "Always Open With" if you want to make it the default

### Setting Log Viewer as Default (Optional)

To make Log Viewer the default application for `.log` files:

1. Right-click on any `.log` file
2. Select **Get Info** (or press `Cmd + I`)
3. In the "Open with:" section, select **Log Viewer**
4. Click **Change All...** to apply to all `.log` files

### Troubleshooting (macOS)

**App doesn't appear in "Open With" menu**:
- Ensure Log Viewer.app is in your Applications folder
- Restart Finder: `killall Finder` in Terminal
- Rebuild Launch Services database: `/System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister -kill -r -domain local -domain system -domain user`

**File doesn't open**:
- Check Console.app for error messages
- Verify the file exists and is readable
- Try opening the file from within Log Viewer (File → Open)

## Windows Instructions

### Using "Open With" Menu

1. Locate a `.log` file in File Explorer
2. Right-click on the file
3. Select **Open with** → **Choose another app**
4. Check "Always use this app to open .log files" (optional)
5. Click **More apps** if Log Viewer isn't listed
6. Scroll down and click **Look for another app on this PC**
7. Navigate to the Log Viewer installation directory
8. Select **LogViewer.exe**

### Setting Log Viewer as Default (Optional)

To make Log Viewer the default application for `.log` files:

1. Right-click on any `.log` file
2. Select **Properties**
3. Click **Change...** next to "Opens with:"
4. Select **Log Viewer** from the list or browse to LogViewer.exe
5. Click **OK** to save

### Troubleshooting (Windows)

**App doesn't appear in "Open with..." menu**:
- For portable executables, you must manually associate files
- Use the "Look for another app on this PC" option to locate LogViewer.exe
- Once associated, it will appear in the "Open with" menu

**File doesn't open**:
- Check that LogViewer.exe is not blocked by antivirus software
- Verify the file path doesn't contain special characters
- Try running Log Viewer as administrator

**Error: "File not found"**:
- The file may have been moved or deleted
- Check the file path in the error message
- Network paths may require additional permissions

## Command-Line Usage

You can also open files from the command line or terminal.

### Opening a Single File

```bash
# macOS (from Applications folder)
open -a "Log Viewer" /path/to/file.log

# Or run the executable directly
/Applications/Log\ Viewer.app/Contents/MacOS/Log\ Viewer /path/to/file.log

# Windows
LogViewer.exe C:\path\to\file.log

# Development (from source)
uv run python -m src.main /path/to/file.log
```

### Opening Multiple Files

Each file opens in a separate window:

```bash
# macOS
/Applications/Log\ Viewer.app/Contents/MacOS/Log\ Viewer file1.log file2.log file3.log

# Windows
LogViewer.exe file1.log file2.log file3.log

# Development
uv run python -m src.main file1.log file2.log file3.log
```

### Invalid Files

If a file doesn't exist or can't be opened:
- A warning is logged (check console output)
- The file is skipped
- Other valid files are still opened

## Troubleshooting

### File Doesn't Open

**Symptoms**: Double-clicking or "Open with..." doesn't launch the app

**Solutions**:
1. Verify the application is installed correctly
2. Check file permissions (read access required)
3. Look for error messages in Console (macOS) or Event Viewer (Windows)
4. Try opening from within the application first

### App Doesn't Appear in "Open With..."

**Symptoms**: Log Viewer not listed in the "Open with" menu

**Solutions**:

**macOS**:
1. Move Log Viewer.app to /Applications
2. Restart Finder
3. Rebuild Launch Services database (see macOS Troubleshooting above)

**Windows**:
1. Use "Look for another app on this PC" to manually locate LogViewer.exe
2. For installer builds, reinstall the application
3. For portable builds, manual association is required

### Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| "File not found" | File deleted or moved | Verify file exists |
| "Permission denied" | Insufficient permissions | Check file permissions |
| "File locked" | File in use by another process | Close other applications |
| "Invalid encoding" | Binary file or unsupported encoding | Try opening as text file |

### Performance Issues

If opening large files is slow:
- This is expected for multi-gigabyte files
- The application uses lazy loading for performance
- Initial indexing may take a few seconds

## Technical Details

For implementation details, see the specification:
- [File Association Specification](specs/features/file-association.md)

### Supported Platforms

| Platform | Version | Architecture |
|----------|---------|--------------|
| macOS | 10.15+ | x86_64, arm64 |
| Windows | 10+ | x64 |

### File Association Registration

**macOS**: File associations are registered via `CFBundleDocumentTypes` in `Info.plist`

**Windows**: File associations are registered via Windows Registry (installer builds) or manually (portable builds)