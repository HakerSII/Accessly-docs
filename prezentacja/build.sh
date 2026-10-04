#!/usr/bin/env bash
# Buduje prezentację do PDF.
#
#   ./build.sh                 # polska wersja, lokalny latexmk (TeX Live / MiKTeX)
#   ./build.sh --en            # wersja angielska (main-en.tex, slides-en/, img-en/)
#   ./build.sh --docker        # bez instalacji TeX-a: obraz texlive/texlive:latest-small
#   ./build.sh --notes         # wersja z notatkami prelegenta (build/main-notatki.pdf)
#
# Wynik: build/main.pdf kopiowany do Accessly-Krakow-bez-barier.pdf
# (z --en: build/main-en.pdf -> Accessly-Krakow-without-barriers.pdf),
# a z --notes: build/main-notatki.pdf lub build/main-en-notes.pdf.
set -euo pipefail
cd "$(dirname "$0")"

DOCKER=0
NOTES=0
MAIN=main
OUT=Accessly-Krakow-bez-barier.pdf
NOTESJOB=main-notatki
for arg in "$@"; do
  case "$arg" in
    --docker) DOCKER=1 ;;
    --notes) NOTES=1 ;;
    --en) MAIN=main-en; OUT=Accessly-Krakow-without-barriers.pdf; NOTESJOB=main-en-notes ;;
    *) echo "użycie: $0 [--docker] [--notes] [--en]" >&2; exit 2 ;;
  esac
done

if [ "$NOTES" = 1 ]; then
  CMD=(latexmk -pdf -jobname="$NOTESJOB" -usepretex='\def\shownotes{1}' "$MAIN.tex")
else
  CMD=(latexmk -pdf "$MAIN.tex")
fi

if [ "$DOCKER" = 1 ]; then
  # MSYS_NO_PATHCONV: w Git Bash na Windows ścieżki kontenera (/work) nie mogą być tłumaczone.
  HOST_DIR="$(pwd -W 2>/dev/null || pwd)"
  MSYS_NO_PATHCONV=1 docker run --rm -v "$HOST_DIR:/work" -w /work texlive/texlive:latest-small "${CMD[@]}"
else
  "${CMD[@]}"
fi

if [ "$NOTES" = 1 ]; then
  echo "gotowe: build/$NOTESJOB.pdf"
else
  cp "build/$MAIN.pdf" "$OUT"
  echo "gotowe: $OUT"
fi
