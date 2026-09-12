"""地图数据、NPC 与对话脚本。

图例: '.'草 ','高草 'p/n'道路 'w'水 'f'花 'T'树 'F'栅栏 'S'告示牌
      'R'屋顶 'B'墙 'V'窗 'D'门  室内: '#'墙 'o'地板 'b'床 's'书架
      'm'地垫 't'桌子 '1/2/3'桌上的精灵球 'g/G'道馆地板/墙
"""

STARTERS = ("草苗龟", "小火猴", "波加曼")


class Map:
    def __init__(self, map_id, name, rows, warps=(), npcs=(), encounters=None, signs=None):
        self.id = map_id
        self.name = name
        self.rows = [list(r) for r in rows]
        self.w = len(rows[0])
        self.h = len(rows)
        self.warps = {tuple(k): v for k, v in warps}
        self.npcs = list(npcs)          # [{"x","y","pal","script","trainer","name"}]
        self.encounters = encounters or {}
        self.signs = dict(signs or {})

    def tile(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.rows[y][x]
        return "T"

    def solid(self, x, y):
        if not (0 <= x < self.w and 0 <= y < self.h):
            return True
        if self.rows[y][x] in "TwFSRBVQrq#Gbst123":
            return True
        for n in self.npcs:
            if n["x"] == x and n["y"] == y:
                return True
        return False

    def npc_at(self, x, y):
        for n in self.npcs:
            if n["x"] == x and n["y"] == y:
                return n
        return None


# ---------------------------------------------------------------- 星辉镇
TOWN = Map("town", "星辉镇", [
    "TTTTTTTTTTnnTTTTTTTTTT",
    "T.rrrr....pp.qqqqqqq.T",
    "T.RRRR....pp.QQQQQQQ.T",
    "T.BBBB....pp.BBBBBBB.T",
    "T.BVDB....pp.BVVDVVB.T",
    "T..p......pp....p....T",
    "T..p......pp....p....T",
    "T..pppppppppppppp....T",
    "T.........pp.....S...T",
    "T..f......pp..FFFFFF.T",
    "T.rrrr...fpp.wwwww.f.T",
    "T.RRRR....pp.wwwww...T",
    "T.BVDB....pp.wwwww...T",
    "T...ff....pp..fff....T",
    "T....................T",
    "TTTTTTTTTTTTTTTTTTTTTT",
], warps=[
    ((10, 0), ("route", 9, 24, "up")),
    ((11, 0), ("route", 9, 24, "up")),
    ((4, 4), ("house", 5, 6, "up")),
    ((16, 4), ("lab", 5, 6, "up")),
    ((4, 12), ("mart", 5, 7, "up")),
], signs={
    (18, 8): "北:1号道路 → 磐石道馆\n橙顶大屋:星辉研究所\n(选初始精灵的地方!)",
})

# ---------------------------------------------------------------- 1号道路
ROUTE = Map("route", "1号道路", [
    "TTTTTTTTTTTTTTTTTTTT",
    "T.....RRRRRRRR.....T",
    "T.....RRRRRRRR.....T",
    "T.....BVVDVVVB.....T",
    "T.......ppp.S......T",
    "T..,,,,..p..,,,,...T",
    "T..,,,,..p..,,,,...T",
    "T........p.........T",
    "T..,,,,..p..,,,,...T",
    "T..,,,,..p..,,,,...T",
    "T........p.........T",
    "T........p.........T",
    "T.S......p.........T",
    "T........p...wwww..T",
    "T..,,,,..p...wwww..T",
    "T..,,,,..p...wwww..T",
    "T........p.........T",
    "T..,,,,..p..,,,,...T",
    "T..,,,,..p..,,,,...T",
    "T........p.........T",
    "T...ff...p...f.....T",
    "T........p.........T",
    "T........p.........T",
    "T........p.........T",
    "T........pp........T",
    "TTTTTTTTTnnTTTTTTTTT",
], warps=[
    ((9, 25), ("town", 10, 1, "down")),
    ((10, 25), ("town", 10, 1, "down")),
    ((9, 3), ("gym", 6, 7, "up")),
], encounters={",": [
    ("姆克儿", 2, 5, 35),
    ("大牙狸", 2, 4, 30),
    ("小猫怪", 3, 5, 14),
    ("圆法师", 2, 3, 8),
    ("皮卡丘", 3, 5, 6),
    ("小拳石", 4, 6, 13),
]}, signs={
    (2, 12): "1号道路 —— 北:磐石道馆  南:星辉镇",
    (12, 4): "磐石道馆 —— 馆长:岩间\n以岩石系精灵镇守。\n挑战者请备好草系或水系伙伴!",
})

# ---------------------------------------------------------------- 自宅
HOUSE = Map("house", "自宅", [
    "##########",
    "#o......o#",
    "#ob.....s#",
    "#o......o#",
    "#o......o#",
    "#o......o#",
    "#oooomooo#",
    "#####D####",
], warps=[
    ((5, 7), ("town", 4, 5, "down")),
])

# ---------------------------------------------------------------- 研究所
LAB = Map("lab", "星辉研究所", [
    "############",
    "#ss......ss#",
    "#o........o#",
    "#o........o#",
    "#oo123ooooo#",
    "#oooooooooo#",
    "#oooooooooo#",
    "#####D######",
], warps=[
    ((5, 7), ("town", 16, 5, "down")),
])

# ---------------------------------------------------------------- 磐石道馆
GYM = Map("gym", "磐石道馆", [
    "GGGGGGDGGGGGG",
    "Ggggggggggggg",
    "Ggggggggggggg",
    "Ggggggggggggg",
    "Ggggggggggggg",
    "Ggggggggggggg",
    "Ggggggggggggg",
    "GgggggggggggG",
    "GGGGGGDGGGGGG",
    "GGGGGGGGGGGGG",
], warps=[
    ((6, 8), ("route", 9, 4, "down")),
    ((6, 0), ("route2", 9, 22, "up")),
])

# ---------------------------------------------------------------- 2号道路
ROUTE2 = Map("route2", "2号道路", [
    "TTTTTTTTTTTTTTTTTTTT",
    "T.....RRRRRRRR.....T",
    "T.....RRRRRRRR.....T",
    "T.....BVVDVVVB.....T",
    "T........p.........T",
    "T..,,,,..p..,,,,...T",
    "T..,,,,..p..,,,,...T",
    "T........p.........T",
    "T..,,,,..p..,,,,...T",
    "T..,,,,..p..,,,,...T",
    "T........p.........T",
    "T..,,,,..p.........T",
    "T.S,,,,..p.........T",
    "T........p....wwww.T",
    "T........p....wwww.T",
    "T..,,,,..p..,,,,...T",
    "T..,,,,..p..,,,,...T",
    "T........p.........T",
    "T...f....p....f....T",
    "T........p.........T",
    "T........p.........T",
    "T........p.........T",
    "T........pp........T",
    "TTTTTTTTTnnTTTTTTTTT",
], warps=[
    ((9, 3), ("gym2", 6, 7, "up")),
    ((9, 23), ("gym", 6, 1, "down")),
    ((10, 23), ("gym", 6, 1, "down")),
], encounters={",": [
    ("姆克儿", 9, 12, 30),
    ("大牙狸", 8, 10, 25),
    ("小猫怪", 8, 11, 20),
    ("圆法师", 7, 9, 10),
    ("勒克猫", 10, 12, 15),
]}, signs={
    (2, 12): "2号道路 —— 北:绿荫道馆  南:磐石道馆",
})

# ---------------------------------------------------------------- 绿荫道馆(草)
GYM2 = Map("gym2", "绿荫道馆", [
    "GGGGGGDGGGGGG",
    "Ggggggggggggg",
    "Ggggggggggggg",
    "Ggggggggggggg",
    "Ggggggggggggg",
    "Ggggggggggggg",
    "Ggggggggggggg",
    "GgggggggggggG",
    "GGGGGGDGGGGGG",
    "GGGGGGGGGGGGG",
], warps=[
    ((6, 8), ("route2", 9, 4, "down")),
    ((6, 0), ("route3", 9, 22, "up")),
])

# ---------------------------------------------------------------- 3号道路
ROUTE3 = Map("route3", "3号道路", [
    "TTTTTTTTTTTTTTTTTTTT",
    "T.....RRRRRRRR.....T",
    "T.....RRRRRRRR.....T",
    "T.....BVVDVVVB.....T",
    "T........p.........T",
    "T..,,,,..p..,,,,...T",
    "T..,,,,..p..,,,,...T",
    "T........p.........T",
    "T..,,,,..p..,,,,...T",
    "T..,,,,..p..,,,,...T",
    "T........p.........T",
    "T..,,,,..p.........T",
    "T.S,,,,..p.........T",
    "T........p....wwww.T",
    "T........p....wwww.T",
    "T..,,,,..p..,,,,...T",
    "T..,,,,..p..,,,,...T",
    "T........p.........T",
    "T...f....p....f....T",
    "T........p.........T",
    "T........p.........T",
    "T........p.........T",
    "T........pp........T",
    "TTTTTTTTTnnTTTTTTTTT",
], warps=[
    ((9, 3), ("gym3", 6, 7, "up")),
    ((9, 23), ("gym2", 6, 1, "down")),
    ((10, 23), ("gym2", 6, 1, "down")),
], encounters={",": [
    ("勒克猫", 12, 15, 25),
    ("姆克儿", 13, 16, 25),
    ("大牙狸", 12, 14, 15),
    ("樱花宝", 12, 14, 15),
    ("小猫怪", 12, 14, 10),
    ("皮卡丘", 14, 16, 10),
]}, signs={
    (2, 12): "3号道路 —— 北:水脉道馆  南:绿荫道馆",
})

# ---------------------------------------------------------------- 水脉道馆(水)
GYM3 = Map("gym3", "水脉道馆", [
    "GGGGGGGGGGGGG",
    "Ggggggggggggg",
    "Ggggggggggggg",
    "Ggggggggggggg",
    "Ggggggggggggg",
    "Ggggggggggggg",
    "Ggggggggggggg",
    "GgggggggggggG",
    "GGGGGGDGGGGGG",
    "GGGGGGGGGGGGG",
], warps=[
    ((6, 8), ("route3", 9, 4, "down")),
])

# ---------------------------------------------------------------- 友里商店
MART = Map("mart", "友里商店", [
    "##########",
    "#o......o#",
    "#ss....ss#",
    "#o......o#",
    "#o......o#",
    "#o......o#",
    "#o......o#",
    "#oooomooo#",
    "#####D####",
], warps=[
    ((5, 8), ("town", 4, 13, "down")),
])

MAPS = {m.id: m for m in (TOWN, ROUTE, HOUSE, LAB, GYM, MART, ROUTE2, GYM2, ROUTE3, GYM3)}

# 徽章门禁:(当前地图, 目标地图) → 所需徽章标记
BADGE_GATES = {
    ("gym", "route2"): "has_badge",
    ("gym2", "route3"): "badge_forest",
}

NPCS = {
    "mart": [
        {"x": 4, "y": 4, "pal": "villager", "script": "shop", "trainer": None,
         "name": "店主", "dir": "down"},
    ],
    "route2": [
        {"x": 7, "y": 10, "pal": "youth", "script": "camper", "trainer": None,
         "name": "野营少年 亚织", "dir": "right"},
    ],
    "route3": [
        {"x": 12, "y": 10, "pal": "leader", "script": "ace", "trainer": None,
         "name": "精英训练家 泽田", "dir": "left"},
    ],
    "gym2": [
        {"x": 6, "y": 2, "pal": "lady", "script": "gardenia", "trainer": None,
         "name": "绿荫道馆馆长 园理", "dir": "down"},
    ],
    "gym3": [
        {"x": 6, "y": 2, "pal": "leader", "script": "wake", "trainer": None,
         "name": "水脉道馆馆长 阿驰", "dir": "down"},
    ],
    "town": [
        {"x": 12, "y": 9, "pal": "villager", "script": "villager", "trainer": None,
         "name": "村民", "dir": "down"},
    ],
    "route": [
        {"x": 7, "y": 11, "pal": "youth", "script": "youth", "trainer": [("姆克儿", 6)],
         "name": "短裤少年 小悠", "dir": "down"},
        {"x": 11, "y": 22, "pal": "villager", "script": "route_guide", "trainer": None,
         "name": "村民", "dir": "left"},
        {"x": 12, "y": 14, "pal": "youth", "script": "bugcatcher",
         "trainer": [("大牙狸", 7), ("姆克儿", 7)],
         "name": "捕虫少年 阿彻", "dir": "left"},
        {"x": 10, "y": 5, "pal": "lady", "script": "gym_greeter", "trainer": None,
         "name": "迎宾女士", "dir": "down"},
    ],
    "house": [
        {"x": 2, "y": 4, "pal": "mom", "script": "mom", "trainer": None,
         "name": "妈妈", "dir": "down"},
    ],
    "lab": [
        {"x": 6, "y": 2, "pal": "prof", "script": "prof", "trainer": None,
         "name": "榆木博士", "dir": "down"},
    ],
    "gym": [
        {"x": 6, "y": 2, "pal": "leader", "script": "leader",
         "trainer": [("小拳石", 12), ("隆隆石", 14)],
         "name": "道馆馆长 岩间", "dir": "down"},
    ],
}
for mid, lst in NPCS.items():
    MAPS[mid].npcs = lst


# ---------------------------------------------------------------- 对话脚本
# 生成器协议: ("msg",t) ("choice",[..]) ("starter",) ("battle",trainer,team)
#             ("heal",) ("give",item,n) ("flag",key)
def sc_villager(g):
    if not g.flags.get("starter_chosen"):
        yield ("msg", "村民:你还一只精灵都没有?\n北边那座橙顶大屋就是星辉研究所,\n榆木博士会送你一只初始精灵!")
        yield ("msg", "村民:从中间的大路一直向上,\n到路口往东(右)走,顺着小路就到了。")
    elif not g.flags.get("beat_gym"):
        yield ("msg", "村民:北边出口出去是1号道路,\n尽头就是磐石道馆。路上草丛有野生精灵,\n记得多带几颗精灵球。")
    else:
        yield ("msg", "村民:那不是岩石徽章吗!\n你打败岩间馆长了?了不起!")


def sc_route_guide(g):
    if not g.flags.get("beat_gym"):
        yield ("msg", "村民:沿着这条路一直向北,\n尽头就是磐石道馆。")
        yield ("msg", "村民:高草丛里有野生精灵出没,\n多备几颗精灵球再走吧。")
    else:
        yield ("msg", "村民:岩石徽章!你真的拿到了啊,\n了不起!")


def sc_bugcatcher(g):
    if g.flags.get("beat_bug"):
        yield ("msg", "阿彻:我的伙伴们还需要多锻炼……\n下次再战!")
        return
    yield ("msg", "阿彻:站住!我以捕虫少年的名义,\n向你发起对战!")
    r = yield ("battle", "捕虫少年 阿彻", [("大牙狸", 7), ("姆克儿", 7)])
    if r != "win":
        return
    g.flags["beat_bug"] = True
    yield ("msg", "阿彻:呜……两连败,完全不是对手。\n这个给你,加油!")
    yield ("give", "精灵球", 3)
    yield ("msg", "(获得了 精灵球×3)")


def sc_gym_greeter(g):
    if g.flags.get("beat_gym"):
        yield ("msg", "女士:这不是新科冠军嘛!\n常回道馆来看看呀。")
        return
    yield ("msg", "女士:前面就是磐石道馆了。")
    yield ("msg", "女士:馆长岩间用的是岩石系——\n草系和水系的招式会很有效哦。")


def sc_mom(g):
    yield ("msg", "妈妈:出门前要好好照顾你的精灵哦。\n要休息一会儿吗?")
    r = yield ("yesno",)
    if r == 0:
        yield ("heal",)
        yield ("msg", "你的精灵们恢复了活力!\n妈妈:路上小心。")
    else:
        yield ("msg", "妈妈:加油哦。")


def sc_prof(g):
    if g.flags.get("starter_chosen"):
        yield ("msg", "榆木博士:精灵的强弱关键在于属性相性。\n多在草丛里锻炼吧!")
        return
    yield ("msg", "榆木博士:哦哦,你终于来了!\n桌上这三只精灵,选一只做你的伙伴吧。")
    pick = yield ("starter",)
    if not pick:
        yield ("msg", "榆木博士:不着急,想好了再来。")
        return
    g.flags["starter_chosen"] = True
    yield ("msg", f"榆木博士:{pick}就交给你了!\n好好珍惜这段旅程。")
    yield ("give", "精灵球", 5)
    yield ("give", "伤药", 3)
    yield ("msg", "榆木博士:这些也带上。\n(获得了 精灵球×5 和 伤药×3)")
    yield ("msg", "榆木博士:北边1号道路尽头的磐石道馆,\n馆长岩间正在等待有实力的挑战者。")


def sc_ball(g):
    if g.flags.get("starter_chosen"):
        yield ("msg", "精灵球已经空了。")
        return
    yield from sc_prof(g)


def sc_youth(g):
    if g.flags.get("beat_youth"):
        yield ("msg", "小悠:你的精灵看起来更强了!\n我还得再练练。")
        return
    yield ("msg", "小悠:嘿,你有精灵了吧?\n来跟我对战一场!")
    r = yield ("battle", "短裤少年 小悠", [("姆克儿", 6)])
    if r != "win":
        return
    g.flags["beat_youth"] = True
    yield ("msg", "小悠:呜哇,完全不是对手!\n你真厉害……这个给你。")
    yield ("give", "伤药", 1)
    yield ("msg", "(获得了 伤药×1)")


def sc_leader(g):
    if g.flags.get("beat_gym"):
        yield ("msg", "岩间:那枚岩石徽章,\n和你的眼神很相配。")
        return
    yield ("msg", "岩间:我是磐石道馆的馆长——岩间!\n我的岩石队伍,坚硬如磐!")
    r = yield ("battle", "道馆馆长 岩间", [("小拳石", 12), ("大岩蛇", 12), ("头盖龙", 14)], 2)
    if r != "win":
        return
    g.flags["beat_gym"] = True
    yield ("msg", "岩间:好!你的信念比岩石更坚硬!\n按照约定,岩石徽章归你了。")
    yield ("flag", "has_badge")
    yield ("msg", "(获得了 岩石徽章!)\n\n★ Demo 主要目标达成! ★\n可以继续锻炼队伍,或在菜单里存档。")


def sc_bed(g):
    yield ("msg", "要躺到床上一觉睡到天亮吗?")
    r = yield ("yesno",)
    if r == 0:
        yield ("heal",)
        yield ("msg", "你美美地睡了一觉。\n精灵们恢复了活力!")
    else:
        yield ("msg", "现在还不想睡。")


def sc_intro(g):
    yield ("msg", "欢迎来到精灵的世界!\n这里是珍珠钻石风格的星辉地区。")
    yield ("msg", "去北边橙顶的星辉研究所找榆木博士,\n领取你的第一只伙伴吧!")
    yield ("msg", "(操作:方向键移动  Z/回车 确认对话\n X/回车 打开菜单)")


def sc_shop(g):
    yield ("msg", "欢迎光临!慢慢挑,不买也没关系。")
    yield ("shop", [("精灵球", 200), ("超级球", 600), ("高级球", 1200),
                    ("伤药", 300), ("好伤药", 700), ("解毒药", 250), ("全复药", 2500)])
    yield ("msg", "感谢惠顾,欢迎再来。")


def sc_camper(g):
    if g.flags.get("beat_camper"):
        yield ("msg", "亚织:野营就是要不断挑战!\n下次我再赢回来。")
        return
    yield ("msg", "亚织:难得遇到训练家,来战一场!")
    r = yield ("battle", "野营少年 亚织", [("圆法师", 10), ("小猫怪", 11)])
    if r != "win":
        return
    g.flags["beat_camper"] = True
    yield ("msg", "亚织:输了输了解……这个给你。")
    yield ("give", "好伤药", 1)
    yield ("msg", "(获得了 好伤药×1)")


def sc_ace(g):
    if g.flags.get("beat_ace"):
        yield ("msg", "泽田:你的队伍越来越强了。")
        return
    yield ("msg", "泽田:前面就是水脉道馆。\n先让我检验一下你的实力!")
    r = yield ("battle", "精英训练家 泽田", [("勒克猫", 16), ("姆克儿", 16)], 2)
    if r != "win":
        return
    g.flags["beat_ace"] = True
    yield ("msg", "泽田:好胜负!去吧,前面道馆的馆长\n阿驰用水系,记得带草系或电系。")
    yield ("give", "全复药", 1)
    yield ("msg", "(获得了 全复药×1)")


def sc_gardenia(g):
    if g.flags.get("beat_gym2"):
        yield ("msg", "园理:森林徽章和你很相配呢。")
        return
    yield ("msg", "园理:我是绿荫道馆的馆长——园理!\n让我看看你和精灵的羁绊!")
    r = yield ("battle", "绿荫道馆馆长 园理", [("圆法师", 15), ("樱花宝", 19), ("罗丝雷朵", 22)], 2)
    if r != "win":
        return
    g.flags["beat_gym2"] = True
    yield ("msg", "园理:输得心服口服!森林徽章归你了。")
    yield ("flag", "badge_forest")
    yield ("msg", "(获得了 森林徽章!)\n北边 3号道路的尽头是水脉道馆。")


def sc_wake(g):
    if g.flags.get("beat_gym3"):
        yield ("msg", "阿驰:哈哈哈!那场战斗真痛快!")
        return
    yield ("msg", "阿驰:哇——!我等好久了!\n我是水脉道馆的馆长——阿驰!")
    r = yield ("battle", "水脉道馆馆长 阿驰", [("暴鲤龙", 26), ("沼王", 26), ("浮鼬王", 28)], 2)
    if r != "win":
        return
    g.flags["beat_gym3"] = True
    yield ("msg", "阿驰:痛快!你的实力,配得上这枚沼泽徽章!")
    yield ("flag", "badge_fen")
    yield ("msg", "(获得了 沼泽徽章!)\n\n★ 三枚徽章到手,Demo 全部目标达成! ★")


SCRIPTS = {
    "mom": sc_mom,
    "prof": sc_prof,
    "ball": sc_ball,
    "youth": sc_youth,
    "bugcatcher": sc_bugcatcher,
    "route_guide": sc_route_guide,
    "gym_greeter": sc_gym_greeter,
    "leader": sc_leader,
    "bed": sc_bed,
    "villager": sc_villager,
    "shop": sc_shop,
    "camper": sc_camper,
    "ace": sc_ace,
    "gardenia": sc_gardenia,
    "wake": sc_wake,
    "intro": sc_intro,
}
