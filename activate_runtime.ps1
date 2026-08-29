# Activate the recovered project's full-CPython venv and workspace-local media tools.
$projectRoot = $PSScriptRoot
$runtimeBin = Resolve-Path -LiteralPath (Join-Path $projectRoot '..\work\tools\python312_full\Library\bin')

. (Join-Path $projectRoot '.venv\Scripts\Activate.ps1')
$env:PATH = $runtimeBin.Path + [IO.Path]::PathSeparator + $env:PATH
