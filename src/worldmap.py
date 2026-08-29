"""地图数据、NPC 与对话脚本。

图例: '.'草 ','高草 'p/n'道路 'w'水 'f'花 'T'树 'F'栅栏 'S'告示牌
      'R'屋顶 'B'墙 'V'窗 'D'门  室内: '#'墙 'o'地板 'b'床 's'书架
      'm'地垫 't'桌子 '1/2/3'桌上的精灵球 'g/G'道馆地板/墙
"""

STARTER_BALLS = ("芽叶兽", "火苗狐", "水泡龟")


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
    "T........fpp.wwwww.f.T",
    "T..f.....fpp.wwwww...T",
    "T........fpp.wwwww...T",
    "T...ff....pp..fff....T",
    "T....................T",
    "TTTTTTTTTTTTTTTTTTTTTT",
], warps=[
    ((10, 0), ("route", 9, 24, "up")),
    ((11, 0), ("route", 9, 24, "up")),
    ((4, 4), ("house", 5, 6, "up")),
    ((16, 4), ("lab", 5, 6, "up")),
], signs={
    (18, 8): "北:1号道路 → 磐石道馆\n橙顶大屋:星辉研究所\n(选初始精灵的地方!)",
})

# ---------------------------------------------------------------- 1号道路
ROUTE = Map("route", "1号道路", [
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
    ("麻雀雏", 2, 5, 40),
    ("啮齿鼠", 2, 4, 35),
    ("电鼠", 3, 5, 12),
    ("小岩蛇", 4, 6, 13),
]}, signs={
    (2, 12): "1号道路 —— 北:磐石道馆  南:星辉镇",
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
    ((6, 8), ("route", 9, 4, "down")),
])

MAPS = {m.id: m for m in (TOWN, ROUTE, HOUSE, LAB, GYM)}

NPCS = {
    "town": [
        {"x": 12, "y": 9, "pal": "villager", "script": "villager", "trainer": None,
         "name": "村民", "dir": "down"},
    ],
    "route": [
        {"x": 7, "y": 11, "pal": "youth", "script": "youth", "trainer": [("麻雀雏", 6)],
         "name": "短裤少年 小悠", "dir": "down"},
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
         "trainer": [("小岩蛇", 12), ("岩铠兽", 14)],
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
    r = yield ("battle", "短裤少年 小悠", [("麻雀雏", 6)])
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
    r = yield ("battle", "道馆馆长 岩间", [("小岩蛇", 12), ("岩铠兽", 14)])
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


SCRIPTS = {
    "mom": sc_mom,
    "prof": sc_prof,
    "ball": sc_ball,
    "youth": sc_youth,
    "leader": sc_leader,
    "bed": sc_bed,
    "villager": sc_villager,
    "intro": sc_intro,
}
