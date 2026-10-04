<#
.SYNOPSIS
  Buduje prezentację do PDF (Windows).

.EXAMPLE
  .\build.ps1            # polska wersja, lokalny latexmk (MiKTeX / TeX Live)
  .\build.ps1 -En        # wersja angielska (main-en.tex, slides-en\, img-en\)
  .\build.ps1 -Docker    # bez instalacji TeX-a: obraz texlive/texlive:latest-small
  .\build.ps1 -Notes     # wersja z notatkami prelegenta (build\main-notatki.pdf)
#>
param(
  [switch]$Docker,
  [switch]$Notes,
  [switch]$En
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)

$main = "main"; $out = "Accessly-Krakow-bez-barier.pdf"; $notesJob = "main-notatki"
if ($En) { $main = "main-en"; $out = "Accessly-Krakow-without-barriers.pdf"; $notesJob = "main-en-notes" }

if ($Notes) {
  $cmd = @("latexmk", "-pdf", "-jobname=$notesJob", "-usepretex=\def\shownotes{1}", "$main.tex")
} else {
  $cmd = @("latexmk", "-pdf", "$main.tex")
}

if ($Docker) {
  $dir = (Get-Location).Path
  & docker run --rm -v "${dir}:/work" -w /work texlive/texlive:latest-small @cmd
} else {
  & $cmd[0] $cmd[1..($cmd.Length - 1)]
}
if ($LASTEXITCODE -ne 0) { throw "latexmk zakończył się kodem $LASTEXITCODE" }

if ($Notes) {
  "gotowe: build\$notesJob.pdf"
} else {
  Copy-Item "build\$main.pdf" $out -Force
  "gotowe: $out"
}
