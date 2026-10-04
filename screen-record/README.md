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
py -3 screen-record/record.py                       # cała historia, do 3 minut (limit filmu w zgłoszeniu)
py -3 screen-record/record.py --preset short        # scenariusz ze slajdu „Demo”, ok. 2 minuty
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

## Co jest w scenariuszu (preset `full`, do 3 minut)

Jedna historia w czterech częściach, 17 kroków; podpisy nad mapą mówią, co się dzieje. Podpisy są krótkie,
a pauzy minimalne, bo limit filmu w zgłoszeniu to 3 minuty. Dłuższe wątki (opinie, ulubione, „Szukaj w pobliżu”,
lista zgłoszeń, nowe miejsce, pomoc medyczna, tryb nocny i języki, strona „Źródła danych”, zdjęcia, pytania do
właściciela) celowo zostały poza scenariuszem; można je dopisać jako kolejne kroki w `scenario.py`.

| Część | Kroki | Pokazane funkcje |
|---|---|---|
| Mieszkanka Anna (wózek) | start, profile, map, places_ai, card, chat, camelot, report, signout | ekran powitalny, logowanie kodem e-mail, profil z konta i preferencje, mapa barier (kształt = waga) i warstwy danych miasta/OSM, asystent w języku naturalnym, karta miejsca (wartość, źródło, data, status), „Aktualne” → status społeczności, „Uzupełnij” → „Spełnia wszystkie Twoje potrzeby”, czat z asystentem na wdrożonej instancji (`/chat`: model na serwerze Rampa, narzędzia MCP), poprawka istniejącej informacji, zgłoszenie awarii windy w 3 krokach (pinezka, typ, waga, opis, podsumowanie) |
| Właścicielka Kasia | owner, owner_features, owner_logout | panel właściciela: stan lokalu, akceptacja poprawki Anny, „Potwierdź informacje”, udogodnienie na miejscu dodane kliknięciem w mapę |
| Administrator | admin, admin_logout | panel administracyjny: wskaźniki, kolejka moderacji (przyjęcie uzupełnienia), trend |
| Anna wraca | anna_back, camelot_after, outro | powiadomienie o przyjętej poprawce, karta „Potwierdzone przez właściciela” z udogodnieniami na mapie, plansza końcowa |

Preset `short` to scenariusz ze slajdu 4 prezentacji (ok. 2 minuty): start, profile, places_ai, card, report,
signout, owner, owner_logout, anna_back, camelot_after, outro.

Krok `chat` przechodzi na chwilę na **wdrożoną instancję** (`--chat-url`, domyślnie
`https://yannie-draft-acihy.onrender.com/chat`), bo lokalny `main` nie ma strony `/chat` (jest na gałęzi
`adjust_to_backend`, która rozmawia z asystentem na serwerze Rampa). Skrypt budzi tę instancję w tle już podczas
zasiewania danych (Render usypia darmowe usługi). Gdy asystent nie jest gotowy albo nie odpowie w `--chat-wait`
sekund (domyślnie 25), krok pokazuje stronę i wraca; `--no-chat` pomija go.

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
* **Sieć**: kafelki mapy, czcionki, Leaflet, Nominatim (nazwy miejsc zgłoszeń), instancja Render (krok `chat`)
  i opcjonalnie asystent AI wymagają internetu. Bez sieci krok `chat` wraca po limicie czasu z wpisem w logu.
* **Nie klikaj paska „udostępniasz tę kartę”** w Chrome ani nie zamykaj karty rejestratora: przycisk „Zatrzymaj”
  kończy przechwytywanie, a film urywa się w tym miejscu (log: „rejestrator zgłosił błąd: udostępnianie zatrzymane”).
* **Zmiany w aplikacji**: kroki opierają się na identyfikatorach i atrybutach `data-*` z `index.html`,
  `owner.html` i `admin.html`. Gdy coś się nie znajduje, w logu jest `nie doczekano się: element …` i zrzut
  ekranu; popraw selektor w `scenario.py`.
