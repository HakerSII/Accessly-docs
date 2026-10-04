# Accessly – materiały na HackYeah 2026 („Kraków bez barier”)

Prezentacja projektu **Accessly** (max 10 slajdów PDF, wymóg regulaminu) w LaTeX-u (beamer), po polsku i po angielsku,
oraz skrypty, które robią zrzuty ekranu działającej aplikacji i przygotowują je do slajdów.
Kod aplikacji jest w osobnym repozytorium (`Yannie-draft-acihy`, katalog `accessly/`).

Prezentacja ma charakter biznesowy: problem jako koszt dla gościa, lokalu i miasta, rynek policzony na własnym katalogu,
cennik ze scenariuszem przychodów, wejście na rynek i regulacje, kamienie milowe z miernikami, zespół i prośba.
Wymogi formalne wyzwania (źródła danych, dostępność cyfrowa, hosting, bezpieczeństwo, demo) są zachowane w skondensowanej
formie, a szczegóły w notatkach prelegenta. Poprzednia, techniczna wersja slajdów leży w `prezentacja/archiwum/`.

```
Accessly-docs/
  README.md                    ten plik: plan prezentacji, mapowanie na kryteria, budowanie
  prezentacja/
    main.tex                   dokument główny, wersja polska (dane zespołu, adresy i wiersze zespołu do uzupełnienia na górze)
    main-en.tex                dokument główny, wersja angielska (te same makra do uzupełnienia)
    beamerthemeaccessly.sty    motyw: kolory z aplikacji (style.css), stopka „n / 10”, makra (\screenshot, \pill, \kpi, \muted)
    slides/01-tytul.tex … 10-zespol.tex        slajdy polskie, jeden slajd = jeden plik, z notatkami prelegenta (\note)
    slides-en/01-title.tex … 10-team.tex       slajdy angielskie (ta sama struktura i numeracja)
    archiwum/                  poprzednia wersja (techniczna) slajdów PL i EN, nie jest budowana
    img/                       zrzuty ekranu z polskim interfejsem (JPEG) i logo
    img-en/                    zrzuty z angielskim interfejsem (logo i wspólne pliki bierze z img/)
    build.sh / build.ps1       budowanie PDF (lokalny latexmk albo Docker); --en = wersja angielska, --notes = z notatkami
    .latexmkrc                 latexmk: pdfLaTeX, pliki pośrednie w build/
    Accessly-Krakow-bez-barier.pdf        gotowy PDF po polsku (kopia build/main.pdf)
    Accessly-Krakow-without-barriers.pdf  gotowy PDF po angielsku (kopia build/main-en.pdf)
  scripts/
    screenshots.py             zrzuty ekranu działającej aplikacji (headless Chrome, stdlib); --lang en dla interfejsu angielskiego
    prepare-images.ps1         przycięcie i zmniejszenie zrzutów do prezentacja/img/ lub img-en/ (.NET, bez instalacji)
```

## Budowanie PDF

Wymagane: beamer, babel (polish, english), tikz, booktabs, tabularx, lmodern (każda pełna dystrybucja: TeX Live, MiKTeX, Overleaf).

```bash
cd prezentacja
./build.sh                 # latexmk -pdf main.tex  →  Accessly-Krakow-bez-barier.pdf
./build.sh --en            # latexmk -pdf main-en.tex  →  Accessly-Krakow-without-barriers.pdf
./build.sh --docker        # bez TeX-a na komputerze: obraz texlive/texlive:latest-small (ok. 630 MB)
./build.sh --notes         # build/main-notatki.pdf: po każdym slajdzie strona z notatkami prelegenta (--en: build/main-en-notes.pdf)
```

Na Windows to samo robi `build.ps1` (`-En`, `-Docker`, `-Notes`). Overleaf: wgraj katalog `prezentacja/`,
kompilator pdfLaTeX, plik główny `main.tex` lub `main-en.tex`. XeLaTeX / LuaLaTeX też działają (`latexmk -xelatex`);
wtedy, jeśli w systemie jest czcionka Atkinson Hyperlegible (ta sama co w aplikacji), slajdy jej użyją.

## Do uzupełnienia i zweryfikowania przed wysłaniem

W `prezentacja/main.tex` (i odpowiednio `main-en.tex`) na górze:

| Makro | Co wpisać |
|---|---|
| `\TeamName` | nazwa zespołu |
| `\TeamId` | identyfikator zespołu z HackTribe |
| `\DemoUrl` | adres działającego demo (Docker/Ansible z repozytorium aplikacji) |
| `\RepoUrl` | repozytorium kodu |
| `\VideoUrl` | film (max 3 min, otwarte repozytorium, np. YouTube) |
| `\TeamRows` | imiona, nazwiska i role członków zespołu (slajd 10) |

Liczby i stwierdzenia, które trzeba potwierdzić (na slajdach oznaczone jako propozycja lub gwiazdką):

| Gdzie | Co | Źródło do sprawdzenia |
|---|---|---|
| slajd 2 | ok. 14 mln odwiedzających Kraków rocznie | badania ruchu turystycznego (Małopolska Organizacja Turystyczna) |
| slajd 2 | 5,4 mln osób z niepełnosprawnością w Polsce; co piąty mieszkaniec 65+ | GUS: NSP 2021, ludność według wieku |
| slajd 5 | porównanie z istniejącymi mapami (Wheelmap, Google Maps, bazy audytowe) | aktualne funkcje tych serwisów |
| slajd 6 | cennik (49 zł, 299 zł, 990 zł, 30–60 tys. zł) i scenariusze przychodów | rozmowy pilotażowe; rachunek w notatkach slajdu 6 |
| slajd 7 | ustawy: o zapewnianiu dostępności (2019), o dostępności cyfrowej (2019), Europejski Akt o Dostępności (od 2025) | pełne nazwy i daty w notatkach slajdu 7 |
| slajd 8 | koszt infrastruktury 60–120 zł/mies. | cenniki VPS |

Zgłoszenie w HackTribe wymaga też: tytułu projektu, ID zespołu, opisu projektu (po polsku), PDF (ten),
filmu mp4 (max 3 min). Opis projektu można wziąć z `docs/accessly_project_description.md`
w repozytorium aplikacji (skrócić do stanu faktycznego: co działa, co jest planem).

## Plan prezentacji i mapowanie na kryteria

Kryteria z „KRYTERIA Kraków Bez Barier.pdf” (pkt 8) i z regulaminu („RULES”, pkt 9).

| # | Slajd | Co pokazuje | Kryteria wyzwania | Kryteria regulaminu |
|---|---|---|---|---|
| 1 | Tytuł | nazwa, slogan, propozycja wartości (bezpłatne dla mieszkańców, płatne dla lokali i miast), zespół, linki | – | – |
| 2 | Kto dziś traci | koszt braku danych dla gościa, lokalu i miasta; rynek z katalogu (502 noclegi, 2 622 gastronomia, 1 117 zdrowie); popyt (dane zewnętrzne*); zakres prototypu | związek z wyzwaniem (25 %), model biznesowy (20 %) | Idea, Relation to category |
| 3 | Rozwiązanie jako usługa | co dostaje mieszkaniec (bezpłatnie), właściciel (plan Pro), miasto i partnerzy; „działa dziś” z liczbami | jakość prototypu (20 %), użyteczność (25 %) | Technical, WOW (asystent, 4 języki, profil „Po zabiegu”) |
| 4 | Demo | 5 kroków scenariusza Anny (profil → pytanie → karta → zgłoszenie → właściciel); przypadki brzegowe; oznaczenie danych przykładowych | pkt 6: działająca demonstracja, dane sprzeczne / niepełne / niedostępne | Idea, Design |
| 5 | Dlaczego nam zaufają | tabela porównawcza z istniejącymi mapami; model wiarygodności: 4 źródła, statusy, brak ≠ dostępne, historia, zachowanie bez sieci | wiarygodność i aktualizacja danych (15 %); pkt 5: źródło, data, status | Idea, Technical |
| 6 | Model biznesowy i cennik | segmenty z ofertą i ceną; scenariusz przychodów (ostrożny / bazowy / ambitny) z założeniami; zasada „płaci się za narzędzia, nie za status” | model biznesowy i komercjalizacja (20 %); pkt 9 | Idea |
| 7 | Wejście na rynek | pierwsi klienci (hotele, kliniki, kultura, wydarzenia), kanały, partner społeczny; regulacje jako popyt; skalowanie na kolejne miasta | potencjał wdrożeniowy i skalowanie (20 %); pkt 5: dodawanie miast | Design |
| 8 | Gotowe do wdrożenia | architektura w jednym rzędzie (pozyskiwanie danych oddzielone od prezentacji); technika; bezpieczeństwo i prywatność; dostępność cyfrowa jako przewaga; utrzymanie poza UMK | pkt 5: komponenty, hosting, ochrona danych, WCAG 2.2 AA | Design, Technical |
| 9 | Kamienie milowe i mierniki | oś czasu 30 dni / 3 / 6 / 12 miesięcy; tabela mierników (dziś → cel); warunki drugiego miasta | pkt 6: plan przejścia od prototypu do usługi | Design |
| 10 | Zespół i prośba | role w zespole; czego szukamy (pilotaż, partner społeczny, dane drugiego miasta, finansowanie); zdanie zamykające, linki | – | Idea |

Notatki prelegenta (`\note` w każdym pliku slajdu) zawierają scenariusz demo krok po kroku z minutnikiem, pełne nazwy
ustaw, rachunek stojący za scenariuszami przychodów, odpowiedzi na spodziewane pytania jury i to, czego nie obiecywać
(np. „zgodność z WCAG” → „sprawdzone kryteria”).

## Skąd są liczby na slajdach

Stan repozytorium aplikacji z 4 października 2026 (gałąź `main`, po scaleniu `feature/wcag`):

| Liczba | Źródło |
|---|---|
| 6 545 miejsc, 7 kategorii; 502 noclegi, 2 622 gastronomia, 1 117 zdrowie, 420 kultura | `accessly/data/places.json` (snapshot OSM z 2.10.2026); 1 495 miejsc (23 %) ma co najmniej jeden atrybut |
| 27 atrybutów, 8 profili potrzeb, 10 typów zgłoszeń | `places.ATTRIBUTES`, `places.NEED_PRESETS`, `server.TYPES` |
| 11 warstw, w tym 6 z otwartych danych miasta (3 756 przystanków, 50 toalet, 2 037 miejsc OzN, 2 633 tras, 3 157 stojaków, 199 obiektów infrastruktury rowerowej) i 5 z OSM (161 wind, 371 krawężników, 7 424 przejść, 10 przechowalni, 49 punktów pomocy) | `GET /api/layers` i snapshoty w `accessly/data/` |
| 503 testy | `py -3 -m unittest discover -s tests -t .` w `accessly/` (ok. 26 s; na Windows 4 testy zależne od `python3` i gniazd są znanymi wyjątkami) |
| statusy i terminy (2 potwierdzenia, 365 dni, 14 / 7 dni, 3 głosy „naprawione”) | `places.attribute_status`, `server.TTL`, `DEFAULT_TTL`, `CONFIRM_EXTENSION` |
| obraz Docker 47 MB | `docker images accessly` (rozmiar zawartości) |
| 3 124 lokali w scenariuszu przychodów | 502 noclegi + 2 622 gastronomia z katalogu; adopcja 2 / 5 / 10 % |

## Wersja angielska

`main-en.tex` + `slides-en/` to ta sama prezentacja po angielsku: te same 10 slajdów, liczby i notatki prelegenta,
zrzuty ekranu z aplikacją przełączoną na angielski (`img-en/`). Nazwy z interfejsu są cytowane tak, jak tłumaczy je
aplikacja (`i18n.js`, `i18n.py`): profile Wheelchair / Pram / Low vision / After treatment, przyciski Up to date /
Outdated / Correct / Add, statusy „Confirmed by the owner”, „From an official source”, „Needs re-checking”, „No data”.
Panel właściciela i administratora pozostają po polsku (tak działa aplikacja), co notatki slajdu 4 uwzględniają.
Zmiany treści warto wprowadzać w obu wersjach naraz; pliki slajdów mają tę samą numerację.

## Zrzuty ekranu

1. Uruchom aplikację (`scripts/run.sh` lub `scripts/docker-run.sh` w repozytorium aplikacji; domyślnie port 8000).
2. `py -3 scripts/screenshots.py --base http://localhost:8000 --out screenshots`
   – otwiera headless Chrome, ustawia profil „Wózek” i widok na Rynek, zapisuje 19 widoków
   (mapa, warstwy, Miejsca, asystent, karty miejsc, zgłoszenie, Zgłoszenia, Profil, widok admina,
   tryb nocny, 3 widoki mobilne, panel właściciela, panel administratora, „Źródła danych”
   oraz kartę miejsca z samymi potwierdzonymi udogodnieniami na slajd tytułowy: Kuchnia u Doroty,
   bez profilu potrzeb, z preferencjami, które to miejsce spełnia, więc ramka jest zielona).
   Z `--lang en --out screenshots-en` robi to samo z interfejsem po angielsku.
3. `powershell -File scripts/prepare-images.ps1 -Source screenshots -Logo <repo>/assets/accessly_logo_main.png`
   – przycina kolumnę boczną, zmniejsza do 1600 px i zapisuje JPEG do `prezentacja/img/`;
   dla wersji angielskiej `-Source screenshots-en -Dest prezentacja/img-en`.

Zrzuty w `prezentacja/img/` i `img-en/` pochodzą z kontenera `accessly` uruchomionego lokalnie 4 października 2026
(zgłoszenia barier z backendu Rampa, asystent w trybie reguł – bez klucza API).

## Demo na żywo (3 minuty) – skrót

Pełna wersja z minutnikiem w notatkach slajdu 4. Przed wejściem: aplikacja na telefonie i laptopie, profil „Wózek”,
mapa na Rynku Głównym, panel właścicielki otwarty w drugiej karcie.

1. Profil „Wózek” → lista „Najbliżej środka mapy” pokazuje tylko istotne bariery.
2. Miejsca → „Opisz, czego szukasz” → zapytanie z przykładu → ranking z uzasadnieniem i brakami.
3. Karta miejsca → atrybut ze źródłem, datą, statusem → „Brak danych” → „Uzupełnij” / pytanie do właściciela.
4. „Zgłoś problem” → pinezka, typ „Brak windy”, waga → zgłoszenie na mapie; głosy „nadal jest” / „naprawione”.
5. `/owner.html` jako `kasia@accessly.test` → „Potwierdź informacje” → w karcie status „Potwierdzone przez właściciela”.

Awaria sieci: wszystko poza kafelkami mapy działa z danych lokalnych; pokazać „Źródła danych” z datami snapshotów.
