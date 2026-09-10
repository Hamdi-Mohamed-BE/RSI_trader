[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Root = [IO.Path]::GetFullPath($PSScriptRoot).TrimEnd('\')
$ArchiveRoot = [IO.Path]::GetFullPath(
    (Join-Path $Root ('usless\archive-' + (Get-Date -Format 'yyyyMMdd-HHmmss')))
)

function Assert-ChildPath([string]$Path, [string]$Parent) {
    $full = [IO.Path]::GetFullPath($Path)
    $prefix = [IO.Path]::GetFullPath($Parent).TrimEnd('\') + '\'
    if (-not $full.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Unsafe path outside expected parent: $full"
    }
    return $full
}

function Get-RelativeChildPath([string]$Path, [string]$Parent) {
    $full = Assert-ChildPath $Path $Parent
    $prefix = [IO.Path]::GetFullPath($Parent).TrimEnd('\') + '\'
    return $full.Substring($prefix.Length)
}

function Move-ArchivedItem(
    [IO.FileSystemInfo]$Item,
    [string]$DestinationDirectory,
    [Collections.Generic.List[string]]$Manifest
) {
    $source = Assert-ChildPath $Item.FullName $Root
    $destinationDirectory = Assert-ChildPath $DestinationDirectory $ArchiveRoot
    [void](New-Item -ItemType Directory -Path $destinationDirectory -Force)
    $destination = Assert-ChildPath (
        Join-Path $destinationDirectory $Item.Name
    ) $ArchiveRoot
    Move-Item -LiteralPath $source -Destination $destination
    [void]$Manifest.Add(
        (Get-RelativeChildPath $source $Root) + ' -> ' +
        (Get-RelativeChildPath $destination $Root)
    )
}

$null = Assert-ChildPath $ArchiveRoot $Root
[void](New-Item -ItemType Directory -Path $ArchiveRoot -Force)
$manifest = [Collections.Generic.List[string]]::new()

$keepRootFiles = [Collections.Generic.HashSet[string]]::new(
    [StringComparer]::OrdinalIgnoreCase
)
@(
    '.env',
    '.env.example',
    '.gitignore',
    'app.py',
    'calendar_provider.py',
    'economic_context.py',
    'ea_file_bridge.py',
    'fomc_pipeline.py',
    'fxmacrodata.py',
    'gold_direction_rules.py',
    'news_core.py',
    'news_ensemble.py',
    'news_v4.py',
    'news_v5.py',
    'news_v8_move_range.py',
    'news_v9_direction.py',
    'official_nowcasts.py',
    'point_in_time_store.py',
    'predict_news.py',
    'release_intelligence.py',
    'mt5_installer_probe.py',
    'pyproject.toml',
    'uv.lock',
    'run.bat',
    'INSTALL_AND_RUN_GOLD_NEWS_V9.bat',
    'Install-GoldNewsV9EA.ps1',
    'Organize-RuntimePackage.ps1',
    'README.md',
    'MT5_V9_NEWS_EA_SPEC.md',
    'LAST_GOLD_NEWS_V9_INSTALL.txt'
) | ForEach-Object { [void]$keepRootFiles.Add($_) }

$keepRootDirectories = [Collections.Generic.HashSet[string]]::new(
    [StringComparer]::OrdinalIgnoreCase
)
@(
    '.git',
    '.venv',
    'data',
    'models',
    'mt5',
    'predictions',
    'release_analyses',
    'analyst_packets',
    'tmp',
    'usless'
) | ForEach-Object { [void]$keepRootDirectories.Add($_) }

$cacheDirectories = @('__pycache__', '.pytest_cache', 'node_modules')
$assetDirectories = @('charts', 'new pdfs')

foreach ($item in @(Get-ChildItem -LiteralPath $Root -Force)) {
    if ($item.PSIsContainer) {
        if ($keepRootDirectories.Contains($item.Name)) {
            continue
        }
        $category = if ($cacheDirectories -contains $item.Name) {
            'cache'
        } elseif ($assetDirectories -contains $item.Name) {
            'research-assets'
        } else {
            'research'
        }
        Move-ArchivedItem $item (Join-Path $ArchiveRoot $category) $manifest
    } elseif (-not $keepRootFiles.Contains($item.Name)) {
        Move-ArchivedItem $item (Join-Path $ArchiveRoot 'research') $manifest
    }
}

$modelsRoot = Join-Path $Root 'models'
$keepModels = @(
    'gold_news_v9_direction.joblib',
    'gold_news_v8_move_range.joblib'
)
foreach ($item in @(Get-ChildItem -LiteralPath $modelsRoot -Force)) {
    if ($keepModels -notcontains $item.Name) {
        Move-ArchivedItem $item (Join-Path $ArchiveRoot 'old-models') $manifest
    }
}

$dataRoot = Join-Path $Root 'data'
$keepData = @(
    'forex-factory-week.json',
    'official-nowcasts',
    'point-in-time',
    'economic-context'
)
foreach ($item in @(Get-ChildItem -LiteralPath $dataRoot -Force)) {
    if ($keepData -notcontains $item.Name) {
        Move-ArchivedItem $item (Join-Path $ArchiveRoot 'research-data') $manifest
    }
}

$tmpRoot = Join-Path $Root 'tmp'
if (Test-Path -LiteralPath $tmpRoot) {
    $keepLogs = @(
        'gold-news-v9-server.out.log',
        'gold-news-v9-server.err.log'
    )
    foreach ($item in @(Get-ChildItem -LiteralPath $tmpRoot -Force)) {
        if ($keepLogs -notcontains $item.Name) {
            Move-ArchivedItem $item (Join-Path $ArchiveRoot 'cache\tmp') $manifest
        }
    }
}

foreach ($outputDirectoryName in @(
    'predictions',
    'release_analyses',
    'analyst_packets'
)) {
    $outputDirectory = Join-Path $Root $outputDirectoryName
    if (-not (Test-Path -LiteralPath $outputDirectory)) {
        continue
    }
    foreach ($item in @(Get-ChildItem -LiteralPath $outputDirectory -Force)) {
        Move-ArchivedItem $item (
            Join-Path $ArchiveRoot ('runtime-history\' + $outputDirectoryName)
        ) $manifest
    }
}

$manifestPath = Join-Path $ArchiveRoot 'MOVED_ITEMS.txt'
$header = @(
    'Gold News V9 runtime cleanup'
    'Created: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')
    'Nothing was deleted. Every non-runtime item was moved into this archive.'
    ''
)
[IO.File]::WriteAllLines(
    $manifestPath,
    @($header + $manifest),
    [Text.UTF8Encoding]::new($true)
)

Write-Host ''
Write-Host "Runtime cleanup complete. Moved $($manifest.Count) items." -ForegroundColor Green
Write-Host "Archive: $ArchiveRoot"
Write-Host "Manifest: $manifestPath"
