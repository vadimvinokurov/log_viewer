# Performance Tests

This directory contains performance testing scripts for Log Viewer.

## Startup Time Test

**File**: [`test-startup-time.ps1`](test-startup-time.ps1)

**Spec Reference**: [`docs/specs/features/windows-startup-optimization.md §4.2`](../../docs/specs/features/windows-startup-optimization.md)

### Purpose

Measures startup time for Log Viewer on Windows to verify performance targets:
- Cold start: < 2 seconds
- Warm start: < 1 second
- Improvement: At least 5x over `--onefile` build

### Requirements

- Windows 10/11 (clean VM recommended for cold start tests)
- PowerShell 5.1+ or PowerShell 7+
- Log Viewer installed or portable build available

### Usage

#### Basic Usage

```powershell
# Run with default settings (5 iterations)
.\test-startup-time.ps1

# Specify custom executable path
.\test-startup-time.ps1 -ExePath "D:\LogViewer\LogViewer.exe"

# Run more iterations for better accuracy
.\test-startup-time.ps1 -Iterations 10
```

#### Cold Start Test

Cold start tests require VM reboot between iterations:

```powershell
# Full test including cold start (requires manual reboots)
.\test-startup-time.ps1

# Skip cold start (warm start only)
.\test-startup-time.ps1 -SkipColdStart
```

#### Comparison Test

Compare new `--onedir` build with old `--onefile` build:

```powershell
.\test-startup-time.ps1 -CompareWith "D:\old-build\LogViewer-onefile.exe"
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ExePath` | string | `C:\Program Files\Log Viewer\LogViewer.exe` | Path to LogViewer.exe |
| `Iterations` | int | 5 | Number of test iterations |
| `OutputPath` | string | `.\performance-report.json` | Path for JSON report |
| `SkipColdStart` | switch | false | Skip cold start test |
| `CompareWith` | string | none | Path to old build for comparison |

### Output

#### Console Output

```
========================================
  Log Viewer Startup Time Test
========================================

[2026-03-22 00:00:00] Executable: C:\Program Files\Log Viewer\LogViewer.exe
[2026-03-22 00:00:00] Iterations: 5

----------------------------------------
 WARM START TEST
----------------------------------------

  Iteration 1/5... (warmup: 0.856s) -> 0.412s
  Iteration 2/5... (warmup: 0.789s) -> 0.398s
  ...

========================================
         PERFORMANCE SUMMARY
========================================

Cold Start (after reboot):
  Min:     1.234 seconds
  Max:     1.567 seconds
  Average: 1.345 seconds
  Median:  1.312 seconds
  Status:  PASSED (< 2s)

Warm Start (second launch):
  Min:     0.398 seconds
  Max:     0.456 seconds
  Average: 0.421 seconds
  Median:  0.418 seconds
  Status:  PASSED (< 1s)

========================================
  ALL TESTS PASSED
========================================
```

#### JSON Report

```json
{
  "timestamp": "2026-03-22T00:00:00Z",
  "build_type": "onedir",
  "exe_path": "C:\\Program Files\\Log Viewer\\LogViewer.exe",
  "cold_start": {
    "values": {
      "Min": 1.234,
      "Max": 1.567,
      "Avg": 1.345,
      "Median": 1.312
    },
    "target_seconds": 2.0,
    "passed": true
  },
  "warm_start": {
    "values": {
      "Min": 0.398,
      "Max": 0.456,
      "Avg": 0.421,
      "Median": 0.418
    },
    "target_seconds": 1.0,
    "passed": true
  },
  "comparison": null
}
```

### Test Procedure

#### Cold Start Test

1. Prepare clean Windows 10/11 VM
2. Install Log Viewer or extract portable build
3. Run script: `.\test-startup-time.ps1`
4. For each iteration:
   - Script pauses and prompts for reboot
   - Reboot VM
   - Log in and press Enter
   - Script measures startup time
5. Review results in console and JSON report

#### Warm Start Test

1. Run script: `.\test-startup-time.ps1 -SkipColdStart`
2. Script automatically:
   - Launches app once (warmup)
   - Waits 500ms
   - Launches app again (measured)
   - Repeats for specified iterations
3. Review results

#### Comparison Test

1. Have both builds available:
   - New: `--onedir` build (installed or portable)
   - Old: `--onefile` build (standalone exe)
2. Run: `.\test-startup-time.ps1 -CompareWith "path\to\old-build.exe"`
3. Script measures both builds and calculates improvement factor

### Performance Targets

Per spec §4.1:

| Metric | Target | Status |
|--------|--------|--------|
| Cold start | < 2 seconds | Required |
| Warm start | < 1 second | Required |
| Improvement | >= 5x vs `--onefile` | Required |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All tests passed |
| 1 | One or more tests failed |

### Troubleshooting

#### "Executable not found"

Ensure Log Viewer is installed or specify `-ExePath`:

```powershell
.\test-startup-time.ps1 -ExePath "D:\portable\LogViewer.exe"
```

#### "Failed to start process"

Check if:
- Executable is blocked by antivirus
- Executable has correct permissions
- Windows Defender is scanning the executable

#### Inconsistent Results

For consistent results:
- Use clean VM for cold start tests
- Close other applications during testing
- Disable Windows Defender real-time scanning temporarily
- Run multiple iterations and use median value

### Related Documentation

- [Windows Startup Optimization Spec](../../docs/specs/features/windows-startup-optimization.md)
- [Application Packaging Spec](../../docs/specs/features/application-packaging.md)
- [Build Instructions](../../docs/BUILD.md)