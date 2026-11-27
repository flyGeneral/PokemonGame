"""生成第四世代(钻石/珍珠)全部数据模块。

输入(由 tools/fetch_sinnoh_sources.py 抓取到 /tmp/pkdp):
  pd/files/poketool/{personal,waza,trainer}/*.json   精灵/招式/训练家
  pd/files/fielddata/encountdata/{d,p}_enc_data      钻石/珍珠二进制遭遇表(NARC,每文件 106 个 u32)
  pd/files/itemtool/itemdata/item_data.json          道具价格/分类/效果
  pd/arm9/src/itemtool.c                             TM/HM → 招式表
  pd/include/constants/{species,moves,trainers,trainer_classes}.h
  xz_text/*.json                                      Xzonn 汉化文本(官方译名体系)
  {move_names,pokemon_species_names}.csv              PokeAPI 官方简中名(优先于汉化文本)
  pokemon.csv                                         体重
  sinnoh_encounters.json                              PokeAPI location-area(遭遇表↔道路对齐)

输出: src/data_dex.py  src/data_moves.py  src/data_items.py  src/data_encounters.py  src/data_trainers.py

用法: python3 tools/fetch_sinnoh_sources.py && python3 tools/gen_sinnoh_data.py
"""
import csv
import glob
import json
import os
import re
import struct
import sys
from collections import Counter

DST = "/tmp/pkdp"
PD = os.path.join(DST, "pd")
XZ = os.path.join(DST, "xz_text")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")

# ---------------------------------------------------------------- 常量
TYPE_CN = {"NORMAL": "一般", "FIGHTING": "格斗", "FLYING": "飞行", "POISON": "毒", "GROUND": "地面",
           "ROCK": "岩石", "BUG": "虫", "GHOST": "幽灵", "STEEL": "钢", "FIRE": "火", "WATER": "水",
           "GRASS": "草", "ELECTRIC": "电", "PSYCHIC": "超能力", "ICE": "冰", "DRAGON": "龙", "DARK": "恶"}
CLASS_CN = {"CLASS_PHYSICAL": "物理", "CLASS_SPECIAL": "特殊", "CLASS_STATUS": "变化"}
GROWTH = {"MEDIUM_FAST": "medium_fast", "MEDIUM_SLOW": "medium_slow", "FAST": "fast",
          "SLOW": "slow", "ERRATIC": "erratic", "FLUCTUATING": "fluctuating"}
UNSUPPORTED = object()

# 自定义道具:原作的通讯/夜间/美丽度条件在单机复刻中用道具替代
LINK_CABLE = "连线电缆"
PRISM_SCALE = "美丽鳞片"

# 奖金(每级):按训练家职业
PRIZE_BY_CLASS = {
    "LEADER_": 100, "ELITE_FOUR": 140, "CHAMPION": 230, "GALACTIC_BOSS": 120, "COMMANDER": 100,
    "GALACTIC": 40, "PKMN_TRAINER_BARRY": 60, "ACE_TRAINER": 60, "VETERAN": 60, "BLACK_BELT": 48,
    "BATTLE_GIRL": 48, "DRAGON_TAMER": 48, "POKEFAN": 200, "RICH_BOY": 200, "LADY": 200, "GENTLEMAN": 200,
    "HIKER": 36, "FISHERMAN": 36, "SAILOR": 36, "RUIN_MANIAC": 36, "COLLECTOR": 40, "PIRATE": 40,
    "NINJA_BOY": 28, "YOUNGSTER": 32, "LASS": 32, "BUG_CATCHER": 28, "CAMPER": 32, "PICNICKER": 32,
    "SCHOOL_KID": 32, "TWINS": 16, "AROMA_LADY": 48, "BEAUTY": 48, "JOGGER": 36, "TUBER": 28,
}
DEFAULT_PRIZE = 40

STARTER_DESC = {
    "草苗龟": "头顶的小苗会感应阳光的方向微微转动。",
    "小火焰猴": "屁股上的火苗是它活力的来源。",
    "波加曼": "骄傲的企鹅,把倔强劲儿都写在脸上。",
}


def st(who, stat, d, chance=100):
    return {"stat": [{"who": who, "stat": stat, "d": d, "chance": chance}]}


def sts(*pairs, who="self", chance=100):
    return {"stat": [{"who": who, "stat": s, "d": d, "chance": chance} for s, d in pairs]}


def status(s, chance):
    return {"status": [s, chance]}


# MOVE_EFFECT_* → fx 字典(callable 接收 effectChance);UNSUPPORTED = 引擎无法表达,从数据中剔除
EFFECT_FX = {
    "NORMAL_HIT": {}, "PRIORITY_HIT": {}, "ALWAYS_HIT": {}, "TRAP_HIT": {}, "STEAL_ITEM": {},
    "FLINCH_HIT": lambda c: {"flinch": c},
    "HIGH_CRIT": {"crit": 1},
    "MULTIHIT_2_5": {"multi": [2, 5]},
    "PARALYZE_HIT": lambda c: status("麻痹", c),
    "SPDEF_DOWN_HIT": lambda c: st("foe", "spd", -1, c),
    "SLEEP": status("睡眠", 100),
    "CONFUSE_HIT": lambda c: {"confuse": c},
    "HIT_RECHARGE": {"recharge": 1},
    "BURN_HIT": lambda c: status("灼伤", c),
    "POISON_HIT": lambda c: status("中毒", c),
    "SPEED_DOWN_HIT": lambda c: st("foe", "spe", -1, c),
    "DRAIN_HP": {"drain": 0.5},
    "RESTORE_HP": {"heal": 0.5},
    "ACCURACY_DOWN_HIT": lambda c: st("foe", "acc", -1, c),
    "OHKO": {"ohko": 1},
    "ACCURACY_DOWN": st("foe", "acc", -1),
    "DEFENSE_DOWN_HIT": lambda c: st("foe", "def", -1, c),
    "HIT_USER_SPATK_2_DOWN": lambda c: st("self", "spa", -2, c),
    "FREEZE_HIT": lambda c: status("冻结", c),
    "DOUBLE_HIT": {"multi": 2},
    "RAMPAGE": {},
    "RECOIL_HIT_HARD": {"recoil": 1 / 3},
    "CONFUSE": {"confuse": 100},
    "PARALYZE": status("麻痹", 100),
    "ATTACK_UP": sts(("atk", 1)),
    "DEFENSE_2UP": sts(("def", 2)),
    "PREVENT_ESCAPE": UNSUPPORTED,
    "RESTORE_HP_DAYTIME": {"heal": 0.5},
    "STATS_UP_HIT": lambda c: sts(("atk", 1), ("def", 1), ("spa", 1), ("spd", 1), ("spe", 1), chance=c),
    "SWITCH_FOE": {"roar": 1},
    "JUMP_KICK": {"crash": 0.5},
    "RECOIL_HIT": {"recoil": 0.25},
    "DEFENSE_DOWN": st("foe", "def", -1),
    "STRONGER_HEAVIER": {"dyn": "weight"},
    "LEVEL_DAMAGE": {"fixed": "level"},
    "POISON": status("中毒", 100),
    "SPEED_2UP": sts(("spe", 2)),
    "DEFENSE_UP": sts(("def", 1)),
    "EXPLOSION": {"faint_user": 1},
    "ENSURE_NEXT_HIT": UNSUPPORTED,
    "BURN_HIT_THAW": lambda c: status("灼伤", c),
    "STRONGER_LOW_HP": {"dyn": "hp_low"},
    "SPEED_2DOWN": st("foe", "spe", -2),
    "PROTECT": {"protect": 1},
    "IDENTIFY": st("foe", "eva", -1),
    "ATTACK_2DOWN": st("foe", "atk", -2),
    "INCREASING_HIT": {},
    "HEAL_ALL_STATUS": {"cure": "party"},
    "ATTACK_UP_HIT": lambda c: st("self", "atk", 1, c),
    "HIT_LATER": {},
    "SWAP_ITEMS": UNSUPPORTED,
    "REVENGE": {"dyn": "revenge"},
    "STRONGER_HIGH_HP": {"dyn": "hp_high"},
    "SPATK_2UP": sts(("spa", 2)),
    "SPDEF_2DOWN": st("foe", "spd", -2),
    "DEFENSE_SPDEF_UP": sts(("def", 1), ("spd", 1)),
    "POISON_HIT_HIGH_CRIT": lambda c: {"crit": 1, "status": ["中毒", c]},
    "BUG_BITE": {},
    "CRUSH_GRIP": {"dyn": "hp_high"},
    "PAYDAY": {"payday": 1},
    "RAZOR_WIND": {},
    "ATTACK_2UP": sts(("atk", 2)),
    "GUST": {},
    "FLY": {},
    "STOMP": {"flinch": 30},
    "POISON_DOUBLE_HIT": {"multi": 2, "status": ["中毒", 20]},
    "ATTACK_DOWN": st("foe", "atk", -1),
    "FIXED_20": {"fixed": 20},
    "FIXED_40": {"fixed": 40},
    "DISABLE": UNSUPPORTED,
    "MIST": UNSUPPORTED,
    "SURF": {},
    "BLIZZARD": lambda c: status("冻结", c),
    "ATTACK_DOWN_HIT": lambda c: st("foe", "atk", -1, c),
    "COUNTER": UNSUPPORTED,
    "LEECH_SEED": {"leech": 1},
    "ACUPRESSURE": UNSUPPORTED,
    "ASSIST": UNSUPPORTED,
    "ASSURANCE": {"dyn": "assurance"},
    "ATTACK_DEFENSE_DOWN": sts(("atk", -1), ("def", -1), who="foe"),
    "ATTACK_DEFENSE_UP": sts(("atk", 1), ("def", 1)),
    "ATTACK_SPEED_UP": sts(("atk", 1), ("spe", 1)),
    "ATTRACT": UNSUPPORTED,
    "BATON_PASS": UNSUPPORTED,
    "BEAT_UP": UNSUPPORTED,
    "BELLY_DRUM": UNSUPPORTED,
    "BIDE": UNSUPPORTED,
    "BOUNCE": {},
    "BRICK_BREAK": {"break_screen": 1},
    "BRINE": {"dyn": "brine"},
    "BURN": status("灼伤", 100),
    "BURN_HIT_HIGH_CRIT": lambda c: {"crit": 1, "status": ["灼伤", c]},
    "CAMOUFLAGE": UNSUPPORTED,
    "CAPTIVATE": UNSUPPORTED,
    "CHARGE": sts(("spd", 1)),
    "CHARGE_BEAM": lambda c: st("self", "spa", 1, c),
    "CHATTER": {},
    "CLOSE_COMBAT": sts(("def", -1), ("spd", -1)),
    "CONVERSION": UNSUPPORTED,
    "CONVERSION_2": UNSUPPORTED,
    "COPYCAT": UNSUPPORTED,
    "CRIT_CHANCE_UP": {"crit_up": 1},
    "CURSE": sts(("atk", 1), ("def", 1), ("spe", -1)),
    "DEFENSE_2DOWN": st("foe", "def", -2),
    "DEFENSE_CURL": sts(("def", 1)),
    "DEFENSE_UP_HIT": lambda c: st("self", "def", 1, c),
    "DEFOG": {"stat": [{"who": "foe", "stat": "eva", "d": -1, "chance": 100}], "break_screen": 1},
    "DESTINY_BOND": UNSUPPORTED,
    "DIG": {},
    "DIVE": {},
    "DREAM_EATER": {"dream": 1},
    "EARTHQUAKE": {},
    "EMBARGO": UNSUPPORTED,
    "ENCORE": UNSUPPORTED,
    "ENDEAVOR": UNSUPPORTED,
    "ENDURE": UNSUPPORTED,
    "EVASION_DOWN": st("foe", "eva", -1),
    "EVASION_UP": sts(("eva", 1)),
    "FACADE": {"dyn": "facade"},
    "FAKE_OUT": {"first_turn": 1, "flinch": 100},
    "FALSE_SWIPE": {"false_swipe": 1},
    "FEINT": {},
    "FIRE_FANG": lambda c: {"flinch": 10, "status": ["灼伤", c]},
    "FLARE_BLITZ": lambda c: {"recoil": 1 / 3, "status": ["灼伤", c]},
    "FLATTER": {"stat": [{"who": "foe", "stat": "atk", "d": 2, "chance": 100}], "confuse": 100},
    "FLING": UNSUPPORTED,
    "FOCUS_PUNCH": {"focus": 1},
    "FOLLOW_ME": UNSUPPORTED,
    "FREEZE_HIT": lambda c: status("冻结", c),
    "FRUSTRATION": {"dyn": "return"},
    "FURY_CUTTER": {},
    "GASTRO_ACID": UNSUPPORTED,
    "GRAVITY": UNSUPPORTED,
    "GRUDGE": UNSUPPORTED,
    "GUARD_SWAP": UNSUPPORTED,
    "GYRO_BALL": {"dyn": "gyro"},
    "HAIL": {"weather": "hail"},
    "HAMMER_ARM": sts(("spe", -1)),
    "HEAD_SMASH": {"recoil": 0.5},
    "HEALING_WISH": UNSUPPORTED,
    "HEAL_BLOCK": UNSUPPORTED,
    "HEART_SWAP": UNSUPPORTED,
    "HELPING_HAND": UNSUPPORTED,
    "HIDDEN_POWER": {"dyn": "hidden"},
    "ICE_FANG": lambda c: {"flinch": 10, "status": ["冻结", c]},
    "IMPRISON": UNSUPPORTED,
    "INGRAIN": {"ingrain": 1},
    "JUDGMENT": {},
    "KNOCK_OFF": {},
    "LAST_RESORT": UNSUPPORTED,
    "LIGHT_SCREEN": {"screen": "light"},
    "LUCKY_CHANT": UNSUPPORTED,
    "LUNAR_DANCE": UNSUPPORTED,
    "MAGIC_COAT": UNSUPPORTED,
    "MAGNET_RISE": UNSUPPORTED,
    "MAGNITUDE": {"dyn": "magnitude"},
    "MEMENTO": UNSUPPORTED,
    "METAL_BURST": UNSUPPORTED,
    "METRONOME": UNSUPPORTED,
    "ME_FIRST": UNSUPPORTED,
    "MIMIC": UNSUPPORTED,
    "MINIMIZE": sts(("eva", 2)),
    "MIRACLE_EYE": UNSUPPORTED,
    "MIRROR_COAT": UNSUPPORTED,
    "MIRROR_MOVE": UNSUPPORTED,
    "MUD_SPORT": UNSUPPORTED,
    "NATURAL_GIFT": UNSUPPORTED,
    "NATURE_POWER": UNSUPPORTED,
    "NIGHTMARE": UNSUPPORTED,
    "NONE": UNSUPPORTED,                       # 跃起
    "PAIN_SPLIT": UNSUPPORTED,
    "PAYBACK": {"dyn": "revenge"},
    "PERISH_SONG": UNSUPPORTED,
    "POWER_SWAP": UNSUPPORTED,
    "POWER_TRICK": UNSUPPORTED,
    "PRESENT": UNSUPPORTED,
    "PSYCHO_SHIFT": UNSUPPORTED,
    "PSYCH_UP": UNSUPPORTED,
    "PUNISHMENT": UNSUPPORTED,
    "PURSUIT": {},
    "RAGE": {},
    "RAIN": {"weather": "rain"},
    "RAPID_SPIN": {"spin": 1},
    "RECYCLE": UNSUPPORTED,
    "REFLECT": {"screen": "reflect"},
    "REFRESH": {"cure": "self"},
    "RETURN": {"dyn": "return"},
    "ROLE_PLAY": UNSUPPORTED,
    "ROOST": {"heal": 0.5},
    "SAFEGUARD": {"safeguard": 1},
    "SANDSTORM": {"weather": "sand"},
    "SECRET_POWER": lambda c: status("麻痹", c),
    "SEED_FLARE": lambda c: st("foe", "spd", -2, c),
    "SHADOW_FORCE": {},
    "SKETCH": UNSUPPORTED,
    "SKILL_SWAP": UNSUPPORTED,
    "SKULL_BASH": {},
    "SKY_ATTACK": lambda c: {"flinch": c},
    "SKY_UPPERCUT": {},
    "SLEEP_TALK": UNSUPPORTED,
    "SLEEP_USER": {"rest": 1},
    "SMELLING_SALTS": {"salts": 1},
    "SNATCH": UNSUPPORTED,
    "SNORE": {},
    "SOLAR_BEAM": {},
    "SPATK_DOWN_HIT": lambda c: st("foe", "spa", -1, c),
    "SPATK_SPDEF_UP": sts(("spa", 1), ("spd", 1)),
    "SPATK_UP": sts(("atk", 1)),                # 第四世代生长:攻击+1
    "SPDEF_2UP": sts(("spd", 2)),
    "SPDEF_DOWN_HIT": lambda c: st("foe", "spd", -1, c),
    "SPEED_DOWN": st("foe", "spe", -1),
    "SPIKES": {"hazard": "spikes"},
    "SPITE": UNSUPPORTED,
    "SPIT_UP": UNSUPPORTED,
    "STATS_RESET": {"reset": 1},
    "STEALTH_ROCK": {"hazard": "stealth"},
    "STOCKPILE": UNSUPPORTED,
    "STRUGGLE": {"typeless": 1, "recoil": 0.25},
    "SUBSTITUTE": UNSUPPORTED,
    "SUCKER_PUNCH": {},
    "SUNNY": {"weather": "sun"},
    "SUPERPOWER": sts(("atk", -1), ("def", -1)),
    "SUPER_FANG": {"super_fang": 1},
    "SWAGGER": {"stat": [{"who": "foe", "stat": "atk", "d": 2, "chance": 100}], "confuse": 100},
    "SWALLOW": UNSUPPORTED,
    "TAILWIND": UNSUPPORTED,
    "TAUNT": UNSUPPORTED,
    "TELEPORT": UNSUPPORTED,
    "THUNDER": lambda c: status("麻痹", c),
    "THUNDER_FANG": lambda c: {"flinch": 10, "status": ["麻痹", c]},
    "TORMENT": UNSUPPORTED,
    "TOXIC": status("剧毒", 100),
    "TOXIC_HIT": lambda c: status("剧毒", c),
    "TOXIC_SPIKES": {"hazard": "tspikes"},
    "TRANSFORM": UNSUPPORTED,
    "TRICK_ROOM": UNSUPPORTED,
    "TRIPLE_KICK": {"multi": 3},
    "TRI_ATTACK": {"tri": 20},
    "TRUMP_CARD": UNSUPPORTED,
    "TWISTER": lambda c: {"flinch": 20},
    "UPROAR": {},
    "U_TURN": {},
    "VITAL_THROW": {},
    "VOLT_TACKLE": lambda c: {"recoil": 1 / 3, "status": ["麻痹", c]},
    "WAKE_UP_SLAP": {"wake_slap": 1},
    "WATER_SPORT": UNSUPPORTED,
    "WEATHER_BALL": {},
    "WHIRLPOOL": {},
    "WISH": UNSUPPORTED,
    "WORRY_SEED": UNSUPPORTED,
    "YAWN": UNSUPPORTED,
    "AQUA_RING": {"aquaring": 1},
}

# 进化方式 → 引擎方法
EVO_METHOD = {
    "EVO_LEVEL": "level", "EVO_LEVEL_FEMALE": "level", "EVO_LEVEL_MALE": "level",
    "EVO_LEVEL_ATK_GT_DEF": "level", "EVO_LEVEL_ATK_LT_DEF": "level", "EVO_LEVEL_ATK_EQ_DEF": "level",
    "EVO_LEVEL_PID_LO": "level", "EVO_LEVEL_PID_HI": "level", "EVO_LEVEL_NINJASK": "level",
    "EVO_LEVEL_SHEDINJA": "level", "EVO_HAS_MOVE": "move", "EVO_FRIENDSHIP": "friendship",
    "EVO_FRIENDSHIP_DAY": "friendship", "EVO_FRIENDSHIP_NIGHT": "friendship",
    "EVO_CORONET": "map", "EVO_ETERNA": "map", "EVO_ROUTE217": "map",
    "EVO_STONE": "item", "EVO_STONE_MALE": "item", "EVO_STONE_FEMALE": "item",
    "EVO_TRADE": "item", "EVO_TRADE_ITEM": "item", "EVO_ITEM_NIGHT": "item", "EVO_ITEM_DAY": "item",
    "EVO_BEAUTY": "item", "EVO_OTHER_PARTY_MON": "party",
}
MAP_TAG = {"EVO_CORONET": "coronet", "EVO_ETERNA": "eterna_forest", "EVO_ROUTE217": "route217"}

BALL_RATE = {
    "ITEM_POKE_BALL": 1.0, "ITEM_GREAT_BALL": 1.5, "ITEM_ULTRA_BALL": 2.0, "ITEM_MASTER_BALL": 255.0,
    "ITEM_NET_BALL": "net", "ITEM_DIVE_BALL": "dive", "ITEM_NEST_BALL": "nest", "ITEM_REPEAT_BALL": "repeat",
    "ITEM_TIMER_BALL": "timer", "ITEM_QUICK_BALL": "quick", "ITEM_DUSK_BALL": "dusk", "ITEM_HEAL_BALL": "heal",
    "ITEM_PREMIER_BALL": 1.0, "ITEM_LUXURY_BALL": 1.0, "ITEM_CHERISH_BALL": 1.0, "ITEM_SAFARI_BALL": 1.5,
}
BALL_DESC = {"net": "对水系/虫系的野生精灵捕获率更高", "dive": "在水上或钓鱼时捕获率更高",
             "nest": "对手等级越低越容易捕捉", "repeat": "对已捕获过的种类更有效",
             "timer": "回合数越多越有效", "quick": "战斗第一回合特别有效", "dusk": "在洞窟里特别有效",
             "heal": "捕获后自动恢复该精灵的体力并治愈异常状态"}
MEDICINE = {  # ident → (kind, param)
    "ITEM_POTION": ("heal", 20), "ITEM_SUPER_POTION": ("heal", 50), "ITEM_HYPER_POTION": ("heal", 200),
    "ITEM_MAX_POTION": ("heal", 9999), "ITEM_FULL_RESTORE": ("fullheal", None),
    "ITEM_ANTIDOTE": ("cure", "中毒"), "ITEM_PARLYZ_HEAL": ("cure", "麻痹"), "ITEM_AWAKENING": ("cure", "睡眠"),
    "ITEM_BURN_HEAL": ("cure", "灼伤"), "ITEM_ICE_HEAL": ("cure", "冻结"), "ITEM_FULL_HEAL": ("cure", "all"),
    "ITEM_REVIVE": ("revive", 0.5), "ITEM_MAX_REVIVE": ("revive", 1.0),
    "ITEM_ENERGY_POWDER": ("heal", 120), "ITEM_ENERGY_ROOT": ("heal", 200), "ITEM_HEAL_POWDER": ("cure", "all"),
    "ITEM_REVIVAL_HERB": ("revive", 1.0),
    "ITEM_ETHER": ("pp", 10), "ITEM_MAX_ETHER": ("pp", 9999), "ITEM_ELIXIR": ("ppall", 10),
    "ITEM_MAX_ELIXIR": ("ppall", 9999),
    "ITEM_X_ATTACK": ("stat", "atk"), "ITEM_X_DEFENSE": ("stat", "def"),
    "ITEM_X_SP_ATK": ("stat", "spa"), "ITEM_X_SP_DEF": ("stat", "spd"),
    "ITEM_X_SPEED": ("stat", "spe"), "ITEM_X_ACCURACY": ("stat", "acc"),
    "ITEM_DIRE_HIT": ("crit", 1),
}
MED_DESC = {"heal": "恢复{}点HP", "fullheal": "恢复全部HP并治愈异常状态", "cure": "治愈{}",
            "revive": "让濒死的精灵复苏并恢复{}HP", "pp": "恢复一个招式{}点PP", "ppall": "恢复全部招式{}PP",
            "stat": "战斗中提高自己的能力等级", "crit": "战斗中更容易击中要害"}
EVOLUTION_ITEMS = {
    "ITEM_THUNDERSTONE", "ITEM_FIRE_STONE", "ITEM_WATER_STONE", "ITEM_LEAF_STONE", "ITEM_MOON_STONE",
    "ITEM_SUN_STONE", "ITEM_SHINY_STONE", "ITEM_DUSK_STONE", "ITEM_DAWN_STONE", "ITEM_KINGS_ROCK",
    "ITEM_METAL_COAT", "ITEM_DRAGON_SCALE", "ITEM_PROTECTOR", "ITEM_ELECTIRIZER", "ITEM_MAGMARIZER",
    "ITEM_UPGRADE", "ITEM_DUBIOUS_DISC", "ITEM_REAPER_CLOTH", "ITEM_RAZOR_FANG", "ITEM_RAZOR_CLAW",
    "ITEM_OVAL_STONE",
}
KEY_ITEMS = {
    "ITEM_OLD_ROD": "rod_old", "ITEM_GOOD_ROD": "rod_good", "ITEM_SUPER_ROD": "rod_super",
    "ITEM_EXP__SHARE": "exp_share", "ITEM_BICYCLE": "bicycle", "ITEM_VS__SEEKER": "vs_seeker",
    "ITEM_TOWN_MAP": "town_map",
}
KEY_DESC = {"rod_old": "面对水面使用,能钓到野生精灵", "rod_good": "比破旧钓竿更容易钓到好东西",
            "rod_super": "最厉害的钓竿", "exp_share": "带着它的精灵即使不出战也能分得经验值",
            "bicycle": "骑上它能更快地移动(本作按住 B/Shift 即可跑步)",
            "vs_seeker": "可以让打败过的训练家再次对战", "town_map": "神奥地区的地图",
            "escape_rope": "使用后立刻离开洞窟或水路,回到最近的精灵中心"}
REPELS = {"ITEM_REPEL": 100, "ITEM_SUPER_REPEL": 200, "ITEM_MAX_REPEL": 250}   # 步数取自 item_data 的 holdEffectParam

GRASS_W = [20, 20, 10, 10, 10, 10, 5, 5, 5, 4, 4, 1]
WATER_W = [60, 30, 5, 4, 1]


# ---------------------------------------------------------------- 工具
def load(path):
    return json.load(open(path, encoding="utf-8"))


def pd_json(rel):
    return load(os.path.join(PD, "files", rel))


def xz(bank):
    return {r["index"]: r["translation"].strip() for r in load(os.path.join(XZ, bank + ".json"))}


def csv_lang12(name, key_field):
    out = {}
    with open(os.path.join(DST, name), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["local_language_id"] == "12":
                out[int(r[key_field])] = r["name"].strip()
    return out


def fmt_py(obj, indent=0):
    """紧凑且可读的 Python 字面量。"""
    pad = " " * indent
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        items = [f"{pad}    {k!r}: {fmt_py(v, indent + 4)}," for k, v in obj.items()]
        return "{\n" + "\n".join(items) + f"\n{pad}}}"
    if isinstance(obj, (list, tuple)):
        if isinstance(obj, tuple) and obj:
            return "(" + ", ".join(fmt_py(v, indent) for v in obj) + ("," if len(obj) == 1 else "") + ")"
        return "[" + ", ".join(fmt_py(v, indent) for v in obj) + "]"
    return repr(obj)


def write_module(fname, doc, variables):
    out = [f'"""{doc}"""', ""]
    for name, value in variables:
        out.append(f"{name} = {fmt_py(value)}")
        out.append("")
    path = os.path.join(SRC, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(f"  写入 src/{fname} ({os.path.getsize(path) // 1024} KB)")


def defines(path, prefix):
    """constants/*.h 的 #define → {编号: 标识符}。"""
    out = {}
    for line in open(path, encoding="utf-8"):
        m = re.match(rf"#define\s+{prefix}(\w+)\s+(\d+)\s*$", line)
        if m:
            out[int(m.group(2))] = m.group(1)
    return out


def item_names(names):
    """ITEM_* 标识符 → 中文名(道具编号以 include/constants/items.h 为准,与文本表索引一致)。"""
    enum = defines(os.path.join(PD, "include/constants/items.h"), "ITEM_")
    return {"ITEM_" + ident: names["item"].get(i) for i, ident in enum.items()}


# ---------------------------------------------------------------- 名称
def load_names():
    mv_xz, sp_xz = xz("wazaname"), xz("monsname")
    mv_official = csv_lang12("move_names.csv", "move_id")
    sp_official = csv_lang12("pokemon_species_names.csv", "pokemon_species_id")
    return {
        "move": {i: mv_official.get(i) or mv_xz.get(i) for i in set(mv_xz) | set(mv_official)},
        "mon": {i: sp_official.get(i) or sp_xz.get(i) for i in set(sp_xz) | set(sp_official)},
        "item": xz("itemname"), "trname": xz("trname"), "trtype": xz("trtype"),
    }


# ---------------------------------------------------------------- 招式
def gen_moves(names):
    waza = pd_json("poketool/waza/waza_tbl.json")["waza_tbl"]
    moves, by_id, unsupported = {}, {}, []
    for mid, m in enumerate(waza):
        if mid == 0 or mid > 467:
            continue
        ident = m["name"].replace("MOVE_", "")
        cn = names["move"].get(mid)
        if not cn or cn in ("?", "ー"):
            unsupported.append(ident)
            continue
        effect = m["effect"].replace("MOVE_EFFECT_", "")
        fx_def = EFFECT_FX.get(effect, UNSUPPORTED)
        if fx_def is UNSUPPORTED:
            unsupported.append(ident)
            continue
        fx = fx_def(m["effectChance"]) if callable(fx_def) else dict(fx_def)
        cat = CLASS_CN[m["class"]]
        if cat == "变化" and not fx:
            unsupported.append(ident)
            continue
        power = m["power"]
        if fx.get("ohko"):
            power = None                 # 一击必杀不使用威力值
        elif fx.get("dyn") == "return":
            power = 102
        elif ident == "HIDDEN_POWER":
            power = 60
        entry = {"type": TYPE_CN.get(m["type"].replace("TYPE_", ""), "一般"), "cat": cat,
                 "power": power if power else None, "acc": m["accuracy"] or None,
                 "pp": m["pp"], "prio": m["priority"]}
        if fx:
            entry["fx"] = fx
        moves[cn] = entry
        by_id[mid] = cn
    return moves, by_id, unsupported


# ---------------------------------------------------------------- 精灵
def gen_dex(names, moves, by_id, items):
    personal = pd_json("poketool/personal/personal.json")["baseStats"]
    wotbl = pd_json("poketool/personal/wotbl.json")["wotbl"]
    evos = pd_json("poketool/personal/evo.json")["evos"]
    growtbl = pd_json("poketool/personal/growtbl.json")["growtbl"]
    ident_to_id = {p["species"]: i for i, p in enumerate(personal)}
    move_ident_id = {v: k for k, v in defines(os.path.join(PD, "include/constants/moves.h"), "MOVE_").items()}
    item_cn = item_names(names)
    weights = {}
    with open(os.path.join(DST, "pokemon.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["is_default"] == "1":
                weights[int(r["species_id"])] = int(float(r["weight"]))      # CSV 单位为 0.1kg
    growth_tables = {GROWTH[g["name"]]: g["table"] for g in growtbl if g["name"] in GROWTH}
    species, by_num, dropped = {}, {}, Counter()

    for sid in range(1, 494):
        p = personal[sid]
        cn = names["mon"].get(sid)
        if not cn:
            continue
        types = tuple(dict.fromkeys(TYPE_CN[t.replace("TYPE_", "")] for t in p["types"]))
        learnset = []
        for mv in wotbl[sid]["moves"]:
            name = by_id.get(move_ident_id.get(mv["move"]))
            if name and (mv["level"], name) not in learnset:
                learnset.append((mv["level"], name))
            elif not name:
                dropped[mv["move"]] += 1
        if not learnset:
            learnset = [(1, "撞击")]
        evo_list = []
        for e in evos[sid]["evos"]:
            method = EVO_METHOD.get(e["method"])
            if not method:
                continue
            target = names["mon"].get(ident_to_id.get(e["target"]))
            if not target:
                continue
            d = {"to": target, "method": method}
            if method == "level":
                d["param"] = e["param"]
                tag = {"EVO_LEVEL_FEMALE": "f", "EVO_LEVEL_MALE": "m"}.get(e["method"])
                if tag:
                    d["gender"] = tag
                cmp = {"EVO_LEVEL_ATK_GT_DEF": "gt", "EVO_LEVEL_ATK_LT_DEF": "lt",
                       "EVO_LEVEL_ATK_EQ_DEF": "eq"}.get(e["method"])
                if cmp:
                    d["stat_cmp"] = cmp
                if e["method"] in ("EVO_LEVEL_PID_LO", "EVO_LEVEL_PID_HI"):
                    d["random"] = 0.5          # 刺尾虫按性格分支:这里随机
                if e["method"] == "EVO_LEVEL_SHEDINJA":
                    d["bonus"] = True
            elif method == "move":
                mv = by_id.get(e["param"])
                if not mv:
                    continue
                d.update(param=1, move=mv)
            elif method == "friendship":
                # 无昼夜:太阳石/月亮石作为伊布、百代蔷薇、铃铛响的替代途径
                if "DAY" in e["method"]:
                    d["item"] = item_cn.get("ITEM_SUN_STONE")
                elif "NIGHT" in e["method"]:
                    d["item"] = item_cn.get("ITEM_MOON_STONE")
            elif method == "map":
                d.update(param=1, map=MAP_TAG[e["method"]])
            elif method == "item":
                if e["method"] == "EVO_TRADE":
                    d["item"] = LINK_CABLE
                elif e["method"] == "EVO_BEAUTY":
                    d["item"] = PRISM_SCALE
                else:
                    d["item"] = item_cn.get(e["param"])
                if not d.get("item") or d["item"] not in items:
                    continue
                tag = {"EVO_STONE_MALE": "m", "EVO_STONE_FEMALE": "f"}.get(e["method"])
                if tag:
                    d["gender"] = tag
            elif method == "party":
                mate = names["mon"].get(ident_to_id.get(e["param"].replace("SPECIES_", "")))
                if not mate:
                    continue
                d.update(param=1, party=mate)
            evo_list.append(d)
        first_level = next((x for x in evo_list if x["method"] == "level" and not x.get("bonus")), None)
        species[cn] = {
            "id": sid, "art": f"dex{sid:03d}", "types": types,
            "base": (p["hp"], p["atk"], p["def"], p["spatk"], p["spdef"], p["speed"]),
            "catch_rate": p["catchRate"], "base_exp": p["expYield"], "growth": GROWTH[p["growthRate"]],
            "weight": weights.get(sid, 300), "female": p["genderRatio"], "friendship": p["friendship"],
            "learnset": learnset, "evos": evo_list,
            "evo": (first_level["to"], first_level["param"]) if first_level else None,
            "tms": list(p["tms"]), "hms": list(p["hms"]),
            "desc": STARTER_DESC.get(cn, f"全国图鉴 No.{sid}"),
        }
        by_num[sid] = cn
    return species, by_num, growth_tables, dropped


# ---------------------------------------------------------------- 道具
def tmhm_table():
    """arm9/src/itemtool.c 的 sTMHMMoves:TM01-92 后接 HM01-08。"""
    src = open(os.path.join(PD, "arm9/src/itemtool.c"), encoding="utf-8").read()
    body = re.search(r"sTMHMMoves\[\]\s*=\s*\{(.*?)\};", src, re.S).group(1)
    return re.findall(r"MOVE_(\w+)", body)


def gen_items(names, moves, by_id, species=None):
    items_data = pd_json("itemtool/itemdata/item_data.json")["item_data"]
    ident_to_id = {v: k for k, v in defines(os.path.join(PD, "include/constants/moves.h"), "MOVE_").items()}
    cn_by_ident = item_names(names)
    tm, hm = {}, {}
    for n, ident in enumerate(tmhm_table(), 1):
        cn = by_id.get(ident_to_id.get(ident))
        if n <= 92:
            tm[n] = cn
        else:
            hm[n - 92] = cn
    items = {}
    for it in items_data:
        ident, price = it["name"], it["price"]
        cn = cn_by_ident.get(ident)
        if not cn or ident == "ITEM_NONE":
            continue
        if ident in BALL_RATE:
            rate = BALL_RATE[ident]
            desc = BALL_DESC.get(rate) or f"用于捕捉野生精灵(捕获率×{rate:g})"
            items[cn] = {"kind": "ball", "rate": rate, "price": price, "desc": desc}
        elif ident in MEDICINE:
            kind, param = MEDICINE[ident]
            txt = "异常状态" if param == "all" else ("全部" if param == 9999 else
                                                   ("一半" if (kind == "revive" and param == 0.5) else param))
            items[cn] = {"kind": kind, "param": param, "price": price, "desc": MED_DESC[kind].format(txt)}
        elif ident in REPELS:
            steps = REPELS[ident]
            items[cn] = {"kind": "repel", "param": steps, "price": price,
                         "desc": f"使用后 {steps} 步之内,不会遇到比队伍首只精灵弱的野生精灵"}
        elif ident == "ITEM_ESCAPE_ROPE":
            items[cn] = {"kind": "key", "key": "escape_rope", "price": price, "desc": KEY_DESC["escape_rope"]}
        elif ident in EVOLUTION_ITEMS:
            targets = [s for s, d in (species or {}).items() if any(e.get("item") == cn for e in d["evos"])]
            desc = f"能让{'/'.join(targets[:3])}进化" if targets else "能让某种精灵进化的道具"
            items[cn] = {"kind": "evo", "price": price, "desc": desc}
        elif ident in KEY_ITEMS:
            items[cn] = {"kind": "key", "key": KEY_ITEMS[ident], "price": 0, "desc": KEY_DESC[KEY_ITEMS[ident]]}
        elif ident.startswith("ITEM_TM") or ident.startswith("ITEM_HM"):
            num = int(ident[-2:])
            is_hm = ident.startswith("ITEM_HM")
            move = hm.get(num) if is_hm else tm.get(num)
            if not move:
                continue
            items[cn] = {"kind": "tm", "move": move, "hm": is_hm, "num": num, "price": price,
                         "desc": f"教会一只精灵「{move}」" + ("(秘传学习器,可反复使用)" if is_hm else "")}
    items["连线电缆"] = {"kind": "evo", "price": 2100, "desc": "能让通讯进化的精灵进化"}
    items["美丽鳞片"] = {"kind": "evo", "price": 3000, "desc": "散发着七色光芒,能让丑丑鱼进化"}
    return items, tm, hm


# ---------------------------------------------------------------- 训练家
def gen_trainers(names, by_num, moves, items):
    tr = pd_json("poketool/trainer/trdata.json")["trdata"]
    item_cn = item_names(names)
    cls_id = defines(os.path.join(PD, "include/constants/trainer_classes.h"), "TRAINER_CLASS_")
    cls_cn = {v: names["trtype"].get(k, "训练家") for k, v in cls_id.items()}
    move_enum = {v: k for k, v in defines(os.path.join(PD, "include/constants/moves.h"), "MOVE_").items()}
    species_enum = {v: k for k, v in defines(os.path.join(PD, "include/constants/species.h"), "SPECIES_").items()}
    trainers = {}
    for t in tr:
        if not t["party"]:
            continue
        cls = t["class"].replace("TRAINER_CLASS_", "")
        party = []
        for pm in t["party"]:
            # species 枚举值即全国图鉴号
            sp = by_num.get(species_enum.get(pm["species"].replace("SPECIES_", "")))
            if not sp:
                continue
            mv = [move_enum and moves and by_id.get(move_enum.get(m.replace("MOVE_", "")))
                  for m in (pm.get("moves") or [])]
            mv = [m for m in mv if m]
            held = item_cn.get(pm.get("item")) if pm.get("item") and pm.get("item") != "ITEM_NONE" else None
            party.append((sp, pm["level"], mv if len(mv) >= 2 else None, held))
        if not party:
            continue
        bag = [item_cn[it] for it in t["items"] if it != "ITEM_NONE" and item_cn.get(it) in items
               and items[item_cn[it]]["kind"] in ("heal", "fullheal", "cure")]
        prize = next((v for k, v in PRIZE_BY_CLASS.items() if cls.startswith(k)), DEFAULT_PRIZE)
        trainers[t["index"]] = {"cls": cls_cn.get(cls, "训练家"), "name": names["trname"].get(t["index"], ""),
                                "party": party, "items": bag, "prize": prize, "raw": cls}
    return trainers


by_id = {}


# ---------------------------------------------------------------- 遭遇
def decode_encounter(path):
    f = struct.unpack("<106I", open(path, "rb").read())

    def lv(v):
        return ((v >> 8) & 0xFF, v & 0xFF)
    return {
        "rate": f[0],
        "grass": [(f[i], f[i + 1]) for i in range(1, 25, 2)],
        "surf": [(lv(f[i]), f[i + 1]) for i in range(52, 62, 2)],
        "rock": [(lv(f[i]), f[i + 1]) for i in range(63, 73, 2)],
        "old": [(lv(f[i]), f[i + 1]) for i in range(74, 84, 2)],
        "good": [(lv(f[i]), f[i + 1]) for i in range(85, 95, 2)],
        "super": [(lv(f[i]), f[i + 1]) for i in range(96, 106, 2)],
    }


def area_key(area):
    k = re.sub(r"^sinnoh-", "", area)
    k = re.sub(r"-area$", "", k)
    k = re.sub(r"-towards-[a-z-]+$", "", k)
    return re.sub(r"[^a-z0-9]+", "_", k).strip("_")


def gen_encounters(by_num):
    """每个 PokeAPI 区域 → 最匹配的二进制文件(方向:区域找文件,避免两个文件抢同一区域)。"""
    cache = load(os.path.join(DST, "sinnoh_encounters.json"))
    raw = {}
    for ver, letter in (("D", "d"), ("P", "p")):
        raw[ver] = [decode_encounter(f) for f in sorted(glob.glob(
            os.path.join(PD, "files/fielddata/encountdata", f"{letter}_enc_data/*.bin")))]
    # PokeAPI 的 walk 集合 = 草丛 + 宝可追踪 + 双插槽 + 大量发生;surf 等方法各自独立
    papi = {}
    for aid, a in cache.items():
        for ver in ("diamond", "pearl"):
            d = papi.setdefault(aid, {}).setdefault(ver, {})
            for e in a["encounters"]:
                if e["version"] != ver:
                    continue
                d.setdefault(e["method"], set()).add(int(e["species_url"].rstrip("/").split("/")[-1]))
    areas = {}
    for aid, a in cache.items():
        k = area_key(a["area"])
        if k in areas:
            continue
        entry = {"name": a["area"]}
        for ver, pv in (("D", "diamond"), ("P", "pearl")):
            per = papi[aid].get(pv, {})
            walk = per.get("walk", set())
            surf = per.get("surf", set())
            cands = []
            for i, dec in enumerate(raw[ver]):
                g = {sp for _, sp in dec["grass"] if sp}
                sf = {sp for _, sp in dec["surf"] if sp}
                if not g and not sf:
                    continue
                ok_g = (not g) or (walk and not (g - walk))
                ok_s = (not sf) or (surf and not (sf - surf))
                if not (g or sf) or not (ok_g and ok_s) or (g and sf and not walk and not surf):
                    continue
                # 要求方向一致:有草丛的区域匹配有草丛的文件
                if bool(walk) != bool(g) and not (surf and sf):
                    continue
                cands.append((-(len(g) * 10 + len(sf)), i))
            if not cands:
                continue
            cands.sort()
            dec = raw[ver][cands[0][1]]
            entry[ver] = {
                "rate": dec["rate"],
                "grass": [[lv, sp, w] for (lv, sp), w in zip(dec["grass"], GRASS_W) if sp],
                **{key: [[mn, mx, sp, w] for ((mn, mx), sp), w in zip(dec[key], WATER_W) if sp]
                   for key in ("surf", "rock", "old", "good", "super")},
            }
        if "D" not in entry and "P" not in entry:
            continue
        if "P" not in entry:
            entry["P"] = entry["D"]
        if "D" not in entry:
            entry["D"] = entry["P"]
        areas[k] = entry
    return dict(sorted(areas.items()))


# ---------------------------------------------------------------- main
def main():
    global by_id
    names = load_names()

    moves, by_id, unsupported = gen_moves(names)
    print(f"招式 {len(moves)} 个,剔除 {len(unsupported)} 个无法表达的招式")

    items, tm, hm = gen_items(names, moves, by_id, None)
    species, by_num, growth_tables, dropped = gen_dex(names, moves, by_id, items)
    items, tm, hm = gen_items(names, moves, by_id, species)     # 补上进化道具说明
    print(f"精灵 {len(species)} 只;学习表中剔除 {sum(dropped.values())} 处不支持招式引用")
    print(f"道具 {len(items)} 个;TM {sum(1 for v in tm.values() if v)}/92,HM {sum(1 for v in hm.values() if v)}/8")
    print("  HM:", hm)
    print("  馆主奖励 TM:", {n: tm.get(n) for n in (76, 86, 60, 55, 65, 91, 72, 57)})

    trainers = gen_trainers(names, by_num, moves, items)
    print(f"训练家 {len(trainers)} 名")

    encounters = gen_encounters(by_num)
    print(f"遭遇区域 {len(encounters)} 个")

    # ---- 校验
    errors = []
    for sp, d in species.items():
        for lv, mv in d["learnset"]:
            if mv not in moves:
                errors.append(f"learnset {sp}:{mv}")
        for e in d["evos"]:
            if e["to"] not in species:
                errors.append(f"evo {sp}->{e['to']}")
            if e.get("item") and e["item"] not in items:
                errors.append(f"evo item {sp}:{e['item']}")
            if e.get("move") and e["move"] not in moves:
                errors.append(f"evo move {sp}:{e['move']}")
        d["tms"] = [n for n in d["tms"] if tm.get(n)]
        d["hms"] = [n for n in d["hms"] if hm.get(n)]
    for k, t in trainers.items():
        for sp, lv, mv, held in t["party"]:
            if sp not in species:
                errors.append(f"trainer {k}:{sp}")
            for m in mv or []:
                if m not in moves:
                    errors.append(f"trainer {k}:{m}")
    for k, a in encounters.items():
        for ver in ("D", "P"):
            for row in a[ver]["grass"]:
                if row[1] not in by_num:
                    errors.append(f"encounter {k}:{row}")
            for key in ("surf", "rock", "old", "good", "super"):
                for row in a[ver][key]:
                    if row[2] not in by_num:
                        errors.append(f"encounter {k}:{row}")
    if errors:
        print("校验错误:", errors[:30])
        sys.exit(1)

    header = "来源: pret/pokediamond 反编译数据 + PokeAPI/Xzonn 官方简中名。\n重新生成: python3 tools/fetch_sinnoh_sources.py && python3 tools/gen_sinnoh_data.py"
    write_module("data_moves.py", "第四世代招式数据(自动生成,勿手改)。" + header +
                 "\nfx 为引擎效果标记,见 src/battle.py 的 _use_move。", [("MOVES", moves)])
    write_module("data_dex.py", "全国图鉴数据(自动生成,勿手改)。" + header +
                 "\nevos: method ∈ level/move/friendship/map/item/party;weight 单位 0.1kg。",
                 [("SPECIES", species), ("SPECIES_BY_ID", by_num), ("GROWTH_TABLES", growth_tables)])
    write_module("data_items.py", "道具数据(自动生成,勿手改)。" + header +
                 "\nTM_MOVES/HM_MOVES: 编号 → 招式名;kind ∈ ball/heal/fullheal/cure/revive/pp/ppall/stat/crit/evo/tm/key。",
                 [("ITEMS", items), ("TM_MOVES", tm), ("HM_MOVES", hm)])
    write_module("data_trainers.py", "训练家数据(自动生成,勿手改)。" + header +
                 "\nparty: (精灵, 等级, [招式]或None=按升级表, 携带道具或None);prize 为每级奖金。",
                 [("TRAINERS", trainers)])
    write_module("data_encounters.py", "神奥地区野生遭遇表(自动生成,勿手改)。" + header +
                 "\n二进制 encountdata 解码后用 PokeAPI location-area 对齐到道路。"
                 "\n草丛行 [等级, 全国图鉴号, 权重];水/碎岩/钓竿行 [最低等级, 最高等级, 全国图鉴号, 权重]。"
                 "\nD=钻石 P=珍珠。", [("ENCOUNTERS", encounters)])
    return 0


if __name__ == "__main__":
    sys.exit(main())
