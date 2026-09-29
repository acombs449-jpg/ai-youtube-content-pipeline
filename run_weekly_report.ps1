# Weekly status report: gathers stats, appends scheduler health, opens the report.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = "$env:LOCALAPPDATA\Python\pythoncore-3.14-64\python.exe" }

& $py weekly_report.py | Out-Null

# Newest report file
$report = Get-ChildItem .\reports\report_*.md | Sort-Object LastWriteTime | Select-Object -Last 1

# Append scheduler health (PowerShell-only info)
$lines = @("", "## Automation health")
foreach ($t in Get-ScheduledTask | Where-Object { $_.TaskName -like "FinanceYT*" }) {
    $i = $t | Get-ScheduledTaskInfo
    if ($i.LastRunTime.Year -lt 2000) {
        $lines += "- $($t.TaskName): not run yet | next: $($i.NextRunTime)"
    } else {
        $ok = if ($i.LastTaskResult -eq 0) { "OK" } else { "FAILED (code $($i.LastTaskResult))" }
        $lines += "- $($t.TaskName): last run $($i.LastRunTime) -> $ok | next: $($i.NextRunTime)"
    }
}
Add-Content -Path $report.FullName -Value ($lines -join "`n") -Encoding utf8

# Pop it open so it actually gets seen (no-op if nobody is logged in)
try { Start-Process notepad $report.FullName } catch {}
