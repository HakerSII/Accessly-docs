"""Minimalny klient Chrome DevTools Protocol – tylko biblioteka standardowa.

Uruchamia Chrome/Edge z portem debugowania, łączy się z przeglądarką
(``Target.*``, ``Browser.*``) i z pojedynczymi kartami (``Page.*``, ``Runtime.*``,
``Input.*``, ``DOM.*``). Zdarzenia są kolejkowane, więc można na nie czekać
(``wait_event``). Używany przez ``record.py``.
"""

import base64
import json
import os
import socket
import struct
import subprocess
import time
import urllib.request

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


def find_chrome():
    """Pierwsza istniejąca przeglądarka z listy kandydatów (albo $CHROME)."""
    env = os.environ.get("CHROME")
    if env and os.path.exists(env):
        return env
    for path in CHROME_CANDIDATES:
        if os.path.exists(path):
            return path
    raise SystemExit("Nie znaleziono Chrome/Edge; podaj --chrome ŚCIEŻKA")


class CdpError(RuntimeError):
    """Błąd zgłoszony przez protokół (np. nieznana metoda, zły parametr)."""


class WebSocket:
    """Klient WebSocket (RFC 6455) wystarczający dla CDP: ramki tekstowe, ping/pong, kolejka zdarzeń."""

    def __init__(self, url, timeout=30.0):
        rest = url.split("://", 1)[1]
        hostport, path = rest.split("/", 1)
        host, port = hostport.rsplit(":", 1)
        self.sock = socket.create_connection((host, int(port)), timeout=timeout)
        self.timeout = timeout
        key = base64.b64encode(os.urandom(16)).decode()
        request = (
            f"GET /{path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(request.encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise EOFError("uścisk dłoni WebSocket przerwany")
            buf += chunk
        head, self.buf = buf.split(b"\r\n\r\n", 1)
        if b" 101 " not in head.split(b"\r\n", 1)[0]:
            raise EOFError("Chrome odrzucił połączenie WebSocket: " + head.decode(errors="replace"))
        self.next_id = 0
        self.events = []
        self.closed = False

    def _exact(self, n):
        while len(self.buf) < n:
            chunk = self.sock.recv(1 << 20)
            if not chunk:
                self.closed = True
                raise EOFError("połączenie zamknięte")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def send_text(self, text):
        """Wyślij jedną zamaskowaną ramkę tekstową."""
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
        masked = bytes(b ^ mask[i & 3] for i, b in enumerate(data)) if n < 1 << 16 else _mask_fast(data, mask)
        self.sock.sendall(bytes(header) + masked)

    def recv_text(self):
        """Odbierz jedną wiadomość tekstową (skleja fragmenty, odpowiada na ping)."""
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
                payload = bytes(b ^ mask[i & 3] for i, b in enumerate(payload))
            if opcode == 8:
                self.closed = True
                raise EOFError("Chrome zamknął połączenie")
            if opcode == 9:
                self._pong(payload)
                continue
            if opcode == 10:
                continue
            message += payload
            if fin:
                return message.decode()

    def _pong(self, payload):
        mask = os.urandom(4)
        header = bytearray([0x8A, 0x80 | len(payload)]) + mask
        self.sock.sendall(bytes(header) + bytes(b ^ mask[i & 3] for i, b in enumerate(payload)))

    def call(self, method, _timeout=None, **params):
        """Wywołaj metodę CDP i zwróć ``result``; zdarzenia po drodze trafiają do kolejki.

        ``_timeout`` to limit oczekiwania na odpowiedź (sekundy); nazwa z podkreśleniem,
        bo ``timeout`` bywa parametrem samej metody (np. ``Runtime.evaluate``).
        """
        self.next_id += 1
        my_id = self.next_id
        self.send_text(json.dumps({"id": my_id, "method": method, "params": params}))
        timeout = _timeout or self.timeout
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"{method}: brak odpowiedzi w {timeout:.0f} s")
            self.sock.settimeout(min(remaining, self.timeout))
            try:
                msg = json.loads(self.recv_text())
            except socket.timeout:
                continue  # gniazdo milczy, ale termin jeszcze nie minął (długie awaitPromise)
            if msg.get("id") == my_id:
                if "error" in msg:
                    err = msg["error"]
                    raise CdpError(f"{method}: {err.get('message')} {err.get('data', '')}".strip())
                return msg.get("result", {})
            if "method" in msg:
                self.events.append(msg)

    def pump(self, seconds):
        """Odbieraj zdarzenia przez ``seconds`` sekund (albo krócej, gdy nic nie przychodzi)."""
        deadline = time.monotonic() + seconds
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            self.sock.settimeout(remaining)
            try:
                msg = json.loads(self.recv_text())
            except socket.timeout:
                return
            if "method" in msg:
                self.events.append(msg)

    def wait_event(self, method, timeout=30.0, where=None):
        """Czekaj na zdarzenie ``method`` (opcjonalnie spełniające ``where(params)``) i zwróć jego parametry."""
        deadline = time.monotonic() + timeout
        while True:
            for i, ev in enumerate(self.events):
                if ev["method"] == method and (where is None or where(ev.get("params", {}))):
                    del self.events[i]
                    return ev.get("params", {})
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"zdarzenie {method} nie nadeszło w {timeout:.0f} s")
            self.sock.settimeout(min(remaining, 1.0))
            try:
                msg = json.loads(self.recv_text())
            except socket.timeout:
                continue
            if "method" in msg:
                self.events.append(msg)

    def drop_events(self, method=None):
        """Wyrzuć zebrane zdarzenia (wszystkie albo jednej metody)."""
        self.events = [e for e in self.events if method and e["method"] != method]

    def close(self):
        """Zamknij gniazdo."""
        try:
            self.sock.close()
        except OSError:
            pass


def _mask_fast(data, mask):
    """Maskowanie dużych ramek bez pętli w Pythonie po bajtach (int XOR na całości)."""
    n = len(data)
    full = (mask * (n // 4 + 1))[:n]
    return (int.from_bytes(data, "big") ^ int.from_bytes(full, "big")).to_bytes(n, "big")


class Tab:
    """Jedna karta (cel typu ``page``) sterowana własnym połączeniem WebSocket."""

    def __init__(self, info, timeout=30.0):
        self.id = info["id"]
        self.ws = WebSocket(info["webSocketDebuggerUrl"], timeout=timeout)
        self.ws.call("Page.enable")
        self.ws.call("Runtime.enable")
        self.ws.call("DOM.enable")

    def call(self, method, **params):
        """Metoda CDP na tej karcie."""
        return self.ws.call(method, **params)

    def evaluate(self, expression, wait=False, timeout=None):
        """Wykonaj JS w stronie i zwróć wartość (``wait=True`` czeka na obietnicę)."""
        params = dict(expression=expression, awaitPromise=wait, returnByValue=True, userGesture=True)
        if timeout:
            params["timeout"] = int(timeout * 1000)
        result = self.ws.call("Runtime.evaluate", _timeout=(timeout or 0) + self.ws.timeout, **params)
        if "exceptionDetails" in result:
            det = result["exceptionDetails"]
            text = det.get("exception", {}).get("description") or det.get("text") or "błąd JS"
            raise CdpError(text.splitlines()[0])
        return result.get("result", {}).get("value")

    def navigate(self, url, timeout=30.0):
        """Przejdź pod adres i poczekaj na ``load``."""
        self.ws.drop_events("Page.loadEventFired")
        self.ws.call("Page.navigate", url=url)
        try:
            self.ws.wait_event("Page.loadEventFired", timeout=timeout)
        except TimeoutError:
            pass  # strona może już być wczytana (np. ten sam adres); dalej czekamy na readyState

    def screenshot(self, path):
        """Zapisz zrzut karty jako PNG."""
        data = self.ws.call("Page.captureScreenshot", format="png")["data"]
        with open(path, "wb") as f:
            f.write(base64.b64decode(data))

    def close(self):
        """Zamknij połączenie (karta zostaje)."""
        self.ws.close()


class Browser:
    """Chrome uruchomiony z portem debugowania; połączenie na poziomie przeglądarki."""

    def __init__(self, chrome, profile, args, timeout=30.0):
        self.proc = subprocess.Popen(
            [chrome, "--remote-debugging-port=0", f"--user-data-dir={profile}", *args],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.port = self._wait_port(profile)
        version = self._json("/json/version")
        self.ws = WebSocket(version["webSocketDebuggerUrl"], timeout=timeout)
        self.timeout = timeout

    def _wait_port(self, profile):
        marker = os.path.join(profile, "DevToolsActivePort")
        for _ in range(240):
            if self.proc.poll() is not None:
                raise SystemExit("Chrome zakończył się zaraz po starcie (zły profil albo flagi?)")
            try:
                with open(marker, encoding="utf-8") as f:
                    port = int(f.readline().strip())
                urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2).read()
                return port
            except (OSError, ValueError):
                time.sleep(0.25)
        self.proc.terminate()
        raise SystemExit("Chrome nie wystartował (port debugowania nie odpowiada)")

    def _json(self, path):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=10) as r:
            return json.load(r)

    def targets(self):
        """Lista celów (kart) z /json."""
        return self._json("/json")

    def tab(self, target_id):
        """Połącz się z kartą o danym ID."""
        info = next(t for t in self.targets() if t["id"] == target_id)
        return Tab(info, timeout=self.timeout)

    def first_tab(self):
        """Pierwsza istniejąca karta (ta, którą Chrome otworzył przy starcie)."""
        for _ in range(40):
            pages = [t for t in self.targets() if t["type"] == "page"]
            if pages:
                return Tab(pages[0], timeout=self.timeout)
            time.sleep(0.25)
        raise SystemExit("Chrome nie otworzył żadnej karty")

    def new_tab(self, url, new_window=False, **bounds):
        """Otwórz kartę (opcjonalnie w nowym oknie o podanych ``width``/``height``/``left``/``top``)."""
        params = dict(url=url, newWindow=new_window, **bounds)
        target_id = self.ws.call("Target.createTarget", **params)["targetId"]
        for _ in range(40):
            try:
                return self.tab(target_id)
            except StopIteration:
                time.sleep(0.25)
        raise SystemExit("nowa karta nie pojawiła się na liście celów")

    def window_for(self, tab):
        """ID okna, w którym jest karta."""
        return self.ws.call("Browser.getWindowForTarget", targetId=tab.id)

    def set_bounds(self, tab, **bounds):
        """Ustaw położenie/rozmiar/stan okna karty (``left``, ``top``, ``width``, ``height``, ``windowState``)."""
        window_id = self.window_for(tab)["windowId"]
        if "windowState" not in bounds:
            # Okno zmaksymalizowane nie przyjmuje rozmiaru: najpierw stan normalny.
            self.ws.call("Browser.setWindowBounds", windowId=window_id, bounds={"windowState": "normal"})
        self.ws.call("Browser.setWindowBounds", windowId=window_id, bounds=bounds)

    def grant(self, origin, permissions):
        """Nadaj uprawnienia (np. geolocation) dla źródła."""
        self.ws.call("Browser.grantPermissions", origin=origin, permissions=permissions)

    def close(self):
        """Zamknij przeglądarkę."""
        try:
            self.ws.call("Browser.close", _timeout=5)
        except (OSError, EOFError, TimeoutError, CdpError):
            pass
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.ws.close()
