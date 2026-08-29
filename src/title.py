"""标题界面。"""
import os

import pygame

from . import settings as S
from .ui import draw_text, panel, cursor_arrow


class Title:
    def __init__(self, game):
        self.game = game
        self.t = 0.0
        self.has_save = os.path.exists(S.SAVE_PATH)
        self.options = ["继续冒险"] if self.has_save else []
        self.options.append("新的冒险")
        self.idx = 0
        self.mons = ["sprout", "foxf", "turtle", "pika", "bird", "rock"]

    def handle_event(self, e):
        if e.type != pygame.KEYDOWN:
            return
        if e.key in (pygame.K_UP, pygame.K_w):
            self.idx = (self.idx - 1) % len(self.options)
        elif e.key in (pygame.K_DOWN, pygame.K_s):
            self.idx = (self.idx + 1) % len(self.options)
        elif e.key in (pygame.K_z, pygame.K_RETURN, pygame.K_SPACE):
            if self.options[self.idx] == "继续冒险":
                self.game.load()
            else:
                self.game.new_game()

    def update(self, dt):
        self.t += dt

    def draw(self, surf):
        for y in range(S.WIN_H):
            r = 24 + 30 * y // S.WIN_H
            g = 34 + 44 * y // S.WIN_H
            b = 66 + 70 * y // S.WIN_H
            pygame.draw.line(surf, (r, g, b), (0, y), (S.WIN_W, y))
        # 巡回展示的精灵
        icons = self.game.assets["icons"]
        for i, art_id in enumerate(self.mons):
            k = (int(self.t * 1.6) + i) % len(self.mons)
            vis = 1.0 if k < 3 else 0.0
            img = icons[art_id]
            big = pygame.transform.scale(img, (72, 72))
            big.set_alpha(int(120 * vis))
            x = 120 + i * 130
            y = 150 + (i % 2) * 26
            surf.blit(big, (x, y))

        draw_text(surf, "星 钻 精 灵", S.WIN_W // 2, 90, 64, color=(255, 240, 200), anchor="center")
        draw_text(surf, "—— 珍珠·钻石风格 致敬 DEMO ——", S.WIN_W // 2, 168, 26,
                  color=(190, 210, 240), anchor="center")

        bw, bh = 300, 64 * len(self.options) + 30
        bx, by = S.WIN_W // 2 - bw // 2, S.WIN_H - bh - 90
        panel(surf, (bx, by, bw, bh), bg=(36, 48, 78))
        for i, opt in enumerate(self.options):
            oy = by + 26 + i * 64
            if i == self.idx:
                cursor_arrow(surf, bx + 46, oy + 18, size=13, color=(255, 210, 110))
            draw_text(surf, opt, bx + 82, oy, 30, color=(235, 240, 250))
        if (self.t * 1.4) % 2 < 1.3:
            draw_text(surf, "按 Z / 回车 确认", S.WIN_W // 2, S.WIN_H - 34, 22,
                      color=(170, 190, 220), anchor="center")
