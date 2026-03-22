# Windows Startup Optimization Specification

**Version**: 1.0  
**Status**: READY  
**Created**: 2026-03-22  
**Feature**: Reduce Windows application startup time from ~10 seconds to < 2 seconds

---

## §1 Problem Analysis

### §1.1 Current Behavior

| Platform | Startup Time | Mode | Root Cause |
|----------|--------------|------|------------|
| macOS | < 1 second | `--onedir` | Pre-extracted app bundle, no extraction overhead |
| Windows | ~10 seconds | `--onefile` | Extracts ~50-100MB to temp directory on every launch |

### §1.2 Root Cause: `--onefile` Extraction Overhead

**Windows Build Configuration** (per [`build/logviewer.spec:162-184`](build/logviewer.spec:162)):
- Uses `--onefile` mode (single executable)
- Embeds all Python runtime, PySide6, and dependencies
- On launch: extracts entire payload to `%TEMP%\_MEIxxxxxx\` directory
- Windows Defender scans all extracted files
- No persistent cache between launches

**Extraction Breakdown** (estimated):
| Phase | Time | Description |
|-------|------|-------------|
| Archive extraction | 3-5 seconds | Extract ~50-100MB to temp directory |
| Windows Defender scan | 3-5 seconds | Real-time scanning of extracted DLLs |
| Python initialization | 0.5 seconds | Start Python interpreter |
| PySide6 loading | 1-2 seconds | Load Qt libraries |
| **Total** | **8-13 seconds** | |

### §1.3 Why macOS is Fast

**macOS Build Configuration** (per [`build/logviewer.spec:87-160`](build/logviewer.spec:87)):
- Uses `--onedir` mode (app bundle)
- Binaries pre-extracted in `Log Viewer.app/Contents/`
- No extraction on launch
- No additional antivirus scanning (Gatekeeper checks only on first launch)

---

## §2 Solution Options

### §2.1 Option A: Switch to `--onedir` for Windows (RECOMMENDED)

**Description**: Use directory bundle like macOS, wrapped in installer.

**Pros**:
- ✅ Instant startup (< 1 second, same as macOS)
- ✅ No extraction overhead
- ✅ Matches macOS architecture
- ✅ Better user experience

**Cons**:
- ❌ Distribution complexity (~100 files in folder)
- ❌ Requires installer (Inno Setup / NSIS)
- ❌ Larger download size (no compression)

**Implementation**:
1. Change Windows build to `--onedir` mode
2. Create installer with Inno Setup
3. Installer installs to `Program Files\Log Viewer\`
4. Creates Start Menu shortcut

**Startup Time**: < 1 second (instant)

### §2.2 Option B: Optimize `--onefile` (Current Approach)

**Description**: Continue with single executable, apply additional optimizations.

**Current Optimizations** (per [`docs/specs/features/application-packaging.md:174-192`](docs/specs/features/application-packaging.md:174)):
- ✅ `upx=False` (saves 2-5 seconds)
- ✅ Excluded unused modules
- ✅ Minimal hidden imports

**Additional Optimizations**:
| Optimization | Time Saved | Feasibility |
|--------------|------------|-------------|
| Windows Defender exclusion | 3-5 seconds | ❌ Requires user action |
| Smaller payload (remove PySide6 modules) | 1-2 seconds | ⚠️ Limited impact |
| Nuitka compilation | 5-8 seconds | ✅ Compiles to native code |
| Pre-extraction cache | 2-3 seconds | ⚠️ Complex, unreliable |

**Startup Time**: 5-8 seconds (still above target)

### §2.3 Option C: Nuitka Compiler (Alternative)

**Description**: Use Nuitka instead of PyInstaller (compiles Python to C).

**Pros**:
- ✅ Faster startup (no Python interpreter initialization)
- ✅ Better performance (compiled code)
- ✅ Smaller executable
- ✅ Can use `--onefile` with acceptable performance

**Cons**:
- ❌ Longer build times (5-10 minutes vs 1-2 minutes)
- ❌ More complex configuration
- ❌ Less community support than PyInstaller
- ❌ May have compatibility issues with PySide6

**Startup Time**: 2-4 seconds (estimated)

---

## §3 Recommendation: Option A (`--onedir` + Installer)

### §3.1 Rationale

1. **Performance Parity**: Matches macOS instant startup
2. **User Experience**: Installer provides professional experience
3. **Maintainability**: Same architecture across platforms
4. **Future-Proof**: Easier to add auto-update mechanism

### §3.2 Implementation Plan

#### §3.2.1 Update PyInstaller Spec

**File**: [`build/logviewer.spec`](build/logviewer.spec)

**Changes** (Windows section):
```python
elif system == 'Windows':
    # See spec §5.3 for Windows configuration
    # Per docs/specs/features/windows-startup-optimization.md §3.2.1: Use --onedir for instant startup
    
    exe = EXE(
        pyz,
        a.scripts,
        [],  # Empty: exclude_binaries=True for onedir
        exclude_binaries=True,  # CHANGED: Use onedir mode
        name='LogViewer',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,  # CHANGED: Enable UPX for onedir (decompress once during install)
        console=False,
        target_arch='x86_64',
    )
    
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='LogViewer',
    )
```

#### §3.2.2 Create Inno Setup Installer Script

**File**: `build/installer/logviewer-setup.iss`

```iss
; Inno Setup Script for Log Viewer
; Ref: docs/specs/features/windows-startup-optimization.md §3.2.2

#define AppName "Log Viewer"
#define AppVersion "0.1.0"
#define AppPublisher "Log Viewer Team"
#define AppURL "https://github.com/..."
#define AppExeName "LogViewer.exe"

[Setup]
AppId={{8A7D9B3C-1234-5678-9ABC-DEF012345678}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
LicenseFile=LICENSE
OutputDir=dist
OutputBaseFilename=LogViewer-{#AppVersion}-windows-setup
SetupIconFile=build\icons\app.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Copy all files from PyInstaller onedir build
Source: "dist\LogViewer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:ProgramOnTheWeb,{#AppName}}"; Filename: "{#AppURL}"
Name: "{group}\{cm:UninstallShortcut,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Registry]
; File association for .log files
Root: HKCR; Subkey: ".log"; ValueType: string; ValueName: ""; ValueData: "LogFile"; Flags: uninsdeletevalue
Root: HKCR; Subkey: "LogFile"; ValueType: string; ValueName: ""; ValueData: "Log File"; Flags: uninsdeletekey
Root: HKCR; Subkey: "LogFile\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExeName},0"
Root: HKCR; Subkey: "LogFile\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""
```

#### §3.2.3 Update Build Script

**File**: `build/scripts/build-windows.py`

**Changes**:
```python
#!/usr/bin/env python3
"""Windows build script for Log Viewer.

Ref: docs/specs/features/windows-startup-optimization.md §3.2.3
"""

import subprocess
import shutil
import hashlib
from pathlib import Path


def build_windows() -> None:
    """Build Log Viewer for Windows with installer."""
    print("Building Log Viewer for Windows...")
    
    # Configuration
    app_name = "LogViewer"
    app_version = "0.1.0"
    
    # Clean previous build
    print("Cleaning previous build...")
    dist_dir = Path("dist")
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    
    # Run PyInstaller (onedir mode)
    print("Running PyInstaller...")
    result = subprocess.run(
        ["uv", "run", "pyinstaller", "--clean", "--noconfirm", "build/logviewer.spec"],
        check=False
    )
    
    if result.returncode != 0:
        print(f"ERROR: PyInstaller failed with code {result.returncode}")
        exit(1)
    
    # Verify onedir build
    app_dir = dist_dir / app_name
    if not app_dir.exists():
        print(f"ERROR: Build failed - {app_dir} not found")
        exit(1)
    
    # Build installer with Inno Setup
    print("Building installer...")
    installer_script = Path("build/installer/logviewer-setup.iss")
    if installer_script.exists():
        result = subprocess.run(
            ["iscc", str(installer_script)],
            check=False
        )
        
        if result.returncode != 0:
            print(f"WARNING: Installer build failed (Inno Setup not installed?)")
            print(f"Fallback: Distributing as ZIP archive")
            # Create ZIP archive as fallback
            shutil.make_archive(
                str(dist_dir / f"{app_name}-{app_version}-windows"),
                "zip",
                app_dir
            )
    else:
        print("WARNING: Inno Setup script not found, creating ZIP archive")
        shutil.make_archive(
            str(dist_dir / f"{app_name}-{app_version}-windows"),
            "zip",
            app_dir
        )
    
    # Generate checksum
    print("Generating checksum...")
    installer_exe = dist_dir / f"{app_name}-{app_version}-windows-setup.exe"
    if installer_exe.exists():
        checksum = calculate_sha256(installer_exe)
        checksum_file = dist_dir / f"{app_name}-{app_version}-windows-setup.exe.sha256"
    else:
        archive = dist_dir / f"{app_name}-{app_version}-windows.zip"
        checksum = calculate_sha256(archive)
        checksum_file = dist_dir / f"{app_name}-{app_version}-windows.zip.sha256"
    
    with open(checksum_file, "w") as f:
        f.write(f"{checksum}  {checksum_file.stem}\n")
    
    # Summary
    print()
    print("=" * 50)
    print("Build complete!")
    print("=" * 50)
    if installer_exe.exists():
        print(f"Installer: dist/{installer_exe.name}")
        print(f"Checksum: dist/{checksum_file.name}")
        print()
        print(f"To test: Run installer from dist/")
    else:
        print(f"Archive: dist/{app_name}-{app_version}-windows.zip")
        print(f"Checksum: dist/{checksum_file.name}")
        print()
        print(f"To test: Extract and run {app_name}/{app_name}.exe")
    print("=" * 50)


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


if __name__ == "__main__":
    build_windows()
```

---

## §4 Performance Targets

### §4.1 Startup Time Requirements

| Platform | Current | Target | Mode |
|----------|---------|--------|------|
| macOS | < 1 second | < 1 second | `--onedir` (no change) |
| Windows | ~10 seconds | < 2 seconds | `--onedir` + installer |

### §4.2 Measurement Method

**Windows PowerShell**:
```powershell
# Cold start (after reboot)
Measure-Command { Start-Process -Wait -NoNewWindow "C:\Program Files\Log Viewer\LogViewer.exe" }

# Warm start (second launch)
Measure-Command { Start-Process -Wait -NoNewWindow "C:\Program Files\Log Viewer\LogViewer.exe" }
```

**Target**: < 2 seconds cold start, < 1 second warm start

---

## §5 Distribution Artifacts

### §5.1 Windows Installer

**Primary Artifact**: `LogViewer-{version}-windows-setup.exe`

**Contents**:
- Application files (~100 MB)
- Inno Setup installer
- Uninstaller
- Start Menu integration
- Optional desktop shortcut
- File association (.log, .txt)

**Size Estimate**: 80-120 MB (compressed with LZMA2)

### §5.2 Fallback: ZIP Archive

**Alternative Artifact**: `LogViewer-{version}-windows.zip`

**Use Case**: Users without installer privileges, portable usage

**Contents**:
- `LogViewer/` directory with all files
- User manually extracts and runs `LogViewer.exe`

---

## §6 Migration Path

### §6.1 For Existing Users

1. **Uninstall old version**: Remove `LogViewer.exe` (standalone)
2. **Install new version**: Run `LogViewer-setup.exe`
3. **Settings preserved**: Stored in `%APPDATA%\LogViewer\`

### §6.2 For Developers

1. **Update build scripts**: Use new `build-windows.py`
2. **Install Inno Setup**: Download from https://jrsoftware.org/isdl.php
3. **Test installer**: Verify on clean Windows VM

---

## §7 Rollback Plan

If installer approach fails:

1. **Revert to `--onefile`**: Restore original spec
2. **Document slow startup**: Add to known issues
3. **Consider Nuitka**: Evaluate for v0.2.0

---

## §8 References

- PyInstaller Onefile vs Onedir: https://pyinstaller.org/en/stable/operating-modes.html
- Inno Setup Documentation: https://jrsoftware.org/ishelp/
- Nuitka Python Compiler: https://nuitka.net/
- Windows Installer Best Practices: https://docs.microsoft.com/en-us/windows/win32/msi/

---

## §9 Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Spec Author | [Author] | 2026-03-22 | [DRAFT] |
| Spec Reviewer | [Reviewer] | [Date] | [PENDING] |

---

**End of Specification**