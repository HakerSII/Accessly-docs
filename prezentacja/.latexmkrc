# Ustawienia latexmk dla prezentacji (XeLaTeX: kroje Atkinson Hyperlegible z fonts/;
# pliki pomocnicze i PDF w build/). pdfLaTeX zapasowo: latexmk -pdf (Latin Modern).
$pdf_mode = 5;
$pdflatex = 'pdflatex -interaction=nonstopmode -halt-on-error -file-line-error -synctex=1 %O %S';
$xelatex  = 'xelatex -interaction=nonstopmode -halt-on-error -file-line-error -synctex=1 %O %S';
$out_dir = 'build';
$clean_ext = 'nav snm vrb synctex.gz';
