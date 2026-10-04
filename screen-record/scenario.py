"""Scenariusz demonstracji Accessly: kolejne kroki klikane w prawdziwej przeglądarce.

Każdy krok to funkcja ``step_<id>(d, ctx)`` zarejestrowana w ``STEPS`` z osobą
(mieszkanka Anna, właścicielka Kasia, administrator) i tytułem rozdziału.
``d`` to ``actions.Demo`` (kursor, podpisy, klikanie), ``ctx`` to słownik
z danymi uruchomienia (adres aplikacji, identyfikatory miejsc, zasiane
zgłoszenia, plik zdjęcia, język). Podpisy mają wersję polską i angielską;
``record.py`` wybiera ``--preset full`` (wszystkie funkcje) albo ``short``
(scenariusz 3-minutowy ze slajdu „Demo”).

Historia: Anna (wózek) ustawia profil, pyta asystenta, otwiera kartę
restauracji, która spełnia jej potrzeby, potwierdza i uzupełnia informacje,
proponuje poprawkę w Camelot Cafe, pyta właścicielkę, zgłasza awarię windy
na przystanku Stradom. Kasia w panelu właściciela przyjmuje poprawkę,
odpowiada, potwierdza dane i dodaje udogodnienia. Administrator moderuje
resztę kolejki. Anna wraca: powiadomienia i karta z danymi potwierdzonymi
przez właściciela.
"""

import json
import re

from actions import StepError

# Przystanek Stradom 02 (dane miasta): tu Anna zgłasza awarię windy.
STRADOM = (50.052163, 19.940972)
# Plac Nowy na Kazimierzu: pozycja „GPS” Anny (Emulation.setGeolocationOverride).
GEO = (50.0518, 19.9447)
# Widok startowy mapy: Kazimierz ze Stradomiem.
VIEW = (50.0520, 19.9435)

AI_QUERY = {
    "pl": "Restauracja na Kazimierzu bez schodów, z dostępną toaletą i parkingiem",
    "en": "A restaurant in Kazimierz without steps, with an accessible toilet and parking",
}

PERSONAS = {
    "anna": ("Mieszkanka Anna · wózek", "Resident Anna · wheelchair"),
    "kasia": ("Właścicielka Kasia · Camelot Cafe", "Owner Kasia · Camelot Cafe"),
    "admin": ("Administrator", "Administrator"),
    "": ("", ""),
}


def persona(d, key):
    """Etykieta osoby nad podpisem, w języku nagrania."""
    pl, en = PERSONAS[key]
    return en if d.lang != "pl" else pl


# ---------- pomocnicze ----------


def sign_in_app(d, email):
    """Zaloguj się w aplikacji głównej (ekran logowania; kod jest weryfikowany automatycznie)."""
    d.wait_visible("#loginEmail")
    d.fill("#loginEmail", email)
    d.click({"sel": "#loginEmailForm button"})
    d.wait_for(f"typeof me !== 'undefined' && me && me.email === {json.dumps(email)}", timeout=20, desc="zalogowanie")
    d.sleep(1.2)


def sign_in_panel(d, email, email_sel, email_form, code_hint, code_sel, code_form, done):
    """Logowanie w panelu właściciela / administratora: e-mail, kod z podpowiedzi trybu deweloperskiego, zaloguj."""
    d.fill(email_sel, email)
    d.click({"sel": f"{email_form} button"})
    d.wait_visible(code_form)
    code = d.wait_for(
        f"(() => {{ const m = ((document.querySelector({json.dumps(code_hint)}) || {{}}).textContent || '').match(/\\d{{6}}/); return m && m[0]; }})()",
        timeout=10, desc="kod logowania (ACCESSLY_DEV_LOGIN musi być włączone)")
    d.sleep(0.8)
    d.fill(code_sel, code)
    d.click({"sel": f"{code_form} button[type=submit]"})
    d.wait_visible(done, timeout=20)
    d.sleep(1.0)


def go_tab(d, name):
    """Kliknij zakładkę paska dolnego; na desktopie otwarty widok pełnoekranowy (karta, szczegóły) zakrywa pasek, więc najpierw go zamknij."""
    for _ in range(3):
        back = d.js("(() => { const v = document.querySelector('.view.full:not([hidden])'); if (!v) return null;"
                    " const b = v.querySelector('.appbar .iconbtn'); return b && b.id ? '#' + b.id : null; })()")
        if not back:
            break
        d.click(back, pause=0.4)
    d.click(f".tab[data-tab={name}]")


def logout_api(d):
    """Zakończ sesję przez API (gdy poprzednia osoba została zalogowana), bez klikania."""
    d.js("fetch('/api/auth/logout', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}'}).then(r => r.status)", wait=True)


def fly(d, lat, lng, zoom, wait=1.8):
    """Przesuń mapę aplikacji głównej w widoczny obszar (flyToVisible z app.js)."""
    d.js(f"flyToVisible([{lat}, {lng}], {zoom})")
    d.sleep(wait)


def open_place_from_catalogue(d, query, place_id):
    """Zakładka Miejsca: wyszukaj w katalogu i otwórz kartę miejsca."""
    go_tab(d, "places")
    d.wait_visible("#placeQuery")
    d.fill("#placeQuery", query)
    d.key("Enter")
    d.wait_visible(f'#placesList [data-place="{place_id}"]', timeout=15)
    d.sleep(0.6)
    d.click(f'#placesList [data-place="{place_id}"]')
    d.wait_visible("#placeBody .matchbox", timeout=15)
    d.sleep(0.8)


def propose(d, key, value, note, expect_toast=True):
    """Na karcie miejsca: „Popraw” / „Uzupełnij” atrybut, wybierz wartość, dopisz szczegół, wyślij."""
    d.click(f"[data-edit={key}]")
    form = f"form[data-propose={key}]"
    d.wait_visible(form)
    d.select_value(f"{form} select", value)
    if note:
        d.fill(f"{form} input[name=note]", note)
    d.click({"sel": f"{form} button.pri"})
    if expect_toast:
        d.wait_toast()
    d.sleep(1.0)


# ---------- część 1: Anna ----------


def step_start(d, ctx):
    """Ekran powitalny."""
    d.step("start", persona(d, ""))
    d.goto("/", "document.querySelector('#loginBody .login-form')")
    d.caption("Accessly: sprawdzone informacje o dostępności miejsc w Krakowie i mapa barier zgłaszanych przez mieszkańców.",
              "Accessly: verified accessibility information about places in Kraków and a map of barriers reported by residents.",
              hold=3.5)
    d.hover(".login-perks", pause=0.8)
    d.caption("Konto nie jest wymagane: zgłaszać bariery i przeglądać mapę można bez logowania.",
              "No account is needed: you can report barriers and browse the map without signing in.", hold=2.5)
    if d.exists("#cookieOk"):
        d.caption("Tylko niezbędne ciasteczko sesji i pamięć przeglądarki na ustawienia. Bez reklam i śledzenia.",
                  "Only the essential session cookie and browser storage for settings. No ads, no tracking.")
        d.hover("#cookieNote p", pause=1.5)
        d.click("#cookieOk", pause=0.8)


def step_login(d, ctx):
    """Logowanie bez hasła."""
    d.step("login", persona(d, "anna"))
    d.caption("Logowanie bez hasła: jednorazowy kod na e-mail. Konto demo anna@accessly.test.",
              "Password-less sign-in: a one-time code by e-mail. Demo account anna@accessly.test.")
    sign_in_app(d, "anna@accessly.test")
    d.caption("Profil Anny (potrzeba „Wózek”) przyszedł z konta: zaznaczone chipy i warstwa wind.",
              "Anna's profile (the “Wheelchair” need) came from her account: selected chips and the elevators layer.", hold=2.5)


def step_profile(d, ctx):
    """Profil: potrzeby i preferencje."""
    d.step("profile", persona(d, "anna"))
    go_tab(d, "profile")
    d.wait_visible("#prefList input")
    d.caption("Profil: potrzeby i preferencje zapisane na koncie. Zapisujemy potrzeby, nigdy informacje o zdrowiu.",
              "Profile: needs and preferences saved to the account. We store needs, never health information.", hold=2)
    d.hover("#accountTitle", pause=0.6)
    d.hover("#profileNeeds", pause=0.6)
    d.caption("Preferencje: bez schodów, dostępna toaleta, parking dla osób z niepełnosprawnościami.",
              "Preferences: step-free, accessible toilet, disabled parking.")
    d.click('label:has(input[data-pref="step_free"])', pause=0.4)
    d.click('label:has(input[data-pref="accessible_toilet"])', pause=0.4)
    if d.js("(document.querySelector('input[data-pref=elevator]') || {}).checked"):
        d.click('label:has(input[data-pref="elevator"])', pause=0.4)
    d.sleep(1.5)


def step_map(d, ctx):
    """Mapa barier i znaczniki."""
    d.step("map", persona(d, "anna"))
    go_tab(d, "map")
    fly(d, *VIEW, 16)
    d.caption("Mapa barier: zgłoszenia mieszkańców przefiltrowane przez profil. Kwadrat blokuje przejazd, koło to utrudnienie.",
              "Barrier map: residents' reports filtered by the profile. A square blocks the way, a circle is an obstacle.", hold=2.5)
    r = ctx["reports"][0]
    fly(d, r["lat"], r["lng"], 17)
    x, y = d.map_point(r["lat"], r["lng"])
    d.click_at(x, y, pause=1.2)
    d.wait_visible("#sheetBody [data-open]")
    d.caption("Kliknięty znacznik pokazuje zgłoszenie w panelu: typ, miejsce, kiedy, ile potwierdzeń.",
              "A clicked marker shows the report in the panel: type, place, when, how many confirmations.")
    d.hover("#sheetBody .issue", pause=1.5)


def step_chip(d, ctx):
    """Chip potrzeb filtruje mapę i włącza warstwy."""
    d.step("chip", persona(d, "anna"))
    d.caption("Chipy potrzeb w pasku filtrują mapę i włączają warstwy: „Senior” dodaje toalety i przystanki.",
              "The need chips filter the map and switch layers on: “Senior” adds toilets and stops.")
    d.click('#needChips [data-need="senior"]', pause=0.5)
    d.wait_toast()
    d.sleep(2.8)
    d.click('#needChips [data-need="senior"]', pause=0.5)
    d.sleep(1.5)


def step_layers(d, ctx):
    """Panel warstw danych publicznych."""
    d.step("layers", persona(d, "anna"))
    d.click("#layersBtn")
    d.wait_visible("#layerList input")
    d.caption("Warstwy z otwartych danych miasta i OpenStreetMap: toalety, parking OzN, przystanki z rodzajem krawężnika, windy, przejścia.",
              "Layers from the city's open data and OpenStreetMap: toilets, disabled parking, stops with kerb type, elevators, crossings.")
    d.click('label:has(input[data-layer="parking"])', pause=0.6)
    d.click('label:has(input[data-layer="stops"])', pause=1.2)
    d.hover("#layerNearbyTitle", pause=0.5)
    d.caption("„Najbliżej na mapie” to tekstowa alternatywa warstw: lista obiektów z odległością (WCAG 1.1.1).",
              "“Nearest on the map” is the text alternative to the layers: a list of items with distances (WCAG 1.1.1).", hold=1.5)
    if d.exists("#layerNearbyList [data-nearby]"):
        d.click("#layerNearbyList [data-nearby]", pause=2.2)
    else:
        d.click("#layersClose")
    d.sleep(0.8)


def step_locate(d, ctx):
    """Moja lokalizacja."""
    d.step("locate", persona(d, "anna"))
    d.caption("„Moja lokalizacja” (tu pozycja demonstracyjna na Kazimierzu): odległości liczą się od Anny.",
              "“My location” (a demo position in Kazimierz here): distances are measured from Anna.")
    d.click("#locateBtn", pause=2.5)
    d.sleep(1.0)


def step_search(d, ctx):
    """Szukanie adresu (Nominatim)."""
    d.step("search", persona(d, "anna"))
    d.caption("Szukanie przystanku lub adresu (OpenStreetMap Nominatim).",
              "Searching for a stop or an address (OpenStreetMap Nominatim).")
    d.fill("#searchInput", "Stradom")
    d.key("Enter")
    try:
        d.wait_visible("#searchResults button[data-lat]", timeout=8)
        d.click("#searchResults button[data-lat]", pause=2.5)
    except StepError:
        d.log("Nominatim nie odpowiedział (brak sieci?) – pomijam wybór wyniku")
        d.key("Escape")
        fly(d, *STRADOM, 17)


def step_places_ai(d, ctx):
    """Zakładka Miejsca i asystent."""
    d.step("places_ai", persona(d, "anna"))
    go_tab(d, "places")
    d.wait_visible("#categoryChips .chip")
    mode = "Asystent AI (Claude) z narzędziem przeszukiwania bazy" if ctx["ai"] == "ai" else "dopasowanie po słowach kluczowych"
    mode_en = "an AI assistant (Claude) with a database search tool" if ctx["ai"] == "ai" else "keyword matching"
    d.caption(f"Miejsca: katalog 6,5 tys. miejsc z OpenStreetMap i pytanie w języku naturalnym ({mode}).",
              f"Places: a catalogue of 6,500 places from OpenStreetMap and a question in natural language ({mode_en}).", hold=1.5)
    d.click("#aiInput", pause=0.2)
    d.type_text(AI_QUERY["en" if d.lang != "pl" else "pl"])
    d.sleep(0.5)
    d.click("#aiSubmit")
    d.wait_visible("#aiAnswerTitle", timeout=90)
    d.sleep(1.0)
    d.caption("Rekomendacje opierają się wyłącznie na danych Accessly: fakty pochodzą z serwera, nie z modelu. Braki są oznaczone „?”.",
              "Recommendations rely only on Accessly data: the facts come from the server, never from the model. Gaps are marked “?”.")
    d.hover("#aiResult .items", pause=2.5)
    target = f'#aiResult [data-place="{ctx["ids"]["doroty"]}"]'
    if not d.exists(target):
        target = "#aiResult .items [data-place]"
    d.click(target)
    d.wait_visible("#placeBody .matchbox", timeout=15)
    d.sleep(1.0)


def step_card(d, ctx):
    """Karta miejsca: źródło, data, status; Aktualne; Uzupełnij."""
    d.step("card", persona(d, "anna"))
    d.caption("Karta miejsca: każdy fakt ma wartość, źródło, datę i status weryfikacji.",
              "Place card: every fact has a value, a source, a date and a verification status.")
    d.hover(".matchbox", pause=1.5)
    d.hover(".attrs li.attr .attr-meta", pause=2.0)
    d.caption("„Aktualne” potwierdza informację. Dwa potwierdzenia dają status „Potwierdzone przez społeczność”.",
              "“Up to date” confirms the information. Two confirmations give the status “Confirmed by the community”.")
    d.click('[data-vote="confirm"][data-key="step_free"]')
    d.wait_toast()
    d.sleep(2.2)
    if d.exists("[data-edit=door_width]"):
        d.caption("Brak informacji nigdy nie znaczy „dostępne”: karta mówi wprost, czego nie wiadomo. Anna zna szerokość drzwi i ją uzupełnia.",
                  "Missing information never means “accessible”: the card says what is unknown. Anna knows the door width and fills it in.")
        propose(d, "door_width", "yes", "Drzwi ok. 95 cm, otwierane na zewnątrz" if d.lang == "pl" else "Door about 95 cm, opens outwards")
        d.js("document.getElementById('view-place').scrollTo({top: 0, behavior: 'smooth'})")
        d.sleep(1.0)
        d.caption("Uzupełnienie jest widoczne od razu jako niezweryfikowane, a karta zmienia się na „Spełnia wszystkie Twoje potrzeby”.",
                  "The addition shows at once as unverified, and the card changes to “Meets all your needs”.")
        d.hover(".matchbox", pause=3.0)


def step_reviews(d, ctx):
    """Opinie."""
    d.step("reviews", persona(d, "anna"))
    d.click("[data-psec=reviews]")
    d.wait_visible("#reviewForm")
    d.caption("Opinie o dostępności, nie o kuchni: co warto wiedzieć przed wizytą.",
              "Reviews about accessibility, not the food: what to know before a visit.")
    d.click('#reviewForm label.star:has(input[value="5"])', pause=0.4)
    d.fill("#reviewText", "Wjechałam bez pomocy, obsługa od razu zaproponowała stolik przy wejściu." if d.lang == "pl"
           else "I rolled in without help; the staff offered a table by the entrance at once.")
    d.click({"sel": "#reviewForm button.pri"})
    d.wait_toast()
    d.sleep(1.2)
    d.hover(".reviews li", pause=1.5)


def step_favorite(d, ctx):
    """Zapisane miejsca i historia zmian."""
    d.step("favorite", persona(d, "anna"))
    d.click("#placeFav")
    d.wait_toast()
    d.caption("Zapisane miejsca są w Profilu na każdym urządzeniu. „Historia zmian” pokazuje, kto i kiedy zmienił każdą informację.",
              "Saved places are in the Profile on every device. “Change history” shows who changed each fact and when.")
    d.click("#historyFold summary")
    d.wait_visible("#historyList li", timeout=10)
    d.hover("#historyList", pause=2.5)


def step_near(d, ctx):
    """Szukaj w pobliżu (turystyka medyczna)."""
    d.step("near", persona(d, "anna"))
    d.click("#placeNear")
    d.wait_visible("#anchorBar:not([hidden])")
    d.caption("„Szukaj w pobliżu”: nocleg, apteka czy restauracja w promieniu 1,5 km od wybranego miejsca, np. kliniki.",
              "“Search nearby”: accommodation, a pharmacy or a restaurant within 1.5 km of a chosen place, e.g. a clinic.")
    d.click('[data-cat="zdrowie"]', pause=1.5)
    d.wait_visible("#placesList li")
    d.hover("#placesSub", pause=2.0)
    d.click('[data-cat=""]', pause=0.6)
    d.click("#anchorClear", pause=0.8)


def step_camelot(d, ctx):
    """Camelot Cafe: poprawka, uzupełnienie, pytanie, zdjęcie."""
    d.step("camelot", persona(d, "anna"))
    open_place_from_catalogue(d, "Camelot", ctx["ids"]["camelot"])
    d.caption("Camelot Cafe: według OpenStreetMap „bez schodów: nie”. Anna wie, że jest podjazd, więc proponuje poprawkę.",
              "Camelot Cafe: according to OpenStreetMap “step-free: no”. Anna knows there is a ramp, so she proposes a correction.")
    d.hover('[data-vote="confirm"][data-key="step_free"]', pause=1.0)
    propose(d, "step_free", "yes", "Jest przenośny podjazd, wystarczy poprosić obsługę" if d.lang == "pl" else "There is a portable ramp, just ask the staff")
    d.caption("Zmiana istniejącej informacji czeka na akceptację właścicielki albo moderatora. Brakującą informację można dodać od razu.",
              "A change to existing information waits for the owner or a moderator. Missing information can be added at once.")
    propose(d, "accessible_toilet", "yes", "")
    d.click("[data-psec=questions]")
    d.wait_visible("#questionForm")
    d.caption("Pytanie do właścicielki: odpowiedź przyjdzie w powiadomieniach, a lokal widzi, czego ludzie szukają.",
              "A question to the owner: the answer arrives in notifications, and the venue sees what people look for.")
    d.select_value("#questionTopic", "changing_table")
    d.fill("#questionText", "Czy jest przewijak dla niemowląt?" if d.lang == "pl" else "Is there a baby changing table?")
    d.click({"sel": "#questionForm button.pri"})
    d.wait_toast()
    d.sleep(1.2)
    d.caption("Zdjęcia użytkowników przechodzą moderację, zanim pojawią się na karcie.",
              "Users' photos are moderated before they appear on the card.")
    d.choose_file("label.file-btn", ctx["photo"])
    d.wait_toast(timeout=15)
    d.sleep(1.5)


def step_report(d, ctx):
    """Zgłoszenie bariery w 3 krokach."""
    d.step("report", persona(d, "anna"))
    go_tab(d, "map")
    fly(d, STRADOM[0], STRADOM[1], 17)
    d.caption("Zgłoszenie bariery w trzech krokach, także bez konta. Krok 1: pinezka stoi, mapa przesuwa się pod nią.",
              "Reporting a barrier in three steps, also without an account. Step 1: the pin stays still, the map moves under it.")
    d.click("#addBtn")
    d.wait_visible("#placebar:not([hidden])")
    d.sleep(0.8)
    cx, cy = d.map_center_point()
    d.drag(cx + 120, cy + 90, cx + 40, cy + 50, duration=1.0)
    d.sleep(0.4)
    px, py = d.map_point(*STRADOM)
    pin = d.js("(() => { const c = document.getElementById('crosshair').getBoundingClientRect(); const m = map.getContainer().getBoundingClientRect(); return [c.left + c.width / 2, c.top + c.height]; })()")
    # Dosuń przystanek pod czubek pinezki.
    d.drag(px, py, pin[0], pin[1] - 2, duration=0.9)
    d.click("#placeNextBtn")
    d.wait_visible("#view-report:not([hidden])")
    d.caption("Krok 2: rodzaj problemu i waga. Nazwa miejsca: przystanek z danych miasta albo adres z OpenStreetMap.",
              "Step 2: the kind of problem and its severity. The place name: a stop from city data or an address from OpenStreetMap.")
    try:
        d.wait_for("!/Ustalam|Finding|Suche|Визнача/.test(document.getElementById('placeName').textContent)", timeout=8, desc="nazwa miejsca")
    except StepError:
        d.log("nazwa miejsca nie ustaliła się w 8 s (Nominatim?) – idę dalej")
    d.hover("#placeName", pause=1.0)
    d.click('label.cat:has(input[value="elevator_broken"])', pause=0.6)
    d.click('label.radio:has(input[value="block"])', pause=0.6)
    d.fill("#description", "Winda na peron nie działa od rana, na drzwiach kartka o awarii." if d.lang == "pl"
           else "The lift to the platform has been out of order since morning; a note on the door says so.")
    d.click("#nextBtn")
    d.wait_visible("#step3:not([hidden])")
    d.caption("Krok 3: podsumowanie i wysłanie. Awaria windy wygasa po 14 dniach, chyba że ktoś ją potwierdzi.",
              "Step 3: summary and send. A broken lift expires after 14 days unless somebody confirms it.", hold=2.0)
    d.click("#nextBtn")
    d.wait_toast(timeout=15)
    d.wait_visible("#sheetBody [data-open]")
    d.caption("Zgłoszenie jest na mapie od razu: kwadrat, bo blokuje przejazd.",
              "The report is on the map at once: a square, because it blocks the way.", hold=2.5)


def step_detail(d, ctx):
    """Szczegóły zgłoszenia i głosy."""
    d.step("detail", persona(d, "anna"))
    d.click("#sheetBody [data-open]")
    d.wait_visible("#detailBody .timeline")
    d.caption("Szczegóły: oś czasu zgłoszone → potwierdzone → naprawione, odległość i windy w pobliżu jako obejście.",
              "Details: a timeline reported → confirmed → fixed, distance, and nearby elevators as a way around.")
    d.hover("#detailBody .timeline", pause=2.5)
    d.click("#detailBack")
    r = ctx["reports"][1]
    fly(d, r["lat"], r["lng"], 17)
    x, y = d.map_point(r["lat"], r["lng"])
    d.click_at(x, y, pause=1.0)
    d.wait_visible("#sheetBody [data-open]")
    d.click("#sheetBody [data-open]")
    d.wait_visible('#detailBody [data-vote="up"]')
    d.caption("Inni głosują „nadal jest” albo „już naprawione”; trzy głosy „naprawione” zamykają zgłoszenie, które znika z mapy po dobie.",
              "Others vote “still there” or “fixed”; three “fixed” votes close the report, which leaves the map after a day.")
    d.click('#detailBody [data-vote="up"]')
    d.wait_toast()
    d.sleep(2.0)
    d.click("#detailBack")


def step_list(d, ctx):
    """Zgłoszenia jako lista i „Moje”."""
    d.step("list", persona(d, "anna"))
    go_tab(d, "list")
    d.wait_visible("#list li")
    d.caption("Zgłoszenia jako tekst: alternatywa mapy dla czytników ekranu, najbliższe pierwsze.",
              "Reports as text: the map's alternative for screen readers, nearest first.", hold=2.0)
    d.click("#view-list [data-segment=mine]")
    d.wait_visible("#view-mine:not([hidden])")
    d.wait_visible("#activity .items", timeout=10)
    d.caption("„Moje”: własne zgłoszenia oraz statusy poprawek i pytań ze wszystkich urządzeń.",
              "“Mine”: own reports plus the statuses of corrections and questions from every device.")
    d.hover("#activity .items", pause=2.5)


def step_newplace(d, ctx):
    """Zgłoszenie nowego miejsca."""
    d.step("newplace", persona(d, "anna"))
    go_tab(d, "places")
    d.wait_visible("#addPlaceBtn")
    d.click("#addPlaceBtn")
    d.wait_visible("#view-newplace:not([hidden])")
    d.caption("Brakujące miejsce można zgłosić z atrybutami dostępności; pojawi się po sprawdzeniu przez moderatora.",
              "A missing place can be suggested with accessibility attributes; it appears after a moderator checks it.")
    d.fill("#npName", "Kawiarnia Bez Barier" if d.lang == "pl" else "Barrier-Free Café")
    d.select_value("#npCategory", "gastronomia")
    d.fill("#npAddress", "ul. Józefa 12")
    d.select_value("[data-np-attr=step_free]", "yes")
    d.select_value("[data-np-attr=accessible_toilet]", "yes")
    d.fill("#npNote", "Nowy lokal, otwarty we wrześniu." if d.lang == "pl" else "A new venue, opened in September.")
    d.click("#npSubmit")
    d.wait_toast()
    d.sleep(1.5)


def step_help(d, ctx):
    """Pomoc medyczna."""
    d.step("help", persona(d, "anna"))
    d.click("#helpBtn")
    d.wait_visible("#helpEr li", timeout=15)
    d.caption("Pomoc medyczna: 112, najbliższe SOR-y i apteki całodobowe. Dla gości po zabiegu jest też profil „Po zabiegu”.",
              "Medical help: 112, the nearest emergency departments and 24-hour pharmacies. Guests after treatment also have the “After treatment” profile.")
    d.hover("#helpEr", pause=2.5)
    d.hover("#help24", pause=1.5)
    d.click("#helpBack")


def step_theme_lang(d, ctx):
    """Tryb nocny i języki."""
    d.step("theme_lang", persona(d, "anna"))
    d.click("#themeBtn")
    d.caption("Tryb nocny; kontrasty kolorów sprawdzane testami według WCAG 2.2 AA.",
              "Night mode; colour contrasts are checked by tests against WCAG 2.2 AA.", hold=3.0)
    d.click("#themeBtn", pause=1.0)
    other = "en" if d.lang == "pl" else "pl"
    d.click("#langBtn")
    d.wait_visible("#langMenu:not([hidden])")
    d.caption("Interfejs po polsku, angielsku, niemiecku i ukraińsku; etykiety i odpowiedzi asystenta też w wybranym języku.",
              "The interface in Polish, English, German and Ukrainian; labels and the assistant's answers in that language too.")
    d.click(f'#langMenu [data-lang="{other}"]')
    d.reload_wait("document.querySelector('#needChips .chip')")
    d.hover("#needChips", pause=1.0)
    go_tab(d, "places")
    d.wait_visible("#categoryChips .chip")
    d.sleep(2.5)
    d.click("#langBtn")
    d.wait_visible("#langMenu:not([hidden])")
    d.click(f'#langMenu [data-lang="{d.lang}"]')
    d.reload_wait("document.querySelector('#needChips .chip')")
    d.sleep(0.8)


def step_sources(d, ctx):
    """Strona „Źródła danych”."""
    d.step("sources", persona(d, "anna"))
    go_tab(d, "profile")
    d.wait_visible('.foot a[href="sources.html"]')
    d.caption("Strony informacyjne: o aplikacji, źródła danych, licencje, polityka prywatności.",
              "Information pages: about, data sources, licences, privacy policy.")
    d.click('.foot a[href="sources.html"]')
    d.wait_ready("document.querySelector('main, body')")
    d.wait_for("document.querySelectorAll('li, tr, article').length > 3", timeout=15, desc="lista warstw")
    d.caption("Źródła danych z datami snapshotów: Gmina Miejska Kraków (otwartedane.um.krakow.pl) i OpenStreetMap.",
              "Data sources with snapshot dates: the City of Kraków (otwartedane.um.krakow.pl) and OpenStreetMap.")
    d.js("window.scrollTo({top: 500, behavior: 'smooth'})")
    d.sleep(3.0)
    d.goto("/", "document.querySelector('#needChips .chip')")


def step_signout(d, ctx):
    """Wylogowanie Anny."""
    d.step("signout", persona(d, "anna"))
    go_tab(d, "profile")
    d.wait_visible("#signOutBtn")
    d.click("#signOutBtn")
    d.wait_visible("#view-login:not([hidden])")
    d.caption("Teraz druga strona: panel właścicielki lokalu.", "Now the other side: the venue owner's panel.", hold=2.0)


# ---------- część 2: Kasia ----------


def step_owner_login(d, ctx):
    """Panel właściciela: logowanie."""
    d.step("owner_login", persona(d, "kasia"))
    logout_api(d)
    d.goto("/owner.html", "document.getElementById('signinView') && !document.getElementById('signinView').hidden")
    d.caption("Panel właściciela obiektu (owner.html): kasia@accessly.test zarządza Camelot Cafe.",
              "The venue owner panel (owner.html): kasia@accessly.test manages Camelot Cafe.")
    sign_in_panel(d, "kasia@accessly.test", "#emailInput", "#emailForm", "#codeHint", "#codeInput", "#codeForm", "#panelView:not([hidden])")
    d.wait_visible("#attrList li")
    d.caption("Na górze stan lokalu: ile informacji uzupełniono, co wymaga sprawdzenia, otwarte pytania i propozycje.",
              "At the top the venue's state: how much is filled in, what needs checking, open questions and proposals.")
    d.hover("#stats", pause=2.5)


def step_owner_subs(d, ctx):
    """Propozycje zmian od użytkowników."""
    d.step("owner_subs", persona(d, "kasia"))
    d.hover("#subsTitle", pause=0.8)
    if not d.exists(".sub-form"):
        d.caption("Propozycje zmian od użytkowników trafiają tutaj; dziś nie ma nic do rozpatrzenia.",
                  "Users' change proposals arrive here; nothing to review today.", hold=2.0)
        return
    d.caption("Propozycja Anny: „bez schodów: nie → tak”. Właścicielka akceptuje; wartość dostaje status „Potwierdzone przez właściciela”.",
              "Anna's proposal: “step-free: no → yes”. The owner accepts; the value gets the status “Confirmed by the owner”.")
    d.hover(".sub-form", pause=1.2)
    d.fill(".sub-form input", "Dziękujemy! Podjazd mamy od maja.")
    d.click('.sub-form button[value="accept"]')
    d.wait_toast()
    d.sleep(1.5)


def step_owner_question(d, ctx):
    """Odpowiedź na pytanie."""
    d.step("owner_question", persona(d, "kasia"))
    d.hover("#qTitle", pause=0.8)
    d.wait_visible(".answer-form textarea", timeout=10)
    d.caption("Pytania i potrzeby od użytkowników: odpowiedź trafia do pytającego, a lokal deklaruje, czy udogodnienie jest albo będzie.",
              "Questions and needs from users: the answer goes to the asker, and the venue declares whether the facility exists or is planned.")
    d.fill(".answer-form textarea", "Tak, przewijak jest w toalecie na parterze.")
    d.click(".answer-form .plan .seg label", pause=0.5)
    d.click({"sel": ".answer-form button[type=submit]"})
    d.wait_toast()
    d.sleep(1.5)


def step_owner_attrs(d, ctx):
    """Edycja atrybutów i „Potwierdź informacje”."""
    d.step("owner_attrs", persona(d, "kasia"))
    d.hover("#attrsTitle", pause=0.6)
    d.click("#attrEditBtn")
    d.wait_visible("#attrList li.editing")
    d.caption("Właściciel ustawia wartości bezpośrednio: tak / nie / nie dotyczy, z uwagą, np. „drzwi 85 cm”.",
              "The owner sets values directly: yes / no / not applicable, with a note, e.g. “door 85 cm”.")
    d.click('label:has(input[name="v-changing_table"][value="yes"])', pause=0.5)
    d.fill("#n-changing_table", "W toalecie na parterze")
    d.click('label:has(input[name="v-dogs"][value="yes"])', pause=0.5)
    d.click("#attrSaveBtn")
    d.wait_toast()
    d.sleep(1.5)
    d.caption("„Potwierdź informacje” oznacza wszystkie dane jako aktualne; po roku bez potwierdzenia status wróciłby do „Wymaga ponownej weryfikacji”.",
              "“Confirm information” marks every fact as up to date; after a year without confirmation the status would return to “Needs re-checking”.")
    d.click("#confirmBtn")
    d.wait_toast()
    d.sleep(2.0)
    d.hover("#attrList li .attr-meta", pause=1.5)


def step_owner_features(d, ctx):
    """Udogodnienia na miejscu: edytor zbiorczy."""
    d.step("owner_features", persona(d, "kasia"))
    d.hover("#featTitle", pause=0.6)
    d.click("#batchBtn")
    d.wait_visible("#batchEditor:not([hidden])")
    d.wait_for("typeof batch !== 'undefined' && !!batch.map", timeout=10, desc="mapa edytora")
    d.sleep(1.0)
    d.caption("Udogodnienia na miejscu jako punkty: windy, podjazdy, toalety. Dodaje się je klikając mapę, wierszami albo wklejając arkusz.",
              "On-site facilities as points: elevators, ramps, toilets. Added by clicking the map, by rows, or by pasting a spreadsheet.")
    d.select_value("#batchKind", "ramp")
    d.hover("#batchMap", pause=0.4)  # mapa ma 380 px wysokości: musi być w całości w viewportcie, zanim policzymy punkty
    cx, cy = d.map_center_point("batch.map")
    d.click_at(cx + 34, cy - 30, pause=0.8)
    d.wait_visible("#batchRows li[data-uid]")
    d.select_value("#batchKind", "toilet")
    d.hover("#batchMap", pause=0.2)
    cx, cy = d.map_center_point("batch.map")
    d.click_at(cx - 46, cy - 10, pause=0.8)
    d.wait_for("document.querySelectorAll('#batchRows li[data-uid]').length >= 2", timeout=5, desc="drugi wiersz")
    d.fill("#batchRows li[data-uid]:nth-child(1) [data-f=name]", "Podjazd przy wejściu głównym")
    d.fill("#batchRows li[data-uid]:nth-child(2) [data-f=name]", "Toaleta dostępna, parter")
    d.fill("#batchRows li[data-uid]:nth-child(2) [data-f=level]", "0")
    d.click("#batchSaveBtn")
    d.wait_toast()
    d.sleep(1.2)
    d.hover("#featList", pause=2.0)


def step_owner_photo(d, ctx):
    """Zdjęcia, historia i statystyki."""
    d.step("owner_photo", persona(d, "kasia"))
    d.hover("#photosTitle", pause=0.6)
    d.caption("Zdjęcia właściciela publikowane są od razu; zdjęcia użytkowników czekają na akceptację.",
              "The owner's photos are published at once; users' photos wait for approval.")
    d.choose_file("#photoBtn", ctx["photo"])
    d.wait_for("document.querySelectorAll('#photoGrid img').length >= 1", timeout=20, desc="zdjęcie w galerii")
    d.sleep(1.5)
    d.hover("#interestTitle", pause=0.6)
    d.caption("„Najczęściej wyszukiwane” mówi, czego goście szukają w tym lokalu, a „Historia zmian” kto i kiedy zmienił dane.",
              "“Most searched” tells what guests look for at this venue, and “Change history” who changed the data and when.")
    d.hover("#interestList", pause=2.0)
    d.hover("#historyList", pause=2.0)


def step_owner_logout(d, ctx):
    """Wylogowanie Kasi."""
    d.step("owner_logout", persona(d, "kasia"))
    d.js("window.scrollTo({top: 0, behavior: 'smooth'})")
    d.sleep(0.8)
    d.click("#logoutBtn")
    d.wait_visible("#signinView:not([hidden])")
    d.sleep(0.8)


# ---------- część 3: administrator ----------


def step_admin_login(d, ctx):
    """Panel administracyjny: logowanie i wskaźniki."""
    d.step("admin_login", persona(d, "admin"))
    logout_api(d)
    d.goto("/admin", "document.getElementById('signin') && (!document.getElementById('signin').hidden || !document.getElementById('dash').hidden)")
    d.caption("Panel administracyjny (/admin): wskaźniki, mapa aktywności, pokrycie kategorii i kolejka moderacji.",
              "The admin panel (/admin): indicators, an activity map, category coverage and the moderation queue.")
    sign_in_panel(d, "admin@accessly.test", "#loginEmail", "#emailForm", "#devCode", "#loginCode", "#codeForm", "#dash:not([hidden])")
    d.wait_visible("#kpis li", timeout=20)
    d.hover("#kpis", pause=2.5)
    d.hover("#coverage", pause=1.5)


def step_admin_queue(d, ctx):
    """Kolejka moderacji."""
    d.step("admin_queue", persona(d, "admin"))
    d.hover("#queueTitle", pause=0.6)
    d.caption("Kolejka: uzupełnienia, poprawki, zdjęcia, nowe miejsca, przejęcia lokali i wnioski o konto właściciela.",
              "The queue: additions, corrections, photos, new places, venue claims and owner-account requests.")
    for group, note in (("missing", "Dziękujemy za uzupełnienie."), ("new_place", "Dodane do katalogu."), ("photo", "")):
        d.click(f'#queueTabs [data-group="{group}"]', pause=0.8)
        if not d.exists("#queuePanel .qitem"):
            continue
        d.hover("#queuePanel .qitem h3", pause=1.0)
        if note:
            d.fill("#queuePanel .qitem input", note)
        d.click('#queuePanel .qitem [data-decision="accept"]')
        d.sleep(1.8)
    d.caption("Każda decyzja ma ślad: autor dostaje powiadomienie z odpowiedzią, a dane zmieniają status.",
              "Every decision leaves a trace: the author gets a notification with the response and the data changes status.")
    d.hover("#trendTitle", pause=0.6)
    d.hover("#trendChart", pause=2.0)
    d.hover("#recent", pause=2.0)


def step_admin_logout(d, ctx):
    """Wylogowanie administratora."""
    d.step("admin_logout", persona(d, "admin"))
    d.js("window.scrollTo({top: 0, behavior: 'smooth'})")
    d.sleep(0.8)
    d.click("#logoutBtn")
    d.wait_visible("#signin:not([hidden])")
    d.sleep(0.8)


# ---------- część 4: Anna wraca ----------


def step_anna_back(d, ctx):
    """Powiadomienia."""
    d.step("anna_back", persona(d, "anna"))
    logout_api(d)
    d.goto("/", "document.querySelector('#loginBody .login-form')")
    sign_in_app(d, "anna@accessly.test")
    go_tab(d, "profile")
    d.wait_visible("#notifFold summary")
    d.click("#notifFold summary")
    d.wait_visible("#notifList li", timeout=10)
    d.caption("Anna ma powiadomienia: odpowiedź właścicielki i przyjęte poprawki.",
              "Anna has notifications: the owner's answer and accepted corrections.")
    d.hover("#notifList", pause=3.0)


def step_camelot_after(d, ctx):
    """Karta po zmianach właściciela."""
    d.step("camelot_after", persona(d, "anna"))
    open_place_from_catalogue(d, "Camelot", ctx["ids"]["camelot"])
    d.caption("Karta po zmianach: „Potwierdzone przez właściciela”, udogodnienia na miejscu z pokazaniem na mapie, zdjęcie lokalu.",
              "The card after the changes: “Confirmed by the owner”, on-site facilities shown on the map, a photo of the venue.")
    d.hover(".matchbox", pause=1.5)
    d.hover(".attrs li.attr .attr-meta", pause=2.0)
    if d.exists("[data-feature-all]"):
        d.hover(".features", pause=1.0)
        d.click("[data-feature-all]", pause=3.0)
    d.sleep(1.0)


def step_outro(d, ctx):
    """Zakończenie."""
    d.step("outro", persona(d, ""))
    go_tab(d, "map")
    fly(d, 50.0545, 19.9440, 15, wait=1.5)
    d.caption("Accessly – Kraków bez barier. Bezpłatne dla mieszkańców, narzędzia dla lokali i miast.",
              "Accessly – Kraków without barriers. Free for residents, tools for venues and cities.", big=True, hold=5.0)
    d.caption_off()
    d.sleep(1.0)


# ---------- rejestr ----------

STEPS = [
    ("start", "Ekran powitalny", step_start),
    ("login", "Logowanie bez hasła", step_login),
    ("profile", "Profil: potrzeby i preferencje", step_profile),
    ("map", "Mapa barier i znaczniki", step_map),
    ("chip", "Chip potrzeb: filtr i warstwy", step_chip),
    ("layers", "Warstwy danych publicznych", step_layers),
    ("locate", "Moja lokalizacja", step_locate),
    ("search", "Szukanie adresu", step_search),
    ("places_ai", "Miejsca i asystent", step_places_ai),
    ("card", "Karta miejsca: Aktualne / Uzupełnij", step_card),
    ("reviews", "Opinie", step_reviews),
    ("favorite", "Zapisane miejsca i historia", step_favorite),
    ("near", "Szukaj w pobliżu", step_near),
    ("camelot", "Poprawka, pytanie, zdjęcie", step_camelot),
    ("report", "Zgłoszenie bariery", step_report),
    ("detail", "Szczegóły i głosy", step_detail),
    ("list", "Zgłoszenia: lista i Moje", step_list),
    ("newplace", "Nowe miejsce", step_newplace),
    ("help", "Pomoc medyczna", step_help),
    ("theme_lang", "Tryb nocny i języki", step_theme_lang),
    ("sources", "Źródła danych", step_sources),
    ("signout", "Wylogowanie", step_signout),
    ("owner_login", "Panel właściciela: logowanie", step_owner_login),
    ("owner_subs", "Właściciel: propozycje zmian", step_owner_subs),
    ("owner_question", "Właściciel: odpowiedź na pytanie", step_owner_question),
    ("owner_attrs", "Właściciel: atrybuty i potwierdzenie", step_owner_attrs),
    ("owner_features", "Właściciel: udogodnienia na miejscu", step_owner_features),
    ("owner_photo", "Właściciel: zdjęcia i statystyki", step_owner_photo),
    ("owner_logout", "Właściciel: wylogowanie", step_owner_logout),
    ("admin_login", "Panel administracyjny", step_admin_login),
    ("admin_queue", "Administrator: kolejka moderacji", step_admin_queue),
    ("admin_logout", "Administrator: wylogowanie", step_admin_logout),
    ("anna_back", "Anna: powiadomienia", step_anna_back),
    ("camelot_after", "Karta po zmianach właściciela", step_camelot_after),
    ("outro", "Zakończenie", step_outro),
]

PRESETS = {
    "full": [s[0] for s in STEPS],
    # Scenariusz ze slajdu „Demo” (ok. 3 minuty): profil → pytanie → karta → zgłoszenie → właściciel → karta.
    "short": ["start", "login", "profile", "places_ai", "card", "report", "signout",
              "owner_login", "owner_attrs", "owner_logout", "anna_back", "camelot_after", "outro"],
}


def select_steps(preset="full", only=None):
    """Lista (id, tytuł, funkcja) do wykonania: preset albo własna lista identyfikatorów (po przecinku)."""
    by_id = {s[0]: s for s in STEPS}
    if only:
        ids = [i.strip() for i in re.split(r"[,\s]+", only) if i.strip()]
        unknown = [i for i in ids if i not in by_id]
        if unknown:
            raise SystemExit(f"Nieznane kroki: {', '.join(unknown)}. Lista: --list-steps")
        return [by_id[i] for i in ids]
    return [by_id[i] for i in PRESETS[preset]]
