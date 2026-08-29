"""渲染美术自检图:精灵/人物/图块/战斗背景 → /tmp/art_sheet.png"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
from src import art, settings as S
from src import data

pygame.init()
pygame.display.set_mode((100, 100))

mons, icons, _backs = art.build_mons()
people = art.build_people()
tiles = art.build_tiles()

COLS = 12
CELL = 96
sheet_w = COLS * CELL
rows = 6
sheet = pygame.Surface((sheet_w, rows * CELL))
sheet.fill((46, 54, 70))

font = pygame.font.Font("/System/Library/Fonts/Hiragino Sans GB.ttc", 16)


def put(img, col, row, label=""):
    x, y = col * CELL, row * CELL
    sheet.blit(img, (x + (CELL - img.get_width()) // 2, y + (CELL - img.get_height() - 14) // 2))
    if label:
        sheet.blit(font.render(label, True, (255, 255, 255)), (x + 4, y + CELL - 18))


r = 0
for i, (aid, img) in enumerate(mons.items()):
    put(img, i % COLS, r, aid)
r += 1
for i, (pid, dirs) in enumerate(people.items()):
    for j, d in enumerate(("down", "up", "side")):
        key = "right" if d == "side" else d
        put(dirs[key][0], (i * 3 + j) % COLS, r, f"{pid}-{d}")
r += 1
for i, (ch, img) in enumerate(tiles.items()):
    put(img, i % COLS, r, repr(ch))
r += 1
put(art.build_ball(4), 0, r, "ball")
put(tiles["w1"], 1, r, "w1")
put(tiles["T"], 2, r, "tree")
put(tiles["S"], 3, r, "sign")
put(tiles["D"], 4, r, "door")
put(tiles["V"], 5, r, "window")
r += 1
bg = art.build_battle_bg()
bg = pygame.transform.scale(bg, (sheet_w, 200))
sheet.blit(bg, (0, r * CELL))
r += 2

out = "/tmp/art_sheet.png"
pygame.image.save(sheet, out)
print("saved", out, sheet.get_size())
