<#
.SYNOPSIS
  Przycina i zmniejsza zrzuty ekranu do slajdów (JPEG), bez dodatkowych narzędzi (.NET System.Drawing).

.PARAMETER Source
  Katalog ze zrzutami z scripts/screenshots.py (PNG).
.PARAMETER Dest
  Katalog docelowy (domyślnie prezentacja/img).
.PARAMETER Logo
  Plik logo (PNG) kopiowany i zmniejszany do img/logo.png.

Przykład:
  powershell -File scripts/prepare-images.ps1 -Source C:\tmp\shots -Logo ..\Yannie-draft-acihy\assets\accessly_logo_main.png
#>
param(
  [Parameter(Mandatory = $true)][string]$Source,
  [string]$Dest = "",
  [string]$Logo = ""
)

# $PSScriptRoot is not available yet while parameter defaults are evaluated (PowerShell 5.1).
if (-not $Dest) { $Dest = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\prezentacja\img" }

Add-Type -AssemblyName System.Drawing
New-Item -ItemType Directory -Force $Dest | Out-Null

function Save-Jpeg([System.Drawing.Bitmap]$bmp, [string]$path, [int]$quality) {
  $codec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq "image/jpeg" }
  $params = New-Object System.Drawing.Imaging.EncoderParameters(1)
  $params.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter([System.Drawing.Imaging.Encoder]::Quality, [long]$quality)
  $bmp.Save($path, $codec, $params)
}

# Crop (x, y, w, h in source pixels; 0 = whole image) and scale to maxWidth, then save as JPEG or PNG.
function Convert-Shot([string]$name, [string]$out, [int]$x, [int]$y, [int]$w, [int]$h, [int]$maxWidth, [int]$quality = 88) {
  $src = Join-Path $Source $name
  if (-not (Test-Path $src)) { Write-Warning "brak $src"; return }
  $img = [System.Drawing.Image]::FromFile($src)
  if ($w -eq 0) { $w = $img.Width - $x }
  if ($h -eq 0) { $h = $img.Height - $y }
  $scale = [Math]::Min(1.0, $maxWidth / $w)
  $tw = [int][Math]::Round($w * $scale); $th = [int][Math]::Round($h * $scale)
  $bmp = New-Object System.Drawing.Bitmap($tw, $th)
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
  $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
  $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
  $g.Clear([System.Drawing.Color]::White)
  $srcRect = New-Object System.Drawing.Rectangle($x, $y, $w, $h)
  $dstRect = New-Object System.Drawing.Rectangle(0, 0, $tw, $th)
  $g.DrawImage($img, $dstRect, $srcRect, [System.Drawing.GraphicsUnit]::Pixel)
  $g.Dispose(); $img.Dispose()
  $path = Join-Path $Dest $out
  if ($out.EndsWith(".png")) { $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png) } else { Save-Jpeg $bmp $path $quality }
  $bmp.Dispose()
  "{0,-34} {1,5}x{2,-5} {3,6:N0} KB" -f $out, $tw, $th, ((Get-Item $path).Length / 1KB)
}

# Desktop shots are 2160x1350 (1440x900 CSS px at 1.5x); the side column is about 420 CSS px = 630 px wide.
Convert-Shot "01-mapa-desktop.png"           "mapa-desktop.jpg"        0 0 0 0 1600
Convert-Shot "04-asystent-desktop.png"       "asystent-panel.jpg"      0 0 640 1350 700
Convert-Shot "05-karta-miejsca-desktop.png"  "karta-panel.jpg"         0 0 640 1350 700
# Two strips from the place card: the needs summary box and one attribute row (value, source, date, status, buttons).
Convert-Shot "05-karta-miejsca-desktop.png"  "karta-dopasowanie.jpg"   15 705 600 200 900 92
Convert-Shot "05-karta-miejsca-desktop.png"  "karta-atrybut.jpg"       15 1030 600 240 900 92
Convert-Shot "07-zglos-krok1-desktop.png"    "zglos-krok1.jpg"         0 0 0 0 1600
Convert-Shot "11-admin-widok-desktop.png"    "admin-widok.jpg"         0 0 0 0 1600
Convert-Shot "12-mapa-noc-desktop.png"       "mapa-noc.jpg"            0 0 0 0 1600
Convert-Shot "13-mapa-mobile.png"            "mobile-mapa.jpg"         0 0 0 0 600
Convert-Shot "14-karta-mobile.png"           "mobile-karta.jpg"        0 0 0 0 600
Convert-Shot "16-panel-wlasciciela.png"      "panel-wlasciciela.jpg"   0 0 0 0 1600
Convert-Shot "18-panel-admina.png"           "panel-admina.jpg"        0 0 0 0 1600
Convert-Shot "19-zrodla-danych.png"          "zrodla-danych.jpg"       0 0 0 0 1200

if ($Logo -and (Test-Path $Logo)) {
  $img = [System.Drawing.Image]::FromFile($Logo)
  $bmp = New-Object System.Drawing.Bitmap(400, 400)
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
  $g.DrawImage($img, 0, 0, 400, 400)
  $g.Dispose(); $img.Dispose()
  $bmp.Save((Join-Path $Dest "logo.png"), [System.Drawing.Imaging.ImageFormat]::Png)
  $bmp.Dispose()
  "logo.png"
}
