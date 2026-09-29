# Daily autonomous run: generate one optimized video and upload it.
# Used by Windows Task Scheduler. Logs EVERY run (incl. early failures) to .\logs\.
param(
    [string]$Format = "short",
    [string]$Privacy = "public"
)

# --- logging FIRST, so even an early crash is captured ---
$root = $PSScriptRoot
$logDir = Join-Path $root "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir ("run_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
# EVERY write to $log must be "-Encoding utf8". Windows PowerShell 5.1's defaults
# are not UTF-8 and not even consistent with each other: Set-Content defaults to
# ANSI, and Tee-Object -Append writes UTF-16LE no matter what encoding is already
# in the file. That mixture is why every log up to 2026-07-28 ended in
#   "= = =   r u n . p y   e x i t   0   = = ="
# - those are UTF-16 bytes (one NUL after every character) being read back as
# UTF-8. Each log carried 235 stray NUL bytes from the three Note() calls.
"=== $(Get-Date) | format=$Format privacy=$Privacy ===" | Set-Content -Path $log -Encoding utf8
function Note($m) { Write-Host $m; $m | Add-Content -Path $log -Encoding utf8 }

try {
    Set-Location $root

    # Ensure ffmpeg is reachable (Task Scheduler starts with a minimal PATH).
    $ff = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Filter ffmpeg.exe -ErrorAction SilentlyContinue |
          Select-Object -First 1 -ExpandProperty DirectoryName
    if ($ff) { $env:PATH = "$ff;$env:PATH"; Note "ffmpeg: $ff" } else { Note "ffmpeg: relying on PATH" }

    # Resolve python.
    $py = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $py) { $py = "$env:LOCALAPPDATA\Python\pythoncore-3.14-64\python.exe" }
    Note "python: $py"

    # Force UTF-8 end to end: Python's own stdout defaults to the Windows console
    # codepage (not UTF-8) when non-interactive under Task Scheduler, and the old
    # "*>&1 | Tee-Object" pipe re-encodes through PowerShell's own default encoding
    # too - either hop can mangle non-ASCII characters (em dashes, curly quotes) into
    # the U+FFFD replacement character seen in a live video title on 2026-07-19.
    $env:PYTHONIOENCODING = "utf-8"
    # Telling Python to emit UTF-8 is only half of it: PowerShell decodes a native
    # process's stdout using [Console]::OutputEncoding, which under Task Scheduler
    # is the OEM codepage (437), not UTF-8. So run.py's UTF-8 em dash (E2 80 94)
    # was decoded as three cp437 glyphs and re-encoded, turning every em dash in
    # the log into 3 garbage characters even though the pipe below writes UTF-8
    # correctly. Keep this file itself pure ASCII for the same reason. Guarded
    # because assigning this can throw when no console is attached, and an
    # exception here would land in the catch below and report a false FAILURE.
    try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
    & $py run.py --format $Format --upload --privacy $Privacy 2>&1 | Add-Content -Path $log -Encoding utf8
    $code = $LASTEXITCODE
    # If the pipeline never launched a native process, $LASTEXITCODE is $null and
    # "exit $null" exits 0 - a false SUCCESS, which is worse for Jarvis HQ's
    # "needs a human" queue than a false failure, because nothing surfaces at all.
    if ($null -eq $code) { $code = 1; Note "!!! run.py produced no exit code - treating as failure" }
    Note "=== run.py exit $code ==="
    exit $code
}
catch {
    Note "!!! SCHEDULER ERROR: $($_.Exception.Message)"
    Note $_.ScriptStackTrace
    exit 1
}
