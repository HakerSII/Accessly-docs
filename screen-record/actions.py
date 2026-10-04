"""Sterownik demonstracji: „ręka” na stronie Accessly (tylko biblioteka standardowa).

Steruje jedną kartą przez CDP (``cdp.Tab``): wstrzykuje do strony nakładkę
(animowany kursor, kółko kliknięcia, pasek z podpisem kroku), klika i pisze
prawdziwymi zdarzeniami wejścia (``Input.*``), przeciąga mapę, wybiera pliki
bez okna systemowego i czeka na warunki w DOM. Każdy podpis zapisuje też
znacznik czasu do listy rozdziałów (``chapters``), z której ``record.py``
robi plik JSON i napisy WebVTT.
"""

import json
import math
import os
import random
import struct
import time
import zlib

# Nakładka dodawana do każdej strony (po każdej nawigacji od nowa): kursor, kółko kliknięcia i podpis.
# Elementy mają data-no-i18n, więc tłumacz interfejsu (i18n.js) ich nie dotyka.
OVERLAY_JS = r"""
(() => {
  if (document.getElementById('__demoCursor')) return 'ok';
  const style = document.createElement('style');
  style.id = '__demoStyle';
  style.textContent = `
    #__demoCursor { position: fixed; left: 0; top: 0; width: 28px; height: 28px; z-index: 2147483647;
      pointer-events: none; transform: translate(-3px, -2px); filter: drop-shadow(0 2px 3px rgba(0,0,0,.5));
      transition: transform .08s; }
    #__demoCursor.down { transform: translate(-3px, -2px) scale(.82); }
    #__demoRipple { position: fixed; width: 44px; height: 44px; margin: -22px 0 0 -22px; border-radius: 50%;
      border: 3px solid #FFB703; z-index: 2147483646; pointer-events: none; opacity: 0; }
    #__demoRipple.go { animation: __demoRip .55s ease-out; }
    @keyframes __demoRip { 0% { transform: scale(.3); opacity: .95 } 100% { transform: scale(1.5); opacity: 0 } }
    #__demoCaption { position: fixed; bottom: 26px; z-index: 2147483645; pointer-events: none;
      background: rgba(8, 24, 52, .93); color: #fff; padding: 13px 22px 15px; border-radius: 14px;
      font: 500 20px/1.35 "Atkinson Hyperlegible Next", "Segoe UI", system-ui, sans-serif;
      box-shadow: 0 8px 30px rgba(0,0,0,.35); opacity: 0; transition: opacity .35s; text-align: center;
      transform: translateX(-50%); }
    #__demoCaption.show { opacity: 1; }
    #__demoCaption small { display: block; font-size: 13px; letter-spacing: .08em; text-transform: uppercase;
      color: #FFB703; margin-bottom: 3px; font-weight: 700; }
    #__demoCaption.big { font-size: 28px; padding: 22px 34px; }
  `;
  document.head.appendChild(style);
  const cur = document.createElement('div');
  cur.id = '__demoCursor'; cur.setAttribute('data-no-i18n', ''); cur.setAttribute('aria-hidden', 'true');
  cur.innerHTML = '<svg viewBox="0 0 24 24" width="28" height="28"><path d="M5 3l14 8.5-6.2 1.3L16 19.5l-2.6 1.2-3.2-6.7L5.5 18z" fill="#fff" stroke="#111" stroke-width="1.6" stroke-linejoin="round"/></svg>';
  const rip = document.createElement('div');
  rip.id = '__demoRipple'; rip.setAttribute('aria-hidden', 'true');
  const cap = document.createElement('div');
  cap.id = '__demoCaption'; cap.setAttribute('data-no-i18n', ''); cap.setAttribute('aria-hidden', 'true');
  document.body.append(cur, rip, cap);
  const pos = window.__demoPos || [innerWidth / 2, innerHeight / 2];
  window.__demoPos = pos;
  cur.style.left = pos[0] + 'px'; cur.style.top = pos[1] + 'px';
  window.__demoMove = (x, y, ms) => new Promise((resolve) => {
    const [x0, y0] = window.__demoPos; const t0 = performance.now();
    const step = (now) => {
      const k = Math.min(1, (now - t0) / Math.max(ms, 1));
      const e = k < .5 ? 2 * k * k : -1 + (4 - 2 * k) * k;
      cur.style.left = (x0 + (x - x0) * e) + 'px'; cur.style.top = (y0 + (y - y0) * e) + 'px';
      if (k < 1) requestAnimationFrame(step); else { window.__demoPos = [x, y]; resolve(); }
    };
    requestAnimationFrame(step);
  });
  window.__demoClick = () => {
    cur.classList.add('down'); setTimeout(() => cur.classList.remove('down'), 120);
    const [x, y] = window.__demoPos;
    rip.style.left = x + 'px'; rip.style.top = y + 'px';
    rip.classList.remove('go'); void rip.offsetWidth; rip.classList.add('go');
  };
  // Podpis nad mapą (na desktopie obok kolumny bocznej), poza przyciskiem „Zgłoś problem” w prawym dolnym rogu.
  window.__demoCaption = (kicker, text, big) => {
    if (!text) { cap.classList.remove('show'); return; }
    const side = document.getElementById('sheet') && innerWidth >= 900 ? Math.min(420, innerWidth / 2) : 0;
    const width = innerWidth - side;
    cap.style.left = (side + width / 2) + 'px';
    cap.style.maxWidth = Math.max(320, width - (side ? 230 : 80)) + 'px';
    cap.classList.toggle('big', Boolean(big));
    cap.innerHTML = (kicker ? '<small></small>' : '') + '<span></span>';
    if (kicker) cap.querySelector('small').textContent = kicker;
    cap.querySelector('span').textContent = text;
    cap.classList.add('show');
  };
  window.__demoFind = (spec) => {
    let root = document;
    if (spec.within) { root = document.querySelector(spec.within); if (!root) return null; }
    let list = [...root.querySelectorAll(spec.sel)];
    if (spec.text) {
      const t = spec.text.toLowerCase();
      list = list.filter((e) => (e.textContent || '').replace(/\s+/g, ' ').trim().toLowerCase().includes(t));
    }
    list = list.filter((e) => { const r = e.getBoundingClientRect(); return (r.width > 0 || r.height > 0) && !e.closest('[hidden]'); });
    return list[spec.index || 0] || null;
  };
  window.__demoSettle = (spec) => new Promise((resolve) => {
    // Przewiń natychmiast (płynne przewijanie dawało wyścig z pomiarem), potem czekaj, aż pozycja nie zmienia się
    // przez trzy klatki (strona mogła się przerysować), najwyżej 0,8 s.
    const el = window.__demoFind(spec);
    if (!el) return resolve(null);
    const inView = (r) => r.top >= 60 && r.bottom <= innerHeight - 110;
    const tall = (r) => r.height > innerHeight - 170;
    const pack = (r) => ({ x: r.left, y: r.top, w: r.width, h: r.height, vw: innerWidth, vh: innerHeight, out: !inView(r) });
    const first = el.getBoundingClientRect();
    if (!inView(first) && !tall(first)) el.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
    let last = null, same = 0; const t0 = performance.now();
    const tick = () => {
      const r = el.getBoundingClientRect();
      if (last !== null && Math.abs(r.top - last) < 0.5 && Math.abs(r.left - (window.__demoLastLeft || r.left)) < 0.5) same += 1; else same = 0;
      last = r.top; window.__demoLastLeft = r.left;
      if (same >= 2 || performance.now() - t0 > 800) return resolve(pack(r));
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });
  window.__demoRect = (spec, mode) => {
    const el = window.__demoFind(spec);
    if (!el) return null;
    let r = el.getBoundingClientRect();
    const out = r.top < 60 || r.bottom > innerHeight - 110;
    if (mode === 'smooth' && out) el.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'smooth' });
    else if (mode === 'instant' && out) el.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
    r = el.getBoundingClientRect();
    return { x: r.left, y: r.top, w: r.width, h: r.height, vw: innerWidth, vh: innerHeight, out };
  };
  return 'ok';
})()
"""


class StepError(RuntimeError):
    """Krok demonstracji nie mógł znaleźć elementu albo doczekać się warunku."""


class Demo:
    """Jedna karta aplikacji sterowana jak ręką użytkownika.

    ``speed`` > 1 skraca pauzy (nagranie szybsze), < 1 wydłuża. ``lang`` wybiera
    język podpisów (``pl`` albo ``en``); ``persona`` to etykieta nad podpisem.
    """

    def __init__(self, tab, base, lang="pl", speed=1.0, captions=True, log=print, shots_dir=None):
        self.tab = tab
        self.base = base.rstrip("/")
        self.lang = lang
        self.speed = max(0.2, speed)
        self.captions = captions
        self.log = log
        self.shots_dir = shots_dir
        self.persona = ""
        self.current_step = ""
        self.chapters = []
        self.t0 = None
        self.pos = (640, 360)
        self.rng = random.Random(7)

    # ---------- czas ----------

    def elapsed(self):
        """Sekundy od startu nagrania (0, gdy nagranie jeszcze nie trwa)."""
        return 0.0 if self.t0 is None else time.monotonic() - self.t0

    def sleep(self, seconds):
        """Pauza skalowana przez ``speed``."""
        time.sleep(max(0.0, seconds) / self.speed)

    # ---------- JS i nakładka ----------

    def js(self, expression, wait=False, timeout=None):
        """Wykonaj JS w stronie."""
        return self.tab.evaluate(expression, wait=wait, timeout=timeout)

    def ensure_overlay(self):
        """Dodaj nakładkę, jeśli strona jej nie ma (po nawigacji, przeładowaniu)."""
        x, y = self.pos
        self.js(f"window.__demoPos = window.__demoPos || [{x:.0f}, {y:.0f}];" + OVERLAY_JS)

    def wait_ready(self, condition="true", timeout=20):
        """Poczekaj, aż strona ma body i spełnia warunek JS (skrypty aplikacji już zadziałały), potem dodaj nakładkę.

        Nie czekamy na ``readyState === 'complete'``: czcionki i kafelki z sieci potrafią opóźnić ``load``
        o dziesiątki sekund, a interfejs jest gotowy wcześniej.
        """
        # !!(…): warunek często zwraca węzeł DOM, a CDP serializuje go do pustego obiektu (fałszywego w Pythonie).
        self.wait_for(f"!!(document.body && document.readyState !== 'loading' && ({condition}))", timeout=timeout, desc="wczytanie strony")
        self.ensure_overlay()
        self.sleep(0.3)

    def goto(self, path, condition="true", timeout=30):
        """Przejdź pod adres (ścieżka w aplikacji albo pełny URL) i poczekaj, aż nowy dokument spełnia warunek.

        Nie czekamy na zdarzenie ``load``: czcionki, CDN i zdalne instancje potrafią opóźnić je o kilkanaście
        sekund, a interfejs jest gotowy wcześniej. Znacznik w starym dokumencie odróżnia go od nowego.
        """
        url = path if "://" in path else self.base + path
        try:
            self.js("window.__demoNavMark = true; 'ok'")
        except Exception:  # pylint: disable=broad-except  # np. about:blank bez kontekstu: znacznik nie jest potrzebny
            pass
        self.tab.call("Page.navigate", url=url)
        self.wait_for(f"!window.__demoNavMark && !!(document.body && document.readyState !== 'loading' && ({condition}))",
                      timeout=timeout, desc="wczytanie strony")
        self.ensure_overlay()
        self.sleep(0.3)

    def reload_wait(self, condition="true", timeout=30):
        """Po przeładowaniu wywołanym przez stronę (np. zmiana języka): poczekaj na nowy dokument i dodaj nakładkę."""
        self.wait_for("!document.getElementById('__demoCursor')", timeout=timeout, desc="przeładowanie strony (zniknięcie nakładki)")
        self.wait_ready(condition, timeout=timeout)

    # ---------- czekanie ----------

    def wait_for(self, expression, timeout=15, every=0.15, desc=None):
        """Czekaj, aż wyrażenie JS będzie prawdziwe; zwróć jego wartość."""
        deadline = time.monotonic() + timeout
        last_error = None
        while time.monotonic() < deadline:
            try:
                value = self.js(expression)
                if value == {}:  # węzeł DOM albo inny obiekt bez wartości: CDP oddaje pusty słownik, a istnienie to prawda
                    value = True
                if value:
                    return value
            except Exception as e:  # pylint: disable=broad-except  # strona może być w trakcie przeładowania
                last_error = e
            time.sleep(every)
        raise StepError(f"nie doczekano się: {desc or expression[:80]}" + (f" ({last_error})" if last_error else ""))

    def wait_visible(self, spec, timeout=15):
        """Czekaj, aż element będzie w DOM i widoczny."""
        spec = _spec(spec)
        return self.wait_for(f"!!window.__demoFind({json.dumps(spec)})", timeout=timeout, desc=f"element {spec['sel']}")

    def wait_hidden(self, selector, timeout=15):
        """Czekaj, aż elementu nie będzie albo będzie ukryty."""
        return self.wait_for(
            f"(() => {{ const e = document.querySelector({json.dumps(selector)}); return !e || e.hidden || e.closest('[hidden]') || e.getBoundingClientRect().height === 0; }})()",
            timeout=timeout, desc=f"ukrycie {selector}")

    def wait_toast(self, timeout=8):
        """Czekaj na komunikat (toast) i zwróć jego tekst."""
        return self.wait_for("(() => { const t = document.getElementById('toast'); return t && !t.hidden && t.textContent.trim(); })()",
                             timeout=timeout, desc="komunikat")

    def exists(self, spec):
        """Czy element jest w DOM i widoczny."""
        return bool(self.js(f"!!window.__demoFind({json.dumps(_spec(spec))})"))

    def text(self, selector):
        """Tekst elementu (albo pusty)."""
        return self.js(f"(document.querySelector({json.dumps(selector)}) || {{}}).textContent || ''") or ""

    # ---------- podpisy i rozdziały ----------

    def step(self, step_id, persona=None):
        """Zacznij krok: ustaw etykietę i zapisz rozdział."""
        self.current_step = step_id
        if persona is not None:
            self.persona = persona
        self.log(f"[{self.elapsed():7.1f}s] krok {step_id}")
        self.chapters.append({"t": round(self.elapsed(), 2), "step": step_id, "kind": "step", "kicker": self.persona, "text": ""})

    def caption(self, pl, en=None, hold=0.0, big=False):
        """Pokaż podpis (PL albo EN według ``lang``) i zapisz go do rozdziałów."""
        text = en if (self.lang != "pl" and en) else pl
        if self.captions:
            self.ensure_overlay()
            self.js(f"window.__demoCaption({json.dumps(self.persona)}, {json.dumps(text)}, {json.dumps(bool(big))})")
        self.chapters.append({"t": round(self.elapsed(), 2), "step": self.current_step, "kind": "caption", "kicker": self.persona, "text": text})
        if hold:
            self.sleep(hold)

    def caption_off(self):
        """Schowaj podpis."""
        if self.captions:
            self.js("window.__demoCaption && window.__demoCaption('', '')")
        self.chapters.append({"t": round(self.elapsed(), 2), "step": self.current_step, "kind": "caption", "kicker": "", "text": ""})

    # ---------- mysz ----------

    def _mouse(self, kind, x, y, **extra):
        params = dict(type=kind, x=float(x), y=float(y), **extra)
        self.tab.call("Input.dispatchMouseEvent", **params)

    def move_to(self, x, y, duration=0.5):
        """Przesuń kursor (nakładka + prawdziwe zdarzenia ``mouseMoved`` po drodze)."""
        x0, y0 = self.pos
        ms = int(duration * 1000 / self.speed)
        self.ensure_overlay()
        self.js(f"window.__demoMove({x:.1f}, {y:.1f}, {ms})")
        steps = max(2, min(10, int(math.hypot(x - x0, y - y0) / 60)))
        for i in range(1, steps + 1):
            k = i / steps
            e = 2 * k * k if k < 0.5 else -1 + (4 - 2 * k) * k
            self._mouse("mouseMoved", x0 + (x - x0) * e, y0 + (y - y0) * e)
            time.sleep(ms / 1000 / steps)
        self.pos = (x, y)
        time.sleep(0.05)

    def rect(self, spec, scroll=True, timeout=10):
        """Prostokąt elementu, gdy jest w widoku i nieruchomy (po przewinięciu); wyjątek, gdy go nie ma.

        Pomiar w trakcie płynnego przewijania albo tuż przed jego startem dawał kliknięcia w sąsiednie
        elementy, dlatego czekamy, aż pozycja nie zmienia się przez trzy klatki (__demoSettle w stronie).
        """
        spec = _spec(spec)
        self.wait_visible(spec, timeout=timeout)
        if not scroll:
            r = self.js(f"window.__demoRect({json.dumps(spec)}, 'none')")
        else:
            r = self.js(f"window.__demoSettle({json.dumps(spec)})", wait=True, timeout=5)
        if not r:
            raise StepError(f"brak elementu {spec}")
        return r

    def hover(self, spec, duration=0.5, pause=0.3):
        """Najedź na element."""
        r = self.rect(spec)
        self.move_to(r["x"] + r["w"] / 2, r["y"] + min(r["h"] / 2, 60), duration)
        self.sleep(pause)
        return r

    def click(self, spec, pause=0.5, duration=0.5, dx=0.5, dy=0.5):
        """Kliknij element (``dx``/``dy``: punkt w elemencie jako ułamek szerokości/wysokości)."""
        r = self.rect(spec)
        x = r["x"] + r["w"] * dx
        y = r["y"] + min(r["h"] * dy, 60 if dy == 0.5 else r["h"] * dy)
        hit = self.js(
            f"(() => {{ const el = window.__demoFind({json.dumps(_spec(spec))}); const at = document.elementFromPoint({x:.1f}, {y:.1f});"
            " if (!at || !el) return 'brak'; if (el === at || el.contains(at) || at.contains(el)) return '';"
            " return at.tagName.toLowerCase() + (at.id ? '#' + at.id : '') + (at.className && typeof at.className === 'string' ? '.' + at.className.split(' ')[0] : ''); })()"
        )
        if hit:
            self.log(f"uwaga: klik w {_spec(spec)['sel']} trafia w {hit}")
        covered = self.captions and self.js(
            f"(() => {{ const c = document.getElementById('__demoCaption'); if (!c || !c.classList.contains('show')) return false;"
            f" const b = c.getBoundingClientRect(); return {x:.1f} >= b.left - 8 && {x:.1f} <= b.right + 8 && {y:.1f} >= b.top - 8 && {y:.1f} <= b.bottom + 8; }})()"
        )
        if covered:
            self.js("document.getElementById('__demoCaption').classList.remove('show')")
        self.move_to(x, y, duration)
        again = self.js(f"window.__demoRect({json.dumps(_spec(spec))}, 'none')")
        if again and (abs(again["x"] - r["x"]) > 2 or abs(again["y"] - r["y"]) > 2):
            x = again["x"] + again["w"] * dx
            y = again["y"] + min(again["h"] * dy, 60 if dy == 0.5 else again["h"] * dy)
            self.move_to(x, y, 0.15)
        self.click_at(x, y, pause=pause, duration=0)
        if covered:
            self.js("document.getElementById('__demoCaption').classList.add('show')")
        return r

    def click_at(self, x, y, pause=0.5, duration=0.5):
        """Kliknij w punkt viewportu (``duration`` 0: kursor już tam jest)."""
        if duration:
            self.move_to(x, y, duration)
        self.js("window.__demoClick && window.__demoClick()")
        self._mouse("mousePressed", x, y, button="left", clickCount=1, buttons=1)
        time.sleep(0.07)
        self._mouse("mouseReleased", x, y, button="left", clickCount=1, buttons=0)
        self.sleep(pause)

    def drag(self, x0, y0, x1, y1, duration=0.9, steps=14, pause=0.4):
        """Przeciągnij lewym przyciskiem (np. mapę)."""
        self.move_to(x0, y0, 0.4)
        self._mouse("mousePressed", x0, y0, button="left", clickCount=1, buttons=1)
        ms = duration / self.speed
        self.js(f"window.__demoMove({x1:.1f}, {y1:.1f}, {int(ms * 1000)})")
        for i in range(1, steps + 1):
            k = i / steps
            e = 2 * k * k if k < 0.5 else -1 + (4 - 2 * k) * k
            self._mouse("mouseMoved", x0 + (x1 - x0) * e, y0 + (y1 - y0) * e, button="left", buttons=1)
            time.sleep(ms / steps)
        self._mouse("mouseReleased", x1, y1, button="left", clickCount=1, buttons=0)
        self.pos = (x1, y1)
        self.sleep(pause)

    def wheel(self, x, y, delta_y, pause=0.6):
        """Kółko myszy w punkcie (np. zoom mapy: ujemne przybliża)."""
        self.move_to(x, y, 0.3)
        self._mouse("mouseWheel", x, y, deltaX=0, deltaY=float(delta_y))
        self.sleep(pause)

    # ---------- klawiatura ----------

    def type_text(self, text, per_char=0.045):
        """Pisz znak po znaku do aktywnego pola (``Input.insertText`` obsługuje polskie znaki)."""
        for ch in text:
            self.tab.call("Input.insertText", text=ch)
            time.sleep((per_char + self.rng.uniform(-0.015, 0.03)) / self.speed if ch != " " else per_char / self.speed)

    def fill(self, spec, text, clear=True, pause=0.3):
        """Kliknij pole, wyczyść je i wpisz tekst."""
        self.click(spec, pause=0.15)
        if clear:
            self.key("a", ctrl=True)
            self.key("Backspace")
        self.type_text(text)
        self.sleep(pause)

    def key(self, name, ctrl=False):
        """Naciśnij klawisz (Enter, Escape, Tab, Backspace, litera)."""
        codes = {"Enter": (13, "Enter", "\r"), "Escape": (27, "Escape", ""), "Tab": (9, "Tab", ""), "Backspace": (8, "Backspace", ""),
                 "ArrowDown": (40, "ArrowDown", ""), " ": (32, "Space", " ")}
        vk, code, text = codes.get(name, (ord(name.upper()) if len(name) == 1 else 0, f"Key{name.upper()}" if len(name) == 1 else name, name if len(name) == 1 else ""))
        mods = 2 if ctrl else 0
        down = dict(type="keyDown", key=name, code=code, windowsVirtualKeyCode=vk, modifiers=mods)
        if text and not ctrl:
            down.update(text=text, unmodifiedText=text)
        self.tab.call("Input.dispatchKeyEvent", **down)
        self.tab.call("Input.dispatchKeyEvent", type="keyUp", key=name, code=code, windowsVirtualKeyCode=vk, modifiers=mods)
        time.sleep(0.05)

    def select_value(self, spec, value, pause=0.4):
        """Ustaw wartość ``<select>`` (najazd kursorem, a wartość przez JS, bo natywnej listy nie da się nagrać)."""
        self.hover(spec, pause=0.1)
        spec = _spec(spec)
        self.js(
            f"(() => {{ const el = window.__demoFind({json.dumps(spec)}); el.value = {json.dumps(value)};"
            " el.dispatchEvent(new Event('input', {bubbles: true})); el.dispatchEvent(new Event('change', {bubbles: true})); return el.value; })()"
        )
        self.sleep(pause)

    # ---------- pliki ----------

    def choose_file(self, click_spec, path, timeout=6):
        """Kliknij przycisk wyboru pliku i podstaw plik bez okna systemowego."""
        self.tab.call("Page.setInterceptFileChooserDialog", enabled=True)
        self.tab.ws.drop_events("Page.fileChooserOpened")
        try:
            self.click(click_spec, pause=0.2)
            ev = self.tab.ws.wait_event("Page.fileChooserOpened", timeout=timeout)
            self.tab.call("DOM.setFileInputFiles", files=[os.path.abspath(path)], backendNodeId=ev["backendNodeId"])
        finally:
            self.tab.call("Page.setInterceptFileChooserDialog", enabled=False)

    def set_files(self, selector, path):
        """Podstaw plik do ``<input type=file>`` bez klikania."""
        doc = self.tab.call("DOM.getDocument", depth=0)["root"]["nodeId"]
        node = self.tab.call("DOM.querySelector", nodeId=doc, selector=selector)["nodeId"]
        self.tab.call("DOM.setFileInputFiles", files=[os.path.abspath(path)], nodeId=node)

    # ---------- mapa ----------

    def map_point(self, lat, lng, map_expr="map"):
        """Współrzędne viewportu punktu mapy Leaflet (``map_expr``: wyrażenie JS z mapą)."""
        return self.js(
            f"(() => {{ const m = {map_expr}; const r = m.getContainer().getBoundingClientRect();"
            f" const p = m.latLngToContainerPoint([{lat}, {lng}]); return [r.left + p.x, r.top + p.y]; }})()"
        )

    def map_center_point(self, map_expr="map"):
        """Środek kontenera mapy w viewportcie."""
        return self.js(
            f"(() => {{ const r = {map_expr}.getContainer().getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }})()"
        )

    # ---------- diagnostyka ----------

    def screenshot(self, name):
        """Zrzut karty do katalogu ``shots_dir`` (jeśli ustawiony)."""
        if not self.shots_dir:
            return None
        os.makedirs(self.shots_dir, exist_ok=True)
        path = os.path.join(self.shots_dir, f"{name}.png")
        try:
            self.tab.screenshot(path)
        except Exception as e:  # pylint: disable=broad-except  # zrzut jest tylko pomocą w diagnozie
            self.log(f"zrzut nieudany: {e}")
            return None
        return path


def _spec(spec):
    """Specyfikacja elementu: selektor CSS albo słownik ``{sel, text?, index?, within?}``."""
    if isinstance(spec, str):
        return {"sel": spec}
    return dict(spec)


def make_photo(path, width=960, height=720, seed=1):
    """Zapisz syntetyczne „zdjęcie wejścia do lokalu” jako PNG (bez bibliotek graficznych).

    Niebo z gradientem, ściana, drzwi i podjazd: wystarczy, żeby pokazać przesyłanie
    i moderację zdjęć bez użycia cudzych fotografii.
    """
    rnd = random.Random(seed)
    wall = (214 - rnd.randint(0, 40), 190 - rnd.randint(0, 30), 160 - rnd.randint(0, 30))
    door = (72, 48, 32)
    ramp = (120, 120, 124)
    sky_top, sky_bottom = (122, 170, 226), (205, 226, 246)
    horizon = int(height * 0.42)
    door_x0, door_x1 = int(width * 0.42), int(width * 0.58)
    door_y0 = int(height * 0.46)
    floor_y = int(height * 0.88)
    rows = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            if y < horizon:
                k = y / horizon
                c = tuple(int(a + (b - a) * k) for a, b in zip(sky_top, sky_bottom))
            elif y >= floor_y:
                c = (96, 96, 98) if (x // 40 + y // 20) % 2 else (104, 104, 106)
            elif door_x0 <= x < door_x1 and y >= door_y0:
                c = door if not (door_x0 + 18 <= x < door_x1 - 18 and door_y0 + 18 <= y < door_y0 + 110) else (160, 196, 220)
            elif door_x1 <= x < door_x1 + int(width * 0.22) and y >= floor_y - int((x - door_x1) * 0.28):
                c = ramp
            else:
                shade = 0 if (y // 24) % 2 == 0 else -10
                c = tuple(max(0, v + shade) for v in wall)
            row += bytes(c)
        rows.append(bytes(row))
    raw = b"".join(rows)

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return path
