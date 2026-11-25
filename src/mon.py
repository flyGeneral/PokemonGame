"""精灵实例:能力值(第四世代公式)、经验/进化、伤害与捕获计算。"""
import math
import random

from . import data

STAT_KEYS = ("hp", "atk", "def", "spa", "spd", "spe")
STAT_CN = {"hp": "HP", "atk": "攻击", "def": "防御", "spa": "特攻", "spd": "特防", "spe": "速度",
           "acc": "命中", "eva": "闪避"}
STATUS_LIST = ("中毒", "剧毒", "灼伤", "麻痹", "睡眠", "冻结")

STATUS_COLORS = {"中毒": (163, 62, 161), "剧毒": (120, 40, 120), "灼伤": (235, 120, 40),
                 "麻痹": (200, 180, 40), "睡眠": (130, 140, 160), "冻结": (150, 200, 240)}


def stage_multiplier(stage):
    """能力等级 → 倍率(-6..+6)。"""
    s = max(-6, min(6, stage))
    return (2 + s) / 2 if s >= 0 else 2 / (2 - s)


def accuracy_multiplier(stages):
    """命中 = 攻方命中等级 − 守方闪避等级(第六世代以前两者共用同一轴)。"""
    return stage_multiplier(stages.get("acc", 0) - stages.get("eva", 0))


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
        m.pp = max(0, min(m.max_pp, d.get("pp", m.max_pp)))
        return m


class Mon:
    def __init__(self, species, level, ivs=None, nickname=None, moves=None, gender=None, held=None):
        assert species in data.SPECIES, species
        self.species = species
        self.level = level
        self.nickname = nickname
        self.ivs = list(ivs) if ivs else [random.randint(0, 31) for _ in range(6)]
        self.status = None          # None / 中毒 / 剧毒 / 灼伤 / 麻痹 / 睡眠 / 冻结
        self.sleep_turns = 0
        self.toxic_counter = 0
        self.gender = gender or ("f" if random.random() < data.SPECIES[species]["female"] else "m")
        self.friendship = data.SPECIES[species].get("friendship", 70)
        self.held = held            # 训练家精灵携带的树果等
        self.exp = data.exp_for_level(level, self.growth)
        names = moves or self.moves_at_level(level)
        self.moves = [Move(n) for n in names]
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

    @property
    def weight(self):
        return data.SPECIES[self.species]["weight"] / 10.0     # kg

    def knows(self, move_name):
        return any(m.name == move_name for m in self.moves)

    # ---- 能力值(世代四公式,无努力值/性格) ----
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
    def gain_exp(self, amount, map_tag=None, party=None):
        """返回 (消息列表, 可进化目标列表, 待决定的新招式列表)。已有 4 招时不自动替换。"""
        msgs = []
        evolve = []
        pending = []
        while self.level < 100 and self.exp + amount >= data.exp_for_level(self.level + 1, self.growth):
            amount -= data.exp_for_level(self.level + 1, self.growth) - self.exp
            self.exp = data.exp_for_level(self.level + 1, self.growth)
            old_hp = self.hp
            self.level += 1
            self.recalc()
            self.hp = min(self.max_hp, self.hp + (self.max_hp - old_hp) + 2)
            self.friendship = min(255, self.friendship + 5)
            msgs.append(f"{self.name}升到了{self.level}级!")
            for mv in self.learnable_new_moves(self.level):
                if len(self.moves) < 4:
                    self.moves.append(Move(mv))
                    msgs.append(f"{self.name}学会了{mv}!")
                else:
                    pending.append(mv)
            evolve.extend(self.evolution_targets(map_tag, party))
            evolve.extend(self.friendship_ready())
        self.exp += amount
        return msgs, evolve, pending

    def learn_move(self, move_name, forget_idx):
        """学习招式;forget_idx 为要忘记的招式下标(None = 不学)。返回提示消息。"""
        if forget_idx is None or forget_idx >= len(self.moves):
            return f"放弃了学习{move_name}。"
        old = self.moves[forget_idx].name
        self.moves[forget_idx] = Move(move_name)
        return f"{self.name}忘记了{old},\n学会了{move_name}!"

    def evolution_targets(self, map_tag=None, party=None):
        """检查当前等级是否满足进化条件。返回去重后的目标列表。"""
        out = []
        party = party if party is not None else [self]
        for e in data.SPECIES[self.species]["evos"]:
            method = e["method"]
            if method == "level":
                if self.level < e["param"]:
                    continue
                if e.get("gender") and e["gender"] != self.gender:
                    continue
                if e.get("stat_cmp"):
                    a, d = self.stats["atk"], self.stats["def"]
                    if {"gt": a > d, "lt": a < d, "eq": a == d}[e["stat_cmp"]] is False:
                        continue
                if e.get("random") and random.random() >= e["random"]:
                    continue
            elif method == "move":
                if not self.knows(e["move"]):
                    continue
            elif method == "friendship":
                continue                     # 亲密度进化只在 battle 层结算(升级瞬间)
            elif method == "map":
                if map_tag != e["map"]:
                    continue
            elif method == "party":
                if not any(m.species == e["party"] for m in party):
                    continue
            else:
                continue
            if e["to"] not in out:
                out.append(e["to"])
        return out

    def friendship_ready(self):
        return [e["to"] for e in data.SPECIES[self.species]["evos"]
                if e["method"] == "friendship" and self.friendship >= 220]

    def item_evolutions(self, item):
        """对精灵使用进化石/道具时的目标。"""
        out = []
        for e in data.SPECIES[self.species]["evos"]:
            if e.get("item") != item:
                continue
            if e.get("gender") and e["gender"] != self.gender:
                continue
            if e["to"] not in out:
                out.append(e["to"])
        return out

    def evolve_into(self, new_species):
        old = self.species
        self.species = new_species
        self.recalc()
        self.friendship = min(255, self.friendship + 10)
        for n in self.moves_at_level(self.level):
            if not self.knows(n) and len(self.moves) < 4:
                self.moves.append(Move(n))
        return old

    # ---- 状态 ----
    def cure_status(self):
        self.status = None
        self.sleep_turns = 0
        self.toxic_counter = 0

    def full_heal(self):
        self.recalc(heal=False)
        self.hp = self.max_hp
        for m in self.moves:
            m.pp = m.max_pp
        self.cure_status()

    @property
    def status_tag(self):
        return {"中毒": "毒", "剧毒": "剧毒", "灼伤": "烧", "麻痹": "麻", "睡眠": "眠", "冻结": "冻"}.get(self.status)

    def status_immune(self, status):
        """第四世代:属性对异常状态的免疫。"""
        t = self.types
        if status == "麻痹":
            return "电" in t
        if status == "灼伤":
            return "火" in t
        if status == "冻结":
            return "冰" in t
        if status in ("中毒", "剧毒"):
            return "毒" in t or "钢" in t
        return False

    # ---- 伤害(第四世代) ----
    def effective_speed(self):
        return int(self.stats["spe"] * (0.25 if self.status == "麻痹" else 1.0))

    def battle_stat(self, key, stages):
        return int(self.stats[key] * stage_multiplier(stages.get(key, 0)))

    def calc_damage(self, dfn, move_name, att_stages=None, dfn_stages=None, rng=random, mods=None):
        """mods: {"power": 倍率, "crit": 强制暴击?, "crit_stage": 暴击等级, "weather": 天气,
        "screen": 0.5/1.0, "double_slap": ...}。返回 {damage, eff, crit}。"""
        att_stages = att_stages or {}
        dfn_stages = dfn_stages or {}
        mods = mods or {}
        md = data.MOVES[move_name]
        if md["cat"] == "变化" or not md["power"]:
            return {"damage": 0, "eff": 1.0, "crit": False}
        eff = 1.0 if (md.get("fx", {}).get("typeless") or mods.get("typeless")) \
            else data.type_multiplier(md["type"], dfn.types)
        if eff == 0:
            return {"damage": 0, "eff": 0.0, "crit": False}
        physical = md["cat"] == "物理"
        a_key, d_key = ("atk", "def") if physical else ("spa", "spd")
        crit_stage = mods.get("crit_stage", 1) + (1 if md.get("fx", {}).get("crit") else 0)
        crit_chance = {1: 1 / 16, 2: 1 / 8, 3: 1 / 4, 4: 1 / 3, 5: 1 / 2}.get(crit_stage, 1 / 2)
        crit = True if mods.get("crit") else rng.random() < crit_chance
        a = self.battle_stat(a_key, att_stages)
        d = dfn.battle_stat(d_key, dfn_stages)
        if crit:                                 # 暴击忽略攻击方负等级与防御方正等级
            a = int(self.stats[a_key] * stage_multiplier(max(0, att_stages.get(a_key, 0))))
            d = int(dfn.stats[d_key] * stage_multiplier(min(0, dfn_stages.get(d_key, 0))))
        if physical and self.status == "灼伤":
            a = a // 2
        power = md["power"] * mods.get("power", 1.0)
        level_term = 2 * self.level // 5 + 2
        dmg = int(int(int(int(level_term * power) * a) / d) / 50) + 2
        if crit:
            dmg *= 2
        stab = 1.5 if (md["type"] in self.types and not md.get("fx", {}).get("typeless")) else 1.0
        rand = rng.randint(85, 100) / 100
        weather = mods.get("weather")
        wmod = 1.0
        if weather == "sun":
            wmod = 1.5 if md["type"] == "火" else 0.5 if md["type"] == "水" else 1.0
        elif weather == "rain":
            wmod = 1.5 if md["type"] == "水" else 0.5 if md["type"] == "火" else 1.0
        dmg = int(int(dmg * stab * eff) * wmod * mods.get("screen", 1.0) * rand)
        return {"damage": max(1, dmg), "eff": eff, "crit": crit}

    # ---- 捕获(第四世代) ----
    def catch_shakes(self, ball_rate, rng=random):
        """返回摇动次数,4 = 捕获成功。ball_rate 已含球种/状态修正。"""
        rate = data.SPECIES[self.species]["catch_rate"]
        bonus = {"睡眠": 2.0, "冻结": 2.0, "中毒": 1.5, "剧毒": 1.5, "灼伤": 1.5, "麻痹": 1.5}.get(self.status, 1.0)
        a = (3 * self.max_hp - 2 * self.hp) * rate * ball_rate * bonus
        a = int(a // (3 * self.max_hp))
        a = min(a, 255)
        if a >= 255:
            return 4
        b = int(1048560 / math.sqrt(math.sqrt(16711680 / max(1, a))))
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
                "moves": [m.to_dict() for m in self.moves], "nickname": self.nickname,
                "gender": self.gender, "friendship": self.friendship}

    @classmethod
    def from_dict(cls, d):
        m = cls(d["species"], d["level"], ivs=d.get("ivs"), nickname=d.get("nickname"),
                gender=d.get("gender"))
        m.exp = d.get("exp", m.exp)
        m.recalc(heal=True)
        m.hp = min(m.max_hp, d.get("hp", m.max_hp))
        m.status = d.get("status")
        m.friendship = d.get("friendship", m.friendship)
        if d.get("moves"):
            m.moves = [Move.from_dict(x) for x in d["moves"]]
        return m

    def __repr__(self):
        return f"<Mon {self.species} Lv{self.level} hp={self.hp}/{self.max_hp}>"


def make_trainer_mon(species, level, moves=None, held=None):
    return Mon(species, level, moves=moves, held=held)
