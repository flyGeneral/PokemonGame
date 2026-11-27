"""神奥 201~230 号道路 + 三湖湖畔。训练家均为原作 trdata 数据(职业/姓名/队伍/等级)。"""
from .. import data as D
from . import Map, Grid, npc, grass, trees
from .interiors import center, mart

MAP_LIST = []


def R(map_id, name, g, enc, **kw):
    m = Map(map_id, name, g.rows(), enc=enc, **kw)
    MAP_LIST.append(m)
    return m


def tn(x, y, key, direction="down", sight=4, show=None):
    """训练家 NPC:视线触发(sight 格),打败后不再触发。"""
    t = D.TRAINERS[key]
    return npc(x, y, "trainer", "trainer", direction, trainer=key, sight=sight,
               name=f"{t['cls']} {t['name']}", show=show)


def build():
    # ============================================================ 201(双叶镇↔真砂镇)
    g = Grid(20, 30)
    g.vline(9, 1, 28, "p")
    g.vline(10, 1, 28, "p")
    g.open_exit("N", 9, 10)
    g.open_exit("S", 9, 10)
    grass(g, [(2, 4, 7, 7), (12, 6, 17, 9), (3, 14, 7, 18), (12, 18, 17, 21), (2, 22, 6, 25)])
    trees(g, [(3, 10), (16, 12), (5, 20), (14, 24)])
    R("r201", "201号道路", g, "route_201",
      exits={"S": ("twinleaf", 10, 1, "down"), "N": ("sandgem", 10, 14, "up")},
      npcs=[tn(6, 9, 9, "right", 3), tn(14, 16, 3, "left", 3)],
      signs={(2, 27): "201号道路\n北:真砂镇(山梨博士的研究所)\n南:双叶镇"},
      items={(17, 3): ("伤药", 1)})

    # ============================================================ 202(真砂镇↔祝庆市)
    g = Grid(30, 16)
    g.hline(1, 28, 7, "p")
    g.hline(1, 28, 8, "p")
    g.open_exit("W", 7, 8)
    g.open_exit("E", 7, 8)
    grass(g, [(3, 2, 9, 5), (12, 10, 18, 13), (20, 2, 27, 5)])
    trees(g, [(11, 3), (19, 11), (2, 11), (27, 11)])
    R("r202", "202号道路", g, "route_202",
      exits={"W": ("sandgem", 20, 8, "right"), "E": ("jubilife", 1, 8, "left")},
      npcs=[tn(6, 6, 11, "down", 3), tn(15, 9, 13, "up", 3), tn(24, 6, 12, "down", 3)],
      signs={(3, 9): "202号道路\n西:真砂镇  东:祝庆市"},
      items={(28, 2): ("解毒药", 1)})

    # ============================================================ 203(祝庆市↔黑金闸口)
    g = Grid(30, 16)
    g.hline(1, 28, 7, "p")
    g.hline(1, 28, 8, "p")
    g.open_exit("W", 7, 8)
    g.open_exit("E", 7, 8)
    grass(g, [(2, 2, 7, 5), (11, 10, 16, 13), (19, 2, 25, 5)])
    g.rect(21, 10, 24, 12, "w")
    trees(g, [(9, 3), (17, 3), (26, 11)])
    R("r203", "203号道路", g, "route_203",
      exits={"W": ("jubilife", 24, 8, "right"), "E": ("oreburgh_gate_1", 1, 8, "left")},
      npcs=[npc(20, 8, "rival", "rival_203", "left", name="帕尔", hide="beat_rival1"),
            tn(5, 6, 245, "down", 3), tn(13, 9, 342, "up", 3), tn(22, 6, 345, "down", 3),
            tn(8, 12, 355, "right", 3)],
      signs={(2, 10): "203号道路\n西:祝庆市  东:黑金闸口"},
      items={(28, 14): ("伤药", 1)})

    # ============================================================ 204 南(祝庆市↔荒芜小道)
    g = Grid(20, 30)
    g.vline(9, 1, 28, "p")
    g.vline(10, 1, 28, "p")
    g.open_exit("S", 9, 10)
    g.open_exit("N", 9, 10)
    grass(g, [(2, 3, 7, 6), (12, 8, 17, 12), (3, 15, 7, 19), (12, 21, 17, 25)])
    g.rect(13, 3, 17, 5, "w")
    trees(g, [(4, 10), (15, 16), (4, 24)])
    R("r204s", "204号道路", g, "route_204_south",
      exits={"S": ("jubilife", 12, 14, "down"), "N": ("ravaged_path", 10, 1, "up")},
      npcs=[tn(5, 8, 4, "right", 3), tn(14, 14, 7, "left", 3)],
      signs={(3, 27): "204号道路\n南:祝庆市  北:荒芜小道"},
      items={(17, 27): ("解毒药", 1)})

    # ============================================================ 204 北(荒芜小道↔花苑镇)
    g = Grid(20, 30)
    g.vline(9, 1, 28, "p")
    g.vline(10, 1, 28, "p")
    g.open_exit("S", 9, 10)
    g.open_exit("N", 9, 10)
    grass(g, [(2, 4, 7, 8), (12, 10, 17, 14), (2, 17, 7, 22), (12, 23, 17, 26)])
    for x, y in ((4, 11), (15, 5), (15, 19), (5, 25)):
        g.set(x, y, "f")
    R("r204n", "204号道路", g, "route_204_north",
      exits={"S": ("ravaged_path", 10, 12, "down"), "N": ("floaroma", 10, 12, "up")},
      npcs=[tn(5, 10, 14, "down", 3), tn(15, 17, 204, "left", 3), tn(5, 23, 21, "right", 3)],
      signs={(3, 2): "204号道路\n南:荒芜小道  北:花苑镇"},
      items={(17, 3): ("伤药", 1)})

    # ============================================================ 205 南(花苑镇↔发电厂↔205 东)
    g = Grid(30, 16)
    g.hline(1, 28, 7, "p")
    g.hline(1, 28, 8, "p")
    g.vline(14, 1, 7, "p")
    g.vline(15, 1, 7, "p")
    g.open_exit("W", 7, 8)
    g.open_exit("E", 7, 8)
    g.open_exit("N", 14, 15)
    grass(g, [(2, 2, 8, 5), (18, 2, 27, 5), (2, 10, 9, 13), (18, 10, 27, 13)])
    g.rect(10, 9, 17, 13, "w")
    R("r205s", "205号道路", g, "route_205_south",
      exits={"W": ("floaroma", 20, 7, "right"), "N": ("r205e", 10, 28, "up"),
             "E": ("valley_windworks", 1, 7, "left")},
      npcs=[npc(14, 3, "galactic", "galactic_205", "down", name="银河队手下", hide="windworks_clear"),
            npc(15, 3, "galactic_f", "galactic_205", "down", name="银河队手下", hide="windworks_clear"),
            tn(6, 6, 244, "down", 3), tn(22, 9, 196, "up", 3)],
      signs={(3, 9): "205号道路\n西:花苑镇  北:205号道路东段  东:谷间发电厂"},
      items={(28, 14): ("好伤药", 1)})

    # ============================================================ 205 东(↔百代森林)
    g = Grid(20, 30)
    g.vline(9, 1, 28, "p")
    g.vline(10, 1, 28, "p")
    g.open_exit("S", 9, 10)
    g.open_exit("N", 9, 10)
    grass(g, [(2, 3, 7, 7), (12, 9, 17, 13), (3, 16, 7, 20), (12, 22, 17, 26)])
    g.rect(12, 3, 17, 6, "w")
    R("r205e", "205号道路", g, "route_205_east",
      exits={"S": ("r205s", 14, 14, "down"), "N": ("eterna_forest", 1, 7, "right")},
      npcs=[tn(5, 9, 17, "right", 3), tn(14, 15, 377, "left", 3), tn(5, 22, 456, "right", 3)],
      signs={(3, 28): "205号道路\n南:205号道路南段  北:百代森林"},
      items={(17, 28): ("精灵球", 2)})

    # ============================================================ 206(自行车道,黑金↕天冠山)
    g = Grid(20, 30)
    g.vline(9, 1, 28, "p")
    g.vline(10, 1, 28, "p")
    g.open_exit("S", 9, 10)
    g.open_exit("N", 9, 10)
    grass(g, [(2, 4, 7, 7), (12, 10, 17, 13), (3, 18, 7, 21), (12, 24, 17, 27)])
    g.rect(2, 11, 7, 15, "C")
    R("r206", "206号道路", g, "route_206",
      exits={"S": ("r207", 1, 8, "right"), "N": ("eterna", 10, 14, "down")},
      npcs=[tn(5, 9, 25, "down", 3), tn(15, 16, 27, "left", 3), tn(5, 23, 26, "right", 3)],
      signs={(3, 2): "206号道路\n自行车道\n南:207号道路  北:百代市"},
      items={(17, 3): ("好伤药", 1)})

    # ============================================================ 207(黑金市↕天冠山)
    g = Grid(20, 30)
    g.vline(9, 1, 28, "p")
    g.vline(10, 1, 28, "p")
    g.open_exit("N", 9, 10)
    g.open_exit("S", 9, 10)
    grass(g, [(2, 5, 7, 8), (12, 12, 17, 16), (3, 19, 7, 23)])
    for x in range(2, 8):
        g.set(x, 11, "m")
    g.hline(1, 9, 8, "p")
    g.open_exit("W", 7, 8)
    R("r207", "207号道路", g, "route_207",
      exits={"N": ("oreburgh", 11, 14, "down"), "S": ("coronet_south", 10, 28, "up"),
             "W": ("r206", 10, 28, "up")},
      npcs=[tn(5, 9, 19, "down", 3), tn(14, 10, 201, "left", 3), tn(15, 19, 16, "right", 3)],
      signs={(3, 27): "207号道路\n北:黑金市  南:天冠山"},
      items={(17, 24): ("精灵球", 3)})

    # ============================================================ 208(天冠山↔家缘市)
    g = Grid(30, 16)
    g.hline(1, 28, 7, "p")
    g.hline(1, 28, 8, "p")
    g.open_exit("W", 7, 8)
    g.open_exit("E", 7, 8)
    grass(g, [(2, 2, 9, 5), (12, 10, 19, 13), (21, 2, 27, 5)])
    g.rect(21, 10, 25, 12, "w")
    R("r208", "208号道路", g, "route_208",
      exits={"W": ("hearthome", 1, 8, "left"), "E": ("coronet_south", 10, 1, "up")},
      npcs=[tn(5, 6, 37, "down", 3), tn(15, 9, 38, "up", 3), tn(24, 6, 44, "down", 3),
            tn(10, 12, 33, "right", 3), tn(22, 13, 83, "right", 3)],
      signs={(2, 10): "208号道路\n西:家缘市  东:天冠山"},
      items={(28, 14): ("好伤药", 1), (2, 14): ("精灵球", 2)})

    # ============================================================ 209(家缘市↕210 南)
    g = Grid(20, 30)
    g.vline(9, 1, 28, "p")
    g.vline(10, 1, 28, "p")
    g.open_exit("S", 9, 10)
    g.open_exit("N", 9, 10)
    grass(g, [(2, 4, 7, 7), (12, 9, 17, 13), (2, 16, 7, 19), (12, 21, 17, 25)])
    g.rect(3, 10, 7, 12, "R")
    g.set(5, 12, "D")        # 丧失塔入口
    R("r209", "209号道路", g, "route_209",
      exits={"S": ("hearthome", 12, 1, "down"), "N": ("r210s", 10, 28, "up")},
      warps=[((5, 12), ("lost_tower_1", 5, 11, "up"))],
      npcs=[tn(5, 8, 34, "down", 3), tn(14, 11, 35, "left", 3), tn(5, 15, 41, "right", 3),
            tn(14, 18, 76, "left", 3), tn(5, 21, 49, "right", 3), tn(14, 26, 82, "up", 3)],
      signs={(3, 2): "209号道路\n南:家缘市  北:210号道路\n高塔:丧失塔"},
      items={(17, 3): ("好伤药", 1), (2, 24): ("全复药", 1), (17, 14): ("高级球", 1)})

    # ============================================================ 210 南(↔随意镇)
    g = Grid(20, 30)
    g.vline(9, 1, 28, "p")
    g.vline(10, 1, 28, "p")
    g.open_exit("S", 9, 10)
    g.open_exit("N", 9, 10)
    grass(g, [(2, 3, 7, 8), (12, 10, 17, 14), (2, 16, 7, 21), (12, 23, 17, 27)])
    g.rect(12, 17, 17, 20, "w")
    R("r210s", "210号道路", g, "route_210_south",
      exits={"S": ("r209", 10, 28, "down"), "N": ("solaceon", 10, 12, "up")},
      npcs=[tn(5, 10, 45, "down", 3), tn(15, 15, 260, "left", 3), tn(5, 23, 348, "right", 3),
            tn(4, 6, 379, "down", 3)],
      signs={(3, 28): "210号道路\n南:209号道路  北:随意镇"},
      items={(17, 3): ("好伤药", 1), (2, 27): ("解麻药", 1)})

    # ============================================================ 210 北(随意镇↕216/215)
    g = Grid(20, 30)
    g.vline(9, 1, 28, "p")
    g.vline(10, 1, 28, "p")
    g.hline(1, 9, 7, "p")
    g.open_exit("S", 9, 10)
    g.open_exit("N", 9, 10)
    g.open_exit("E", 7, 8)
    g.open_exit("W", 7, 8)
    grass(g, [(2, 11, 7, 14), (12, 12, 17, 16), (2, 18, 7, 22), (12, 23, 17, 27)])
    R("r210n", "210号道路", g, "route_210_west",
      exits={"S": ("solaceon", 10, 1, "down"), "N": ("r216", 10, 28, "up"),
             "E": ("r215", 10, 28, "up"), "W": ("r210w", 28, 7, "right")},
      npcs=[tn(5, 13, 278, "down", 3), tn(15, 18, 287, "left", 3), tn(5, 20, 94, "right", 3),
            tn(14, 26, 96, "up", 3), tn(4, 9, 119, "down", 3)],
      signs={(3, 2): "210号道路\n雾之道路\n南:随意镇  东:215号道路  西:神和镇  北:216号道路"},
      items={(17, 3): ("好伤药", 1), (2, 25): ("全复药", 1)})

    # ============================================================ 210 西(神和镇↔210 北)
    g = Grid(30, 16)
    g.hline(1, 28, 7, "p")
    g.hline(1, 28, 8, "p")
    g.open_exit("W", 7, 8)
    g.open_exit("E", 7, 8)
    grass(g, [(2, 2, 9, 5), (12, 10, 19, 13), (21, 2, 27, 5)])
    R("r210w", "210号道路", g, "route_210_west",
      exits={"W": ("celestic", 17, 7, "right"), "E": ("r210n", 1, 7, "left")},
      npcs=[tn(5, 6, 113, "down", 3), tn(15, 9, 120, "up", 3), tn(24, 6, 273, "down", 3)],
      signs={(2, 10): "210号道路\n西:神和镇  东:210号道路北段"},
      items={(28, 14): ("高级球", 1)})

    # ============================================================ 211 西(百代市↔天冠山)
    g = Grid(30, 16)
    g.hline(1, 28, 7, "p")
    g.hline(1, 28, 8, "p")
    g.open_exit("W", 7, 8)
    g.open_exit("E", 7, 8)
    grass(g, [(2, 2, 8, 5), (11, 10, 18, 13), (20, 2, 27, 5)])
    R("r211w", "211号道路", g, "route_211_west",
      exits={"W": ("eterna", 22, 8, "right"), "E": ("coronet_west", 1, 8, "left")},
      npcs=[tn(5, 6, 326, "down", 3), tn(15, 9, 451, "up", 3), tn(23, 6, 36, "down", 3),
            tn(8, 12, 78, "right", 3)],
      signs={(2, 10): "211号道路\n西:百代市  东:天冠山"},
      items={(28, 14): ("精灵球", 2)})

    # ============================================================ 211 东(天冠山↔神和镇)
    g = Grid(30, 16)
    g.hline(1, 28, 7, "p")
    g.hline(1, 28, 8, "p")
    g.open_exit("W", 7, 8)
    g.open_exit("E", 7, 8)
    grass(g, [(2, 2, 8, 5), (11, 10, 18, 13), (20, 2, 27, 5)])
    R("r211e", "211号道路", g, "route_211_east",
      exits={"W": ("coronet_east", 27, 7, "right"), "E": ("celestic", 1, 7, "left")},
      npcs=[tn(5, 6, 388, "down", 3), tn(15, 9, 283, "up", 3), tn(23, 6, 634, "down", 3)],
      signs={(2, 10): "211号道路\n西:天冠山  东:神和镇"},
      items={(28, 14): ("全复药", 1)})

    # ============================================================ 212 北(家缘市↔212 东)
    g = Grid(30, 16)
    g.hline(1, 28, 7, "p")
    g.hline(1, 28, 8, "p")
    g.open_exit("W", 7, 8)
    g.open_exit("E", 7, 8)
    for x in range(1, 29):
        for y in (2, 3, 10, 11, 12, 13):
            if g.g[y][x] == ".":
                g.set(x, y, ",")
    R("r212n", "212号道路", g, "route_212_north",
      exits={"W": ("hearthome", 24, 8, "right"), "E": ("r212e", 10, 28, "up")},
      npcs=[tn(5, 5, 84, "down", 3), tn(15, 9, 85, "up", 3), tn(24, 5, 531, "down", 3)],
      signs={(2, 9): "212号道路\n被雨淋湿的道路\n西:家缘市  东:212号道路东段"},
      items={(28, 14): ("好伤药", 1), (2, 14): ("解眠药", 1)})

    # ============================================================ 212 东(↔湿原市)
    g = Grid(20, 30)
    g.vline(9, 1, 28, "p")
    g.vline(10, 1, 28, "p")
    g.open_exit("N", 9, 10)
    g.open_exit("S", 9, 10)
    grass(g, [(2, 4, 7, 8), (12, 11, 17, 15), (2, 18, 7, 22), (12, 24, 17, 27)])
    g.rect(12, 4, 17, 7, "w")
    R("r212e", "212号道路", g, "route_212_east",
      exits={"N": ("r212n", 28, 8, "right"), "S": ("pastoria", 10, 14, "down")},
      npcs=[tn(5, 10, 92, "right", 3), tn(5, 16, 93, "right", 3), tn(14, 18, 111, "left", 3),
            tn(5, 24, 715, "right", 3)],
      signs={(3, 2): "212号道路\n大雨的道路\n北:212号道路北段  南:湿原市"},
      items={(17, 28): ("解毒药", 1), (2, 12): ("好伤药", 1)})

    # ============================================================ 213(帷幕市↔湿原市/立志湖畔)
    g = Grid(30, 16)
    g.hline(1, 28, 7, "p")
    g.hline(1, 28, 8, "p")
    g.vline(15, 9, 14, "p")
    g.open_exit("W", 7, 8)
    g.open_exit("E", 7, 8)
    g.open_exit("S", 15, 16)
    g.hline(1, 28, 2, "s")
    g.rect(1, 0, 28, 1, "w")
    grass(g, [(3, 10, 8, 13), (20, 10, 27, 13)])
    R("r213", "213号道路", g, "route_213",
      exits={"W": ("veilstone", 24, 8, "right"), "E": ("pastoria", 20, 8, "left"),
             "S": ("valor_lakefront", 26, 8, "left")},
      npcs=[tn(6, 5, 105, "down", 3), tn(23, 5, 106, "down", 3), tn(12, 11, 43, "right", 3),
            tn(20, 12, 328, "left", 3), tn(9, 3, 339, "down", 3)],
      signs={(2, 9): "213号道路\n海边道路\n西:帷幕市  东:湿原市  南:立志湖畔"},
      items={(28, 14): ("好伤药", 1), (2, 14): ("高级球", 1)})

    # ============================================================ 214(帷幕市↔立志湖畔)
    g = Grid(20, 30)
    g.vline(9, 1, 28, "p")
    g.vline(10, 1, 28, "p")
    g.open_exit("N", 9, 10)
    g.open_exit("S", 9, 10)
    grass(g, [(2, 5, 7, 8), (12, 11, 17, 14), (2, 18, 7, 21), (12, 24, 17, 27)])
    R("r214", "214号道路", g, "route_214",
      exits={"N": ("veilstone", 12, 15, "down"), "S": ("valor_lakefront", 14, 12, "up")},
      npcs=[tn(5, 9, 279, "down", 3), tn(15, 15, 280, "left", 3), tn(5, 17, 284, "right", 3),
            tn(14, 22, 300, "up", 3), tn(4, 26, 646, "down", 3)],
      signs={(3, 2): "214号道路\n北:帷幕市  南:立志湖畔"},
      items={(17, 3): ("全复药", 1), (2, 23): ("高级球", 1)})

    # ============================================================ 215(210 北↕帷幕市)
    g = Grid(20, 30)
    g.vline(9, 1, 28, "p")
    g.vline(10, 1, 28, "p")
    g.open_exit("N", 9, 10)
    g.open_exit("S", 9, 10)
    grass(g, [(2, 4, 7, 7), (12, 10, 17, 13), (2, 16, 7, 19), (12, 22, 17, 25)])
    R("r215", "215号道路", g, "route_215",
      exits={"S": ("r210n", 18, 7, "right"), "N": ("veilstone", 12, 15, "down")},
      npcs=[tn(5, 9, 66, "down", 3), tn(15, 14, 67, "left", 3), tn(5, 14, 72, "right", 3),
            tn(14, 20, 80, "up", 3), tn(5, 22, 266, "down", 3), tn(14, 27, 330, "up", 3)],
      signs={(3, 2): "215号道路\n南:210号道路  北:帷幕市"},
      items={(17, 3): (D.item_by_tm(34), 1), (2, 27): ("好伤药", 1)})

    # ============================================================ 216(210 北↕217)
    g = Grid(20, 30, fill="x")
    g.vline(9, 1, 28, "p")
    g.vline(10, 1, 28, "p")
    g.open_exit("S", 9, 10)
    g.open_exit("N", 9, 10)
    for x0, y0, x1, y1 in [(2, 4, 7, 7), (12, 10, 17, 13), (2, 16, 7, 19), (12, 22, 17, 25)]:
        g.rect(x0, y0, x1, y1, ",")
    for x, y in ((4, 10), (15, 8), (5, 22), (14, 27)):
        g.set(x, y, "X")
    R("r216", "216号道路", g, "route_216",
      exits={"S": ("r210n", 10, 1, "down"), "N": ("r217", 10, 28, "up")},
      npcs=[tn(5, 9, 136, "down", 3), tn(15, 15, 144, "left", 3), tn(5, 14, 135, "right", 3),
            tn(14, 20, 132, "up", 3)],
      signs={(3, 2): "216号道路\n雪之路\n南:210号道路  北:217号道路"},
      items={(17, 3): ("全复药", 1), (2, 27): ("高级球", 1)})

    # ============================================================ 217(↕雪峰市,西:睿智湖畔)
    g = Grid(20, 30, fill="x")
    g.vline(9, 1, 28, "p")
    g.vline(10, 1, 28, "p")
    g.hline(1, 9, 7, "p")
    g.open_exit("S", 9, 10)
    g.open_exit("N", 9, 10)
    g.open_exit("W", 7, 8)
    for x0, y0, x1, y1 in [(2, 10, 7, 14), (12, 11, 17, 15), (2, 18, 7, 22), (12, 23, 17, 27), (2, 24, 7, 27)]:
        g.rect(x0, y0, x1, y1, ",")
    for x, y in ((5, 9), (15, 17), (4, 23), (14, 21), (8, 12)):
        g.set(x, y, "X")
    R("r217", "217号道路", g, "route_217", tag="route217",
      exits={"S": ("r216", 10, 14, "down"), "N": ("snowpoint", 10, 1, "down"),
             "W": ("acuity_lakefront", 1, 7, "right")},
      npcs=[tn(5, 13, 139, "down", 3), tn(15, 17, 140, "left", 3), tn(5, 16, 138, "right", 3),
            tn(14, 22, 141, "up", 3), tn(4, 25, 143, "down", 3), tn(14, 27, 145, "up", 3)],
      signs={(3, 2): "217号道路\n暴风雪之路\n南:216号道路  北:雪峰市  西:睿智湖畔"},
      items={(17, 3): (D.item_by_tm(13), 1), (2, 16): ("全复药", 1)})

    # ============================================================ 218(水脉市↔天冠山)
    g = Grid(30, 16)
    g.hline(1, 28, 7, "p")
    g.hline(1, 28, 8, "p")
    g.open_exit("W", 7, 8)
    g.open_exit("E", 7, 8)
    grass(g, [(2, 2, 9, 5), (12, 10, 19, 13), (21, 2, 27, 5)])
    g.rect(21, 10, 27, 13, "w")
    R("r218", "218号道路", g, "route_218",
      exits={"W": ("canalave", 22, 8, "right"), "E": ("coronet_west", 27, 15, "left")},
      npcs=[tn(5, 6, 170, "down", 3), tn(15, 9, 171, "up", 3), tn(23, 6, 392, "down", 3),
            tn(8, 12, 153, "right", 3)],
      signs={(2, 10): "218号道路\n西:水脉市  东:天冠山"},
      items={(28, 14): ("好伤药", 1), (2, 14): ("高级球", 1)})

    # ============================================================ 220(真砂镇南↔心齐湖畔,海上水路)
    g = Grid(30, 16, fill="w", border=None)
    g.open_exit("N", 12, 13, "w")
    g.open_exit("S", 14, 15, "w")
    g.rect(13, 5, 16, 10, "s")
    R("r220", "220号水路", g, "sea_route_220",
      exits={"N": ("sandgem", 12, 14, "down"), "S": ("verity_lakefront", 26, 13, "up")})

    # ============================================================ 221(水脉市南)  → 严酷山方向(后日谈)
    g = Grid(20, 30)
    g.vline(9, 1, 28, "p")
    g.vline(10, 1, 28, "p")
    g.open_exit("N", 9, 10)
    g.open_exit("S", 9, 10)
    grass(g, [(2, 5, 7, 8), (12, 12, 17, 15), (2, 19, 7, 22)])
    R("r221", "221号道路", g, "route_221",
      exits={"N": ("canalave", 12, 14, "up")},
      npcs=[tn(5, 10, 401, "right", 3), tn(14, 17, 442, "left", 3)],
      signs={(3, 2): "221号道路\n水脉市南面的岛屿道路"},
      items={(17, 3): ("高级球", 1)})

    # ============================================================ 222(立志湖畔↔滨海市)
    g = Grid(30, 16)
    g.hline(1, 28, 7, "p")
    g.hline(1, 28, 8, "p")
    g.open_exit("W", 7, 8)
    g.open_exit("E", 7, 8)
    grass(g, [(2, 2, 9, 5), (12, 10, 19, 13), (21, 2, 27, 5)])
    R("r222", "222号道路", g, "route_222",
      exits={"W": ("valor_lakefront", 1, 8, "right"), "E": ("sunyshore", 24, 8, "left")},
      npcs=[npc(16, 7, "officer", "gate_222", "left", name="警察"),
            tn(5, 6, 636, "down", 3), tn(15, 9, 673, "up", 3), tn(23, 6, 234, "down", 3),
            tn(8, 12, 677, "right", 3)],
      signs={(2, 10): "222号道路\n西:立志湖畔  东:滨海市"},
      items={(28, 14): ("全复药", 1), (2, 14): ("高级球", 1)})

    # ============================================================ 223(滨海市北,海上水路)
    g = Grid(20, 30, fill="w", border=None)
    g.vline(9, 1, 28, "w")
    g.vline(10, 1, 28, "w")
    g.open_exit("S", 9, 10, "w")
    g.open_exit("N", 9, 10, "w")
    for x in range(g.w):
        if x not in (9, 10):
            g.set(x, 0, "m")            # 北端是悬崖,只有爬瀑布(攀瀑)才能上 224 道路(与原作一致)
    g.set(9, 1, "W")
    g.set(10, 1, "W")
    g.rect(3, 6, 6, 8, "s")
    g.rect(13, 18, 16, 20, "s")
    R("r223", "223号水路", g, "sea_route_223",
      exits={"S": ("sunyshore", 12, 14, "down"), "N": ("r224", 10, 1, "up")},
      npcs=[tn(4, 7, 191, "down", 3), tn(15, 19, 184, "down", 3), tn(10, 12, 597, "left", 4),
            tn(10, 22, 602, "right", 4)],
      items={(5, 6): ("高级球", 2)})

    # ============================================================ 224(↔冠军之路)
    g = Grid(20, 30)
    g.vline(9, 1, 28, "p")
    g.vline(10, 1, 28, "p")
    g.open_exit("S", 9, 10)
    g.open_exit("N", 9, 10)
    grass(g, [(2, 5, 7, 9), (12, 12, 17, 16), (2, 19, 7, 23)])
    for x, y in ((4, 11), (15, 4), (5, 25), (14, 26)):
        g.set(x, y, "f")
    R("r224", "224号道路", g, "route_224",
      exits={"S": ("r223", 10, 2, "down"), "N": ("victory_road_1", 12, 24, "up")},
      npcs=[tn(5, 10, 305, "down", 3), tn(15, 17, 564, "left", 3), tn(5, 20, 574, "right", 3),
            tn(14, 8, 397, "up", 3), npc(12, 26, "villager", "gate_228", "left", name="研究员")],
      signs={(3, 2): "224号道路\n北:冠军之路 → 宝可梦联盟"},
      items={(17, 3): ("全复药", 1), (2, 27): ("高级球", 1)})

    # ============================================================ 湖畔与湖
    # 心齐湖畔(真砂镇西)
    g = Grid(28, 14)
    g.hline(1, 26, 7, "p")
    g.hline(1, 26, 8, "p")
    g.open_exit("E", 7, 8)
    g.open_exit("W", 7, 8)
    g.hline(1, 26, 12, "s")
    g.hline(1, 26, 13, "w")
    grass(g, [(3, 2, 9, 5), (14, 10, 20, 11), (22, 2, 26, 5)])
    g.open_exit("S", 14, 15, "w")
    R("verity_lakefront", "心齐湖畔", g, "route_201",
      exits={"E": ("sandgem", 1, 8, "left"), "W": ("lake_verity", 27, 7, "right"),
             "S": ("r220", 14, 1, "up")},
      npcs=[tn(6, 6, 23, "down", 3), tn(18, 6, 24, "down", 3)],
      signs={(3, 9): "心齐湖畔\n西:心齐湖  东:真砂镇"},
      items={(26, 2): ("好伤药", 1)})
    g = Grid(28, 14)
    g.hline(1, 26, 7, "p")
    g.hline(1, 26, 8, "p")
    g.open_exit("E", 7, 8)
    g.rect(1, 2, 18, 12, "w")
    g.set(10, 6, "c")
    g.set(10, 7, "c")
    R("lake_verity", "心齐湖", g, "lake_verity_after_galactic_intervention",
      exits={"E": ("verity_lakefront", 1, 8, "left")},
      warps=[((10, 7), ("lake_verity_cavern", 9, 10, "up"))],
      npcs=[npc(19, 7, "villager", "lake_verity_lady", "left", name="游客")],
      signs={(20, 5): "心齐湖\n传说中由湖之守护者庇护"})
    g = Grid(20, 14, fill="c", border="C")
    g.open_exit("S", 9, 10, "c")
    g.set(9, 4, "S")
    R("lake_verity_cavern", "心齐湖洞窟", g, None,
      warps=[((9, 13), ("lake_verity", 10, 8, "down"))],
      npcs=[npc(9, 3, "legendary", "lake_uxie_verity", "down", name="艾姆利多", legend="lake_emesprit")], cave=True)

    # 立志湖畔
    g = Grid(28, 14)
    g.hline(1, 26, 7, "p")
    g.hline(1, 26, 8, "p")
    g.open_exit("E", 7, 8)
    g.open_exit("W", 7, 8)
    g.open_exit("N", 14, 15)
    g.open_exit("S", 14, 15)
    g.building(20, 4, 6, "R")
    g.set(22, 6, "D")
    R("valor_lakefront", "立志湖畔", g, "valor_lakefront",
      exits={"E": ("r213", 15, 14, "up"), "W": ("r222", 27, 8, "left"),
             "N": ("r214", 10, 28, "down"), "S": ("lake_valor", 14, 1, "up")},
      warps=[((22, 6), ("lakefront_hotel", 5, 6, "up"))],
      npcs=[tn(6, 6, 442, "down", 3), tn(15, 10, 452, "down", 3)],
      signs={(3, 9): "立志湖畔\n酒店:可免费休息\n北:214号道路  南:立志湖"},
      items={(26, 2): ("好伤药", 1)})
    g = Grid(28, 14)
    g.hline(1, 26, 7, "p")
    g.hline(1, 26, 8, "p")
    g.open_exit("N", 14, 15)
    g.rect(1, 8, 18, 12, "w")
    g.set(10, 9, "c")
    g.set(10, 10, "c")
    R("lake_valor", "立志湖", g, "lake_valor",
      exits={"N": ("valor_lakefront", 14, 13, "down")},
      warps=[((10, 10), ("lake_valor_cavern", 9, 10, "up"))],
      signs={(20, 5): "立志湖\n湖中央有一座小岛"})
    g = Grid(20, 14, fill="c", border="C")
    g.open_exit("S", 9, 10, "c")
    R("lake_valor_cavern", "立志湖洞窟", g, None,
      warps=[((9, 13), ("lake_valor", 10, 9, "down"))],
      npcs=[npc(9, 3, "legendary", "lake_azelf", "down", name="亚克诺姆", legend="lake_azelf")], cave=True)

    # 睿智湖畔(217 西)
    g = Grid(28, 14, fill="x")
    g.hline(1, 26, 7, "p")
    g.hline(1, 26, 8, "p")
    g.open_exit("E", 7, 8)
    g.open_exit("W", 7, 8)
    R("acuity_lakefront", "睿智湖畔", g, "acuity_lakefront",
      exits={"E": ("r217", 1, 7, "left"), "W": ("lake_acuity", 27, 7, "right")},
      signs={(3, 9): "睿智湖畔\n西:睿智湖  东:217号道路"},
      items={(26, 2): ("高级球", 1)})
    g = Grid(28, 14)
    g.hline(1, 26, 7, "p")
    g.hline(1, 26, 8, "p")
    g.open_exit("E", 7, 8)
    g.rect(1, 2, 18, 12, "w")
    g.set(10, 6, "c")
    g.set(10, 7, "c")
    R("lake_acuity", "睿智湖", g, "lake_acuity",
      exits={"E": ("acuity_lakefront", 1, 8, "left")},
      warps=[((10, 7), ("lake_acuity_cavern", 9, 10, "up"))],
      signs={(20, 5): "睿智湖\n被冰雪覆盖的湖"})
    g = Grid(20, 14, fill="c", border="C")
    g.open_exit("S", 9, 10, "c")
    R("lake_acuity_cavern", "睿智湖洞窟", g, None,
      warps=[((9, 13), ("lake_acuity", 10, 8, "down"))],
      npcs=[npc(9, 3, "legendary", "lake_uxie", "down", name="由克希", legend="lake_uxie")], cave=True)

    # ============================================================ 后日谈:战斗区(225~230)
    g = Grid(22, 16)
    g.vline(10, 1, 14, "p")
    g.vline(11, 1, 14, "p")
    g.hline(1, 20, 8, "p")
    d_center = g.building(2, 2, 6, "Y")
    d_mart = g.building(14, 2, 6, "R")
    g.open_exit("N", 10, 11)
    g.open_exit("E", 8, 9)
    R("fight_area", "战斗区", g, None,
      exits={"N": ("r225", 10, 28, "up"), "E": ("r230", 3, 7, "left")},
      warps=[(d_center, ("fight_area_center", 5, 8, "up")), (d_mart, ("fight_area_mart", 5, 8, "up"))],
      npcs=[npc(14, 8, "sailor", "fight_area_sailor", "down", name="船夫")],
      signs={(8, 8): "战斗区\n通往对战塔的入口(本作未开放)"})
    MAP_LIST.append(center("fight_area", "战斗区", ("fight_area", 3, 5, "down")))
    MAP_LIST.append(mart("fight_area", "战斗区", "league", ("fight_area", 16, 5, "down")))
    g = Grid(20, 30)
    g.vline(9, 1, 28, "p")
    g.vline(10, 1, 28, "p")
    g.open_exit("S", 9, 10)
    g.open_exit("N", 9, 10)
    grass(g, [(2, 5, 7, 8), (12, 12, 17, 15), (2, 19, 7, 22)])
    R("r225", "225号道路", g, "route_225",
      exits={"S": ("fight_area", 10, 1, "down"), "N": ("r226", 10, 1, "down")},
      npcs=[tn(5, 10, 563, "down", 3), tn(15, 17, 573, "left", 3)],
      items={(17, 3): ("活力块", 1)})
    g = Grid(20, 30, fill="w", border=None)
    g.vline(9, 1, 28, "w")
    g.vline(10, 1, 28, "w")
    g.rect(3, 12, 7, 17, "s")
    R("r226", "226号水路", g, "sea_route_226",
      exits={"S": ("r225", 10, 28, "up"), "N": ("r227", 10, 1, "down")},
      npcs=[tn(5, 13, 598, "down", 3)])
    g = Grid(20, 30)
    g.vline(9, 1, 28, "p")
    g.vline(10, 1, 28, "p")
    g.open_exit("S", 9, 10)
    g.open_exit("N", 9, 10)
    g.hline(2, 18, 10, "m")
    R("r227", "227号道路", g, "route_227",
      exits={"S": ("r226", 10, 28, "up"), "N": ("r228", 10, 1, "down")},
      npcs=[tn(5, 6, 567, "down", 3), tn(15, 20, 570, "left", 3)],
      signs={(3, 2): "227号道路\n北:228号道路"},
      items={(17, 3): ("全复药", 1)})
    g = Grid(30, 16)
    g.hline(1, 28, 7, "p")
    g.hline(1, 28, 8, "p")
    g.open_exit("S", 14, 15)
    g.open_exit("N", 14, 15)
    g.open_exit("E", 7, 8)
    grass(g, [(2, 2, 9, 5), (18, 10, 27, 13)])
    R("r228", "228号道路", g, "route_228",
      exits={"S": ("r227", 10, 28, "up"), "N": ("r229", 10, 1, "down"), "E": ("fight_area", 20, 8, "left")},
      npcs=[tn(5, 6, 572, "down", 3), tn(15, 11, 561, "up", 3), tn(22, 11, 579, "up", 3)],
      signs={(2, 10): "228号道路\n沙暴之路"},
      items={(28, 2): ("全复药", 1)})
    g = Grid(20, 30)
    g.vline(9, 1, 28, "p")
    g.vline(10, 1, 28, "p")
    g.open_exit("S", 9, 10)
    g.open_exit("N", 9, 10)
    grass(g, [(2, 5, 7, 8), (12, 12, 17, 15), (2, 19, 7, 22)])
    R("r229", "229号道路", g, "route_229",
      exits={"S": ("r228", 14, 14, "down"), "N": ("r230", 3, 7, "left")},
      npcs=[tn(5, 10, 586, "down", 3), tn(15, 17, 595, "left", 3)],
      signs={(3, 2): "229号道路\n北:230号水路"})
    g = Grid(30, 16, fill="w", border=None)
    g.hline(1, 28, 7, "w")
    g.hline(1, 28, 8, "w")
    g.rect(12, 4, 18, 11, "s")
    g.rect(13, 5, 17, 10, ",")
    R("r230", "230号水路", g, "sea_route_230",
      exits={"W": ("fight_area", 20, 8, "left"), "E": ("r229", 10, 28, "up")},
      npcs=[tn(15, 6, 594, "down", 3), tn(15, 10, 591, "up", 3)],
      items={(14, 7): ("活力块", 1)})
    return MAP_LIST
