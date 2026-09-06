"""从 pret/pokediamond 反编译数据 + PokeAPI 官方中文名,生成神奥图鉴数据文件。

产物 src/dex_sinnoh.py 由本脚本生成并提交,游戏构建不依赖网络。
数据来源:
  /tmp/pkdp/personal.json  pokediamond files/poketool/personal(种族值/属性/捕获率/成长率)
  /tmp/pkdp/wotbl.json     升级招式表(DPPt 原作)
  /tmp/pkdp/evo.json       进化表(只取等级进化)
  /tmp/pkdp/species_names.csv、move_names.csv   PokeAPI 官方简中名(lang=12)
  /tmp/pkdp/moves.csv      招式静态数据(当代值,含 GEN4_FIX 第四世代修正)

说明:
- 无法在本引擎表达的招式(变化招未映射、固定伤害、替身类)从学习表中剔除;
  伤害招式默认按"纯伤害"导入(威力/属性/命中/PP 正确,次要效果省略)。
- 图鉴范围:全国 387-493(神奥原生)+ 额外允许表(大岩蛇等)。

用法: python3 tools/gen_sinnoh_dex.py
"""
import csv
import json
import os
import sys

SRC = "/tmp/pkdp"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "dex_sinnoh.py")

# 已在 data.py 手写维护的全国图鉴号(草苗龟等 11 只),生成器跳过
EXISTING_DEX = {25, 74, 75, 387, 388, 390, 391, 393, 394, 396, 399}

TYPE_CN = {
    "NORMAL": "一般", "FIGHTING": "格斗", "FLYING": "飞行", "POISON": "毒", "GROUND": "地面",
    "ROCK": "岩石", "BUG": "虫", "GHOST": "幽灵", "STEEL": "钢", "FIRE": "火", "WATER": "水",
    "GRASS": "草", "ELECTRIC": "电", "PSYCHIC": "超能力", "ICE": "冰", "DRAGON": "龙", "DARK": "恶",
}
CLASS_CN = {1: "变化", 2: "物理", 3: "特殊"}

# 第四世代之后的数值变动回填(招式 id 标识符 → 覆盖字段)
GEN4_FIX = {
    "TACKLE": {"power": 35},
    "THUNDERBOLT": {"power": 95},
    "VOLT_TACKLE": {"power": 80},
}

# 已实现效果的招式(标识符 → 附加 effect/flags);未列出的变化招将被剔除
EFFECT_MAP = {
    # 能力上升(自己)
    "HOWL": {"effect": {"stat": ("atk", 1), "target": "self"}},
    "MEDITATE": {"effect": {"stat": ("atk", 1), "target": "self"}},
    "SWORDS_DANCE": {"effect": {"stat": ("atk", 2), "target": "self"}},
    "AGILITY": {"effect": {"stat": ("spe", 2), "target": "self"}},
    "IRON_DEFENSE": {"effect": {"stat": ("def", 2), "target": "self"}},
    "ROCK_POLISH": {"effect": {"stat": ("spe", 2), "target": "self"}},
    "AMNESIA": {"effect": {"stat": ("spa", 2), "target": "self"}},
    "BARRIER": {"effect": {"stat": ("def", 2), "target": "self"}},
    "DEFENSE_CURL": {"effect": {"stat": ("def", 1), "target": "self"}},
    "WITHDRAW": {"effect": {"stat": ("def", 1), "target": "self"}},
    "HARDEN": {"effect": {"stat": ("def", 1), "target": "self"}},
    "GROWTH": {"effect": {"stat": ("atk", 1), "target": "self"}},          # 第四世代:攻击+1
    "CURSE": {"effect": {"stat": ("atk", 1), "target": "self"}},           # 非幽灵近似
    "BULK_UP": {"effect": {"stat": ("atk", 1), "target": "self"}},         # 近似(实际攻防+1)
    "CALM_MIND": {"effect": {"stat": ("spa", 1), "target": "self"}},       # 近似
    "DRAGON_DANCE": {"effect": {"stat": ("atk", 1), "target": "self"}},    # 近似
    # 能力下降(对手)
    "GROWL": {"effect": {"stat": ("atk", -1), "target": "foe"}},
    "LEER": {"effect": {"stat": ("def", -1), "target": "foe"}},
    "TAIL_WHIP": {"effect": {"stat": ("def", -1), "target": "foe"}},
    "SCARY_FACE": {"effect": {"stat": ("spe", -2), "target": "foe"}},
    "SCREECH": {"effect": {"stat": ("def", -2), "target": "foe"}},
    "STRING_SHOT": {"effect": {"stat": ("spe", -1), "target": "foe"}},
    "CHARM": {"effect": {"stat": ("atk", -2), "target": "foe"}},
    "FAKE_TEARS": {"effect": {"stat": ("spd", -2), "target": "foe"}},
    "METAL_SOUND": {"effect": {"stat": ("spd", -2), "target": "foe"}},
    "KINESIS": {"effect": {"stat": ("spe", -1), "target": "foe"}},
    # 异常状态
    "THUNDER_WAVE": {"effect": {"status": "麻痹", "chance": 100}},
    "STUN_SPORE": {"effect": {"status": "麻痹", "chance": 100}},
    "GLARE": {"effect": {"status": "麻痹", "chance": 100}},
    "SLEEP_POWDER": {"effect": {"status": "睡眠", "chance": 100}},
    "HYPNOSIS": {"effect": {"status": "睡眠", "chance": 100}},
    "SING": {"effect": {"status": "睡眠", "chance": 100}},
    "GRASS_WHISTLE": {"effect": {"status": "睡眠", "chance": 100}},
    "LOVELY_KISS": {"effect": {"status": "睡眠", "chance": 100}},
    "TOXIC": {"effect": {"status": "中毒", "chance": 100}},
    "POISONPOWDER": {"effect": {"status": "中毒", "chance": 100}},
    "POISON_GAS": {"effect": {"status": "中毒", "chance": 100}},
    "WILL_O_WISP": {"effect": {"status": "灼伤", "chance": 100}},
    "ICE_BEAM": {"effect": {"status": "冻结", "chance": 10}},
    "BLIZZARD": {"effect": {"status": "冻结", "chance": 10}},
    "POWDERSNOW": {"effect": {"status": "冻结", "chance": 10}},
    # 伤害+异常/能力
    "EMBER": {"effect": {"status": "灼伤", "chance": 10}},
    "FLAMETHROWER": {"effect": {"status": "灼伤", "chance": 10}},
    "FIRE_BLAST": {"effect": {"status": "灼伤", "chance": 30}},
    "FIRE_FANG": {"effect": {"status": "灼伤", "chance": 10}},
    "THUNDER": {"effect": {"status": "麻痹", "chance": 30}},
    "DISCHARGE": {"effect": {"status": "麻痹", "chance": 30}},
    "SPARK": {"effect": {"status": "麻痹", "chance": 30}},
    "BODY_SLAM": {"effect": {"status": "麻痹", "chance": 30}},
    "LICK": {"effect": {"status": "麻痹", "chance": 30}},
    "DRAGONBREATH": {"effect": {"status": "麻痹", "chance": 30}},
    "POISON_STING": {"effect": {"status": "中毒", "chance": 30}},
    "SLUDGE": {"effect": {"status": "中毒", "chance": 30}},
    "SLUDGE_BOMB": {"effect": {"status": "中毒", "chance": 30}},
    "CROSS_POISON": {"effect": {"status": "中毒", "chance": 10}, "highcrit": True},
    "ICY_WIND": {"effect": {"stat": ("spe", -1), "target": "foe", "chance": 100}},
    "MUD_SHOT": {"effect": {"stat": ("spe", -1), "target": "foe", "chance": 100}},
    "BUBBLE": {"effect": {"stat": ("spe", -1), "target": "foe", "chance": 10}},
    # 吸血
    "ABSORB": {"drain": 0.5},
    "MEGA_DRAIN": {"drain": 0.5},
    "GIGA_DRAIN": {"drain": 0.5},
    "DRAIN_PUNCH": {"drain": 0.5},
    "LEECH_LIFE": {"drain": 0.5},
    # 反作用力
    "TAKE_DOWN": {"recoil": 0.25},
    "DOUBLE_EDGE": {"recoil": 1 / 3},
    "BRAVE_BIRD": {"recoil": 1 / 3},
    "WOOD_HAMMER": {"recoil": 1 / 3},
    "FLARE_BLITZ": {"recoil": 1 / 3},
    "HEAD_SMASH": {"recoil": 0.5},
    # 优先度
    "QUICK_ATTACK": {"priority": 1},
    "MACH_PUNCH": {"priority": 1},
    "BULLET_PUNCH": {"priority": 1},
    "ICE_SHARD": {"priority": 1},
    "SHADOW_SNEAK": {"priority": 1},
    "AQUA_JET": {"priority": 1},
    "VACUUM_WAVE": {"priority": 1},
    "EXTREMESPEED": {"priority": 2},
    # 必中
    "AERIAL_ACE": {"acc": None},
    "SWIFT": {"acc": None},
    "MAGICAL_LEAF": {"acc": None},
    "SHADOW_PUNCH": {"acc": None},
    "FEINT_ATTACK": {"acc": None},
    "SHOCK_WAVE": {"acc": None},
    # 高暴击
    "RAZOR_LEAF": {"highcrit": True},
    "SLASH": {"highcrit": True},
    "LEAF_BLADE": {"highcrit": True},
    "NIGHT_SLASH": {"highcrit": True},
    "SHADOW_CLAW": {"highcrit": True},
    "CROSS_CHOP": {"highcrit": True},
    "KARATE_CHOP": {"highcrit": True},
    "PSYCHO_CUT": {"highcrit": True},
    "STONE_EDGE": {"highcrit": True},
    "CRABHAMMER": {"highcrit": True},
    # 连续攻击(2-5 次)
    "FURY_SWIPES": {"multihit": (2, 5)},
    "FURY_ATTACK": {"multihit": (2, 5)},
    "PIN_MISSILE": {"multihit": (2, 5)},
    "COMET_PUNCH": {"multihit": (2, 5)},
    "DOUBLE_SLAP": {"multihit": (2, 5)},
    "BARRAGE": {"multihit": (2, 5)},
    "BONE_RUSH": {"multihit": (2, 5)},
    "DOUBLE_HIT": {"multihit": (2, 2)},
}

# 无法表达的机制,直接从学习表剔除
FILTER_IDS = {
    "HIDDEN_POWER", "RETURN", "FRUSTRATION", "FLING", "GYRO_BALL", "METAL_BURST",
    "COUNTER", "MIRROR_COAT", "SONICBOOM", "NIGHT_SHADE", "SEISMIC_TOSS", "DRAGON_RAGE",
    "PAIN_SPLIT", "FAKE_OUT", "SUCKER_PUNCH", "PRESENT", "BEAT_UP", "SPIT_UP", "SWALLOW",
    "STOCKPILE", "PAYBACK", "ASSURANCE", "ME_FIRST", "COMET_PUNCH2", "NATURAL_GIFT",
    "TRUMP_CARD", "WRING_OUT", "CRUSH_GRIP", "DOUBLE_EDGE2",
}


def load():
    personal = json.load(open(f"{SRC}/personal.json"))["baseStats"]
    wotbl = json.load(open(f"{SRC}/wotbl.json"))["wotbl"]
    evo = json.load(open(f"{SRC}/evo.json"))["evos"]
    sp_names = {}
    for r in csv.DictReader(open(f"{SRC}/species_names.csv")):
        if r["local_language_id"] == "12":
            sp_names[int(r["pokemon_species_id"])] = r["name"]
    mv_names = {}
    for r in csv.DictReader(open(f"{SRC}/move_names.csv")):
        if r["local_language_id"] == "12":
            mv_names[int(r["move_id"])] = r["name"]
    moves_csv = {}
    for r in csv.DictReader(open(f"{SRC}/moves.csv")):
        moves_csv[int(r["id"])] = r
    # species.h: 标识符 → 全国图鉴号
    id_by_ident = {}
    with open(f"{SRC}/species.h", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#define SPECIES_") and "(" not in line:
                parts = line.split()
                if len(parts) >= 3:
                    id_by_ident[parts[1][len("SPECIES_"):]] = int(parts[2])
    return personal, wotbl, evo, sp_names, mv_names, moves_csv, id_by_ident


def gen_moves(moves_csv, mv_names):
    """第四世代招式静态数据(含 GEN4_FIX 与效果映射),供学习表引用。"""
    out = {}
    for mid, r in moves_csv.items():
        ident = r["identifier"].upper()
        if int(r["generation_id"]) > 4 or ident in FILTER_IDS:
            continue
        cls = CLASS_CN.get(int(r["damage_class_id"]))
        power = int(r["power"]) if r["power"] else None
        acc = int(r["accuracy"]) if r["accuracy"] else None
        if not r["pp"]:                        # 挣扎等特殊招,跳过
            continue
        if power is None and ident not in EFFECT_MAP:   # 无伤害且无映射(忍耐等),跳过
            continue
        pp = int(r["pp"])
        t = TYPE_CN.get(int(r["type_id"]), "一般")
        entry = {"type": t, "cat": cls, "power": power, "acc": acc, "pp": pp}
        prio = int(r["priority"] or 0)
        if prio:
            entry["priority"] = prio
        fix = GEN4_FIX.get(ident)
        if fix:
            entry.update(fix)
        eff = EFFECT_MAP.get(ident)
        if eff:
            for k, v in eff.items():
                if k == "acc":
                    entry["acc"] = None
                else:
                    entry[k] = v
        elif cls == "变化":
            continue                       # 未映射的变化招:剔除
        name = mv_names.get(mid)
        if not name or name in out:
            continue
        out[name] = entry
    return out


def main():
    personal, wotbl, evo, sp_names, mv_names, moves_csv, id_by_ident = load()
    MOVES = gen_moves(moves_csv, mv_names)

    extra_dex = {95: "大岩蛇"}          # 额外允许(道馆队伍用)
    species_out = {}
    skipped = 0
    for dex in list(range(387, 494)) + list(extra_dex):
        if dex in EXISTING_DEX:
            continue
        p = personal[dex] if dex < len(personal) else None
        name = sp_names.get(dex)
        if p is None or not name:
            skipped += 1
            continue
        types = tuple(dict.fromkeys(
            TYPE_CN[t.split("_", 1)[1]] for t in p["types"]
            if t != "TYPE_NORMAL" or all(x == "TYPE_NORMAL" for x in p["types"])))
        moves = []
        ident_by_upper = {r["identifier"].upper().replace("-", "_"): mid
                          for mid, r in moves_csv.items()}
        for m in wotbl[dex]["moves"]:
            mid = ident_by_upper.get(m["move"])
            mv_name = mv_names.get(mid) if mid else None
            if mv_name and mv_name in MOVES and (m["level"], mv_name) not in moves:
                moves.append((m["level"], mv_name))
        moves.sort(key=lambda x: x[0])
        evos = []
        for x in evo[dex]["evos"]:
            if x["method"] == "EVO_LEVEL":
                tid = id_by_ident.get(x["target"])
                tname = sp_names.get(tid)
                if tname:
                    evos.append((tname, x["param"]))
        species_out[name] = {
            "art": f"dex{dex:03d}",
            "types": types,
            "base": (p["hp"], p["atk"], p["def"], p["spatk"], p["spdef"], p["speed"]),
            "catch_rate": p["catchRate"],
            "base_exp": p["expYield"],
            "growth": p["growthRate"].lower(),
            "evo": (evos[0][0], evos[0][1]) if evos else None,
            "learnset": moves,
            "desc": f"全国图鉴 No.{dex}",
        }

    # ---- 输出 ----
    def fmt(d, indent=4):
        pad = " " * indent
        lines = ["{"]
        for k, v in d.items():
            lines.append(f"{pad}{k!r}: {v!r},")
        lines.append(pad[:-indent] + "}")
        return "\n".join(lines)

    with open(OUT, "w", encoding="utf-8") as f:
        f.write('"""神奥图鉴数据(自动生成,勿手改)。\n\n'
                '来源: pret/pokediamond 数据表 + PokeAPI 官方简中名。\n'
                '重新生成: python3 tools/gen_sinnoh_dex.py\n"""\n\n'
                'SINNOH_MOVES = ' + fmt(MOVES) + '\n\n'
                'SINNOH_SPECIES = ' + fmt(species_out) + '\n')
    print(f"招式 {len(MOVES)} 个,精灵 {len(species_out)} 只,跳过 {skipped}。输出 {OUT}")


if __name__ == "__main__":
    sys.exit(main())
