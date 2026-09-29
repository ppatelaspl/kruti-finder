# Copy an installed Tesseract (UB-Mannheim build, via Chocolatey) into vendor\tesseract
# so it ships inside the app. Language models come from vendor\tessdata instead.
$ErrorActionPreference = "Stop"
$src = "C:\Program Files\Tesseract-OCR"
if (-not (Test-Path "$src\tesseract.exe")) { throw "Tesseract not found at $src" }
$dst = Join-Path $PSScriptRoot "..\..\vendor\tesseract"
if (Test-Path $dst) { Remove-Item $dst -Recurse -Force }
Copy-Item $src $dst -Recurse
Remove-Item (Join-Path $dst "tessdata") -Recurse -Force     # we bundle our own models
Get-ChildItem $dst -Filter "unins*" | Remove-Item -Force   # installer leftovers
& (Join-Path $dst "tesseract.exe") --version
