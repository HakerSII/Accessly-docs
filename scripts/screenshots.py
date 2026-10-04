"""Zrzuty ekranu działającej aplikacji Accessly do slajdów – tylko biblioteka standardowa.

Steruje przeglądarką Chrome w trybie headless przez Chrome DevTools Protocol (własny,
minimalny klient WebSocket), ustawia pamięć lokalną (profil „Wózek”, widok na Rynek,
tryb dzienny, pominięty ekran logowania) i zapisuje widoki jako PNG.

Użycie (aplikacja musi działać, np. ``scripts/run.sh`` lub ``scripts/docker-run.sh``):

    py -3 scripts/screenshots.py --base http://localhost:8000 --out screenshots
    py -3 scripts/screenshots.py --lang en --out screenshots-en      # interfejs po angielsku

Potem ``scripts/prepare-images.ps1 -Source screenshots`` przycina i zmniejsza pliki
do ``prezentacja/img/``. Konta demo (``kasia@accessly.test`` – właścicielka Camelot Cafe,
``admin@accessly.test``) istnieją, gdy serwer tworzy użytkowników demo
(``ACCESSLY_DEMO_USERS`` różne od 0) i zwraca kod logowania w odpowiedzi
(``ACCESSLY_DEV_LOGIN`` różne od 0).
"""

import argparse
import base64
import json
import os
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
]

PLACE_IDS = {
    "karta-miejsca": "p6ef6adf3e3d",  # Przypiecek – bar z kilkoma atrybutami z OSM (prepare-images.ps1 tnie ten plik)
    "karta-wlasciciel": "p35344c730ca",  # Camelot Cafe – miejsce konta demo kasia@
    "karta-pozytywna": "pcb082342597",  # Kuchnia u Doroty – bez schodów, toaleta, parking OzN: wszystkie potwierdzone
}

# Preferencje, które to miejsce spełnia w całości: karta pokazuje zielone „Spełnia wszystkie Twoje potrzeby”
# (slajd tytułowy ma pokazywać udogodnienia, nie bariery).
POSITIVE_PREFS = ["step_free", "accessible_toilet", "disabled_parking"]


class WebSocket:
    """Minimalny klient WebSocket (RFC 6455) wystarczający dla CDP."""

    def __init__(self, url):
        rest = url.split("://", 1)[1]
        hostport, path = rest.split("/", 1)
        host, port = hostport.split(":")
        self.sock = socket.create_connection((host, int(port)))
        key = base64.b64encode(os.urandom(16)).decode()
        request = (
            f"GET /{path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(request.encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += self.sock.recv(4096)
        self.buf = buf.split(b"\r\n\r\n", 1)[1]
        self.next_id = 0

    def _exact(self, n):
        while len(self.buf) < n:
            chunk = self.sock.recv(1 << 20)
            if not chunk:
                raise EOFError("połączenie zamknięte")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def send(self, text):
        data = text.encode()
        header = bytearray([0x81])
        mask = os.urandom(4)
        n = len(data)
        if n < 126:
            header.append(0x80 | n)
        elif n < 65536:
            header.append(0x80 | 126)
            header += struct.pack(">H", n)
        else:
            header.append(0x80 | 127)
            header += struct.pack(">Q", n)
        header += mask
        self.sock.sendall(bytes(header) + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def recv(self):
        message = b""
        while True:
            b1, b2 = self._exact(2)
            fin, opcode = b1 & 0x80, b1 & 0x0F
            n = b2 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._exact(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._exact(8))[0]
            mask = self._exact(4) if b2 & 0x80 else None
            payload = self._exact(n)
            if mask:
                payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
            if opcode == 8:
                raise EOFError("serwer zamknął połączenie")
            if opcode == 9:  # ping
                continue
            message += payload
            if fin:
                return message.decode()

    def call(self, method, **params):
        self.next_id += 1
        self.send(json.dumps({"id": self.next_id, "method": method, "params": params}))
        while True:
            msg = json.loads(self.recv())
            if msg.get("id") == self.next_id:
                if "error" in msg:
                    raise RuntimeError(msg["error"])
                return msg.get("result", {})


class Browser:
    """Headless Chrome sterowany przez CDP."""

    def __init__(self, chrome, profile, port=9333):
        self.proc = subprocess.Popen(
            [
                chrome,
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                "--no-first-run",
                "--lang=pl",
                f"--remote-debugging-port={port}",
                f"--user-data-dir={profile}",
                "--window-size=1440,900",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        page = None
        for _ in range(80):
            try:
                targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json"))
                page = next(t for t in targets if t["type"] == "page")
                break
            except (OSError, StopIteration, ValueError):
                time.sleep(0.25)
        if page is None:
            self.proc.terminate()
            raise SystemExit("Chrome nie wystartował (port debugowania nie odpowiada)")
        self.ws = WebSocket(page["webSocketDebuggerUrl"])
        self.ws.call("Page.enable")
        self.ws.call("Runtime.enable")

    def evaluate(self, expression, wait=False):
        result = self.ws.call("Runtime.evaluate", expression=expression, awaitPromise=wait, returnByValue=True)
        return result.get("result", {}).get("value")

    def goto(self, url, wait=5):
        self.ws.call("Page.navigate", url=url)
        time.sleep(wait)

    def metrics(self, width, height, mobile=False, scale=1.5):
        self.ws.call(
            "Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=scale, mobile=mobile
        )
        self.ws.call("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": "light"}])

    def shot(self, path, wait=1.5):
        time.sleep(wait)
        data = self.ws.call("Page.captureScreenshot", format="png")["data"]
        with open(path, "wb") as f:
            f.write(base64.b64decode(data))
        print("zapisano", os.path.basename(path), os.path.getsize(path), "B")

    def close(self):
        self.proc.terminate()


SETUP = """
localStorage.setItem('bp.guest', 'true');
localStorage.setItem('bp.cookiesOk', 'true');
localStorage.setItem('bp.lang', JSON.stringify(%(lang)s));
localStorage.setItem('bp.theme', '"light"');
localStorage.setItem('bp.view', JSON.stringify({center: [50.0617, 19.9373], zoom: 16}));
localStorage.setItem('bp.needs', JSON.stringify(['wheelchair']));
localStorage.setItem('bp.layers', JSON.stringify(['toilets', 'elevators', 'parking']));
'ok'
"""

SIGN_IN = """
(async () => {
  const h = {'Content-Type': 'application/json'};
  const r = await fetch('/api/auth/request', {method: 'POST', headers: h, body: JSON.stringify({email: '%(email)s'})});
  const j = await r.json();
  const v = await fetch('/api/auth/verify', {method: 'POST', headers: h,
      body: JSON.stringify({email: '%(email)s', code: j.devCode})});
  return r.status + ' ' + v.status;
})()
"""

CLICK_TAB = "document.querySelector('.tab[data-tab=\"%s\"]').click()"


def find_chrome():
    """Pierwsza istniejąca przeglądarka z listy kandydatów."""
    for path in CHROME_CANDIDATES:
        if os.path.exists(path):
            return path
    raise SystemExit("Nie znaleziono Chrome/Edge; podaj --chrome ŚCIEŻKA")


def main():
    """Zrób komplet zrzutów."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", default="http://localhost:8000", help="adres działającej aplikacji")
    parser.add_argument("--out", default="screenshots", help="katalog na pliki PNG")
    parser.add_argument("--chrome", default=None, help="ścieżka do chrome.exe / msedge.exe")
    parser.add_argument("--lang", default="pl", choices=["pl", "en", "de", "uk"], help="język interfejsu (bp.lang)")
    parser.add_argument("--ai-query", default=None, help="zapytanie do asystenta (domyślnie przykład w języku --lang)")
    args = parser.parse_args()
    if args.ai_query is None:
        args.ai_query = {
            "pl": "Kawiarnia w centrum, wjadę na wózku, przyda się dostępna toaleta",
            "en": "A café in the centre I can enter in a wheelchair, ideally with an accessible toilet",
            "de": "Ein Café im Zentrum, in das ich mit dem Rollstuhl komme, am besten mit barrierefreier Toilette",
            "uk": "Кав'ярня в центрі, куди заїду на візку, бажано з доступним туалетом",
        }[args.lang]

    os.makedirs(args.out, exist_ok=True)
    out = lambda name: os.path.join(args.out, name)  # noqa: E731  # krótki pomocnik ścieżki
    base = args.base.rstrip("/")
    profile = tempfile.mkdtemp(prefix="accessly-shots-")
    browser = Browser(args.chrome or find_chrome(), profile)
    try:
        browser.metrics(1440, 900)
        browser.goto(base + "/", 4)
        browser.evaluate(SETUP % {"lang": json.dumps(args.lang)})

        browser.goto(base + "/", 7)
        browser.shot(out("01-mapa-desktop.png"))
        browser.evaluate("document.getElementById('layersBtn').click()")
        browser.shot(out("02-warstwy-desktop.png"), 2)
        browser.evaluate("document.getElementById('layersBtn').click()")
        browser.evaluate(CLICK_TAB % "places")
        browser.shot(out("03-miejsca-desktop.png"), 3)
        browser.evaluate(
            "document.getElementById('aiInput').value = %s; document.getElementById('aiSubmit').click()"
            % json.dumps(args.ai_query)
        )
        browser.shot(out("04-asystent-desktop.png"), 10)
        for name, place_id in PLACE_IDS.items():
            browser.goto(f"{base}/#place-{place_id}", 5)
            browser.shot(out(f"05-{name}-desktop.png"), 2)
        browser.goto(base + "/", 6)
        browser.evaluate("document.getElementById('addBtn').click()")
        browser.shot(out("07-zglos-krok1-desktop.png"), 2)
        browser.goto(base + "/", 6)
        browser.evaluate(CLICK_TAB % "list")
        browser.shot(out("09-zgloszenia-desktop.png"), 3)
        browser.evaluate(CLICK_TAB % "profile")
        browser.shot(out("10-profil-desktop.png"), 3)
        browser.goto(base + "/#admin", 7)
        browser.shot(out("11-admin-widok-desktop.png"), 2)
        browser.evaluate("localStorage.setItem('bp.theme', '\"dark\"'); 'ok'")
        browser.goto(base + "/", 7)
        browser.shot(out("12-mapa-noc-desktop.png"))
        browser.evaluate("localStorage.setItem('bp.theme', '\"light\"'); 'ok'")

        browser.metrics(390, 844, mobile=True, scale=2)
        browser.goto(base + "/", 7)
        browser.shot(out("13-mapa-mobile.png"))
        browser.goto(f"{base}/#place-{PLACE_IDS['karta-miejsca']}", 5)
        browser.shot(out("14-karta-mobile.png"), 2)
        browser.evaluate(CLICK_TAB % "places")
        browser.shot(out("15-miejsca-mobile.png"), 3)
        # Karta z samymi udogodnieniami: bez profilu potrzeb, za to z preferencjami, które miejsce spełnia.
        browser.evaluate(
            "localStorage.setItem('bp.needs', '[]'); localStorage.setItem('bp.prefs', %s); 'ok'"
            % json.dumps(json.dumps(POSITIVE_PREFS))
        )
        browser.goto(base + "/", 6)  # pełne przeładowanie: aplikacja czyta pamięć lokalną przy starcie
        browser.goto(f"{base}/#place-{PLACE_IDS['karta-pozytywna']}", 5)
        browser.shot(out("14-karta-pozytywna-mobile.png"), 2)
        browser.evaluate("localStorage.setItem('bp.needs', JSON.stringify(['wheelchair'])); localStorage.removeItem('bp.prefs'); 'ok'")

        browser.metrics(1440, 900)
        browser.goto(base + "/", 4)
        print("logowanie kasia@:", browser.evaluate(SIGN_IN % {"email": "kasia@accessly.test"}, wait=True))
        browser.goto(base + "/owner.html", 6)
        browser.shot(out("16-panel-wlasciciela.png"), 2)
        browser.evaluate("fetch('/api/auth/logout', {method: 'POST'}).then(r => r.status)", wait=True)
        browser.goto(base + "/", 4)
        print("logowanie admin@:", browser.evaluate(SIGN_IN % {"email": "admin@accessly.test"}, wait=True))
        browser.goto(base + "/admin", 7)
        browser.shot(out("18-panel-admina.png"), 2)
        browser.evaluate("fetch('/api/auth/logout', {method: 'POST'}).then(r => r.status)", wait=True)
        browser.goto(base + "/sources.html", 5)
        browser.shot(out("19-zrodla-danych.png"), 1)
    finally:
        browser.close()
    print("gotowe:", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
