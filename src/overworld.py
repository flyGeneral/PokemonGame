"""世界场景:格子移动、图块绘制、NPC 交互、遇敌、菜单/队伍/背包/初始选择。"""
import random

import pygame

from . import settings as S
from . import worldmap
from . import data
from .mon import Mon
from .ui import (TextBox, PartyScreen, BagScreen, panel, draw_text, hp_bar, _art_of,
                 cursor_arrow)

SOLID_OVERLAY = "TfFS"
STEP_TIME = 0.22
ENCOUNTER_RATE = 0.12
MOVE_KEYS = (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s,
             pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d)


def _face_back(nx, ny, px, py):
    if px < nx:
        return "left"
    if px > nx:
        return "right"
    if py < ny:
        return "up"
    return "down"


class StarterUI:
    """三只初始精灵的选择界面。"""

    def __init__(self):
        self.opts = list(worldmap.STARTER_BALLS)
        self.cursor = 0
        self.confirm = False
        self.cidx = 0
        self.done = False
        self.result = None

    def key(self, event, icons):
        if not self.confirm:
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self.cursor = (self.cursor - 1) % 3
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.cursor = (self.cursor + 1) % 3
            elif event.key in (pygame.K_z, pygame.K_RETURN):
                self.confirm = True
                self.cidx = 0
            elif event.key in (pygame.K_x, pygame.K_ESCAPE):
                self.done = True
        else:
            if event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
                self.cidx = 1 - self.cidx
            elif event.key in (pygame.K_z, pygame.K_RETURN):
                self.done = True
                self.result = self.opts[self.cursor] if self.cidx == 0 else None
            elif event.key in (pygame.K_x, pygame.K_ESCAPE):
                self.confirm = False

    def draw(self, surf, icons):
        dim = pygame.Surface((S.WIN_W, S.WIN_H), pygame.SRCALPHA)
        dim.fill((10, 16, 30, 150))
        surf.blit(dim, (0, 0))
        w, h = 620, 380
        x, y = (S.WIN_W - w) // 2, (S.WIN_H - h - 130) // 2
        panel(surf, (x, y, w, h), bg=S.C_MENU_BG)
        draw_text(surf, "选择你的伙伴!", S.WIN_W // 2, y + 22, 28, anchor="center")
        sp = w // 3
        for i, name in enumerate(self.opts):
            cx = x + sp * i + sp // 2
            r = (cx - 86, y + 64, 172, 170)
            bg = (255, 232, 150) if i == self.cursor else (214, 226, 240)
            pygame.draw.rect(surf, bg, r, border_radius=10)
            pygame.draw.rect(surf, (200, 90, 40) if i == self.cursor else S.C_UI_BORDER2,
                             r, 3, border_radius=10)
            icon = icons.get(_art_of_mon(name))
            if icon:
                big = pygame.transform.scale(icon, (96, 96))
                surf.blit(big, (cx - 48, y + 76))
            draw_text(surf, name, cx, y + 186, 24, anchor="center")
            draw_text(surf, "/".join(data.SPECIES[name]["types"]), cx, y + 212, 20,
                      color=(110, 120, 140), anchor="center")
        sp_name = self.opts[self.cursor]
        draw_text(surf, data.SPECIES[sp_name]["desc"], x + w // 2, y + h - 44, 22, anchor="center")
        if self.confirm:
            cw, ch = 220, 108
            cx, cy = S.WIN_W // 2 - cw // 2, y + h + 16
            panel(surf, (cx, cy, cw, ch), bg=S.C_MENU_BG)
            draw_text(surf, f"就决定是{sp_name}了?", S.WIN_W // 2, cy + 14, 24, anchor="center")
            for i, opt in enumerate(("是", "否")):
                ox = S.WIN_W // 2 - 60 + i * 120
                if i == self.cidx:
                    cursor_arrow(surf, ox - 22, cy + 66)
                draw_text(surf, opt, ox, cy + 52, 24, anchor="center")


def _art_of_mon(species):
    return data.SPECIES[species]["art"]


class Overworld:
    def __init__(self, game, map_id="town", x=10, y=12, facing="down"):
        self.game = game
        self.map_id = map_id
        self.px, self.py = x, y
        self.dir = facing
        self.moving = False
        self.step_from = (x, y)
        self.step_t = 0.0
        self.water_t = 0.0
        self.state = "field"          # field/dialog/menu/party/bag/starter
        self.textbox = TextBox()
        self.script = None
        self.script_after_battle = None
        self.menu_idx = 0
        self.party_screen = None
        self.bag_screen = None
        self.bag_pending_item = None
        self.starter = None
        self.fade_t = -1.0            # 黑屏倒计时
        self.notice = None
        self._sent_once = False
        self._blackout_done = False
        self.held = set()

    # -------------------------------------------------- 地图/位置
    @property
    def map(self):
        return worldmap.MAPS[self.map_id]

    def warp_to(self, map_id, x, y, facing):
        self.map_id = map_id
        self.px, self.py = x, y
        self.dir = facing
        self.moving = False

    # -------------------------------------------------- 脚本运行
    def start_script(self, gen):
        self.script = gen
        self.state = "dialog"
        self._sent_once = False
        self._pump(None)

    def _pump(self, value):
        """推进脚本生成器,直到需要等待输入或结束。"""
        while True:
            try:
                item = self.script.send(value) if self._sent_once else next(self.script)
            except StopIteration:
                self.script = None
                if self.state == "dialog":
                    self.state = "field"
                self.textbox.hide()
                return
            self._sent_once = True
            kind = item[0]
            value = None
            if kind == "msg":
                self.textbox.show(item[1])
                return
            elif kind in ("choice", "yesno"):
                opts = item[1] if kind == "choice" else ["是", "否"]
                self.textbox.show("", choices=opts)
                return
            elif kind == "starter":
                self.starter = StarterUI()
                self.state = "starter"
                return
            elif kind == "battle":
                trainer, team = item[1], item[2]
                self.state = "field"
                self.game.push_battle([Mon(s, lv) for s, lv in team],
                                      trainer_name=trainer,
                                      callback=lambda r: self._battle_done(r))
                return
            elif kind == "heal":
                self.game.heal_party()
            elif kind == "give":
                self.game.bag[item[1]] = self.game.bag.get(item[1], 0) + item[2]
            elif kind == "flag":
                self.game.flags[item[1]] = True

    def _battle_done(self, result):
        if result == "lose":
            self.start_blackout()
            return
        if self.script:
            self.state = "dialog"
            self._pump(result)
        elif result == "caught":
            pass

    def show_notice(self, text):
        self.textbox.show(text)
        self.state = "dialog"
        self.script = None
        self._sent_once = False

    def start_blackout(self):
        self.fade_t = 1.2

    # -------------------------------------------------- 交互
    def _interact(self):
        dx, dy = {"down": (0, 1), "up": (0, -1), "left": (-1, 0), "right": (1, 0)}[self.dir]
        tx, ty = self.px + dx, self.py + dy
        npc = self.map.npc_at(tx, ty)
        if npc:
            npc["dir"] = _face_back(tx, ty, self.px, self.py)
            self._sent_once = False
            self.start_script(worldmap.SCRIPTS[npc["script"]](self.game))
            return
        t = self.map.tile(tx, ty)
        if t == "S" and (tx, ty) in self.map.signs:
            text = self.map.signs[(tx, ty)]
            self._sent_once = False
            self.start_script((lambda: (yield ("msg", text)))())
        elif t in "123":
            self._sent_once = False
            self.start_script(worldmap.SCRIPTS["ball"](self.game))
        elif t == "b":
            self._sent_once = False
            self.start_script(worldmap.SCRIPTS["bed"](self.game))

    def _open_menu(self):
        self.state = "menu"
        self.menu_idx = 0

    # -------------------------------------------------- 事件
    def handle_event(self, e):
        if e.type == pygame.KEYDOWN and e.key in MOVE_KEYS:
            self.held.add(e.key)
        elif e.type == pygame.KEYUP and e.key in MOVE_KEYS:
            self.held.discard(e.key)
        if e.type != pygame.KEYDOWN:
            return
        if self.state == "field":
            if e.key in (pygame.K_RETURN, pygame.K_x):
                self._open_menu()
            elif e.key in (pygame.K_z, pygame.K_SPACE):
                self._interact()
        elif self.state == "dialog":
            r = self.textbox.key(e)
            if r and r[0] == "advance":
                if self.script:
                    self._pump(None)
                else:
                    self.state = "field"
                    self.textbox.hide()
            elif r and r[0] == "choice":
                self._pump(r[1])
        elif self.state == "menu":
            self._menu_key(e)
        elif self.state == "party":
            self.party_screen.key(e)
            if self.party_screen.done:
                self._party_done()
        elif self.state == "bag":
            self.bag_screen.key(e)
            if self.bag_screen.done:
                self._bag_done()
        elif self.state == "starter":
            self.starter.key(e, self.game.assets["icons"])
            if self.starter.done:
                self._starter_done()

    def _menu_key(self, e):
        n = 4
        if e.key in (pygame.K_UP, pygame.K_w):
            self.menu_idx = (self.menu_idx - 1) % n
        elif e.key in (pygame.K_DOWN, pygame.K_s):
            self.menu_idx = (self.menu_idx + 1) % n
        elif e.key in (pygame.K_x, pygame.K_ESCAPE, pygame.K_RETURN):
            self.state = "field"
        elif e.key in (pygame.K_z, pygame.K_SPACE):
            if self.menu_idx == 0:
                if not self.game.party:
                    self.show_notice("你还没有精灵!")
                else:
                    self.party_screen = PartyScreen(self.game, "menu")
                    self.state = "party"
            elif self.menu_idx == 1:
                self.bag_screen = BagScreen(self.game, "menu")
                self.state = "bag"
            elif self.menu_idx == 2:
                self.game.save()
                self.show_notice("记录已经保存好了!")
            else:
                self.state = "field"

    def _party_done(self):
        ps = self.party_screen
        self.party_screen = None
        if ps.mode == "target" and ps.result is not None:
            self._apply_item(ps.result)
            self.state = "field"
        else:
            self.state = "menu"

    def _bag_done(self):
        bs = self.bag_screen
        self.bag_screen = None
        if bs.result:
            from . import data
            kind = data.ITEMS[bs.result]["kind"]
            if kind == "ball":
                self.show_notice("现在还不能使用精灵球。")
            else:
                self.bag_pending_item = bs.result
                self.party_screen = PartyScreen(self.game, "target")
                self.state = "party"
        else:
            self.state = "menu"

    def _apply_item(self, idx):
        from . import data
        name = self.bag_pending_item
        self.bag_pending_item = None
        m = self.game.party[idx]
        item = data.ITEMS[name]
        kind = item["kind"]
        if kind == "heal":
            if m.hp <= 0:
                self.show_notice(f"{m.name}陷入了濒死状态,\n伤药没有效果……")
                return
            if m.hp >= m.max_hp:
                self.show_notice(f"{m.name}的HP已经满了!")
                return
            m.hp = min(m.max_hp, m.hp + item["amount"])
            self.show_notice(f"{m.name}恢复了{item['amount']}点HP!")
        elif kind == "fullheal":
            if m.hp >= m.max_hp and not m.status:
                self.show_notice("现在没有使用的必要。")
                return
            m.hp = m.max_hp
            m.cure_status()
            self.show_notice(f"{m.name}完全恢复了!")
        elif kind == "cure":
            if not m.status:
                self.show_notice("现在没有使用的必要。")
                return
            m.cure_status()
            self.show_notice(f"{m.name}的异常状态被治愈了!")
        self.game.bag[name] -= 1
        if self.game.bag[name] <= 0:
            del self.game.bag[name]

    def _starter_done(self):
        pick = self.starter.result
        self.starter = None
        if pick:
            self.game.party = [Mon(pick, 5)]
            self.state = "dialog"
            self._pump(pick)
        else:
            self.state = "dialog"
            self._pump(None)

    # -------------------------------------------------- 更新
    def update(self, dt):
        self.water_t += dt
        self.textbox.update(dt)
        if self.fade_t >= 0:
            self.fade_t -= dt
            if self.fade_t <= 0.8 and not self._blackout_done:
                self._blackout_done = True
                self.game.heal_party()
                self.warp_to("house", 5, 6, "down")
                self.show_notice("你眼前一黑……\n醒来时已被送回了家,精灵们也恢复了。")
            if self.fade_t <= 0:
                self.fade_t = -1.0
                self._blackout_done = False
            return
        if self.state != "field":
            return
        if self.moving:
            self.step_t += dt / STEP_TIME
            if self.step_t >= 1.0:
                self.px, self.py = self.step_to
                self.moving = False
                self._arrive()
        if not self.moving:
            d = None
            if self.held & {pygame.K_UP, pygame.K_w}:
                d = "up"
            elif self.held & {pygame.K_DOWN, pygame.K_s}:
                d = "down"
            elif self.held & {pygame.K_LEFT, pygame.K_a}:
                d = "left"
            elif self.held & {pygame.K_RIGHT, pygame.K_d}:
                d = "right"
            if d:
                self.dir = d
                dx, dy = {"down": (0, 1), "up": (0, -1), "left": (-1, 0), "right": (1, 0)}[d]
                nx, ny = self.px + dx, self.py + dy
                if not self.map.solid(nx, ny):
                    self.moving = True
                    self.step_to = (nx, ny)
                    self.step_from = (self.px, self.py)
                    self.step_t = 0.0

    def _arrive(self):
        warp = self.map.warps.get((self.px, self.py))
        if warp:
            # 门禁只限制离开小镇去道路,不影响自宅/研究所的门
            if warp[0] == "route" and not self.game.flags.get("starter_chosen"):
                self.py += 1
                self.show_notice("还没有伙伴就出发太危险了!\n先去研究所找榆木博士吧。")
                return
            self.warp_to(*warp)
            return
        if self.map.tile(self.px, self.py) == ",":
            table = self.map.encounters.get(",")
            if table and random.random() < ENCOUNTER_RATE:
                species, lv = self._roll(table)
                self.game.push_battle([Mon(species, lv)],
                                      callback=lambda r: self._battle_done(r))

    def _roll(self, table):
        total = sum(t[3] for t in table)
        r = random.random() * total
        for sp, l1, l2, w in table:
            r -= w
            if r <= 0:
                return sp, random.randint(l1, l2)
        return table[0][0], table[0][1]

    # -------------------------------------------------- 绘制
    def draw(self, surf):
        surf.fill((10, 12, 18))     # 小于视野的室内地图边界外为纯色
        tiles = self.game.assets["tiles"]
        m = self.map
        mw, mh = m.w * S.TILE, m.h * S.TILE
        view_w, view_h = S.VIEW_TW * S.TILE, S.VIEW_TH * S.TILE

        px_w = self.px * S.TILE
        py_w = self.py * S.TILE
        cam_x = px_w + S.TILE // 2 - view_w // 2
        cam_y = py_w + S.TILE // 2 - view_h // 2
        cam_x = 0 if mw <= view_w else max(0, min(mw - view_w, cam_x))
        cam_y = 0 if mh <= view_h else max(0, min(mh - view_h, cam_y))
        if mw < view_w:
            cam_x = (mw - view_w) // 2
        if mh < view_h:
            cam_y = (mh - view_h) // 2

        water_frame = "w0" if int(self.water_t * 2) % 2 == 0 else "w1"
        tx0, ty0 = int(cam_x // S.TILE), int(cam_y // S.TILE)
        for ty in range(max(0, ty0 - 1), min(m.h, ty0 + S.VIEW_TH + 2)):
            for tx in range(max(0, tx0 - 1), min(m.w, tx0 + S.VIEW_TW + 2)):
                ch = m.rows[ty][tx]
                tchar = water_frame if ch == "w" else ch
                surf.blit(tiles["."], ((tx * S.TILE - cam_x) * S.SCALE,
                                       (ty * S.TILE - cam_y) * S.SCALE))
                surf.blit(tiles.get(tchar, tiles["."]),
                          ((tx * S.TILE - cam_x) * S.SCALE,
                           (ty * S.TILE - cam_y) * S.SCALE))

        people = self.game.assets["people"]
        for npc in m.npcs:
            self._blit_char(surf, people[npc["pal"]], npc["x"], npc["y"], npc.get("dir", "down"),
                            0, cam_x, cam_y)
        if self.moving:
            fx, fy = self.step_from
            t = self.step_t
            wx = (fx + (self.step_to[0] - fx) * t) * S.TILE
            wy = (fy + (self.step_to[1] - fy) * t) * S.TILE
            frame = 1 if t < 0.5 else 2
            self._blit_char_px(surf, people["player"], wx, wy, self.dir, frame, cam_x, cam_y)
        else:
            self._blit_char(surf, people["player"], self.px, self.py, self.dir, 0, cam_x, cam_y)

        self._draw_overlays(surf)

    def _blit_char(self, surf, sprites, tx, ty, d, frame, cam_x, cam_y):
        self._blit_char_px(surf, sprites, tx * S.TILE, ty * S.TILE, d, frame, cam_x, cam_y)

    def _blit_char_px(self, surf, sprites, wx, wy, d, frame, cam_x, cam_y):
        img = sprites[d][frame]
        x = (wx - cam_x) * S.SCALE
        y = (wy - cam_y) * S.SCALE + S.STILE - img.get_height() + 4 * S.SCALE
        surf.blit(img, (x, y - 4 * S.SCALE))

    def _draw_overlays(self, surf):
        if self.state == "menu":
            opts = ["精灵", "背包", "存档", "关闭"]
            panel(surf, (S.WIN_W - 250, 20, 210, 44 * len(opts) + 26), bg=S.C_MENU_BG)
            for i, o in enumerate(opts):
                oy = 42 + i * 44
                if i == self.menu_idx:
                    cursor_arrow(surf, S.WIN_W - 222, oy + 15)
                draw_text(surf, o, S.WIN_W - 196, oy, 24)
            if self.game.flags.get("has_badge"):
                pygame.draw.rect(surf, (188, 150, 90), (S.WIN_W - 236, 20 + 44 * 4 + 8, 26, 26),
                                 border_radius=13)
                draw_text(surf, "岩", S.WIN_W - 223, 20 + 44 * 4 + 12, 18, color=(120, 80, 30),
                          anchor="center")
        elif self.state == "party" and self.party_screen:
            self.party_screen.draw(surf, self.game.assets["icons"])
        elif self.state == "bag" and self.bag_screen:
            self.bag_screen.draw(surf)
        elif self.state == "starter" and self.starter:
            self.starter.draw(surf, self.game.assets["icons"])
        if self.state == "dialog":
            self.textbox.draw(surf)
        if self.fade_t >= 0:
            fog = pygame.Surface((S.WIN_W, S.WIN_H))
            fog.fill((0, 0, 0))
            fog.set_alpha(int(255 * min(1.0, self.fade_t / 0.8)))
            surf.blit(fog, (0, 0))
        draw_text(surf, self.map.name, 14, 10, 18, color=(255, 255, 255))
