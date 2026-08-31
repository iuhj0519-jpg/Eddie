[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$manifestDirectory = $PSScriptRoot
$projectRoot = (Resolve-Path (Join-Path $manifestDirectory '..')).Path
$checksumPath = Join-Path $manifestDirectory 'checksums\source_files.sha256'
$errors = New-Object System.Collections.Generic.List[string]
$passes = New-Object System.Collections.Generic.List[string]

function Add-CheckResult {
    param([bool]$Condition, [string]$PassMessage, [string]$ErrorMessage)
    if ($Condition) { $script:passes.Add($PassMessage) }
    else { $script:errors.Add($ErrorMessage) }
}

$requiredFiles = @(
    'source_manifest.yaml', 'phase_access_policy.yaml', 'baseline_manifest.yaml',
    'index_manifest.yaml', 'checksums\source_files.sha256'
)
foreach ($relativePath in $requiredFiles) {
    Add-CheckResult `
        (Test-Path -LiteralPath (Join-Path $manifestDirectory $relativePath) -PathType Leaf) `
        "manifest file exists: $relativePath" "missing manifest file: $relativePath"
}

if ($errors.Count -eq 0) {
    foreach ($yamlFile in Get-ChildItem -LiteralPath $manifestDirectory -Filter '*.yaml' -File) {
        $yamlText = Get-Content -Raw -Encoding utf8 -LiteralPath $yamlFile.FullName
        Add-CheckResult (-not $yamlText.Contains("`t")) `
            "YAML contains no tab indentation: $($yamlFile.Name)" `
            "YAML contains tab indentation: $($yamlFile.Name)"
        Add-CheckResult ($yamlText -match '(?m)^schema_version:\s+"1\.0"\s*$') `
            "YAML schema version is present: $($yamlFile.Name)" `
            "missing YAML schema version: $($yamlFile.Name)"
        Add-CheckResult ($yamlText -match '(?m)^status:\s+\S+') `
            "YAML status is present: $($yamlFile.Name)" `
            "missing YAML status: $($yamlFile.Name)"
    }

    $checksumLines = Get-Content -Encoding utf8 -LiteralPath $checksumPath
    Add-CheckResult ($checksumLines.Count -eq 265) `
        'checksum inventory contains 265 files' `
        "checksum inventory count is $($checksumLines.Count), expected 265"

    $seenPaths = @{}
    foreach ($line in $checksumLines) {
        if ($line -notmatch '^([0-9a-f]{64})  (.+)$') {
            $errors.Add("invalid checksum line: $line")
            continue
        }
        $expectedHash = $Matches[1]
        $relativePath = $Matches[2]
        if ($seenPaths.ContainsKey($relativePath)) {
            $errors.Add("duplicate checksum path: $relativePath")
            continue
        }
        $seenPaths[$relativePath] = $true
        $deniedSource = $relativePath -match '^(historical_baselines|verification|experiments|artifacts|rag/(data|cache|runs))(/|$)' -or
                        ($relativePath -match '^workspace/' -and $relativePath -notmatch '^workspace/systolic_prototype/')
        if ($deniedSource) {
            $errors.Add("denied path is present in checksum inventory: $relativePath")
            continue
        }
        $fullPath = Join-Path $projectRoot ($relativePath.Replace('/', '\'))
        if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
            $errors.Add("manifested source file is missing: $relativePath")
            continue
        }
        $actualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $fullPath).Hash.ToLowerInvariant()
        if ($actualHash -ne $expectedHash) { $errors.Add("SHA-256 mismatch: $relativePath") }
    }
    if ($errors.Count -eq 0) {
        $passes.Add('all manifested files exist and SHA-256 values match')
        $passes.Add('checksum inventory contains no denied paths')
    }

    $groupChecks = @(
        @('reference RTL', 'inputs\reference_model\model\rtl', '*.v', 11),
        @('reference TB', 'inputs\reference_model\model\tb', 'top_sim.v', 1),
        @('weights', 'inputs\reference_model\weights', 'w_*.mif', 60),
        @('biases', 'inputs\reference_model\biases', 'b_*.mif', 60),
        @('activation LUT', 'inputs\reference_model\activation', 'sigContent.mif', 1),
        @('test vectors', 'inputs\reference_model\testdata', 'test_data_*.txt', 100),
        @('reference script', 'inputs\reference_model\scripts', 'run_modelsim.sh', 1),
        @('controller references', 'inputs\systolic_controller\rtl', '*.sv', 4),
        @('prototype RTL SV', 'workspace\systolic_prototype\rtl', '*.sv', 13),
        @('prototype RTL header', 'workspace\systolic_prototype\rtl', '*.svh', 1),
        @('prototype TB', 'workspace\systolic_prototype\tb', 'top_sim.sv', 1)
    )
    foreach ($check in $groupChecks) {
        $actual = @(Get-ChildItem -LiteralPath (Join-Path $projectRoot $check[1]) -Filter $check[2] -File).Count
        Add-CheckResult ($actual -eq $check[3]) `
            "source group count matches: $($check[0]) = $($check[3])" `
            "source group count mismatch: $($check[0]) = $actual, expected $($check[3])"
    }

    $specPaths = @(
        'inputs\specifications\01_reference_model\REFERENCE_MODEL_SPECIFICATION.md',
        'inputs\specifications\02_systolic_accelerator\SYSTOLIC_ACCELERATOR_SPECIFICATION.md',
        'inputs\specifications\03_architecture_optimization\ARCHITECTURE_OPTIMIZATION_SPECIFICATION.md'
    )
    foreach ($specPath in $specPaths) {
        $specText = Get-Content -Raw -Encoding utf8 -LiteralPath (Join-Path $projectRoot $specPath)
        Add-CheckResult `
            ([regex]::IsMatch($specText, '(?m)^- [^:\r\n]+:\s*approved\s*$')) `
            "normative SPEC is approved: $specPath" "normative SPEC is not approved: $specPath"
    }

    $sourceManifest = Get-Content -Raw -Encoding utf8 -LiteralPath (Join-Path $manifestDirectory 'source_manifest.yaml')
    $accessPolicy = Get-Content -Raw -Encoding utf8 -LiteralPath (Join-Path $manifestDirectory 'phase_access_policy.yaml')
    $baselineManifest = Get-Content -Raw -Encoding utf8 -LiteralPath (Join-Path $manifestDirectory 'baseline_manifest.yaml')
    $indexManifest = Get-Content -Raw -Encoding utf8 -LiteralPath (Join-Path $manifestDirectory 'index_manifest.yaml')

    Add-CheckResult ($sourceManifest -match '(?m)^expected_total_files:\s+265\s*$') `
        'source manifest expects 265 files' 'source manifest expected_total_files is not 265'
    Add-CheckResult ($accessPolicy -match '(?m)^default_action:\s+deny\s*$') `
        'phase access policy uses default deny' 'phase access policy is not default deny'
    Add-CheckResult ($accessPolicy -match '(?ms)optimization_generation:\s*\r?\n\s+enabled:\s+true') `
        'optimization generation phase is enabled' 'optimization generation phase is not enabled'
    Add-CheckResult ($accessPolicy -match 'historical_baselines/\*\*') `
        'generation phases deny Historical Baselines' 'Historical Baseline deny rule is missing'
    Add-CheckResult ($accessPolicy -match 'workspace/optimized_accelerator/\*\*') `
        'optimization output is denied as generation evidence' 'optimization output deny rule is missing'
    Add-CheckResult ($accessPolicy -match 'external_knowledge_access:\s+false') `
        'external knowledge is disabled for generation' 'external knowledge disable rule is missing'
    Add-CheckResult ($baselineManifest -match '(?m)^\s+pass:\s+99\s*$' -and
                     $baselineManifest -match '(?m)^\s+fail:\s+1\s*$' -and
                     $baselineManifest -match '(?m)^\s+accuracy_percent:\s+99\.0\s*$') `
        'functional baseline is 99 PASS / 1 FAIL / 99.0 percent' `
        'functional baseline values do not match'
    Add-CheckResult ($indexManifest -match '(?m)^status:\s+(not_built|built)\s*$') `
        'index manifest has a recognized lifecycle status' `
        'index manifest status must be not_built or built'
}

foreach ($message in $passes) { Write-Output "PASS: $message" }
if ($errors.Count -gt 0) {
    foreach ($message in $errors) { Write-Error "FAIL: $message" }
    exit 1
}
Write-Output "PASS: manifest validation completed with $($passes.Count) checks"
exit 0
