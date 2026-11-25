"""战斗场景:第四世代式回合制,协程驱动流程。

yield 协议: ("msg",t) ("anim",kind,dur,extra) ("menu",) ("movesel",) ("bag",)
            ("party",mode) ("learnmove",mon,move)
状态:能力等级/天气/光墙反射壁/神秘守护/撒菱隐形岩毒菱/寄生种子/混乱/畏缩/守住/蓄力/树果。
"""
import math
import random

import pygame

from . import settings as S
from . import data
from . import keys as K
from .mon import Mon, Move, accuracy_multiplier, stage_multiplier
from .ui import (TextBox, PartyScreen, BagScreen, LearnMoveScreen, panel, draw_text, hp_bar, exp_bar,
                 down_arrow, cursor_arrow)

MENU_OPTS = ("战斗", "背包", "精灵", "逃跑")
STAT_KEYS = ("atk", "def", "spa", "spd", "spe", "acc", "eva")
SUPPORT_BERRIES = ("欧兰果", "文柚果", "芒果果", "樟樟果", "木子果")   # 回复/解睡/解状态的树果

# 抛球动画分段时长(秒)
BALL_THROW_T = 0.55
BALL_FLASH_T = 0.30
BALL_SHAKE_T = 0.50

WEATHER_CN = {"sand": "沙暴", "sun": "大晴天", "rain": "求雨", "hail": "冰雹"}


def _new_side():
    return {"reflect": 0, "light": 0, "safeguard": 0, "stealth": False, "spikes": 0, "tspikes": 0}


def _new_volatile():
    return {"confuse": 0, "leech": False, "ingrain": False, "aquaring": False, "flinch": False,
            "protected": False, "protect_streak": 0, "recharge": False, "damaged": False,
            "focus_broken": False, "acted": False}


def weight_power(weight_kg):
    """踢倒/打草结:按体重分档。"""
    for limit, power in ((10, 20), (25, 40), (50, 60), (100, 80), (200, 100)):
        if weight_kg < limit:
            return power
    return 120


class Battle:
    def __init__(self, game, enemy_team, trainer_name=None, callback=None, can_run=True,
                 ai_level=1, trainer_key=None, display=None, context=None, safari=False, safari_balls=0):
        self.game = game
        self.safari = safari
        self.safari_balls = safari_balls
        self.can_catch = safari or trainer_name is None
        self.trainer_key = trainer_key
        tdata = data.TRAINERS.get(trainer_key) if trainer_key is not None else None
        if tdata:
            self.enemies = [Mon(sp, lv, moves=mv, held=h) for sp, lv, mv, h in tdata["party"]]
            self.trainer = display or f"{tdata['cls']} {tdata['name']}".strip()
            self.trainer_items = list(tdata["items"])
            self.prize_rate = tdata["prize"]
        else:
            self.enemies = enemy_team or []
            self.trainer = trainer_name
            self.trainer_items = []
            self.prize_rate = 40
        self.can_run = can_run
        self.ai_level = ai_level
        self.turns = 0
        self.callback = callback
        self.context = context or {}             # {"cave": True, "surf": True, "fishing": True}
        self.p_idx = next((i for i, m in enumerate(game.party) if m.hp > 0), 0)
        self.stages = {"ally": {}, "foe": {}}
        self.sides = {"ally": _new_side(), "foe": _new_side()}
        self.vol = {"ally": _new_volatile(), "foe": _new_volatile()}
        self.crit_stage = {"ally": 1, "foe": 1}
        self.weather = None
        self.weather_turns = 0
        self.run_attempts = 0
        self.pending_evo = []                    # [(mon, target)] 战斗结束后结算
        self.textbox = TextBox()
        self.phase = "anim"
        self.anim = None                         # (kind, t, dur, extra)
        self.menu_idx = 0
        self.move_idx = 0
        self.party_screen = None
        self.bag_screen = None
        self.learn_screen = None
        self.item_pending = None
        self.done = False
        self.result = None
        self.auto = False                        # 测试模式:消息自动推进
        self.intro_t = 0.6
        self.disp = {"ally": None, "foe": None}
        self._thrown_item = None
        self._flow = self._main_flow()
        self._started = False
        self._advance(None)

    # -------------------------------------------------- 常用引用
    @property
    def ally(self):
        return self.game.party[self.p_idx]

    @property
    def foe(self):
        return self.enemies[self.e_idx] if hasattr(self, "e_idx") else self.enemies[0]

    def mon(self, side):
        return self.ally if side == "ally" else self.foe

    def other(self, side):
        return "foe" if side == "ally" else "ally"

    @property
    def e_idx(self):
        return getattr(self, "_e_idx", 0)

    @e_idx.setter
    def e_idx(self, v):
        self._e_idx = v

    # -------------------------------------------------- 流程驱动
    def _advance(self, value):
        try:
            item = self._flow.send(value) if self._started else next(self._flow)
        except StopIteration:
            self._finish()
            return
        self._started = True
        kind = item[0]
        if kind == "msg":
            self.textbox.show(item[1])
            self.phase = "msg"
        elif kind == "anim":
            self.anim = [item[1], 0.0, item[2], item[3] if len(item) > 3 else None]
            self.phase = "anim"
        elif kind == "menu":
            self.menu_idx = 0
            self.phase = "menu"
        elif kind == "movesel":
            self.move_idx = 0
            self.phase = "movesel"
        elif kind == "bag":
            self.bag_screen = BagScreen(self.game, "battle")
            self.phase = "bag"
        elif kind == "party":
            mode = item[1] if len(item) > 1 else "battle"
            self.party_screen = PartyScreen(self.game, mode, current_idx=self.p_idx)
            self.phase = "party"
        elif kind == "learnmove":
            self.learn_screen = LearnMoveScreen(item[1], item[2])
            self.phase = "learnmove"

    def _finish(self):
        self.done = True
        self.game.last_battle = self

    def _end_battle(self, result):
        self.result = result
        self._flow = iter(())

    # -------------------------------------------------- 主流程
    def _main_flow(self):
        self.e_idx = 0
        if self.trainer:
            yield ("msg", f"{self.trainer}想要和你对战!\n{self.trainer}派出了{self.foe.name}!")
        else:
            yield ("msg", f"野生的{self.foe.name}出现了!")
        if self.ally.hp <= 0:
            self.p_idx = next((i for i, m in enumerate(self.game.party) if m.hp > 0), 0)
        yield ("msg", f"去吧!{self.ally.name}!")
        yield from self._entry_effects("ally")
        while True:
            act = yield ("menu",)
            if self.safari and act in ("fight", "bag", "party"):
                if act == "fight":
                    yield from self._safari_throw()
                else:
                    yield ("msg", "在大湿地里只能投掷狩猎球!")
                if self.result:
                    return
                continue
            if act == "fight":
                r = yield ("movesel",)
                if r == "back":
                    continue
                idx = r[1]
                move = self.ally.moves[idx]
                if move.pp <= 0:
                    yield ("msg", "PP不够了!")
                    continue
                if self.vol["ally"]["recharge"]:
                    self.vol["ally"]["recharge"] = False
                    yield ("msg", f"{self.ally.name}正在蓄力……")
                    yield from self._turn([("foe", None)])
                else:
                    enemy_move = self._ai_pick_move()
                    if self._ai_wants_item():
                        yield from self._turn([("ally", move.name)], foe_item=True)
                    elif enemy_move is None:          # 对方蓄力
                        yield from self._turn([("ally", move.name)])
                    else:
                        player_first = self._order_first(move.name, enemy_move)
                        order = ([("ally", move.name), ("foe", enemy_move)] if player_first
                                 else [("foe", enemy_move), ("ally", move.name)])
                        yield from self._turn(order)
            elif act == "bag":
                item = yield ("bag",)
                if not item:
                    continue
                res = yield from self._use_item(item)
                if res == "used":
                    yield from self._turn([], foe_item=False, foe_free=True)
            elif act == "party":
                idx = yield ("party",)
                if idx is None:
                    continue
                yield from self._switch_to(idx)
                yield from self._turn([], foe_free=True)
            elif act == "run":
                yield from self._try_run()
            if self.result:
                return

    def _order_first(self, p_move, e_move):
        pp = data.MOVES[p_move].get("prio", 0)
        ep = data.MOVES[e_move].get("prio", 0)
        if pp != ep:
            return pp > ep
        ps, es = self.ally.effective_speed(), self.foe.effective_speed()
        if ps == es:
            return random.random() < 0.5
        return ps > es

    def _turn(self, order, foe_item=False, foe_free=False):
        """执行一回合。order 为 [(side, move|None)];foe_free=True 时对方额外行动一次(换人/道具后)。"""
        self.turns += 1
        for side in ("ally", "foe"):
            self.vol[side].update({"flinch": False, "protected": False, "damaged": False,
                                   "focus_broken": False, "acted": False})
        if foe_item:
            msgs, used = self._ai_turn()
            for t in msgs:
                yield ("msg", t)
            if used:
                order = [(s, m) for s, m in order if s == "ally"]
        for side, move_name in order:
            if self.result:
                return
            if move_name is None:
                continue                 # 该方本回合因蓄力等原因不行动
            yield from self._use_move(side, move_name)
            if self.result:
                return
            dead = [s for s in ("ally", "foe") if self.mon(s).hp <= 0]
            for s in dead:
                if not (yield from self._faint_flow(s)):
                    return
        if foe_free and not self.result:
            yield from self._use_move("foe", self._ai_pick_move())
            if not self.result and self.ally.hp <= 0:
                if not (yield from self._faint_flow("ally")):
                    return
            if not self.result and self.foe.hp <= 0:
                if not (yield from self._faint_flow("foe")):
                    return
        if self.result:
            return
        yield from self._end_of_turn()

    def _end_of_turn(self):
        # 天气
        if self.weather in ("sand", "hail"):
            for side in ("ally", "foe"):
                m = self.mon(side)
                immune = ("岩石" in m.types) if self.weather == "sand" else ("冰" in m.types)
                if m.hp > 0 and not immune:
                    m.hp = max(0, m.hp - max(1, m.max_hp // 16))
                    yield ("msg", f"{m.name}受到了{WEATHER_CN[self.weather]}的伤害!")
        if self.weather:
            self.weather_turns -= 1
            if self.weather_turns <= 0:
                yield ("msg", f"{WEATHER_CN[self.weather]}停止了。")
                self.weather = None
        # 异常状态
        for side in ("ally", "foe"):
            m = self.mon(side)
            if m.hp <= 0:
                continue
            if m.status in ("中毒", "剧毒"):
                if m.status == "剧毒":
                    m.toxic_counter += 1
                dmg = max(1, m.max_hp // 8) if m.status == "中毒" else max(1, m.max_hp * m.toxic_counter // 16)
                m.hp = max(0, m.hp - dmg)
                yield ("msg", f"{m.name}受到了毒的伤害!")
            elif m.status == "灼伤":
                m.hp = max(0, m.hp - max(1, m.max_hp // 8))
                yield ("msg", f"{m.name}受到了灼伤的伤害!")
        # 寄生种子 / 扎根 / 水流环
        for side in ("ally", "foe"):
            m, o = self.mon(side), self.mon(self.other(side))
            v = self.vol[side]
            if m.hp > 0 and v["leech"]:
                dmg = min(m.hp, max(1, m.max_hp // 8))
                m.hp -= dmg
                o.hp = min(o.max_hp, o.hp + dmg)
                yield ("msg", f"{m.name}被寄生种子吸取了养分!")
            if m.hp > 0 and v["ingrain"]:
                m.hp = min(m.max_hp, m.hp + max(1, m.max_hp // 8))
            if m.hp > 0 and v["aquaring"]:
                m.hp = min(m.max_hp, m.hp + max(1, m.max_hp // 16))
        for side in ("ally", "foe"):
            if self.mon(side).hp <= 0:
                if not (yield from self._faint_flow(side)):
                    return
        # 树果(训练家精灵)
        for side in ("ally", "foe"):
            m = self.mon(side)
            if m.held and m.hp > 0:
                yield from self._eat_berry(side, m)
        # 回合数倒计时
        for side in ("ally", "foe"):
            sd = self.sides[side]
            for key in ("reflect", "light", "safeguard"):
                if sd[key] > 0:
                    sd[key] -= 1
                    if sd[key] == 0:
                        name = {"reflect": "反射壁", "light": "光墙", "safeguard": "神秘守护"}[key]
                        yield ("msg", f"{self.mon(side).name}一方的{name}失效了。")
        for side in ("ally", "foe"):
            if self.vol[side]["confuse"] > 0:
                self.vol[side]["confuse"] -= 1
                if self.vol[side]["confuse"] == 0:
                    yield ("msg", f"{self.mon(side).name}解除了混乱!")
            if not self.vol[side]["protected"]:
                self.vol[side]["protect_streak"] = 0

    def _eat_berry(self, side, m):
        b = m.held
        heal = {"欧兰果": 10, "文柚果": m.max_hp // 4, "芒果果": m.max_hp // 2}.get(b)
        if heal and m.hp <= m.max_hp // 2 and m.hp < m.max_hp:
            m.held = None
            m.hp = min(m.max_hp, m.hp + heal)
            yield ("msg", f"{m.name}吃下了{b}恢复了体力!")
        elif b == "樟樟果" and m.status == "睡眠":
            m.held = None
            m.cure_status()
            yield ("msg", f"{m.name}吃下了樟樟果醒了过来!")
        elif b == "木子果" and m.status:
            m.held = None
            m.cure_status()
            yield ("msg", f"{m.name}吃下了木子果,恢复了状态!")

    # -------------------------------------------------- 入场(撒菱/隐形岩/毒菱)
    def _entry_effects(self, side):
        m = self.mon(side)
        v = self.vol[side]
        v.update({"leech": False, "ingrain": False, "aquaring": False, "confuse": 0, "recharge": False,
                  "flinch": False, "protected": False, "protect_streak": 0})
        self.stages[side] = {}
        self.crit_stage[side] = 1
        sd = self.sides[side]
        if sd["stealth"]:
            eff = data.type_multiplier("岩石", m.types)
            dmg = int(m.max_hp * 0.125 * eff)
            if dmg > 0:
                m.hp = max(0, m.hp - dmg)
                yield ("msg", f"隐形岩刺中了{m.name}!")
                yield ("anim", "hit_" + side, 0.3, "岩石")
        if sd["spikes"] and m.hp > 0:
            m.hp = max(0, m.hp - m.max_hp * (sd["spikes"] * 12) // 100)
            yield ("msg", f"{m.name}被撒菱刺中了!")
            yield ("anim", "hit_" + side, 0.3)
        if sd["tspikes"] and m.hp > 0 and not m.status_immune("中毒"):
            if "毒" in m.types:
                sd["tspikes"] = 0
                yield ("msg", f"{m.name}吸收了毒菱!")
            else:
                m.status = "剧毒" if sd["tspikes"] >= 2 else "中毒"
                m.toxic_counter = 0
                yield ("msg", f"{m.name}中了毒!")

    # -------------------------------------------------- 招式执行
    def _use_move(self, side, move_name):
        user, tside = self.mon(side), self.other(side)
        target = self.mon(tside)
        v, tv = self.vol[side], self.vol[tside]
        md = data.MOVES[move_name]
        fx = md.get("fx", {})
        v["acted"] = True
        # ---- 行动前检查
        if v["recharge"]:
            v["recharge"] = False
            yield ("msg", f"{user.name}正在蓄力……")
            return
        if v["flinch"]:
            yield ("msg", f"{user.name}因畏缩而无法行动!")
            return
        if user.status == "睡眠":
            user.sleep_turns -= 1
            if user.sleep_turns > 0:
                yield ("msg", f"{user.name}睡得正香……")
                return
            user.cure_status()
            yield ("msg", f"{user.name}醒过来了!")
        if user.status == "冻结":
            if random.random() < 0.2:
                user.cure_status()
                yield ("msg", f"{user.name}身上的冰融化了!")
            else:
                yield ("msg", f"{user.name}被冻结了,无法动弹!")
                return
        if user.status == "麻痹" and random.random() < 0.25:
            yield ("msg", f"{user.name}身体麻痹,无法动弹!")
            return
        if v["confuse"] > 0:
            if v["confuse"] > 1 and random.random() < 0.5:
                v["confuse"] -= 1
                yield ("msg", f"{user.name}精神混乱!")
                yield ("msg", "呜哇呜哇……\n自己把自己打伤了!")
                dmg = self._self_hit_damage(user)
                user.hp = max(0, user.hp - dmg)
                yield ("anim", "hit_" + side, 0.35)
                return
            v["confuse"] = 0
            yield ("msg", f"{user.name}解除了混乱!")
        mv = next((m for m in user.moves if m.name == move_name), None)
        if mv:
            mv.pp = max(0, mv.pp - 1)
        yield ("msg", f"{user.name}使用了{move_name}!")
        if fx.get("first_turn") and self.turns > 1:
            yield ("msg", "但是失败了……")
            return
        if fx.get("focus") and v["focus_broken"]:
            yield ("msg", f"{user.name}受到了攻击,\n真气拳失败了!")
            return

        # ---- 变化招式
        if md["cat"] == "变化":
            yield from self._status_move(side, md, fx)
            return

        # ---- 伤害招式
        if tv["protected"]:
            yield ("msg", f"{target.name}保护了自己!")
            return
        if fx.get("ohko"):
            if user.level <= target.level or random.random() * 100 >= 30 + user.level - target.level:
                yield ("msg", "但是没有命中……")
            else:
                target.hp = 0
                yield ("anim", "hit_" + tside, 0.45, md["type"])
                yield ("msg", "一击必杀!")
            return
        if not self._hits(user, target, side, tside, md):
            yield ("msg", "但是没有命中……")
            if fx.get("crash"):
                user.hp = max(0, user.hp - user.max_hp // 2)
                yield ("msg", f"{user.name}因冲击受到了反作用力伤害!")
            return
        if fx.get("dream") and target.status != "睡眠":
            yield ("msg", f"但是{target.name}没有睡着,\n招式没有效果……")
            return
        power_mod, fixed = self._power_modifiers(fx, user, target, tside, md)
        if fx.get("faint_user"):
            yield ("msg", f"{user.name}倒下了!")
        res = user.calc_damage(target, move_name, att_stages=self.stages[side],
                               dfn_stages=self.stages[tside], rng=random,
                               mods={"power": power_mod, "crit_stage": self.crit_stage[side],
                                     "weather": self.weather, "screen": self._screen_mod(tside, md)})
        if fixed is not None:
            dmg = fixed
            eff, crit = 1.0, False
        else:
            dmg, eff, crit = res["damage"], res["eff"], res["crit"]
        if res["eff"] == 0 and fixed is None:
            yield ("msg", f"对{target.name}没有效果……")
            if fx.get("faint_user"):
                user.hp = 0
            return
        hits = random.randint(*fx["multi"]) if isinstance(fx.get("multi"), list) else fx.get("multi", 1)
        total, landed = 0, 0
        for _ in range(hits):
            if target.hp <= 0:
                break
            d = max(1, int(dmg * random.uniform(0.85, 1.15))) if hits > 1 else dmg
            if fx.get("false_swipe") and d >= target.hp:
                d = target.hp - 1
            target.hp = max(0, target.hp - d)
            total += d
            landed += 1
        tv["damaged"] = True
        tv["focus_broken"] = True
        yield ("anim", "hit_" + tside, 0.45, md["type"])
        if fx.get("faint_user"):
            user.hp = 0
        if landed == 0:
            return
        if hits > 1:
            yield ("msg", f"连续命中了{landed}次!")
        if crit:
            yield ("msg", "击中要害!")
        if fx.get("false_swipe") and target.hp == 1:
            pass
        elif eff > 1:
            yield ("msg", "效果拔群!")
        elif eff < 1:
            yield ("msg", "收效甚微……")
        if fx.get("payday"):
            self.game.money += user.level * 5
            yield ("msg", "金币散落了一地!")
        if fx.get("super_fang"):
            pass
        if fx.get("salts") and target.status == "麻痹":
            target.cure_status()
            yield ("msg", f"{target.name}的麻痹被治好了!")
        if fx.get("wake_slap") and target.status == "睡眠":
            target.cure_status()
            yield ("msg", f"{target.name}醒过来了!")
        if target.status == "冻结" and md["type"] == "火" and target.hp > 0:
            target.cure_status()
            yield ("msg", f"{target.name}身上的冰被融化了!")
        if fx.get("recoil"):
            rc = max(1, int(total * fx["recoil"]))
            user.hp = max(0, user.hp - rc)
            yield ("msg", f"{user.name}受到了反作用力伤害!")
        if fx.get("drain") and total > 0 and user.hp > 0:
            user.hp = min(user.max_hp, user.hp + max(1, int(total * fx["drain"])))
            yield ("msg", f"{user.name}吸取了养分!")
        if fx.get("recharge"):
            v["recharge"] = True
        if fx.get("break_screen"):
            yield from self._break_screens(tside)
        if fx.get("spin"):
            yield from self._spin(side)
        if fx.get("tri") and target.hp > 0 and not target.status:
            st = random.choice(("麻痹", "灼伤", "冻结"))
            yield from self._apply_status(side, st, 100, announce=True)
        # 次要效果
        if target.hp > 0:
            yield from self._apply_effects(side, fx, target)
        if user.hp > 0:
            yield from self._self_effects(side, fx, user)

    def _self_hit_damage(self, user):
        level_term = 2 * user.level // 5 + 2
        a = user.battle_stat("atk", {})
        d = user.battle_stat("def", {})
        return max(1, int(int(int(int(level_term * 40) * a) / d) / 50) + 2)

    def _hits(self, user, target, side, tside, md):
        if md["acc"] is None:
            return True
        if self.weather == "rain" and md["type"] == "电" and md["power"] and md["power"] >= 100:
            return True                      # 求雨中打雷必中
        if self.weather == "hail" and md["type"] == "冰" and md["power"] and md["power"] >= 110:
            return True                      # 冰雹中暴风雪必中
        acc = md["acc"] * accuracy_multiplier({**self.stages[side], "eva": self.stages[tside].get("eva", 0)})
        return random.random() * 100 <= acc

    def _screen_mod(self, tside, md):
        sd = self.sides[tside]
        if md["cat"] == "物理" and sd["reflect"] > 0:
            return 0.5
        if md["cat"] == "特殊" and sd["light"] > 0:
            return 0.5
        return 1.0

    def _power_modifiers(self, fx, user, target, tside, md):
        """返回 (威力倍率, 固定伤害或None)。"""
        dyn = fx.get("dyn")
        power = 1.0
        fixed = None
        if fx.get("super_fang"):
            fixed = max(1, target.hp // 2)
        elif fx.get("fixed") is not None:
            fixed = 20 if fx["fixed"] == 20 else user.level if fx["fixed"] == "level" else fx["fixed"]
        elif dyn == "weight":
            power = weight_power(target.weight) / md["power"]
        elif dyn == "gyro":
            power = max(1, min(150, 25 * target.effective_speed() // max(1, user.effective_speed()))) / md["power"]
        elif dyn == "brine":
            if target.hp <= target.max_hp // 2:
                power = 2.0
        elif dyn == "revenge":
            if self.vol[tside]["damaged"]:
                power = 2.0
        elif dyn == "assurance":
            if self.vol[tside]["damaged"]:
                power = 2.0
        elif dyn == "hp_high":
            power = 150 * target.hp / target.max_hp / md["power"]
        elif dyn == "hp_low":
            power = (20 + 200 * (1 - user.hp / user.max_hp)) / md["power"]
        elif dyn == "facade":
            if user.status in ("中毒", "剧毒", "灼伤", "麻痹"):
                power = 2.0
        elif dyn == "magnitude":
            power = random.choice((10, 30, 30, 50, 50, 50, 70, 70, 90, 110)) / md["power"]
        if fx.get("salts") and target.status == "麻痹":
            power *= 2
        if fx.get("wake_slap") and target.status == "睡眠":
            power *= 2
        if fx.get("dream") and target.status == "睡眠":
            pass
        return power, fixed

    def _apply_effects(self, side, fx, target):
        """伤害招式命中后的次要效果(对目标)。"""
        if target.hp <= 0:
            return
        tside = self.other(side)
        if fx.get("flinch") and not self.vol[tside]["acted"] and random.random() * 100 < fx["flinch"]:
            self.vol[tside]["flinch"] = True
        if fx.get("status"):
            yield from self._apply_status(side, fx["status"][0], fx["status"][1])
        for eff in fx.get("stat", []):
            if eff["who"] != "foe":
                continue
            if random.random() * 100 <= eff["chance"]:
                yield from self._change_stage(self.other(side), eff["stat"], eff["d"])
        if fx.get("confuse") and random.random() * 100 < fx["confuse"]:
            yield from self._confuse(self.other(side))

    def _self_effects(self, side, fx, user):
        if user.hp <= 0:
            return
        for eff in fx.get("stat", []):
            if eff["who"] != "self" or random.random() * 100 > eff["chance"]:
                continue
            yield from self._change_stage(side, eff["stat"], eff["d"])

    # -------------------------------------------------- 变化招式
    def _status_move(self, side, md, fx):
        tside = self.other(side)
        user, target = self.mon(side), self.mon(tside)
        v, tv = self.vol[side], self.vol[tside]
        foe_targeted = any(k in fx for k in ("status", "confuse", "leech", "hazard", "roar", "reset")) or \
            any(e["who"] == "foe" for e in fx.get("stat", []))
        if foe_targeted and tv["protected"]:
            yield ("msg", f"{target.name}保护了自己!")
            return
        if foe_targeted and not self._hits(user, target, side, tside, md):
            yield ("msg", "但是没有命中……")
            return
        if fx.get("protect"):
            yield from self._protect(side)
            return
        if fx.get("heal") or fx.get("rest"):
            if fx.get("rest"):
                if user.status == "睡眠":
                    yield ("msg", "但是失败了……")
                    return
                user.hp = user.max_hp
                user.cure_status()
                user.status = "睡眠"
                user.sleep_turns = 3
                yield ("msg", f"{user.name}睡著了,恢复了体力!")
            else:
                if user.hp >= user.max_hp:
                    yield ("msg", "但是失败了……")
                    return
                user.hp = min(user.max_hp, user.hp + user.max_hp // 2)
                yield ("msg", f"{user.name}恢复了体力!")
            yield ("anim", "heal_" + side, 0.4)
            return
        if fx.get("cure"):
            if fx["cure"] == "party":
                n = 0
                for m in (self.game.party if side == "ally" else self.enemies):
                    if m.status:
                        m.cure_status()
                        n += 1
                yield ("msg", f"{user.name}的队伍恢复了状态!" if n else "但是什么也没有发生……")
            else:
                if user.status:
                    user.cure_status()
                    yield ("msg", f"{user.name}恢复了状态!")
                else:
                    yield ("msg", "但是什么也没有发生……")
            return
        if fx.get("weather"):
            self.weather = fx["weather"]
            self.weather_turns = 5
            yield ("anim", "weather", 0.5, fx["weather"])
            yield ("msg", f"刮起了{WEATHER_CN[fx['weather']]}!" if fx["weather"] == "sand"
                   else f"{WEATHER_CN[fx['weather']]}开始了!")
            return
        if fx.get("screen"):
            key = {"reflect": "reflect", "light": "light"}[fx["screen"]]
            self.sides[side][key] = 5
            yield ("msg", f"{user.name}使出了{'反射壁' if key == 'reflect' else '光墙'}!")
            return
        if fx.get("safeguard"):
            self.sides[side]["safeguard"] = 5
            yield ("msg", f"{user.name}被神秘守护包围了!")
            return
        if fx.get("hazard"):
            h = fx["hazard"]
            sd = self.sides[tside]
            if h == "stealth":
                if sd["stealth"]:
                    yield ("msg", "但是失败了……")
                else:
                    sd["stealth"] = True
                    yield ("msg", f"无数岩石悬浮在{target.name}周围!")
            elif h == "spikes":
                if sd["spikes"] >= 3:
                    yield ("msg", "但是失败了……")
                else:
                    sd["spikes"] += 1
                    yield ("msg", f"撒菱散落在{target.name}周围!")
            else:
                if sd["tspikes"] >= 2:
                    yield ("msg", "但是失败了……")
                else:
                    sd["tspikes"] += 1
                    yield ("msg", f"毒菱散落在{target.name}周围!")
            return
        if fx.get("leech"):
            if tv["leech"] or "草" in target.types:
                yield ("msg", "但是没有效果……")
            else:
                tv["leech"] = True
                yield ("msg", f"{target.name}被种下了寄生种子!")
            return
        if fx.get("ingrain"):
            v["ingrain"] = True
            yield ("msg", f"{user.name}扎下了根!")
            return
        if fx.get("aquaring"):
            v["aquaring"] = True
            yield ("msg", f"{user.name}被水流环包围了!")
            return
        if fx.get("reset"):
            self.stages = {"ally": {}, "foe": {}}
            yield ("msg", "所有的能力变化都恢复了正常!")
            return
        if fx.get("crit_up"):
            self.crit_stage[side] = min(4, self.crit_stage[side] + 2)
            yield ("msg", f"{user.name}集中了精神,变得容易击中要害!")
            return
        if fx.get("break_screen"):
            yield from self._break_screens(tside)
            return
        if fx.get("spin"):
            yield from self._spin(side)
            return
        if fx.get("roar"):
            if self.trainer:
                yield ("msg", "但是失败了……")
            else:
                yield ("msg", f"野生的{target.name}逃走了!")
                self._end_battle("ran")
            return
        if fx.get("status"):
            yield from self._apply_status(side, fx["status"][0], fx["status"][1], announce=True)
        if fx.get("confuse"):
            yield from self._confuse(tside)
        for eff in fx.get("stat", []):
            who = side if eff["who"] == "self" else tside
            yield from self._change_stage(who, eff["stat"], eff["d"])

    def _protect(self, side):
        v = self.vol[side]
        if v["protect_streak"] > 0 and random.random() < 1 - 0.5 ** v["protect_streak"]:
            v["protect_streak"] = 0
            yield ("msg", "但是失败了……")
            return
        v["protected"] = True
        v["protect_streak"] += 1
        yield ("msg", f"{self.mon(side).name}保护了自己!")

    def _break_screens(self, tside):
        sd = self.sides[tside]
        if sd["reflect"] or sd["light"]:
            sd["reflect"] = sd["light"] = 0
            yield ("msg", "墙壁被打碎了!")
        else:
            yield ("msg", "但是什么也没有发生……")

    def _spin(self, side):
        sd = self.sides[side]
        v = self.vol[side]
        cleared = sd["stealth"] or sd["spikes"] or sd["tspikes"] or v["leech"]
        sd["stealth"], sd["spikes"], sd["tspikes"], v["leech"] = False, 0, 0, False
        yield ("msg", f"{self.mon(side).name}扫掉了场上的障碍!" if cleared else "但是什么也没有发生……")

    def _confuse(self, side):
        v = self.vol[side]
        if v["confuse"] > 0 or self.sides[side]["safeguard"] > 0:
            yield ("msg", "但是失败了……")
            return
        v["confuse"] = random.randint(2, 5)
        yield ("msg", f"{self.mon(side).name}变得混乱了!")

    def _apply_status(self, side, status, chance, announce=False):
        tside = self.other(side)
        target = self.mon(tside)
        if target.hp <= 0 or chance <= 0:
            return
        if not announce and random.random() * 100 >= chance:
            return
        if self.sides[tside]["safeguard"] > 0:
            yield ("msg", f"神秘守护挡住了{target.name}的异常状态!")
            return
        if target.status:
            yield ("msg", f"{target.name}已经处于异常状态了!")
            return
        if target.status_immune(status):
            yield ("msg", f"对{target.name}没有效果……")
            return
        target.status = status
        target.toxic_counter = 0
        if status == "睡眠":
            target.sleep_turns = random.randint(2, 5)
        word = {"中毒": "中毒了!", "剧毒": "中了剧毒!", "灼伤": "被灼伤了!", "麻痹": "麻痹了!", "睡眠": "睡着了!",
                "冻结": "被冻结了!"}
        yield ("msg", f"{target.name}{word[status]}")

    def _change_stage(self, side, key, delta):
        mon = self.mon(side)
        cur = self.stages[side].get(key, 0)
        if (delta < 0 and cur <= -6) or (delta > 0 and cur >= 6):
            yield ("msg", f"{mon.name}的能力已经无法再变化了!")
            return
        self.stages[side][key] = max(-6, min(6, cur + delta))
        cn = {"atk": "攻击", "def": "防御", "spa": "特攻", "spd": "特防", "spe": "速度", "acc": "命中", "eva": "闪避"}[key]
        word = "提高" if delta > 0 else "降低"
        how = "" if abs(delta) == 1 else "大幅"
        yield ("msg", f"{mon.name}的{cn}{how}{word}了!")

    # -------------------------------------------------- 濒倒
    def _faint_flow(self, side):
        mon = self.mon(side)
        yield ("anim", "faint_" + side, 0.45)
        yield ("msg", f"{mon.name}倒下了!")
        if side == "foe":
            gain = data.exp_gain(mon, self.trainer is not None)
            yield from self._give_exp(gain)
            if self.trainer and self.e_idx < len(self.enemies) - 1:
                self.e_idx += 1
                self.disp["foe"] = None
                yield ("msg", f"{self.trainer}派出了{self.foe.name}!")
                yield from self._entry_effects("foe")
                return True
            if self.trainer:
                prize = self.prize_rate * max(m.level for m in self.enemies)
                self.game.money += prize
                yield ("msg", f"你战胜了{self.trainer}!\n获得了{prize}元奖金!")
            self._end_battle("win")
            return False
        # 我方濒倒
        if any(m.hp > 0 for m in self.game.party):
            idx = yield ("party", "forced")
            if idx is not None:
                yield from self._switch_to(idx)
            return True
        yield ("msg", "你已经没有能战斗的精灵了……")
        self._end_battle("lose")
        return False

    def _give_exp(self, gain):
        """参战精灵获得全额经验;携带学习装置(背包里)的其他精灵获得一半。"""
        m = self.ally
        yield ("msg", f"{m.name}获得了{gain}点经验值!")
        yield from self._grant_exp(m, gain)
        if self.game.has_item("学习装置"):
            share = gain // 2
            for other in self.game.party:
                if other is m or other.hp <= 0:
                    continue
                yield ("msg", f"{other.name}通过学习装置获得了{share}点经验值!")
                yield from self._grant_exp(other, share)

    def _grant_exp(self, m, gain):
        msgs, evos, pending = m.gain_exp(gain, map_tag=self.context.get("map_tag"), party=self.game.party)
        for t in msgs:
            yield ("msg", t)
        for mv in pending:
            forget = yield ("learnmove", m, mv)
            yield ("msg", m.learn_move(mv, forget))
        for e in evos:
            self.pending_evo.append((m, e))

    def resolve_pending_evolution(self):
        """战斗结束后由 overworld 调用:返回 [(mon, old, new)] 列表。"""
        out = []
        for m, target in self.pending_evo:
            old = m.species
            m.evolve_into(target)
            out.append((m, old, target))
        self.pending_evo = []
        return out

    def _switch_to(self, idx):
        old = self.ally.name
        self.p_idx = idx
        self.disp["ally"] = None
        yield ("msg", f"回来吧,{old}!")
        yield ("msg", f"去吧!{self.ally.name}!")
        yield from self._entry_effects("ally")

    # -------------------------------------------------- 道具
    def _safari_throw(self):
        if self.safari_balls <= 0:
            self._end_battle("ran")
            return
        self.safari_balls -= 1
        shakes = self.foe.catch_shakes(1.5, rng=random)
        self._thrown_item = "精灵球"
        yield ("msg", f"投出了狩猎球!(剩余 {self.safari_balls})")
        dur = BALL_THROW_T + BALL_FLASH_T + BALL_SHAKE_T * shakes + (0.7 if shakes >= 4 else 0.35)
        yield ("anim", "ball", dur, shakes)
        if shakes >= 4:
            yield ("msg", f"太好了!{self.foe.name}被抓住了!")
            self.game.caught.add(self.foe.species)
            if len(self.game.party) < 6:
                self.game.party.append(self.foe)
            else:
                self.game.pc.append(self.foe.to_dict())
            self._end_battle("caught")
            return
        yield ("msg", "哎呀!差一点就成功了!")
        if self.safari_balls <= 0:
            self._end_battle("ran")
            return
        yield from self._turn([], foe_free=True)

    def _use_item(self, name):
        item = data.ITEMS[name]
        kind = item["kind"]
        if kind == "ball":
            if not self.can_catch:
                yield ("msg", "不能对训练家的精灵扔球!")
                return None
            rate = self._ball_rate(item["rate"])
            self.game.remove_item(name, 1)
            shakes = self.foe.catch_shakes(rate, rng=random)
            self._thrown_item = name
            yield ("msg", f"你扔出了{name}!")
            dur = BALL_THROW_T + BALL_FLASH_T + BALL_SHAKE_T * shakes + (0.7 if shakes >= 4 else 0.35)
            yield ("anim", "ball", dur, shakes)
            if shakes >= 4:
                yield ("msg", f"太好了!{self.foe.name}被抓住了!")
                if item["rate"] == "heal":
                    self.foe.full_heal()
                    yield ("msg", f"{self.foe.name}恢复了体力!")
                self.game.caught.add(self.foe.species)
                self.foe.held = None
                if len(self.game.party) < 6:
                    self.game.party.append(self.foe)
                    yield ("msg", f"{self.foe.name}加入了队伍!")
                else:
                    self.game.pc.append(self.foe.to_dict())
                    yield ("msg", f"队伍已满,{self.foe.name}被传送到了电脑里。")
                self._end_battle("caught")
                return None
            yield ("msg", "哎呀!差一点就成功了!")
            return "used"
        if kind in ("heal", "fullheal", "cure", "revive", "pp", "ppall"):
            idx = yield ("party", "target")
            if idx is None:
                return None
            target = self.game.party[idx]
            ok = self._apply_item_to(target, item)
            if not ok:
                yield ("msg", "现在没有使用的效果!")
                return None
            self.game.remove_item(name, 1)
            yield ("msg", self._item_msg(target, item))
            return "used"
        if kind in ("stat", "crit"):
            self.game.remove_item(name, 1)
            if kind == "stat":
                yield from self._change_stage("ally", item["param"], 1)
            else:
                self.crit_stage["ally"] = min(4, self.crit_stage["ally"] + 2)
                yield ("msg", f"{self.ally.name}变得容易击中要害!")
            return "used"
        yield ("msg", "现在不能使用那个!")
        return None

    def _apply_item_to(self, m, item):
        kind, param = item["kind"], item.get("param")
        if kind == "revive":
            if m.hp > 0:
                return False
            m.hp = max(1, int(m.max_hp * param))
            m.cure_status()
            return True
        if kind == "heal":
            if m.hp <= 0 or m.hp >= m.max_hp:
                return False
            m.hp = min(m.max_hp, m.hp + (param if param < 9999 else m.max_hp))
            return True
        if kind == "fullheal":
            if m.hp <= 0 or (m.hp >= m.max_hp and not m.status):
                return False
            m.hp = m.max_hp
            m.cure_status()
            return True
        if kind == "cure":
            if not m.status or (param != "all" and m.status != param):
                return False
            m.cure_status()
            return True
        if kind in ("pp", "ppall"):
            moves = m.moves if kind == "ppall" else None
            if kind == "pp":
                idx = 0                     # 简化:恢复第一个 PP 不足的招式
                cands = [x for x in m.moves if x.pp < x.max_pp]
                if not cands:
                    return False
                cands[0].pp = min(cands[0].max_pp, cands[0].pp + (param if param < 9999 else 99))
                return True
            if not any(x.pp < x.max_pp for x in m.moves):
                return False
            for x in moves:
                x.pp = min(x.max_pp, x.pp + (param if param < 9999 else 99))
            return True
        return False

    def _item_msg(self, m, item):
        kind = item["kind"]
        if kind == "revive":
            return f"{m.name}恢复了意识!"
        if kind == "heal":
            return f"{m.name}的HP恢复了!"
        if kind == "fullheal":
            return f"{m.name}完全恢复了!"
        if kind == "cure":
            return f"{m.name}的异常状态被治愈了!"
        return f"{m.name}的PP恢复了!"

    def _ball_rate(self, rate):
        if isinstance(rate, (int, float)):
            return rate
        foe = self.foe
        if rate == "net":
            return 3.5 if ("虫" in foe.types or "水" in foe.types) else 1.0
        if rate == "dive":
            return 3.5 if (self.context.get("surf") or self.context.get("fishing")) else 1.0
        if rate == "nest":
            return max(1.0, (41 - foe.level) / 10)
        if rate == "repeat":
            return 3.0 if foe.species in self.game.caught else 1.0
        if rate == "timer":
            return min(4.0, (self.turns + 10) / 10)
        if rate == "quick":
            return 4.0 if self.turns == 0 else 1.0
        if rate == "dusk":
            return 4.0 if self.context.get("cave") else 1.5
        return 1.0

    def _try_run(self):
        if not self.can_run:
            yield ("msg", "不能从训练家对战中逃走!")
            return
        ps = self.ally.effective_speed()
        es = max(1, self.foe.effective_speed())
        f = ps * 128 // es + 30 * self.run_attempts
        self.run_attempts += 1
        if f > 255 or random.randint(0, 255) < f:
            yield ("msg", "成功逃走了!")
            self._end_battle("ran")
        else:
            yield ("msg", "没能逃走!")
            yield from self._turn([], foe_free=True)

    # -------------------------------------------------- AI
    def _ai_wants_item(self):
        m = self.foe
        if not self.trainer_items or m.hp > m.max_hp * 0.35:
            return False
        return True

    def _ai_use_item(self):
        m = self.foe
        missing = m.max_hp - m.hp
        best = None
        for name in self.trainer_items:
            it = data.ITEMS.get(name)
            if not it or it["kind"] not in ("heal", "fullheal"):
                continue
            amount = 9999 if it["kind"] == "fullheal" else it.get("param", 0)
            if amount >= missing or amount >= 200:
                if best is None or amount > best[1]:
                    best = (name, amount)
        if best is None:
            for name in self.trainer_items:
                it = data.ITEMS.get(name)
                if it and it["kind"] == "heal":
                    if best is None or it.get("param", 0) > best[1]:
                        best = (name, it.get("param", 0))
        if best is None:
            return False
        name = best[0]
        self.trainer_items.remove(name)
        it = data.ITEMS[name]
        if it["kind"] == "fullheal":
            m.hp = m.max_hp
            m.cure_status()
        else:
            m.hp = min(m.max_hp, m.hp + it["param"])
        return name

    def _ai_pick_move(self):
        usable = [m for m in self.foe.moves if m.pp > 0]
        if not usable:
            return "挣扎"
        noise = {0: 45, 1: 20, 2: 8, 3: 3}.get(min(self.ai_level, 3), 20)
        best, best_score = None, None
        for m in usable:
            s = self._score_move(m) + random.uniform(0, noise)
            if best_score is None or s > best_score:
                best, best_score = m, s
        return best.name if best else "挣扎"

    def _expected_damage(self, move):
        md = data.MOVES[move.name]
        fx = md.get("fx", {})
        if md["cat"] == "变化" or not md["power"]:
            return 0, 1.0
        power_mod, fixed = self._power_modifiers(fx, self.foe, self.ally, "ally", md)
        if fixed is not None:
            return fixed, 1.0
        res = self.foe.calc_damage(self.ally, move.name, att_stages=self.stages["foe"],
                                   dfn_stages=self.stages["ally"], rng=_FixedRandom(),
                                   mods={"power": power_mod, "crit_stage": 1, "weather": self.weather,
                                         "screen": self._screen_mod("ally", md)})
        return res["damage"], res["eff"]

    def _score_move(self, move):
        md = data.MOVES[move.name]
        fx = md.get("fx", {})
        ally, foe = self.ally, self.foe
        if md["cat"] == "变化":
            return self._score_status_move(fx, ally, foe)
        if fx.get("dream") and ally.status != "睡眠":
            return -1
        dmg, eff = self._expected_damage(move)
        if eff == 0:
            return -1
        if fx.get("first_turn") and self.turns > 1:
            return -1
        if fx.get("faint_user"):
            if len([m for m in self.enemies if m.hp > 0]) <= 1 and not self.trainer_items:
                return dmg >= ally.hp * 1.2 and 60 or 5
            return 40 if dmg >= ally.hp else 10
        if fx.get("recoil"):
            if foe.hp <= foe.max_hp // 3 and fx["recoil"] >= 0.33:
                dmg *= 0.5
        if fx.get("recharge"):
            dmg *= 0.6
        s = min(100, int(100 * min(1.2, dmg / max(1, ally.hp))))
        if dmg >= ally.hp:
            s = 100
        elif eff > 1:
            s = min(100, s + 10)
        elif eff < 1:
            s -= 5
        if fx.get("super_fang") and ally.hp > ally.max_hp * 0.6:
            s = 70
        if fx.get("status") and not ally.status and not ally.status_immune(fx["status"][0]):
            s += fx["status"][1] // 5
        if fx.get("flinch") and self.turns < 4:
            s += fx["flinch"] // 6
        return s

    def _score_status_move(self, fx, ally, foe):
        tside, fside = "ally", "foe"
        if fx.get("heal"):
            r = foe.hp / foe.max_hp
            return 85 if r < 0.35 else 40 if r < 0.6 else 2
        if fx.get("rest"):
            if foe.status == "睡眠":
                return 1
            if foe.held == "樟樟果" and foe.hp < foe.max_hp * 0.6:
                return 90
            return 65 if foe.hp < foe.max_hp * 0.3 else 3
        if fx.get("protect"):
            return 15 if self.vol["foe"]["protect_streak"] else 30
        if fx.get("cure"):
            return 70 if foe.status else 5
        if fx.get("weather"):
            if self.weather:
                return 2
            if fx["weather"] == "sun" and any("火" in m.types for m in self.enemies if m.hp > 0):
                return 45
            return 20
        if fx.get("screen"):
            return 45 if self.turns < 3 and self.sides["foe"][{"reflect": "reflect", "light": "light"}[fx["screen"]]] == 0 else 3
        if fx.get("safeguard"):
            return 30 if self.turns < 3 and not self.sides["foe"]["safeguard"] else 2
        if fx.get("hazard"):
            sd = self.sides["ally"]
            return 40 if self.turns < 4 else 6
        if fx.get("leech"):
            return 45 if not self.vol["ally"]["leech"] and "草" not in ally.types else 2
        if fx.get("ingrain"):
            return 30 if not self.vol["foe"]["ingrain"] else 1
        if fx.get("aquaring"):
            return 25 if not self.vol["foe"]["aquaring"] else 1
        if fx.get("reset"):
            return 20 if any(v > 1 for v in self.stages["ally"].values()) else 0
        if fx.get("crit_up"):
            return 30 if self.crit_stage["foe"] == 1 else 0
        if fx.get("roar"):
            return 0
        if fx.get("spin"):
            sd = self.sides["foe"]
            return 60 if (sd["stealth"] or sd["spikes"] or self.vol["foe"]["leech"]) else 3
        if fx.get("break_screen"):
            sd = self.sides["ally"]
            return 55 if (sd["reflect"] or sd["light"]) else 5
        s = 0
        if fx.get("status"):
            st, chance = fx["status"]
            if ally.status or ally.status_immune(st) or self.sides["ally"]["safeguard"]:
                s = 0
            else:
                base = {"睡眠": 60, "麻痹": 52, "剧毒": 55, "灼伤": 52, "中毒": 42, "冻结": 60}[st]
                s = base if self.turns <= 2 else base * 0.45
                if st == "灼伤" and ally.stats["spa"] > ally.stats["atk"]:
                    s -= 12
                if st == "麻痹" and ally.effective_speed() < foe.effective_speed():
                    s -= 15
        if fx.get("confuse"):
            if self.vol["ally"]["confuse"] or self.sides["ally"]["safeguard"]:
                s = 0
            else:
                s += 45 if self.turns <= 2 else 20
        for eff in fx.get("stat", []):
            who = fside if eff["who"] == "self" else tside
            cur = self.stages[who].get(eff["stat"], 0)
            if (eff["d"] > 0 and cur >= 6) or (eff["d"] < 0 and cur <= -6):
                continue
            if eff["who"] == "self":
                val = abs(eff["d"]) * 20
                if any(e["stat"] in ("atk", "spa") and e["d"] > 0 for e in fx.get("stat", [])):
                    val += 8
                if foe.hp < foe.max_hp * 0.4:
                    val -= 18
                s += val if self.turns < 5 else val * 0.5
            else:
                s += abs(eff["d"]) * 15
        return s

    def _ai_turn(self):
        """训练家回合:低血量先用伤药,否则选招。返回 (msg 列表, 是否使用了道具)。"""
        if self._ai_wants_item():
            name = self._ai_use_item()
            if name:
                return [f"{self.trainer}对{self.foe.name}使用了{name}!"], True
        return [], False

    # -------------------------------------------------- 输入
    def handle_event(self, e):
        if e.type != pygame.KEYDOWN or self.done:
            return
        ph = self.phase
        if ph == "msg":
            r = self.textbox.key(e)
            if r:
                self._advance(None)
        elif ph == "menu":
            self._menu_key(e)
        elif ph == "movesel":
            self._move_key(e)
        elif ph == "bag" and self.bag_screen:
            self.bag_screen.key(e)
            if self.bag_screen.done:
                item = self.bag_screen.result
                self.bag_screen = None
                self._advance(item)
        elif ph == "party" and self.party_screen:
            self.party_screen.key(e)
            if self.party_screen.done:
                idx = self.party_screen.result
                self.party_screen = None
                self._advance(idx)
        elif ph == "learnmove" and self.learn_screen:
            self.learn_screen.key(e)
            if self.learn_screen.done:
                forget = self.learn_screen.result
                self.learn_screen = None
                self._advance(forget)

    def _menu_key(self, e):
        opts = ("fight", "run") if self.safari else ("fight", "bag", "party", "run")
        n = len(opts)
        if e.key in K.UP:
            self.menu_idx = (self.menu_idx - 2) % n
        elif e.key in K.DOWN:
            self.menu_idx = (self.menu_idx + 2) % n
        elif e.key in K.LEFT:
            self.menu_idx = (self.menu_idx - 1) % n
        elif e.key in K.RIGHT:
            self.menu_idx = (self.menu_idx + 1) % n
        elif e.key in K.A:
            self._advance(opts[self.menu_idx])
        elif e.key in K.Y and not self.safari:       # Y = 快捷背包
            self._advance("bag")

    def _move_key(self, e):
        n = len(self.ally.moves)
        if e.key in K.UP:
            self.move_idx = (self.move_idx - 2) % n
        elif e.key in K.DOWN:
            self.move_idx = (self.move_idx + 2) % n
        elif e.key in K.LEFT:
            self.move_idx = (self.move_idx - 1) % n
        elif e.key in K.RIGHT:
            self.move_idx = (self.move_idx + 1) % n
        elif e.key in K.B:
            self._advance("back")
        elif e.key in K.A:
            self._advance(("move", self.move_idx))

    # -------------------------------------------------- 更新
    def update(self, dt):
        self.textbox.update(dt)
        for k in ("ally", "foe"):
            mon = self.mon(k)
            tgt = mon.hp / mon.max_hp
            cur = self.disp[k] if self.disp[k] is not None else tgt
            self.disp[k] = cur + (tgt - cur) * min(1.0, dt * 5)
        if self.phase == "anim" and self.anim:
            self.anim[1] += dt
            if self.anim[1] >= self.anim[2]:
                self.anim = None
                self._advance(None)
        elif self.phase == "msg" and self.auto and self.textbox.wait_key:
            self._advance(None)
        if self.intro_t > 0:
            self.intro_t -= dt

    # -------------------------------------------------- 绘制
    def _draw_type_fx(self, surf, mtype, cx, cy, t, dur):
        """按招式属性绘制命中粒子特效(t 为动画已进行时间)。"""
        p = min(1.0, max(0.0, t / dur))
        N = 10

        def rnd(i, m=13):
            return ((i * 97 + int(t * 60)) % m) / m

        if mtype == "火":
            for i in range(N):
                x = cx + int((rnd(i) - 0.5) * 70)
                y = cy + 30 - int(p * 90) - rnd(i + 5) * 20
                col = (255, 160, 40) if i % 2 else (230, 70, 40)
                pygame.draw.polygon(surf, col, [(x - 4, y + 5), (x + 4, y + 5), (x, y - 6)])
        elif mtype == "水":
            for i in range(N):
                x = cx + int((rnd(i) - 0.5) * 90)
                y = cy + 20 - int(p * 70)
                pygame.draw.circle(surf, (110, 170, 245), (x, y), 3 + i % 3)
        elif mtype == "电":
            for i in range(4):
                x0 = cx + (i - 2) * 22
                pts = [(x0, cy - 70)]
                for seg in range(1, 5):
                    pts.append((x0 + (rnd(i * 4 + seg) - 0.5) * 26, cy - 70 + seg * 16))
                pygame.draw.lines(surf, (255, 226, 70), False, pts, 3)
        elif mtype == "草":
            for i in range(N):
                a = p * 6 + i
                x = cx + int(math.cos(a) * (20 + p * 40))
                y = cy - int(math.sin(a) * (14 + p * 36))
                col = (90, 190, 80) if i % 2 else (140, 210, 90)
                pygame.draw.polygon(surf, col, [(x - 4, y), (x + 4, y), (x, y - 7)])
        elif mtype == "冰":
            for i in range(N):
                x = cx + int((rnd(i) - 0.5) * 80)
                y = cy - 40 + int(p * 80)
                pygame.draw.polygon(surf, (200, 235, 255), [(x, y - 5), (x + 4, y), (x, y + 5), (x - 4, y)])
        elif mtype in ("岩石", "地面"):
            for i in range(N):
                x = cx + int((rnd(i) - 0.5) * 90)
                y = cy + 40 - int(p * 90) - rnd(i + 3) * 25
                pygame.draw.circle(surf, (150, 118, 84) if i % 2 else (110, 88, 62), (x, y), 4)
        elif mtype in ("超能力", "幽灵"):
            for i in range(3):
                r = 8 + i * 10 + int(p * 30)
                pygame.draw.circle(surf, (180, 120, 220) if mtype == "超能力" else (120, 90, 160),
                                   (cx, cy), r, 3)
        elif mtype == "毒":
            for i in range(N):
                x = cx + int((rnd(i) - 0.5) * 80)
                y = cy + 20 - int(p * 60)
                pygame.draw.circle(surf, (160, 90, 190), (x, y), 3 + i % 2)
        elif mtype == "恶":
            for i in range(N):
                a = i * 0.63 + p * 3
                r = 30 + p * 50
                pygame.draw.circle(surf, (90, 60, 110) if i % 2 else (60, 40, 80),
                                   (int(cx + math.cos(a) * r), int(cy + math.sin(a) * r * 0.6)), 6)
        elif mtype == "钢":
            for i in range(8):
                a = i * math.pi / 4
                r0 = 20 + p * 30
                pygame.draw.line(surf, (220, 226, 240), (cx + math.cos(a) * 14, cy + math.sin(a) * 14),
                                 (cx + math.cos(a) * r0, cy + math.sin(a) * r0), 5)
        else:
            # 一般/格斗/飞行/虫/龙 等:放射冲击线
            for i in range(8):
                a = i * math.pi / 4 + 0.3
                r0 = 12 + p * 26
                r1 = r0 + 14
                pygame.draw.line(surf, (255, 240, 180) if i % 2 == 0 else (240, 200, 120),
                                 (cx + math.cos(a) * r0, cy + math.sin(a) * r0),
                                 (cx + math.cos(a) * r1, cy + math.sin(a) * r1), 3)

    def draw(self, surf):
        assets = self.game.assets
        surf.blit(assets["battle_bg"], (0, 0))
        foe_x = S.WIN_W - 240
        foe_y = 120
        ally_x = 190
        ally_y = S.WIN_H - 130 - 210
        slide = max(0, self.intro_t / 0.6) * 160
        hit = self.anim[0] == "hit_foe" if self.anim else False
        hit_a = self.anim[0] == "hit_ally" if self.anim else False
        flick = 0 if (self.anim and self.anim[0].startswith("hit") and
                      int(self.anim[1] * 24) % 2 == 0) else 1
        ball_anim = self.anim is not None and self.anim[0] == "ball"
        ball_t = self.anim[1] if ball_anim else 0.0
        ball_shakes = (self.anim[3] or 0) if ball_anim else 0
        suck_k = None
        if ball_anim and ball_t > BALL_THROW_T:
            suck_k = min(1.0, (ball_t - BALL_THROW_T) / BALL_FLASH_T)
        show_foe = (self.foe.hp > 0 or (self.anim and self.anim[0] == "faint_foe")) and suck_k != 1.0

        if show_foe:
            img = assets["mons"].get(data.SPECIES[self.foe.species]["art"])
            if img:
                dy = 0
                if self.anim and self.anim[0] == "faint_foe":
                    k = min(1.0, self.anim[1] / self.anim[2])
                    dy = int(k * 60)
                    img = img.copy()
                    img.set_alpha(int(255 * (1 - k)))
                if suck_k is not None:
                    sc = 1.0 - 0.92 * suck_k
                    iw = max(2, int(img.get_width() * sc))
                    ih = max(2, int(img.get_height() * sc))
                    small = pygame.transform.scale(img, (iw, ih))
                    surf.blit(small, (foe_x + 40 - iw // 2, foe_y - ih // 2))
                elif flick or not hit:
                    x = foe_x + int(slide) + (random.randint(-2, 2) if hit else 0)
                    surf.blit(img, (x, foe_y - 40 + dy))
                if self.vol["foe"]["confuse"] and self.foe.hp > 0:
                    for i in range(3):
                        a = pygame.time.get_ticks() / 300 + i * 2.1
                        pygame.draw.circle(surf, (240, 120, 220), (int(foe_x + 40 + math.cos(a) * 36),
                                                                   int(foe_y - 60 + math.sin(a) * 10)), 4)
        if ball_anim:
            ball = self.game.assets.get("balls", {}).get(self._thrown_item, "") or assets["ball"]
            sx0, sy0 = ally_x + 170, ally_y + 60
            ex, ey = foe_x + 30, foe_y + 56
            if ball_t < BALL_THROW_T:
                k = ball_t / BALL_THROW_T
                x = sx0 + (ex - sx0) * k
                y = sy0 + (ey - sy0) * k - int(math.sin(math.pi * k) * 130)
                img = pygame.transform.rotate(ball, int(540 * k))
                surf.blit(img, (x - img.get_width() // 2, y - img.get_height() // 2))
            else:
                st = ball_t - BALL_THROW_T
                pygame.draw.ellipse(surf, (96, 140, 96), (ex - 15, ey + 7, 30, 9))
                if st < BALL_FLASH_T:
                    k = st / BALL_FLASH_T
                    r = int(6 + k * 40)
                    pygame.draw.circle(surf, (255, 255, 255), (foe_x + 40, foe_y), r, max(2, int(7 * (1 - k))))
                else:
                    st2 = st - BALL_FLASH_T
                    idx = int(st2 // BALL_SHAKE_T)
                    if idx < ball_shakes:
                        k2 = (st2 % BALL_SHAKE_T) / BALL_SHAKE_T
                        ang = math.sin(math.pi * k2) * 24
                        img = pygame.transform.rotate(ball, ang)
                        surf.blit(img, (ex - img.get_width() // 2, ey - img.get_height() // 2))
                    else:
                        surf.blit(ball, (ex - ball.get_width() // 2, ey - ball.get_height() // 2))
                        if ball_shakes >= 4:
                            for dx, dy2, rr in ((-15, -8, 3), (13, -12, 2), (17, 3, 2)):
                                pygame.draw.circle(surf, (255, 214, 90), (ex + dx, ey + dy2), rr)
        if self.ally.hp > 0 or (self.anim and self.anim[0] == "faint_ally"):
            img = assets["mons_back"].get(data.SPECIES[self.ally.species]["art"])
            if img:
                back = pygame.transform.scale(img, (int(img.get_width() * 1.35),
                                                    int(img.get_height() * 1.35)))
                dy = 0
                if self.anim and self.anim[0] == "faint_ally":
                    k = min(1.0, self.anim[1] / self.anim[2])
                    dy = int(k * 70)
                    back = back.copy()
                    back.set_alpha(int(255 * (1 - k)))
                if flick or not hit_a:
                    surf.blit(back, (ally_x - int(slide), ally_y + 40 + dy))
                if self.vol["ally"]["confuse"] and self.ally.hp > 0:
                    for i in range(3):
                        a = pygame.time.get_ticks() / 300 + i * 2.1
                        pygame.draw.circle(surf, (240, 120, 220), (int(ally_x + 60 + math.cos(a) * 44),
                                                                   int(ally_y + 60 + math.sin(a) * 12)), 4)

        # 属性粒子特效 / 回复 / 天气动画
        if self.anim and self.anim[0].startswith("hit") and len(self.anim) > 3 and self.anim[3]:
            fx_x = foe_x + 40 if self.anim[0] == "hit_foe" else ally_x + 54
            fx_y = foe_y if self.anim[0] == "hit_foe" else ally_y + 94
            self._draw_type_fx(surf, self.anim[3], fx_x, fx_y, self.anim[1], self.anim[2])
        if self.anim and self.anim[0].startswith("heal_"):
            cx = ally_x + 60 if self.anim[0] == "heal_ally" else foe_x + 40
            cy = ally_y + 80 if self.anim[0] == "heal_ally" else foe_y
            for i in range(6):
                yy = cy + 40 - int((self.anim[1] / self.anim[2]) * 90) - i * 12
                pygame.draw.circle(surf, (150, 240, 160), (cx + (i % 2) * 20 - 10, yy), 4)
        if self.anim and self.anim[0] == "weather":
            self._draw_weather(surf, self.anim[3], self.anim[1])
        if self.weather:
            self._draw_weather(surf, self.weather, None, subtle=True)

        # 信息面板
        f = self.foe
        panel(surf, (24, 24, 340, 92))
        draw_text(surf, f.name, 44, 36, 24)
        draw_text(surf, f"Lv{f.level}", 320, 36, 24, anchor="tr")
        hp_bar(surf, 44, 88, 240, self.disp["foe"] or 1)
        st = f.status_tag
        if st:
            draw_text(surf, st, 330, 74, 20, color=(200, 70, 70))
        if self.trainer:
            remaining = len(self.enemies) - self.e_idx - (1 if self.foe.hp <= 0 else 0)
            for i in range(len(self.enemies)):
                cx = 44 + i * 20
                col = (230, 60, 50) if i < remaining else (120, 120, 130)
                pygame.draw.circle(surf, col, (cx, 108), 6)
                pygame.draw.circle(surf, (40, 40, 50), (cx, 108), 6, 1)
        a = self.ally
        panel(surf, (S.WIN_W - 400, S.WIN_H - 130 - 150, 376, 138))
        draw_text(surf, a.name, S.WIN_W - 380, S.WIN_H - 130 - 134, 24)
        draw_text(surf, f"Lv{a.level}", S.WIN_W - 44, S.WIN_H - 130 - 134, 24, anchor="tr")
        hp_bar(surf, S.WIN_W - 380, S.WIN_H - 130 - 74, 260, self.disp["ally"] or 1)
        draw_text(surf, f"{a.hp}/{a.max_hp}", S.WIN_W - 60, S.WIN_H - 130 - 56, 20, anchor="tr")
        st = a.status_tag
        if st:
            draw_text(surf, st, S.WIN_W - 60, S.WIN_H - 130 - 134 + 30, 20, color=(200, 70, 70))
        need = data.exp_to_next(a.level, a.growth)
        cur = a.exp - data.exp_for_level(a.level, a.growth)
        exp_bar(surf, S.WIN_W - 380, S.WIN_H - 130 - 32, 260, cur / need)

        # 场上状态提示
        tags = []
        if self.weather:
            tags.append(WEATHER_CN[self.weather])
        for side, label in (("ally", "我"), ("foe", "敌")):
            sd = self.sides[side]
            if sd["reflect"]:
                tags.append(f"{label}反射壁")
            if sd["light"]:
                tags.append(f"{label}光墙")
            if sd["stealth"]:
                tags.append(f"{label}隐形岩")
            if sd["spikes"]:
                tags.append(f"{label}撒菱")
            if self.vol[side]["leech"]:
                tags.append(f"{label}寄生")
        for i, t in enumerate(tags[:5]):
            draw_text(surf, t, 30 + i * 76, 130, 16, color=(240, 240, 255))

        # 底部文本框与菜单
        self.textbox.draw(surf)
        if self.phase == "menu":
            bx, by = S.WIN_W - 320, S.WIN_H - 130 - 6
            panel(surf, (bx, by, 300, 122), bg=S.C_MENU_BG)
            for i, opt in enumerate((("投球", "逃跑") if self.safari else MENU_OPTS)):
                ox = bx + 30 + (i % 2) * 150
                oy = by + 16 + (i // 2) * 48
                if i == self.menu_idx:
                    cursor_arrow(surf, ox - 18, oy + 15)
                draw_text(surf, opt, ox, oy, 24)
        elif self.phase == "movesel":
            bx, by = 10, S.WIN_H - 136
            panel(surf, (bx, by, 640, 124), bg=S.C_MENU_BG)
            for i, mv in enumerate(self.ally.moves):
                ox = bx + 30 + (i % 2) * 310
                oy = by + 14 + (i // 2) * 50
                if i == self.move_idx:
                    cursor_arrow(surf, ox - 18, oy + 14)
                draw_text(surf, mv.name, ox, oy, 22)
                md = data.MOVES[mv.name]
                col = S.TYPE_COLOR.get(md["type"], (120, 120, 120))
                pygame.draw.rect(surf, col, (ox + 150, oy + 2, 48, 22), border_radius=5)
                draw_text(surf, md["type"], ox + 174, oy + 3, 16, color=S.C_WHITE, shadow=False, anchor="center")
                if mv.pp <= 0:
                    draw_text(surf, "PP0", ox + 206, oy, 18, color=(200, 70, 70))
            md = data.MOVES[self.ally.moves[self.move_idx].name]
            panel(surf, (660, by, S.WIN_W - 672, 124), bg=S.C_MENU_BG)
            col = S.TYPE_COLOR.get(md["type"], (120, 120, 120))
            pygame.draw.rect(surf, col, (676, by + 14, 64, 28), border_radius=6)
            draw_text(surf, md["type"], 708, by + 18, 20, color=S.C_WHITE, shadow=False, anchor="center")
            draw_text(surf, f"PP {self.ally.moves[self.move_idx].pp}/{self.ally.moves[self.move_idx].max_pp}",
                      752, by + 18, 20)
            draw_text(surf, f"威力 {md['power'] or '—'}  命中 {md['acc'] if md['acc'] is not None else '必中'}",
                      676, by + 54, 20)
            eff = self._move_effect_text(md)
            if eff:
                draw_text(surf, eff, 676, by + 86, 16, color=(90, 100, 120))
            draw_text(surf, f"{K.HINT_CANCEL} 返回", S.WIN_W - 90, by + 14, 18, color=(90, 110, 140))
        if self.phase == "party" and self.party_screen:
            self.party_screen.draw(surf, self.game.assets["icons"])
        elif self.phase == "bag" and self.bag_screen:
            self.bag_screen.draw(surf)
        elif self.phase == "learnmove" and self.learn_screen:
            self.learn_screen.draw(surf)

    def _move_effect_text(self, md):
        fx = md.get("fx", {})
        parts = []
        if fx.get("status"):
            parts.append(f"{fx['status'][0]}{fx['status'][1]}%")
        if fx.get("flinch"):
            parts.append(f"畏缩{fx['flinch']}%")
        if fx.get("crit"):
            parts.append("容易击中要害")
        if fx.get("drain"):
            parts.append("吸取")
        if fx.get("recoil"):
            parts.append("反作用力")
        if fx.get("recharge"):
            parts.append("下一回合蓄力")
        if fx.get("multi"):
            parts.append("连续攻击")
        for e in fx.get("stat", []):
            cn = {"atk": "攻击", "def": "防御", "spa": "特攻", "spd": "特防", "spe": "速度", "acc": "命中",
                  "eva": "闪避"}[e["stat"]]
            parts.append(f"{'自身' if e['who'] == 'self' else '对手'}{cn}{'+' if e['d'] > 0 else '-'}{abs(e['d'])}")
        if fx.get("heal"):
            parts.append("回复体力")
        if fx.get("weather"):
            parts.append(WEATHER_CN[fx["weather"]])
        if fx.get("screen"):
            parts.append("反射壁" if fx["screen"] == "reflect" else "光墙")
        if fx.get("protect"):
            parts.append("守住")
        return " ".join(parts[:3])

    def _draw_weather(self, surf, weather, t, subtle=False):
        w, h = S.WIN_W, S.WIN_H - 130
        alpha = 40 if subtle else 90
        ticks = pygame.time.get_ticks()
        if weather == "rain":
            for i in range(40):
                x = (i * 97 + ticks // 2) % w
                y = (i * 53 + ticks) % h
                pygame.draw.line(surf, (170, 200, 255, alpha), (x, y), (x - 4, y + 14), 2)
        elif weather == "sand":
            for i in range(30):
                x = (i * 131 - ticks // 3) % w
                y = (i * 71 + (ticks // 7) * (i % 3)) % h
                pygame.draw.circle(surf, (220, 190, 120, alpha), (x, y), 3)
        elif weather == "hail":
            for i in range(25):
                x = (i * 113 + ticks // 5) % w
                y = (i * 67 + ticks // 2) % h
                pygame.draw.circle(surf, (230, 245, 255, alpha), (x, y), 4)
        elif weather == "sun":
            pygame.draw.circle(surf, (255, 230, 120, alpha), (w - 140, 90), 60, 4)

    # 测试辅助:自动驱动直到需要输入或结束
    def drive_for_test(self, actions):
        """actions: 队列,元素为 ("menu",action) / ("move",idx) / ("bag",item) / ("party",idx) /
        ("learn", forget_idx 或 None)。缺省动作:战斗→第一招。"""
        guard = 0
        while not self.done and guard < 4000:
            guard += 1
            self.update(0.05)
            if self.phase == "menu":
                if actions and actions[0][0] == "menu":
                    self._advance(actions.pop(0)[1])
                elif actions and actions[0][0] == "move":
                    self._advance("fight")
                else:
                    self._advance("fight")
            elif self.phase == "movesel":
                if actions and actions[0][0] == "move":
                    self._advance(("move", actions.pop(0)[1]))
                else:
                    self._advance(("move", 0))
            elif self.phase == "bag" and actions and actions[0][0] == "bag":
                self._advance(actions.pop(0)[1])
            elif self.phase == "party" and actions and actions[0][0] == "party":
                self._advance(actions.pop(0)[1])
            elif self.phase == "party":
                self._advance(None if self.party_screen.mode != "forced" else
                              next((i for i, m in enumerate(self.game.party) if m.hp > 0), None))
            elif self.phase == "learnmove":
                act = actions.pop(0)[1] if actions and actions[0][0] == "learn" else 0
                self._advance(act)
        return self.result


class _FixedRandom:
    """评分用:随机因子恒为 1.0,不触发暴击。"""

    def random(self):
        return 0.99

    def randint(self, a, b):
        return b
