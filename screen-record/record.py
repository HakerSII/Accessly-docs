"""Nagranie demonstracji Accessly w prawdziwej przeglądarce – tylko biblioteka standardowa.

Co robi:

1. Uruchamia serwer aplikacji z czystą bazą (``accessly/server.py`` z repozytorium
   aplikacji; konta demo i katalog miejsc wczytują się same) i zasiewa kilka
   zgłoszeń barier oraz opinię, żeby mapa nie była pusta.
2. Otwiera Chrome w zwykłym oknie (nie headless), a w drugim oknie stronę
   ``recorder.html``, która nagrywa kartę aplikacji przez ``getDisplayMedia`` +
   ``MediaRecorder`` (Chrome sam wybiera kartę po tytule, bez okna wyboru).
   Wynik to MP4 (H.264), bez ffmpeg; starsze przeglądarki dadzą WebM.
3. Klika scenariusz z ``scenario.py`` jak użytkownik: animowany kursor, pisanie
   znak po znaku, przeciąganie mapy, wybór plików, podpisy pod każdym krokiem.
4. Zapisuje film, rozdziały (``chapters.json``), napisy (``captions.vtt``) i dziennik.

Użycie (z dowolnego katalogu; Python 3.8+, Chrome lub Edge):

    py -3 screen-record/record.py                      # cała historia, do 3 min
    py -3 screen-record/record.py --preset short       # scenariusz ze slajdu „Demo”, ok. 2 min
    py -3 screen-record/record.py --lang en            # interfejs i podpisy po angielsku
    py -3 screen-record/record.py --steps login,card   # wybrane kroki (--list-steps pokazuje listę)
    py -3 screen-record/record.py --base http://localhost:8000   # działająca instancja zamiast własnego serwera

Klucze (``ANTHROPIC_API_KEY``, ``ACCESSLY_ORS_KEY``) są czytane z ``.env`` w repozytorium
aplikacji; ``--no-ai`` wymusza tryb reguł (deterministyczny, bez sieci).
"""

import argparse
import base64
import datetime
import http.cookiejar
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import cdp  # noqa: E402  # pylint: disable=wrong-import-position
import scenario  # noqa: E402  # pylint: disable=wrong-import-position
from actions import Demo, make_photo  # noqa: E402  # pylint: disable=wrong-import-position

DEFAULT_APP_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "Yannie-draft-acihy", "accessly"))

# Zgłoszenia barier zasiewane przed nagraniem (Kazimierz i Stradom, przy prawdziwych przystankach).
SEED_REPORTS = [
    {"type": "high_kerb", "severity": "partial", "lat": 50.048068, "lng": 19.943336, "place": "Przystanek Plac Wolnica 01",
     "description": "Wysoki krawężnik bez obniżenia przy przejściu na plac."},
    {"type": "entrance_closed", "severity": "block", "lat": 50.0532, "lng": 19.9487, "place": "ul. Miodowa 20",
     "description": "Wejście od ul. Miodowej zamknięte, remont chodnika do końca miesiąca."},
    {"type": "high_step", "severity": "partial", "lat": 50.0505, "lng": 19.9458, "place": "ul. Józefa 15",
     "description": "Dwa stopnie do wejścia, brak podjazdu."},
    {"type": "escalator", "severity": "partial", "lat": 50.0538, "lng": 19.9532, "place": "Galeria Kazimierz",
     "description": "Schody ruchome od strony parkingu wyłączone."},
    {"type": "tactile", "severity": "partial", "lat": 50.056907, "lng": 19.944997, "place": "Przystanek Starowiślna 02",
     "description": "Brak oznaczeń dotykowych na peronie."},
]

PLACES = {
    "doroty": ("Kuchnia u Doroty", 50.050562, 19.941171),
    "camelot": ("Camelot Cafe", 50.062997, 19.939105),
    "przypiecek": ("Przypiecek", 50.065198, 19.938466),
}


class Log:
    """Dziennik na ekran i do pliku."""

    def __init__(self, path):
        self.f = open(path, "a", encoding="utf-8")  # pylint: disable=consider-using-with  # zamykany w close()
        self.t0 = time.monotonic()

    def __call__(self, msg):
        line = f"{time.monotonic() - self.t0:7.1f}s  {msg}"
        print(line, flush=True)
        self.f.write(line + "\n")
        self.f.flush()

    def close(self):
        """Zamknij plik."""
        self.f.close()


class Client:
    """Klient JSON API z ciasteczkami (jedna osoba = jeden klient)."""

    def __init__(self, base):
        self.base = base
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def call(self, method, path, body=None):
        """Wywołaj ``method path`` z opcjonalnym JSON-em; zwróć odpowiedź JSON."""
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method, headers={"Content-Type": "application/json"})
        try:
            with self.opener.open(req, timeout=30) as r:
                raw = r.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"{method} {path}: {e.code} {e.read().decode(errors='replace')[:200]}") from e

    def sign_in(self, email):
        """Zaloguj się kodem z odpowiedzi (wymaga ACCESSLY_DEV_LOGIN włączonego)."""
        res = self.call("POST", "/api/auth/request", {"email": email})
        code = res.get("devCode")
        if not code:
            raise SystemExit("Serwer nie zwraca kodu logowania (devCode): uruchom go z ACCESSLY_DEV_LOGIN=1.")
        self.call("POST", "/api/auth/verify", {"email": email, "code": code})


def parse_args():
    """Argumenty wiersza poleceń."""
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--app-dir", default=DEFAULT_APP_DIR, help="katalog accessly/ z server.py (domyślnie repozytorium obok)")
    p.add_argument("--base", default=None, help="adres działającej aplikacji zamiast własnego serwera z czystą bazą")
    p.add_argument("--port", type=int, default=8765, help="port własnego serwera (domyślnie 8765)")
    p.add_argument("--out", default=os.path.join(HERE, "out"), help="katalog na nagrania (domyślnie screen-record/out)")
    p.add_argument("--name", default=None, help="nazwa pliku filmu bez rozszerzenia (domyślnie accessly-demo)")
    p.add_argument("--lang", default="pl", choices=["pl", "en"], help="język interfejsu i podpisów")
    p.add_argument("--preset", default="full", choices=sorted(scenario.PRESETS), help="full: cała historia (do 3 min); short: scenariusz ze slajdu „Demo” (ok. 2 min)")
    p.add_argument("--steps", default=None, help="własna lista kroków po przecinku (zamiast presetu)")
    p.add_argument("--list-steps", action="store_true", help="wypisz kroki i zakończ")
    p.add_argument("--speed", type=float, default=1.0, help="tempo: 1 = normalne, 1.5 = szybciej, 0.8 = wolniej")
    p.add_argument("--size", default="1280x720", help="rozmiar viewportu w px CSS, np. 1280x720, 1600x900 (Chrome nagrywa kartę w rozdzielczości ekranu, np. 1920x1080)")
    p.add_argument("--video", default="1920x1080", help="rozdzielczość filmu (Chrome renderuje kartę w tej skali), np. 1920x1080, 1280x720; auto = jak viewport")
    p.add_argument("--fps", type=int, default=30, help="klatki na sekundę nagrania")
    p.add_argument("--bitrate", type=int, default=6_000_000, help="bitrate wideo w b/s")
    p.add_argument("--capture", default="tab", choices=["tab", "screen"], help="tab: sama karta aplikacji (domyślnie); screen: cały ekran")
    p.add_argument("--screen-name", default="Entire screen", help="nazwa źródła przy --capture screen (np. 'Screen 1')")
    p.add_argument("--no-captions", action="store_true", help="bez podpisów na filmie (zostają w captions.vtt)")
    p.add_argument("--no-ai", action="store_true", help="nie przekazuj klucza AI: asystent w trybie reguł (deterministyczny)")
    p.add_argument("--chat-url", default="https://yannie-draft-acihy.onrender.com/chat",
                   help="adres strony czatu z asystentem na wdrożonej instancji (krok „chat”; lokalny main nie ma /chat)")
    p.add_argument("--no-chat", action="store_true", help="pomiń krok z czatem")
    p.add_argument("--chat-wait", type=int, default=25, help="ile sekund czekać na gotowość czatu i na odpowiedź (domyślnie 25)")
    p.add_argument("--no-record", action="store_true", help="tylko przeklikaj scenariusz, bez nagrywania")
    p.add_argument("--no-remux", action="store_true", help="nie przepakowuj MP4 przez ffmpeg, nawet gdy jest w PATH")
    p.add_argument("--keep-open", action="store_true", help="zostaw przeglądarkę i serwer po zakończeniu (Enter zamyka)")
    p.add_argument("--chrome", default=None, help="ścieżka do chrome.exe / msedge.exe")
    p.add_argument("--position", default="40,40", help="położenie okna przeglądarki na ekranie, np. 40,40")
    return p.parse_args()


def load_env(path):
    """Wczytaj plik .env (KEY=VALUE, komentarze #) do słownika."""
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def start_server(app_dir, port, run_dir, env_file, no_ai, log):
    """Uruchom server.py z czystą bazą w katalogu nagrania; poczekaj, aż odpowie /api/config."""
    server = os.path.join(app_dir, "server.py")
    if not os.path.exists(server):
        raise SystemExit(f"Nie znaleziono {server}; podaj --app-dir albo --base.")
    dotenv = load_env(env_file)
    env = dict(os.environ)
    env["ACCESSLY_DB"] = os.path.join(run_dir, "demo.db")
    env["ACCESSLY_DEV_LOGIN"] = "1"
    env["ACCESSLY_DEMO_USERS"] = "1"
    env["ACCESSLY_API_BASE"] = ""  # zgłoszenia lokalnie: deterministyczne i bez sieci
    for key in ("ACCESSLY_CITY", "ACCESSLY_AI_MODEL", "ACCESSLY_ORS_KEY", "ANTHROPIC_API_KEY"):
        if dotenv.get(key) and not env.get(key):
            env[key] = dotenv[key]
    if no_ai:
        env.pop("ANTHROPIC_API_KEY", None)
    env.pop("ACCESSLY_SMTP_HOST", None)
    out = open(os.path.join(run_dir, "server.log"), "w", encoding="utf-8")  # pylint: disable=consider-using-with
    proc = subprocess.Popen([sys.executable, "server.py", str(port)], cwd=app_dir, env=env, stdout=out, stderr=subprocess.STDOUT)
    base = f"http://localhost:{port}"
    log(f"serwer: {sys.executable} server.py {port} (baza {env['ACCESSLY_DB']}); czekam na import katalogu miejsc…")
    deadline = time.monotonic() + 240
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise SystemExit(f"Serwer zakończył się kodem {proc.returncode}; zobacz {os.path.join(run_dir, 'server.log')}")
        try:
            with urllib.request.urlopen(base + "/api/config", timeout=3) as r:
                if r.status == 200:
                    return proc, base
        except (OSError, ValueError):
            time.sleep(1.0)
    proc.terminate()
    raise SystemExit("Serwer nie odpowiedział w 4 minuty.")


def resolve_places(base, log):
    """Identyfikatory miejsc demo po nazwie (katalog może mieć inne ID po odświeżeniu snapshotu)."""
    client = Client(base)
    ids = {}
    for key, (name, lat, lng) in PLACES.items():
        q = urllib.parse.quote(name)
        data = client.call("GET", f"/api/places?q={q}&near={lat},{lng}&limit=10")
        items = data.get("items", [])
        hit = next((i for i in items if i.get("name") == name), items[0] if items else None)
        if not hit:
            raise SystemExit(f"W katalogu nie ma miejsca „{name}”; zaktualizuj PLACES w record.py.")
        ids[key] = hit["id"]
        log(f"miejsce {name}: {hit['id']}")
    return ids


def seed(base, ids, log):
    """Zasiej zgłoszenia barier oraz opinię i potwierdzenie Piotra (żeby „Aktualne” Anny dało status społeczności)."""
    anon = Client(base)
    reports = []
    for r in SEED_REPORTS:
        try:
            created = anon.call("POST", "/api/reports", r)
            reports.append({**r, "id": created.get("id")})
        except RuntimeError as e:
            log(f"zgłoszenie nie zasiane ({e})")
    log(f"zasiano zgłoszeń: {len(reports)}")
    piotr = Client(base)
    try:
        piotr.sign_in("piotr@accessly.test")
        piotr.call("POST", f"/api/places/{ids['doroty']}/reviews",
                   {"rating": 5, "text": "Wjechałem bez problemu, obsługa pomogła z drzwiami, toaleta przestronna."})
        piotr.call("POST", f"/api/places/{ids['doroty']}/attributes/step_free/vote", {"vote": "confirm"})
        piotr.call("POST", "/api/auth/logout", {})
        log("Piotr: opinia i potwierdzenie „bez schodów” w Kuchni u Doroty")
    except (RuntimeError, SystemExit) as e:
        log(f"dane Piotra nie zasiane ({e})")
    return reports


def warm_up(chat_url, log):
    """Obudź wdrożoną instancję (Render usypia darmowe usługi): strona czatu, jej /api/config i status asystenta."""
    root = chat_url.rsplit("/", 1)[0]
    try:
        urllib.request.urlopen(chat_url, timeout=90).read()
        cfg = json.load(urllib.request.urlopen(root + "/api/config", timeout=90))
        api = cfg.get("apiBase") or root
        status = json.load(urllib.request.urlopen(api + "/api/v1/ai/chat/status", timeout=90))
        log(f"czat na {root}: asystent {status.get('state')} ({status.get('model')})")
    except Exception as e:  # pylint: disable=broad-except  # rozgrzewka jest tylko pomocą; krok czatu i tak ma własne limity
        log(f"czat: rozgrzewka nieudana ({e})")


def chrome_args(a, width, height, left, top):
    """Flagi Chrome dla nagrania w zwykłym oknie."""
    args = [
        "--no-first-run", "--no-default-browser-check", "--disable-search-engine-choice-screen",
        "--disable-features=Translate,MediaRouter,PrivacySandboxSettings4,HttpsUpgrades",
        "--hide-crash-restore-bubble", "--disable-session-crashed-bubble", "--disable-infobars",
        f"--lang={a.lang}", "--force-device-scale-factor=1",
        "--disable-renderer-backgrounding", "--disable-background-timer-throttling", "--disable-backgrounding-occluded-windows",
        "--autoplay-policy=no-user-gesture-required", "--disable-popup-blocking",
        f"--window-size={width},{height + 110}", f"--window-position={left},{top}",
    ]
    if a.capture == "tab":
        args.append("--auto-select-tab-capture-source-by-title=Accessly")
    else:
        args.append(f"--auto-select-desktop-capture-source={a.screen_name}")
    args.append("about:blank")
    return args


def fit_viewport(browser, tab, width, height, log, tries=4):
    """Dopasuj okno tak, by viewport karty miał dokładnie ``width``×``height`` CSS px."""
    for _ in range(tries):
        iw, ih = tab.evaluate("[innerWidth, innerHeight]")
        if abs(iw - width) <= 1 and abs(ih - height) <= 1:
            return iw, ih
        b = browser.window_for(tab)["bounds"]
        browser.set_bounds(tab, left=b.get("left", 40), top=b.get("top", 40),
                           width=int(b["width"] + (width - iw)), height=int(b["height"] + (height - ih)))
        time.sleep(0.7)
    iw, ih = tab.evaluate("[innerWidth, innerHeight]")
    log(f"uwaga: viewport {iw}x{ih} zamiast {width}x{height} (za mały ekran?)")
    return iw, ih


class Recorder:
    """Karta rejestratora: start, zrzucanie fragmentów do pliku w tle, stop."""

    def __init__(self, tab, path, log):
        self.tab = tab
        self.path = path
        self.log = log
        self.f = None
        self.info = None
        self.stop_event = threading.Event()
        self.thread = None
        self.bytes = 0

    def open(self, fps, bitrate, size=None):
        """Przechwyć kartę (bez kodowania) i zwróć rozmiar źródła; ``size``: (szer, wys) klatki albo None."""
        self.tab.call("Page.bringToFront")
        time.sleep(0.4)
        self.opts = {"fps": fps, "bitrate": bitrate, "timeslice": 2000}
        if size:
            self.opts.update(width=size[0], height=size[1])
        return self.tab.evaluate(f"R.open({json.dumps(self.opts)})", wait=True, timeout=30)

    def record(self):
        """Zacznij kodować przechwycony strumień (po dopasowaniu okna, żeby rozmiar klatki już się nie zmieniał)."""
        self.info = self.tab.evaluate(f"R.record({json.dumps(self.opts)})")
        return self.info

    def run_in_background(self):
        """Wątek zrzucający fragmenty co 2 s (osobne połączenie, więc nie koliduje z kartą aplikacji)."""
        self.f = open(self.path, "wb")  # pylint: disable=consider-using-with  # zamykany w finish()
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        while not self.stop_event.wait(2.0):
            try:
                self._drain("R.drain()")
            except Exception as e:  # pylint: disable=broad-except  # nagranie ma trwać mimo pojedynczego błędu
                self.log(f"rejestrator: {e}")

    def _drain(self, expression):
        for part in self.tab.evaluate(expression, wait=True, timeout=120) or []:
            data = base64.b64decode(part)
            self.f.write(data)
            self.bytes += len(data)
        self.f.flush()

    def state(self):
        """Stan rejestratora (klatki, bajty, błąd)."""
        return self.tab.evaluate("R.state()")

    def finish(self):
        """Zatrzymaj nagranie, dopisz resztę i zamknij plik."""
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=130)
        state = self.state()
        self._drain("R.stop()")
        self.f.close()
        return state


def remux(path, log):
    """Przepakuj MP4 przez ffmpeg (poprawny czas trwania, moov na początku), jeśli ffmpeg jest w PATH."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not path.endswith(".mp4"):
        return path
    tmp = path[:-4] + ".remux.mp4"
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-i", path, "-c", "copy", "-movflags", "+faststart", tmp]
    try:
        subprocess.run(cmd, check=True, timeout=600)
        os.replace(tmp, path)
        log("ffmpeg: plik przepakowany (faststart)")
    except (subprocess.SubprocessError, OSError) as e:
        log(f"ffmpeg pominięty ({e})")
        if os.path.exists(tmp):
            os.remove(tmp)
    return path


def vtt_time(seconds):
    """Czas w formacie WebVTT."""
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def write_chapters(run_dir, demo, steps_run, video, info, duration):
    """Zapisz chapters.json (kroki i podpisy z czasami) i captions.vtt."""
    titles = {s[0]: s[1] for s in scenario.STEPS}
    steps = [{"id": c["step"], "title": titles.get(c["step"], c["step"]), "start": c["t"]} for c in demo.chapters if c["kind"] == "step"]
    captions = [c for c in demo.chapters if c["kind"] == "caption"]
    data = {
        "video": os.path.basename(video), "duration": round(duration, 1), "capture": info, "lang": demo.lang,
        "steps": steps, "captions": [{"start": c["t"], "kicker": c["kicker"], "text": c["text"]} for c in captions if c["text"]],
        "failed": steps_run["failed"],
    }
    with open(os.path.join(run_dir, "chapters.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    lines = ["WEBVTT", ""]
    for i, c in enumerate(captions):
        if not c["text"]:
            continue
        end = next((n["t"] for n in captions[i + 1:]), duration)
        end = min(max(end, c["t"] + 1.0), duration if duration > c["t"] else c["t"] + 5)
        lines += [f"{vtt_time(c['t'])} --> {vtt_time(end)}", (f"[{c['kicker']}] " if c["kicker"] else "") + c["text"], ""]
    with open(os.path.join(run_dir, "captions.vtt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():  # pylint: disable=too-many-locals,too-many-statements,too-many-branches
    """Cały przebieg: serwer → dane → Chrome → nagranie → pliki."""
    a = parse_args()
    if a.list_steps:
        for step_id, title, _ in scenario.STEPS:
            marks = " ".join(f"[{p}]" for p, ids in scenario.PRESETS.items() if step_id in ids)
            print(f"{step_id:16} {title:42} {marks}")
        return 0
    steps = scenario.select_steps(a.preset, a.steps)
    width, height = (int(v) for v in a.size.lower().split("x"))
    video_size = None if a.video.lower() == "auto" else tuple(int(v) for v in a.video.lower().split("x"))
    left, top = (int(v) for v in a.position.split(","))
    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    run_dir = os.path.join(a.out, stamp)
    os.makedirs(run_dir, exist_ok=True)
    log = Log(os.path.join(run_dir, "log.txt"))
    log(f"katalog nagrania: {run_dir}")

    server = None
    browser = None
    try:
        if a.base:
            base = a.base.rstrip("/")
            log(f"używam działającej aplikacji: {base}")
        else:
            server, base = start_server(a.app_dir, a.port, run_dir, os.path.join(a.app_dir, "..", ".env"), a.no_ai, log)
            log(f"serwer gotowy: {base}")
        config = Client(base).call("GET", "/api/config")
        ids = resolve_places(base, log)
        reports = seed(base, ids, log)
        photo = make_photo(os.path.join(run_dir, "zdjecie-wejscia.png"))
        ctx = {"base": base, "ids": ids, "reports": reports, "photo": photo, "lang": a.lang, "ai": config.get("ai", "rules"),
               "routing": config.get("routing", False), "chat_url": "" if a.no_chat else a.chat_url, "chat_wait": a.chat_wait}
        if ctx["chat_url"]:
            threading.Thread(target=warm_up, args=(ctx["chat_url"], log), daemon=True).start()

        profile = tempfile.mkdtemp(prefix="accessly-rec-")
        browser = cdp.Browser(a.chrome or cdp.find_chrome(), profile, chrome_args(a, width, height, left, top))
        app = browser.first_tab()
        # Nagranie zaczyna się na planszy tytułowej: w jej trakcie okno jest dopasowywane (na jednolitym tle
        # tego nie widać), a pasek „udostępniasz tę kartę” jest już na ekranie, zanim ruszy kodowanie.
        title_url = "file:///" + os.path.join(HERE, "title.html").replace("\\", "/") + f"?lang={a.lang}&base={urllib.parse.quote(base, safe='')}"
        app.navigate(title_url)
        time.sleep(0.8)
        browser.grant(base, ["geolocation"])
        app.call("Emulation.setGeolocationOverride", latitude=scenario.GEO[0], longitude=scenario.GEO[1], accuracy=25)

        shots = os.path.join(run_dir, "shots")
        demo = Demo(app, base, lang=a.lang, speed=a.speed, captions=not a.no_captions, log=log, shots_dir=shots)
        demo.pos = (width * 0.6, height * 0.6)

        recorder = None
        video = None
        if not a.no_record:
            rec_url = "file:///" + os.path.join(HERE, "recorder.html").replace("\\", "/")
            rec_tab = browser.new_tab(rec_url, new_window=True, width=560, height=380, left=left + 60, top=top + 60)
            time.sleep(0.8)
            video = os.path.join(run_dir, (a.name or "accessly-demo") + ".mp4")
            recorder = Recorder(rec_tab, video, log)
            opened = recorder.open(a.fps, a.bitrate, video_size)
            log(f"przechwycono kartę: {opened.get('width')}x{opened.get('height')}")
            app.call("Page.bringToFront")
            time.sleep(0.8)
        if a.capture == "tab":
            fit_viewport(browser, app, width, height, log)
        else:
            browser.set_bounds(app, windowState="fullscreen")
            time.sleep(1.0)
        time.sleep(1.0)  # rozmiar źródła musi się ustalić przed startem kodowania
        if recorder:
            info = recorder.record()
            if not str(info.get("mime", "")).startswith("video/mp4"):
                video = recorder.path = video[:-4] + ".webm"  # starsza przeglądarka: WebM zamiast MP4
            recorder.run_in_background()
            log(f"nagrywam: {info}")
        app.call("Page.bringToFront")
        demo.t0 = time.monotonic()
        app.evaluate("window.show && window.show()")
        demo.sleep(2.5)  # plansza tytułowa
        iw, ih = app.evaluate("[innerWidth, innerHeight]")
        log(f"viewport podczas nagrania: {iw}x{ih}")
        demo.ensure_overlay()

        steps_run = {"done": [], "failed": []}
        for step_id, title, fn in steps:
            try:
                fn(demo, ctx)
                steps_run["done"].append(step_id)
            except (EOFError, ConnectionError) as e:
                log(f"przeglądarka zamknięta w kroku {step_id}: {e}")
                steps_run["failed"].append({"step": step_id, "error": str(e)})
                break
            except Exception as e:  # pylint: disable=broad-except  # jeden nieudany krok nie przerywa nagrania
                log(f"BŁĄD w kroku {step_id} ({title}): {e}")
                steps_run["failed"].append({"step": step_id, "error": str(e)})
                demo.screenshot(f"blad-{step_id}")
                try:
                    demo.key("Escape")
                    demo.ensure_overlay()
                except Exception:  # pylint: disable=broad-except  # próba powrotu do normalnego stanu
                    pass
            if recorder and recorder.state().get("error") and not steps_run.get("capture_lost"):
                steps_run["capture_lost"] = recorder.state()["error"]
                log(f"UWAGA: rejestrator zgłosił błąd „{steps_run['capture_lost']}”. Przechwytywanie karty zostało zatrzymane"
                    " (przycisk „Zatrzymaj” na pasku Chrome albo zamknięta karta rejestratora?) – film jest urwany w tym miejscu.")
        duration = time.monotonic() - demo.t0
        time.sleep(1.0)

        info = None
        if recorder:
            state = recorder.finish()
            info = {**(recorder.info or {}), "frames": state.get("frames"), "bytes": recorder.bytes}
            log(f"nagranie zakończone: {duration:.0f} s, {recorder.bytes / 1e6:.1f} MB, klatek {state.get('frames')}")
            if not a.no_remux:
                video = remux(video, log)
        write_chapters(run_dir, demo, steps_run, video or "", info, duration)
        log(f"rozdziały: {os.path.join(run_dir, 'chapters.json')}; napisy: captions.vtt")
        if steps_run["failed"]:
            log("kroki z błędami: " + ", ".join(f["step"] for f in steps_run["failed"]))
        if steps_run.get("capture_lost"):
            log("UWAGA: nagranie niepełne – przechwytywanie przerwano w trakcie; uruchom ponownie i nie dotykaj paska udostępniania w Chrome.")
        if video:
            log(f"FILM: {video}")
        if a.keep_open:
            input("Przeglądarka i serwer działają; Enter zamyka. ")
        return 1 if steps_run["failed"] or steps_run.get("capture_lost") else 0
    finally:
        if browser:
            browser.close()
        if server:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
        log.close()


if __name__ == "__main__":
    sys.exit(main())
