$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
$logDir = Join-Path $HOME '.agents\komiai-install-logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir 'bootstrap-windows.log'
$exitCode = 1
$transcriptStarted = $false
$temporary = $null
try {
    Start-Transcript -Path $logFile -Append | Out-Null
    $transcriptStarted = $true
    Write-Host 'KomiAI 安装：首次需要联网下载 Python，请稍候。'
    $taskUv = Join-Path $HOME '.local\bin\uv.exe'
    if (-not (Test-Path -LiteralPath $taskUv)) {
        $temporary = Join-Path ([IO.Path]::GetTempPath()) ('komiai-' + [guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory -Path $temporary | Out-Null
        $installer = Join-Path $temporary 'install-uv.ps1'
        [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -UseBasicParsing -Uri 'https://astral.sh/uv/0.13.9/install.ps1' -OutFile $installer -TimeoutSec 180
        $env:UV_INSTALL_DIR = Join-Path $HOME '.local\bin'
        $env:UV_NO_MODIFY_PATH = '1'
        & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $installer
        if ($LASTEXITCODE -ne 0) { throw 'uv 安装失败。' }
        if (-not (Test-Path -LiteralPath $taskUv)) { throw '未找到安装后的 uv.exe。' }
    }
    & $taskUv --no-config python install 3.12
    if ($LASTEXITCODE -ne 0) { throw 'Python 下载或安装失败，请检查网络后重试。' }
    $found = & $taskUv --no-config python find --managed-python 3.12
    if ($LASTEXITCODE -ne 0) { throw '无法定位 Python 3.12。' }
    $taskPython = ($found | Out-String).Trim()
    if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Python 路径无效。' }
    & $taskPython (Join-Path $PSScriptRoot 'setup.py') --uv $taskUv
    $exitCode = $LASTEXITCODE
} catch {
    Write-Host ('安装未完成：' + $_.Exception.Message) -ForegroundColor Red
    Write-Host ('请将此日志发给管理员：' + $logFile)
} finally {
    if ($temporary -and (Test-Path -LiteralPath $temporary)) {
        Remove-Item -LiteralPath $temporary -Recurse -Force -ErrorAction SilentlyContinue
    }
    if ($transcriptStarted) { Stop-Transcript | Out-Null }
}
exit $exitCode
