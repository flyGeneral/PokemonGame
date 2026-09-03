"""精灵实例、个体值/能力值、伤害计算、捕获率计算(第四世代公式)。"""
import math
import random

from . import data

STAT_KEYS = ("hp", "atk", "def", "spa", "spd", "spe")
STAT_CN = {"hp": "HP", "atk": "攻击", "def": "防御", "spa": "特攻", "spd": "特防", "spe": "速度"}

STATUS_COLORS = {"中毒": (163, 62, 161), "灼伤": (235, 120, 40), "麻痹": (200, 180, 40), "睡眠": (130, 140, 160)}


def stage_multiplier(stage):
    """能力等级 → 倍率(-6..+6)。"""
    s = max(-6, min(6, stage))
    return (2 + s) / 2 if s >= 0 else 2 / (2 - s)


class Move:
    __slots__ = ("name", "pp", "max_pp")

    def __init__(self, name):
        self.name = name
        self.max_pp = data.MOVES[name]["pp"]
        self.pp = self.max_pp

    @property
    def d(self):
        return data.MOVES[self.name]

    def to_dict(self):
        return {"name": self.name, "pp": self.pp}

    @classmethod
    def from_dict(cls, d):
        m = cls(d["name"])
        m.pp = d.get("pp", m.max_pp)
        return m


class Mon:
    def __init__(self, species, level, ivs=None, nickname=None):
        assert species in data.SPECIES, species
        self.species = species
        self.level = level
        self.nickname = nickname
        self.ivs = list(ivs) if ivs else [random.randint(0, 31) for _ in range(6)]
        self.status = None          # None / 中毒 / 灼伤 / 麻痹 / 睡眠
        self.sleep_turns = 0
        self.exp = data.exp_for_level(level, data.SPECIES[species].get("growth", "medium_fast"))
        self.moves = [Move(n) for n in self.moves_at_level(level)]
        self.recalc(heal=True)

    # ---- 名字/属性 ----
    @property
    def name(self):
        return self.nickname or self.species

    @property
    def types(self):
        return data.SPECIES[self.species]["types"]

    @property
    def growth(self):
        return data.SPECIES[self.species].get("growth", "medium_fast")

    @property
    def base(self):
        return data.SPECIES[self.species]["base"]

    # ---- 能力值(世代四公式,无努力值) ----
    def recalc(self, heal=False):
        b, iv, L = self.base, self.ivs, self.level
        old_hp = getattr(self, "hp", None)
        self.max_hp = (2 * b[0] + iv[0]) * L // 100 + L + 10
        self.stats = {
            "hp": self.max_hp,
            "atk": (2 * b[1] + iv[1]) * L // 100 + 5,
            "def": (2 * b[2] + iv[2]) * L // 100 + 5,
            "spa": (2 * b[3] + iv[3]) * L // 100 + 5,
            "spd": (2 * b[4] + iv[4]) * L // 100 + 5,
            "spe": (2 * b[5] + iv[5]) * L // 100 + 5,
        }
        if heal or old_hp is None:
            self.hp = self.max_hp
        elif old_hp > self.max_hp:
            self.hp = self.max_hp
        else:
            self.hp = old_hp

    def moves_at_level(self, level):
        learnable = [n for lv, n in data.SPECIES[self.species]["learnset"] if lv <= level]
        return learnable[-4:] if learnable else ["撞击"]

    def learnable_new_moves(self, level):
        return [n for lv, n in data.SPECIES[self.species]["learnset"] if lv == level]

    # ---- 经验/升级/进化 ----
    def gain_exp(self, amount):
        """返回 (消息列表, 是否触发进化)。升级学招:多余4招时替换第一招。"""
        msgs = []
        evolve = None
        while self.level < 100 and self.exp + amount >= data.exp_for_level(self.level + 1, self.growth):
            amount -= data.exp_for_level(self.level + 1, self.growth) - self.exp
            self.exp = data.exp_for_level(self.level + 1, self.growth)
            old_hp = self.hp
            self.level += 1
            self.recalc()
            self.hp = min(self.max_hp, self.hp + (self.max_hp - old_hp) + 2)
            msgs.append(f"{self.name}升到了{self.level}级!")
            for mv in self.learnable_new_moves(self.level):
                if len(self.moves) < 4:
                    self.moves.append(Move(mv))
                    msgs.append(f"{self.name}学会了{mv}!")
                else:
                    old = self.moves[0].name
                    self.moves.pop(0)
                    self.moves.append(Move(mv))
                    msgs.append(f"{self.name}忘记了{old},学会了{mv}!")
            evo = data.SPECIES[self.species]["evo"]
            if evo and self.level >= evo[1]:
                evolve = evo[0]
        self.exp += amount
        return msgs, evolve

    def evolve_into(self, new_species):
        old = self.species
        self.species = new_species
        self.recalc()
        new_moves = self.moves_at_level(self.level)
        for n in new_moves:
            if n not in [m.name for m in self.moves]:
                if len(self.moves) < 4:
                    self.moves.append(Move(n))
        return old

    # ---- 状态 ----
    def cure_status(self):
        self.status = None
        self.sleep_turns = 0

    def full_heal(self):
        self.recalc(heal=False)
        self.hp = self.max_hp
        for m in self.moves:
            m.pp = m.max_pp
        self.cure_status()

    @property
    def status_tag(self):
        return {"中毒": "毒", "灼伤": "烧", "麻痹": "麻", "睡眠": "眠"}.get(self.status)

    # ---- 伤害(第四世代) ----
    def battle_stat(self, key, stages):
        v = self.stats[key] * stage_multiplier(stages.get(key, 0))
        if key == "atk":
            pass  # 灼伤减攻在 calc_damage 中处理
        return int(v)

    def calc_damage(self, dfn, move_name, att_stages=None, dfn_stages=None, rng=random):
        att_stages = att_stages or {}
        dfn_stages = dfn_stages or {}
        md = data.MOVES[move_name]
        if md["cat"] == "变化" or not md["power"]:
            return {"damage": 0, "eff": 1.0, "crit": False}
        eff = 1.0 if md.get("typeless") else data.type_multiplier(md["type"], dfn.types)
        if eff == 0:
            return {"damage": 0, "eff": 0.0, "crit": False}
        physical = md["cat"] == "物理"
        a = self.battle_stat("atk" if physical else "spa", att_stages)
        d = dfn.battle_stat("def" if physical else "spd", dfn_stages)
        if physical and self.status == "灼伤":
            a = a // 2
        crit = rng.random() < (1 / 8 if md.get("highcrit") else 1 / 16)
        level_term = 2 * self.level // 5 + 2
        dmg = level_term * md["power"] * a // d // 50 + 2
        if crit:
            dmg *= 2
        stab = 1.5 if md["type"] in self.types else 1.0
        rand = rng.randint(85, 100) / 100
        dmg = int(dmg * stab * eff * rand)
        return {"damage": max(1, dmg), "eff": eff, "crit": crit}

    # ---- 捕获(第四世代) ----
    def catch_shakes(self, ball_rate, rng=random):
        """返回摇动次数,4 = 捕获成功。"""
        rate = data.SPECIES[self.species]["catch_rate"]
        bonus = {"睡眠": 2.0, "中毒": 1.5, "灼伤": 1.5, "麻痹": 1.5}.get(self.status, 1.0)
        a = (3 * self.max_hp - 2 * self.hp) * rate * ball_rate * bonus
        a = int(a // (3 * self.max_hp))
        if a >= 255:
            return 4
        b = int(1048560 / math.sqrt(math.sqrt(16711680 / a)))
        shakes = 0
        for _ in range(4):
            if rng.randint(0, 65535) < b:
                shakes += 1
            else:
                break
        return shakes

    # ---- 序列化 ----
    def to_dict(self):
        return {"species": self.species, "level": self.level, "ivs": self.ivs,
                "exp": self.exp, "hp": self.hp, "status": self.status,
                "moves": [m.to_dict() for m in self.moves], "nickname": self.nickname}

    @classmethod
    def from_dict(cls, d):
        m = cls(d["species"], d["level"], ivs=d.get("ivs"))
        m.exp = d.get("exp", m.exp)
        m.recalc(heal=True)
        m.hp = d.get("hp", m.max_hp)
        m.status = d.get("status")
        m.nickname = d.get("nickname")
        if d.get("moves"):
            m.moves = [Move.from_dict(x) for x in d["moves"]]
        return m

    def __repr__(self):
        return f"<Mon {self.species} Lv{self.level} hp={self.hp}/{self.max_hp}>"


def make_mon(species, level):
    return Mon(species, level)
