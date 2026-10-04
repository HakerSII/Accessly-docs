# Ustawienia latexmk dla prezentacji (pdfLaTeX; pliki pomocnicze i PDF w build/).
$pdf_mode = 1;
$pdflatex = 'pdflatex -interaction=nonstopmode -halt-on-error -file-line-error -synctex=1 %O %S';
$xelatex  = 'xelatex -interaction=nonstopmode -halt-on-error -file-line-error -synctex=1 %O %S';
$out_dir = 'build';
$clean_ext = 'nav snm vrb synctex.gz';
