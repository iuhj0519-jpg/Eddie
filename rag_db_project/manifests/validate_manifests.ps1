[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$manifestDirectory = $PSScriptRoot
$projectRoot = (Resolve-Path (Join-Path $manifestDirectory '..')).Path
$checksumPath = Join-Path $manifestDirectory 'checksums\source_files.sha256'
$errors = New-Object System.Collections.Generic.List[string]
$passes = New-Object System.Collections.Generic.List[string]

function Add-CheckResult {
    param(
        [bool]$Condition,
        [string]$PassMessage,
        [string]$ErrorMessage
    )

    if ($Condition) {
        $script:passes.Add($PassMessage)
    }
    else {
        $script:errors.Add($ErrorMessage)
    }
}

$requiredManifestFiles = @(
    'source_manifest.yaml',
    'phase_access_policy.yaml',
    'baseline_manifest.yaml',
    'index_manifest.yaml',
    'checksums\source_files.sha256'
)

foreach ($relativePath in $requiredManifestFiles) {
    $fullPath = Join-Path $manifestDirectory $relativePath
    Add-CheckResult (Test-Path -LiteralPath $fullPath -PathType Leaf) `
        "manifest file exists: $relativePath" `
        "missing manifest file: $relativePath"
}

if ($errors.Count -eq 0) {
    $yamlFiles = Get-ChildItem -LiteralPath $manifestDirectory -Filter '*.yaml' -File
    foreach ($yamlFile in $yamlFiles) {
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
    Add-CheckResult ($checksumLines.Count -eq 247) `
        'checksum inventory contains 247 files' `
        "checksum inventory count is $($checksumLines.Count), expected 247"

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

        if ($relativePath -match '^(historical_baselines|workspace|verification|experiments|artifacts|rag/(data|cache|runs))(/|$)') {
            $errors.Add("denied path is present in checksum inventory: $relativePath")
            continue
        }

        $fullPath = Join-Path $projectRoot ($relativePath.Replace('/', '\'))
        if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
            $errors.Add("manifested source file is missing: $relativePath")
            continue
        }

        $actualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $fullPath).Hash.ToLowerInvariant()
        if ($actualHash -ne $expectedHash) {
            $errors.Add("SHA-256 mismatch: $relativePath")
        }
    }

    if ($errors.Count -eq 0) {
        $passes.Add('all manifested files exist and SHA-256 values match')
        $passes.Add('checksum inventory contains no denied paths')
    }

    $expectedCounts = [ordered]@{
        'inputs\reference_model\model\rtl' = 11
        'inputs\reference_model\model\tb' = 1
        'inputs\reference_model\weights' = 60
        'inputs\reference_model\biases' = 60
        'inputs\reference_model\activation' = 1
        'inputs\reference_model\testdata' = 100
        'inputs\reference_model\scripts' = 1
        'inputs\systolic_controller' = 6
        'inputs\specifications\01_reference_model' = 2
        'inputs\specifications\02_systolic_accelerator' = 2
    }
    foreach ($relativeDirectory in $expectedCounts.Keys) {
        $actualCount = (Get-ChildItem -LiteralPath (Join-Path $projectRoot $relativeDirectory) -File -Recurse).Count
        $expectedCount = $expectedCounts[$relativeDirectory]
        Add-CheckResult ($actualCount -eq $expectedCount) `
            "source group count matches: $relativeDirectory = $expectedCount" `
            "source group count mismatch: $relativeDirectory = $actualCount, expected $expectedCount"
    }

    $navigationDocuments = @(
        'inputs\README.md',
        'inputs\reference_model\README.md',
        'inputs\specifications\README.md'
    )
    $navigationDocumentCount = @(
        $navigationDocuments | Where-Object {
            Test-Path -LiteralPath (Join-Path $projectRoot $_) -PathType Leaf
        }
    ).Count
    Add-CheckResult `
        -Condition ($navigationDocumentCount -eq 3) `
        -PassMessage 'source group count matches: input navigation documents = 3' `
        -ErrorMessage "source group count mismatch: input navigation documents = $navigationDocumentCount, expected 3"

    $referenceSpec = Get-Content -Raw -Encoding utf8 -LiteralPath `
        (Join-Path $projectRoot 'inputs\specifications\01_reference_model\REFERENCE_MODEL_SPECIFICATION.md')
    $systolicSpec = Get-Content -Raw -Encoding utf8 -LiteralPath `
        (Join-Path $projectRoot 'inputs\specifications\02_systolic_accelerator\SYSTOLIC_ACCELERATOR_SPECIFICATION.md')
    # Match the metadata value without embedding a locale-dependent field name.
    # This keeps the validator stable under legacy Windows console code pages.
    $referenceSpecApproved = [regex]::IsMatch(
        $referenceSpec,
        '(?m)^- [^:\r\n]+:\s*approved\s*$'
    )
    $systolicSpecApproved = [regex]::IsMatch(
        $systolicSpec,
        '(?m)^- [^:\r\n]+:\s*approved\s*$'
    )
    Add-CheckResult `
        -Condition $referenceSpecApproved `
        -PassMessage 'Reference Model SPEC is approved' `
        -ErrorMessage 'Reference Model SPEC is not approved'
    Add-CheckResult `
        -Condition $systolicSpecApproved `
        -PassMessage 'Systolic Accelerator SPEC is approved' `
        -ErrorMessage 'Systolic Accelerator SPEC is not approved'

    $sourceManifest = Get-Content -Raw -Encoding utf8 -LiteralPath `
        (Join-Path $manifestDirectory 'source_manifest.yaml')
    $accessPolicy = Get-Content -Raw -Encoding utf8 -LiteralPath `
        (Join-Path $manifestDirectory 'phase_access_policy.yaml')
    $baselineManifest = Get-Content -Raw -Encoding utf8 -LiteralPath `
        (Join-Path $manifestDirectory 'baseline_manifest.yaml')
    $indexManifest = Get-Content -Raw -Encoding utf8 -LiteralPath `
        (Join-Path $manifestDirectory 'index_manifest.yaml')

    Add-CheckResult ($sourceManifest -match '(?m)^expected_total_files:\s+247\s*$') `
        'source manifest expects 247 files' `
        'source manifest expected_total_files is not 247'
    Add-CheckResult ($accessPolicy -match '(?m)^default_action:\s+deny\s*$') `
        'phase access policy uses default deny' `
        'phase access policy is not default deny'
    Add-CheckResult ($accessPolicy -match 'historical_baselines/\*\*') `
        'prototype phase denies comparison-result paths' `
        'prototype phase does not deny comparison-result paths'
    Add-CheckResult ($baselineManifest -match '(?m)^\s+pass:\s+99\s*$' -and
                     $baselineManifest -match '(?m)^\s+fail:\s+1\s*$' -and
                     $baselineManifest -match '(?m)^\s+accuracy_percent:\s+99\.0\s*$') `
        'functional baseline is 99 PASS / 1 FAIL / 99.0 percent' `
        'functional baseline values do not match'
    $indexNotBuilt = $indexManifest -match '(?m)^status:\s+not_built\s*$'
    $indexBuilt = $indexManifest -match '(?m)^status:\s+built\s*$'
    Add-CheckResult `
        -Condition ($indexNotBuilt -or $indexBuilt) `
        -PassMessage 'index manifest has a recognized lifecycle status' `
        -ErrorMessage 'index manifest status must be not_built or built'
    if ($indexBuilt) {
        Add-CheckResult `
            -Condition ($indexManifest -match '(?m)^\s+chunk_count:\s+[1-9][0-9]*\s*$') `
            -PassMessage 'index manifest records a positive chunk count' `
            -ErrorMessage 'built index manifest does not record a positive chunk count'
        Add-CheckResult `
            -Condition ($indexManifest -match '(?ms)^\s+dense_index:\s*\r?\n\s+status:\s+built\s*$' -and
                        $indexManifest -match '(?m)^\s+embedding_dimension:\s+384\s*$') `
            -PassMessage 'dense index is built with dimension 384' `
            -ErrorMessage 'dense index build metadata is incomplete'
        Add-CheckResult `
            -Condition ($indexManifest -match '(?ms)^\s+sparse_index:\s*\r?\n\s+status:\s+built\s*$' -and
                        $indexManifest -match '(?m)^\s+engine:\s+sqlite_fts5\s*$') `
            -PassMessage 'SQLite FTS5 sparse index is built' `
            -ErrorMessage 'sparse index build metadata is incomplete'
        Add-CheckResult `
            -Condition ($indexManifest -match 'retrieval_smoke_test_passed') `
            -PassMessage 'retrieval smoke test gate is recorded' `
            -ErrorMessage 'retrieval smoke test gate is missing'
    }
}

foreach ($message in $passes) {
    Write-Output "PASS: $message"
}

if ($errors.Count -gt 0) {
    foreach ($message in $errors) {
        Write-Error "FAIL: $message"
    }
    exit 1
}

Write-Output "PASS: manifest validation completed with $($passes.Count) checks"
exit 0
