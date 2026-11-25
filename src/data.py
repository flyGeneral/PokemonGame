"""属性克制表 + 第四世代数据访问层。

精灵/招式/道具/训练家/遭遇表数据由 tools/gen_sinnoh_data.py 从 pret/pokediamond 反编译数据生成,
官方简中名取自 PokeAPI / Xzonn 汉化修正项目;本文件只保留手写的克制表与辅助函数。
"""
from .data_moves import MOVES
from .data_dex import SPECIES, SPECIES_BY_ID, GROWTH_TABLES
from .data_items import ITEMS, TM_MOVES, HM_MOVES
from .data_trainers import TRAINERS
from .data_encounters import ENCOUNTERS

# ---------------------------------------------------------------- 属性克制表(第四世代,无妖精)
TYPES = ("一般", "火", "水", "草", "电", "冰", "格斗", "毒", "地面", "飞行",
         "超能力", "虫", "岩石", "幽灵", "龙", "恶", "钢")

_CHART = {
    "一般":   {"岩石": .5, "钢": .5, "幽灵": 0},
    "火":     {"火": .5, "水": .5, "草": 2, "冰": 2, "虫": 2, "岩石": .5, "龙": .5, "钢": 2},
    "水":     {"火": 2, "水": .5, "草": .5, "地面": 2, "岩石": 2, "龙": .5},
    "草":     {"火": .5, "水": 2, "草": .5, "毒": .5, "地面": 2, "飞行": .5, "虫": .5, "岩石": 2, "龙": .5, "钢": .5},
    "电":     {"水": 2, "电": .5, "草": .5, "地面": 0, "飞行": 2, "龙": .5},
    "冰":     {"火": .5, "水": .5, "草": 2, "冰": .5, "地面": 2, "飞行": 2, "龙": 2, "钢": .5},
    "格斗":   {"一般": 2, "冰": 2, "毒": .5, "飞行": .5, "超能力": .5, "虫": .5,
              "岩石": 2, "幽灵": 0, "恶": 2, "钢": 2},
    "毒":     {"草": 2, "毒": .5, "地面": .5, "岩石": .5, "幽灵": .5, "钢": 0},
    "地面":   {"火": 2, "草": .5, "电": 2, "毒": 2, "飞行": 0, "虫": .5, "岩石": 2, "钢": 2},
    "飞行":   {"草": 2, "电": .5, "格斗": 2, "虫": 2, "岩石": .5, "钢": .5},
    "超能力": {"格斗": 2, "毒": 2, "超能力": .5, "恶": 0, "钢": .5},
    "虫":     {"火": .5, "草": 2, "格斗": .5, "毒": .5, "飞行": .5, "超能力": 2,
              "幽灵": .5, "恶": 2, "钢": .5},
    "岩石":   {"火": 2, "冰": 2, "格斗": .5, "地面": .5, "飞行": 2, "虫": 2, "钢": .5},
    "幽灵":   {"一般": 0, "超能力": 2, "幽灵": 2, "恶": .5},
    "龙":     {"龙": 2, "钢": .5},
    "恶":     {"格斗": .5, "超能力": 2, "幽灵": 2, "恶": .5, "钢": .5},
    "钢":     {"火": .5, "水": .5, "电": .5, "冰": 2, "岩石": 2, "钢": .5},
}


def type_multiplier(atk_type, def_types):
    m = 1.0
    for d in def_types:
        m *= _CHART.get(atk_type, {}).get(d, 1.0)
    return m


STARTERS = ("草苗龟", "小火焰猴", "波加曼")

# 徽章:(旗标名, 显示名, 单字, 颜色) —— 顺序即原作推荐顺序
BADGES = [
    ("badge_coal", "煤炭徽章", "炭", (188, 150, 90)),
    ("badge_forest", "森林徽章", "森", (90, 170, 90)),
    ("badge_cobble", "圆石徽章", "石", (150, 150, 170)),
    ("badge_fen", "沼泽徽章", "沼", (90, 140, 200)),
    ("badge_relic", "遗迹徽章", "迹", (160, 110, 180)),
    ("badge_mine", "矿山徽章", "矿", (120, 130, 150)),
    ("badge_icicle", "冰河徽章", "冰", (130, 200, 230)),
    ("badge_beacon", "灯塔徽章", "灯", (240, 200, 70)),
]

# 秘传招式地图使用:招式名 → (所需旗标, 提示)
HM_FIELD = {
    "居合劈": ("hm_cut", "砍断树丛"),
    "飞翔": ("hm_fly", "飞往去过的城镇"),
    "冲浪": ("hm_surf", "在水面上冲浪"),
    "怪力": ("hm_strength", "推动沉重的岩石"),
    "碎岩": ("hm_rock_smash", "打碎裂开的岩石"),
    "攀瀑": ("hm_waterfall", "攀上瀑布"),
}

# 手绘像素矩阵回退映射(art_data.MON_ART 键),未下载官方贴图时使用
DEX_ART_ALIAS = {387: "sprout", 388: "vine", 390: "foxf", 391: "firef", 393: "turtle",
                 394: "wave", 396: "bird", 399: "rat", 25: "pika", 74: "rock", 75: "boulder"}


# ---------------------------------------------------------------- 经验(官方成长曲线)
def exp_for_level(level, growth="medium_fast"):
    return GROWTH_TABLES[growth][max(0, min(100, level))]


def exp_to_next(level, growth="medium_fast"):
    if level >= 100:
        return 1
    return GROWTH_TABLES[growth][level + 1] - GROWTH_TABLES[growth][level]


def exp_gain(enemy, trainer_battle):
    g = SPECIES[enemy.species]["base_exp"] * enemy.level // 7
    return int(g * 1.5) if trainer_battle else g


def species_name(national_id):
    return SPECIES_BY_ID.get(national_id)


def item_by_tm(num, hm=False):
    for name, d in ITEMS.items():
        if d["kind"] == "tm" and d["hm"] == hm and d["num"] == num:
            return name
    return None
