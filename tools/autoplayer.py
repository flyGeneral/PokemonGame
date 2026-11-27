"""自动试玩:用真实的按键驱动游戏(不传送、不直接调脚本),按攻略顺序从双叶镇一路打到冠军。

做法:
  - 地图内用 BFS 规划最短路线(考虑 NPC、秘传障碍、冰面/箭头滑行、平台传送、冲浪/瀑布),
    按方向键逐格走;对话按 A,是/否按攻略选择;战斗用引擎伤害估算选招、低血用药、想抓的扔球
  - 道馆/天王前在精灵中心恢复;等级不够就在附近草丛刷野生精灵
用法:
  python3 tools/autoplayer.py                # 全程(无头,跳过绘制,几分钟)
  python3 tools/autoplayer.py --draw         # 实时绘制(慢,可观看)
  python3 tools/autoplayer.py --stop 25      # 只执行前 25 步(调试)
  python3 tools/autoplayer.py --resume 56     # 从上一步成功后的存档继续,从第 56 步开始(调试)
  python3 tools/autoplayer.py --verbose       # 打印每回合的战斗决策
"""
import collections
import os
import random
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame   # noqa: E402

from src import data, world   # noqa: E402
from src import settings as S   # noqa: E402
from src import keys as K   # noqa: E402
from src import ui as U   # noqa: E402
from src.battle import Battle, _FixedRandom   # noqa: E402
from src.game import Game   # noqa: E402
from src.ui import BagScreen   # noqa: E402

DIRS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
KEY_OF = {"up": pygame.K_UP, "down": pygame.K_DOWN, "left": pygame.K_LEFT, "right": pygame.K_RIGHT}
A = K.A[0]
DOWN = K.DOWN[0]
HM_MOVES = set(data.HM_MOVES.values())
WANTED = ["大牙狸", "姆克儿", "小猫怪", "含羞苞", "无壳海兔"]   # 想抓的伙伴(按优先级)
WANTED_LATE = ["毒蔷薇", "浮潜鼬", "恰雷姆", "大钢蛇"]           # 后期补伙伴用(224 道路 / 冠军之路)
_PREVO = {}
for _sp, _d in data.SPECIES.items():
    for _e in _d.get("evos", []):
        _PREVO.setdefault(_e["to"], _sp)


def family(sp):
    """进化链的最初形态:队伍里已经有同一家族(如已进化)就不再抓。"""
    seen = {sp}
    while sp in _PREVO and _PREVO[sp] not in seen:
        sp = _PREVO[sp]
        seen.add(sp)
    return sp
BALLS = ["高级球", "超级球", "精灵球"]
REPELS = ["黄金喷雾", "白银喷雾", "除虫喷雾"]
GRIND_MAPS = {"r203", "oreburgh_mine_b1", "r205s", "eterna_forest", "r208", "r215", "r212e", "r212n",
              "r210w", "iron_island", "r217", "coronet_peak", "r222", "victory_road_1"}   # 要刷野生精灵的地方,不用喷雾
# 帷幕百货买的学习器(编号, 教给谁):按优先级,钱不够的下次路过再买
TM_PLAN = [(35, "烈焰猴"),   # 喷射火焰
           (53, "毒蔷薇"),   # 能量球
           (24, "伦琴猫"),   # 十万伏特
           (36, "毒蔷薇"),   # 污泥炸弹
           (26, "烈焰猴"),   # 地震
           (27, "姆克鹰"),   # 报恩
           (13, "海兔兽"),   # 冰冻光束(对付竹兰的烈咬陆鲨)
           (30, "毒蔷薇")]   # 暗影球
VERBOSE = "--verbose" in sys.argv
S.SAVE_PATH = "/tmp/autoplayer_save.json"       # 不覆盖玩家的 save.json
HEALS = ["全复药", "厉害伤药", "好伤药", "伤药"]


class BotError(Exception):
    pass


def ev(key):
    return pygame.event.Event(pygame.KEYDOWN, key=key)


class Bot:
    def __init__(self, draw=False, version="D", seed=1):
        U.TEXT_SPEED = 1.0 if draw else 8.0
        random.seed(seed)
        self.game = Game()
        self.game.skip_draw = not draw
        self.game.new_game(version)
        self.ow = self.game.scenes[0]
        self.ticks = 0
        self.t0 = time.time()
        self.stats = collections.Counter()
        self.choice_plan = collections.deque()
        self.bag_intent = None
        self.potions_used = 0
        self.catch_tries = 0
        self.max_level_seen = 0
        self.heal_cooldown = 0
        self.avoid_sight = True
        self.sight_cache = set()
        self.heal_town = None        # 最近恢复过的城镇(有精灵中心),练级时低血回去恢复
        self._healing = False

    # ================================================================ 基础输入
    def log(self, msg):
        print(f"[{time.time() - self.t0:7.1f}s] {msg}", flush=True)

    def post(self, key, up=False):
        pygame.event.post(pygame.event.Event(pygame.KEYUP if up else pygame.KEYDOWN, key=key))

    def tick(self, n=1):
        for _ in range(n):
            self.game.tick(1 / 30)
            self.ticks += 1

    def tap(self, key, n=1):
        self.post(key)
        self.tick(1)
        self.post(key, True)
        self.tick(n)

    def ui_key(self, key):
        """向当前界面发一次按键,并立刻补一个松键事件,避免方向键留在 held 里。"""
        self.ow.handle_event(ev(key))
        self.ow.handle_event(pygame.event.Event(pygame.KEYUP, key=key))

    # ================================================================ 状态推进
    def settle(self, limit=60000):
        """处理对话/战斗/演出,直到回到可行动的野外状态;菜单类界面留给调用者。"""
        for _ in range(limit):
            self.tick(1)
            if len(self.game.scenes) > 1:
                top = self.game.scenes[-1]
                if isinstance(top, Battle):
                    self.drive_battle(top)
                elif hasattr(top, "handle_event"):
                    top.handle_event(ev(A))            # 名人堂/制作人员名单
                continue
            ow = self.ow
            if ow.fade_t >= 0:
                continue
            st = ow.state
            if st == "field":
                if not ow.moving and ow.script is None:
                    if ow.bubble is None or ow.alert_t >= 0.6:
                        if self.field_heal():
                            continue
                        return
                continue
            if st == "dialog":
                tb = ow.textbox
                if tb.wait_key:
                    if tb.choices is not None:
                        idx = self.choice_plan.popleft() if self.choice_plan else 0
                        for _ in range(idx):
                            self.ui_key(DOWN)
                        self.stats["choices"] += 1
                    self.ui_key(A)
                else:
                    self.ui_key(A)
                continue
            if st == "starter":
                self.ui_key(A)
                self.ui_key(A)
                if ow.starter and ow.starter.done:
                    ow._starter_done()
                continue
            return                                           # menu/bag/party/learn/shop: 调用者处理
        raise BotError("settle 超时:状态卡住")

    def field_heal(self):
        """野外:有精灵 HP 低于 35% 且有药时,用背包里的药(避免下一个训练家直接打输)。"""
        game = self.game
        if not game.party:
            return False
        hurt = [m for m in game.party if m.hp > 0 and m.hp < m.max_hp * 0.35]
        if not hurt or len(hurt) == len([m for m in game.party if m.hp > 0]) and len(hurt) > 1 and False:
            return False
        item = next((n for n in HEALS if game.has_item(n)), None)
        if not item:
            return False
        if self.heal_cooldown > 0:
            self.heal_cooldown -= 1
            return False
        target = min(hurt, key=lambda m: m.hp / m.max_hp)
        ow = self.ow
        ow.bag_from = "field"
        ow.bag_screen = BagScreen(game, "menu")
        ow.state = "bag"
        for _ in range(ow.bag_screen.items.index(item)):
            self.ui_key(DOWN)
        self.ui_key(A)                                # 选道具 → 选精灵
        if ow.state == "party":
            self.party_select(game.party.index(target))
        self.heal_cooldown = 6                                 # 不要每步都停下来喝药(先设置,避免嵌套递归)
        self.settle()
        self.stats["field_heals"] += 1
        return True

    def party_select(self, idx):
        """在精灵选择界面把光标移到第 idx 只并确认(光标默认停在第一只有战斗能力的精灵上)。"""
        party = self.game.party
        start = next((i for i, m in enumerate(party) if m.hp > 0), 0)
        for _ in range((idx - start) % len(party)):
            self.ui_key(DOWN)
        self.ui_key(A)

    # ================================================================ 战斗
    def drive_battle(self, b):
        b.auto = True
        self.potions_used = 0
        self.catch_tries = 0
        guard = turns = 0
        while not b.done and guard < 20000:
            guard += 1
            b.update(1 / 30)
            ph = b.phase
            if ph == "menu":
                turns += 1
                if b.trainer is None and turns > 30:       # 野生对战打太久(双方都在回血):像玩家一样跑
                    b._advance("run")
                    continue
                act = self.battle_menu(b)
                if VERBOSE:
                    a, f = b.ally, b.foe
                    self.log(f"      [决策] {act}  |  {a.species}{a.level} {a.hp}/{a.max_hp} "
                             f"vs {f.species}{f.level} {f.hp}/{f.max_hp}")
            elif ph == "movesel":
                mv = self.best_move(b)
                if VERBOSE:
                    self.log(f"      {b.ally.species} 使用 {b.ally.moves[mv].name}")
                b._advance(("move", mv))
            elif ph == "bag":
                item = self.bag_pick(b)
                b._advance(item)
            elif ph == "party":
                pick = self.party_pick(b)
                if self.bag_intent and self.bag_intent[0] == "item":
                    self.bag_intent = None
                b._advance(pick)
            elif ph == "learnmove":
                b._advance(self.learn_pick(b.learn_screen))
        if not b.done:
            raise BotError(f"对 {b.trainer or '野生'} 的战斗陷入僵局({turns} 回合)")
        if b.done:
            self.stats["battles"] += 1
            self.stats["result_" + str(b.result)] += 1
            kind = b.trainer or "wild"
            self.log(f"    战斗: {kind} → {b.result}  队伍 " +
                     "/".join(f"{m.species}{m.level}" for m in self.game.party[:3]) + " ...")
            self.tick(1)                                     # 弹出战斗层,触发回调

    def matchup(self, b, mon, foe):
        """该精灵对当前对手:每回合造成伤害 / 承受伤害(粗估)。"""
        best = 0
        for mv in mon.moves:
            if mv.pp <= 0:
                continue
            md = data.MOVES[mv.name]
            if md["cat"] == "变化" or not md["power"]:
                continue
            power_mod, fixed = b._power_modifiers(md.get("fx", {}), mon, foe, "foe", md)
            if fixed is not None:
                best = max(best, fixed)
                continue
            res = mon.calc_damage(foe, mv.name, rng=_FixedRandom(),
                                  mods={"power": power_mod, "crit_stage": 1, "weather": b.weather,
                                        "screen": b._screen_mod("foe", md)})
            if res["eff"] > 0:
                best = max(best, res["damage"])
        taken = 0
        for mv in foe.moves:
            md = data.MOVES[mv.name]
            if md["cat"] == "变化" or not md["power"]:
                continue
            res = foe.calc_damage(mon, mv.name, rng=_FixedRandom(), mods={"crit_stage": 1, "weather": b.weather})
            if res["eff"] > 0:
                taken = max(taken, res["damage"])
        return best, taken

    def race(self, b, mon, foe):
        """回合竞赛差:对方击倒我方所需回合数 - 我方击倒对方所需回合数(正=我方占优)。
        速度慢的一方后手,同等回合数时算输一回合。"""
        dealt, taken = self.matchup(b, mon, foe)
        my_ttk = 99 if dealt <= 0 else -(-foe.hp // dealt)
        foe_ttk = 99 if taken <= 0 else -(-mon.hp // taken)
        first = 1 if mon.effective_speed() >= foe.effective_speed() else -1
        return foe_ttk - my_ttk + first

    def battle_menu(self, b):
        ally, foe = b.ally, b.foe
        dealt, taken = self.matchup(b, ally, foe)
        kill = dealt >= foe.hp                                  # 估算能一招打倒:别浪费回合用药/扔球
        if b.trainer is None and self.want_catch(foe) and not kill:
            ball = self.best_ball(foe)
            if ball and self.catch_tries < 5:
                self.catch_tries += 1
                self.bag_intent = ("item", ball)
                b._advance("bag")
                return f"扔 {ball}"
        my_r = self.race(b, ally, foe)
        # 换人候选(上场要挨一下,所以领先回合数减 1);野生对战不派唯一会秘传招式的精灵
        cands = [(self.race(b, m, foe) - 1, i) for i, m in enumerate(self.game.party)
                 if i != b.p_idx and m.hp > 0 and not (b.trainer is None and self.sole_hm_user(m))]
        best_r, best_i = max(cands) if cands else (-99, None)
        if not kill:
            low = ally.hp < ally.max_hp * 0.4
            item = self.best_heal(ally) if self.potions_used < 4 else None
            if low:
                if my_r <= 0 and best_r > 0:
                    return self._switch(b, best_i, f"换 {self.game.party[best_i].species}(我方劣势 {my_r} → {best_r})")
                # 用药要能活过下一击(对方先手就按满血算,否则按补满后的血算)
                heal_amt = {"全复药": 999, "全满药": 999, "厉害伤药": 120, "好伤药": 50, "伤药": 20}.get(item, 20)
                after = min(ally.max_hp, ally.hp + heal_amt) if ally.effective_speed() >= foe.effective_speed() \
                    else ally.max_hp
                if item and after > taken:
                    self.potions_used += 1
                    self.bag_intent = ("item", item)
                    b._advance("bag")
                    return f"用 {item}(第 {self.potions_used} 次)"
                if best_r > my_r:
                    return self._switch(b, best_i, f"换 {self.game.party[best_i].species}(没药,我方劣势 {my_r} → {best_r})")
            elif best_r > my_r + 2 and (taken >= dealt * 1.5 or dealt <= ally.max_hp * 0.1):
                return self._switch(b, best_i, f"换 {self.game.party[best_i].species}(优势 {my_r} → {best_r})")
        b._advance("fight")
        return f"攻击(造成 {dealt} 承受 {taken}{' ,可击倒' if kill else ''})"

    def _switch(self, b, idx, why):
        self.stats["switches"] += 1
        b._advance("party")
        self.bag_intent = ("switch", idx)
        return why

    def want_catch(self, foe):
        party = self.game.party
        if len(party) >= 6 or foe.species not in WANTED + WANTED_LATE:
            return False
        fam = family(foe.species)
        if any(family(m.species) == fam for m in party):
            return False
        return any(self.game.has_item(b) for b in BALLS)

    def best_ball(self, foe):
        for name in BALLS:
            if self.game.has_item(name):
                return name
        return None

    def best_heal(self, ally):
        missing = ally.max_hp - ally.hp
        cands = [n for n in HEALS if self.game.has_item(n)]
        if not cands:
            return None
        # 缺得多用好药,缺得少用伤药
        if missing > 120 and "全复药" in cands:
            return "全复药"
        if missing > 90 and "厉害伤药" in cands:
            return "厉害伤药"
        for n in ("伤药", "好伤药", "厉害伤药", "全复药"):
            if n in cands:
                return n
        return cands[0]

    def bag_pick(self, b):
        if not self.bag_intent:
            b._advance(None)
            return None
        items = b.bag_screen.items
        name = self.bag_intent[1]
        self.bag_intent = None
        if name not in items:
            return None
        for _ in range(items.index(name)):
            b.bag_screen.key(ev(DOWN))
        b.bag_screen.key(ev(A))
        b.bag_screen = None
        return name

    def party_pick(self, b):
        ps = b.party_screen
        if ps.mode == "forced":
            cands = [i for i, m in enumerate(self.game.party) if m.hp > 0]
            # 选对当前对手最有利的(按回合竞赛差)
            return max(cands, key=lambda i: self.race(b, self.game.party[i], b.foe)) if cands else None
        if self.bag_intent and self.bag_intent[0] == "switch":
            idx = self.bag_intent[1]
            self.bag_intent = None
            return idx
        return b.p_idx                                       # 道具目标 = 当前出战

    def learn_pick(self, ls):
        """要学的新招式比最弱的旧招式强才替换;秘传招式永不忘记。"""
        new_val = self.move_val(ls.move)
        vals = [self.move_val(m.name) for m in ls.mon.moves]
        weakest = min(range(len(vals)), key=lambda i: vals[i])
        if new_val > vals[weakest] and ls.mon.moves[weakest].name not in HM_MOVES:
            return weakest
        return None

    def move_val(self, name):
        if name in HM_MOVES:
            return 500
        md = data.MOVES[name]
        fx = md.get("fx", {})
        if md["cat"] != "变化" and md["power"] and md["power"] > 1:
            return md["power"]
        if fx:
            return 60
        return 20

    def best_move(self, b):
        best, best_score = 0, -1e9
        for i, mv in enumerate(b.ally.moves):
            if mv.pp <= 0:
                continue
            s = self.move_score(b, mv)
            if s > best_score:
                best, best_score = i, s
        return best

    def move_score(self, b, mv):
        md = data.MOVES[mv.name]
        fx = md.get("fx", {})
        ally, foe = b.ally, b.foe
        if md["cat"] == "变化" or not md["power"]:
            if fx.get("heal") or fx.get("rest"):
                return 95 if ally.hp < ally.max_hp * 0.5 else 1
            if fx.get("status"):
                st = fx["status"][0]
                if foe.status or foe.status_immune(st) or foe.hp < foe.max_hp * 0.3:
                    return 1
                return 60 if st in ("睡眠", "麻痹", "剧毒") else 45
            if fx.get("confuse"):
                return 40 if not b.vol["foe"]["confuse"] and foe.hp > foe.max_hp * 0.4 else 1
            if fx.get("protect"):
                return 4
            if fx.get("stat"):
                eff = fx["stat"][0]
                if eff["who"] == "self" and eff["d"] > 0 and eff["stat"] in ("atk", "spa") \
                        and any(data.MOVES[mv2.name]["cat"] != "变化" for mv2 in ally.moves):
                    return 25 if b.turns < 2 and ally.hp > ally.max_hp * 0.7 and foe.hp > foe.max_hp * 0.7 else 3
                return 3
            if fx.get("ohko"):
                return 20
            return 1
        power_mod, fixed = b._power_modifiers(fx, ally, foe, "foe", md)
        if fixed is not None:
            dmg, eff = fixed, 1.0
        else:
            res = ally.calc_damage(foe, mv.name, att_stages=b.stages["ally"],
                                   dfn_stages=b.stages["foe"], rng=_FixedRandom(),
                                   mods={"power": power_mod, "crit_stage": 1, "weather": b.weather,
                                         "screen": b._screen_mod("foe", md)})
            dmg, eff = res["damage"], res["eff"]
        if eff == 0:
            return -1e9
        if dmg >= foe.hp:
            return 1e6
        s = float(dmg)
        if fx.get("recoil"):
            s -= dmg * fx["recoil"] * 0.6
        if fx.get("recharge"):
            s *= 0.55
        if fx.get("drain"):
            s += dmg * fx["drain"] * (1 - ally.hp / ally.max_hp)
        if fx.get("status") and not foe.status:
            s += dmg * fx["status"][1] / 300
        if fx.get("flinch") and b.turns < 3:
            s += dmg * fx["flinch"] / 400
        return s

    # ================================================================ 导航
    def npc_blocked(self, x, y):
        return self.ow.npc_at(x, y) is not None

    def sight_tiles(self):
        """未打败且有望远镜(视线范围)的训练家看到的格子;路线规划默认绕开。"""
        ow, m = self.ow, self.ow.map
        seen = set()
        for n in ow.visible_npcs():
            if not n.get("trainer") or not n.get("sight") or self.game.flags.get(f"beat_{n['trainer']}"):
                continue
            dx, dy = DIRS[n.get("dir", "down")]
            for k in range(1, n["sight"] + 1):
                tx, ty = n["x"] + dx * k, n["y"] + dy * k
                if not (0 <= tx < m.w and 0 <= ty < m.h) or m.solid(tx, ty) or ow.npc_at(tx, ty):
                    break
                seen.add((tx, ty))
        return seen

    def passable(self, x, y, surf):
        ow, m = self.ow, self.ow.map
        if not (0 <= x < m.w and 0 <= y < m.h):
            return False
        if self.avoid_sight and (x, y) in self.sight_cache and (x, y) != (ow.px, ow.py):
            return False
        t = ow.tile(x, y)
        blocker = ow.npc_at(x, y)
        if blocker is not None and not str(blocker.get("script")).startswith("quiz_door"):
            return False                                       # 算术之门NPC:对话即可穿过
        if t == "W":
            return surf and self.game.knowable_hm("攀瀑")
        if t == "K" and not self.game.knowable_hm("碎岩"):
            return False
        if t == "J" and not self.game.knowable_hm("居合劈"):
            return False
        if t == "O" and not self.game.knowable_hm("怪力"):
            return False
        if t in "KJO":
            return True                                       # 会相应秘传招式,可以打碎/砍/推
        if surf:
            return t == "w" or t not in world.SOLID
        if t == "w":
            return False
        return t not in world.SOLID

    def slide(self, x, y, surf, d):
        """冰面/箭头:模拟游戏的连续滑动,返回最终格。图内传送(移动平台)会跟随到落点。"""
        ow, m = self.ow, self.ow.map
        for _ in range(40):
            w = m.warps.get((x, y))
            if w is not None:
                if w[0] == m.id:                            # 同图平台传送:落到目标格
                    x, y = w[1], w[2]
                    surf = surf and m.tile(x, y, ow.tile_over) in ("w", "W")
                    continue
                return (x, y, surf)                         # 去别的图:到此为止
            t = ow.tile(x, y)
            nd = d if t == "i" else {"^": "up", "v": "down", "<": "left", ">": "right"}.get(t)
            if not nd:
                break
            dx, dy = DIRS[nd]
            nx, ny = x + dx, y + dy
            if not self.passable(nx, ny, surf):
                break
            if ow.tile(nx, ny) == "W" and surf and nd == "up":
                # 瀑布:游戏会自动再往上走一格
                if self.passable(nx, ny - 1, surf):
                    x, y = nx, ny - 1
                    continue
                break
            x, y = nx, ny
            d = nd
        t = ow.tile(x, y)
        return (x, y, surf and t in ("w", "W"))

    def step_result(self, x, y, surf, d):
        ow = self.ow
        dx, dy = DIRS[d]
        nx, ny = x + dx, y + dy
        if not self.passable(nx, ny, surf):
            return None
        if ow.tile(nx, ny) == "W" and surf and d == "up":
            if not self.passable(nx, ny - 1, surf):
                return None
            return self.slide(nx, ny - 1, True, d)
        return self.slide(nx, ny, surf, d)

    def mount_result(self, x, y, d, surf=False):
        """在陆地上面向水按 A 冲浪(已在水上则不能再上艇)。"""
        ow = self.ow
        if surf or not self.game.knowable_hm("冲浪"):
            return None
        dx, dy = DIRS[d]
        nx, ny = x + dx, y + dy
        if not (0 <= nx < ow.map.w and 0 <= ny < ow.map.h) or ow.tile(nx, ny) != "w":
            return None
        if self.npc_blocked(nx, ny):
            return None
        return self.slide(nx, ny, True, d)

    def plan(self, goal, allow_mount=True):
        ow = self.ow
        self.sight_cache = self.sight_tiles() if self.avoid_sight else set()
        start = (ow.px, ow.py, ow.surfing)
        if goal(*start):
            return []
        prev = {start: None}
        q = collections.deque([start])
        while q:
            st = q.popleft()
            x, y, surf = st
            if st != start and goal(x, y, surf):
                path = []
                cur = st
                while prev[cur] is not None:
                    cur, act = prev[cur]
                    path.append(act)
                path.reverse()
                return path
            if (x, y) in ow.map.warps and st != start:
                continue                                     # 传送格:到此为止(起点例外)
            for d in DIRS:
                res = self.step_result(x, y, surf, d)
                if res and res not in prev:
                    prev[res] = (st, ("move", d))
                    q.append(res)
            if allow_mount and not surf:
                for d in DIRS:
                    res = self.mount_result(x, y, d, surf)
                    if res and res not in prev:
                        prev[res] = (st, ("mount", d))
                        q.append(res)
        return None

    def navigate(self, goal, desc="", max_actions=400):
        """走到满足 goal 的格子;每走一步重新规划(对话/战斗打断后自动续路)。"""
        map0 = self.ow.map_id
        for _ in range(max_actions):
            ow = self.ow
            if goal(ow.px, ow.py, ow.surfing) and ow.map_id == map0:
                return True
            if ow.map_id != map0:
                return False                                    # 踩上出口/黑屏回中心等:换图了
            path = self.plan(goal)
            if not path:
                self.avoid_sight = False
                path = self.plan(goal)                         # 绕不开就硬闯(会被拉进对战)
                self.avoid_sight = True
            if not path and self.hm_user_down():
                # 原作规则:倒下的精灵不能用秘传招式 → 先用复苏道具,不行就回中心
                if self.revive_item():
                    continue
                if self.escape_rope():
                    return False
                if self.nearest_center() and not self._healing:
                    self.log(f"  会秘传招式的精灵倒下了,回 {self.nearest_center()} 恢复")
                    self.heal()
                    return False
            if not path:
                near = [(n.get("name") or n.get("script"), n["x"], n["y"]) for n in ow.visible_npcs()
                        if abs(n["x"] - ow.px) + abs(n["y"] - ow.py) <= 3]
                raise BotError(f"找不到路线: {desc}(从 {ow.map_id}@{ow.px},{ow.py} surf={ow.surfing} "
                               f"state={ow.state} moving={ow.moving} script={ow.script is not None} "
                               f"fade={ow.fade_t:.1f} npcs={near})")
            self.do_action(path[0])
            self.settle()
        raise BotError(f"路线太长: {desc}")

    def must_navigate(self, goal, desc=""):
        """同 navigate,但换图(被打回中心等)视为失败,交给上层重试。"""
        if not self.navigate(goal, desc):
            raise BotError(f"中途换图(打输回中心?),前往 {desc} 失败")

    def do_action(self, action):
        kind, d = action
        ow = self.ow
        key = KEY_OF[d]
        dx, dy = DIRS[d]
        nx, ny = ow.px + dx, ow.py + dy
        if kind == "mount":
            self.tap(key)
            self.tap(A)
            return
        t = ow.tile(nx, ny)
        door = ow.npc_at(nx, ny)
        if door is not None and str(door.get("script")).startswith("quiz_door"):
            self.tap(key)                                   # 面向算术之门
            self.tap(A)
            self.choice_plan.append(0 if door["script"] == "quiz_door_1" else 1)
            self.settle()
            return
        if t in "KJO":
            self.tap(key)                                   # 面向障碍(不会移动)
            self.tap(A)                                     # 使用秘传招式 → 是
        if t == "w" and not ow.surfing:
            raise BotError("需要冲浪但没有走 mount 动作")
        self.post(key)
        for _ in range(12):
            self.tick(1)
            if ow.moving or ow.state != "field" or len(self.game.scenes) > 1:
                break
        self.post(key, True)

    # ================================================================ 高层动作
    def world_route(self, src, dest):
        """世界地图图上的最短地图序列。"""
        prev = {src: None}
        q = collections.deque([src])
        while q:
            cur = q.popleft()
            if cur == dest:
                break
            for (x, y), (d, *_r) in world.MAPS[cur].warps.items():
                if d != cur and d not in prev:
                    prev[d] = cur
                    q.append(d)
        if dest not in prev:
            raise BotError(f"世界图上无法从 {src} 到 {dest}")
        route = []
        cur = dest
        while cur != src:
            route.append(cur)
            cur = prev[cur]
        return route[::-1]

    def travel(self, dest):
        # 像玩家一样:队伍状态差就先回中心,而不是带着残阵赶路
        town = self.nearest_center()
        if not self._healing and town and self.party_hp_ratio() < 0.4 \
                and dest not in (f"{town}_center", f"{town}_gate") and self.ow.map_id not in (f"{town}_center", f"{town}_gate"):
            self.log(f"  队伍状态不佳(HP {self.party_hp_ratio():.0%}),先回 {town} 恢复")
            try:
                self.heal()
            except BotError as e:
                self.log(f"  先回去恢复失败: {e}")
        hops = replans = 0
        if dest not in GRIND_MAPS:
            route = self.world_route(self.ow.map_id, dest)
            if len(route) >= 2 or (self._healing and self.party_hp_ratio() < 0.6):
                self.use_repel()
        while self.ow.map_id != dest:
            nxt = self.world_route(self.ow.map_id, dest)[0]
            ow = self.ow
            cands = [(x, y) for (x, y), (d, *_r) in ow.map.warps.items() if d == nxt]
            if not cands:
                raise BotError(f"{ow.map_id} 没有通往 {nxt} 的出口")
            cands.sort(key=lambda c: abs(c[0] - ow.px) + abs(c[1] - ow.py))
            ok = False
            last_err = None
            here = ow.map_id
            for (x, y) in cands:
                try:
                    self.navigate(lambda X, Y, S, tx=x, ty=y: X == tx and Y == ty, f"出口→{nxt}")
                    self.settle()
                    if ow.map_id not in (nxt, here):
                        break                                # 中途被打回中心等:换图了,重新规划路线
                    if ow.map_id != nxt and (ow.px, ow.py) == (x, y):
                        self.retrigger_warp()                  # 被野生对战打断在出口上:挪一格再踩回来
                    if ow.map_id == nxt:
                        ok = True
                        break
                    last_err = BotError(f"站在通往 {nxt} 的出口上却没有传送(被门禁?)")
                except BotError as e:
                    last_err = e
                    if self.ow.map_id not in (nxt, here):
                        break
            if not ok:
                if self.ow.map_id not in (nxt, here):          # 途中被打回中心等:换图了,重新规划路线
                    replans += 1
                    if replans <= 3:
                        self.log(f"  途中换图({self.ow.map_id}),重新规划前往 {dest} 的路线")
                        continue
                raise last_err or BotError(f"无法到达 {nxt}")
            hops += 1
            if hops > 60:
                raise BotError(f"前往 {dest} 的路线过长")
        self.stats["maps"] += 1

    def retrigger_warp(self):
        ow, m = self.ow, self.ow.map
        for d, (dx, dy) in DIRS.items():
            nx, ny = ow.px + dx, ow.py + dy
            if not m.solid(nx, ny) and (nx, ny) not in m.warps and not ow.npc_at(nx, ny):
                self.do_action(("move", d))
                self.settle()
                back = {"up": "down", "down": "up", "left": "right", "right": "left"}[d]
                self.do_action(("move", back))
                self.settle()
                return

    def adjacent_goals(self, tx, ty):
        tiles = [(tx + dx, ty + dy) for dx, dy in DIRS.values()]
        return tiles

    def approach(self, tx, ty, desc=""):
        tiles = self.adjacent_goals(tx, ty)
        ow = self.ow
        # 目标本身必须不可走(NPC/告示/道具/机关),否则"面对"它就会走上去
        self.must_navigate(lambda X, Y, S: (X, Y) in tiles and (tx, ty) != (X, Y), f"靠近 {desc} ({tx},{ty})")
        dx, dy = tx - ow.px, ty - ow.py
        d = {(-1, 0): "left", (1, 0): "right", (0, -1): "up", (0, 1): "down"}[(dx, dy)]
        self.tap(KEY_OF[d])                                  # 面向目标
        assert ow.tile(tx, ty) in world.SOLID or ow.npc_at(tx, ty), f"面对的目标 {desc} 不应是可走格"

    def find_npc(self, script):
        """在全世界找当前可见的、带指定脚本的 NPC(先找当前地图)。"""
        ow = self.ow
        for mid, m in [(ow.map_id, ow.map)] + list(world.MAPS.items()):
            for n in m.npcs:
                if n.get("script") != script:
                    continue
                if self.game.flags.get(f"hide_{mid}_{n['x']}_{n['y']}"):
                    continue                                     # 事件脚本里已 ("hide",) 的
                if n.get("hide") and self.game.flags.get(n["hide"]):
                    continue
                if n.get("show") and not self.game.flags.get(n["show"]):
                    continue
                return mid, n
        return None, None

    def talk(self, script, choices=(), expect=None, optional=False):
        """和带指定脚本的 NPC 对话;expect 为谈话后必须成立的旗标(没成立=打输了,抛错让上层练级重试)。
        optional: NPC 已不在(上次已打败并隐藏)时直接跳过。"""
        ow = self.ow
        mid, npc = self.find_npc(script)
        if npc is None:
            if optional:
                return
            raise BotError(f"找不到脚本 {script} 的 NPC(条件未满足?)")
        if mid != ow.map_id:
            self.travel(mid)
        self.choice_plan.extend(choices)
        self.approach(npc["x"], npc["y"], npc.get("name") or script)
        self.tap(A)
        self.settle()
        if expect and not self.game.flags.get(expect):
            raise BotError(f"与 {npc.get('name') or script} 的对战没有拿到 {expect}")

    def interact(self, x, y, choices=()):
        self.choice_plan.extend(choices)
        self.approach(x, y, f"格子 {x},{y}")
        self.tap(A)
        self.settle()

    def take_item(self, x, y):
        self.interact(x, y)

    def nearest_center(self):
        """世界图上离当前位置最近、且去过的精灵中心(联盟在 8 枚徽章后也算)。"""
        visited = {k[8:] for k, v in self.game.flags.items() if k.startswith("visited_") and v}
        if self.game.badge_count() >= 8:
            visited.add("league")
        prev = {self.ow.map_id: None}
        q = collections.deque([self.ow.map_id])
        while q:
            cur = q.popleft()
            town = cur[:-7] if cur.endswith("_center") else ("league" if cur == "league_gate" else None)
            if town and town in visited:
                return town
            for (x, y), (d, *_r) in world.MAPS[cur].warps.items():
                if d != cur and d not in prev and d in world.MAPS:
                    prev[d] = cur
                    q.append(d)
        return None

    def heal(self, town=None):
        town = town or self.nearest_center() or self.heal_town
        if not town:
            raise BotError("不知道哪里有精灵中心")
        self.heal_town = town
        center = next((m for m in (f"{town}_center", f"{town}_gate", town) if m in world.MAPS), f"{town}_center")
        self._healing = True
        try:
            try:
                self.travel(center)
            except BotError as e:
                # 走不回去(例如冲浪精灵倒下被困在水路上):像玩家一样用飞翔
                if not self.fly(town) and not self.escape_rope():
                    raise
                self.log(f"  走不回 {town}({e}),用飞翔/离洞绳")
                self.travel(center)
        finally:
            self._healing = False
        ow, m = self.ow, self.ow.map
        targets = [(x, y) for y in range(m.h) for x in range(m.w)
                   if m.tile(x, y) == "N" and not m.solid(x, y + 1)]
        self.must_navigate(lambda X, Y, S: any(X == x and Y == y + 1 for x, y in targets), "护士柜台")
        self.tap(KEY_OF["up"])
        self.tap(A)
        self.settle()
        hp = sum(m_.hp for m_ in self.game.party)
        self.stats["heals"] += 1
        self.log(f"  在 {town} 恢复(HP {hp})")
        self.leave_center()

    def leave_center(self):
        ow, m = self.ow, self.ow.map
        self.navigate(lambda X, Y, S: m.tile(X, Y) == "D", "中心大门")
        self.settle()

    def shop_for(self, town):
        """城镇对应的商店:(地图, 柜台行)。联盟的商店在 league_gate 的左侧柜台。"""
        if f"{town}_mart" in world.MAPS:
            return (f"{town}_mart", None)
        if town == "league":
            return ("league_gate", 5)
        return None

    def restock(self, town, balls=0):
        """按需补货:药补到 8 个(商店里有好药就买好药),球少于 balls 就补,喷雾/离洞绳/活力块备着。"""
        shop = self.shop_for(town)
        if not shop:
            return
        from src.world.interiors import SHOP_STOCK
        stock = dict(SHOP_STOCK["league" if town == "league" else "late"])
        items = []
        if self.game.badge_count() >= 3:
            if not self.game.has_item("离洞绳"):
                items.append(("离洞绳", 2))
            if sum(self.game.bag.get(n, 0) for n in REPELS) < 2:
                items.append(("白银喷雾", 2))
        potions = sum(self.game.bag.get(n, 0) for n in HEALS)
        if potions < (12 if self.game.badge_count() >= 8 else 8):
            for name in ("全复药", "厉害伤药", "好伤药"):
                if name in stock and self.game.money > stock[name] * 4:
                    items.append((name, 8 - potions))
                    break
        if self.game.badge_count() >= 7 and sum(self.game.bag.get(n, 0) for n in ("活力块", "活力碎片")) < 2 \
                and "活力块" in stock:
            items.append(("活力块", 2))
        if balls:
            have = sum(self.game.bag.get(n, 0) for n in BALLS)
            if have < balls:
                items.append(("高级球" if self.game.badge_count() >= 4 else "精灵球", balls - have))
        items = [(n, q) for n, q in items if n in stock or n in ("精灵球", "伤药", "好伤药", "超级球")]
        if items:
            try:
                self.buy(town, items, shop=shop)
            except BotError as e:
                self.log(f"  补货失败: {e}")

    def buy(self, town, items, shop=None, reserve=0):
        """shop=(地图, 柜台行) 用于多柜台商店;reserve=买完后至少要剩下的钱。"""
        self.travel(shop[0] if shop else f"{town}_mart")
        ow, m = self.ow, self.ow.map
        targets = [(x, y) for y in range(m.h) for x in range(m.w)
                   if m.tile(x, y) == "M" and not m.solid(x, y + 1) and (not shop or shop[1] is None or y == shop[1])]
        self.must_navigate(lambda X, Y, S: any(X == x and Y == y + 1 for x, y in targets), "商店柜台")
        self.tap(KEY_OF["up"])
        self.tap(A)
        for _ in range(60):                                   # 欢迎语 → 商店界面
            self.tick(1)
            if ow.state == "shop":
                break
            if ow.state == "dialog" and ow.textbox.wait_key:
                self.ui_key(A)
        if ow.state != "shop":
            raise BotError(f"{town} 的商店柜台没有打开商店")
        ss = ow.shop_screen
        names = [n for n, _p in ss.stock]
        for name, qty in items:
            price = dict(ss.stock).get(name)
            if name not in names or not price:
                continue
            qty = min(qty, (self.game.money - reserve) // price)    # 钱不够就买得起几个买几个
            if qty < 1:
                continue
            delta = (names.index(name) - ss.idx) % len(names)
            for _ in range(delta):
                self.ui_key(DOWN)
            while ss.qty < qty:
                self.ui_key(K.RIGHT[0])
            while ss.qty > qty:
                self.ui_key(K.LEFT[0])
            self.ui_key(A)
        self.ui_key(K.B[0])
        self.settle()
        self.stats["buys"] += 1
        self.log(f"  在 {town} 购物,余额 ¥{self.game.money}")

    def teach_hm(self, num, species=None):
        """教秘传招式;species 可以是候选列表(如 ["海兔兽", "大尾狸"]),依次尝试队伍里能学的。"""
        item = data.item_by_tm(num, hm=True)
        for sp in (species if isinstance(species, (list, tuple)) else [species]):
            try:
                self.teach_item(item, sp)
                return
            except BotError:
                continue
        self.log(f"  没有精灵能学 {data.ITEMS[item]['move']},跳过")

    def teach_tm(self, num, species):
        """把招式学习器 num 教给指定精灵(按进化链匹配,未进化的也算;已会/学不了则跳过)。"""
        item = data.item_by_tm(num)
        if not self.game.has_item(item):
            return
        if not any(family(m.species) == family(species) for m in self.game.party):
            return
        try:
            self.teach_item(item, species)
        except BotError as e:
            self.log(f"  {e}")

    def tm_shopping(self):
        """帷幕百货学习器柜台:按 TM_PLAN 买得起的学习器并教给队伍。"""
        items = [(data.item_by_tm(n), 1) for n, _sp in TM_PLAN
                 if not self.game.has_item(data.item_by_tm(n))
                 and any(family(m.species) == family(_sp) and not m.knows(data.ITEMS[data.item_by_tm(n)]["move"])
                         for m in self.game.party)]
        if items:
            try:
                self.buy("veilstone", items, shop=("veilstone_dept", 5), reserve=3000)
            except BotError as e:
                self.log(f"  买学习器失败: {e}")
        for n, sp in TM_PLAN:
            self.teach_tm(n, sp)

    def teach_item(self, item, species=None):
        game, ow = self.game, self.ow
        if not game.has_item(item):
            raise BotError(f"背包里没有 {item}")
        md = data.ITEMS[item]
        move = md["move"]
        cands = [i for i, m in enumerate(game.party) if not m.knows(move)       # 学习器对倒下的精灵也能用
                 and (species is None or m.species == species or family(m.species) == family(species))
                 and ((md["num"] in data.SPECIES[m.species]["hms"]) if md["hm"]
                      else (md["num"] in data.SPECIES[m.species]["tms"]))]
        if not cands:
            raise BotError(f"没有精灵能学 {move}")
        # 优先非初始精灵(初始精灵保留招式位),再按等级低优先
        cands.sort(key=lambda i: (i == 0, game.party[i].level))
        pi = cands[0]
        ow.bag_from = "field"
        ow.bag_screen = BagScreen(game, "menu")
        ow.state = "bag"
        idx = ow.bag_screen.items.index(item)
        for _ in range(idx):
            self.ui_key(DOWN)
        self.ui_key(A)                                # 选道具 → 进入选精灵
        if ow.state != "party":
            self.settle()
            return
        self.party_select(pi)                         # 选精灵 → 学习/询问替换
        if ow.state == "learn":
            pick = self.learn_pick(ow.learn_screen)
            for _ in range(pick if pick is not None else len(ow.learn_screen.mon.moves)):
                self.ui_key(DOWN)
            self.ui_key(A)
        self.settle()
        self.log(f"  {game.party[pi].species} 学会了 {move}")

    def hunt(self, species_list, where, max_battles=40):
        """在草丛里来回走,直到抓到指定精灵(或次数用完)。"""
        self.travel(where)
        battles0 = self.stats["battles"]
        while not any(family(m.species) in {family(sp) for sp in species_list} for m in self.game.party) \
                and self.stats["battles"] - battles0 < max_battles:
            self.grind_step()
        got = [m.species for m in self.game.party if m.species in species_list]
        self.log(f"  捕捉 {species_list} → {got or '没有抓到'}")

    def encounter_tile(self, x, y):
        """会触发野生对战(且可来回走)的格子:高草丛,或洞窟地面。"""
        t = self.ow.map.tile(x, y)
        return t == "," or (t == "c" and self.ow.map.cave and self.ow.map.enc)

    def town(self):
        """最近去过的精灵中心所在城镇(读档后从重生点推断)。"""
        if self.heal_town:
            return self.heal_town
        r = self.game.respawn
        if not r:
            return None
        mid = r[0]
        if mid == "league_gate":
            self.heal_town = "league"
        elif mid.endswith("_center"):
            self.heal_town = mid[:-7]
        return self.heal_town

    def hm_user_down(self):
        """有倒下的精灵会秘传招式(冲浪/怪力等),导致地形过不去。"""
        return any(m.hp <= 0 and any(mv.name in HM_MOVES for mv in m.moves) for m in self.game.party)

    def use_repel(self):
        """长途赶路前用喷雾(队伍弱的时候不被野生精灵耗死)。"""
        game, ow = self.game, self.ow
        item = next((n for n in REPELS if game.has_item(n)), None)
        if not item or game.repel > 40 or ow.state != "field":
            return False
        ow.bag_from = "field"
        ow.bag_screen = BagScreen(game, "menu")
        ow.state = "bag"
        for _ in range(ow.bag_screen.items.index(item)):
            self.ui_key(DOWN)
        self.ui_key(A)
        self.settle()
        self.stats["repels"] += 1
        self.log(f"  使用了 {item}")
        return True

    def escape_rope(self):
        """用离洞绳回到最近的精灵中心(被困在水路/洞窟深处时)。"""
        game, ow = self.game, self.ow
        if not game.has_item("离洞绳") or ow.state != "field" or not game.respawn:
            return False
        ow.bag_from = "field"
        ow.bag_screen = BagScreen(game, "menu")
        ow.state = "bag"
        for _ in range(ow.bag_screen.items.index("离洞绳")):
            self.ui_key(DOWN)
        self.ui_key(A)
        self.settle()
        self.log(f"  用离洞绳回到了 {ow.map_id}")
        return ow.map_id != "r223"

    def revive_item(self):
        """有复苏道具就给倒下的秘传招式使用者用,返回是否用了。"""
        game, ow = self.game, self.ow
        down = [i for i, m in enumerate(game.party) if m.hp <= 0 and any(mv.name in HM_MOVES for mv in m.moves)]
        item = next((n for n in ("活力块", "活力碎片") if game.has_item(n)), None)
        if not down or not item:
            return False
        ow.bag_from = "field"
        ow.bag_screen = BagScreen(game, "menu")
        ow.state = "bag"
        for _ in range(ow.bag_screen.items.index(item)):
            self.ui_key(DOWN)
        self.ui_key(A)
        if ow.state == "party":
            start = next((i for i, m in enumerate(game.party) if m.hp > 0), 0)
            # 复苏道具的目标是倒下的精灵:PartyScreen 光标从第一只活着的开始,逐格移到目标
            idx = down[0]
            for _ in range((idx - start) % len(game.party)):
                self.ui_key(DOWN)
            self.ui_key(A)
        self.settle()
        self.log(f"  用 {item} 复苏了 {game.party[down[0]].species}")
        return game.party[down[0]].hp > 0

    def sole_hm_user(self, mon):
        """该精灵是队伍里唯一会某个秘传招式的(打倒了路就走不了)。"""
        return any(mv.name in HM_MOVES and not any(o is not mon and o.hp > 0 and o.knows(mv.name)
                                                   for o in self.game.party) for mv in mon.moves)

    def party_hp_ratio(self):
        return sum(m.hp for m in self.game.party) / max(1, sum(m.max_hp for m in self.game.party))

    def grind_step(self):
        ow, m = self.ow, self.ow.map
        # 血量低又没药:回最近的精灵中心恢复(而不是硬撑到眼前发黑)
        if self.party_hp_ratio() < 0.3 and not any(self.game.has_item(n) for n in HEALS) and self.nearest_center():
            self.log("  队伍体力不支且没有药,回中心恢复")
            self.heal()
            return
        self.must_navigate(lambda X, Y, S: self.encounter_tile(X, Y) and
                           any(self.encounter_tile(X + dx, Y + dy) and not m.solid(X + dx, Y + dy)
                               and (X + dx, Y + dy) not in m.warps for dx, dy in DIRS.values()), "草丛")
        spot = (ow.px, ow.py)
        for dx, dy in DIRS.values():
            nx, ny = spot[0] + dx, spot[1] + dy
            if self.encounter_tile(nx, ny) and not m.solid(nx, ny) and (nx, ny) not in m.warps:
                self.do_action(("move", {(-1, 0): "left", (1, 0): "right", (0, -1): "up", (0, 1): "down"}[(dx, dy)]))
                break
        self.settle()

    def team_level(self):
        """主力平均等级(不算只会秘传招式的工具精灵)。"""
        main = [m for m in self.game.party if not all(mv.name in HM_MOVES for mv in m.moves)]
        return sum(m.level for m in main) / max(1, len(main))

    def grind(self, level, where=None, max_battles=400, label=""):
        """在草丛来回走刷野生精灵,直到主力平均等级 ≥ level。"""
        if where:
            self.travel(where)
        battles0 = self.stats["battles"]
        while self.team_level() < level and self.stats["battles"] - battles0 < max_battles:
            m = self.ow.map
            if not any(self.encounter_tile(x, y) for y in range(m.h) for x in range(m.w)):
                raise BotError(f"{m.id} 没有草丛/洞窟地面,无法练级")
            try:
                self.grind_step()
            except BotError:
                if self.ow.map_id != m.id:
                    self.log("  练级时被打回中心,回去继续")
                    self.travel(m.id)
                else:
                    raise
            if self.ow.map_id != m.id:
                self.travel(m.id)
        lv = "/".join(f"{mm.species}{mm.level}" for mm in self.game.party)
        self.log(f"  练级{label}:目标 {level} → {lv}")
        if self.team_level() < level:
            self.log("  (未达到目标等级,继续推进)")

    # ================================================================ 流程
    def choose_starter(self, species):
        idx = data.STARTERS.index(species)
        ow = self.ow
        bx = (4, 5, 6)[idx]
        self.must_navigate(lambda X, Y, S: X == bx and Y == 4, "研究所桌上的精灵球")
        self.tap(KEY_OF["up"])
        self.tap(A)
        self.settle()
        assert self.game.party and self.game.party[0].species == species, "选初始精灵失败"
        self.log(f"  获得初始精灵 {species}")

    def fly(self, town):
        ow = self.ow
        if not self.game.knowable_hm("飞翔") or not self.game.flags.get(f"visited_{town}"):
            return False
        ow._open_menu()
        idx = ow.menu_opts.index("飞翔")
        for _ in range(idx):
            self.ui_key(DOWN)
        self.ui_key(A)                                # 打开飞翔列表
        if ow.state != "fly":
            ow.state = "field"
            return False
        names = [o[1] for o in ow.fly_screen.opts]
        if town not in names:
            self.ui_key(K.B[0])
            ow.state = "field"
            return False
        for _ in range(names.index(town)):
            self.ui_key(DOWN)
        self.ui_key(A)
        self.settle()
        return True

    def summary(self):
        g = self.game
        lv = "/".join(f"{m.species}Lv{m.level}" for m in g.party)
        return (f"徽章 {g.badge_count()}/8  队伍 {lv}  金钱 ¥{g.money}  "
                f"战斗 {self.stats['battles']}(胜 {self.stats['result_win']})  恢复 {self.stats['heals']}  "
                f"ticks {self.ticks}")


# ================================================================ 攻略步骤
def build_plan():
    P = []

    def step(name, fn, retries=2, heal_town=None, grind=None, cap=4):
        P.append((name, fn, retries, heal_town, grind, cap))

    step("离开自宅前往真砂镇", lambda b: b.travel("sandgem"))
    step("研究所领取小火焰猴", lambda b: (b.travel("sandgem_lab"), b.choose_starter("小火焰猴")))
    step("前往祝庆市", lambda b: b.travel("jubilife"))
    step("祝庆市:恢复+买药", lambda b: (b.heal("jubilife"), b.restock("jubilife", balls=10), b.buy("jubilife", [("精灵球", 10), ("伤药", 5)])))
    step("202 道路:抓大牙狸和小猫怪", lambda b: (b.hunt(["大牙狸"], "r202", 30), b.hunt(["小猫怪", "姆克儿"], "r203", 30)))
    step("203 道路:劲敌帕尔", lambda b: (b.travel("r203"), b.grind(12, "r203", max_battles=60), b.talk("rival_203", expect="beat_rival1")),
         retries=2, heal_town="jubilife", grind=(14, "r203"))
    step("前往黑金市", lambda b: b.travel("oreburgh"))
    step("黑金市:恢复+补药", lambda b: (b.heal("oreburgh"), b.restock("oreburgh", balls=10)))
    step("黑金炭坑:拿碎岩、叫瓢太回道馆", lambda b: (b.travel("oreburgh_mine_b1"), b.talk("mine_hiker_hm"),
                                   b.teach_hm(6), b.talk("roark_mine")))
    step("练级到 14", lambda b: b.grind(14, "oreburgh_mine_b1", max_battles=60))
    step("挑战黑金道馆", lambda b: (b.heal("oreburgh"), b.travel("oreburgh_gym"), b.talk("gym_roark", expect="beat_gym1")),
         retries=2, heal_town="oreburgh", grind=(16, "oreburgh_mine_b1"))
    step("博士助手的学习装置", lambda b: (b.travel("oreburgh_house1"), b.talk("aide_exp_share")))
    step("回祝庆市", lambda b: b.travel("jubilife"))
    step("204 道路:抓含羞苞", lambda b: (b.hunt(["含羞苞"], "r204s", 30),))
    step("荒芜小道 → 花苑镇", lambda b: (b.travel("floaroma"), b.heal("floaroma")))
    step("205 道路:抓无壳海兔,练到 17", lambda b: (b.hunt(["无壳海兔", "泳圈鼬"], "r205s", 30), b.grind(17, "r205s", max_battles=80)))
    step("谷间发电厂:银河队", lambda b: (b.travel("valley_windworks"), b.talk("galactic_ww1", optional=True),
                              b.talk("galactic_ww2", optional=True), b.talk("mars_windworks", expect="windworks_clear")), retries=2,
         heal_town="floaroma", grind=(19, "r205s"))
    step("百代森林:竹兰给居合劈", lambda b: (b.travel("eterna_forest"), b.talk("cynthia_forest"), b.teach_hm(1),
                                b.grind(21, "eterna_forest", max_battles=60)))
    step("百代市:恢复+补药", lambda b: (b.travel("eterna"), b.heal("eterna"), b.restock("eterna", balls=10)))
    step("百代市:劲敌帕尔", lambda b: b.talk("rival_eterna", expect="beat_rival2"), retries=2,
         heal_town="eterna", grind=(23, "eterna_forest"))
    step("挑战百代道馆", lambda b: (b.heal("eterna"), b.travel("eterna_gym"), b.interact(14, 5), b.talk("gym_gardenia", expect="beat_gym2")),
         retries=2, heal_town="eterna", grind=(24, "eterna_forest"))
    step("银河队百代基地", lambda b: (b.travel("galactic_eterna"), b.talk("galactic_et_1", optional=True), b.talk("galactic_et_2", optional=True),
                            b.talk("jupiter_eterna", expect="eterna_galactic_clear")), retries=2, heal_town="eterna", grind=(24, "eterna_forest"))
    step("211/天冠山/208 → 家缘市", lambda b: b.travel("hearthome"))
    step("家缘市:恢复+补药", lambda b: (b.heal("hearthome"), b.restock("hearthome", balls=10)))
    step("家缘市:劲敌帕尔", lambda b: b.talk("rival_hearthome", expect="beat_rival3"), retries=2, heal_town="hearthome", grind=(26, "r208"))
    step("209 道路 → 丧失塔拿怪力", lambda b: (b.travel("lost_tower_top"), b.take_item(9, 2),
                                         b.teach_hm(4, ["海兔兽", "烈焰猴"])))
    step("随意镇", lambda b: b.travel("solaceon"))
    step("前往帷幕市", lambda b: b.travel("veilstone"))
    step("帷幕市:恢复+买药", lambda b: (b.heal("veilstone"), b.restock("veilstone", balls=10), b.buy("veilstone", [("超级球", 10), ("好伤药", 8)])))
    step("练级到 29", lambda b: b.grind(29, "r215", max_battles=200))
    step("挑战帷幕道馆", lambda b: (b.heal("veilstone"), b.travel("veilstone_gym"), b.talk("gym_maylene", expect="beat_gym3")),
         retries=2, heal_town="veilstone", grind=(31, "r215"))
    step("银河队仓库:拿飞翔", lambda b: (b.travel("veilstone_warehouse"), b.talk("galactic_wh_1", optional=True),
                            b.talk("galactic_wh_2", expect="warehouse_clear", optional=True), b.take_item(4, 1),
                            b.teach_hm(2), b.tm_shopping()), retries=2, heal_town="veilstone", grind=(32, "r215"))
    step("前往湿原市", lambda b: b.travel("pastoria"))
    step("挑战湿原道馆", lambda b: (b.heal("pastoria"), b.travel("pastoria_gym"), b.interact(2, 9),
                          b.interact(3, 5), b.talk("gym_wake", expect="beat_gym4")), retries=2, heal_town="pastoria", grind=(31, "r212e"))
    step("劲敌帕尔(湿原)", lambda b: b.talk("rival_pastoria", expect="beat_rival4"), retries=2, heal_town="pastoria", grind=(35, "r212e"))
    step("前往家缘市", lambda b: b.travel("hearthome"))
    step("挑战家缘道馆", lambda b: (b.heal("hearthome"), b.travel("hearthome_gym"), b.talk("quiz_door_2", [1]),
                          b.talk("quiz_door_1", [0]), b.talk("gym_fantina", expect="beat_gym5"),
                          b.teach_tm(65, "烈焰猴")), retries=2, heal_town="hearthome", grind=(36, "r212n"))
    step("前往神和镇", lambda b: b.travel("celestic"))
    step("神和镇:赤日、长老给冲浪", lambda b: (b.talk("cyrus_celestic", expect="celestic_cyrus"), b.travel("celestic_elder"),
                                b.talk("celestic_elder"), b.teach_hm(3)), retries=2, heal_town="celestic", grind=(40, "r210w"))
    step("经天冠山前往水脉市", lambda b: b.travel("canalave"))
    step("水脉市:恢复+买药", lambda b: (b.heal("canalave"), b.restock("canalave", balls=10), b.buy("canalave", [("高级球", 10), ("厉害伤药", 6)])))
    step("挑战水脉道馆", lambda b: (b.heal("canalave"), b.travel("canalave_gym"), b.talk("gym_byron", expect="beat_gym6")),
         retries=2, heal_town="canalave", grind=(39, "iron_island"))
    step("经天冠山回神和镇", lambda b: b.travel("celestic"))
    step("前往雪峰市", lambda b: b.travel("snowpoint"))
    step("雪峰市:恢复+买药", lambda b: (b.heal("snowpoint"), b.restock("snowpoint", balls=10), b.buy("snowpoint", [("高级球", 10), ("厉害伤药", 8), ("活力块", 2)])))
    step("练级到 41", lambda b: b.grind(41, "r217", max_battles=250))
    step("挑战雪峰道馆", lambda b: (b.heal("snowpoint"), b.travel("snowpoint_gym"), b.talk("gym_candice", expect="beat_gym7")),
         retries=2, heal_town="snowpoint", grind=(43, "r217"))
    step("前往帷幕市", lambda b: (b.fly("veilstone") or b.travel("veilstone"), b.tm_shopping()))
    step("银河队总部:镇星", lambda b: (b.talk("galactic_hq_door", optional=True), b.travel("galactic_veilstone"), b.talk("galactic_hq_1", optional=True),
                          b.talk("galactic_hq_2", optional=True), b.talk("galactic_hq_3", optional=True), b.talk("saturn_hq", expect="hq_clear")),
         retries=2, heal_town="veilstone", grind=(44, "r215"))
    step("枪之柱:赤日与神兽", lambda b: (b.travel("spear_pillar"), b.talk("galactic_spear_1", optional=True),
                          b.talk("galactic_spear_2", optional=True), b.talk("cyrus_spear", expect="spear_cyrus", optional=True),
                          b.talk("spear_legendary", expect="spear_clear")), retries=3,
         heal_town="celestic", grind=(48, "coronet_peak"))
    step("前往滨海市", lambda b: b.travel("sunyshore"))
    step("滨海市:拿攀瀑、恢复、买药", lambda b: (b.take_item(22, 1), b.teach_hm(7, ["海兔兽", "大尾狸"]), b.heal("sunyshore"),
                                  b.buy("sunyshore", [("厉害伤药", 8), ("全复药", 4), ("活力块", 2), ("离洞绳", 2),
                                                   ("白银喷雾", 3)])))
    step("练级到 48", lambda b: b.grind(48, "r222", max_battles=300))
    step("挑战滨海道馆", lambda b: (b.heal("sunyshore"), b.travel("sunyshore_gym"), b.interact(2, 9),
                         b.interact(2, 6), b.talk("gym_volkner", expect="beat_gym8")), retries=2, heal_town="sunyshore", grind=(50, "r222"))
    step("223 水路 → 224 道路", lambda b: b.travel("r224"))
    step("224 道路补伙伴(毒蔷薇/浮潜鼬)", lambda b: b.hunt(["毒蔷薇", "浮潜鼬"], "r224", 60) if len(b.game.party) < 6 else None)
    step("224 → 冠军之路", lambda b: b.travel("victory_road_1"))
    step("冠军之路补伙伴(恰雷姆/大钢蛇)", lambda b: b.hunt(["恰雷姆", "大钢蛇"], "victory_road_1", 60) if len(b.game.party) < 6 else None)
    step("冠军之路练到 54", lambda b: b.grind(54, "victory_road_1", max_battles=400))
    step("冠军之路:劲敌帕尔", lambda b: (b.travel("victory_road_peak"), b.talk("rival_victory", expect="beat_rival5")),
         retries=3, heal_town="sunyshore", grind=(54, "victory_road_1"))
    step("联盟前练级到 62", lambda b: b.grind(62, "victory_road_1", max_battles=900))
    step("联盟大门恢复+补给", lambda b: (b.heal("league"),
                                 b.buy("league", [("厉害伤药", 10), ("全复药", 6), ("活力块", 2), ("离洞绳", 2), ("黄金喷雾", 2)],
                                       shop=("league_gate", 5))))
    for who in ("e4_aaron", "e4_bertha", "e4_flint", "e4_lucian"):
        step(f"四天王 {who}", lambda b, w=who: (b.travel(w), b.talk(w, expect=f"beat_{w[3:]}")), retries=5,
             heal_town="league", grind=(60, "victory_road_1"), cap=10)
    step("冠军竹兰", lambda b: (b.travel("champion_room"), b.talk("champion_cynthia", expect="champion")), retries=8,
         heal_town="league", grind=(64, "victory_road_1"), cap=12)
    return P


def main():
    import faulthandler
    faulthandler.dump_traceback_later(240, repeat=True)     # 看门狗:卡住时把调用栈打进日志
    draw = "--draw" in sys.argv
    stop = int(sys.argv[sys.argv.index("--stop") + 1]) if "--stop" in sys.argv else None
    bot = Bot(draw=draw)
    plan = build_plan()
    resume = int(sys.argv[sys.argv.index("--resume") + 1]) if "--resume" in sys.argv else 0
    if resume:
        bot.game.load()
        bot.ow = bot.game.scenes[0]
        plan = plan[resume - 1:]
        bot.log(f"(从存档继续:第 {resume} 步起)")
    if stop:
        plan = plan[:stop]
    for i, (name, fn, retries, heal_town, grind, cap) in enumerate(plan):
        start = resume or 1
        bot.log(f"[{i + start}/{len(plan) + start - 1}] {name}  —  {bot.summary()}")
        for attempt in range(retries + 1):
            try:
                fn(bot)
                bot.game.save()
                break
            except (BotError, AssertionError) as e:
                bot.log(f"  ✗ 第 {attempt + 1} 次失败: {e}")
                bot.log(traceback.format_exc().strip().splitlines()[-1])
                try:
                    bot.settle(limit=2000)
                except BotError:
                    pass
                # 回血;如果是打输/等级不够,先练两级再来
                town = heal_town
                if town and bot.ow.map_id != f"{town}_center":
                    try:
                        bot.heal(town)
                    except BotError as e2:
                        bot.log(f"  无法回到 {town} 恢复: {e2}")
                else:
                    try:
                        bot.leave_center()
                    except BotError:
                        pass
                if attempt == retries:
                    bot.log("!!! 无法继续,流程中止")
                    bot.log(bot.summary())
                    bot.game.save()
                    return 1
                try:
                    bot.restock(town or bot.town() or "jubilife")
                except BotError as e2:
                    bot.log(f"  补货失败: {e2}")
                if grind:
                    lv, where = grind
                    try:
                        bot.grind(min(lv + 2 * (attempt + 1), lv + cap), where, max_battles=120)
                    except BotError as e2:
                        bot.log(f"  练级失败: {e2}")
        if bot.game.flags.get("champion"):
            break
    bot.log("流程结束: " + bot.summary())
    bot.log("徽章: " + ", ".join(n for f, n, *_ in data.BADGES if bot.game.flags.get(f)))
    bot.game.save()
    return 0 if bot.game.flags.get("champion") else 2


if __name__ == "__main__":
    sys.exit(main())
