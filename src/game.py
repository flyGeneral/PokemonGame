"""游戏总控:资产构建、场景栈、道具/队伍状态、存档/读档、主循环。"""
import json
import os

import pygame

from . import settings as S
from . import art
from . import data
from .mon import Mon


class Game:
    def __init__(self):
        pygame.mixer = None  # 不使用音频
        pygame.init()
        # 上一局 run() 结束会 pygame.quit(),旧字体对象随之失效,必须清缓存
        from .ui import _FONT_CACHE
        _FONT_CACHE.clear()
        self.screen = pygame.display.set_mode((S.WIN_W, S.WIN_H))
        pygame.display.set_caption("宝可梦 钻石·珍珠 · 神奥复刻")
        mons, icons, mons_back = art.build_mons()
        self.assets = {
            "mons": mons,
            "mons_back": mons_back,
            "icons": icons,
            "people": art.build_people(),
            "tiles": art.build_tiles(),
            "ball": art.build_ball(48),
            "balls": art.build_balls(48),
            "battle_bg": art.build_battle_bg(),
        }
        self.party = []
        self.pc = []
        self.bag = {}
        self.money = 0
        self.flags = {}
        self.version = "D"            # D=钻石 P=珍珠
        self.caught = set()           # 已捕获过的种类(重复球)
        self.respawn = None           # 黑屏后回到的精灵中心 (map, x, y, facing)
        self.tile_over = {}           # {map_id: {(x,y): 图块}} 打碎的岩石/推开的石头/拾取的道具/拉杆
        self.player_name = "小辉"
        self.last_battle = None
        self.scenes = []

    # -------------------------------------------------- 队伍/道具
    def heal_party(self):
        for m in self.party:
            m.full_heal()

    def bag_order(self, pocket=None):
        """按类别排序的道具名列表;pocket ∈ items/tm/key/battle 时只返回该口袋。"""
        from .ui import KIND_ORDER
        groups = {"items": ("ball", "heal", "fullheal", "cure", "revive", "pp", "ppall", "evo"),
                  "tm": ("tm",), "key": ("key",), "battle": ("stat", "crit")}
        want = groups.get(pocket) if pocket else None
        items = [n for n in self.bag if self.bag.get(n, 0) > 0 and n in data.ITEMS]
        if want:
            items = [n for n in items if data.ITEMS[n]["kind"] in want]
        return sorted(items, key=lambda n: (KIND_ORDER.index(data.ITEMS[n]["kind"])
                                            if data.ITEMS[n]["kind"] in KIND_ORDER else 99, items.index(n)))

    def has_item(self, name):
        return self.bag.get(name, 0) > 0

    def give_item(self, name, n=1):
        self.bag[name] = self.bag.get(name, 0) + n

    def remove_item(self, name, n=1):
        self.bag[name] = self.bag.get(name, 0) - n
        if self.bag[name] <= 0:
            del self.bag[name]

    @property
    def version_name(self):
        return {"D": "钻石", "P": "珍珠"}[self.version]

    def badge_count(self):
        return sum(1 for flag, *_ in data.BADGES if self.flags.get(flag))

    def knowable_hm(self, move_name):
        """队伍中是否有精灵会某秘传招式(地图使用)。"""
        return any(m.hp > 0 and m.knows(move_name) for m in self.party)

    # -------------------------------------------------- 场景
    def new_game(self, version="D"):
        from .overworld import Overworld
        from .world import START
        self.party = []
        self.pc = []
        self.bag = {}
        self.flags = {}
        self.money = 3000
        self.version = version
        self.caught = set()
        self.respawn = None
        self.tile_over = {}
        self.last_battle = None
        ow = Overworld(self, START[0], START[1], START[2], START[3])
        self.scenes = [ow]
        ow.start_intro()

    def push_battle(self, enemy_team=None, trainer_name=None, callback=None, ai_level=1,
                    trainer_key=None, display=None, context=None, safari=False, safari_balls=0):
        from .battle import Battle
        for sc in self.scenes:            # 进战斗前清掉移动按键,防止出战斗后漂移
            if hasattr(sc, "held"):
                sc.held.clear()
        b = Battle(self, enemy_team, trainer_name=trainer_name, callback=callback,
                   ai_level=ai_level, trainer_key=trainer_key, display=display, context=context,
                   safari=safari, safari_balls=safari_balls)
        self.scenes.append(b)
        return b

    # -------------------------------------------------- 存档
    def save(self):
        ow = self._overworld()
        d = {
            "version": self.version,
            "party": [m.to_dict() for m in self.party],
            "pc": self.pc,
            "bag": self.bag,
            "flags": self.flags,
            "money": self.money,
            "caught": sorted(self.caught),
            "respawn": self.respawn,
            "tile_over": {k: {f"{x},{y}": c for (x, y), c in v.items()} for k, v in self.tile_over.items()},
        }
        if ow:
            d["map"] = ow.map_id
            d["x"], d["y"], d["facing"] = ow.px, ow.py, ow.dir
            d["surfing"] = ow.surfing
        with open(S.SAVE_PATH, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)

    def load(self):
        with open(S.SAVE_PATH, encoding="utf-8") as f:
            d = json.load(f)
        if "map" not in d:
            raise ValueError("旧版存档")
        from .overworld import Overworld
        from .world import MAPS
        self.party = []
        for x in d.get("party", []):
            try:                       # 跳过存档里已不存在的精灵
                self.party.append(Mon.from_dict(x))
            except (AssertionError, KeyError):
                continue
        self.pc = [m for m in (self._safe_mon(x) for x in d.get("pc", [])) if m]
        self.bag = {k: v for k, v in d.get("bag", {}).items() if k in data.ITEMS}
        self.flags = d.get("flags", {})
        self.money = d.get("money", 3000)
        self.version = d.get("version", "D")
        self.caught = set(d.get("caught", []))
        self.respawn = d.get("respawn")
        self.tile_over = {}
        for k, v in d.get("tile_over", {}).items():
            self.tile_over[k] = {tuple(int(c) for c in key.split(",")): ch for key, ch in v.items()}
        map_id = d.get("map") if d.get("map") in MAPS else "twinleaf"
        ow = Overworld(self, map_id, d.get("x", 10), d.get("y", 12), d.get("facing", "down"))
        ow.surfing = bool(d.get("surfing")) and ow.map.tile(ow.px, ow.py) == "w"
        self.scenes = [ow]

    @staticmethod
    def _safe_mon(x):
        try:
            return Mon.from_dict(x)
        except (AssertionError, KeyError):
            return None

    def _overworld(self):
        for s in self.scenes:
            if hasattr(s, "map_id"):
                return s
        return None

    # -------------------------------------------------- 主循环
    def tick(self, dt):
        """推进一帧:弹窗结算、更新、绘制。供主循环与 RL 环境共用。"""
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return False
            if not self.scenes:
                continue
            if e.type == pygame.KEYUP:
                # 松键必须广播:否则战斗吞掉 KEYUP,出战斗后方向键会卡死
                for sc in self.scenes:
                    sc.handle_event(e)
            else:
                self.scenes[-1].handle_event(e)
        while len(self.scenes) > 1 and getattr(self.scenes[-1], "done", False):
            b = self.scenes.pop()
            if b.callback:
                b.callback(getattr(b, "result", None))
        if self.scenes:
            self.scenes[-1].update(dt)
            self.scenes[-1].draw(self.screen)
            pygame.display.flip()
        return True

    def run(self, max_frames=None):
        from .title import Title
        if not self.scenes:
            self.scenes = [Title(self)]
        clock = pygame.time.Clock()
        running = True
        frames = 0
        while running and self.scenes:
            dt = clock.tick(S.FPS) / 1000.0
            running = self.tick(dt)
            frames += 1
            if max_frames and frames >= max_frames:
                running = False
        pygame.quit()
