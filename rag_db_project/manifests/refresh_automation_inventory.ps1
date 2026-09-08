param([string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference = 'Stop'
$projectPath = (Resolve-Path -LiteralPath $ProjectRoot).Path
$inventoryPath = Join-Path $projectPath 'manifests/checksums/automation_loop_files.sha256'
$relativePaths = [System.Collections.Generic.HashSet[string]]::new()
if (Test-Path -LiteralPath $inventoryPath) {
    foreach ($line in Get-Content -LiteralPath $inventoryPath) {
        if ($line -match '^[0-9a-fA-F]{64}\s+(.+)$') { [void]$relativePaths.Add($Matches[1]) }
    }
}
foreach ($folder in @('experiments/automation_loop','rag/automation','artifacts/implementation/optimized_accelerator','artifacts/automation_system_tests')) {
    foreach ($file in Get-ChildItem -LiteralPath (Join-Path $projectPath $folder) -Recurse -File -ErrorAction SilentlyContinue) {
        if ($file.FullName -match '__pycache__' -or $file.Extension -notin @('.py','.tcl','.md','.yaml','.json','.rpt','.log')) { continue }
        [void]$relativePaths.Add($file.FullName.Substring($projectPath.Length + 1).Replace('\','/'))
    }
}
foreach ($name in @('manifests/automation_loop_manifest.yaml','manifests/automation_loop_policy.yaml','manifests/phase_access_policy.yaml','rag/config/automation_loop.yaml','rag/config/automation_loop_index.yaml')) { [void]$relativePaths.Add($name) }
$lines = foreach ($name in ($relativePaths | Sort-Object)) {
    $file = [System.IO.Path]::GetFullPath((Join-Path $projectPath $name))
    if (-not $file.StartsWith($projectPath + '\', [System.StringComparison]::OrdinalIgnoreCase) -or $name.StartsWith('historical_baselines/')) { throw "Forbidden inventory path: $name" }
    if (Test-Path -LiteralPath $file -PathType Leaf) { (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLower() + '  ' + $name }
}
[System.IO.File]::WriteAllLines($inventoryPath, $lines, [System.Text.UTF8Encoding]::new($false))
Write-Output "Automation inventory: $($lines.Count) files"
