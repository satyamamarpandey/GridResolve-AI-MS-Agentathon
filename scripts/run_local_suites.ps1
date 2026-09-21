# Runs the three local GridResolve AI test suites and prints one compact summary.
#
# Every number printed is parsed from the actual run. Nothing is hardcoded, so a
# regression shows up as a failure in the summary rather than a clean-looking
# screenshot that is no longer true.
#
# verify_live_config.py is deliberately excluded: it prints the Foundry resource
# and project names, which are kept out of the public repository.
#
# Usage, from anywhere:
#   powershell -ExecutionPolicy Bypass -File scripts\run_local_suites.ps1

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# In an interactive console the test runners emit ANSI colour codes, which put
# escape sequences in front of the summary line and break a naive line match.
# Colour is turned off at the source and stripped defensively as well, because
# one of those two will hold even if a runner ignores the environment.
$env:NO_COLOR = '1'
$env:FORCE_COLOR = '0'
$env:CI = '1'

$ESC = [char]27

function Remove-Ansi {
    param([string]$Text)
    if (-not $Text) { return '' }
    return [regex]::Replace($Text, "$ESC\[[0-9;?]*[A-Za-z]", '')
}

function New-Result { @{ Passed = 0; Failed = 0; Found = $false; Raw = '' } }

function Read-PythonResult {
    param([string]$Text)
    $r = New-Result
    $r.Raw = $Text
    $m = [regex]::Match($Text, 'RESULT:\s*(\d+)\s*passed,\s*(\d+)\s*failed')
    if ($m.Success) {
        $r.Passed = [int]$m.Groups[1].Value
        $r.Failed = [int]$m.Groups[2].Value
        $r.Found = $true
    }
    return $r
}

function Read-VitestResult {
    param([string]$Text)
    # Vitest prints "Tests  132 passed (132)" when green but
    # "Tests  1 failed | 121 passed (122)" when red, with failed first. So the
    # summary line is isolated and each count read independently, otherwise a
    # failing run would report zero passed and misstate the totals.
    $r = New-Result
    $r.Raw = $Text
    $line = [regex]::Match($Text, '(?m)^\s*Tests\s+\d+.*$')
    if ($line.Success) {
        $r.Found = $true
        $p = [regex]::Match($line.Value, '(\d+)\s+passed')
        if ($p.Success) { $r.Passed = [int]$p.Groups[1].Value }
        $f = [regex]::Match($line.Value, '(\d+)\s+failed')
        if ($f.Success) { $r.Failed = [int]$f.Groups[1].Value }
    }
    return $r
}

Write-Host ""
Write-Host "Running three local suites. No model is called and no Azure cost is incurred." -ForegroundColor DarkGray
Write-Host ""

# 1. Routing semantics and case data
Write-Host "  [1/3] routing and case data ..." -NoNewline
$routing = Read-PythonResult (Remove-Ansi ((& python tests\test_routing_and_data.py) | Out-String))
Write-Host " done"

# 2. Synthetic data integrity
Write-Host "  [2/3] synthetic data integrity ..." -NoNewline
$synth = Read-PythonResult (Remove-Ansi ((& python tests\validate_synthetic_data.py) | Out-String))
Write-Host " done"

# 3. Control Center application
# Invoked through node against the local install rather than npx, so the run
# does not depend on npx being resolvable in whatever shell this is started
# from, and no extra cmd.exe layer sits between here and the output.
Write-Host "  [3/3] Control Center application ..." -NoNewline
$app = New-Result
$vitest = Join-Path $root 'control-center\node_modules\vitest\vitest.mjs'
$node = (Get-Command node -ErrorAction SilentlyContinue)

if (-not (Test-Path $vitest)) {
    $app.Raw = "vitest not found at $vitest. Run: cd control-center; npm install"
} elseif (-not $node) {
    $app.Raw = 'node was not found on PATH.'
} else {
    Push-Location (Join-Path $root 'control-center')
    $raw = (& $node.Source $vitest run --reporter=default --no-color 2>&1) | Out-String
    Pop-Location
    $app = Read-VitestResult (Remove-Ansi $raw)
}
Write-Host " done"

$total = $routing.Passed + $synth.Passed + $app.Passed
$totalFailed = $routing.Failed + $synth.Failed + $app.Failed
$allFound = $routing.Found -and $synth.Found -and $app.Found

$line = '=' * 64
Write-Host ""
Write-Host $line -ForegroundColor DarkCyan
Write-Host "  GridResolve AI - Local Verification" -ForegroundColor White
Write-Host ("  " + (Get-Date -Format 'yyyy-MM-dd HH:mm')) -ForegroundColor DarkGray
Write-Host $line -ForegroundColor DarkCyan
Write-Host ""

function Write-Row {
    param([string]$Name, $Result)
    Write-Host ("  {0,-30}" -f $Name) -NoNewline
    if (-not $Result.Found) {
        Write-Host "   could not read result" -ForegroundColor Red
        return
    }
    $status = "{0,4} passed, {1} failed" -f $Result.Passed, $Result.Failed
    $colour = 'Green'
    if ($Result.Failed -gt 0) { $colour = 'Red' }
    Write-Host $status -ForegroundColor $colour
}

Write-Row 'Routing and case data'      $routing
Write-Row 'Synthetic data integrity'   $synth
Write-Row 'Control Center application' $app

Write-Host ("  " + ('-' * 60)) -ForegroundColor DarkGray
Write-Host ("  {0,-30}" -f 'TOTAL') -NoNewline
if ($totalFailed -eq 0 -and $allFound) {
    Write-Host ("{0,4} passed, 0 failed" -f $total) -ForegroundColor Green
} else {
    Write-Host ("{0,4} passed, {1} failed" -f $total, $totalFailed) -ForegroundColor Red
}

Write-Host ""
if ($totalFailed -eq 0 -and $allFound) {
    Write-Host "  ALL LOCAL SUITES PASS" -ForegroundColor Green
} else {
    Write-Host "  SUITE FAILURE, do not screenshot this as passing" -ForegroundColor Red
}
Write-Host "  No model call. No workflow execution. Azure cost: `$0.00" -ForegroundColor DarkGray
Write-Host $line -ForegroundColor DarkCyan
Write-Host ""

# A suite whose result could not be read is a tooling problem, not a pass or a
# fail. Print enough of its output to diagnose it instead of leaving a silent
# zero in the summary.
foreach ($pair in @(@('Routing', $routing), @('Synthetic data', $synth), @('Control Center', $app))) {
    if (-not $pair[1].Found) {
        Write-Host ("  Diagnostic for {0}:" -f $pair[0]) -ForegroundColor Yellow
        $tail = ($pair[1].Raw -split "`r?`n" | Where-Object { $_.Trim() } | Select-Object -Last 12)
        if ($tail) { $tail | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkYellow } }
        else { Write-Host "    no output captured" -ForegroundColor DarkYellow }
        Write-Host ""
    }
}

if ($totalFailed -eq 0 -and $allFound) { exit 0 } else { exit 1 }
