param(
    [string]$RuntimeDir = "$env:LOCALAPPDATA/TradingAgentsRuntime"
)
$ErrorActionPreference = 'Stop'
$ollamaExe = Join-Path $RuntimeDir 'ollama/ollama.exe'
if (-not (Test-Path -LiteralPath $ollamaExe)) { throw "Missing Ollama: $ollamaExe" }
$socket = [System.Net.Sockets.TcpClient]::new()
$inUse = $false
try { $socket.Connect('127.0.0.1', 11434); $inUse = $true } catch { } finally { $socket.Dispose() }
if ($inUse) { throw 'Port 11434 is already in use. Verify the existing server before reusing it.' }

$env:OLLAMA_NO_CLOUD = '1'
$env:OLLAMA_HOST = '127.0.0.1:11434'
$env:OLLAMA_MODELS = Join-Path $RuntimeDir 'models'
$env:OLLAMA_CONTEXT_LENGTH = '8192'
$env:OLLAMA_NUM_PARALLEL = '1'
$env:OLLAMA_MAX_LOADED_MODELS = '1'
$env:OLLAMA_KEEP_ALIVE = '5m'
$logDir = Join-Path $RuntimeDir 'logs'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$errLog = Join-Path $logDir "server-$stamp.stderr.log"
$outLog = Join-Path $logDir "server-$stamp.stdout.log"
$server = Start-Process -FilePath $ollamaExe -ArgumentList 'serve' -WindowStyle Hidden -PassThru -RedirectStandardError $errLog -RedirectStandardOutput $outLog
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    $server.Refresh()
    if ($server.HasExited) { throw "Ollama exited. Inspect $errLog" }
    try {
        $version = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/version' -TimeoutSec 2
        if (Select-String -LiteralPath $errLog -Pattern 'Ollama cloud disabled: true' -Quiet) {
            $ready = $true
            break
        }
    } catch { }
}
if (-not $ready) {
    Stop-Process -Id $server.Id -ErrorAction SilentlyContinue
    throw "Local server/cloud-disabled verification failed. Inspect $errLog"
}
$state = [ordered]@{ pid = $server.Id; version = $version.version; endpoint = 'http://127.0.0.1:11434'; cloud_disabled = $true; stderr_log = $errLog; stdout_log = $outLog }
$state | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $RuntimeDir 'server-state.json') -Encoding UTF8
$state | ConvertTo-Json
