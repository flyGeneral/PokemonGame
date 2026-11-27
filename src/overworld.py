"""世界场景:格子移动、冲浪、滑冰/箭头、秘传招式、训练家视线、遇敌、交互、菜单/队伍/背包。"""
import random

import pygame

from . import settings as S
from . import world
from . import data
from . import keys as K
from .mon import Mon
from .ui import (TextBox, PartyScreen, BagScreen, ShopScreen, BadgeScreen, ListScreen, LearnMoveScreen,
                 panel, draw_text, hp_bar, _art_of, cursor_arrow)

STEP_TIME = 0.22            # 步行一格
STEP_TIME_RUN = 0.12        # 按住跑步键(B / Shift)跑步
SURF_RATE = 0.10
MOVE_KEYS = K.MOVE_KEYS
DIRS = {"down": (0, 1), "up": (0, -1), "left": (-1, 0), "right": (1, 0)}
ARROWS = {"^": "up", "v": "down", "<": "left", ">": "right"}
HAM = {"hm_cut", "hm_fly", "hm_surf", "hm_strength", "hm_rock_smash", "hm_waterfall"}

# 训练家职业 → 人物调色板(程序化小人)
PAL_BY_CLASS = {
    "YOUNGSTER": "youth", "LASS": "lass", "BUG_CATCHER": "bugcatcher", "CAMPER": "youth",
    "PICNICKER": "lass", "HIKER": "hiker", "FISHERMAN": "fisherman", "AROMA_LADY": "lady",
    "BATTLE_GIRL": "battle_girl", "BLACK_BELT": "blackbelt", "ACE_TRAINER_M": "ace",
    "ACE_TRAINER_F": "ace", "ACE_TRAINER_SNOW_M": "skier", "ACE_TRAINER_SNOW_F": "skier",
    "PSYCHIC_M": "psychic", "PSYCHIC_F": "psychic", "WORKER": "worker", "SCIENTIST": "scientist",
    "SCHOOL_KID_M": "youth", "SCHOOL_KID_F": "lass", "SWIMMER_M": "swimmer", "SWIMMER_F": "swimmer",
    "SKIER_M": "skier", "SKIER_F": "skier", "SAILOR": "sailor", "JOGGER": "youth",
    "BIRD_KEEPER": "youth", "NINJA_BOY": "ninja", "COLLECTOR": "scientist", "RUIN_MANIAC": "hiker",
    "GUITARIST": "youth", "POLICEMAN": "officer", "BEAUTY": "lady", "RICH_BOY": "ace",
    "LADY": "lady", "GENTLEMAN": "prof", "TUBER_M": "youth", "TUBER_F": "lass", "VETERAN": "blackbelt",
    "DRAGON_TAMER": "ace", "GALACTIC": "galactic", "GALACTIC_F": "galactic", "POKEFAN_M": "villager",
    "POKEFAN_F": "lady", "ARTIST": "villager", "PARASOL_LADY": "lady", "COWGIRL": "lass",
    "IDOL": "lady", "PKMN_RANGER_M": "ranger", "PKMN_RANGER_F": "ranger", "INTERVIEWERS": "youth",
    "DOUBLE_TEAM": "ace", "PKMN_BREEDER_M": "villager", "PKMN_BREEDER_F": "villager", "TWINS": "lass",
}


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

    def __init__(self, init_idx=0):
        self.opts = list(data.STARTERS)
        self.cursor = init_idx % 3
        self.confirm = False
        self.cidx = 0
        self.done = False
        self.result = None

    def key(self, event, icons):
        if not self.confirm:
            if event.key in K.LEFT:
                self.cursor = (self.cursor - 1) % 3
            elif event.key in K.RIGHT:
                self.cursor = (self.cursor + 1) % 3
            elif event.key in K.A:
                self.confirm = True
                self.cidx = 0
            elif event.key in K.B:
                self.done = True
        else:
            if event.key in K.LEFT or event.key in K.RIGHT:
                self.cidx = 1 - self.cidx
            elif event.key in K.A:
                self.done = True
                self.result = self.opts[self.cursor] if self.cidx == 0 else None
            elif event.key in K.B:            # B = 不决定
                self.done = True
                self.result = None

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
            icon = icons.get(_art_of(name))
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


def _art_of(species):
    return data.SPECIES[species]["art"]


# ================================================================ 名人堂 / 制作人员
class HallScene:
    """名人堂:依次展示队伍精灵。"""

    def __init__(self, game, callback=None):
        self.game = game
        self.callback = callback
        self.idx = 0
        self.t = 0.0
        self.done = False
        self.msg_done = False

    def handle_event(self, e):
        if e.type != pygame.KEYDOWN:
            return
        if e.key in K.A:
            self.idx += 1
            self.t = 0.0
            if self.idx >= len(self.game.party) + 1:
                self.done = True

    def update(self, dt):
        self.t += dt

    def draw(self, surf):
        for y in range(S.WIN_H):
            pygame.draw.line(surf, (30 + y // 20, 40 + y // 25, 90 + y // 12), (0, y), (S.WIN_W, y))
        draw_text(surf, "名 人 堂", S.WIN_W // 2, 60, 48, color=(255, 230, 150), anchor="center")
        draw_text(surf, f"第 {self.idx + 1} 位" if self.idx < len(self.game.party) else "",
                  S.WIN_W // 2, 130, 22, color=(200, 210, 240), anchor="center")
        if self.idx < len(self.game.party):
            m = self.game.party[self.idx]
            icon = self.game.assets["mons"].get(_art_of(m.species))
            if icon:
                k = min(1.0, self.t * 2)
                big = pygame.transform.smoothscale(icon, (int(240 * k), int(240 * k)))
                surf.blit(big, (S.WIN_W // 2 - big.get_width() // 2, 180 + (240 - big.get_height()) // 2))
            draw_text(surf, f"{m.name}  Lv{m.level}", S.WIN_W // 2, 440, 28, anchor="center")
            draw_text(surf, f"{'/'.join(m.types)}   亲密 {m.friendship}", S.WIN_W // 2, 480, 20,
                      color=(200, 210, 240), anchor="center")
        else:
            draw_text(surf, f"{self.game.player_name} 与伙伴们\n一同被记录在了名人堂!", S.WIN_W // 2, 300, 26,
                      color=(255, 255, 255), anchor="center")
        if self.t > 0.8:
            draw_text(surf, "Z 继续", S.WIN_W - 40, S.WIN_H - 34, 18, color=(200, 210, 240), anchor="tr")


CREDITS = [
    "", "", "宝可梦 钻石·珍珠 · 神奥复刻", "",
    "—— 制作 ——", "",
    "引擎 / 地图 / 剧情脚本", "Claude Code", "",
    "—— 数据来源 ——", "",
    "精灵·招式·训练家·遭遇表数值", "pret/pokediamond(反编译工程)", "",
    "官方简体中文译名", "Xzonn/PokemonChineseTranslationRevise", "PokeAPI", "",
    "—— 特别感谢 ——", "",
    "Nintendo / Creatures / GAME FREAK", "创造了宝可梦的世界", "",
    "以及所有踏上神奥之旅的训练家", "", "", "", "感谢游玩!", "",
]


class CreditsScene:
    def __init__(self, game, callback=None):
        self.game = game
        self.callback = callback
        self.t = 0.0
        self.done = False

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN and (e.key in K.A or e.key in K.B):
            self.done = True

    def update(self, dt):
        self.t += dt
        if self.t > 28:
            self.done = True

    def draw(self, surf):
        surf.fill((8, 10, 24))
        y = S.WIN_H - self.t * 40
        for line in CREDITS:
            if -40 < y < S.WIN_H + 20:
                draw_text(surf, line, S.WIN_W // 2, y, 24 if not line.startswith("宝可梦") else 32,
                          color=(235, 235, 245), anchor="center")
            y += 40


# ================================================================ 大地图
class Overworld:
    def __init__(self, game, map_id="twinleaf", x=10, y=12, facing="down"):
        self.game = game
        self.map_id = map_id
        self.px, self.py = x, y
        self.dir = facing
        self.moving = False
        self.step_from = (x, y)
        self.step_to = (x, y)
        self.step_t = 0.0
        self.water_t = 0.0
        self.state = "field"
        self.textbox = TextBox()
        self.script = None
        self.script_npc = None
        self._sent_once = False
        self.menu_idx = 0
        self.menu_opts = []
        self.party_screen = None
        self.bag_screen = None
        self.shop_screen = None
        self.badge_screen = None
        self.fly_screen = None
        self.learn_screen = None
        self.bag_pending_item = None
        self.bag_pending_mon = None
        self.bag_from = "menu"         # 背包关闭后回到哪里:menu / field
        self.starter = None
        self.fade_t = -1.0
        self.fade_kind = None
        self.notice = None
        self._blackout_done = False
        self._starter_hint = 0
        self._stride_parity = 0
        self.held = set()
        self.surfing = False
        self.safari = None
        self.steps = 0
        self.tile_over = {}
        self.visited = set()
        self.bubble = None            # (npc, t) 训练家发现玩家时的"!"
        self.alert_t = 0.0
        self.reload_overrides()

    # -------------------------------------------------- 地图/位置
    @property
    def map(self):
        return world.MAPS[self.map_id]

    def reload_overrides(self):
        over = dict(self.game.tile_over.get(self.map_id, {}))
        for (lx, ly), tiles in self.map.levers.items():
            flag = f"lever_{self.map_id}_{lx}_{ly}"
            if self.game.flags.get(flag):
                for tx, ty, ch in tiles:
                    over[(tx, ty)] = ch
        self.tile_over = over

    def tile(self, x, y):
        return self.map.tile(x, y, self.tile_over)

    def warp_to(self, map_id, x, y, facing):
        self.map_id = map_id
        self.px, self.py = x, y
        self.dir = facing
        self.moving = False
        self.reload_overrides()
        self.bubble = None
        m = self.map
        self.visited.add(map_id)
        if map_id in world.FLY_SPOTS and m.indoor is False and map_id.endswith("_center") is False:
            pass
        # 冲浪状态:到达点不是水面则下艇;落在水面上(如从 224 道路走进 223 水路)则自动上艇,
        # 否则会站在水上动弹不得
        t = self.tile(x, y)
        if self.surfing and t not in ("w", "W"):
            self.surfing = False
        if not self.surfing and t in ("w", "W") and self.game.knowable_hm("冲浪"):
            self.surfing = True
        if m.safari:
            if not self.safari:
                self.safari = {"balls": 30, "steps": 400}
        else:
            self.safari = None

    def legend_back(self, n):
        """被打倒(未被捕捉)的传说宝可梦:成为冠军后重新现身(与原作一致)。"""
        f = self.game.flags
        return bool(n.get("legend") and f.get("champion") and not f.get(n["legend"] + "_caught"))

    def visible_npcs(self):
        """事件脚本里 ("hide",) 隐藏的 NPC 以 hide_地图_x_y 旗标存档,读档后依然隐藏。"""
        f = self.game.flags
        return [n for n in self.map.npcs if self.npc_visible(n)]

    def npc_visible(self, n):
        f = self.game.flags
        if self.legend_back(n):
            return True
        if (n.get("hide") and f.get(n["hide"])) or f.get(f"hide_{self.map_id}_{n['x']}_{n['y']}"):
            return False
        return not n.get("show") or bool(f.get(n["show"]))

    def npc_at(self, x, y):
        for n in self.visible_npcs():
            if n["x"] == x and n["y"] == y:
                return n
        return None

    def solid(self, x, y):
        m = self.map
        if not (0 <= x < m.w and 0 <= y < m.h):
            return True
        t = self.tile(x, y)
        if t == "W":
            return not (self.surfing and self.dir == "up" and self.game.knowable_hm("攀瀑"))
        if self.surfing:
            if t == "w":
                return False
            return t in world.SOLID
        return t in world.SOLID

    # -------------------------------------------------- 脚本运行
    def start_script(self, gen, npc=None):
        self.script = gen
        self.script_npc = npc
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
                self.script_npc = None
                if getattr(self, "_pending_script", None):
                    pending, res = self._pending_script
                    self._pending_script = None
                    if pending is not None:
                        self.script = pending
                        self._sent_once = True
                        self.state = "dialog"
                        self._pump(res)
                        return
                if self.state == "dialog":
                    self.state = "field"
                self.textbox.hide()
                return
            self._sent_once = True
            value = None
            kind = item[0]
            if kind == "msg":
                self.textbox.show(item[1])
                return
            elif kind in ("choice", "yesno"):
                opts = item[1] if kind == "choice" else ["是", "否"]
                self.textbox.show("", choices=opts)
                return
            elif kind == "quiz":
                self.textbox.show(item[1], choices=item[2])
                self._quiz_answer = item[3]
                return
            elif kind in ("fishing", "rocksmash"):
                self._sent_once = False
                self.state = "field"
                rows = item[1]
                self._wild_from(rows, {"fishing": kind == "fishing", "cave": self.map.cave})
                return
            elif kind == "starter":
                self.starter = StarterUI(self._starter_hint)
                self.state = "starter"
                return
            elif kind == "trainer":
                key = item[1]
                display = item[2] if len(item) > 2 else None
                ai = item[3] if len(item) > 3 else 2
                self.state = "field"
                self.game.push_battle(trainer_key=key, display=display, ai_level=ai,
                                      callback=lambda r: self._battle_done(r),
                                      context=self._battle_context())
                return
            elif kind == "wild":
                self.state = "field"
                self.game.push_battle([Mon(item[1], item[2])], callback=lambda r: self._battle_done(r),
                                      context=self._battle_context())
                return
            elif kind == "legendary":
                flag = item[3]
                if self.game.flags.get(flag) and not self.legend_back(self.script_npc or {}):
                    self.textbox.show("它已经不在这里了。")
                    return
                self._legend_flag = flag
                self.state = "field"
                self.game.push_battle([Mon(item[1], item[2])], callback=lambda r: self._battle_done(r),
                                      context=self._battle_context())
                return
            elif kind == "shop":
                stock = item[1]
                if isinstance(stock, str):
                    from .world.interiors import SHOP_STOCK
                    stock = SHOP_STOCK[stock] if stock != "tms" else __import__("src.world.interiors",
                                                                              fromlist=["x"]).tm_stock()
                self.shop_screen = ShopScreen(self.game, stock)
                self.state = "shop"
                return
            elif kind == "heal":
                self.game.heal_party()
            elif kind == "give":
                self.game.give_item(item[1], item[2])
            elif kind == "give_pokemon":
                m = Mon(item[1], item[2])
                if len(self.game.party) < 6:
                    self.game.party.append(m)
                else:
                    self.game.pc.append(m.to_dict())
                self.game.caught.add(item[1])
            elif kind == "flag":
                self.game.flags[item[1]] = item[2] if len(item) > 2 else True
            elif kind == "money":
                self.game.money += item[1]
            elif kind == "tm":
                name = data.item_by_tm(item[1])
                if name:
                    self.game.give_item(name, 1)
                    self.textbox.show(f"(获得了 {name}!)")
                    return
            elif kind == "hm":
                name = data.item_by_tm(item[1], hm=True)
                if name:
                    self.game.give_item(name, 1)
                    flag = {1: "hm_cut", 2: "hm_fly", 3: "hm_surf", 4: "hm_strength",
                            6: "hm_rock_smash", 7: "hm_waterfall"}.get(item[1])
                    if flag:
                        self.game.flags[flag] = True
                    self.textbox.show(f"(获得了 {name}!)")
                    return
            elif kind == "badge":
                self.game.flags[item[1]] = True
            elif kind == "warp":
                self.warp_to(item[1], item[2], item[3], item[4])
            elif kind == "fade":
                self.fade_t = item[1]
                self.fade_kind = "fade"
            elif kind == "fly":
                spots = [(v[4], k) for k, v in world.FLY_SPOTS.items() if self.game.flags.get(f"visited_{k}")]
                self.fly_screen = ListScreen("飞往哪里?", spots or [("还没有去过的地方", None)])
                self.state = "fly"
                return
            elif kind == "hall":
                self.state = "field"
                self.game.scenes.append(HallScene(self.game, callback=lambda *_: self._resume_script()))
                return
            elif kind == "credits":
                self.state = "field"
                self.game.scenes.append(CreditsScene(self.game, callback=lambda *_: self._resume_script()))
                self.game.save()
                return
            elif kind == "hide":
                if self.script_npc is not None:
                    key = f"hide_{self.map_id}_{self.script_npc['x']}_{self.script_npc['y']}"
                    self.game.flags[key] = True
                    self.script_npc["hide"] = key
            elif kind == "toggle":
                lx, ly = item[1], item[2]
                flag = f"lever_{self.map_id}_{lx}_{ly}"
                self.game.flags[flag] = not self.game.flags.get(flag)
                self.reload_overrides()
                self.textbox.show("咔嚓!机关启动了!")
                return

    def _battle_context(self):
        m = self.map
        return {"cave": m.cave and not m.indoor, "surf": self.surfing, "fishing": False,
                "map_tag": m.tag}

    def _resume_script(self):
        if self.script:
            self.state = "dialog"
            self._pump(None)

    def _battle_done(self, result):
        b = getattr(self.game, "last_battle", None)
        evos = b.resolve_pending_evolution() if b is not None else []
        self._pending_evo_msgs = [f"什么?{m.name}的样子变了!\n{old}进化成了{new}!" for m, old, new in evos]
        self._after_battle(result)

    def _after_battle(self, result):
        legend = getattr(self, "_legend_flag", None)
        self._legend_flag = None
        if result == "lose":
            self.start_blackout()
            return
        if legend:
            flag = legend
            if result in ("win", "caught"):
                self.game.flags[flag] = True
                if result == "caught":
                    self.game.flags[flag + "_caught"] = True
                if self.script_npc is not None:        # 对峙结束:从地图上消失(冠军后未捕捉的会回来)
                    key = f"hide_{self.map_id}_{self.script_npc['x']}_{self.script_npc['y']}"
                    self.game.flags[key] = True
                    self.script_npc["hide"] = key
        if self.safari:
            b = getattr(self.game, "last_battle", None)
            if b is not None and getattr(b, "safari", False):
                self.safari["balls"] = b.safari_balls
            if self.safari["balls"] <= 0:
                self.safari = None
                self.start_script(self._safari_end_script())
                return
        msgs = getattr(self, "_pending_evo_msgs", [])
        self._pending_evo_msgs = []
        if msgs:
            # 先播进化提示,结束后再把对战结果交还给被打断的脚本(不能在生成器内部 _pump)
            self._pending_script = (self.script, result)

            def gen():
                for t in msgs:
                    yield ("msg", t)
            self.start_script(gen())
            return
        if self.script:
            self.state = "dialog"
            self._pump(result)
        elif self.state != "dialog":
            self.state = "field"

    def _safari_end_script(self):
        yield ("fade", 0.6)
        yield ("warp", "pastoria_marsh_gate", 8, 4, "left")
        yield ("msg", "接待员:辛苦了,\n狩猎球已经用完了呢。")

    def show_notice(self, text):
        self.textbox.show(text)
        self.state = "dialog"
        self.script = None
        self._sent_once = False

    def _escape_rope_script(self):
        yield ("msg", "使用了离洞绳!")
        r = self.game.respawn if self.game.respawn and self.game.respawn[0] in world.MAPS else world.START
        yield ("fade", 0.6)
        yield ("warp", r[0], r[1], r[2], r[3])

    def start_blackout(self):
        self.fade_t = 1.2
        self.fade_kind = "blackout"
        self.surfing = False
        self._legend_flag = None          # 脚本被打断:之后的事不能再算到神兽头上
        self.script_npc = None

    def start_intro(self):
        def gen(g):
            yield ("msg", "欢迎来到神奥地区!\n这里是充满传说与冒险的地方。")
            yield ("msg", "今天是出发的日子。\n山梨博士在真砂镇的研究所等你。")
            yield ("msg", f"(操作:{K.HINT_FIELD})")
        self.start_script(gen(self.game))

    # -------------------------------------------------- 交互
    def _interact(self):
        dx, dy = DIRS[self.dir]
        tx, ty = self.px + dx, self.py + dy
        npc = self.npc_at(tx, ty)
        if npc:
            npc["dir"] = _face_back(tx, ty, self.px, self.py)
            self._sent_once = False
            self._run_npc(npc)
            return
        t = self.tile(tx, ty)
        m = self.map
        if t == "S":
            text = m.signs.get((tx, ty))
            if text:
                self._sent_once = False
                self.start_script((lambda: (yield ("msg", text)))())
            return
        if t == "*" and (tx, ty) in m.items:
            item, n = m.items[(tx, ty)]
            self.game.give_item(item, n)
            self.game.tile_over.setdefault(self.map_id, {})[(tx, ty)] = self._floor_under(tx, ty)
            self.reload_overrides()
            self._sent_once = False
            self.start_script((lambda: (yield ("msg", f"(发现了 {item}×{n}!)")))())
            return
        if t in "123" and self.map_id == "sandgem_lab":
            self._starter_hint = int(t) - 1
            self._sent_once = False
            self.start_script(self._call_script("ball"))
            return
        if t == "b":
            self._sent_once = False
            self.start_script((lambda: (yield ("heal",)))())
            return
        if t == "N":
            self._sent_once = False
            self.start_script(self._call_script("nurse"))
            return
        if t == "P":
            self._sent_once = False
            n = len(self.game.pc)
            self.start_script((lambda: (yield ("msg", f"这是宝可梦储存系统。\n电脑里存放着 {n} 只精灵。")))())
            return
        if t == "M":
            stock = getattr(m, "stock", None)
            counters = getattr(m, "counters", None)
            if counters:
                for row, key in counters:
                    if ty == row:                       # counters 记录的是柜台所在行
                        from .world.interiors import SHOP_STOCK, tm_stock
                        stock = SHOP_STOCK[key] if key != "tms" else tm_stock()
                        break
            if stock:
                self._sent_once = False
                self.start_script(self._call_script("shop", stock))
            return
        if t == "L":
            self._sent_once = False
            self.start_script(self._call_script("lever", {"x": tx, "y": ty}))
            return
        if t == "K":
            self._rock_smash(tx, ty)
            return
        if t == "J":
            self._cut(tx, ty)
            return
        if t == "O":
            self._strength(tx, ty)
            return
        if t == "w" and not self.surfing:
            if any(self.game.has_item(r) for r in ("破旧钓竿", "好钓竿", "厉害钓竿")):
                self._fish()
                return
            if self.game.knowable_hm("冲浪"):
                self._sent_once = False
                self.start_script(self._surf_script(tx, ty))
            return
        if self.surfing and t != "w" and t not in world.SOLID:
            self._sent_once = False
            self.start_script(self._dismount_script())

    def _floor_under(self, x, y):
        """障碍物清除后露出的地面,按地图风格推断。"""
        m = self.map
        joined = "".join("".join(r) for r in m.rows)
        if "g" in joined and m.indoor:
            return "g"
        if m.indoor:
            return "o"
        if m.cave:
            return "c"
        if self.map_id == "r223" or m.rows[y][x] == "s":
            return "s"
        if "x" in joined and "." not in joined:
            return "x"
        return "," if "," in "".join(m.rows[y]) else "."

    def _call_script(self, name, *args):
        """按脚本函数的参数个数传参:大多数脚本只接收 game,少数(训练家/拉杆/商店)还接收 npc 或库存。"""
        import inspect
        fn = world.SCRIPTS[name]
        n = len([p for p in inspect.signature(fn).parameters.values()
                 if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)])
        return fn(self.game, *args[:max(0, n - 1)])

    def _run_npc(self, npc):
        sc = npc["script"]
        if sc == "trainer":
            self.start_script(self._call_script("trainer", npc), npc)
        elif isinstance(sc, tuple):
            self.start_script(self._call_script(sc[0], *sc[1:]), npc)
        else:
            self.start_script(self._call_script(sc, npc), npc)

    def _surf_script(self, tx, ty):
        yield ("msg", "要在水面上冲浪吗?")
        r = yield ("yesno",)
        if r == 0:
            self.surfing = True
            yield ("msg", f"{self._surf_mon()}在水面上了!")
            self._start_step(tx, ty)

    def _dismount_script(self):
        yield ("msg", "要回到岸上吗?")
        r = yield ("yesno",)
        if r == 0:
            dx, dy = DIRS[self.dir]
            self._start_step(self.px + dx, self.py + dy)

    def _surf_mon(self):
        m = next((x for x in self.game.party if x.hp > 0 and x.knows("冲浪")), None)
        return m.name if m else "伙伴"

    def _start_step(self, nx, ny):
        self.moving = True
        self.step_from = (self.px, self.py)
        self.step_to = (nx, ny)
        self.step_t = 0.0

    def _fish(self):
        rod = "厉害钓竿" if self.game.has_item("厉害钓竿") else \
            "好钓竿" if self.game.has_item("好钓竿") else "破旧钓竿"
        key = {"厉害钓竿": "super", "好钓竿": "good", "破旧钓竿": "old"}[rod]

        def gen(g):
            yield ("msg", f"甩出了{rod}……")
            table = self._encounter_table(key)
            if not table or random.random() < 0.3:
                yield ("msg", "……没有钓到任何东西。")
                return
            yield ("msg", "咬钩了!")
            yield ("fishing", table)
        self._sent_once = False
        self.start_script(gen(self.game))

    def _rock_smash(self, x, y):
        def gen(g):
            if not self.game.knowable_hm("碎岩"):
                yield ("msg", "岩石上有一道裂缝。\n(需要有精灵会「碎岩」)")
                return
            yield ("msg", "要使用碎岩吗?")
            r = yield ("yesno",)
            if r != 0:
                return
            self.game.tile_over.setdefault(self.map_id, {})[(x, y)] = self._floor_under(x, y)
            self.reload_overrides()
            yield ("msg", "咔啦!岩石碎掉了!")
            table = self._encounter_table("rock")
            if table and random.random() < 0.4:
                yield ("rocksmash", table)
        self._sent_once = False
        self.start_script(gen(self.game))

    def _cut(self, x, y):
        def gen(g):
            if not self.game.knowable_hm("居合劈"):
                yield ("msg", "茂密的树丛挡住了路。\n(需要有精灵会「居合劈」)")
                return
            yield ("msg", "要使用居合劈吗?")
            r = yield ("yesno",)
            if r != 0:
                return
            self.game.tile_over.setdefault(self.map_id, {})[(x, y)] = self._floor_under(x, y)
            self.reload_overrides()
            yield ("msg", "唰!树丛被砍掉了!")
        self._sent_once = False
        self.start_script(gen(self.game))

    def _strength(self, x, y):
        def gen(g):
            if not self.game.knowable_hm("怪力"):
                yield ("msg", "沉重的岩石。\n(需要有精灵会「怪力」)")
                return
            dx, dy = DIRS[self.dir]
            nx, ny = x + dx, y + dy
            if not (0 <= nx < self.map.w and 0 <= ny < self.map.h) or self.tile(nx, ny) != self._floor_under(nx, ny) \
                    and self.tile(nx, ny) not in ".pncoxci_^<>":
                yield ("msg", "岩石推不动……")
                return
            if self.npc_at(nx, ny):
                yield ("msg", "岩石推不动……")
                return
            over = self.game.tile_over.setdefault(self.map_id, {})
            over[(x, y)] = self._floor_under(x, y)
            over[(nx, ny)] = "O"
            self.reload_overrides()
            yield ("msg", "嘿咻!岩石被推开了!")
        self._sent_once = False
        self.start_script(gen(self.game))

    # -------------------------------------------------- 遭遇
    def _encounter_table(self, kind):
        m = self.map
        area = data.ENCOUNTERS.get(m.enc) if m.enc else None
        if not area:
            return self._default_water(kind)
        ver = self.game.version
        rows = (area.get(ver) or area.get("D") or area.get("P")).get(kind) or []
        return rows if rows else (self._default_water(kind) if kind in ("surf", "old", "good", "super") else None)

    def _default_water(self, kind):
        """没有遭遇表的水面:默认水系表(鲤鱼王/角金鱼等)。"""
        return {"surf": [[20, 30, 72, 60], [20, 30, 278, 30], [20, 40, 73, 5], [20, 40, 118, 4], [20, 40, 279, 1]],
                "old": [[3, 6, 129, 60], [4, 7, 129, 30], [5, 10, 129, 10]],
                "good": [[15, 20, 129, 60], [15, 20, 118, 30], [10, 25, 129, 10]],
                "super": [[30, 40, 130, 60], [30, 40, 119, 30], [40, 55, 130, 10]]}.get(kind)

    def _roll(self, rows, rng=random):
        total = sum(r[-1] for r in rows)
        r = rng.random() * total
        for row in rows:
            r -= row[-1]
            if r <= 0:
                if len(row) == 3:
                    return data.species_name(row[1]), row[0]
                return data.species_name(row[2]), rng.randint(row[0], row[1])
        row = rows[0]
        return data.species_name(row[1] if len(row) == 3 else row[2]), row[0]

    def _wild_from(self, rows, context=None):
        sp, lv = self._roll(rows)
        lead = next((m for m in self.game.party if m.hp > 0), None)
        if self.game.repel > 0 and lead is not None and lv < lead.level:
            return                                   # 喷雾生效中:比队伍首领弱的野生精灵不会出现
        ctx = self._battle_context()
        ctx.update(context or {})
        if self.safari:
            self.game.push_battle([Mon(sp, lv)], callback=lambda r: self._battle_done(r), context=ctx,
                                  safari=True, safari_balls=self.safari["balls"])
        else:
            self.game.push_battle([Mon(sp, lv)], callback=lambda r: self._battle_done(r), context=ctx)

    def _grass_encounter(self):
        rows = self._encounter_table("grass")
        if not rows:
            return
        area = data.ENCOUNTERS[self.map.enc]
        rate = (area.get(self.game.version) or area["D"]).get("rate", 30) / 100.0
        if random.random() < rate:
            self._wild_from(rows)

    def _water_encounter(self):
        rows = self._encounter_table("surf")
        if not rows:
            return
        if random.random() < SURF_RATE:
            self._wild_from(rows, {"surf": True})

    # -------------------------------------------------- 菜单
    def _open_menu(self):
        self.bag_from = "menu"
        opts = ["精灵", "背包", "徽章"]
        if self.game.knowable_hm("飞翔"):
            opts.append("飞翔")
        opts += ["存档", "关闭"]
        self.menu_opts = opts
        self.menu_idx = 0
        self.state = "menu"

    def _menu_key(self, e):
        n = len(self.menu_opts)
        if e.key in K.UP:
            self.menu_idx = (self.menu_idx - 1) % n
        elif e.key in K.DOWN:
            self.menu_idx = (self.menu_idx + 1) % n
        elif e.key in K.B or e.key in K.X:        # B 返回 / 再按 X 收起菜单
            self.state = "field"
        elif e.key in K.A:
            opt = self.menu_opts[self.menu_idx]
            if opt == "精灵":
                if not self.game.party:
                    self.show_notice("你还没有精灵!")
                else:
                    self.party_screen = PartyScreen(self.game, "menu")
                    self.state = "party"
            elif opt == "背包":
                self.bag_screen = BagScreen(self.game, "menu")
                self.state = "bag"
            elif opt == "徽章":
                if self.game.party:
                    self.badge_screen = BadgeScreen(self.game)
                    self.state = "badges"
                else:
                    self.show_notice("你还没有精灵!")
            elif opt == "飞翔":
                self.start_script((lambda: (yield ("fly",)))())
            elif opt == "存档":
                self.game.save()
                self.show_notice("记录已经保存好了!")
            else:
                self.state = "field"

    def _party_done(self):
        ps = self.party_screen
        self.party_screen = None
        if ps.mode == "target" and ps.result is not None:
            self._apply_item(ps.result)          # 结果提示由 show_notice/界面决定状态
        elif ps.mode == "learn" and ps.result is not None:
            self._teach_move(self.game.party[ps.result])
        else:
            self.state = "menu"

    def _apply_item(self, idx):
        name = self.bag_pending_item
        self.bag_pending_item = None
        m = self.game.party[idx]
        item = data.ITEMS[name]
        kind = item["kind"]
        if kind == "heal":
            if m.hp <= 0 or m.hp >= m.max_hp:
                self.show_notice(f"{m.name}现在没有使用的效果。")
                return
            amount = item.get("param", item.get("amount", 20))
            m.hp = min(m.max_hp, m.hp + (amount if amount < 9999 else m.max_hp))
            self.show_notice(f"{m.name}恢复了HP!")
        elif kind == "fullheal":
            if m.hp <= 0 or (m.hp >= m.max_hp and not m.status):
                self.show_notice("现在没有使用的必要。")
                return
            m.hp = m.max_hp
            m.cure_status()
            self.show_notice(f"{m.name}完全恢复了!")
        elif kind == "cure":
            if not m.status or (item["param"] != "all" and m.status != item["param"]):
                self.show_notice("现在没有使用的必要。")
                return
            m.cure_status()
            self.show_notice(f"{m.name}的异常状态被治愈了!")
        elif kind == "revive":
            if m.hp > 0:
                self.show_notice(f"{m.name}并没有濒死。")
                return
            m.hp = max(1, int(m.max_hp * item["param"]))
            m.cure_status()
            self.show_notice(f"{m.name}恢复了意识!")
        elif kind in ("pp", "ppall"):
            cands = m.moves if kind == "ppall" else [x for x in m.moves if x.pp < x.max_pp]
            if not cands or all(x.pp >= x.max_pp for x in cands):
                self.show_notice("现在没有使用的必要。")
                return
            for x in cands:
                x.pp = min(x.max_pp, x.pp + (item["param"] if item["param"] < 9999 else 99))
            self.show_notice(f"{m.name}的PP恢复了!")
        elif kind == "evo":
            targets = m.item_evolutions(name)
            if not targets:
                self.show_notice(f"对{m.name}没有效果……")
                return
            old = m.species
            m.evolve_into(targets[0])
            self.game.caught.add(m.species)
            self.show_notice(f"什么?{old}的样子变了!\n{old}进化成了{m.species}!")
        else:
            self.show_notice("现在不能使用那个。")
            return
        self.game.remove_item(name, 1)

    def _teach_move(self, m):
        name = self.bag_pending_item
        self.bag_pending_item = None
        item = data.ITEMS[name]
        sp = data.SPECIES[m.species]
        ok = (item["num"] in sp["tms"]) if not item["hm"] else (item["num"] in sp["hms"])
        if not ok:
            self.show_notice(f"{m.name}无法学会{item['move']}。")
            return
        if m.knows(item["move"]):
            self.show_notice(f"{m.name}已经会{item['move']}了。")
            return
        if len(m.moves) < 4:
            from .mon import Move
            m.moves.append(Move(item["move"]))
            if not item["hm"]:
                self.game.remove_item(name, 1)
            self.show_notice(f"{m.name}学会了{item['move']}!")
            return
        self.bag_pending_item = name
        self.learn_screen = LearnMoveScreen(m, item["move"])
        self.state = "learn"

    def _learn_done(self):
        ls = self.learn_screen
        self.learn_screen = None
        name = self.bag_pending_item
        self.bag_pending_item = None
        self.state = "field"
        if ls.result is None:
            self.show_notice(f"放弃了学习{name}对应招式。")
            return
        item = data.ITEMS[name]
        m = ls.mon
        msg = m.learn_move(item["move"], ls.result)
        if not item["hm"]:
            self.game.remove_item(name, 1)
        self.show_notice(msg)

    def _bag_done(self):
        bs = self.bag_screen
        self.bag_screen = None
        if not bs.result:
            self.state = self.bag_from
            return
        name = bs.result
        kind = data.ITEMS[name]["kind"]
        if kind in ("heal", "fullheal", "cure", "revive", "pp", "ppall", "evo"):
            self.bag_pending_item = name
            self.party_screen = PartyScreen(self.game, "target")
            self.state = "party"
        elif kind == "tm":
            self.bag_pending_item = name
            self.party_screen = PartyScreen(self.game, "learn")
            self.state = "party"
        elif kind == "repel":
            steps = data.ITEMS[name]["param"]
            self.state = "menu"
            if self.game.repel >= steps:
                self.show_notice("喷雾的效果还在持续呢。")
            else:
                self.game.remove_item(name, 1)
                self.game.repel = steps
                self.show_notice(f"使用了{name}!\n之后 {steps} 步之内不会遇到弱的野生精灵。")
        elif kind == "key" and data.ITEMS[name].get("key") == "escape_rope":
            self.game.remove_item(name, 1)
            self.state = "field"
            self.start_script(self._escape_rope_script())
        elif kind == "key":
            self.state = "menu"
            key = data.ITEMS[name]["key"]
            if key == "vs_seeker":
                n = 0
                for k in list(self.game.flags):
                    if k.startswith("beat_") and k[5:].isdigit():
                        del self.game.flags[k]
                        n += 1
                self.show_notice(f"对战寻呼机发出了电波!\n({n} 位训练家愿意再战了)")
            else:
                self.show_notice(data.ITEMS[name]["desc"])
        else:
            self.state = "menu"
            self.show_notice("现在不能使用那个。")

    # -------------------------------------------------- 事件
    def handle_event(self, e):
        if e.type == pygame.KEYDOWN and e.key in K.HELD_KEYS:
            self.held.add(e.key)
        elif e.type == pygame.KEYUP and e.key in K.HELD_KEYS:
            self.held.discard(e.key)
        if e.type != pygame.KEYDOWN:
            return
        if self.state == "field":
            if e.key in K.X:                      # X 键:菜单(回车兼容旧习惯,先于 A 判定)
                self._open_menu()
            elif e.key in K.A:
                self._interact()
            elif e.key in K.Y:                    # Y 键:快捷背包
                self.bag_from = "field"
                self.bag_screen = BagScreen(self.game, "menu")
                self.state = "bag"
        elif self.state == "dialog":
            r = self.textbox.key(e)
            if r and r[0] == "advance":
                if self.script:
                    self._pump(None)
                else:
                    self.state = "field"
                    self.textbox.hide()
            elif r and r[0] == "choice":
                if getattr(self, "_quiz_answer", None) is not None:
                    ans = r[1] == self._quiz_answer
                    self._quiz_answer = None
                    self._pump(ans)
                else:
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
        elif self.state == "shop":
            self.shop_screen.key(e)
            if self.shop_screen.done:
                self.shop_screen = None
                self.state = "dialog"
                self._pump(None)
        elif self.state == "badges":
            self.badge_screen.key(e)
            if self.badge_screen.done:
                self.badge_screen = None
                self.state = "menu"
        elif self.state == "fly":
            self.fly_screen.key(e)
            if self.fly_screen.done:
                spot = self.fly_screen.result
                self.fly_screen = None
                self.state = "dialog"
                if spot:
                    mp, x, y, facing, _ = world.FLY_SPOTS[spot]
                    self.fade_t = 0.6
                    self.fade_kind = "fade"
                    self.warp_to(mp, x, y, facing)
                self._pump(None)
        elif self.state == "learn":
            self.learn_screen.key(e)
            if self.learn_screen.done:
                self._learn_done()

    def _starter_done(self):
        pick = self.starter.result
        self.starter = None
        if pick:
            self.game.party = [Mon(pick, 5)]
            self.game.caught.add(pick)
            self.state = "dialog"
            self._pump(pick)
        else:
            self.state = "dialog"
            self._pump(None)

    # -------------------------------------------------- 更新
    def update(self, dt):
        self.water_t += dt
        self.alert_t += dt
        self.textbox.update(dt)
        if self.fade_t >= 0:
            self.fade_t -= dt
            if self.fade_kind == "blackout" and self.fade_t <= 0.8 and not self._blackout_done:
                self._blackout_done = True
                self.game.heal_party()
                if self.game.respawn and self.game.respawn[0] in world.MAPS:
                    mp, x, y, facing = self.game.respawn
                else:
                    mp, x, y, facing = world.START
                self.warp_to(mp, x, y, facing)
                self.show_notice("你眼前一黑……\n醒来时已经被送回了精灵中心,\n精灵们也恢复了。")
            if self.fade_t <= 0:
                self.fade_t = -1.0
                self._blackout_done = False
                self.fade_kind = None
            return
        if self.state != "field":
            return
        if self.alert_t < 0.6 and self.bubble:
            return
        if self.moving:
            running = bool(self.held & set(K.RUN))
            self.step_t += dt / (STEP_TIME_RUN if running else STEP_TIME)
            if self.step_t >= 1.0:
                self.px, self.py = self.step_to
                self.moving = False
                self._stride_parity += 1
                self._arrive()
                if self.state != "field":
                    return
                if self._auto_slide():
                    return
        if not self.moving and self.state == "field":
            d = None
            if self.held & set(K.UP):
                d = "up"
            elif self.held & set(K.DOWN):
                d = "down"
            elif self.held & set(K.LEFT):
                d = "left"
            elif self.held & set(K.RIGHT):
                d = "right"
            if d:
                self.dir = d
                dx, dy = DIRS[d]
                nx, ny = self.px + dx, self.py + dy
                if self._can_step(nx, ny, d):
                    self._start_step(nx, ny)

    def _can_step(self, nx, ny, d):
        m = self.map
        if self.surfing and self.tile(nx, ny) == "w":
            return True
        if self.solid(nx, ny):
            return False
        if self.npc_at(nx, ny):
            return False
        return True

    def _auto_slide(self):
        """冰面/箭头:落在滑块上时自动继续滑动。"""
        t = self.tile(self.px, self.py)
        d = None
        if t == "i":
            d = self.dir
        elif t in ARROWS:
            d = ARROWS[t]
        if not d or self.surfing:
            return False
        dx, dy = DIRS[d]
        nx, ny = self.px + dx, self.py + dy
        if self._can_step(nx, ny, d):
            self.dir = d
            self._start_step(nx, ny)
            return True
        return False

    def _arrive(self):
        m = self.map
        warp = m.warps.get((self.px, self.py))
        if warp:
            rule = m.rules.get((self.px, self.py))
            if rule and not self.game.flags.get(rule[0]):
                self.px, self.py = self.step_from
                self.show_notice(rule[1])
                return
            if self._gate(warp):
                return
            self.warp_to(*warp)
            return
        t = self.tile(self.px, self.py)
        if t == "W" and self.surfing:
            dx, dy = DIRS[self.dir]
            if self.dir == "up" and self._can_step(self.px + dx, self.py + dy, "up"):
                self._start_step(self.px + dx, self.py + dy)
            return
        if self.surfing and t not in ("w", "W"):
            self.surfing = False           # 踏上陆地即下艇
        self.steps += 1
        if self.steps % 128 == 0:
            for mon in self.game.party:
                mon.friendship = min(255, mon.friendship + 1)
        if self.safari:
            self.safari["steps"] -= 1
            if self.safari["steps"] <= 0:
                self.safari = None
                self.start_script(self._safari_end_script())
                return
        if self.game.repel > 0:
            self.game.repel -= 1
            if self.game.repel == 0:
                self.show_notice("喷雾的效果消失了!")
                return
        if t == "," or (t == "c" and self.map.cave):
            self._grass_encounter()                         # 高草丛与洞窟地面都会遇到野生精灵
        elif t == "w" and self.surfing:
            self._water_encounter()
        if self.state != "field":
            return
        self._check_sight()

    def _gate(self, warp):
        """剧情门禁:按目标地图检查。"""
        dest = warp[0]
        f = self.game.flags
        dm = world.MAPS.get(dest)
        if dm is not None and not self.surfing and dm.tile(warp[1], warp[2]) in ("w", "W") \
                and not self.game.knowable_hm("冲浪"):
            # 从陆地走进水路却没有能冲浪的精灵:过去就会被困在水面上
            self.px, self.py = self.step_from
            self.show_notice("前面是水路。\n(需要一只会冲浪、且还有战斗能力的精灵才能过去)")
            return True
        if dest in ("r202", "verity_lakefront", "r220") and not f.get("starter"):
            # 没有伙伴不能离开真砂镇(研究所就在镇上西南角)
            self.px, self.py = self.step_from
            self.show_notice("还没有伙伴就出远门太危险了!\n先去镇西南黄色屋顶的研究所\n找山梨博士领取精灵吧。")
            return True
        if dest == "e4_aaron" and self.map_id == "league_gate":
            if self.game.badge_count() < 8:
                self.px, self.py = self.step_from
                self.show_notice("工作人员:只有集齐 8 枚徽章\n才能挑战四天王!")
                return True
        if self.map_id in ("e4_aaron", "e4_bertha", "e4_flint", "e4_lucian") and warp[0].startswith("e4_") \
                or (self.map_id == "e4_lucian" and dest == "champion_room"):
            need = {"e4_aaron": "beat_aaron", "e4_bertha": "beat_bertha",
                    "e4_flint": "beat_flint", "e4_lucian": "beat_lucian"}[self.map_id]
            if not f.get(need):
                self.px, self.py = self.step_from
                self.show_notice("门紧闭着。\n(先打败这间房间的天王吧。)")
                return True
        if dest == "r222" and self.map_id == "valor_lakefront" and not f.get("spear_clear"):
            self.px, self.py = self.step_from
            self.show_notice("警察:前面禁止通行!")
            return True
        return False

    def _check_sight(self):
        for n in self.visible_npcs():
            if not n.get("trainer") or not n.get("sight"):
                continue
            if self.game.flags.get(f"beat_{n['trainer']}"):
                continue
            dx, dy = DIRS[n.get("dir", "down")]
            for k in range(1, n["sight"] + 1):
                tx, ty = n["x"] + dx * k, n["y"] + dy * k
                if not (0 <= tx < self.map.w and 0 <= ty < self.map.h):
                    break
                if tx == self.px and ty == self.py:
                    n["dir"] = _face_back(tx, ty, n["x"], n["y"])
                    self.bubble = n
                    self.alert_t = 0.0
                    self._run_npc(n)
                    return
                t = self.tile(tx, ty)
                if t in world.SOLID or self.npc_at(tx, ty):
                    break

    # -------------------------------------------------- 绘制
    def _cam(self):
        m = self.map
        if self.moving:
            fx, fy = self.step_from
            t = max(0.0, min(1.0, self.step_t))
            pwx = (fx + (self.step_to[0] - fx) * t) * S.TILE + S.TILE // 2
            pwy = (fy + (self.step_to[1] - fy) * t) * S.TILE + S.TILE // 2
        else:
            pwx = self.px * S.TILE + S.TILE // 2
            pwy = self.py * S.TILE + S.TILE // 2
        vw, vh = S.VIEW_TW * S.TILE, S.VIEW_TH * S.TILE
        cam_x = int(pwx - vw / 2)
        cam_y = int(pwy - vh / 2)
        mw, mh = m.w * S.TILE, m.h * S.TILE
        cam_x = (mw - vw) // 2 if mw <= vw else max(0, min(mw - vw, cam_x))
        cam_y = (mh - vh) // 2 if mh <= vh else max(0, min(mh - vh, cam_y))
        return cam_x, cam_y

    def _player_world_px(self):
        if self.moving:
            fx, fy = self.step_from
            t = max(0.0, min(1.0, self.step_t))
            return ((fx + (self.step_to[0] - fx) * t) * S.TILE,
                    (fy + (self.step_to[1] - fy) * t) * S.TILE)
        return self.px * S.TILE, self.py * S.TILE

    def _door_tile(self, ch, tx, ty):
        m = self.map
        if ch == "w":
            return "wt" if self.tile(tx, ty - 1) != "w" else ("w0" if int(self.water_t * 2) % 2 == 0 else "w1")
        if ch == "D":
            if self.map_id.endswith("_center"):
                return "DI"
            return {"gym": "DG"}.get(self.map_id.split("_")[-1], "DI" if m.indoor else "D")
        return ch

    def draw(self, surf):
        m = self.map
        base = (10, 12, 18) if m.indoor else ((40, 44, 60) if m.cave else (10, 12, 18))
        self._legend_flag = getattr(self, "_legend_flag", None)
        surf.fill(base)
        cam_x, cam_y = self._cam()
        tiles = self.game.assets["tiles"]
        water_frame = "w0" if int(self.water_t * 2) % 2 == 0 else "w1"
        tx0, ty0 = int(cam_x // S.TILE), int(cam_y // S.TILE)
        for ty in range(max(0, ty0 - 1), min(m.h, ty0 + S.VIEW_TH + 2)):
            for tx in range(max(0, tx0 - 1), min(m.w, tx0 + S.VIEW_TW + 2)):
                ch = self.tile(tx, ty)
                under = "o" if m.indoor else ("c" if m.cave else ".")
                surf.blit(tiles[under], ((tx * S.TILE - cam_x) * S.SCALE,
                                         (ty * S.TILE - cam_y) * S.SCALE))
                if ch == "w":
                    tchar = "wt" if self.tile(tx, ty - 1) != "w" else water_frame
                elif ch == "D":
                    tchar = "DI" if m.indoor else "D"
                else:
                    tchar = ch
                surf.blit(tiles.get(tchar, tiles[under]),
                          ((tx * S.TILE - cam_x) * S.SCALE, (ty * S.TILE - cam_y) * S.SCALE))
        people = self.game.assets["people"]
        for npc in self.visible_npcs():
            pal = npc["pal"]
            if pal == "trainer":
                pal = PAL_BY_CLASS.get(data.TRAINERS[npc["trainer"]]["raw"].replace("TRAINER_CLASS_", ""),
                                       "villager")
            sprites = people.get(pal, people["villager"])
            self._blit_char(surf, sprites, npc["x"], npc["y"], npc.get("dir", "down"), 0, cam_x, cam_y)
        if self.bubble and self.alert_t < 0.6:
            n = self.bubble
            x = (n["x"] * S.TILE - cam_x) * S.SCALE
            y = (n["y"] * S.TILE - cam_y) * S.SCALE - 30
            draw_text(surf, "!", x + 20, y, 26, color=(240, 60, 60))
        if self.moving:
            wx, wy = self._player_world_px()
            stride = 1 if self._stride_parity % 2 == 0 else 2
            frame = stride if self.step_t < 0.55 else 0
            self._blit_char_px(surf, people["player"], wx, wy, self.dir, frame, cam_x, cam_y, self.surfing)
        else:
            self._blit_char(surf, people["player"], self.px, self.py, self.dir, 0, cam_x, cam_y, self.surfing)
        self._draw_overlays(surf)

    def _blit_char(self, surf, sprites, tx, ty, d, frame, cam_x, cam_y, surf_board=False):
        self._blit_char_px(surf, sprites, tx * S.TILE, ty * S.TILE, d, frame, cam_x, cam_y, surf_board)

    def _blit_char_px(self, surf, sprites, wx, wy, d, frame, cam_x, cam_y, surf_board=False):
        if surf_board:
            x = (wx - cam_x) * S.SCALE
            y = (wy - cam_y) * S.SCALE
            pygame.draw.ellipse(surf, (240, 120, 60), (x + 4, y + 30, 40, 20))
            pygame.draw.ellipse(surf, (90, 170, 240), (x - 4, y + 34, 52, 18))
        img = sprites[d][frame]
        x = (wx - cam_x) * S.SCALE
        y = (wy - cam_y) * S.SCALE + S.STILE - img.get_height() + 4 * S.SCALE
        surf.blit(img, (x, y - 4 * S.SCALE - (6 * S.SCALE if surf_board else 0)))

    def _draw_overlays(self, surf):
        if self.state == "menu":
            n = len(self.menu_opts)
            panel(surf, (S.WIN_W - 250, 20, 210, 44 * n + 124), bg=S.C_MENU_BG)
            for i, o in enumerate(self.menu_opts):
                oy = 42 + i * 44
                if i == self.menu_idx:
                    cursor_arrow(surf, S.WIN_W - 222, oy + 15)
                draw_text(surf, o, S.WIN_W - 196, oy, 24)
            for bi, (flag, name, label, col) in enumerate(data.BADGES):
                bx = S.WIN_W - 236 + bi % 4 * 50
                by = 20 + 44 * n + 26 + (bi // 4) * 30
                pygame.draw.circle(surf, col if self.game.flags.get(flag) else (150, 160, 180),
                                   (bx, by), 12)
                if self.game.flags.get(flag):
                    draw_text(surf, label, bx, by - 1, 15, color=(70, 50, 20), anchor="center")
            draw_text(surf, f"{K.HINT_CONFIRM} 确认   {K.HINT_CANCEL} 返回", S.WIN_W - 236, 20 + 44 * n + 94, 16,
                      color=(110, 125, 150), shadow=False)
        elif self.state == "party" and self.party_screen:
            self.party_screen.draw(surf, self.game.assets["icons"])
        elif self.state == "bag" and self.bag_screen:
            self.bag_screen.draw(surf)
        elif self.state == "starter" and self.starter:
            self.starter.draw(surf, self.game.assets["icons"])
        elif self.state == "badges" and self.badge_screen:
            self.badge_screen.draw(surf)
        elif self.state == "fly" and self.fly_screen:
            self.fly_screen.draw(surf)
        elif self.state == "learn" and self.learn_screen:
            self.learn_screen.draw(surf)
        if self.state == "shop" and self.shop_screen:
            self.shop_screen.draw(surf)
        if self.state == "dialog":
            self.textbox.draw(surf)
        if self.fade_t >= 0:
            fog = pygame.Surface((S.WIN_W, S.WIN_H))
            fog.fill((0, 0, 0))
            k = self.fade_t / (1.2 if self.fade_kind == "blackout" else 0.6)
            fog.set_alpha(int(255 * max(0.0, min(1.0, k))))
            surf.blit(fog, (0, 0))
        name = m_name = self.map.name
        if self.surfing:
            name += "(冲浪中)"
        if self.safari:
            name += f"  狩猎球×{self.safari['balls']}"
        panel(surf, (6, 6, 60 + 22 * len(name), 30), bg=S.C_MENU_BG)
        draw_text(surf, name, 18, 10, 18, color=S.C_UI_TEXT, shadow=False)
