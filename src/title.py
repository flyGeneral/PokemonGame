"""标题界面:继续/新游戏 → 选择钻石或珍珠版本。"""
import os

import pygame

from . import settings as S
from . import keys as K
from .ui import draw_text, panel, cursor_arrow


class Title:
    def __init__(self, game):
        self.game = game
        self.t = 0.0
        self.has_save = os.path.exists(S.SAVE_PATH)
        self.options = ["继续冒险"] if self.has_save else []
        self.options.append("新的冒险")
        self.idx = 0
        self.stage = "main"
        self.vidx = 0
        self.mons = ["dex387", "dex390", "dex393", "dex483", "dex484", "dex493"]

    def handle_event(self, e):
        if e.type != pygame.KEYDOWN:
            return
        if self.stage == "main":
            if e.key in K.UP:
                self.idx = (self.idx - 1) % len(self.options)
            elif e.key in K.DOWN:
                self.idx = (self.idx + 1) % len(self.options)
            elif e.key in K.A:
                if self.options[self.idx] == "继续冒险":
                    try:
                        self.game.load()
                    except Exception:          # 存档损坏则回到标题
                        self.has_save = False
                        self.options = ["新的冒险"]
                        self.idx = 0
                else:
                    self.stage = "version"
        elif self.stage == "version":
            if e.key in K.LEFT:
                self.vidx = 0
            elif e.key in K.RIGHT:
                self.vidx = 1
            elif e.key in K.A:
                self.game.new_game("D" if self.vidx == 0 else "P")
            elif e.key in K.B:
                self.stage = "main"

    def update(self, dt):
        self.t += dt

    def draw(self, surf):
        for y in range(S.WIN_H):
            r = 24 + 30 * y // S.WIN_H
            g = 34 + 44 * y // S.WIN_H
            b = 66 + 70 * y // S.WIN_H
            pygame.draw.line(surf, (r, g, b), (0, y), (S.WIN_W, y))
        icons = self.game.assets["icons"]
        for i, art_id in enumerate(self.mons):
            k = (int(self.t * 1.6) + i) % len(self.mons)
            vis = 1.0 if k < 3 else 0.0
            img = icons.get(art_id)
            if img:
                big = pygame.transform.scale(img, (72, 72))
                big.set_alpha(int(120 * vis))
                x = 120 + i * 130
                y = 150 + (i % 2) * 26
                surf.blit(big, (x, y))

        draw_text(surf, "神 奥 地 区", S.WIN_W // 2, 80, 64, color=(255, 240, 200), anchor="center")
        draw_text(surf, "—— 宝可梦 钻石·珍珠 复刻 ——", S.WIN_W // 2, 160, 26,
                  color=(190, 210, 240), anchor="center")
        draw_text(surf, "8 道馆 · 四天王 · 冠军竹兰", S.WIN_W // 2, 200, 20,
                  color=(150, 170, 210), anchor="center")

        if self.stage == "main":
            bw, bh = 300, 64 * len(self.options) + 30
            bx, by = S.WIN_W // 2 - bw // 2, S.WIN_H - bh - 90
            panel(surf, (bx, by, bw, bh), bg=(36, 48, 78))
            for i, opt in enumerate(self.options):
                oy = by + 26 + i * 64
                if i == self.idx:
                    cursor_arrow(surf, bx + 46, oy + 18, size=13, color=(255, 210, 110))
                draw_text(surf, opt, bx + 82, oy, 30, color=(235, 240, 250))
            if (self.t * 1.4) % 2 < 1.3:
                draw_text(surf, f"↑↓ 选择  {K.HINT_CONFIRM} 确认", S.WIN_W // 2, S.WIN_H - 34, 22,
                          color=(170, 190, 220), anchor="center")
        else:
            panel(surf, (S.WIN_W // 2 - 320, 230, 640, 300), bg=(36, 48, 78))
            draw_text(surf, "选择版本", S.WIN_W // 2, 250, 30, color=(235, 240, 250), anchor="center")
            for i, (name, legend) in enumerate((("钻石", "帝牙卢卡"), ("珍珠", "帕路奇亚"))):
                cx = S.WIN_W // 2 - 160 + i * 320
                col = (120, 160, 240) if i == 0 else (240, 150, 190)
                pygame.draw.rect(surf, (60, 80, 120) if i == self.vidx else (40, 52, 84),
                                 (cx - 140, 296, 280, 200), border_radius=12)
                pygame.draw.rect(surf, col if i == self.vidx else (90, 110, 150),
                                 (cx - 140, 296, 280, 200), 3, border_radius=12)
                icon = icons.get("dex483" if i == 0 else "dex484")
                if icon:
                    big = pygame.transform.scale(icon, (110, 110))
                    surf.blit(big, (cx - 55, 306))
                draw_text(surf, name, cx, 426, 30, color=(255, 240, 200), anchor="center")
                draw_text(surf, f"传说的宝可梦:{legend}", cx, 464, 18, color=(170, 190, 220), anchor="center")
            draw_text(surf, f"←→ 选择  {K.HINT_CONFIRM} 确认  {K.HINT_CANCEL} 返回", S.WIN_W // 2, S.WIN_H - 60, 20,
                      color=(170, 190, 220), anchor="center")
