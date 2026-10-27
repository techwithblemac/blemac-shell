"""
shell/core/manifest.py — Reads game.json from sideloaded game folders.

Each game folder structure:
    games/
        my_game/
            game.json       ← required
            main.py         ← required (entry point)
            icon.png        ← optional 256x256
            assets/         ← game assets

game.json schema:
{
    "id":          "my_game",
    "title":       "MY GAME",
    "version":     "v1.0",
    "author":      "Your Name",
    "description": "Short blurb",
    "entry":       "main.py",
    "icon":        "icon.png",
    "tags":        ["arcade"],
    "orientation": "landscape",    ← "portrait" | "landscape" | "any"
    "touch_profile": "dpad"        ← "dpad" | "platformer" | "custom" | "none"
}

touch_profile tells the shell which virtual gamepad layout to overlay.
"""

import json
import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class GameManifest:
    id:            str
    title:         str
    version:       str
    author:        str
    description:   str
    entry:         str
    folder:        str
    icon_path:     Optional[str] = None
    tags:          List[str] = field(default_factory=list)
    orientation:   str = "landscape"    # portrait | landscape | any
    touch_profile: str = "dpad"         # dpad | platformer | custom | none


def load_manifest(folder: str) -> Optional[GameManifest]:
    path = os.path.join(folder, "game.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)

        icon = None
        if d.get("icon"):
            p = os.path.join(folder, d["icon"])
            if os.path.isfile(p):
                icon = p

        return GameManifest(
            id            = d.get("id", os.path.basename(folder)),
            title         = d.get("title", "Untitled"),
            version       = d.get("version", "v1.0"),
            author        = d.get("author", "Unknown"),
            description   = d.get("description", ""),
            entry         = d.get("entry", "main.py"),
            folder        = folder,
            icon_path     = icon,
            tags          = d.get("tags", []),
            orientation   = d.get("orientation", "landscape"),
            touch_profile = d.get("touch_profile", "dpad"),
        )
    except Exception as e:
        print(f"[Manifest] Error in {path}: {e}")
        return None


def scan_games(games_dir: str) -> List[GameManifest]:
    """Scan a directory for valid game folders."""
    results = []
    if not os.path.isdir(games_dir):
        return results
    for name in sorted(os.listdir(games_dir)):
        folder = os.path.join(games_dir, name)
        if not os.path.isdir(folder):
            continue
        m = load_manifest(folder)
        if m:
            results.append(m)
            print(f"[Scanner] Found: {m.title} ({m.id}) touch={m.touch_profile}")
        else:
            print(f"[Scanner] Skipping {name} — no valid game.json")
    return results
