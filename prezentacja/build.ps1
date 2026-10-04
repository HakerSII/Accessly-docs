<#
.SYNOPSIS
  Buduje prezentację do PDF (Windows).

.EXAMPLE
  .\build.ps1            # lokalny latexmk (MiKTeX / TeX Live)
  .\build.ps1 -Docker    # bez instalacji TeX-a: obraz texlive/texlive:latest-small
  .\build.ps1 -Notes     # wersja z notatkami prelegenta (build\main-notatki.pdf)
#>
param(
  [switch]$Docker,
  [switch]$Notes
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)

if ($Notes) {
  $cmd = @("latexmk", "-pdf", "-jobname=main-notatki", "-usepretex=\def\shownotes{1}", "main.tex")
} else {
  $cmd = @("latexmk", "-pdf", "main.tex")
}

if ($Docker) {
  $dir = (Get-Location).Path
  & docker run --rm -v "${dir}:/work" -w /work texlive/texlive:latest-small @cmd
} else {
  & $cmd[0] $cmd[1..($cmd.Length - 1)]
}
if ($LASTEXITCODE -ne 0) { throw "latexmk zakończył się kodem $LASTEXITCODE" }

if ($Notes) {
  "gotowe: build\main-notatki.pdf"
} else {
  Copy-Item build\main.pdf Accessly-Krakow-bez-barier.pdf -Force
  "gotowe: Accessly-Krakow-bez-barier.pdf"
}
