param(
    [switch]$Delete
)

$ErrorActionPreference = "Stop"

# Safety defaults:
# - Dry-run unless -Delete is explicitly provided
# - Never touch runtime-critical folders/files

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$excludeNames = @(
    "app.py",
    "database.py",
    "utils.py",
    "sds_translator_v4.py",
    "sds_parser.py",
    "sds_xml_importer.py",
    "sds_json_importer.py",
    "sds_json_parser.py",
    "sds_validator.py",
    "ghs_pictogram_manager.py",
    "odl_pdf_importer.py",
    "chandra_pdf_importer.py",
    "pdf_gap_filler.py",
    "SDS_PERFEKT_TEMPLATE.html",
    "mb_logo.svg",
    "requirements.txt"
)

$excludeDirs = @(
    "routes",
    "templates",
    "static",
    "uploads",
    "ghs",
    "symbole",
    "datalab_exports",
    "bibliothek",
    "chandra_cache"
)

$candidatePatterns = @(
    "debug_*.py",
    "test_*.py",
    "analyze_*.py",
    "check_*.py",
    "clean_*.py",
    "evaluate_*.py",
    "extract_*.py",
    "download_datalab_*.py",
    "export_*.py",
    "import_*_bulk.py",
    "tmp_*.py"
)

$candidateDirs = @(
    "__pycache__",
    ".ruff_cache",
    ".venv",
    "venv",
    "tmp_chandra",
    "node_modules"
)

$items = @()

foreach ($pattern in $candidatePatterns) {
    $items += Get-ChildItem -Path $root -Filter $pattern -File -ErrorAction SilentlyContinue
}

foreach ($dir in $candidateDirs) {
    $path = Join-Path $root $dir
    if (Test-Path $path) {
        $items += Get-Item $path
    }
}

# Add specific standalone optional files
$explicitFiles = @(
    "debug_out.txt",
    "package.json",
    "package-lock.json"
)
foreach ($f in $explicitFiles) {
    $path = Join-Path $root $f
    if (Test-Path $path) {
        $items += Get-Item $path
    }
}

$items = $items | Sort-Object FullName -Unique | Where-Object {
    $name = $_.Name
    $isExcludedName = $excludeNames -contains $name
    $isInExcludedDir = $false
    foreach ($d in $excludeDirs) {
        if ($_.FullName -like "*\$d\*") {
            $isInExcludedDir = $true
            break
        }
    }
    -not $isExcludedName -and -not $isInExcludedDir
}

if (-not $items -or $items.Count -eq 0) {
    Write-Host "No cleanup candidates found."
    exit 0
}

Write-Host "Cleanup candidates ($($items.Count)):"
$items | ForEach-Object { Write-Host " - $($_.FullName)" }

if (-not $Delete) {
    Write-Host ""
    Write-Host "Dry-run only. Re-run with -Delete to remove these items."
    exit 0
}

Write-Host ""
Write-Host "Deleting candidates..."
foreach ($item in $items) {
    if ($item.PSIsContainer) {
        Remove-Item -Path $item.FullName -Recurse -Force
    } else {
        Remove-Item -Path $item.FullName -Force
    }
    Write-Host "Deleted: $($item.FullName)"
}

Write-Host "Cleanup complete."
