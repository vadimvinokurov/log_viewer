# PowerShell Script for Measuring Log Viewer Startup Time
# Ref: docs/specs/features/windows-startup-optimization.md §4.2
# Master: docs/SPEC.md §1

<#
.SYNOPSIS
    Measures startup time for Log Viewer application on Windows.

.DESCRIPTION
    This script measures both cold start (after reboot) and warm start 
    performance for the Log Viewer application. It runs multiple iterations
    and calculates average startup times.
    
    Performance Targets (per spec §4.1):
    - Cold start: < 2 seconds
    - Warm start: < 1 second
    - Improvement: At least 5x over --onefile build

.PARAMETER ExePath
    Path to LogViewer.exe. Default: "C:\Program Files\Log Viewer\LogViewer.exe"

.PARAMETER Iterations
    Number of test iterations. Default: 5

.PARAMETER OutputPath
    Path to save performance report. Default: ".\performance-report.json"

.PARAMETER SkipColdStart
    Skip cold start test (useful for quick warm start testing)

.PARAMETER CompareWith
    Path to old --onefile build for comparison testing

.EXAMPLE
    .\test-startup-time.ps1
    Run default tests with 5 iterations.

.EXAMPLE
    .\test-startup-time.ps1 -ExePath "D:\LogViewer\LogViewer.exe" -Iterations 10
    Test custom installation with 10 iterations.

.EXAMPLE
    .\test-startup-time.ps1 -CompareWith "D:\old-build\LogViewer-onefile.exe"
    Compare new build with old --onefile build.

.NOTES
    File: tests/performance/test-startup-time.ps1
    Context: Testing
    Language: PowerShell 5.1+ / PowerShell 7+
    
    Requirements:
    - Test on clean Windows 10/11 VM
    - Test cold start (after reboot)
    - Test warm start (second launch)
#>

# ============================================================================
# Configuration
# ============================================================================

param(
    [string]$ExePath = "C:\Program Files\Log Viewer\LogViewer.exe",
    [int]$Iterations = 5,
    [string]$OutputPath = ".\performance-report.json",
    [switch]$SkipColdStart,
    [string]$CompareWith
)

# ============================================================================
# Helper Functions
# ============================================================================

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] $Message"
}

function Test-ExecutableExists {
    param([string]$Path)
    
    if (-not (Test-Path $Path)) {
        Write-Error "ERROR: Executable not found at '$Path'"
        Write-Host ""
        Write-Host "Please ensure Log Viewer is installed or specify -ExePath parameter."
        Write-Host "Example: .\test-startup-time.ps1 -ExePath 'D:\LogViewer\LogViewer.exe'"
        exit 1
    }
    return $true
}

function Measure-SingleStart {
    param([string]$Path)
    
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    
    try {
        $process = Start-Process -FilePath $Path -PassThru -ErrorAction Stop
        $process.WaitForExit()
        $stopwatch.Stop()
        return $stopwatch.Elapsed.TotalSeconds
    }
    catch {
        $stopwatch.Stop()
        Write-Error "ERROR: Failed to start process: $_"
        return -1
    }
}

function Measure-WarmStart {
    param(
        [string]$Path,
        [int]$Count
    )
    
    $results = @()
    
    Write-Log "Measuring warm start ($Count iterations)..."
    
    for ($i = 1; $i -le $Count; $i++) {
        Write-Host "  Iteration $i/$Count..." -NoNewline
        
        # First launch to warm up (not counted)
        $warmup = Measure-SingleStart -Path $Path
        Write-Host " (warmup: $([math]::Round($warmup, 3))s)" -NoNewline
        
        # Small delay between launches
        Start-Sleep -Milliseconds 500
        
        # Second launch (measured)
        $time = Measure-SingleStart -Path $Path
        $results += $time
        
        Write-Host " -> $([math]::Round($time, 3))s"
        
        # Delay before next iteration
        Start-Sleep -Milliseconds 500
    }
    
    return $results
}

function Measure-ColdStart {
    param(
        [string]$Path,
        [int]$Count
    )
    
    Write-Log "Measuring cold start ($Count iterations)..."
    Write-Log "IMPORTANT: Reboot VM before each cold start measurement!"
    Write-Host ""
    
    $results = @()
    
    for ($i = 1; $i -le $Count; $i++) {
        Write-Host "  Iteration $i/$Count - Press Enter after reboot..." -NoNewline
        Read-Host
        
        $time = Measure-SingleStart -Path $Path
        $results += $time
        
        Write-Host "  Result: $([math]::Round($time, 3))s"
        
        if ($i -lt $Count) {
            Write-Log "Please reboot VM for next iteration..."
        }
    }
    
    return $results
}

function Get-Statistics {
    param([double[]]$Values)
    
    if ($Values.Count -eq 0) {
        return @{ Min = 0; Max = 0; Avg = 0; Median = 0 }
    }
    
    $sorted = $Values | Sort-Object
    $min = $sorted[0]
    $max = $sorted[-1]
    $avg = ($Values | Measure-Object -Average).Average
    
    # Calculate median
    $midIndex = [math]::Floor($sorted.Count / 2)
    if ($sorted.Count % 2 -eq 0) {
        $median = ($sorted[$midIndex - 1] + $sorted[$midIndex]) / 2
    } else {
        $median = $sorted[$midIndex]
    }
    
    return @{
        Min = [math]::Round($min, 3)
        Max = [math]::Round($max, 3)
        Avg = [math]::Round($avg, 3)
        Median = [math]::Round($median, 3)
    }
}

function New-PerformanceReport {
    param(
        [string]$BuildType,
        [hashtable]$ColdStats,
        [hashtable]$WarmStats,
        [double]$ImprovementFactor,
        [string]$CompareWith
    )
    
    $report = @{
        timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
        build_type = $BuildType
        exe_path = $ExePath
        cold_start = @{
            values = $ColdStats
            target_seconds = 2.0
            passed = $ColdStats.Avg -lt 2.0
        }
        warm_start = @{
            values = $WarmStats
            target_seconds = 1.0
            passed = $WarmStats.Avg -lt 1.0
        }
        comparison = $null
    }
    
    if ($CompareWith) {
        $report.comparison = @{
            old_build = $CompareWith
            improvement_factor = $ImprovementFactor
            target_factor = 5.0
            passed = $ImprovementFactor -ge 5.0
        }
    }
    
    return $report
}

function Write-Report {
    param(
        [hashtable]$Report,
        [string]$Path
    )
    
    $json = $Report | ConvertTo-Json -Depth 5
    $json | Out-File -FilePath $Path -Encoding UTF8
    Write-Log "Report saved to: $Path"
}

function Show-Summary {
    param(
        [hashtable]$ColdStats,
        [hashtable]$WarmStats,
        [double]$ImprovementFactor,
        [string]$CompareWith
    )
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "         PERFORMANCE SUMMARY" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    # Cold start results
    Write-Host "Cold Start (after reboot):" -ForegroundColor Yellow
    Write-Host "  Min:     $($ColdStats.Min) seconds"
    Write-Host "  Max:     $($ColdStats.Max) seconds"
    Write-Host "  Average: $($ColdStats.Avg) seconds"
    Write-Host "  Median:  $($ColdStats.Median) seconds"
    
    $coldPassed = $ColdStats.Avg -lt 2.0
    if ($coldPassed) {
        Write-Host "  Status:  PASSED (< 2s)" -ForegroundColor Green
    } else {
        Write-Host "  Status:  FAILED (>= 2s)" -ForegroundColor Red
    }
    Write-Host ""
    
    # Warm start results
    Write-Host "Warm Start (second launch):" -ForegroundColor Yellow
    Write-Host "  Min:     $($WarmStats.Min) seconds"
    Write-Host "  Max:     $($WarmStats.Max) seconds"
    Write-Host "  Average: $($WarmStats.Avg) seconds"
    Write-Host "  Median:  $($WarmStats.Median) seconds"
    
    $warmPassed = $WarmStats.Avg -lt 1.0
    if ($warmPassed) {
        Write-Host "  Status:  PASSED (< 1s)" -ForegroundColor Green
    } else {
        Write-Host "  Status:  FAILED (>= 1s)" -ForegroundColor Red
    }
    Write-Host ""
    
    # Comparison results
    if ($CompareWith) {
        Write-Host "Comparison with --onefile build:" -ForegroundColor Yellow
        Write-Host "  Improvement: $([math]::Round($ImprovementFactor, 1))x faster"
        
        $comparisonPassed = $ImprovementFactor -ge 5.0
        if ($comparisonPassed) {
            Write-Host "  Status:      PASSED (>= 5x)" -ForegroundColor Green
        } else {
            Write-Host "  Status:      FAILED (< 5x)" -ForegroundColor Red
        }
        Write-Host ""
    }
    
    # Overall result
    Write-Host "========================================" -ForegroundColor Cyan
    $allPassed = $coldPassed -and $warmPassed
    if ($CompareWith) {
        $allPassed = $allPassed -and $comparisonPassed
    }
    
    if ($allPassed) {
        Write-Host "  ALL TESTS PASSED" -ForegroundColor Green
    } else {
        Write-Host "  SOME TESTS FAILED" -ForegroundColor Red
    }
    Write-Host "========================================" -ForegroundColor Cyan
}

# ============================================================================
# Main Script
# ============================================================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Log Viewer Startup Time Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Validate executable exists
Test-ExecutableExists -Path $ExePath

Write-Log "Executable: $ExePath"
Write-Log "Iterations: $Iterations"
Write-Host ""

# Initialize results
$coldResults = @()
$warmResults = @()
$oldBuildResults = @()

# Cold start test
if (-not $SkipColdStart) {
    Write-Host "----------------------------------------" -ForegroundColor Gray
    Write-Host " COLD START TEST" -ForegroundColor Yellow
    Write-Host "----------------------------------------" -ForegroundColor Gray
    Write-Host ""
    Write-Host "This test requires VM reboot between iterations."
    Write-Host "The script will pause and wait for you to reboot."
    Write-Host ""
    
    $coldResults = Measure-ColdStart -Path $ExePath -Count $Iterations
    Write-Host ""
}

# Warm start test
Write-Host "----------------------------------------" -ForegroundColor Gray
Write-Host " WARM START TEST" -ForegroundColor Yellow
Write-Host "----------------------------------------" -ForegroundColor Gray
Write-Host ""

$warmResults = Measure-WarmStart -Path $ExePath -Count $Iterations
Write-Host ""

# Comparison test (if old build specified)
if ($CompareWith) {
    Test-ExecutableExists -Path $CompareWith
    
    Write-Host "----------------------------------------" -ForegroundColor Gray
    Write-Host " COMPARISON TEST (--onefile build)" -ForegroundColor Yellow
    Write-Host "----------------------------------------" -ForegroundColor Gray
    Write-Host ""
    Write-Log "Old build: $CompareWith"
    
    $oldBuildResults = Measure-WarmStart -Path $CompareWith -Count $Iterations
    Write-Host ""
}

# Calculate statistics
$coldStats = if ($coldResults.Count -gt 0) { Get-Statistics -Values $coldResults } else { @{ Min = 0; Max = 0; Avg = 0; Median = 0 } }
$warmStats = Get-Statistics -Values $warmResults

# Calculate improvement factor
$improvementFactor = 0
if ($oldBuildResults.Count -gt 0 -and $warmStats.Avg -gt 0) {
    $oldStats = Get-Statistics -Values $oldBuildResults
    $improvementFactor = $oldStats.Avg / $warmStats.Avg
}

# Generate report
$buildType = if ($ExePath -match "onedir|LogViewer") { "onedir" } else { "onefile" }
$report = New-PerformanceReport -BuildType $buildType -ColdStats $coldStats -WarmStats $warmStats -ImprovementFactor $improvementFactor -CompareWith $CompareWith

# Save report
Write-Report -Report $report -Path $OutputPath

# Show summary
Show-Summary -ColdStats $coldStats -WarmStats $warmStats -ImprovementFactor $improvementFactor -CompareWith $CompareWith

# Exit with appropriate code
$allPassed = $report.cold_start.passed -and $report.warm_start.passed
if ($CompareWith) {
    $allPassed = $allPassed -and $report.comparison.passed
}

if ($allPassed) {
    exit 0
} else {
    exit 1
}