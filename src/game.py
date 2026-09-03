"""游戏总控:资产构建、场景栈、存档/读档、主循环。"""
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
        self.screen = pygame.display.set_mode((S.WIN_W, S.WIN_H))
        pygame.display.set_caption("星钻精灵 — 珍珠·钻石风格 致敬 DEMO")
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
        self.flags = {}
        self.scenes = []

    # -------------------------------------------------- 队伍/道具
    def heal_party(self):
        for m in self.party:
            m.full_heal()

    def bag_order(self):
        return [n for n in data.ITEMS if n in self.bag]

    # -------------------------------------------------- 场景
    def new_game(self):
        self.party = []
        self.pc = []
        self.bag = {}
        self.flags = {}
        from .overworld import Overworld
        from .worldmap import SCRIPTS
        ow = Overworld(self)
        self.scenes = [ow]
        ow.start_script(SCRIPTS["intro"](self))

    def push_battle(self, enemy_team, trainer_name=None, callback=None):
        from .battle import Battle
        for sc in self.scenes:            # 进战斗前清掉移动按键,防止出战斗后漂移
            if hasattr(sc, "held"):
                sc.held.clear()
        b = Battle(self, enemy_team, trainer_name=trainer_name, callback=callback)
        self.scenes.append(b)
        return b

    # -------------------------------------------------- 存档
    def save(self):
        ow = self._overworld()
        d = {
            "party": [m.to_dict() for m in self.party],
            "pc": self.pc,
            "bag": self.bag,
            "flags": self.flags,
        }
        if ow:
            d["map"] = ow.map_id
            d["x"], d["y"], d["facing"] = ow.px, ow.py, ow.dir
        with open(S.SAVE_PATH, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)

    def load(self):
        with open(S.SAVE_PATH, encoding="utf-8") as f:
            d = json.load(f)
        self.party = [Mon.from_dict(x) for x in d.get("party", [])]
        self.pc = d.get("pc", [])
        self.bag = d.get("bag", {})
        self.flags = d.get("flags", {})
        from .overworld import Overworld
        ow = Overworld(self, d.get("map", "town"), d.get("x", 10), d.get("y", 12),
                       d.get("facing", "down"))
        self.scenes = [ow]

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
                b.callback(b.result)
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
