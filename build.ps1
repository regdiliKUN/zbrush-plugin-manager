# 打包成单个 exe：.\build.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m PyInstaller --noconfirm --onefile --windowed `
  --name "ZBrush插件管理器" --icon "$PSScriptRoot\icon.ico" `
  --add-data "$PSScriptRoot\ui;ui" --add-data "$PSScriptRoot\icon.ico;." `
  --collect-submodules webview `
  --distpath "$PSScriptRoot\dist" --workpath "$PSScriptRoot\build" --specpath "$PSScriptRoot\build" `
  ZBrushPluginManager.py
Write-Host "完成：$PSScriptRoot\dist\ZBrush插件管理器.exe"
