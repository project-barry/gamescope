#!/usr/bin/env python3
"""Headless checks for gamescope's bottom screen (dual-screen branch).

Runs as gamescope's child (DISPLAY set) with GAMESCOPE_BOTTOM_SCREEN_SIMULATE
on. Imitates emulators' windows and checks, from gamescope's log (GS_LOG)
and the root window's GAMESCOPE_FOCUSED_WINDOW, which window the bottom
screen shows and which one has focus.

Usage: bottomtest.py <scenario>
"""
import os, re, sys, time
from Xlib import X, Xatom, display

LOG = os.environ["GS_LOG"]
d = display.Display()
root = d.screen().root
FOCUSED = d.intern_atom("GAMESCOPE_FOCUSED_WINDOW")
BOTTOM = d.intern_atom("GAMESCOPE_BOTTOM_SCREEN")
NET_WM_NAME = d.intern_atom("_NET_WM_NAME")
UTF8 = d.intern_atom("UTF8_STRING")
failures = []


def log_text():
    with open(LOG, errors="replace") as f:
        return f.read()


def pump(seconds):
    """Let gamescope work, redrawing our windows meanwhile."""
    end = time.time() + seconds
    while time.time() < end:
        for w in list(Win.alive):
            w.draw()
        d.flush()
        time.sleep(0.05)
        while d.pending_events():
            d.next_event()


class Win:
    alive = []

    def __init__(self, title, color, size=(640, 480), transient_for=None):
        scr = d.screen()
        self.color = color
        self.w = root.create_window(0, 0, size[0], size[1], 0, scr.root_depth,
                                    background_pixel=0,
                                    event_mask=X.ExposureMask | X.StructureNotifyMask)
        self.gc = self.w.create_gc(foreground=color)
        self.size = size
        if transient_for:
            self.w.set_wm_transient_for(transient_for.w)
        self.set_title(title)
        self.w.set_wm_class("bottomtest", "BottomTest")

    @property
    def id(self):
        return self.w.id

    def set_title(self, title):
        self.w.set_wm_name(title)
        self.w.change_property(NET_WM_NAME, UTF8, 8, title.encode())
        d.flush()

    def set_bottom_prop(self, on):
        if on:
            self.w.change_property(BOTTOM, Xatom.CARDINAL, 32, [1])
        else:
            self.w.delete_property(BOTTOM)
        d.flush()

    def map(self):
        self.w.map()
        Win.alive.append(self)
        d.flush()

    def unmap(self):
        self.w.unmap()
        if self in Win.alive:
            Win.alive.remove(self)
        d.flush()

    def draw(self):
        # The window's colour, with a white quarter at its top left, to see
        # in the PNG that drawing arrives and which way it is turned.
        w, h = self.size
        self.w.fill_rectangle(self.gc, 0, 0, w, h)
        self.w.fill_rectangle(Win.white_gc(self.w), 0, 0, w // 2, h // 2)

    _white = {}

    @staticmethod
    def white_gc(window):
        if window.id not in Win._white:
            Win._white[window.id] = window.create_gc(foreground=0xFFFFFF)
        return Win._white[window.id]


def focused():
    p = root.get_full_property(FOCUSED, X.AnyPropertyType)
    return p.value[0] if p and len(p.value) else 0


def check(cond, what):
    print(("PASS " if cond else "FAIL ") + what, flush=True)
    if not cond:
        failures.append(what)


def showing_lines(since=0):
    return re.findall(r"bottom-screen: showing (0x[0-9a-f]+) '([^']*)' \((\w+)\)", log_text()[since:])


def mark():
    return len(log_text())


def shown_last(since):
    lines = showing_lines(since)
    return int(lines[-1][0], 16) if lines else None


def gave_back(since):
    return "gave the simulated panel back" in log_text()[since:]


RED, BLUE, GREEN, YELLOW = 0xC03030, 0x3050D0, 0x30A040, 0xD0C030


def scenario_melonds():
    main = Win("[60/60] melonDS 1.0", RED, (512, 384))
    main.map()
    pump(1.5)
    check(focused() == main.id, "melonDS: main window has focus")
    m = mark()
    # melonDS opens the extra window titled like the main one, as a
    # transient child, then prefixes "[w2] " once the game runs.
    second = Win("[60/60] melonDS 1.0", BLUE, (256, 384), transient_for=main)
    second.map()
    pump(1.0)
    check(shown_last(m) is None, "melonDS: an unprefixed window is not taken")
    second.set_title("[w2] [60/60] melonDS 1.0")
    pump(1.5)
    check(shown_last(m) == second.id, "melonDS: the [w2] window is shown on the bottom screen")
    check(focused() == main.id, "melonDS: focus stays on the main window (not the transient [w2])")
    # Titles change every second with the frame rate.
    for fps in range(55, 61):
        main.set_title(f"[w1] [{fps}/60] melonDS 1.0")
        second.set_title(f"[w2] [{fps}/60] melonDS 1.0")
        pump(0.2)
    check(len(showing_lines(m)) == 1, "melonDS: frame-rate title updates don't re-take the screen")
    check(focused() == main.id, "melonDS: focus still on the main window after title updates")
    m = mark()
    second.unmap()
    pump(1.0)
    check(gave_back(m), "melonDS: closing [w2] gives the bottom screen back")
    check(focused() == main.id, "melonDS: main window keeps focus after [w2] closes")


def scenario_azahar():
    main = Win("Azahar 2125.0 | Mario Kart 7", RED, (400, 240))
    main.map()
    pump(1.5)
    m = mark()
    second = Win("Azahar 2125.0 | Mario Kart 7 | Secondary Window", GREEN, (320, 240))
    second.map()
    pump(1.5)
    check(shown_last(m) == second.id, "Azahar: the Secondary Window is shown on the bottom screen")
    check(focused() == main.id, "Azahar: focus stays on the main window")


def scenario_cemu():
    main = Win("Cemu 2.6 - FPS: 30.00 [TitleId: 00050000-10101d00] Mario Kart 8", RED, (854, 480))
    main.map()
    pump(1.5)
    m = mark()
    pad = Win("GamePad View", YELLOW, (854, 480))
    pad.map()
    pump(1.0)
    pad.set_title("GamePad View - FPS: 59.94")
    pump(1.0)
    check(shown_last(m) == pad.id, "Cemu: the GamePad View is shown on the bottom screen")
    check(len(showing_lines(m)) == 1, "Cemu: its FPS title update doesn't re-take the screen")
    check(focused() == main.id, "Cemu: focus stays on the TV window")


def scenario_property_wins():
    main = Win("[60/60] melonDS 1.0", RED, (512, 384))
    main.map()
    pump(1.0)
    second = Win("[w2] [60/60] melonDS 1.0", BLUE, (256, 384), transient_for=main)
    second.map()
    pump(1.5)
    m = mark()
    barry = Win("Barry Launcher", GREEN, (540, 620))
    barry.set_bottom_prop(True)
    barry.map()
    pump(1.5)
    check(shown_last(m) == barry.id, "property: a GAMESCOPE_BOTTOM_SCREEN window beats a title match")
    m = mark()
    barry.unmap()
    pump(1.5)
    check(shown_last(m) == second.id, "property: the title match is shown again when it closes")
    check(focused() == main.id, "property: focus stays on the main window throughout")


def scenario_disabled():
    # Run with GAMESCOPE_BOTTOM_SCREEN_TITLES set empty.
    main = Win("[60/60] melonDS 1.0", RED, (512, 384))
    main.map()
    pump(1.0)
    m = mark()
    second = Win("[w2] [60/60] melonDS 1.0", BLUE, (256, 384))
    second.map()
    pump(1.5)
    check(shown_last(m) is None, "disabled: with the titles set empty nothing is taken")


def scenario_stress():
    main = Win("[60/60] melonDS 1.0", RED, (512, 384))
    main.map()
    pump(1.0)
    second = Win("[w2] [60/60] melonDS 1.0", BLUE, (256, 384), transient_for=main)
    for i in range(150):
        second.map()
        pump(0.02 if i % 3 else 0.1)
        second.unmap()
        pump(0.01)
    # Title flips in and out of matching while mapped.
    second.map()
    for i in range(100):
        second.set_title("[w2] [60/60] melonDS 1.0" if i % 2 else "[60/60] melonDS 1.0")
        pump(0.02)
    second.set_title("[w2] [60/60] melonDS 1.0")
    pump(1.5)
    check(focused() == main.id, "stress: main window has focus after 150 open/close cycles")
    m = mark()
    pump(1.0)
    check("bottom-screen" in log_text(), "stress: gamescope still running and logging")
    second.unmap()
    pump(1.0)
    check(gave_back(m), "stress: the screen is given back at the end")


def read_png(path):
    """RGBA rows of an 8-bit, non-interlaced PNG (as stb_image_write makes)."""
    import struct, zlib
    data = open(path, "rb").read()
    pos, idat, width, height = 8, b"", 0, 0
    while pos < len(data):
        n, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + n]
        if kind == b"IHDR":
            width, height = struct.unpack(">II", body[:8])
        elif kind == b"IDAT":
            idat += body
        pos += 12 + n
    raw, bpp, stride = zlib.decompress(idat), 4, width * 4
    rows, prev = [], bytearray(stride)
    for y in range(height):
        f = raw[y * (stride + 1)]
        line = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride):
            a = line[i - bpp] if i >= bpp else 0
            b, c = prev[i], (prev[i - bpp] if i >= bpp else 0)
            if f == 1: line[i] = (line[i] + a) & 255
            elif f == 2: line[i] = (line[i] + b) & 255
            elif f == 3: line[i] = (line[i] + (a + b) // 2) & 255
            elif f == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append(line)
        prev = line
    return width, height, rows


def pixel(img, x, y):
    w, h, rows = img
    return tuple(rows[y][x * 4:x * 4 + 3])


def near(rgb, want, tol=4):
    return all(abs(a - b) <= tol for a, b in zip(rgb, want))


def scenario_png():
    # A still frame for checking the fit and turn by eye.
    main = Win("[60/60] melonDS 1.0", RED, (512, 384))
    main.map()
    pump(1.0)
    second = Win("[w2] [60/60] melonDS 1.0", BLUE, (256, 192), transient_for=main)
    second.map()
    pump(3.0)
    path = os.environ.get("GAMESCOPE_BOTTOM_SCREEN_SIMULATE_PNG", "/nonexistent")
    check(os.path.exists(path), "png: the simulated panel's frame was saved")
    if not os.path.exists(path):
        return
    # Under a headless gamescope, Xwayland's shm buffers now and then arrive
    # empty (black), on the main output too; wait for a frame with content.
    for _ in range(20):
        img = read_png(path)
        if pixel(img, 300, 900) != (0, 0, 0):
            break
        pump(0.5)
    # The panel is 1080x1240, turned one step back (rotation 3): the
    # 256x192 window fills its 1240x1080 logical space as 1240x930, i.e.
    # 930 wide and centred in the buffer, its top left at the buffer's top
    # right.
    check(img[:2] == (1080, 1240), f"png: the frame is the panel's size (got {img[0]}x{img[1]})")
    blue = (0x30, 0x50, 0xD0)
    check(near(pixel(img, 300, 900), blue), f"png: the window's colour is kept, not darkened (got {pixel(img, 300, 900)})")
    check(near(pixel(img, 780, 300), (255, 255, 255)), "png: the window's top left lands at the buffer's top right")
    check(near(pixel(img, 300, 300), blue) and near(pixel(img, 780, 900), blue), "png: the other quarters are the window's colour")
    check(near(pixel(img, 30, 600), (0, 0, 0)) and near(pixel(img, 1050, 600), (0, 0, 0)), "png: black bars at the sides")


if __name__ == "__main__":
    name = sys.argv[1]
    try:
        globals()["scenario_" + name]()
    except Exception as e:  # a crash of gamescope shows up here too
        check(False, f"{name}: exception {e!r}")
    print(f"RESULT {name}: {'FAIL' if failures else 'PASS'} ({len(failures)} failed)", flush=True)
    sys.exit(1 if failures else 0)
