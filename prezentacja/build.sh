#!/usr/bin/env bash
# Buduje prezentację do PDF.
#
#   ./build.sh            # lokalny latexmk (TeX Live / MiKTeX)
#   ./build.sh --docker   # bez instalacji TeX-a: obraz texlive/texlive:latest-small
#   ./build.sh --notes    # wersja z notatkami prelegenta (main-notatki.pdf)
#
# Wynik: build/main.pdf (kopiowany do Accessly-Krakow-bez-barier.pdf) oraz,
# z --notes, build/main-notatki.pdf.
set -euo pipefail
cd "$(dirname "$0")"

DOCKER=0
NOTES=0
for arg in "$@"; do
  case "$arg" in
    --docker) DOCKER=1 ;;
    --notes) NOTES=1 ;;
    *) echo "użycie: $0 [--docker] [--notes]" >&2; exit 2 ;;
  esac
done

if [ "$NOTES" = 1 ]; then
  CMD=(latexmk -pdf -jobname=main-notatki -usepretex='\def\shownotes{1}' main.tex)
else
  CMD=(latexmk -pdf main.tex)
fi

if [ "$DOCKER" = 1 ]; then
  # MSYS_NO_PATHCONV: w Git Bash na Windows ścieżki kontenera (/work) nie mogą być tłumaczone.
  HOST_DIR="$(pwd -W 2>/dev/null || pwd)"
  MSYS_NO_PATHCONV=1 docker run --rm -v "$HOST_DIR:/work" -w /work texlive/texlive:latest-small "${CMD[@]}"
else
  "${CMD[@]}"
fi

if [ "$NOTES" = 1 ]; then
  echo "gotowe: build/main-notatki.pdf"
else
  cp build/main.pdf Accessly-Krakow-bez-barier.pdf
  echo "gotowe: Accessly-Krakow-bez-barier.pdf"
fi
