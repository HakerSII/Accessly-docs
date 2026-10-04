"""Scenariusz demonstracji Accessly: kolejne kroki klikane w prawdziwej przeglądarce (do 3 minut).

Każdy krok to funkcja ``step_<id>(d, ctx)`` zarejestrowana w ``STEPS`` z osobą
(mieszkanka Anna, właścicielka Kasia, administrator) i tytułem rozdziału.
``d`` to ``actions.Demo`` (kursor, podpisy, klikanie), ``ctx`` to słownik
z danymi uruchomienia (adres aplikacji, identyfikatory miejsc, zasiane
zgłoszenia, plik zdjęcia, język). Podpisy mają wersję polską i angielską.

Historia (preset ``full``, ok. 3 minuty przy tempie 1): Anna (wózek) loguje się,
ustawia preferencje, ogląda mapę barier i warstwy, pyta asystenta, otwiera
kartę restauracji (źródło, data, status; „Aktualne”; uzupełnia brakującą
informację i karta zmienia się na „Spełnia wszystkie Twoje potrzeby”),
pyta też asystenta w czacie na wdrożonej instancji (``/chat``, model na serwerze
Rampa), proponuje poprawkę w Camelot Cafe i zgłasza awarię windy na przystanku
Stradom. Kasia w panelu właściciela przyjmuje poprawkę, potwierdza dane
i dodaje udogodnienie na mapie. Administrator przyjmuje uzupełnienie
z kolejki. Anna wraca: powiadomienie i karta z danymi potwierdzonymi przez
właściciela. Preset ``short`` to scenariusz ze slajdu „Demo” (bez warstw,
poprawki, udogodnień i administratora).

Czas jest tu najważniejszy: podpisy są krótkie (czytelne w 2–3 s), teksty
wpisywane krótkie, bez zbędnych najazdów kursorem.
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
    "pl": "Restauracja na Kazimierzu bez schodów, z toaletą i parkingiem",
    "en": "A step-free restaurant in Kazimierz with a toilet and parking",
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
    d.fill("#loginEmail", email, pause=0.1)
    d.click({"sel": "#loginEmailForm button"}, pause=0.2)
    d.wait_for(f"typeof me !== 'undefined' && me && me.email === {json.dumps(email)}", timeout=20, desc="zalogowanie")
    d.sleep(0.4)


def sign_in_panel(d, email, email_sel, email_form, code_hint, code_sel, code_form, done):
    """Logowanie w panelu właściciela / administratora: e-mail, kod z podpowiedzi trybu deweloperskiego, zaloguj."""
    d.fill(email_sel, email, pause=0.1)
    d.click({"sel": f"{email_form} button"}, pause=0.2)
    d.wait_visible(code_form)
    code = d.wait_for(
        f"(() => {{ const m = ((document.querySelector({json.dumps(code_hint)}) || {{}}).textContent || '').match(/\\d{{6}}/); return m && m[0]; }})()",
        timeout=10, desc="kod logowania (ACCESSLY_DEV_LOGIN musi być włączone)")
    d.fill(code_sel, code, pause=0.1)
    d.click({"sel": f"{code_form} button[type=submit]"}, pause=0.2)
    d.wait_visible(done, timeout=20)
    d.sleep(0.5)


def go_tab(d, name):
    """Kliknij zakładkę paska dolnego; na desktopie otwarty widok pełnoekranowy (karta, szczegóły) zakrywa pasek, więc najpierw go zamknij."""
    for _ in range(3):
        back = d.js("(() => { const v = document.querySelector('.view.full:not([hidden])'); if (!v) return null;"
                    " const b = v.querySelector('.appbar .iconbtn'); return b && b.id ? '#' + b.id : null; })()")
        if not back:
            break
        d.click(back, pause=0.3)
    d.click(f".tab[data-tab={name}]", pause=0.4)


def logout_api(d):
    """Zakończ sesję przez API (gdy poprzednia osoba została zalogowana), bez klikania."""
    d.js("fetch('/api/auth/logout', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}'}).then(r => r.status)", wait=True)


def fly(d, lat, lng, zoom, wait=1.2):
    """Przesuń mapę aplikacji głównej w widoczny obszar (flyToVisible z app.js)."""
    d.js(f"flyToVisible([{lat}, {lng}], {zoom})")
    d.sleep(wait)


def open_place_from_catalogue(d, query, place_id):
    """Zakładka Miejsca: wyszukaj w katalogu i otwórz kartę miejsca."""
    go_tab(d, "places")
    d.wait_visible("#placeQuery")
    d.fill("#placeQuery", query, pause=0.1)
    d.key("Enter")
    d.wait_visible(f'#placesList [data-place="{place_id}"]', timeout=15)
    d.click(f'#placesList [data-place="{place_id}"]', pause=0.3)
    d.wait_visible("#placeBody .matchbox", timeout=15)
    d.sleep(0.5)


def propose(d, key, value, note):
    """Na karcie miejsca: „Popraw” / „Uzupełnij” atrybut, wybierz wartość, dopisz szczegół, wyślij."""
    d.click(f"[data-edit={key}]", pause=0.3)
    form = f"form[data-propose={key}]"
    d.wait_visible(form)
    d.select_value(f"{form} select", value, pause=0.3)
    if note:
        d.fill(f"{form} input[name=note]", note, pause=0.1)
    d.click({"sel": f"{form} button.pri"}, pause=0.2)
    d.wait_toast()
    d.sleep(0.6)


# ---------- część 1: Anna ----------


def step_start(d, ctx):
    """Ekran powitalny i logowanie bez hasła."""
    d.step("start", persona(d, ""))
    d.goto("/", "document.querySelector('#loginBody .login-form')")
    d.caption("Accessly: sprawdzone informacje o dostępności miejsc w Krakowie i mapa barier od mieszkańców.",
              "Accessly: verified accessibility information about places in Kraków and a barrier map from residents.", hold=1.8)
    if d.exists("#cookieOk"):
        d.click("#cookieOk", pause=0.3)
    d.persona = persona(d, "anna")
    d.caption("Logowanie bez hasła: jednorazowy kod e-mail. Bez konta też można zgłaszać i przeglądać.",
              "Password-less sign-in: a one-time e-mail code. Browsing and reporting work without an account too.")
    sign_in_app(d, "anna@accessly.test")
    d.caption("Profil „Wózek” przyszedł z konta: chipy potrzeb i warstwa wind już włączone.",
              "The “Wheelchair” profile came from the account: need chips and the elevators layer are already on.", hold=1.3)


def step_profile(d, ctx):
    """Profil: preferencje."""
    d.step("profile", persona(d, "anna"))
    go_tab(d, "profile")
    d.wait_visible("#prefList input")
    d.caption("Preferencje: bez schodów, dostępna toaleta, parking OzN. Zapisujemy potrzeby, nigdy dane o zdrowiu.",
              "Preferences: step-free, accessible toilet, disabled parking. We store needs, never health data.")
    d.click('label:has(input[data-pref="step_free"])', pause=0.3)
    d.click('label:has(input[data-pref="accessible_toilet"])', pause=0.3)
    if d.js("(document.querySelector('input[data-pref=elevator]') || {}).checked"):
        d.click('label:has(input[data-pref="elevator"])', pause=0.3)
    d.sleep(0.5)


def step_map(d, ctx):
    """Mapa barier, znacznik, warstwy."""
    d.step("map", persona(d, "anna"))
    go_tab(d, "map")
    fly(d, *VIEW, 16, wait=0.8)
    d.caption("Mapa barier filtrowana przez profil: kwadrat blokuje przejazd, koło to utrudnienie.",
              "The barrier map filtered by the profile: a square blocks the way, a circle is an obstacle.")
    r = ctx["reports"][0]
    fly(d, r["lat"], r["lng"], 17, wait=1.0)
    x, y = d.map_point(r["lat"], r["lng"])
    d.click_at(x, y, pause=0.4)
    d.wait_visible("#sheetBody [data-open]")
    d.hover("#sheetBody .issue", pause=0.6)
    d.click("#layersBtn", pause=0.3)
    d.wait_visible("#layerList input")
    d.caption("Warstwy z otwartych danych miasta i OpenStreetMap: toalety, parking OzN, przystanki, windy, przejścia.",
              "Layers from the city's open data and OpenStreetMap: toilets, disabled parking, stops, elevators, crossings.")
    d.click('label:has(input[data-layer="parking"])', pause=0.3)
    d.click('label:has(input[data-layer="stops"])', pause=0.6)
    d.hover("#layerNearbyTitle", pause=0.6)
    d.click("#layersClose", pause=0.2)


def step_places_ai(d, ctx):
    """Miejsca i asystent."""
    d.step("places_ai", persona(d, "anna"))
    go_tab(d, "places")
    d.wait_visible("#categoryChips .chip")
    mode = "asystent AI" if ctx["ai"] == "ai" else "dopasowanie po słowach kluczowych"
    mode_en = "an AI assistant" if ctx["ai"] == "ai" else "keyword matching"
    d.caption(f"6,5 tys. miejsc z OpenStreetMap i pytanie w języku naturalnym ({mode}).",
              f"6,500 places from OpenStreetMap and a question in natural language ({mode_en}).")
    d.click("#aiInput", pause=0.1)
    d.type_text(AI_QUERY["en" if d.lang != "pl" else "pl"], per_char=0.035)
    d.click("#aiSubmit", pause=0.2)
    d.wait_visible("#aiAnswerTitle", timeout=90)
    d.caption("Fakty pochodzą z serwera, nie z modelu. Braki są oznaczone „?”.",
              "The facts come from the server, never from the model. Gaps are marked “?”.")
    d.hover("#aiResult .items", pause=1.4)
    target = f'#aiResult [data-place="{ctx["ids"]["doroty"]}"]'
    if not d.exists(target):
        target = "#aiResult .items [data-place]"
    d.click(target, pause=0.3)
    d.wait_visible("#placeBody .matchbox", timeout=15)
    d.sleep(0.5)


def step_card(d, ctx):
    """Karta miejsca: źródło, data, status; Aktualne; Uzupełnij."""
    d.step("card", persona(d, "anna"))
    d.caption("Każdy fakt ma wartość, źródło, datę i status weryfikacji.",
              "Every fact has a value, a source, a date and a verification status.")
    d.hover(".attrs li.attr .attr-meta", pause=1.2)
    d.caption("„Aktualne” potwierdza; dwa potwierdzenia dają „Potwierdzone przez społeczność”.",
              "“Up to date” confirms; two confirmations give “Confirmed by the community”.")
    d.click('[data-vote="confirm"][data-key="step_free"]', pause=0.3)
    d.wait_toast()
    d.sleep(0.8)
    if d.exists("[data-edit=door_width]"):
        d.caption("Brak informacji nigdy nie znaczy „dostępne”. Anna zna szerokość drzwi i ją uzupełnia.",
                  "Missing information never means “accessible”. Anna knows the door width and fills it in.")
        propose(d, "door_width", "yes", "ok. 95 cm" if d.lang == "pl" else "about 95 cm")
        d.js("document.getElementById('view-place').scrollTo({top: 0, behavior: 'smooth'})")
        d.sleep(0.8)
        d.caption("Uzupełnienie widać od razu jako niezweryfikowane, a karta mówi „Spełnia wszystkie Twoje potrzeby”.",
                  "The addition shows at once as unverified, and the card now says “Meets all your needs”.")
        d.hover(".matchbox", pause=1.8)


def step_chat(d, ctx):
    """Czat z asystentem (/chat) na wdrożonej instancji: pytanie w języku naturalnym, odpowiedź z narzędzi MCP."""
    d.step("chat", persona(d, "anna"))
    url = ctx.get("chat_url")
    if not url:
        d.log("czat pominięty (--no-chat albo brak adresu)")
        return
    back = "document.querySelector('#needChips .chip')"
    d.goto(url, "document.getElementById('question') && document.getElementById('status')", timeout=60)
    d.caption("Czat z asystentem: lokalny model Phi-3.5 na serwerze Rampa, dane z bazy przez narzędzia MCP, bez zewnętrznych firm AI.",
              "Chat with the assistant: a local Phi-3.5 model on the Rampa server, data from the database through MCP tools, no external AI vendors.")
    try:
        d.wait_for("!document.getElementById('question').disabled", timeout=ctx.get("chat_wait", 25), desc="gotowość czatu")
    except StepError:
        d.log("czat: asystent niedostępny – pokazuję stronę i wracam")
        d.hover("#status", pause=2.0)
        d.goto("/", back)
        return
    question = "Czy Muzeum Narodowe jest dostępne na wózku?" if d.lang == "pl" else "Is the National Museum wheelchair accessible?"
    d.click("#question", pause=0.1)
    d.type_text(question, per_char=0.03)
    d.click("#send", pause=0.3)
    d.caption("Widać każdy krok: wywołanie narzędzia MCP i odpowiedź oparta na danych z bazy, nie na zgadywaniu.",
              "Every step is visible: the MCP tool call and an answer based on database data, not guesswork.")
    try:
        d.wait_for("!!document.querySelector('#log .msg.ai') && !document.getElementById('question').disabled",
                   timeout=ctx.get("chat_wait", 25), desc="odpowiedź czatu")
    except StepError:
        d.log("czat: odpowiedź nie dotarła w czasie – idę dalej")
    d.hover("#log .msg.ai", pause=2.0) if d.exists("#log .msg.ai") else d.sleep(1.0)
    d.goto("/", back)
    d.sleep(0.3)


def step_camelot(d, ctx):
    """Camelot Cafe: poprawka istniejącej informacji."""
    d.step("camelot", persona(d, "anna"))
    open_place_from_catalogue(d, "Camelot", ctx["ids"]["camelot"])
    d.caption("Camelot Cafe: według OpenStreetMap „bez schodów: nie”. Anna wie, że jest podjazd, i proponuje poprawkę.",
              "Camelot Cafe: per OpenStreetMap “step-free: no”. Anna knows there is a ramp and proposes a correction.")
    propose(d, "step_free", "yes", "Przenośny podjazd, poproś obsługę" if d.lang == "pl" else "Portable ramp, ask the staff")
    d.caption("Zmiana istniejącej informacji czeka na właścicielkę albo moderatora.",
              "A change to existing information waits for the owner or a moderator.", hold=1.0)


def step_report(d, ctx):
    """Zgłoszenie bariery w 3 krokach."""
    d.step("report", persona(d, "anna"))
    go_tab(d, "map")
    fly(d, STRADOM[0], STRADOM[1], 17, wait=0.8)
    d.caption("Zgłoszenie bariery w trzech krokach. Krok 1: pinezka stoi, mapa przesuwa się pod nią.",
              "Reporting a barrier in three steps. Step 1: the pin stays still, the map moves under it.")
    d.click("#addBtn", pause=0.3)
    d.wait_visible("#placebar:not([hidden])")
    d.sleep(0.3)
    px, py = d.map_point(*STRADOM)
    pin = d.js("(() => { const c = document.getElementById('crosshair').getBoundingClientRect(); return [c.left + c.width / 2, c.top + c.height]; })()")
    d.drag(px, py, pin[0], pin[1] - 2, duration=0.8, pause=0.3)
    d.click("#placeNextBtn", pause=0.3)
    d.wait_visible("#view-report:not([hidden])")
    d.caption("Krok 2: rodzaj i waga problemu. Nazwa miejsca: przystanek z danych miasta albo adres z OpenStreetMap.",
              "Step 2: kind and severity. The place name: a stop from city data or an address from OpenStreetMap.")
    try:
        d.wait_for("!/Ustalam|Finding|Suche|Визнача/.test(document.getElementById('placeName').textContent)", timeout=6, desc="nazwa miejsca")
    except StepError:
        d.log("nazwa miejsca nie ustaliła się w 6 s (Nominatim?) – idę dalej")
    d.click('label.cat:has(input[value="elevator_broken"])', pause=0.4)
    d.click('label.radio:has(input[value="block"])', pause=0.4)
    d.fill("#description", "Winda na peron nie działa od rana." if d.lang == "pl" else "The platform lift has been down since morning.", pause=0.1)
    d.click("#nextBtn", pause=0.3)
    d.wait_visible("#step3:not([hidden])")
    d.caption("Krok 3: podsumowanie. Awaria windy wygasa po 14 dniach, chyba że ktoś ją potwierdzi.",
              "Step 3: summary. A broken lift expires after 14 days unless somebody confirms it.", hold=0.8)
    d.click("#nextBtn", pause=0.2)
    d.wait_toast(timeout=15)
    d.wait_visible("#sheetBody [data-open]")
    d.caption("Zgłoszenie jest na mapie od razu; inni głosują „nadal jest” albo „naprawione”.",
              "The report is on the map at once; others vote “still there” or “fixed”.", hold=1.4)


def step_signout(d, ctx):
    """Wylogowanie Anny."""
    d.step("signout", persona(d, "anna"))
    go_tab(d, "profile")
    d.wait_visible("#signOutBtn")
    d.click("#signOutBtn", pause=0.2)
    d.wait_visible("#view-login:not([hidden])")
    d.caption("Teraz druga strona: panel właścicielki lokalu.", "Now the other side: the venue owner's panel.", hold=1.0)


# ---------- część 2: Kasia ----------


def step_owner(d, ctx):
    """Panel właściciela: logowanie, przyjęcie poprawki, potwierdzenie danych."""
    d.step("owner", persona(d, "kasia"))
    logout_api(d)
    d.goto("/owner.html", "document.getElementById('signinView') && !document.getElementById('signinView').hidden")
    d.caption("Panel właściciela obiektu: Kasia zarządza Camelot Cafe.", "The venue owner panel: Kasia manages Camelot Cafe.")
    sign_in_panel(d, "kasia@accessly.test", "#emailInput", "#emailForm", "#codeHint", "#codeInput", "#codeForm", "#panelView:not([hidden])")
    d.wait_visible("#attrList li")
    d.hover("#stats", pause=0.6)
    d.hover("#subsTitle", pause=0.3)
    if d.exists(".sub-form"):
        d.caption("Propozycja Anny „bez schodów: nie → tak”. Akceptacja daje status „Potwierdzone przez właściciela”.",
                  "Anna's proposal “step-free: no → yes”. Accepting gives the status “Confirmed by the owner”.")
        d.hover(".sub-form", pause=0.6)
        d.click('.sub-form button[value="accept"]', pause=0.2)
        d.wait_toast()
        d.sleep(0.6)
    d.caption("„Potwierdź informacje” oznacza wszystko jako aktualne; po roku bez potwierdzenia status wraca do „Wymaga weryfikacji”.",
              "“Confirm information” marks everything as up to date; after a year without confirmation it returns to “Needs re-checking”.")
    d.click("#confirmBtn", pause=0.2)
    d.wait_toast()
    d.sleep(0.8)


def step_owner_features(d, ctx):
    """Udogodnienia na miejscu: punkt na mapie."""
    d.step("owner_features", persona(d, "kasia"))
    d.hover("#featTitle", pause=0.2)
    d.click("#batchBtn", pause=0.3)
    d.wait_visible("#batchEditor:not([hidden])")
    d.wait_for("typeof batch !== 'undefined' && !!batch.map", timeout=10, desc="mapa edytora")
    d.caption("Udogodnienia na miejscu jako punkty: klik w mapę, wiersze albo wklejony arkusz.",
              "On-site facilities as points: a map click, rows, or a pasted spreadsheet.")
    d.select_value("#batchKind", "ramp", pause=0.2)
    d.hover("#batchMap", pause=0.2)  # mapa ma 380 px wysokości: musi być w całości w viewportcie
    cx, cy = d.map_center_point("batch.map")
    d.click_at(cx + 34, cy - 30, pause=0.4)
    d.wait_visible("#batchRows li[data-uid]")
    d.fill("#batchRows li[data-uid]:nth-child(1) [data-f=name]", "Podjazd przy wejściu", pause=0.1)
    d.click("#batchSaveBtn", pause=0.2)
    d.wait_toast()
    d.sleep(0.6)


def step_owner_logout(d, ctx):
    """Wylogowanie Kasi."""
    d.step("owner_logout", persona(d, "kasia"))
    d.js("window.scrollTo({top: 0, behavior: 'instant'})")
    d.sleep(0.2)
    d.click("#logoutBtn", pause=0.2)
    d.wait_visible("#signinView:not([hidden])")


# ---------- część 3: administrator ----------


def step_admin(d, ctx):
    """Panel administracyjny: wskaźniki i kolejka moderacji."""
    d.step("admin", persona(d, "admin"))
    logout_api(d)
    d.goto("/admin", "document.getElementById('signin') && (!document.getElementById('signin').hidden || !document.getElementById('dash').hidden)")
    d.caption("Panel administracyjny: wskaźniki, mapa aktywności, pokrycie kategorii i kolejka moderacji.",
              "The admin panel: indicators, an activity map, category coverage and the moderation queue.")
    sign_in_panel(d, "admin@accessly.test", "#loginEmail", "#emailForm", "#devCode", "#loginCode", "#codeForm", "#dash:not([hidden])")
    d.wait_visible("#kpis li", timeout=20)
    d.hover("#kpis", pause=0.6)
    d.hover("#queueTitle", pause=0.2)
    d.click('#queueTabs [data-group="missing"]', pause=0.5)
    d.caption("Kolejka: uzupełnienia, poprawki, zdjęcia, nowe miejsca, przejęcia lokali. Autor dostaje powiadomienie.",
              "The queue: additions, corrections, photos, new places, venue claims. The author gets a notification.")
    if d.exists("#queuePanel .qitem"):
        d.hover("#queuePanel .qitem h3", pause=0.6)
        d.click('#queuePanel .qitem [data-decision="accept"]', pause=0.2)
        d.sleep(0.8)
    d.hover("#trendTitle", pause=0.4)


def step_admin_logout(d, ctx):
    """Wylogowanie administratora."""
    d.step("admin_logout", persona(d, "admin"))
    d.js("window.scrollTo({top: 0, behavior: 'instant'})")
    d.sleep(0.2)
    d.click("#logoutBtn", pause=0.2)
    d.wait_visible("#signin:not([hidden])")


# ---------- część 4: Anna wraca ----------


def step_anna_back(d, ctx):
    """Powiadomienia."""
    d.step("anna_back", persona(d, "anna"))
    logout_api(d)
    d.goto("/", "document.querySelector('#loginBody .login-form')")
    sign_in_app(d, "anna@accessly.test")
    go_tab(d, "profile")
    d.wait_visible("#notifFold summary")
    d.click("#notifFold summary", pause=0.2)
    d.wait_visible("#notifList li", timeout=10)
    d.caption("Anna ma powiadomienie: poprawka przyjęta przez właścicielkę.",
              "Anna has a notification: the correction was accepted by the owner.")
    d.hover("#notifList", pause=1.4)


def step_camelot_after(d, ctx):
    """Karta po zmianach właściciela."""
    d.step("camelot_after", persona(d, "anna"))
    open_place_from_catalogue(d, "Camelot", ctx["ids"]["camelot"])
    d.caption("Karta po zmianach: „Potwierdzone przez właściciela” i udogodnienia na mapie.",
              "The card after the changes: “Confirmed by the owner” and facilities on the map.")
    d.hover(".attrs li.attr .attr-meta", pause=1.0)
    if d.exists("[data-feature-all]"):
        d.click("[data-feature-all]", pause=1.4)


def step_outro(d, ctx):
    """Zakończenie."""
    d.step("outro", persona(d, ""))
    go_tab(d, "map")
    fly(d, 50.0545, 19.9440, 15, wait=1.0)
    d.caption("Accessly – Kraków bez barier. Bezpłatne dla mieszkańców, narzędzia dla lokali i miast.",
              "Accessly – Kraków without barriers. Free for residents, tools for venues and cities.", big=True, hold=2.8)
    d.caption_off()
    d.sleep(0.3)


# ---------- rejestr ----------

STEPS = [
    ("start", "Ekran powitalny i logowanie", step_start),
    ("profile", "Profil: preferencje", step_profile),
    ("map", "Mapa barier i warstwy", step_map),
    ("places_ai", "Miejsca i asystent", step_places_ai),
    ("card", "Karta miejsca: Aktualne / Uzupełnij", step_card),
    ("chat", "Czat z asystentem (instancja Render)", step_chat),
    ("camelot", "Poprawka istniejącej informacji", step_camelot),
    ("report", "Zgłoszenie bariery", step_report),
    ("signout", "Wylogowanie", step_signout),
    ("owner", "Panel właściciela: poprawka i potwierdzenie", step_owner),
    ("owner_features", "Właściciel: udogodnienia na miejscu", step_owner_features),
    ("owner_logout", "Właściciel: wylogowanie", step_owner_logout),
    ("admin", "Panel administracyjny: kolejka", step_admin),
    ("admin_logout", "Administrator: wylogowanie", step_admin_logout),
    ("anna_back", "Anna: powiadomienie", step_anna_back),
    ("camelot_after", "Karta po zmianach właściciela", step_camelot_after),
    ("outro", "Zakończenie", step_outro),
]

PRESETS = {
    "full": [s[0] for s in STEPS],
    # Scenariusz ze slajdu „Demo”: profil → pytanie → karta → zgłoszenie → właściciel → karta (ok. 2 minuty).
    "short": ["start", "profile", "places_ai", "card", "report", "signout", "owner", "owner_logout", "anna_back", "camelot_after", "outro"],
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
