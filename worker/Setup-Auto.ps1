# Windows x64 first-run bootstrap; no system Python or CUDA toolkit.
param([ValidateSet('review','cpu','cuda')][string]$Profile,[switch]$AcceptDownloads)
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
$root=[IO.Path]::GetFullPath($PSScriptRoot)
$sha='ebe90cc1dce2dd2d7afa1f0aa9b6c269c7c0174aeabdc6a801381602b7283424'
$size=48077770
$name='cpython-3.13.18+20261026-x86_64-pc-windows-msvc-install_only.tar.gz'
$url='https://github.com/astral-sh/python-build-standalone/releases/download/20261026/cpython-3.13.18%2B20261026-x86_64-pc-windows-msvc-install_only.tar.gz'
$tar=Join-Path $env:SystemRoot 'System32\tar.exe'
function Assert-Safe([string]$Path) {
    $full=[IO.Path]::GetFullPath($Path)
    if (-not ($full.Equals($root,[StringComparison]::OrdinalIgnoreCase) -or $full.StartsWith($root.TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase))) { throw 'Path outside VRS root.' }
    $cur=$full
    while ($cur) {
        if (Test-Path -LiteralPath $cur) {
            if ((Get-Item -LiteralPath $cur -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Reparse point refused: $cur" }
        }
        $parent=[IO.Path]::GetDirectoryName($cur)
        if ($parent -eq $cur) { break };$cur=$parent
    }
}
function Local-Dir([string]$Relative) {
    $p=Join-Path $root $Relative;Assert-Safe $p
    [void][IO.Directory]::CreateDirectory($p);Assert-Safe $p;return $p
}
function Assert-Archive([string]$Path) {
    Assert-Safe $Path
    if ((Get-Item -LiteralPath $Path).Length -ne $size -or (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $sha) { throw 'Pinned Python download integrity failure.' }
}
$guard=$null;$stage=$null;$createdBootstrap=$false;$part=$null
try {
    if (-not [Environment]::Is64BitOperatingSystem -or -not [Environment]::Is64BitProcess -or $env:PROCESSOR_ARCHITECTURE -ne 'AMD64' -or $root.StartsWith('\\')) { throw 'Local Windows x64 required.' }
    Assert-Safe $root
    if (-not (Test-Path -LiteralPath $tar -PathType Leaf)) { throw 'Windows tar.exe is required.' }
    $temp=Local-Dir 'temp';$env:TEMP=$temp;$env:TMP=$temp;$env:TMPDIR=$temp
    $env:HOME=Local-Dir 'data\home';$env:USERPROFILE=$env:HOME
    $env:APPDATA=Local-Dir 'config\appdata';$env:LOCALAPPDATA=Local-Dir 'data\localappdata'
    $env:PYTHONHOME=$null;$env:PYTHONPATH=$null;$env:PYTHONNOUSERSITE='1';$env:PYTHONDONTWRITEBYTECODE='1'
    $env:PIP_CONFIG_FILE='NUL';$env:PIP_NO_CACHE_DIR='1';$env:PIP_DISABLE_PIP_VERSION_CHECK='1';$env:PIP_NO_INPUT='1'
    $state=Local-Dir 'workspace';$lockFile=Join-Path $state 'auto-setup.lock';Assert-Safe $lockFile
    $guard=[IO.File]::Open($lockFile,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
    $manifest=Join-Path $root 'data\rc1\trial\run.json';Assert-Safe $manifest
    if (Test-Path -LiteralPath $manifest -PathType Leaf) {
        if ((Get-Item -LiteralPath $manifest).Length -gt 1048576) { throw 'Invalid trial manifest size.' }
        $backend=(Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json).backend
        if ($backend -notin @('cpu','cuda')) { throw 'Unsupported trial backend.' }
        if ($Profile -and $Profile -ne $backend) { throw 'Profile conflicts with prepared trial.' }
        $Profile=$backend
    }
    if (-not $Profile) {
        $Profile=(Read-Host 'Profil [review / cpu / cuda]').ToLowerInvariant()
        if ($Profile -notin @('review','cpu','cuda')) { throw 'Unknown profile.' }
    }
    $installed=Join-Path $root 'config\portable.json';Assert-Safe $installed
    if (Test-Path -LiteralPath $installed) {
        $old=Get-Content -LiteralPath $installed -Raw | ConvertFrom-Json
        if ($old.profile -ne $Profile -or $old.root -ne $root) { throw 'Existing installation: use Repair or separate folder.' }
        Write-Host 'VRS already installed. Use Start.bat or Repair.bat.';exit 0
    }
    $boot=Join-Path $root 'bootstrap';Assert-Safe $boot
    if (Test-Path -LiteralPath $boot) { throw 'Existing bootstrap: preserve it, use explicit setup or fresh folder.' }
    $plan=Join-Path $root "config\install-$Profile.json";Assert-Safe $plan
    if (Test-Path -LiteralPath $plan) { throw 'Existing install plan: preserve and inspect it.' }
    Write-Host "VRS first-run setup: $Profile"
    Write-Host 'Downloads: pinned portable Python 3.13.18, PyPI and PyTorch wheels. All VRS-managed files remain here.'
    if ($Profile -eq 'cuda') { Write-Host 'CUDA runtime via PyTorch cu128. Compatible NVIDIA driver required.' }
    if (-not $AcceptDownloads) {
        if ((Read-Host 'Download and install locally? [J/Y/N]') -notin @('j','y')) { exit 0 }
    }
    $assetDir=Local-Dir "cache\downloads\$sha";$archive=Join-Path $assetDir $name;Assert-Safe $archive
    if (-not (Test-Path -LiteralPath $archive)) {
        $part=$archive+'.part';Assert-Safe $part
        if (Test-Path -LiteralPath $part) { Remove-Item -LiteralPath $part -Force }
        [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $part -MaximumRedirection 5
        Assert-Archive $part;Move-Item -LiteralPath $part -Destination $archive;$part=$null
    }
    Assert-Archive $archive
    $members=@(& $tar -tzf $archive)
    if ($LASTEXITCODE -ne 0 -or $members.Count -lt 1 -or $members.Count -gt 100000) { throw 'Invalid Python archive.' }
    foreach ($member in $members) {
        if ($member -notmatch '^python(?:/|$)' -or $member -match '(^|/)\.\.(/|$)|[:\\]' -or $member.StartsWith('/')) { throw 'Unsafe Python archive path.' }
    }
    $stage=Local-Dir ('temp\python-'+[Guid]::NewGuid().ToString('N'))
    & $tar -xzf $archive -C $stage
    if ($LASTEXITCODE -ne 0) { throw 'Python extraction failed.' }
    $runtime=Join-Path $stage 'python';Assert-Safe $runtime
    foreach ($item in (Get-ChildItem -LiteralPath $runtime -Force -Recurse)) {
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Runtime link refused.' }
    }
    $python=Join-Path $runtime 'python.exe';Assert-Safe $python
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw 'Python executable missing.' }
    Move-Item -LiteralPath $runtime -Destination $boot;$createdBootstrap=$true
    $python=Join-Path $boot 'python.exe'
    & $python -E -s -B (Join-Path $root 'vrs_auto_setup.py') --root $root --profile $Profile
    if ($LASTEXITCODE -ne 0) { throw 'Local dependency setup failed. See console and local logs.' }
    Write-Host 'Setup completed. Start VRS with Start.bat.';exit 0
} catch {
    Write-Host ('VRS setup failed: '+$_.Exception.Message) -ForegroundColor Red
    if ($createdBootstrap -and -not (Test-Path -LiteralPath (Join-Path $root 'config\portable.json'))) {
        Remove-Item -LiteralPath (Join-Path $root 'bootstrap') -Recurse -Force -ErrorAction SilentlyContinue
    }
    exit 1
} finally {
    if ($part -and (Test-Path -LiteralPath $part)) { Remove-Item -LiteralPath $part -Force -ErrorAction SilentlyContinue }
    if ($stage -and (Test-Path -LiteralPath $stage)) { Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue }
    if ($guard) { $guard.Dispose() }
}
