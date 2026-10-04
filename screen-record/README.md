# Nagranie demonstracji Accessly

`record.py` otwiera **prawdziwą przeglądarkę** (Chrome lub Edge, zwykłe okno), przeklikuje aplikację jak
użytkownik i **nagrywa ekran** karty do pliku MP4. Wszystko w bibliotece standardowej Pythona: bez Playwrighta,
Selenium, Node ani ffmpeg.

```
screen-record/
  record.py      uruchomienie: serwer aplikacji z czystą bazą, dane demo, Chrome, nagranie, pliki wynikowe
  scenario.py    kroki demonstracji (co po kolei, z podpisami PL/EN) i presety full / short
  actions.py     „ręka”: animowany kursor, klikanie, pisanie, przeciąganie mapy, wybór plików, podpisy
  cdp.py         minimalny klient Chrome DevTools Protocol (WebSocket) – uruchamia i steruje Chrome
  recorder.html  karta rejestratora: getDisplayMedia + MediaRecorder (MP4 H.264), sterowana przez CDP
  title.html     plansza tytułowa na początku filmu
  out/           nagrania (ignorowane przez git): out/<data_godzina>/accessly-demo.mp4 + chapters.json + captions.vtt + log.txt
```

## Uruchomienie

Wymagania: Python 3.8+ (`py -3` na Windows), Google Chrome lub Microsoft Edge, repozytorium aplikacji
(`Yannie-draft-acihy`) obok tego repozytorium (albo `--app-dir` / `--base`). Mapa, czcionki i Leaflet są
ładowane z sieci, więc do ładnego nagrania potrzebny jest internet.

```powershell
py -3 screen-record/record.py                       # pełna demonstracja wszystkich funkcji (ok. 10 min)
py -3 screen-record/record.py --preset short        # scenariusz 3-minutowy ze slajdu „Demo” (ok. 4 min)
py -3 screen-record/record.py --lang en             # interfejs i podpisy po angielsku (panele zostają po polsku)
py -3 screen-record/record.py --steps login,card    # wybrane kroki; --list-steps wypisuje listę
py -3 screen-record/record.py --speed 1.3           # szybsze tempo (pauzy krótsze o 30 %)
py -3 screen-record/record.py --no-ai               # asystent w trybie reguł (deterministyczny, bez klucza)
py -3 screen-record/record.py --base http://localhost:8000   # działająca instancja zamiast własnego serwera
py -3 screen-record/record.py --no-record --steps report     # tylko przeklikaj (test kroku), bez nagrywania
py -3 screen-record/record.py --size 1600x900 --video 1920x1080 # większy układ (viewport) przy tej samej rozdzielczości filmu
```

Pozostałe opcje: `--fps`, `--bitrate`, `--name` (nazwa pliku), `--out` (katalog), `--port`, `--position` (położenie okna),
`--chrome` (ścieżka do chrome.exe/msedge.exe), `--no-captions`, `--no-remux`, `--keep-open` (zostaw przeglądarkę
i serwer po nagraniu), `--capture screen` (cały ekran zamiast karty; eksperymentalne).

Skrypt sam uruchamia `accessly/server.py` na porcie 8765 z **czystą bazą** w katalogu nagrania
(`ACCESSLY_DB`), więc kolejka moderacji, powiadomienia i statusy wyglądają za każdym razem tak samo. Konta
demo (`anna@`, `piotr@`, `kasia@`, `admin@accessly.test`) tworzy serwer; logowanie działa bez poczty
(`ACCESSLY_DEV_LOGIN=1`). Klucze `ANTHROPIC_API_KEY` i `ACCESSLY_ORS_KEY` są czytane z `.env` w repozytorium
aplikacji; bez klucza AI asystent odpowiada regułami. Zgłoszenia barier są lokalne (`ACCESSLY_API_BASE` puste),
nie w backendzie Rampa.

Przed nagraniem skrypt zasiewa dane: pięć zgłoszeń barier na Kazimierzu i Stradomiu (przy prawdziwych
przystankach), opinię i potwierdzenie „bez schodów” Piotra w Kuchni u Doroty (dzięki temu „Aktualne” Anny daje
status „Potwierdzone przez społeczność” na ekranie) oraz syntetyczne zdjęcie wejścia (`zdjecie-wejscia.png`,
rysowane w Pythonie) do testu przesyłania zdjęć.

W trakcie nagrania nie ruszaj okna przeglądarki ani nie zamykaj karty „Rejestrator nagrania”. Nagrywana jest
tylko karta aplikacji (nie pulpit), więc reszta ekranu może być używana. Ctrl+C przerywa; plik z dotychczasowym
nagraniem zostaje.

## Co jest w scenariuszu (preset `full`)

Historia w czterech częściach, 35 kroków, podpisy nad mapą mówią, co się dzieje:

| Część | Kroki | Pokazane funkcje |
|---|---|---|
| Mieszkanka Anna (wózek) | start, login, profile, map, chip, layers, locate, search | ekran powitalny i polityka ciasteczek, logowanie kodem e-mail, profil potrzeb i preferencje z konta, mapa barier (kształt = waga), chipy potrzeb filtrujące mapę i warstwy, warstwy danych miasta i OSM z listą „Najbliżej na mapie”, lokalizacja, szukanie adresu (Nominatim) |
| | places_ai, card, reviews, favorite, near, camelot | katalog miejsc i asystent w języku naturalnym, karta miejsca (wartość, źródło, data, status), „Aktualne” → status społeczności, „Uzupełnij” brakujących danych i zmiana na „Spełnia wszystkie Twoje potrzeby”, opinie, ulubione, historia zmian, „Szukaj w pobliżu”, poprawka istniejącej informacji, pytanie do właściciela, zdjęcie do moderacji |
| | report, detail, list, newplace, help, theme_lang, sources, signout | zgłoszenie bariery w 3 krokach (pinezka, typ, waga, opis, podsumowanie), szczegóły z osią czasu i głosami, lista zgłoszeń i „Moje” z aktywnością, zgłoszenie nowego miejsca, pomoc medyczna (112, SOR, apteki), tryb nocny, 4 języki, strona „Źródła danych”, wylogowanie |
| Właścicielka Kasia | owner_login … owner_logout | panel właściciela: stan lokalu, akceptacja poprawki Anny, odpowiedź na pytanie, edycja atrybutów, „Potwierdź informacje”, udogodnienia na miejscu (edytor zbiorczy na mapie), zdjęcia, „Najczęściej wyszukiwane”, historia |
| Administrator | admin_login, admin_queue, admin_logout | panel administracyjny: wskaźniki, mapa aktywności, pokrycie kategorii, kolejka moderacji (uzupełnienia, nowe miejsce, zdjęcie), trend |
| Anna wraca | anna_back, camelot_after, outro | powiadomienia (odpowiedź, przyjęta poprawka), karta z danymi „Potwierdzone przez właściciela” i udogodnieniami na mapie, plansza końcowa |

Preset `short` to scenariusz ze slajdu 4 prezentacji: start, login, profile, places_ai, card, report, signout,
owner_login, owner_attrs, owner_logout, anna_back, camelot_after, outro.

## Pliki wynikowe

* `accessly-demo.mp4` – H.264 w MP4 (fragmentowany, jak zapisuje go Chrome), 1920×1080 z viewportu 1280×720
  (Chrome renderuje nagrywaną kartę w większej skali, więc tekst jest ostry), zmienna liczba klatek do 30/s.
  Jeśli `ffmpeg` jest w PATH, plik jest przepakowywany z `-movflags +faststart` (`--no-remux` wyłącza).
  Bez ffmpeg plik też się odtwarza (VLC, Chrome, Edge, odtwarzacz Windows) i wgrywa na YouTube.
* `chapters.json` – kroki i podpisy z czasem od początku filmu (do cięcia krótszej wersji w edytorze).
* `captions.vtt` – podpisy jako napisy WebVTT (można je wyłączyć na filmie przez `--no-captions`, a dodać z pliku).
* `log.txt`, `server.log`, `shots/blad-<krok>.png` – dziennik; zrzut ekranu dla kroku, który się nie udał.
  Nieudany krok nie przerywa nagrania: skrypt idzie dalej i wypisuje listę błędów na końcu (kod wyjścia 1).

## Jak to działa i na co uważać

* **Nagrywanie**: druga karta (`recorder.html`, osobne okno) woła `getDisplayMedia`; flaga Chrome
  `--auto-select-tab-capture-source-by-title=Accessly` wybiera kartę aplikacji bez okna dialogowego (tytuły
  wszystkich stron aplikacji zawierają „Accessly”). `MediaRecorder` koduje `video/mp4;codecs=avc1` (Chrome 126+;
  starsze dają WebM). Fragmenty są co 2 s zrzucane do pliku przez CDP, więc przerwane nagranie nie przepada.
* **Pasek „udostępniasz tę kartę”** zmniejsza okno, gdy zaczyna się przechwytywanie. Rozmiar klatki nie może się
  zmienić po starcie kodowania (strumień H.264 się psuje), dlatego kolejność to: plansza tytułowa → przechwycenie
  → dopasowanie okna do 1280×720 → start kodowania → aplikacja. Nie zmieniaj tej kolejności.
* **Sterowanie**: prawdziwe zdarzenia wejścia (`Input.dispatchMouseEvent`, `Input.insertText`), więc działają
  stany `:hover`, fokus i walidacja formularzy. Kursor na filmie to nakładka rysowana w stronie (prawdziwy kursor
  nie jest nagrywany przy przechwytywaniu karty). Listy `<select>` są ustawiane przez JS (natywnej listy nie da
  się nagrać), wybór pliku przez `Page.setInterceptFileChooserDialog` (bez okna systemowego).
* **Pozycja**: `Emulation.setGeolocationOverride` ustawia Plac Nowy na Kazimierzu, żeby „Moja lokalizacja”
  działała bez pytania o zgodę i bez GPS.
* **Sieć**: kafelki mapy, czcionki, Leaflet, Nominatim (szukanie adresu, nazwy miejsc zgłoszeń) i opcjonalnie
  asystent AI wymagają internetu. Krok `search` bez sieci jest pomijany z wpisem w logu.
* **Zmiany w aplikacji**: kroki opierają się na identyfikatorach i atrybutach `data-*` z `index.html`,
  `owner.html` i `admin.html`. Gdy coś się nie znajduje, w logu jest `nie doczekano się: element …` i zrzut
  ekranu; popraw selektor w `scenario.py`.
