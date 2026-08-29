"""UI 层:中文字体、DP 风格面板/文本框、队伍与背包界面。"""
import os

import pygame

from . import settings as S
from .mon import Mon, STATUS_COLORS

_FONT_CACHE = {}
_FONT_CANDIDATES = [
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
]


def get_font(size):
    if size in _FONT_CACHE:
        return _FONT_CACHE[size]
    font = None
    for path in _FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                font = pygame.font.Font(path, size)
                break
            except Exception:
                continue
    if font is None:
        font = pygame.font.Font(None, int(size * 1.3))
    _FONT_CACHE[size] = font
    return font


def draw_text(surf, text, x, y, size=22, color=S.C_UI_TEXT, shadow=True, anchor="tl"):
    font = get_font(size)
    img = font.render(text, True, color)
    rect = img.get_rect()
    if anchor == "tl":
        pos = (x, y)
    elif anchor == "center":
        pos = (x - rect.w // 2, y - rect.h // 2)
    elif anchor == "tr":
        pos = (x - rect.w, y)
    elif anchor == "bl":
        pos = (x, y - rect.h)
    else:
        pos = (x, y)
    if shadow:
        sh = font.render(text, True, S.C_WHITE)
        surf.blit(sh, (pos[0] + 2, pos[1] + 2))
    surf.blit(img, pos)
    return rect


def wrap_text(text, size, max_w):
    """按像素宽度折行(中文逐字,西文按词)。"""
    font = get_font(size)
    lines, cur = [], ""
    for ch in text:
        if ch == "\n":
            lines.append(cur)
            cur = ""
            continue
        if font.size(cur + ch)[0] > max_w and cur:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def panel(surf, rect, bg=S.C_UI_BG, border=S.C_UI_BORDER, inner=S.C_UI_BORDER2):
    """DP 风格双线圆角面板。"""
    x, y, w, h = rect
    pygame.draw.rect(surf, border, (x, y, w, h), border_radius=8)
    pygame.draw.rect(surf, inner, (x + 2, y + 2, w - 4, h - 4), 2, border_radius=6)
    pygame.draw.rect(surf, bg, (x + 4, y + 4, w - 8, h - 8), border_radius=5)


def hp_bar(surf, x, y, w, ratio, h=8):
    ratio = max(0.0, min(1.0, ratio))
    pygame.draw.rect(surf, (70, 90, 110), (x - 2, y - 2, w + 4, h + 4), border_radius=4)
    pygame.draw.rect(surf, (228, 232, 238), (x, y, w, h), border_radius=3)
    col = S.C_HP_GREEN if ratio > 0.5 else S.C_HP_YELLOW if ratio > 0.2 else S.C_HP_RED
    if ratio > 0:
        pygame.draw.rect(surf, col, (x, y, max(4, int(w * ratio)), h), border_radius=3)


def exp_bar(surf, x, y, w, ratio, h=6):
    ratio = max(0.0, min(1.0, ratio))
    pygame.draw.rect(surf, (70, 90, 110), (x - 2, y - 2, w + 4, h + 4), border_radius=3)
    pygame.draw.rect(surf, (228, 232, 238), (x, y, w, h), border_radius=2)
    pygame.draw.rect(surf, S.C_EXP_BLUE, (x, y, int(w * ratio), h), border_radius=2)


def cursor_arrow(surf, x, y, size=11, color=(200, 90, 40)):
    """文字字体缺少 ▶ 字形,用三角形绘制选择光标。y 为垂直中心。"""
    pygame.draw.polygon(surf, color, [(x, y - size // 2), (x, y + size // 2), (x + size, y)])


def down_arrow(surf, x, y, t):
    """闪烁的▼提示。"""
    if (t * 2) % 2 < 1.2:
        col = S.C_UI_BORDER
        for i in range(4):
            pygame.draw.polygon(surf, col, [(x - 8 + i, y + i), (x + 8 - i, y + i), (x, y + 8)])


# ================================================================ 文本框
class TextBox:
    """底部文本框:打字机效果 + 可选选项。"""

    def __init__(self):
        self.text = ""
        self.shown = 0.0
        self.wait_key = False
        self.choices = None
        self.cidx = 0
        self.arrow_t = 0.0
        self.active = False

    def show(self, text, choices=None):
        self.text = text
        self.shown = 0.0
        self.wait_key = False
        self.choices = list(choices) if choices else None
        self.cidx = 0
        self.active = True

    def hide(self):
        self.active = False

    def update(self, dt):
        self.arrow_t += dt
        if not self.wait_key:
            self.shown += dt * 34
            if self.shown >= len(self.text):
                self.shown = float(len(self.text))
                self.wait_key = True

    def key(self, event):
        """返回 None / ("advance",) / ("choice", idx)"""
        if event.key in (pygame.K_z, pygame.K_RETURN):
            if not self.wait_key:
                self.shown = float(len(self.text))
                self.wait_key = True
                return None
            if self.choices is not None:
                return ("choice", self.cidx)
            return ("advance",)
        if event.key in (pygame.K_UP, pygame.K_w) and self.choices and self.wait_key:
            self.cidx = (self.cidx - 1) % len(self.choices)
        if event.key in (pygame.K_DOWN, pygame.K_s) and self.choices and self.wait_key:
            self.cidx = (self.cidx + 1) % len(self.choices)
        return None

    def draw(self, surf):
        if not self.active:
            return
        h = 128
        panel(surf, (6, S.WIN_H - h - 6, S.WIN_W - 12, h))
        lines = wrap_text(self.text[: int(self.shown)], 24, S.WIN_W - 70)
        y = S.WIN_H - h + 10
        for line in lines[:3]:
            draw_text(surf, line, 26, y, 24)
            y += 34
        if self.wait_key and not self.choices:
            down_arrow(surf, S.WIN_W - 60, S.WIN_H - 40, self.arrow_t)
        if self.choices is not None and self.wait_key:
            cw, ch = 240, 40 * len(self.choices) + 20
            cx, cy = S.WIN_W - cw - 24, S.WIN_H - h - ch - 10
            panel(surf, (cx, cy, cw, ch), bg=S.C_MENU_BG)
            for i, opt in enumerate(self.choices):
                oy = cy + 14 + i * 40
                if i == self.cidx:
                    cursor_arrow(surf, cx + 18, oy + 15)
                draw_text(surf, opt, cx + 44, oy, 24)


# ================================================================ 队伍界面
class PartyScreen:
    """mode: menu(查看/调序) / battle(选择出战) / forced(濒倒强制换人)"""

    def __init__(self, game, mode, current_idx=None):
        self.game = game
        self.mode = mode
        self.current_idx = current_idx
        self.cursor = 0
        self.done = False
        self.result = None
        self.submenu = 0      # menu 模式下的子选项光标
        self.in_submenu = False
        self.msg = None

    def _valid_pick(self, m):
        if m.hp <= 0:
            return False
        if self.mode == "battle" and self.current_idx is not None and \
                self.game.party.index(m) == self.current_idx:
            return False
        return True

    def key(self, event):
        party = self.game.party
        if not party:
            self.done = True
            return
        if self.in_submenu:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.submenu = (self.submenu - 1) % 3
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.submenu = (self.submenu + 1) % 3
            elif event.key in (pygame.K_z, pygame.K_RETURN):
                m = party[self.cursor]
                if self.submenu == 0:      # 设为队长
                    if m.hp > 0:
                        party.insert(0, party.pop(self.cursor))
                        self.cursor = 0
                elif self.submenu == 1:    # 详情
                    self.msg = (f"{m.name}  Lv{m.level}  {('/'.join(m.types))}\n"
                                f"HP {m.hp}/{m.max_hp}  攻{m.stats['atk']} 防{m.stats['def']}\n"
                                f"特攻{m.stats['spa']} 特防{m.stats['spd']} 速{m.stats['spe']}")
                self.in_submenu = False
            elif event.key in (pygame.K_x, pygame.K_ESCAPE):
                self.in_submenu = False
            return
        if event.key in (pygame.K_UP, pygame.K_w):
            self.cursor = (self.cursor - 1) % len(party)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.cursor = (self.cursor + 1) % len(party)
        elif event.key in (pygame.K_z, pygame.K_RETURN):
            if self.mode == "menu":
                self.in_submenu = True
                self.submenu = 0
            else:
                m = party[self.cursor]
                if self._valid_pick(m):
                    self.done = True
                    self.result = self.cursor
                else:
                    self.msg = "这只精灵现在不能上场!"
        elif event.key in (pygame.K_x, pygame.K_ESCAPE):
            if self.mode != "forced":
                self.done = True
                self.result = None

    def update(self, dt):
        pass

    def draw(self, surf, icons):
        surf.fill((26, 34, 52))
        draw_text(surf, {"menu": "队伍", "battle": "派出哪只精灵?", "forced": "换谁上场?"}[self.mode],
                  30, 18, 28, color=S.C_WHITE)
        y0 = 60
        for i, m in enumerate(self.game.party):
            r = (24, y0 + i * 74, S.WIN_W - 48, 66)
            bg = S.C_MENU_BG if i == self.cursor else (208, 220, 234)
            pygame.draw.rect(surf, bg, r, border_radius=8)
            pygame.draw.rect(surf, S.C_UI_BORDER if i == self.cursor else (150, 165, 185),
                             r, 2, border_radius=8)
            icon = icons.get(_art_of(m))
            if icon:
                surf.blit(icon, (34, r[1] + 8))
            draw_text(surf, m.name, 110, r[1] + 8, 24)
            tag = m.status_tag
            if tag:
                c = STATUS_COLORS.get(m.status, (120, 120, 130))
                pygame.draw.rect(surf, c, (S.WIN_W - 160, r[1] + 10, 44, 26), border_radius=5)
                draw_text(surf, tag, S.WIN_W - 138, r[1] + 12, 20, color=S.C_WHITE, shadow=False, anchor="center")
            draw_text(surf, f"Lv{m.level}", 110, r[1] + 34, 20, color=(90, 100, 120))
            hpbar_w = 320
            hp_bar(surf, 330, r[1] + 40, hpbar_w, m.hp / m.max_hp)
            draw_text(surf, f"{m.hp}/{m.max_hp}", 330 + hpbar_w + 14, r[1] + 30, 20)
        if self.in_submenu:
            cw, ch = 240, 3 * 40 + 20
            cx, cy = S.WIN_W - cw - 30, S.WIN_H - ch - 40
            panel(surf, (cx, cy, cw, ch), bg=S.C_MENU_BG)
            for i, opt in enumerate(("设为队长", "详情", "取消")):
                oy = cy + 14 + i * 40
                if i == self.submenu:
                    cursor_arrow(surf, cx + 18, oy + 15)
                draw_text(surf, opt, cx + 44, oy, 24)
        elif self.msg:
            panel(surf, (60, S.WIN_H - 150, S.WIN_W - 120, 110))
            y = S.WIN_H - 138
            for line in self.msg.split("\n"):
                draw_text(surf, line, 84, y, 22)
                y += 30
            draw_text(surf, "Z 关闭", S.WIN_W - 150, S.WIN_H - 70, 20, color=(90, 110, 140))
        draw_text(surf, "Z 确认  X 返回", S.WIN_W - 200, S.WIN_H - 30, 18, color=(150, 165, 185))


def _art_of(m):
    from . import data
    return data.SPECIES[m.species]["art"]


# ================================================================ 背包
class BagScreen:
    """mode: menu / battle。result: 选中道具名 或 None"""

    def __init__(self, game, mode):
        self.game = game
        self.mode = mode
        self.items = [n for n in game.bag_order() if game.bag.get(n, 0) > 0]
        self.cursor = 0
        self.done = False
        self.result = None

    def key(self, event):
        if not self.items:
            if event.key in (pygame.K_z, pygame.K_x, pygame.K_RETURN, pygame.K_ESCAPE):
                self.done = True
            return
        if event.key in (pygame.K_UP, pygame.K_w):
            self.cursor = (self.cursor - 1) % len(self.items)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.cursor = (self.cursor + 1) % len(self.items)
        elif event.key in (pygame.K_z, pygame.K_RETURN):
            self.done = True
            self.result = self.items[self.cursor]
        elif event.key in (pygame.K_x, pygame.K_ESCAPE):
            self.done = True

    def update(self, dt):
        pass

    def draw(self, surf):
        surf.fill((26, 34, 52))
        draw_text(surf, "背包", 30, 18, 28, color=S.C_WHITE)
        if not self.items:
            draw_text(surf, "口袋里空空如也……", 60, 120, 24, color=S.C_WHITE)
        for i, name in enumerate(self.items):
            r = (24, 60 + i * 52, S.WIN_W - 48, 44)
            bg = S.C_MENU_BG if i == self.cursor else (208, 220, 234)
            pygame.draw.rect(surf, bg, r, border_radius=8)
            pygame.draw.rect(surf, S.C_UI_BORDER if i == self.cursor else (150, 165, 185),
                             r, 2, border_radius=8)
            draw_text(surf, name, 44, r[1] + 8, 24)
            draw_text(surf, f"×{self.game.bag[name]}", S.WIN_W - 90, r[1] + 8, 24,
                      color=(90, 100, 120))
        if self.items:
            desc = _item_desc(self.items[self.cursor])
            panel(surf, (24, S.WIN_H - 100, S.WIN_W - 48, 72))
            draw_text(surf, desc, 48, S.WIN_H - 84, 22)
        draw_text(surf, "Z 使用  X 返回", S.WIN_W - 200, S.WIN_H - 26, 18, color=(150, 165, 185))


def _item_desc(name):
    from . import data
    return data.ITEMS.get(name, {}).get("desc", "")
