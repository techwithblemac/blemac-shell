"""
BLEMAC Shell (pygame edition).

One pygame window, no Kivy. The launcher and the games share it, so games
run unmodified: they just get the shell's screen.

Games live in:  Android /sdcard/BlemacShell/games/<game>/   (game.json + main.py)
                Desktop ./games/<game>/
Back button / Esc inside a game returns to the menu.
"""

import os
import sys
import shutil
import traceback
import importlib.util

import pygame

from manifest import scan_games

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ON_ANDROID = "ANDROID_ARGUMENT" in os.environ or "ANDROID_ROOT" in os.environ

BG = (8, 10, 20)
CARD = (16, 22, 42)
CARD_HI = (26, 36, 66)
ACCENT = (0, 220, 180)
TEXT = (220, 230, 255)
DIM = (110, 125, 155)
RED = (255, 110, 110)

notes = []   # startup problems, shown on the menu


# ── Games folder ──────────────────────────────────────────────────────────────

def resolve_games_dir():
    bundled = os.path.join(APP_DIR, "games")
    if not ON_ANDROID:
        os.makedirs(bundled, exist_ok=True)
        return bundled

    try:
        from android.permissions import request_permissions, Permission  # type: ignore
        request_permissions([Permission.READ_EXTERNAL_STORAGE,
                             Permission.WRITE_EXTERNAL_STORAGE])
    except Exception as e:
        notes.append(f"permissions: {e}")

    candidates = []
    try:
        from android.storage import primary_external_storage_path  # type: ignore
        candidates.append(os.path.join(primary_external_storage_path(),
                                       "BlemacShell", "games"))
    except Exception as e:
        notes.append(f"external storage: {e}")
    candidates.append(os.path.join(os.environ.get("ANDROID_PRIVATE", APP_DIR), "games"))

    games_dir = candidates[-1]
    for c in candidates:
        try:
            os.makedirs(c, exist_ok=True)
            t = os.path.join(c, ".write_test")
            open(t, "w").close()
            os.remove(t)
            games_dir = c
            break
        except Exception as e:
            notes.append(f"cannot use {c}: {e}")

    # copy bundled games the first time
    try:
        for name in os.listdir(bundled):
            src, dst = os.path.join(bundled, name), os.path.join(games_dir, name)
            if os.path.isdir(src) and not os.path.exists(dst):
                shutil.copytree(src, dst)
    except Exception as e:
        notes.append(f"copy bundled: {e}")
    return games_dir


# ── Running a game inside our window ─────────────────────────────────────────

def run_game(screen, m):
    """Run a game's main() in this process. Returns a traceback string or None."""
    saved = []

    def patch(obj, name, fn):
        saved.append((obj, name, getattr(obj, name)))
        setattr(obj, name, fn)

    noop = lambda *a, **k: None
    real_get = pygame.event.get
    ac_back = getattr(pygame, "K_AC_BACK", None)

    def get(*a, **k):                      # Android back button -> Escape
        out = []
        for e in real_get(*a, **k):
            if e.type == pygame.KEYDOWN and ac_back is not None and e.key == ac_back:
                e = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE,
                                       mod=0, unicode="", scancode=0)
            out.append(e)
        return out

    patch(pygame.event, "get", get)
    patch(pygame.display, "set_mode", lambda *a, **k: screen)  # one window only
    patch(pygame.display, "quit", noop)
    patch(pygame, "quit", noop)            # the shell owns SDL

    old_cwd, old_path = os.getcwd(), sys.path[:]
    before = set(sys.modules)
    err = None
    try:
        entry = os.path.join(m.folder, m.entry)
        if not os.path.isfile(entry):
            raise FileNotFoundError(entry)
        os.chdir(m.folder)
        sys.path.insert(0, m.folder)
        spec = importlib.util.spec_from_file_location(f"blemac_game_{m.id}", entry)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "main"):
            try:
                mod.main(screen)           # games that take a screen reuse ours
            except TypeError as e:
                if "positional argument" not in str(e):
                    raise
                mod.main()
    except SystemExit:
        pass
    except Exception:
        err = traceback.format_exc()
    finally:
        for obj, name, orig in reversed(saved):
            setattr(obj, name, orig)
        os.chdir(old_cwd)
        sys.path[:] = old_path
        for name in set(sys.modules) - before:       # let games reload cleanly
            sys.modules.pop(name, None)
        pygame.event.clear()
        pygame.key.set_repeat()
    if err:
        try:
            with open(os.path.join(m.folder, "crash.log"), "w") as f:
                f.write(err)
        except Exception:
            pass
    return err


# ── Menu UI ───────────────────────────────────────────────────────────────────

def wrap(font, text, width):
    lines = []
    for para in text.split("\n"):
        line = ""
        for word in para.split(" "):
            t = (line + " " + word).strip()
            if font.size(t)[0] <= width or not line:
                line = t
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines


class Menu:
    def __init__(self, screen, games_dir):
        self.screen = screen
        self.games_dir = games_dir
        self.W, self.H = screen.get_size()
        u = self.u = self.W / 480
        self.f_title = pygame.font.Font(None, int(54 * u))
        self.f_card = pygame.font.Font(None, int(38 * u))
        self.f_small = pygame.font.Font(None, int(26 * u))
        self.header = int(120 * u)
        self.card_h = int(130 * u)
        self.gap = int(14 * u)
        self.pad = int(16 * u)
        self.scroll = 0
        self.error = None
        self.rescan()

    def rescan(self):
        self.games = scan_games(self.games_dir)
        self.scroll = 0

    def rects(self):
        out = []
        y = self.header - self.scroll
        for _ in self.games:
            out.append(pygame.Rect(self.pad, y, self.W - 2 * self.pad, self.card_h))
            y += self.card_h + self.gap
        return out

    def max_scroll(self):
        total = self.header + len(self.games) * (self.card_h + self.gap)
        return max(0, total - self.H + self.pad)

    def draw(self, pressed=None):
        s, u = self.screen, self.u
        s.fill(BG)
        for i, (g, r) in enumerate(zip(self.games, self.rects())):
            if r.bottom < self.header or r.top > self.H:
                continue
            pygame.draw.rect(s, CARD_HI if i == pressed else CARD, r, border_radius=int(14 * u))
            s.blit(self.f_card.render(g.title, True, TEXT), (r.x + 18 * u, r.y + 14 * u))
            ver = self.f_small.render(f"{g.version}  ·  {g.author}", True, ACCENT)
            s.blit(ver, (r.x + 18 * u, r.y + 52 * u))
            desc = wrap(self.f_small, g.description, r.w - 36 * u)[:2]
            for j, line in enumerate(desc):
                s.blit(self.f_small.render(line, True, DIM), (r.x + 18 * u, r.y + (80 + 22 * j) * u))
        if not self.games:
            msg = [f"No games found in:", self.games_dir, "",
                   "Each game needs a folder with game.json + main.py.", "",
                   "Tap here to rescan."] + notes
            y = self.header + 30 * u
            for m in msg:
                for line in wrap(self.f_small, m, self.W - 2 * self.pad):
                    s.blit(self.f_small.render(line, True, DIM), (self.pad, y))
                    y += 28 * u
        # header on top
        pygame.draw.rect(s, BG, (0, 0, self.W, self.header))
        s.blit(self.f_title.render("BLEMAC SHELL", True, ACCENT), (self.pad, 30 * u))
        s.blit(self.f_small.render(f"{len(self.games)} game(s)", True, DIM), (self.pad, 82 * u))
        pygame.display.flip()

    def show_error(self, title, tb):
        s, u = self.screen, self.u
        lines = wrap(self.f_small, tb, self.W - 2 * self.pad)
        clock = pygame.time.Clock()
        off = 0
        down = None
        while True:
            clock.tick(30)
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    raise SystemExit
                if e.type == pygame.KEYDOWN:
                    return
                if e.type == pygame.MOUSEBUTTONDOWN:
                    down = e.pos
                    moved = 0
                elif e.type == pygame.MOUSEMOTION and down and e.buttons[0]:
                    off = max(0, off - e.rel[1])
                    moved += abs(e.rel[1])
                elif e.type == pygame.MOUSEBUTTONUP and down:
                    if moved < 12 * u and e.pos[1] > self.H - 90 * u:
                        return
                    down = None
            s.fill((14, 6, 10))
            s.blit(self.f_card.render(f"{title} crashed", True, RED), (self.pad, 20 * u - 0 + 0))
            y = 80 * u - off
            for line in lines:
                if 60 * u < y < self.H - 90 * u:
                    s.blit(self.f_small.render(line, True, (255, 215, 215)), (self.pad, y))
                y += 26 * u
            pygame.draw.rect(s, CARD, (0, self.H - 80 * u, self.W, 80 * u))
            c = self.f_card.render("TAP HERE TO CLOSE", True, TEXT)
            s.blit(c, c.get_rect(center=(self.W // 2, self.H - 40 * u)))
            pygame.display.flip()

    def run(self):
        clock = pygame.time.Clock()
        down = None
        moved = 0
        pressed = None
        while True:
            clock.tick(60)
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    return
                if e.type == pygame.KEYDOWN and e.key in (
                        pygame.K_ESCAPE, getattr(pygame, "K_AC_BACK", -1)):
                    return
                if e.type == pygame.MOUSEBUTTONDOWN:
                    down, moved = e.pos, 0
                    pressed = next((i for i, r in enumerate(self.rects())
                                    if r.collidepoint(e.pos)), None)
                elif e.type == pygame.MOUSEMOTION and down and e.buttons[0]:
                    moved += abs(e.rel[1])
                    if moved > 12 * self.u:
                        pressed = None
                        self.scroll = min(self.max_scroll(), max(0, self.scroll - e.rel[1]))
                elif e.type == pygame.MOUSEBUTTONUP and down:
                    if moved <= 12 * self.u:
                        hit = next((i for i, r in enumerate(self.rects())
                                    if r.collidepoint(e.pos)), None)
                        if hit is not None:
                            m = self.games[hit]
                            err = run_game(self.screen, m)
                            if err:
                                self.show_error(m.title, err)
                            self.rescan()
                        elif not self.games:
                            self.rescan()
                    down, pressed = None, None
            self.draw(pressed)


def main():
    pygame.init()
    flags = pygame.FULLSCREEN if ON_ANDROID else 0
    screen = pygame.display.set_mode((0, 0) if ON_ANDROID else (480, 800), flags)
    pygame.display.set_caption("BLEMAC Shell")
    try:
        games_dir = resolve_games_dir()
        Menu(screen, games_dir).run()
    except SystemExit:
        pass
    except Exception:
        tb = traceback.format_exc()
        try:
            open(os.path.join(APP_DIR, "blemac_crash.log"), "w").write(tb)
        except Exception:
            pass
        m = Menu.__new__(Menu)       # minimal screen to show startup failure
        m.screen, m.W, m.H = screen, *screen.get_size()
        m.u = m.W / 480
        m.pad = int(16 * m.u)
        m.f_card = pygame.font.Font(None, int(38 * m.u))
        m.f_small = pygame.font.Font(None, int(26 * m.u))
        m.show_error("BLEMAC Shell", tb)
    pygame.quit()


if __name__ == "__main__":
    main()
