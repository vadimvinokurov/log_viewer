# Windows Startup Optimization - Implementation Plan

**Spec**: docs/specs/features/windows-startup-optimization.md v1.0  
**Status**: READY FOR IMPLEMENTATION  
**Created**: 2026-03-22  
**Orchestrator**: spec-orchestrator

---

## Overview

**Goal**: Reduce Windows startup time from ~10 seconds to < 2 seconds by switching from `--onefile` to `--onedir` mode with Inno Setup installer.

**Approach**: Match macOS architecture (pre-extracted binaries) for instant startup.

**Performance Target**: < 2 seconds cold start, < 1 second warm start

---

## Task Breakdown

### Task T-001: Update PyInstaller Spec for Windows

**Status**: PENDING  
**Spec Reference**: §3.2.1 in docs/specs/features/windows-startup-optimization.md  
**Master Constraints**: docs/SPEC.md §1 (project structure), docs/specs/features/application-packaging.md §5.3  
**Project Context**: Build System  
**Language**: Python (PyInstaller spec)

**Scope**:
- Modify `build/logviewer.spec` (lines 162-184)
- Change Windows build from `--onefile` to `--onedir` mode

**Input/Output**:
- Input: Current `--onefile` configuration
- Output: `--onedir` configuration with `COLLECT` block

**Constraints**:
- Thread context: Build time (no threading)
- Memory: N/A
- Performance: Must produce `dist/LogViewer/` directory

**Implementation Details**:
1. Change `EXE()` parameters:
   - Set `exclude_binaries=True` (enables onedir mode)
   - Change `a.binaries` and `a.datas` from EXE to COLLECT
   - Enable `upx=True` (safe for onedir, decompress once during install)
   
2. Add `COLLECT()` block:
   - Collect all binaries and data into `LogViewer` directory
   - Enable UPX compression (decompresses during install, not at runtime)

**Code Changes**:
```python
# build/logviewer.spec (Windows section, lines 162-184)
elif system == 'Windows':
    # Per docs/specs/features/windows-startup-optimization.md §3.2.1
    exe = EXE(
        pyz,
        a.scripts,
        [],  # Empty: exclude_binaries=True for onedir
        exclude_binaries=True,  # CHANGED: Use onedir mode
        name='LogViewer',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,  # CHANGED: Enable UPX for onedir
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

**Tests Required**:
- Build test: Run `python build/scripts/build-windows.py`
- Verify: `dist/LogViewer/` directory exists with all files
- Verify: `dist/LogViewer/LogViewer.exe` runs successfully
- Performance test: Measure startup time (target < 2 seconds)

**Dependencies**: None (first task)

**Acceptance Criteria**:
- ✅ PyInstaller spec updated with onedir configuration
- ✅ Build produces `dist/LogViewer/` directory
- ✅ `dist/LogViewer/LogViewer.exe` launches successfully
- ✅ Startup time < 2 seconds (cold start)

---

### Task T-002: Create Inno Setup Installer Script

**Status**: PENDING  
**Spec Reference**: §3.2.2 in docs/specs/features/windows-startup-optimization.md  
**Master Constraints**: docs/SPEC.md §1  
**Project Context**: Build System  
**Language**: Inno Setup Script (ISS)

**Scope**:
- Create `build/installer/` directory
- Create `build/installer/logviewer-setup.iss` file

**Input/Output**:
- Input: `dist/LogViewer/` directory from T-001
- Output: `dist/LogViewer-0.1.0-windows-setup.exe` installer

**Constraints**:
- Thread context: Build time (no threading)
- Memory: N/A
- Performance: Installer size < 120 MB compressed

**Implementation Details**:
1. Create Inno Setup script with:
   - App metadata (name, version, publisher)
   - Installation directory: `Program Files\Log Viewer`
   - File copy from `dist\LogViewer\*` to `{app}`
   - Start Menu shortcut
   - Optional desktop shortcut
   - File association for `.log` files
   - Uninstaller

2. Compression settings:
   - LZMA2/ultra64 for maximum compression
   - Solid compression for smaller size

**File Structure**:
```
build/
└── installer/
    └── logviewer-setup.iss  # NEW FILE
```

**Tests Required**:
- Build test: Run `iscc build/installer/logviewer-setup.iss`
- Verify: `dist/LogViewer-0.1.0-windows-setup.exe` exists
- Install test: Run installer on clean Windows VM
- Uninstall test: Verify clean uninstall

**Dependencies**: T-001 (requires onedir build output)

**Acceptance Criteria**:
- ✅ Inno Setup script created at `build/installer/logviewer-setup.iss`
- ✅ Installer builds successfully (requires Inno Setup installed)
- ✅ Installer installs to `Program Files\Log Viewer`
- ✅ Start Menu shortcut created
- ✅ File association for `.log` files works
- ✅ Uninstaller removes all files

---

### Task T-003: Update Windows Build Script

**Status**: PENDING  
**Spec Reference**: §3.2.3 in docs/specs/features/windows-startup-optimization.md  
**Master Constraints**: docs/SPEC.md §1  
**Project Context**: Build System  
**Language**: Python 3.12

**Scope**:
- Modify `build/scripts/build-windows.py`
- Add installer build step
- Add fallback to ZIP archive if Inno Setup not available

**Input/Output**:
- Input: `dist/LogViewer/` directory (from PyInstaller)
- Output: `dist/LogViewer-0.1.0-windows-setup.exe` OR `dist/LogViewer-0.1.0-windows.zip`

**Constraints**:
- Thread context: Build time (no threading)
- Memory: N/A
- Performance: Build time < 5 minutes

**Implementation Details**:
1. Run PyInstaller with updated spec (T-001)
2. Check if Inno Setup (`iscc`) is available
3. If available: Build installer
4. If not available: Create ZIP archive as fallback
5. Generate SHA256 checksum

**Code Changes**:
```python
# build/scripts/build-windows.py
# Add after PyInstaller build:

# Build installer with Inno Setup
installer_script = Path("build/installer/logviewer-setup.iss")
if installer_script.exists():
    result = subprocess.run(["iscc", str(installer_script)], check=False)
    if result.returncode != 0:
        print("WARNING: Installer build failed, creating ZIP archive")
        shutil.make_archive(f"dist/LogViewer-{version}-windows", "zip", "dist/LogViewer")
else:
    print("WARNING: Inno Setup not found, creating ZIP archive")
    shutil.make_archive(f"dist/LogViewer-{version}-windows", "zip", "dist/LogViewer")
```

**Tests Required**:
- Build test: Run `python build/scripts/build-windows.py`
- Verify: Either installer or ZIP created
- Verify: Checksum file generated
- Test both scenarios: with and without Inno Setup

**Dependencies**: T-001, T-002

**Acceptance Criteria**:
- ✅ Build script updated
- ✅ Produces installer when Inno Setup available
- ✅ Falls back to ZIP archive when Inno Setup not available
- ✅ SHA256 checksum generated
- ✅ Build completes in < 5 minutes

---

### Task T-004: Create Windows Icon

**Status**: PENDING  
**Spec Reference**: §7 in docs/specs/features/application-packaging.md  
**Master Constraints**: docs/SPEC.md §1  
**Project Context**: Build System  
**Language**: N/A (asset file)

**Scope**:
- Create `build/icons/app.ico` (Windows icon format)

**Input/Output**:
- Input: `build/icons/app.PNG` (source image, 1024x1024)
- Output: `build/icons/app.ico` (Windows icon, 256x256)

**Constraints**:
- Icon sizes: 16x16, 32x32, 48x48, 64x64, 128x128, 256x256
- Format: ICO with PNG compression
- Size: < 500 KB

**Implementation Details**:
1. Use ImageMagick or online tool to convert PNG to ICO
2. Include multiple sizes in single ICO file
3. Verify icon displays correctly in Windows Explorer

**Command** (if ImageMagick installed):
```bash
convert build/icons/app.PNG -define icon:auto-resize=256,128,64,48,32,16 build/icons/app.ico
```

**Tests Required**:
- Visual test: Icon displays in Windows Explorer
- Visual test: Icon displays in taskbar when app running
- Visual test: Icon displays in Start Menu shortcut

**Dependencies**: None (can run in parallel with T-001)

**Acceptance Criteria**:
- ✅ `build/icons/app.ico` created
- ✅ Icon contains all required sizes
- ✅ Icon displays correctly in Windows

---

### Task T-005: Update Documentation

**Status**: PENDING  
**Spec Reference**: §14 in docs/specs/features/application-packaging.md  
**Master Constraints**: docs/SPEC.md §1  
**Project Context**: Documentation  
**Language**: Markdown

**Scope**:
- Update `docs/BUILD.md` with new Windows build instructions
- Update `README.md` with Windows installation instructions

**Input/Output**:
- Input: Current documentation
- Output: Updated documentation with installer instructions

**Constraints**:
- Clear instructions for end users
- Include both installer and ZIP archive options

**Implementation Details**:
1. Update `docs/BUILD.md`:
   - Add Inno Setup requirement
   - Update build commands
   - Add troubleshooting for missing Inno Setup

2. Update `README.md`:
   - Add Windows installation section
   - Explain installer vs ZIP archive
   - Add startup time expectations

**Tests Required**:
- Review: Documentation is clear and accurate
- Review: All links work
- Review: Instructions match actual build process

**Dependencies**: T-001, T-002, T-003

**Acceptance Criteria**:
- ✅ `docs/BUILD.md` updated with Inno Setup instructions
- ✅ `README.md` updated with Windows installation section
- ✅ Documentation matches actual build process

---

### Task T-006: Performance Testing

**Status**: PENDING  
**Spec Reference**: §4.2 in docs/specs/features/windows-startup-optimization.md  
**Master Constraints**: docs/SPEC.md §1  
**Project Context**: Testing  
**Language**: PowerShell

**Scope**:
- Create performance test script
- Measure startup time on clean Windows VM
- Compare before/after performance

**Input/Output**:
- Input: Built installer or ZIP archive
- Output: Performance report

**Constraints**:
- Test on clean Windows 10/11 VM
- Test cold start (after reboot)
- Test warm start (second launch)

**Implementation Details**:
1. Create PowerShell script to measure startup time:
```powershell
# test-startup-time.ps1
Measure-Command { Start-Process -Wait -NoNewWindow "C:\Program Files\Log Viewer\LogViewer.exe" }
```

2. Run tests:
   - Cold start: Reboot VM, run test
   - Warm start: Close app, run test again
   - Repeat 5 times, calculate average

3. Compare with old `--onefile` build

**Tests Required**:
- Cold start test: < 2 seconds
- Warm start test: < 1 second
- Comparison: At least 5x improvement over `--onefile`

**Dependencies**: T-001, T-002, T-003

**Acceptance Criteria**:
- ✅ Performance test script created
- ✅ Cold start < 2 seconds
- ✅ Warm start < 1 second
- ✅ Performance report documented

---

## Task Dependency Graph

```
T-001 (PyInstaller Spec) ──┬──> T-002 (Inno Setup Script) ──┬──> T-003 (Build Script)
                            │                                 │
                            └─────────────────────────────────┴──> T-005 (Documentation)
                                                                      │
T-004 (Windows Icon) ───────────────────────────────────────────────┘
                                                                      
T-001 + T-002 + T-003 ──> T-006 (Performance Testing)
```

**Parallel Tasks**:
- T-001 and T-004 can run in parallel
- T-005 can start after T-001, T-002, T-003 complete
- T-006 must wait for all build tasks

---

## Execution Order

1. **T-001**: Update PyInstaller Spec (foundation)
2. **T-004**: Create Windows Icon (parallel with T-001)
3. **T-002**: Create Inno Setup Installer Script (requires T-001)
4. **T-003**: Update Windows Build Script (requires T-001, T-002)
5. **T-005**: Update Documentation (requires T-001, T-002, T-003)
6. **T-006**: Performance Testing (requires all build tasks)

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Inno Setup not installed | Medium | Fallback to ZIP archive (T-003) |
| Icon conversion fails | Low | Use existing PNG, document manual conversion |
| Performance target not met | High | Profile startup, optimize imports |
| Installer fails on some systems | Medium | Test on multiple Windows versions |

---

## Rollback Plan

If implementation fails:

1. **Revert T-001**: Restore original `--onefile` configuration
2. **Document slow startup**: Add to known issues in README
3. **Consider alternatives**: Evaluate Nuitka compiler for v0.2.0

---

## Success Criteria

- ✅ Windows startup time < 2 seconds (cold start)
- ✅ Windows startup time < 1 second (warm start)
- ✅ Installer builds successfully
- ✅ ZIP archive fallback works
- ✅ Documentation updated
- ✅ Performance tests pass

---

## Next Steps

1. **Switch to spec-coder mode** for T-001 implementation
2. **Verify T-001 completion** before proceeding to T-002
3. **Continue sequentially** through remaining tasks
4. **Trigger spec-auditor** after all tasks complete

---

**End of Implementation Plan**