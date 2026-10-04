# Accessly – materiały na HackYeah 2026 („Kraków bez barier”)

Prezentacja projektu **Accessly** (max 10 slajdów PDF, wymóg regulaminu) w LaTeX-u (beamer)
oraz skrypty, które robią zrzuty ekranu działającej aplikacji i przygotowują je do slajdów.
Kod aplikacji jest w osobnym repozytorium (`Yannie-draft-acihy`, katalog `accessly/`).

```
Accessly-docs/
  README.md                    ten plik: plan prezentacji, mapowanie na kryteria, budowanie
  prezentacja/
    main.tex                   dokument główny (dane zespołu i adresy do uzupełnienia na górze)
    beamerthemeaccessly.sty    motyw: kolory z aplikacji (style.css), stopka „n / 10”, makra
    slides/01-tytul.tex … 10-plan.tex   jeden slajd = jeden plik, każdy z notatkami prelegenta (\note)
    img/                       zrzuty ekranu (JPEG) i logo
    build.sh / build.ps1       budowanie PDF (lokalny latexmk albo Docker), --notes = wersja z notatkami
    .latexmkrc                 latexmk: pdfLaTeX, pliki pośrednie w build/
    Accessly-Krakow-bez-barier.pdf   gotowy PDF (kopia build/main.pdf)
  scripts/
    screenshots.py             zrzuty ekranu działającej aplikacji (headless Chrome, stdlib)
    prepare-images.ps1         przycięcie i zmniejszenie zrzutów do prezentacja/img/ (.NET, bez instalacji)
```

## Budowanie PDF

Wymagane: beamer, babel-polish, tikz, booktabs, tabularx, lmodern (każda pełna dystrybucja: TeX Live, MiKTeX, Overleaf).

```bash
cd prezentacja
./build.sh                 # latexmk -pdf main.tex  →  Accessly-Krakow-bez-barier.pdf
./build.sh --docker        # bez TeX-a na komputerze: obraz texlive/texlive:latest-small (ok. 630 MB)
./build.sh --notes         # build/main-notatki.pdf: po każdym slajdzie strona z notatkami prelegenta
```

Na Windows to samo robi `build.ps1` (`-Docker`, `-Notes`). Overleaf: wgraj katalog `prezentacja/`,
kompilator pdfLaTeX, plik główny `main.tex`. XeLaTeX / LuaLaTeX też działają (`latexmk -xelatex`);
wtedy, jeśli w systemie jest czcionka Atkinson Hyperlegible (ta sama co w aplikacji), slajdy jej użyją.

## Do uzupełnienia przed wysłaniem

W `prezentacja/main.tex` na górze:

| Makro | Co wpisać |
|---|---|
| `\TeamName` | nazwa zespołu |
| `\TeamId` | identyfikator zespołu z HackTribe |
| `\DemoUrl` | adres działającego demo (Docker/Ansible z repozytorium aplikacji) |
| `\RepoUrl` | repozytorium kodu |
| `\VideoUrl` | film (max 3 min, otwarte repozytorium, np. YouTube) |

Zgłoszenie w HackTribe wymaga też: tytułu projektu, ID zespołu, opisu projektu (po polsku), PDF (ten),
filmu mp4 (max 3 min). Opis projektu można wziąć z `docs/accessly_project_description.md`
w repozytorium aplikacji (skrócić do stanu faktycznego: co działa, co jest planem).

## Plan prezentacji i mapowanie na kryteria

Kryteria z „KRYTERIA Kraków Bez Barier.pdf” (pkt 8) i z regulaminu („RULES”, pkt 9).

| # | Slajd | Co pokazuje | Kryteria wyzwania | Kryteria regulaminu |
|---|---|---|---|---|
| 1 | Tytuł | nazwa, slogan, zespół, linki (demo, kod, film), zrzut mobilny | – | – |
| 2 | „Dostępne / niedostępne” to za mało | problem, grupa docelowa (wózki, wózki dziecięce; pozostałe profile; właściciele), teza | związek z wyzwaniem i użyteczność (25 %) | Idea, Relation to category |
| 3 | Działający prototyp | katalog 6 545 miejsc, 27 atrybutów, profil potrzeb, karta, mapa barier, asystent, warstwy, panele, 4 języki | jakość i kompletność prototypu (20 %) | Technical, WOW (asystent, 4 języki, profil „Po zabiegu”) |
| 4 | Demo na scenie | 5 kroków scenariusza Anny (profil → pytanie → karta → zgłoszenie → właściciel); oznaczenie danych przykładowych | pkt 6: działająca demonstracja, oznaczenie danych przykładowych | Idea, Design |
| 5 | Dane | tabela źródeł (OSM, ArcGIS miasta, właściciel, społeczność): co, jak odświeżane, co gdy źródło milczy; statusy weryfikacji; zasady (brak ≠ dostępne) | wiarygodność i aktualizacja danych (15 %); pkt 5: źródło/data/status, pkt 6: dane sprzeczne, niepełne, niedostępne | Technical |
| 6 | Architektura | diagram: źródła → pozyskanie → SQLite → API → prezentacja; usługi opcjonalne; nowe miasto / źródło / kategoria | potencjał wdrożeniowy i skalowanie (20 %); pkt 5: komponenty, przepływ danych, dodawanie źródeł i miast | Design, Technical |
| 7 | Dostępność cyfrowa | co jest (klawiatura, czytnik, mapa jako tekst, kontrast, formularze), co do zrobienia | pkt 5–6: WCAG 2.2 AA, wykaz funkcji i braków | Design |
| 8 | Prywatność i utrzymanie | zakres danych, konto bez hasła, HTTPS; operator, koszty, aktualizacje, moderacja | pkt 5: ochrona danych, hosting poza UMK | Design |
| 9 | Model biznesowy | segmenty (mieszkańcy, właściciele, wydarzenia, miasta, API), oferta, przychód, zasady | model biznesowy i komercjalizacja (20 %); pkt 9 | Idea |
| 10 | Od prototypu do usługi | co jest dziś, plan 3–6 mies., warunki drugiego miasta, zdanie zamykające, linki | pkt 6: plan przejścia do usługi | – |

Notatki prelegenta (`\note` w każdym pliku slajdu) zawierają scenariusz demo krok po kroku, odpowiedzi na
spodziewane pytania jury i to, czego nie obiecywać (np. „zgodność z WCAG” → „sprawdzone kryteria”).

## Skąd są liczby na slajdach

Stan repozytorium aplikacji z 4 października 2026 (gałąź `main`, po scaleniu `feature/wcag`):

| Liczba | Źródło |
|---|---|
| 6 545 miejsc, 7 kategorii | `accessly/data/places.json` (snapshot OSM z 2.10.2026); 1 495 miejsc ma co najmniej jeden atrybut |
| 27 atrybutów, 8 profili potrzeb, 10 typów zgłoszeń | `places.ATTRIBUTES`, `places.NEED_PRESETS`, `server.TYPES` |
| 11 warstw i ich liczności (3 756 przystanków, 50 toalet, 2 037 miejsc OzN, 2 633 tras, 3 157 stojaków, 199 obiektów infrastruktury rowerowej, 161 wind, 371 krawężników, 7 424 przejść, 10 przechowalni, 49 punktów pomocy) | `GET /api/layers` i snapshoty w `accessly/data/` |
| 503 testy | `py -3 -m unittest discover -s tests -t .` w `accessly/` (ok. 26 s; na Windows 4 testy zależne od `python3` i gniazd są znanymi wyjątkami) |
| statusy i terminy (2 potwierdzenia, 365 dni, 14 / 7 dni, 3 głosy „naprawione”) | `places.attribute_status`, `server.TTL`, `DEFAULT_TTL`, `CONFIRM_EXTENSION` |
| obraz Docker 47 MB | `docker images accessly` (rozmiar zawartości) |
| koszty hostingu | szacunek na podstawie cenników VPS; na slajdzie oznaczone jako szacunek |

## Zrzuty ekranu

1. Uruchom aplikację (`scripts/run.sh` lub `scripts/docker-run.sh` w repozytorium aplikacji; domyślnie port 8000).
2. `py -3 scripts/screenshots.py --base http://localhost:8000 --out screenshots`
   – otwiera headless Chrome, ustawia profil „Wózek” i widok na Rynek, zapisuje 18 widoków
   (mapa, warstwy, Miejsca, asystent, karty miejsc, zgłoszenie, Zgłoszenia, Profil, widok admina,
   tryb nocny, 3 widoki mobilne, panel właściciela, panel administratora, „Źródła danych”).
3. `powershell -File scripts/prepare-images.ps1 -Source screenshots -Logo <repo>/assets/accessly_logo_main.png`
   – przycina kolumnę boczną, zmniejsza do 1600 px i zapisuje JPEG do `prezentacja/img/`.

Zrzuty w `prezentacja/img/` pochodzą z kontenera `accessly` uruchomionego lokalnie 4 października 2026
(zgłoszenia barier z backendu Rampa, asystent w trybie reguł – bez klucza API).

## Demo na żywo (3 minuty) – skrót

Pełna wersja w notatkach slajdu 4. Przed wejściem: aplikacja na telefonie i laptopie, profil „Wózek”,
mapa na Rynku Głównym.

1. Profil „Wózek” → lista „Najbliżej środka mapy” pokazuje tylko istotne bariery.
2. Miejsca → „Opisz, czego szukasz” → zapytanie z przykładu → ranking z uzasadnieniem i brakami.
3. Karta miejsca → atrybut ze źródłem, datą, statusem → „Brak danych” → „Uzupełnij” / pytanie do właściciela.
4. „Zgłoś problem” → pinezka, typ „Brak windy”, waga → zgłoszenie na mapie; głosy „nadal jest” / „naprawione”.
5. `/owner.html` jako `kasia@accessly.test` → „Potwierdź informacje” → w karcie status „Potwierdzone przez właściciela”.

Awaria sieci: wszystko poza kafelkami mapy działa z danych lokalnych; pokazać „Źródła danych” z datami snapshotów.
