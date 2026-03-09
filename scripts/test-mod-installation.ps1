# ============================================================================
# Total War: Napoleon Mod Installation Test Suite - Windows
# Comprehensive validation tests for mod installations
# Usage: .\test-mod-installation.ps1 -ModName "ModName" [-GameRoot "Path"]
# ============================================================================

param(
    [Parameter(Mandatory=$true)]
    [string]$ModName,
    
    [Parameter(Mandatory=$false)]
    [string]$GameRoot,
    
    [Parameter(Mandatory=$false)]
    [switch]$Verbose,
    
    [Parameter(Mandatory=$false)]
    [switch]$CI
)

# Test results tracking
$TestResults = @()
$TotalTests = 0
$PassedTests = 0
$FailedTests = 0
$Warnings = 0

# Helper function - must be defined before use
function Format-FileSize {
    param([long]$Size)
    
    if ($Size -gt 1GB) { return "{0:N2} GB" -f ($Size / 1GB) }
    elseif ($Size -gt 1MB) { return "{0:N2} MB" -f ($Size / 1MB) }
    elseif ($Size -gt 1KB) { return "{0:N2} KB" -f ($Size / 1KB) }
    else { return "{0:N0} bytes" -f $Size }
}

# Colors for output
function Write-TestHeader {
    param([string]$Text)
    Write-Host "============================================================================" -ForegroundColor Cyan
    Write-Host $Text -ForegroundColor Cyan
    Write-Host "============================================================================" -ForegroundColor Cyan
}

function Write-TestPass {
    param([string]$Text)
    Write-Host "[PASS] $Text" -ForegroundColor Green
}

function Write-TestFail {
    param([string]$Text)
    Write-Host "[FAIL] $Text" -ForegroundColor Red
}

function Write-TestWarn {
    param([string]$Text)
    Write-Host "[WARN] $Text" -ForegroundColor Yellow
}

function Write-TestInfo {
    param([string]$Text)
    Write-Host "[INFO] $Text" -ForegroundColor Gray
}

function Add-TestResult {
    param(
        [string]$TestName,
        [bool]$Passed,
        [string]$Message,
        [string]$Severity = "Error"
    )
    
    $Global:TestResults += [PSCustomObject]@{
        Test = $TestName
        Passed = $Passed
        Message = $Message
        Severity = $Severity
    }
    
    $Global:TotalTests++
    if ($Passed) {
        $Global:PassedTests++
    } elseif ($Severity -ne "Info" -and $Severity -ne "Warning") {
        # Only count as failure if severity is Error (not Info or Warning)
        $Global:FailedTests++
    }
}

# Auto-detect game installation if not provided
if (-not $GameRoot) {
    Write-TestInfo "Auto-detecting game installation..."
    
    # Check Steam registry
    $SteamPath = Get-ItemProperty -Path "HKLM:\SOFTWARE\Wow6432Node\Valve\Steam" -Name "InstallPath" -ErrorAction SilentlyContinue
    if ($SteamPath) {
        $TestGameRoot = "$($SteamPath.InstallPath)\steamapps\common\Napoleon Total War"
        if (Test-Path $TestGameRoot) {
            $GameRoot = $TestGameRoot
            Write-TestInfo "Found game at: $GameRoot"
        }
    }
    
    # Check common paths
    if (-not $GameRoot) {
        $CommonPaths = @(
            "C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War",
            "C:\Program Files\Steam\steamapps\common\Napoleon Total War",
            "C:\Program Files (x86)\Napoleon Total War",
            "C:\Program Files\Napoleon Total War"
        )
        
        foreach ($Path in $CommonPaths) {
            if (Test-Path $Path) {
                $GameRoot = $Path
                Write-TestInfo "Found game at: $GameRoot"
                break
            }
        }
    }
    
    if (-not $GameRoot) {
        Write-Host "============================================================================" -ForegroundColor Red
        Write-Host "[ERROR] Could not detect Total War: Napoleon installation" -ForegroundColor Red
        Write-Host "============================================================================" -ForegroundColor Red
        Write-Host "Please specify the game root path using -GameRoot parameter" -ForegroundColor Yellow
        Write-Host "Example: .\test-mod-installation.ps1 -ModName `"The Great War`" -GameRoot `"C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War`"" -ForegroundColor Yellow
        exit 1
    }
}

$ModPath = "$GameRoot\data\$ModName"
$LogFile = "$env:TEMP\ntw_mod_test_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

Write-TestHeader "Total War: Napoleon Mod Test Suite - Windows"
Write-Host ""
Write-TestInfo "Mod Name: $ModName"
Write-TestInfo "Game Root: $GameRoot"
Write-TestInfo "Mod Path: $ModPath"
Write-TestInfo "Log File: $LogFile"
Write-Host ""

# Check if mod directory exists
if (-not (Test-Path $ModPath)) {
    Write-TestHeader "CRITICAL ERROR"
    Write-TestFail "Mod directory does not exist: $ModPath"
    Write-TestInfo "Please install the mod first using install-mod-windows.bat"
    exit 1
}

Write-TestHeader "Running Tests"
Write-Host ""

# ============================================================================
# TEST 1: Directory Structure Validation
# ============================================================================
Write-TestInfo "Test 1: Directory Structure Validation"
$Test1Pass = $true
$Test1Msg = ""

if (-not (Test-Path $ModPath)) {
    $Test1Pass = $false
    $Test1Msg = "Mod directory missing"
} elseif ((Get-ChildItem -Path $ModPath -Directory).Count -eq 0) {
    $Test1Pass = $false
    $Test1Msg = "No subdirectories found in mod"
} else {
    $SubDirs = Get-ChildItem -Path $ModPath -Directory
    $Test1Msg = "Found $($SubDirs.Count) subdirectories"
}

if ($Test1Pass) { Write-TestPass $Test1Msg } else { Write-TestFail $Test1Msg }
Add-TestResult -TestName "Directory Structure" -Passed $Test1Pass -Message $Test1Msg

Write-Host ""

# ============================================================================
# TEST 2: File Count Validation
# ============================================================================
Write-TestInfo "Test 2: File Count Validation"
$FileCount = (Get-ChildItem -Path $ModPath -Recurse -File).Count
$Test2Pass = $FileCount -gt 0
$Test2Msg = "Total files: $FileCount"

if ($Test2Pass) { Write-TestPass $Test2Msg } else { Write-TestFail $Test2Msg }
Add-TestResult -TestName "File Count" -Passed $Test2Pass -Message $Test2Msg

Write-Host ""

# ============================================================================
# TEST 3: Pack File Validation
# ============================================================================
Write-TestInfo "Test 3: Pack File Validation"
$PackFiles = Get-ChildItem -Path $ModPath -Filter "*.pack" -File
$Test3Pass = $PackFiles.Count -gt 0
$Test3Msg = ""

if ($Test3Pass) {
    $Test3Msg = "Found $($PackFiles.Count) .pack files"
    if ($Verbose) {
        foreach ($Pack in $PackFiles) {
            Write-TestInfo "  - $($Pack.Name) ($(Format-FileSize $Pack.Length))"
        }
    }
} else {
    $Test3Msg = "No .pack files found (mod may use different structure)"
    $Warnings++
}

if ($Test3Pass) { Write-TestPass $Test3Msg } else { Write-TestWarn $Test3Msg }
Add-TestResult -TestName "Pack Files" -Passed $Test3Pass -Message $Test3Msg -Severity "Warning"

Write-Host ""

# ============================================================================
# TEST 4: Pack File Integrity Check
# ============================================================================
Write-TestInfo "Test 4: Pack File Integrity Check"
$Test4Pass = $true
$Test4Msg = ""
$CorruptPacks = @()

foreach ($Pack in $PackFiles) {
    try {
        # Check if file is readable and has content
        $FileContent = Get-Content -Path $Pack.FullName -Encoding Byte -TotalCount 1 -ErrorAction Stop
        if ($Pack.Length -lt 1024) {
            # Very small pack files might be corrupted or empty
            $CorruptPacks += $Pack.Name
            $Test4Pass = $false
        }
    } catch {
        $CorruptPacks += $Pack.Name
        $Test4Pass = $false
    }
}

if ($Test4Pass) {
    $Test4Msg = "All pack files are readable and valid"
    Write-TestPass $Test4Msg
} else {
    $Test4Msg = "Potentially corrupt pack files: $($CorruptPacks -join ', ')"
    Write-TestFail $Test4Msg
}

Add-TestResult -TestName "Pack File Integrity" -Passed $Test4Pass -Message $Test4Msg

Write-Host ""

# ============================================================================
# TEST 5: Launcher Validation
# ============================================================================
Write-TestInfo "Test 5: Launcher Validation"
$LauncherPath = "$ModPath\launcher.exe"
$Test5Pass = Test-Path $LauncherPath
$Test5Msg = ""

if ($Test5Pass) {
    $Launcher = Get-Item $LauncherPath
    $Test5Msg = "Launcher found ($([Math]::Round($Launcher.Length / 1KB, 2)) KB)"
    Write-TestPass $Test5Msg
} else {
    $Test5Msg = "No launcher.exe found (not all mods include one)"
    Write-TestInfo $Test5Msg
}

Add-TestResult -TestName "Launcher" -Passed $Test5Pass -Message $Test5Msg -Severity "Info"

Write-Host ""

# ============================================================================
# TEST 6: Data Folder Structure
# ============================================================================
Write-TestInfo "Test 6: Data Folder Structure"
$TestDataPath = "$ModPath\data"
$Test6Pass = Test-Path $TestDataPath
$Test6Msg = ""

if ($Test6Pass) {
    $DataSubDirs = (Get-ChildItem -Path $TestDataPath -Directory).Count
    $Test6Msg = "Data folder structure valid ($DataSubDirs subdirectories)"
    Write-TestPass $Test6Msg
} else {
    $Test6Msg = "No data subfolder (structure may vary by mod)"
    Write-TestInfo $Test6Msg
}

Add-TestResult -TestName "Data Folder Structure" -Passed $Test6Pass -Message $Test6Msg -Severity "Info"

Write-Host ""

# ============================================================================
# TEST 7: Common Mod File Types
# ============================================================================
Write-TestInfo "Test 7: Common Mod File Types"
$CommonExtensions = @("*.pack", "*.txt", "*.lua", "*.xml", "*.json", "*.tga", "*.dds")
$FoundFiles = @()

foreach ($Ext in $CommonExtensions) {
    $FoundFiles += Get-ChildItem -Path $ModPath -Filter $Ext -Recurse -File -ErrorAction SilentlyContinue
}

$Test7Pass = $FoundFiles.Count -gt 0
$Test7Msg = ""

if ($Test7Pass) {
    $Test7Msg = "Found $($FoundFiles.Count) common mod files"
    if ($Verbose) {
        $GroupedFiles = $FoundFiles | Group-Object Extension | Sort-Object Count -Descending
        foreach ($Group in $GroupedFiles) {
            Write-TestInfo "  - $($Group.Name): $($Group.Count) files"
        }
    }
    Write-TestPass $Test7Msg
} else {
    $Test7Msg = "No common mod file types found"
    Write-TestWarn $Test7Msg
    $Warnings++
}

Add-TestResult -TestName "Common File Types" -Passed $Test7Pass -Message $Test7Msg -Severity "Warning"

Write-Host ""

# ============================================================================
# TEST 8: File Permissions Check
# ============================================================================
Write-TestInfo "Test 8: File Permissions Check"
$Test8Pass = $true
$Test8Msg = ""
$PermissionIssues = @()

try {
    # Try to read files to check permissions
    $TestFile = Get-ChildItem -Path $ModPath -File | Select-Object -First 1
    if ($TestFile) {
        $Null = Get-Content -Path $TestFile.FullName -ErrorAction Stop
        $Test8Msg = "File permissions OK"
        Write-TestPass $Test8Msg
    } else {
        $Test8Msg = "No files to check permissions"
        Write-TestInfo $Test8Msg
    }
} catch {
    $Test8Pass = $false
    $Test8Msg = "Permission issues detected: $($_.Exception.Message)"
    Write-TestFail $Test8Msg
}

Add-TestResult -TestName "File Permissions" -Passed $Test8Pass -Message $Test8Msg

Write-Host ""

# ============================================================================
# TEST 9: Mod Configuration Files
# ============================================================================
Write-TestInfo "Test 9: Mod Configuration Files"
$ConfigFiles = @()
$ConfigPatterns = @("*.script.txt", "user.script", "preferences*", "config*", "*.ini", "mod.info")

foreach ($Pattern in $ConfigPatterns) {
    $ConfigFiles += Get-ChildItem -Path $ModPath -Filter $Pattern -File -ErrorAction SilentlyContinue
}

$Test9Pass = $ConfigFiles.Count -gt 0
$Test9Msg = ""

if ($Test9Pass) {
    $Test9Msg = "Found $($ConfigFiles.Count) configuration file(s)"
    Write-TestPass $Test9Msg
} else {
    $Test9Msg = "No configuration files found (may be optional)"
    Write-TestInfo $Test9Msg
}

Add-TestResult -TestName "Configuration Files" -Passed $Test9Pass -Message $Test9Msg -Severity "Info"

Write-Host ""

# ============================================================================
# TEST 10: Directory Size Check
# ============================================================================
Write-TestInfo "Test 10: Directory Size Check"
$Test10Pass = $true
$Test10Msg = ""

try {
    $TotalSize = (Get-ChildItem -Path $ModPath -Recurse -File | Measure-Object -Property Length -Sum).Sum
    $SizeFormatted = Format-FileSize $TotalSize
    $Test10Msg = "Total mod size: $SizeFormatted"
    
    if ($TotalSize -eq 0) {
        $Test10Pass = $false
        $Test10Msg = "Mod directory is empty (0 bytes)"
        Write-TestFail $Test10Msg
    } else {
        Write-TestPass $Test10Msg
    }
} catch {
    $Test10Pass = $false
    $Test10Msg = "Could not calculate directory size"
    Write-TestFail $Test10Msg
}

Add-TestResult -TestName "Directory Size" -Passed $Test10Pass -Message $Test10Msg

Write-Host ""

# ============================================================================
# Generate Test Report
# ============================================================================
Write-TestHeader "Test Summary"
Write-Host ""
Write-Host "Total Tests:  $TotalTests" -ForegroundColor Cyan
Write-Host "Passed:       $PassedTests" -ForegroundColor Green
Write-Host "Failed:       $FailedTests" -ForegroundColor $(if ($FailedTests -gt 0) { "Red" } else { "Gray" })
Write-Host "Warnings:     $Warnings" -ForegroundColor Yellow
Write-Host ""

$SuccessRate = [Math]::Round(($PassedTests / $TotalTests) * 100, 2)
Write-Host "Success Rate: $SuccessRate%" -ForegroundColor $(if ($SuccessRate -eq 100) { "Green" } else { "Yellow" })
Write-Host ""

# Save detailed report to log
$ReportPath = "$env:TEMP\ntw_mod_test_report_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"
$TestResults | Format-Table -AutoSize | Out-File -FilePath $ReportPath -Encoding UTF8
Write-TestInfo "Detailed report saved to: $ReportPath"
Write-Host ""

# Final verdict
Write-TestHeader "Final Verdict"

if ($FailedTests -eq 0) {
    Write-Host "[SUCCESS] All critical tests passed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Your mod is ready to use!" -ForegroundColor Green
    if (Test-Path $LauncherPath) {
        Write-Host "Launch the mod with: $LauncherPath" -ForegroundColor Cyan
    } else {
        Write-Host "Enable the mod through your game launcher or mod manager" -ForegroundColor Cyan
    }
    
    if ($CI) {
        exit 0
    }
} else {
    Write-Host "[WARNING] Some tests failed ($FailedTests/$TotalTests)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Review the failed tests above and check:" -ForegroundColor Yellow
    Write-Host "  - Mod files are complete and not corrupted" -ForegroundColor Yellow
    Write-Host "  - Installation path is correct" -ForegroundColor Yellow
    Write-Host "  - All required files were copied" -ForegroundColor Yellow
    Write-Host "  - File permissions are correct" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Log file: $LogFile" -ForegroundColor Gray
    
    if ($CI) {
        exit 1
    }
}
