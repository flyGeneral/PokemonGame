"""UI 层:中文字体、DP 风格面板/文本框、队伍/背包/商店/学习招式/徽章/飞翔界面。"""
import os

import pygame

from . import data
from . import keys as K
from . import settings as S
from .mon import Mon, STATUS_COLORS

_FONT_CACHE = {}
TEXT_SPEED = 1.0            # 文本打字速度倍率(自动试玩会调高)
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


def type_badge(surf, x, y, t, size=18, w=48):
    col = S.TYPE_COLOR.get(t, (120, 120, 120))
    pygame.draw.rect(surf, col, (x, y, w, size + 4), border_radius=5)
    draw_text(surf, t, x + w // 2, y + 2, size, color=S.C_WHITE, shadow=False, anchor="center")


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
            self.shown += dt * 34 * TEXT_SPEED
            if self.shown >= len(self.text):
                self.shown = float(len(self.text))
                self.wait_key = True

    def key(self, event):
        """返回 None / ("advance",) / ("choice", idx)。A 确定;是/否选择中按 B 直接选「否」。"""
        if event.key in K.A:
            if not self.wait_key:
                self.shown = float(len(self.text))
                self.wait_key = True
                return None
            if self.choices is not None:
                return ("choice", self.cidx)
            return ("advance",)
        if event.key in K.B and self.wait_key and self.choices == ["是", "否"]:
            self.cidx = 1
            return ("choice", 1)
        if event.key in K.UP and self.choices and self.wait_key:
            self.cidx = (self.cidx - 1) % len(self.choices)
        if event.key in K.DOWN and self.choices and self.wait_key:
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
    """mode: menu(查看/调序) / battle(选择出战) / forced(濒倒强制换人) / target(道具目标)"""
    MODE_TITLE = {"menu": "队伍", "battle": "派出哪只精灵?", "forced": "换谁上场?", "target": "对哪只精灵使用?"}

    def __init__(self, game, mode, current_idx=None, allow_fainted=False):
        self.game = game
        self.mode = mode
        self.current_idx = current_idx
        self.allow_fainted = allow_fainted or mode == "target"
        self.cursor = next((i for i, m in enumerate(game.party) if m.hp > 0), 0)
        self.done = False
        self.result = None
        self.submenu = 0
        self.in_submenu = False
        self.msg = None

    def _valid_pick(self, m):
        if self.mode in ("battle", "forced") and m.hp <= 0:
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
            if event.key in K.UP:
                self.submenu = (self.submenu - 1) % 3
            elif event.key in K.DOWN:
                self.submenu = (self.submenu + 1) % 3
            elif event.key in K.A:
                m = party[self.cursor]
                if self.submenu == 0:      # 设为队长
                    if m.hp > 0:
                        party.insert(0, party.pop(self.cursor))
                        self.cursor = 0
                elif self.submenu == 1:    # 详情
                    self.msg = (f"{m.name}  Lv{m.level}  {'/'.join(m.types)}  "
                                f"{'♂' if m.gender == 'm' else '♀'}\n"
                                f"HP {m.hp}/{m.max_hp}  攻{m.stats['atk']} 防{m.stats['def']} "
                                f"特攻{m.stats['spa']} 特防{m.stats['spd']} 速{m.stats['spe']}\n"
                                f"经验 {m.exp}/{data.exp_for_level(m.level + 1, m.growth)}  "
                                f"下一级还需 {data.exp_to_next(m.level, m.growth) - (m.exp - data.exp_for_level(m.level, m.growth))}")
                self.in_submenu = False
            elif event.key in K.B:
                self.in_submenu = False
            return
        if event.key in K.UP:
            self.cursor = (self.cursor - 1) % len(party)
        elif event.key in K.DOWN:
            self.cursor = (self.cursor + 1) % len(party)
        elif event.key in K.A:
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
        elif event.key in K.B:
            if self.mode != "forced":
                self.done = True
                self.result = None

    def update(self, dt):
        pass

    def draw(self, surf, icons):
        surf.fill((26, 34, 52))
        draw_text(surf, self.MODE_TITLE[self.mode], 30, 18, 28, color=S.C_WHITE)
        y0 = 60
        for i, m in enumerate(self.game.party):
            r = (24, y0 + i * 74, S.WIN_W - 48, 66)
            bg = S.C_MENU_BG if i == self.cursor else (208, 220, 234)
            if m.hp <= 0:
                bg = tuple(int(c * 0.75) for c in bg)
            pygame.draw.rect(surf, bg, r, border_radius=8)
            pygame.draw.rect(surf, S.C_UI_BORDER if i == self.cursor else (150, 165, 185),
                             r, 2, border_radius=8)
            icon = icons.get(_art_of(m))
            if icon:
                surf.blit(icon, (34, r[1] + 8))
            draw_text(surf, m.name, 110, r[1] + 8, 24)
            draw_text(surf, "♂" if m.gender == "m" else "♀", 110 + get_font(24).size(m.name)[0] + 6, r[1] + 10, 18,
                      color=(60, 110, 220) if m.gender == "m" else (220, 80, 140), shadow=False)
            tag = m.status_tag
            if tag:
                c = STATUS_COLORS.get(m.status, (120, 120, 130))
                pygame.draw.rect(surf, c, (S.WIN_W - 160, r[1] + 10, 44, 26), border_radius=5)
                draw_text(surf, tag, S.WIN_W - 138, r[1] + 12, 18, color=S.C_WHITE, shadow=False, anchor="center")
            draw_text(surf, f"Lv{m.level}", 110, r[1] + 34, 20, color=(90, 100, 120))
            hpbar_w = 320
            hp_bar(surf, 330, r[1] + 40, hpbar_w, m.hp / m.max_hp)
            draw_text(surf, f"{m.hp}/{m.max_hp}", 330 + hpbar_w + 14, r[1] + 30, 20)
            x = 640
            for mv in m.moves:
                md = data.MOVES[mv.name]
                pygame.draw.rect(surf, S.TYPE_COLOR.get(md["type"], (120, 120, 120)), (x, r[1] + 36, 56, 22), border_radius=4)
                draw_text(surf, mv.name[:3], x + 28, r[1] + 37, 15, color=S.C_WHITE, shadow=False, anchor="center")
                x += 62
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
            draw_text(surf, K.HINT_CLOSE, S.WIN_W - 150, S.WIN_H - 70, 20, color=(90, 110, 140))
        draw_text(surf, K.HINT_UI, S.WIN_W - 200, S.WIN_H - 30, 18, color=(150, 165, 185))


def _art_of(m):
    return data.SPECIES[m.species]["art"]


# ================================================================ 背包
KIND_ORDER = ["ball", "heal", "fullheal", "cure", "revive", "pp", "ppall", "stat", "crit", "evo", "tm", "key",
              "repel"]
KIND_CN = {"ball": "精灵球", "heal": "伤药", "fullheal": "回复", "cure": "状态药", "revive": "复苏",
           "pp": "PP 回复", "ppall": "PP 回复", "stat": "战斗道具", "crit": "战斗道具", "evo": "进化道具",
           "tm": "招式学习机", "key": "重要道具", "repel": "喷雾"}


class BagScreen:
    """mode: menu / battle。result: 选中道具名 或 None。按道具类别排序。"""

    def __init__(self, game, mode, pocket=None):
        self.game = game
        self.mode = mode
        self.items = game.bag_order(pocket)
        self.cursor = 0
        self.done = False
        self.result = None
        self.scroll = 0

    def key(self, event):
        if not self.items:
            if event.key in K.A or event.key in K.B:
                self.done = True
            return
        n = len(self.items)
        if event.key in K.UP:
            self.cursor = (self.cursor - 1) % n
        elif event.key in K.DOWN:
            self.cursor = (self.cursor + 1) % n
        elif event.key in K.A:
            self.done = True
            self.result = self.items[self.cursor]
        elif event.key in K.B:
            self.done = True
        if self.cursor < self.scroll:
            self.scroll = self.cursor
        if self.cursor >= self.scroll + 9:
            self.scroll = self.cursor - 8

    def update(self, dt):
        pass

    def draw(self, surf):
        surf.fill((26, 34, 52))
        draw_text(surf, "背包", 30, 18, 28, color=S.C_WHITE)
        draw_text(surf, f"¥{getattr(self.game, 'money', 0)}", S.WIN_W - 30, 22, 24, color=(255, 214, 110), anchor="tr")
        if not self.items:
            draw_text(surf, "口袋里空空如也……", 60, 120, 24, color=S.C_WHITE)
        visible = self.items[self.scroll:self.scroll + 9]
        last_kind = None
        for j, name in enumerate(visible):
            kind = data.ITEMS[name]["kind"]
            y = 60 + j * 52
            r = (24, y, S.WIN_W - 300, 44)
            i = self.scroll + j
            bg = S.C_MENU_BG if i == self.cursor else (208, 220, 234)
            pygame.draw.rect(surf, bg, r, border_radius=8)
            pygame.draw.rect(surf, S.C_UI_BORDER if i == self.cursor else (150, 165, 185), r, 2, border_radius=8)
            if kind != last_kind:
                draw_text(surf, KIND_CN.get(kind, ""), 34, y + 10, 18, color=(120, 100, 160))
            draw_text(surf, name, 130, y + 8, 24)
            draw_text(surf, f"×{self.game.bag[name]}", S.WIN_W - 280, y + 8, 24, color=(90, 100, 120), anchor="tr")
            last_kind = kind
        if self.items:
            name = self.items[self.cursor]
            item = data.ITEMS[name]
            px, py = S.WIN_W - 262, 60
            panel(surf, (px, py, 238, 300), bg=S.C_MENU_BG)
            draw_text(surf, name, px + 18, py + 14, 24)
            draw_text(surf, KIND_CN.get(item["kind"], ""), px + 18, py + 48, 18, color=(90, 100, 120))
            if item["kind"] == "tm":
                md = data.MOVES[item["move"]]
                type_badge(surf, px + 18, py + 76, md["type"])
                draw_text(surf, f"威力 {md['power'] or '—'}  命中 {md['acc'] if md['acc'] is not None else '必中'}",
                          px + 18, py + 106, 18)
            elif item["kind"] == "ball":
                rate = item["rate"]
                draw_text(surf, f"捕获率 ×{rate:g}" if isinstance(rate, (int, float)) else "特殊精灵球",
                          px + 18, py + 76, 18)
            elif item.get("amount"):
                draw_text(surf, f"恢复 {item['amount']} HP", px + 18, py + 76, 18)
            for k, line in enumerate(wrap_text(item.get("desc", ""), 18, 200)[:6]):
                draw_text(surf, line, px + 18, py + 140 + k * 26, 18, color=(60, 70, 90))
        draw_text(surf, f"{K.HINT_CONFIRM} 使用/选择   {K.HINT_CANCEL} 返回", S.WIN_W - 40, S.WIN_H - 30, 18,
                  color=(150, 165, 185), anchor="tr")


def _item_desc(name):
    return data.ITEMS.get(name, {}).get("desc", "")


# ================================================================ 学习招式
class LearnMoveScreen:
    """想要学习新招式但已有 4 招:选择忘记哪一招(None = 放弃学习)。"""

    def __init__(self, mon, move):
        self.mon = mon
        self.move = move
        self.cursor = 0
        self.done = False
        self.result = None

    def key(self, event):
        n = len(self.mon.moves) + 1
        if event.key in K.UP:
            self.cursor = (self.cursor - 1) % n
        elif event.key in K.DOWN:
            self.cursor = (self.cursor + 1) % n
        elif event.key in K.B:
            self.done = True
            self.result = None
        elif event.key in K.A:
            self.done = True
            self.result = self.cursor if self.cursor < n - 1 else None

    def draw(self, surf):
        dim = pygame.Surface((S.WIN_W, S.WIN_H), pygame.SRCALPHA)
        dim.fill((10, 16, 30, 150))
        surf.blit(dim, (0, 0))
        w, h = 620, 92 + 44 * (len(self.mon.moves) + 1)
        x, y = (S.WIN_W - w) // 2, (S.WIN_H - h) // 2
        panel(surf, (x, y, w, h), bg=S.C_MENU_BG)
        draw_text(surf, f"{self.mon.name}想学习{self.move},\n但已经会 4 招了。要忘记哪一招?", x + 24, y + 16, 22)
        yy = y + 92
        for i, mv in enumerate(self.mon.moves):
            if i == self.cursor:
                cursor_arrow(surf, x + 30, yy + 16)
            draw_text(surf, mv.name, x + 54, yy, 24)
            md = data.MOVES[mv.name]
            type_badge(surf, x + 240, yy + 2, md["type"], w=56)
            draw_text(surf, f"威力 {md['power'] or '—'}", x + 320, yy + 2, 20, color=(90, 100, 120))
            yy += 44
        if self.cursor == len(self.mon.moves):
            cursor_arrow(surf, x + 30, yy + 16)
        draw_text(surf, f"不学习{self.move}", x + 54, yy, 24, color=(180, 60, 60))


# ================================================================ 商店
class ShopScreen:
    """友好商店:上下选商品,左右调数量,A 购买,B 离开。"""

    def __init__(self, game, stock, title="友好商店"):
        self.game = game
        self.stock = stock            # [(道具名, 单价)]
        self.title = title
        self.idx = 0
        self.qty = 1
        self.done = False
        self.msg = None
        self.scroll = 0

    def key(self, event):
        if event.key in K.UP:
            self.idx = (self.idx - 1) % len(self.stock)
            self.qty = 1
        elif event.key in K.DOWN:
            self.idx = (self.idx + 1) % len(self.stock)
            self.qty = 1
        elif event.key in K.LEFT:
            self.qty = max(1, self.qty - 1)
        elif event.key in K.RIGHT:
            self.qty = min(99, self.qty + 1)
        elif event.key in K.A:
            name, price = self.stock[self.idx]
            cost = price * self.qty
            if self.game.money < cost:
                self.msg = "钱不够……"
            else:
                self.game.money -= cost
                self.game.give_item(name, self.qty)
                self.msg = f"买下了{name}×{self.qty}!"
        elif event.key in K.B:
            self.done = True
        if self.idx < self.scroll:
            self.scroll = self.idx
        if self.idx >= self.scroll + 8:
            self.scroll = self.idx - 7

    def update(self, dt):
        pass

    def draw(self, surf):
        surf.fill((26, 34, 52))
        draw_text(surf, self.title, 30, 16, 28, color=S.C_WHITE)
        draw_text(surf, f"所持金  ¥{self.game.money}", S.WIN_W - 40, 22, 24,
                  color=(255, 214, 110), anchor="tr")
        panel(surf, (24, 60, 560, min(len(self.stock) * 48 + 24, S.WIN_H - 140)))
        for j in range(self.scroll, min(len(self.stock), self.scroll + 8)):
            name, price = self.stock[j]
            r = (36, 72 + (j - self.scroll) * 48, 536, 42)
            if j == self.idx:
                pygame.draw.rect(surf, (255, 232, 150), r, border_radius=6)
                cursor_arrow(surf, 48, 72 + (j - self.scroll) * 48 + 21)
            owned = self.game.bag.get(name, 0)
            col = S.C_UI_TEXT if j == self.idx else (90, 100, 120)
            draw_text(surf, name, 66, 78 + (j - self.scroll) * 48, 22, color=col, shadow=False)
            draw_text(surf, f"¥{price}", 380, 78 + (j - self.scroll) * 48, 22, color=col, shadow=False)
            draw_text(surf, f"持有{owned}", 540, 78 + (j - self.scroll) * 48, 18, color=col, shadow=False, anchor="tr")
        name, price = self.stock[self.idx]
        panel(surf, (600, 60, S.WIN_W - 624, 250), bg=S.C_MENU_BG)
        draw_text(surf, name, 624, 76, 24)
        draw_text(surf, f"单价 ¥{price}", 624, 110, 20, color=(90, 100, 120))
        draw_text(surf, f"数量 ←{self.qty}→", 624, 140, 24)
        draw_text(surf, f"合计 ¥{price * self.qty}", 624, 172, 22,
                  color=(200, 90, 40) if price * self.qty > self.game.money else S.C_UI_TEXT)
        for k, line in enumerate(wrap_text(_item_desc(name), 17, S.WIN_W - 660)[:4]):
            draw_text(surf, line, 624, 206 + k * 24, 17, color=(110, 120, 140))
        if self.msg:
            panel(surf, (600, 320, S.WIN_W - 624, 70), bg=S.C_MENU_BG)
            draw_text(surf, self.msg, 624, 338, 22)
        draw_text(surf, f"{K.HINT_CONFIRM} 购买  ←→ 数量  {K.HINT_CANCEL} 离开", S.WIN_W - 40, S.WIN_H - 34, 20,
                  color=(150, 165, 185), anchor="tr")


# ================================================================ 徽章盒
class BadgeScreen:
    def __init__(self, game):
        self.game = game
        self.cursor = 0
        self.done = False

    def key(self, event):
        n = len(data.BADGES)
        if event.key in K.RIGHT:
            self.cursor = (self.cursor + 1) % n
        elif event.key in K.LEFT:
            self.cursor = (self.cursor - 1) % n
        elif event.key in K.DOWN:
            self.cursor = (self.cursor + 4) % n
        elif event.key in K.UP:
            self.cursor = (self.cursor - 4) % n
        elif event.key in K.A or event.key in K.B:
            self.done = True

    def update(self, dt):
        pass

    def draw(self, surf):
        surf.fill((26, 34, 52))
        got = sum(1 for f, *_ in data.BADGES if self.game.flags.get(f))
        draw_text(surf, f"徽章盒  {got}/8", 30, 18, 28, color=S.C_WHITE)
        for i, (flag, name, label, col) in enumerate(data.BADGES):
            x = 90 + (i % 4) * 200
            y = 110 + (i // 4) * 180
            has = self.game.flags.get(flag)
            r = (x - 70, y - 40, 140, 110)
            pygame.draw.rect(surf, (245, 240, 220) if has else (90, 96, 110), r, border_radius=14)
            pygame.draw.rect(surf, S.C_UI_BORDER if i == self.cursor else (150, 165, 185), r, 3, border_radius=14)
            if has:
                pygame.draw.polygon(surf, col, [(x, y - 24), (x + 22, y), (x, y + 24), (x - 22, y)])
                pygame.draw.polygon(surf, (255, 255, 255), [(x, y - 16), (x + 14, y), (x, y + 16), (x - 14, y)])
                draw_text(surf, label, x, y, 18, color=(40, 30, 20), anchor="center", shadow=False)
                draw_text(surf, name, x, y + 36, 18, anchor="center")
            else:
                draw_text(surf, "???", x, y, 22, color=(200, 200, 210), anchor="center")
        draw_text(surf, f"←→↑↓ 查看  {K.HINT_CONFIRM}/{K.HINT_CANCEL} 返回", S.WIN_W - 40, S.WIN_H - 30, 18,
                  color=(150, 165, 185), anchor="tr")


# ================================================================ 飞翔
class ListScreen:
    """通用列表选择:opts 为 [(显示文本, 值)],返回 value 或 None。"""

    def __init__(self, title, opts, hint=K.HINT_UI):
        self.title = title
        self.opts = opts
        self.hint = hint
        self.cursor = 0
        self.done = False
        self.result = None

    def key(self, event):
        if not self.opts:
            if event.key in K.A or event.key in K.B:
                self.done = True
            return
        n = len(self.opts)
        if event.key in K.UP:
            self.cursor = (self.cursor - 1) % n
        elif event.key in K.DOWN:
            self.cursor = (self.cursor + 1) % n
        elif event.key in K.A:
            self.done = True
            self.result = self.opts[self.cursor][1]
        elif event.key in K.B:
            self.done = True

    def update(self, dt):
        pass

    def draw(self, surf):
        surf.fill((26, 34, 52))
        draw_text(surf, self.title, 30, 18, 28, color=S.C_WHITE)
        cols = 2 if len(self.opts) > 8 else 1
        per_col = (len(self.opts) + cols - 1) // cols
        for i, (text, _) in enumerate(self.opts):
            c, r = i // per_col, i % per_col
            x = 60 + c * 440
            y = 80 + r * 52
            if i == self.cursor:
                pygame.draw.rect(surf, S.C_MENU_BG, (x - 20, y - 10, 400, 44), border_radius=8)
                cursor_arrow(surf, x - 8, y + 12)
            draw_text(surf, text, x + 16, y, 24)
        draw_text(surf, self.hint, S.WIN_W - 40, S.WIN_H - 30, 18, color=(150, 165, 185), anchor="tr")

