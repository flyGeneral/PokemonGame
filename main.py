"""入口:python3 main.py [--headless]"""
import sys

if "--headless" in sys.argv or "SMOKE" in sys.argv:
    import os
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from src.game import Game

if __name__ == "__main__":
    g = Game()
    max_frames = 240 if "SMOKE" in sys.argv else None
    g.run(max_frames=max_frames)
