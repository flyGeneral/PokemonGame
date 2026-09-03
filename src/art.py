"""把像素矩阵与程序化图形构建成 pygame Surface。

所有美术均为代码生成:精灵来自 art_data.py 的字符矩阵,
人物与图块由矩形/噪声程序绘制,风格为 GBA/NDS 式像素风。

官方素材替换接口(个人本地使用):
  assets/mons/<art_id>.png        → 战斗正面图(自动等比缩放放进 80x80)
  assets/mons/icon_<art_id>.png   → 菜单图标(32x32)
存在同名文件时优先使用外部图片,否则回退到内置原创像素画。
"""
import json
import os
import random

import pygame

from . import art_data
from . import settings as S

ASSET_MON_DIR = os.path.join(S.ROOT, "assets", "mons")


def _load_override(filename, box):
    """从 assets 目录加载外部图片并等比缩放进 box×box 画布,失败返回 None。"""
    path = os.path.join(ASSET_MON_DIR, filename)
    if not os.path.exists(path):
        return None
    try:
        img = pygame.image.load(path)
        if img.get_alpha() is None and img.get_bitsize() != 32:
            img = img.convert()
        else:
            img = img.convert_alpha()
        w, h = img.get_size()
        m = max(w, h)
        k = box / m if m > box else 1.0
        if k != 1.0:
            img = pygame.transform.scale(img, (max(1, int(w * k)), max(1, int(h * k))))
        canvas = _surf(box, box)
        canvas.blit(img, ((box - img.get_width()) // 2, (box - img.get_height()) // 2))
        return canvas
    except Exception:
        return None


def _surf(w, h):
    return pygame.Surface((w, h), pygame.SRCALPHA)


def matrix_surface(rows, pal, scale=1):
    w = max(len(r) for r in rows)
    h = len(rows)
    s = _surf(w, h)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != ".":
                c = pal.get(ch)
                if c:
                    s.set_at((x, y), c)
    if scale != 1:
        s = pygame.transform.scale(s, (w * scale, h * scale))
    return s


# ================================================================ 精灵
def build_mons():
    """{art_id: Surface(80x80)} 战斗正面图;另存 icon(32x32)、背面图。
    assets/mons/ 下存在同名 png 时优先使用外部官方素材:
      <id>.png / icon_<id>.png / back_<id>.png
    """
    out, icons, backs = {}, {}, {}
    for art_id, d in art_data.MON_ART.items():
        front = _load_override(art_id + ".png", 80) or matrix_surface(d["rows"], d["pal"], 5)
        out[art_id] = front
        icons[art_id] = _load_override("icon_" + art_id + ".png", 32) or matrix_surface(d["rows"], d["pal"], 2)
        backs[art_id] = (_load_override("back_" + art_id + ".png", 80)
                         or pygame.transform.flip(front, True, False))
    return out, icons, backs


def mon_back(surf):
    return pygame.transform.flip(surf, True, False)


# ================================================================ 人物
PEOPLE = {
    "player":  {"cap": (198, 58, 50), "hair": (62, 46, 38), "skin": (250, 220, 185),
                "shirt": (74, 114, 194), "pants": (64, 64, 80)},
    "prof":    {"hair": (170, 170, 178), "skin": (250, 222, 190),
                "shirt": (242, 242, 248), "pants": (112, 92, 70)},
    "mom":     {"hair": (152, 98, 56), "skin": (250, 222, 190),
                "shirt": (222, 98, 108), "pants": (240, 240, 240), "dress": True},
    "youth":   {"hair": (52, 46, 42), "skin": (250, 220, 185),
                "shirt": (242, 206, 92), "pants": (86, 122, 82)},
    "leader":  {"hair": (112, 76, 46), "skin": (245, 215, 180),
                "shirt": (152, 106, 66), "pants": (74, 63, 56)},
    "villager": {"hair": (42, 40, 48), "skin": (250, 220, 185),
                 "shirt": (74, 152, 140), "pants": (96, 84, 74)},
    "lady":     {"hair": (150, 90, 130), "skin": (250, 222, 190),
                 "shirt": (196, 120, 170), "pants": (110, 80, 96), "dress": True},
}

def _human_grid(pal, direction, frame):
    g = [[None] * 16 for _ in range(20)]

    def R(x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                g[y][x] = c

    cap, hair = pal.get("cap"), pal["hair"]
    skin, shirt, pants = pal["skin"], pal["shirt"], pal["pants"]
    shoe, eye = (48, 42, 50), (46, 42, 56)
    side = direction in ("left", "right")

    # 头部
    if direction == "down":
        R(5, 2, 10, 3, hair)
        R(5, 4, 10, 7, skin)
        if cap:
            R(4, 1, 11, 2, cap)
            R(3, 3, 12, 3, cap)
            R(5, 4, 10, 4, hair)
        g[5][6] = eye
        g[5][9] = eye
        R(4, 4, 4, 6, hair)
        R(11, 4, 11, 6, hair)
    elif direction == "up":
        R(5, 2, 10, 7, hair)
        if cap:
            R(4, 1, 11, 2, cap)
            R(4, 3, 11, 4, cap)
    else:
        R(5, 2, 10, 3, hair)
        R(5, 4, 9, 7, skin)
        if cap:
            R(4, 1, 11, 2, cap)
            R(3, 3, 11, 3, cap)
            R(4, 4, 5, 4, hair)
        g[5][8] = eye
        R(4, 4, 4, 6, hair)
        R(10, 4, 10, 6, hair)

    # 身体
    if side:
        R(5, 8, 10, 13, shirt)
        R(9, 9, 10, 11, shirt)
    else:
        R(4, 8, 11, 13, shirt)
        R(3, 9, 3, 11, shirt)
        R(12, 9, 12, 11, shirt)

    # 腿脚
    if pal.get("dress"):
        R(3, 12, 12, 15, shirt)
        if side:
            R(6, 16, 9, 17, skin)
            R(6, 18, 9, 18, shoe)
        elif frame == 1:
            R(5, 15, 6, 17, skin); R(5, 18, 6, 18, shoe)
            R(9, 16, 10, 17, skin); R(9, 18, 10, 18, shoe)
        elif frame == 2:
            R(9, 15, 10, 17, skin); R(9, 18, 10, 18, shoe)
            R(5, 16, 6, 17, skin); R(5, 18, 6, 18, shoe)
        else:
            R(5, 16, 6, 17, skin); R(9, 16, 10, 17, skin)
            R(5, 18, 6, 18, shoe); R(9, 18, 10, 18, shoe)
    elif side:
        if frame == 1:      # 迈步
            R(9, 14, 10, 16, pants); R(9, 17, 10, 17, shoe)
            R(4, 14, 5, 16, pants); R(4, 17, 5, 17, shoe)
        elif frame == 2:    # 并拢
            R(6, 14, 8, 16, pants); R(6, 17, 8, 17, shoe)
        else:
            R(6, 14, 7, 17, pants); R(8, 14, 9, 17, pants)
            R(6, 18, 7, 18, shoe); R(8, 18, 9, 18, shoe)
    else:
        if frame == 1:      # 左脚抬起
            R(5, 13, 6, 16, pants); R(5, 17, 6, 17, shoe)
            R(9, 14, 10, 17, pants); R(9, 18, 10, 18, shoe)
        elif frame == 2:    # 右脚抬起
            R(9, 13, 10, 16, pants); R(9, 17, 10, 17, shoe)
            R(5, 14, 6, 17, pants); R(5, 18, 6, 18, shoe)
        else:
            R(5, 14, 6, 17, pants); R(9, 14, 10, 17, pants)
            R(5, 18, 6, 18, shoe); R(9, 18, 10, 18, shoe)
    return g


def _outline_grid(g, color=(52, 46, 56)):
    """给非空像素的四周空位加 1px 轮廓,接近官方 GBA 小人的描边。"""
    h, w = len(g), len(g[0])
    out = [row[:] for row in g]
    for y in range(h):
        for x in range(w):
            if g[y][x]:
                continue
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                yy, xx = y + dy, x + dx
                if 0 <= yy < h and 0 <= xx < w and g[yy][xx]:
                    out[y][x] = color
                    break
    return out


def _grid_surface(g, scale=1, outline=False):
    if outline:
        g = _outline_grid(g)
    h, w = len(g), len(g[0])
    s = _surf(w, h)
    for y in range(h):
        for x in range(w):
            c = g[y][x]
            if c:
                s.set_at((x, y), c)
    if scale != 1:
        s = pygame.transform.scale(s, (w * scale, h * scale))
    return s


def _load_charsets():
    """assets/chars/chars.json 存在时,从 XP 4x4 行走图构建人物帧(1.5x → 48x72)。"""
    if not os.path.exists(CHARSET_META):
        return None
    try:
        with open(CHARSET_META) as f:
            meta = json.load(f)
        out = {}
        row_of = {"down": 0, "left": 1, "right": 2, "up": 3}
        for pal, info in meta.items():
            path = os.path.join(os.path.dirname(CHARSET_META), info["file"])
            sheet = pygame.image.load(path).convert_alpha()
            fw = sheet.get_width() // info["cols"]
            fh = sheet.get_height() // info["rows"]
            d = {}
            for direction, row in row_of.items():
                frames = []
                for fidx in (1, 0, 2):          # 待机=第2帧,走路=第1/3帧
                    fr = sheet.subsurface((fidx * fw, row * fh, fw, fh)).copy()
                    frames.append(pygame.transform.scale(fr, (int(fw * 1.5), int(fh * 1.5))))
                d[direction] = frames
            out[pal] = d
        return out or None
    except Exception:
        return None


def build_people():
    override = _load_charsets()
    out = {}
    for name, pal in PEOPLE.items():
        if override and name in override:
            out[name] = override[name]
            continue
        d = {}
        for direction in ("down", "up", "right"):
            frames = [_grid_surface(_human_grid(pal, direction, f), S.SCALE, outline=True)
                      for f in (0, 1, 2)]
            d[direction] = frames
        d["left"] = [pygame.transform.flip(s, True, False) for s in d["right"]]
        out[name] = d
    return out


# ================================================================ 图块
GRASS = (114, 192, 84)

def _noise(base, spots, seed):
    s = _surf(16, 16)
    s.fill(base)
    rng = random.Random(seed)
    for color, n in spots:
        for _ in range(n):
            s.set_at((rng.randrange(16), rng.randrange(16)), color)
    return s


def _tallgrass():
    s = _noise(GRASS, [((96, 172, 70), 10), ((132, 208, 98), 6)], 7)
    dark, mid = (60, 130, 56), (82, 156, 66)
    for x0 in (3, 8, 13):
        s.set_at((x0, 7), dark)
        for y in range(8, 16):
            s.set_at((x0, y), dark)
        for y in range(11, 16):
            if x0 > 0:
                s.set_at((x0 - 1, y), mid)
            if x0 < 15:
                s.set_at((x0 + 1, y), mid)
    return s


def _water(phase):
    s = _surf(16, 16)
    s.fill((72, 132, 222))
    light = (138, 186, 248)
    dark = (56, 110, 198)
    for row in (2, 8, 13):
        off = (phase * 2 + row) % 6
        for x in range(16):
            if (x + off) % 6 < 3:
                s.set_at((x, row), light)
    for x, y in ((1, 5), (9, 11), (13, 4), (5, 14)):
        s.set_at((x, y), dark)
    return s


TREE_ROWS = [
    "................",
    ".....kkkkk......",
    "...kkGGGGGkk....",
    "..kGGGGGGGGGk...",
    ".kGGDDGGGGGGGk..",
    ".kGGGGGGGDDGGk..",
    ".kGDGGGGGGGGGk..",
    ".kGGGGGDGGGGGk..",
    "..kGGGGGGGGGk...",
    "...kkGGGGGkk....",
    ".....kttk.......",
    ".....kttk.......",
    ".....kttk.......",
    "....kttttk......",
    "................",
    "................",
]

SIGN_ROWS = [
    "................",
    "................",
    "..kkkkkkkkkkkk..",
    "..kSSSSSSSSSSk..",
    "..kSddSddSddSk..",
    "..kSSSSSSSSSSk..",
    "..kSddSddSddSk..",
    "..kSSSSSSSSSSk..",
    "..kkkkkkkkkkkk..",
    ".....kppk.......",
    ".....kppk.......",
    ".....kppk.......",
    ".....kppk.......",
    "................",
    "................",
    "................",
]


def _flower(seed):
    s = _noise(GRASS, [((96, 172, 70), 8)], seed)
    rng = random.Random(seed + 1)
    for _ in range(3):
        x, y = rng.randrange(2, 13), rng.randrange(2, 13)
        col = (232, 84, 84) if rng.random() < 0.5 else (246, 246, 240)
        s.set_at((x, y), col)
        s.set_at((x - 1, y), col)
        s.set_at((x, y - 1), col)
        s.set_at((x + 1, y), col)
        s.set_at((x, y + 1), col)
        s.set_at((x, y), (250, 214, 90))
    return s


def _fence():
    s = _noise(GRASS, [((96, 172, 70), 6)], 11)
    wood, dark = (156, 116, 74), (108, 76, 46)
    for y in (5, 6, 10, 11):
        for x in range(16):
            s.set_at((x, y), wood if y % 2 == 0 else dark if x % 4 == 3 else wood)
    for x0 in (2, 12):
        for y in range(4, 13):
            s.set_at((x0, y), dark if y in (4, 12) else wood)
            s.set_at((x0 + 1, y), dark if y in (4, 12) else (136, 98, 60))
    return s


def _roof(main, dark, edge):
    s = _surf(16, 16)
    s.fill(main)
    for y in range(0, 16, 4):
        for x in range(16):
            s.set_at((x, y), dark)
            if (x + y) % 8 == 0:
                s.set_at((x, y + 1), (main[0] + 16, main[1] + 14, main[2] + 16) if main[2] < 240 else main)
    for x in range(16):
        s.set_at((x, 15), edge)
    return s


def _wall():
    s = _surf(16, 16)
    s.fill((230, 216, 184))
    for y in (5, 10):
        for x in range(16):
            s.set_at((x, y), (206, 190, 154))
    for y in range(16):
        for x in ((3, 11) if (y // 5) % 2 == 0 else (7,)):
            s.set_at((x, y), (206, 190, 154))
    return s


def _window():
    s = _wall()
    for y in range(3, 13):
        for x in range(3, 13):
            s.set_at((x, y), (112, 82, 60))
    for y in range(4, 12):
        for x in range(4, 12):
            s.set_at((x, y), (152, 198, 240))
    for y in range(4, 12):
        s.set_at((8, y), (112, 82, 60))
    for x in range(4, 12):
        s.set_at((x, 8), (112, 82, 60))
    s.set_at((5, 5), (210, 232, 252))
    s.set_at((6, 6), (210, 232, 252))
    return s


def _door():
    s = _wall()
    for y in range(3, 16):
        for x in range(4, 12):
            s.set_at((x, y), (94, 66, 44))
    for y in range(4, 16):
        for x in range(5, 11):
            s.set_at((x, y), (124, 88, 58))
    s.set_at((9, 9), (240, 210, 90))
    return s


def _interior_wall():
    s = _surf(16, 16)
    s.fill((190, 170, 150))
    for y in (4, 9, 14):
        for x in range(16):
            s.set_at((x, y), (164, 144, 124))
    for x in (5, 11):
        for y in range(16):
            s.set_at((x, y), (172, 152, 132))
    return s


def _gym_wall():
    s = _surf(16, 16)
    s.fill((150, 128, 156))
    for y in (3, 8, 13):
        for x in range(16):
            s.set_at((x, y), (122, 102, 128))
    for x in (7,):
        for y in range(16):
            s.set_at((x, y), (136, 114, 142))
    return s


def _gym_floor():
    s = _surf(16, 16)
    s.fill((206, 180, 140))
    for y in (3, 7, 11, 15):
        for x in range(16):
            s.set_at((x, y), (188, 160, 120))
    for x, y in ((4, 1), (11, 5), (7, 9), (13, 13), (2, 12)):
        s.set_at((x, y), (196, 170, 130))
    return s


def _floor_indoor():
    s = _surf(16, 16)
    s.fill((228, 214, 190))
    for y in range(0, 16, 4):
        for x in range(0, 16, 4):
            s.set_at((x, y), (206, 190, 162))
    return s


def _mat():
    s = _floor_indoor()
    for y in range(2, 14):
        for x in range(2, 14):
            s.set_at((x, y), (176, 124, 112))
    for y in range(3, 13):
        for x in range(3, 13):
            s.set_at((x, y), (196, 146, 130) if (x + y) % 2 == 0 else (176, 124, 112))
    return s


def _bed():
    s = _surf(16, 16)
    s.fill((152, 98, 64))
    for y in range(1, 15):
        for x in range(1, 15):
            s.set_at((x, y), (238, 244, 250))
    for y in range(2, 6):
        for x in range(2, 14):
            s.set_at((x, y), (255, 255, 255))
    for y in range(7, 14):
        for x in range(2, 14):
            s.set_at((x, y), (122, 162, 212))
    for x in range(2, 14, 3):
        s.set_at((x, 9), (100, 138, 188))
    return s


def _shelf():
    s = _surf(16, 16)
    s.fill((144, 104, 68))
    for y in range(0, 16):
        for x in (0, 15):
            s.set_at((x, y), (108, 76, 48))
    book_cols = [(196, 84, 74), (86, 128, 190), (234, 196, 92), (108, 168, 108),
                 (172, 120, 190), (230, 150, 88)]
    rng = random.Random(5)
    for row0 in (2, 9):
        x = 2
        while x < 14:
            w = rng.choice((1, 1, 2))
            c = rng.choice(book_cols)
            for y in range(row0, row0 + 5):
                for dx in range(w):
                    if x + dx < 14:
                        s.set_at((x + dx, y), c)
            x += w + 1
    for y in (7, 14):
        for x in range(1, 15):
            s.set_at((x, y), (120, 86, 54))
    return s


def _table():
    s = _surf(16, 16)
    s.fill((174, 134, 88))
    for y in range(14, 16):
        for x in range(16):
            s.set_at((x, y), (142, 106, 66))
    for y in (4, 9):
        for x in range(1, 15):
            s.set_at((x, y), (160, 122, 78))
    return s


def _ball_table():
    s = _table()
    ball = matrix_surface(art_data.BALL_ROWS, art_data.BALL_PAL, 1)
    s.blit(ball, (4, 4))
    return s


def build_tiles():
    """返回 {tile_char: Surface}。水面有两帧 'w0'/'w1'。"""
    t = {}
    t["."] = _noise(GRASS, [((96, 172, 70), 12), ((132, 208, 98), 6)], 1)
    t[","] = _tallgrass()
    t["p"] = _noise((219, 199, 152), [((200, 178, 128), 10), ((232, 214, 172), 6)], 2)
    t["n"] = t["p"]
    t["w0"] = _water(0)
    t["w1"] = _water(1)
    t["f"] = _flower(3)
    t["T"] = matrix_surface(TREE_ROWS, {"k": (40, 92, 42), "G": (72, 152, 64),
                                        "D": (54, 122, 52), "t": (114, 84, 56)})
    t["F"] = _fence()
    t["S"] = matrix_surface(SIGN_ROWS, {"k": (70, 50, 35), "S": (198, 160, 110),
                                        "d": (120, 88, 56), "p": (132, 96, 62)})
    t["R"] = _roof((88, 134, 178), (66, 110, 152), (52, 88, 124))
    t["Q"] = _roof((198, 92, 76), (160, 68, 56), (128, 52, 44))   # 研究所红顶
    t["B"] = _wall()
    t["V"] = _window()
    t["D"] = _door()
    t["#"] = _interior_wall()
    t["G"] = _gym_wall()
    t["g"] = _gym_floor()
    t["o"] = _floor_indoor()
    t["m"] = _mat()
    t["b"] = _bed()
    t["s"] = _shelf()
    t["t"] = _table()
    t["1"] = _ball_table()
    t["2"] = _ball_table()
    t["3"] = _ball_table()
    # 统一放大到屏幕图块尺寸(STILE)
    for k in t:
        t[k] = pygame.transform.scale(t[k], (S.STILE, S.STILE))
    return _apply_sheet_tiles(t)


BALL_SPRITE = None

# 官方风格图块替换表:char → (图块集, 32px块col, 32px块row, 子砖)。
# 图块集为 2x 素材:子砖 "tl/tr/bl/br" 取块内 16px 原生砖(缩放 3x 最清晰),
# "full" 取整个 32px 块(跨子砖的整体图案,如树冠)。坐标人工目视挑选。
TILE_FROM_SHEET = {
    ".":  ("Outside", 1, 0, "tl"),
    ",":  ("Outside", 7, 0, "tl"),
    "p":  ("Outside", 0, 18, "tl"),
    "n":  ("Outside", 0, 18, "tl"),
    "f":  None,                    # 草地+程序花朵合成,见 _apply_sheet_tiles
    "w0": ("Outside", 6, 87, "tl"),
    "w1": ("Outside", 6, 87, "tl"),   # 纯水面(带岸线的帧只用于边缘,见 'wt')
    "wt": ("Outside", 6, 86, "full"), # 水域上岸线(邻接陆地的顶行)
    "T":  ("Outside", 1, 56, "tl"),
    "F":  ("Outside", 2, 74, "tl"),
    "r":  ("Outside", 1, 180, "tl"),
    "R":  ("Outside", 1, 181, "tl"),
    "q":  [("Outside", 1, 180, "tl"), ("Outside", 1, 189, "full"), ("Outside", 0, 190, "full")],
    "Q":  [("Outside", 1, 191, "full"), ("Outside", 2, 191, "full")],
    "B":  [("Outside", 0, 182, "full"), ("Outside", 2, 182, "full"),
           ("Outside", 3, 182, "full"), ("Outside", 3, 192, "full")],
    "V":  [("Outside", 1, 182, "full"), ("Outside", 0, 182, "full")],
    "D":  ("Doors", 1, 0, "full"),
    "#":  [("InteriorGeneral", 1, 116, "tr"), ("InteriorGeneral", 1, 116, "tl"),
           ("InteriorGeneral", 2, 116, "tr"), ("InteriorGeneral", 1, 117, "tr"),
           ("InteriorGeneral", 1, 42, "tl")],
    "o":  ("InteriorGeneral", 1, 28, "tl"),
    "m":  ("InteriorGeneral", 0, 100, "full"),
    "b":  None,                    # 床保留内置(图块集无对应)
    "s":  ("InteriorGeneral", 0, 23, "tl"),
    "t":  ("InteriorGeneral", 0, 0, "tl"),
    "g":  ("Gyms", 2, 19, "tl"),
    "G":  ("Gyms", 2, 16, "tl"),
}

CHAR_DIR_SRC = os.path.join(S.ROOT, "assets", "src", "%s.png")
CHARSET_META = os.path.join(S.ROOT, "assets", "chars", "chars.json")


def _apply_sheet_tiles(t):
    """用官方风图块集替换程序生成的图块(存在 assets/src/*.png 时)。"""
    sheets = {}
    for name in ("Outside", "InteriorGeneral", "Gyms"):
        p = CHAR_DIR_SRC % name
        if os.path.exists(p):
            sheets[name] = pygame.image.load(p).convert_alpha()
    if not sheets:
        return t
    SUB = {"tl": (0, 0), "tr": (16, 0), "bl": (0, 16), "br": (16, 16)}

    def _block(img, c, r, sub):
        if sub == "full":
            return img.subsurface((c * 32, r * 32, 32, 32)).copy()
        sx, sy = SUB[sub]
        return img.subsurface((c * 32 + sx, r * 32 + sy, 16, 16)).copy()

    def _has_magenta(surf):
        w, h = surf.get_size()
        for y in range(0, h, 3):
            for x in range(0, w, 3):
                c = surf.get_at((x, y))
                if c.r > 240 and c.b > 240 and c.g < 40:
                    return True
        return False

    for ch, cands in TILE_FROM_SHEET.items():
        if not cands:
            continue
        if isinstance(cands, tuple):     # 兼容单候选写法
            cands = [cands]
        for spec in cands:
            sheet_name, c, r = spec[0], spec[1], spec[2]
            sub = spec[3] if len(spec) > 3 else "tl"
            img = sheets.get(sheet_name)
            if img is None:
                continue
            block = _block(img, c, r, sub)
            if _has_magenta(block):      # 图块集空槽位是洋红占位,跳过
                continue
            t[ch] = pygame.transform.scale(block, (S.STILE, S.STILE))
            break
    # 门 = 官方门体切块 合成到墙砖上(门精灵四周透明,直接贴会浮在草地上)
    if "Doors" in sheets and "B" in t:
        door = sheets["Doors"].subsurface((36, 2, 24, 30)).copy()
        door = pygame.transform.scale(door, (36, 45))
        d = t["B"].copy()
        d.blit(door, ((S.STILE - 36) // 2, S.STILE - 45))
        t["D"] = d
    # 精灵球桌 = 桌子 + 平滑球体
    ball_small = _draw_smooth_ball(16)
    for k in "123":
        s = t["t"].copy()
        s.blit(ball_small, (16, 8))
        t[k] = pygame.transform.scale(s, (S.STILE, S.STILE))
    # 花丛 = 官方草地 + 程序花朵点缀
    if "." in t:
        fl = t["."].copy()
        rng = random.Random(7)
        for _ in range(4):
            x, y = rng.randrange(8, 40), rng.randrange(8, 40)
            col = (225, 60, 60) if rng.random() < 0.5 else (250, 250, 244)
            for dx, dy in ((0, 0), (-3, 0), (3, 0), (0, -3), (0, 3)):
                for w in (-1, 0, 1):
                    fl.set_at((x + dx + w, y + dy), col)
                    fl.set_at((x + dx, y + dy + w), col)
            fl.set_at((x, y), (250, 214, 90))
        t["f"] = fl
    return t

def _draw_smooth_ball(size=48):
    """程序化高分辨率精灵球:4x 超采样 + 分区填色 + 高光/阴影,非像素风。"""
    ss = 4
    R = size * ss
    s = _surf(R, R)
    c = R // 2
    r = int(R * 0.47)
    # 外圈描边
    pygame.draw.circle(s, (30, 30, 38), (c, c), r)
    rad = r - int(1.5 * ss)
    # 底半白
    pygame.draw.circle(s, (242, 240, 234), (c, c), rad)
    # 顶半红(set_clip 到上半)
    s.set_clip(pygame.Rect(0, 0, R, c))
    pygame.draw.circle(s, (226, 56, 50), (c, c), rad)
    # 红区深浅过渡
    pygame.draw.circle(s, (196, 40, 40), (c, int(c + rad * 0.25)), int(rad * 0.98))
    s.set_clip(pygame.Rect(0, 0, R, c))
    pygame.draw.circle(s, (226, 56, 50), (c, c), rad)
    pygame.draw.circle(s, (244, 108, 96), (int(c - rad * 0.28), int(c - rad * 0.34)),
                       int(rad * 0.34))
    s.set_clip(None)
    # 底部内阴影
    sh = _surf(R, R)
    pygame.draw.circle(sh, (70, 60, 70, 60), (c, int(c + rad * 0.35)), rad)
    sh.set_clip(pygame.Rect(0, c - int(2 * ss), R, R))
    s.blit(sh, (0, 0))
    # 中缝黑带
    band_h = int(4.6 * ss)
    pygame.draw.rect(s, (30, 30, 38), (c - rad, c - band_h // 2, rad * 2, band_h))
    # 按钮
    br = int(3.4 * ss)
    pygame.draw.circle(s, (30, 30, 38), (c, c), br + int(1.2 * ss))
    pygame.draw.circle(s, (200, 200, 206), (c, c), br)
    pygame.draw.circle(s, (250, 250, 250), (c, c), int(br * 0.62))
    # 顶部高光
    gl = _surf(R, R)
    pygame.draw.ellipse(gl, (255, 255, 255, 88),
                        (int(c - rad * 0.55), int(c - rad * 0.62),
                         int(rad * 0.72), int(rad * 0.42)))
    gl.set_clip(pygame.Rect(0, 0, R, c - band_h // 2))
    s.blit(gl, (0, 0))
    return pygame.transform.smoothscale(s, (size, size))


BALL_DIR = os.path.join(S.ROOT, "assets", "balls")

# 官方道具图标(PokeAPI/sprites,网络可用时 fetch_balls.py 一键下载后自动启用)
OFFICIAL_BALL_FILES = {
    "精灵球": "poke-ball.png",
    "超级球": "great-ball.png",
    "高级球": "ultra-ball.png",
    "大师球": "master-ball.png",
}


def build_balls(size=48):
    """{中文名: Surface}。assets/balls/ 有官方图标用官方,否则程序化平滑球。"""
    out = {}
    os.makedirs(BALL_DIR, exist_ok=True)
    fallback = None
    for name, fname in OFFICIAL_BALL_FILES.items():
        surf = None
        path = os.path.join(BALL_DIR, fname)
        if os.path.exists(path):
            try:
                img = pygame.image.load(path).convert_alpha()
                w, h = img.get_size()
                k = size / max(w, h)
                surf = pygame.transform.smoothscale(img, (max(1, int(w * k)), max(1, int(h * k))))
            except Exception:
                surf = None
        if surf is None:
            if fallback is None:
                fallback = _draw_smooth_ball(size)
            surf = fallback
        out[name] = surf
    return out


def build_ball(size=48):
    return _draw_smooth_ball(size)


def build_battle_bg():
    """战斗背景:天空渐变 + 草地 + 两个站台。"""
    w, h = S.WIN_W, S.WIN_H - 130
    s = _surf(w, h)
    for y in range(h):
        r = 186 - 30 * y // h
        g = 216 - 20 * y // h
        b = 242 - 12 * y // h
        pygame.draw.line(s, (r, g, b), (0, y), (w, y))
    ground_y = int(h * 0.62)
    pygame.draw.rect(s, (154, 204, 122), (0, ground_y, w, h - ground_y))
    for x0, y0, rx, ry, col in ((w - 250, int(h * 0.42), 190, 44, (172, 216, 140)),
                                (250, int(h * 0.86), 230, 52, (162, 206, 130))):
        pygame.draw.ellipse(s, col, (x0 - rx // 2, y0 - ry // 2, rx, ry))
        pygame.draw.ellipse(s, (120, 168, 100), (x0 - rx // 2, y0 - ry // 2, rx, ry), 3)
    return s
