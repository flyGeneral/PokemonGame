"""星钻精灵 Gym 风格强化学习环境。

设计参考 PWhiddy/PokemonRedExperiments (MIT):
  - 手柄式离散动作空间(↑↓←→ / A / B / START),帧跳执行
  - 基于坐标的探索奖励(V2 思路):新格子高额奖励、重访奖励衰减
  - 进度信号:徽章、等级总和、队伍数量(捕捉)、黑屏惩罚
  - 观测 = 降采样画面像素 + 游戏状态向量(原项目读 RAM,这里直接读游戏对象)

不依赖 gymnasium 也能跑;若安装了 gymnasium 则自动暴露 spaces。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import numpy as np
import pygame

from src import settings as S
from src.game import Game
from src.overworld import Overworld

# 动作: 0↑ 1↓ 2← 3→ 4=A(Z) 5=B(X) 6=START(回车)
ACTIONS = [pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT,
           pygame.K_z, pygame.K_x, pygame.K_RETURN]
ACTION_NAMES = ["up", "down", "left", "right", "A", "B", "START"]
OBS_SCREEN = (120, 78)          # 降采样画面 WxH

REWARD = {
    "new_tile": 0.5,        # 首次踏足格子
    "revisit": -0.001,      # 重访衰减
    "level_up": 1.0,        # 每级
    "catch": 3.0,           # 每只捕捉
    "badge": 10.0,          # 目标达成
    "blackout": -2.0,
    "step": -0.002,
}

try:  # 可选: gymnasium spaces
    from gymnasium import spaces
    HAS_GYM = True
except Exception:
    HAS_GYM = False


class PokeEnv:
    """用法:
        env = PokeEnv(max_steps=5000)
        obs, info = env.reset()
        obs, reward, terminated, truncated, info = env.step(0)
    """

    metadata = {"name": "stardrop-mon-v0"}

    def __init__(self, max_steps=20000, frame_skip=4, seed=None,
                 screen_obs=True, headless=True):
        self.max_steps = max_steps
        self.frame_skip = frame_skip
        self.screen_obs = screen_obs
        self.rng = np.random.default_rng(seed)
        if headless:
            os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        self.game = Game()
        self.reset()

    # -------------------------------------------------- 空间描述
    @property
    def action_space_n(self):
        return len(ACTIONS)

    def observation_spec(self):
        spec = {
            "state": {"shape": (8,), "dtype": "float32",
                      "desc": "x,y,地图,HP比,最高等级,徽章,球数,步数"},
            "screen": {"shape": (OBS_SCREEN[1], OBS_SCREEN[0], 3), "dtype": "uint8"},
        }
        return spec

    if HAS_GYM:
        @property
        def action_space(self):
            return spaces.Discrete(len(ACTIONS))

        @property
        def observation_space(self):
            return spaces.Dict({
                "state": spaces.Box(0, 1, (8,), np.float32),
                "screen": spaces.Box(0, 255, (OBS_SCREEN[1], OBS_SCREEN[0], 3), np.uint8),
            })

    # -------------------------------------------------- 内部状态
    def _overworld(self):
        ow = self.game._overworld()
        return ow

    def _snapshot(self):
        ow = self._overworld()
        g = self.game
        levels = sum(m.level for m in g.party)
        hp = (sum(m.hp for m in g.party) /
              max(1, sum(m.max_hp for m in g.party))) if g.party else 0.0
        balls = sum(v for k, v in g.bag.items() if "球" in k)
        return {
            "x": ow.px, "y": ow.py, "map": ow.map_id,
            "hp_ratio": hp, "total_levels": levels,
            "badges": 1 if g.flags.get("has_badge") else 0,
            "party_size": len(g.party), "pc_size": len(g.pc),
            "balls": balls, "starter": bool(g.flags.get("starter_chosen")),
        }

    def _obs(self):
        snap = self._snapshot()
        map_idx = ["town", "route", "house", "lab", "gym"].index(snap["map"])
        state = np.array([
            snap["x"] / 32.0,
            snap["y"] / 32.0,
            map_idx / 4.0,
            snap["hp_ratio"],
            snap["total_levels"] / 300.0,
            snap["badges"],
            min(1.0, snap["balls"] / 10.0),
            self.steps / self.max_steps,
        ], dtype=np.float32)
        obs = {"state": state}
        if self.screen_obs:
            small = pygame.transform.scale(self.game.screen, OBS_SCREEN)
            arr = pygame.surfarray.array3d(small)          # (W,H,3)
            obs["screen"] = arr.transpose(1, 0, 2).copy()   # → (H,W,3)
        return obs

    def _info(self, snap=None):
        snap = snap or self._snapshot()
        return {
            **snap,
            "steps": self.steps,
            "total_reward": round(self.total_reward, 3),
            "explored": len(self.visited),
            "explored_ratio": round(len(self.visited) / max(1, self.total_walkable), 3),
        }

    # -------------------------------------------------- API
    def reset(self, seed=None, options=None):
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        import random as _r
        _r.seed(self.rng.integers(1 << 30))
        self.game.party = []
        self.game.pc = []
        self.game.bag = {}
        self.game.flags = {}
        self.game.scenes = []
        from src.worldmap import SCRIPTS
        ow = Overworld(self.game)
        self.game.scenes = [ow]
        ow.start_script(SCRIPTS["intro"](self.game))
        self.steps = 0
        self.total_reward = 0.0
        self.visited = set()
        self._prev = self._snapshot()
        self._prev_levels = 0
        self._prev_team = 0
        self._held = None
        self._held_left = 0
        # 可踏足格子总数(探索率分母)
        self.total_walkable = 0
        from src import worldmap
        for mp in worldmap.MAPS.values():
            for y in range(mp.h):
                for x in range(mp.w):
                    if not mp.solid(x, y):
                        self.total_walkable += 1
        return self._obs(), self._info()

    def step(self, action):
        assert 0 <= action < len(ACTIONS), f"非法动作 {action}"
        key = ACTIONS[action]
        pressed = pygame.event.Event(pygame.KEYDOWN, key=key)
        released = pygame.event.Event(pygame.KEYUP, key=key)
        reward = REWARD["step"]
        terminated = truncated = False

        for f in range(self.frame_skip):
            if f == 0:
                self.game.scenes[-1].handle_event(pressed)
            alive = self.game.tick(1.0 / 60.0)
            if not alive:
                truncated = True
                break
            # 战斗结算(弹层)
            while len(self.game.scenes) > 1 and getattr(self.game.scenes[-1], "done", False):
                b = self.game.scenes.pop()
                if b.callback:
                    b.callback(b.result)
        # 松开按键:避免 held 集合累积导致方向锁死
        scene = self.game.scenes[-1] if self.game.scenes else None
        if scene is not None and hasattr(scene, "held"):
            scene.handle_event(released)

        self.steps += 1
        snap = self._snapshot()
        ow = self._overworld()

        # --- 奖励塑形 ---
        tile_key = (snap["map"], snap["x"], snap["y"])
        if tile_key not in self.visited:
            self.visited.add(tile_key)
            reward += REWARD["new_tile"]
        else:
            reward += REWARD["revisit"]
        dl = snap["total_levels"] - self._prev_levels
        if dl > 0:
            reward += dl * REWARD["level_up"]
        dt_team = (snap["party_size"] + snap["pc_size"]) - self._prev_team
        if dt_team > 0:
            reward += dt_team * REWARD["catch"]
        if snap["badges"] > self._prev.get("badges", 0):
            reward += REWARD["badge"]
            terminated = True
        if (snap["map"] == "house" and self._prev["map"] != "house"
                and self._prev["hp_ratio"] < 0.5):
            reward += REWARD["blackout"]
        self._prev = snap
        self._prev_levels = snap["total_levels"]
        self._prev_team = snap["party_size"] + snap["pc_size"]
        self.total_reward += reward

        if self.steps >= self.max_steps:
            truncated = True
        obs = self._obs()
        return obs, round(float(reward), 4), terminated, truncated, self._info(snap)

    # -------------------------------------------------- 可视化
    def render_exploration(self, path):
        """把已探索格子画到全部地图拼接图上。"""
        from src import worldmap
        pad = 1
        maps = [worldmap.MAPS[k] for k in ("town", "route", "house", "lab", "gym")]
        W = max(m.w for m in maps) + 2 * pad
        H = sum(m.h + 2 * pad for m in maps)
        img = np.zeros((H, W, 3), dtype=np.uint8)
        img[:] = (30, 34, 46)
        y_off = pad
        for m in maps:
            for y in range(m.h):
                for x in range(m.w):
                    c = (58, 64, 84) if m.solid(x, y) else (96, 140, 90)
                    img[y_off + y, pad + x] = c
            y_off += m.h + 2 * pad
        y_off = pad
        for m in maps:
            for (mid, x, y) in self.visited:
                if mid == m.id:
                    img[y_off + y, pad + x] = (255, 220, 90)
            y_off += m.h + 2 * pad
        try:
            from PIL import Image
            Image.fromarray(img).save(path)
        except Exception:
            surf = pygame.Surface((W, H))
            pygame.surfarray.blit_array(surf, img.transpose(1, 0, 2))
            pygame.image.save(surf, path)
        return path
