"""神奥 15 座城镇/城市 + 各自的精灵中心、友好商店、民宅。"""
from .. import data as D
from . import Map, Grid, npc, register
from .interiors import center, mart, house

MAP_LIST = []


def T(map_id, name, g, **kw):
    m = Map(map_id, name, g.rows(), **kw)
    MAP_LIST.append(m)
    return m


def build():
    # ------------------------------------------------------------ 双叶镇
    g = Grid(22, 16)
    g.vline(10, 1, 14, "p")
    g.vline(11, 1, 14, "p")
    d_rival = g.building(2, 2, 4, "R")
    d_h1 = g.building(16, 2, 4, "R")
    d_home = g.building(2, 11, 4, "R")
    g.rect(15, 8, 17, 9, "w")
    for x, y in ((5, 6), (14, 6), (6, 13), (16, 12)):
        g.set(x, y, "f")
    g.set(2, 7, "S")
    g.open_exit("N", 10, 11)
    T("twinleaf", "双叶镇", g, enc="route_201", exits={"N": ("r201", 10, 28, "up")},
      warps=[(d_rival, ("twinleaf_rival", 5, 7, "up")), (d_h1, ("twinleaf_house1", 4, 6, "up")),
             (d_home, ("twinleaf_home", 5, 7, "up"))],
      npcs=[npc(6, 7, "villager", "twinleaf_villager", "right", name="村民")],
      signs={(2, 7): "双叶镇\n开始冒险的小镇\n北边201号道路通往真砂镇,\n山梨博士的研究所就在那里"})

    # ------------------------------------------------------------ 真砂镇
    g = Grid(22, 16)
    g.vline(10, 1, 14, "p")
    g.vline(11, 1, 14, "p")
    g.hline(2, 20, 7, "p")
    g.hline(2, 20, 8, "p")
    d_h1 = g.building(2, 2, 4, "R")
    d_center = g.building(15, 2, 6, "Y")
    d_lab = g.building(4, 10, 6, "Q", door_dx=2)
    for y in range(12, 15):
        g.hline(12, 20, y, "s")
    g.rect(12, 14, 20, 14, "w")
    for x, y in ((7, 5), (13, 5), (7, 13), (3, 8)):
        g.set(x, y, "f")
    g.set(14, 8, "S")
    g.open_exit("N", 10, 11)
    g.open_exit("E", 7, 8)
    g.open_exit("W", 7, 8)
    g.open_exit("S", 12, 13, "w")
    T("sandgem", "真砂镇", g, enc="route_201", exits={"N": ("r201", 10, 1, "down"), "E": ("r202", 1, 8, "left"),
                                   "W": ("verity_lakefront", 26, 8, "right"),
                                   "S": ("r220", 14, 1, "up")},
      warps=[(d_h1, ("sandgem_house1", 4, 6, "up")), (d_center, ("sandgem_center", 5, 8, "up")),
             (d_lab, ("sandgem_lab", 5, 7, "up"))],
      npcs=[npc(13, 10, "lady", "sandgem_villager", "down", name="居民")],
      signs={(14, 8): "真砂镇\n沙之镇\n西南黄色屋顶的大屋:山梨博士研究所\n西:心齐湖畔  北:201号道路  东:202号道路"})
    MAP_LIST.append(center("sandgem", "真砂镇", ("sandgem", 16, 5, "down")))

    # ------------------------------------------------------------ 祝庆市
    g = Grid(26, 18)
    g.hline(1, 24, 8, "p")
    g.hline(1, 24, 9, "p")
    g.vline(12, 1, 8, "p")
    g.vline(13, 1, 8, "p")
    d_center = g.building(2, 2, 6, "Y")
    d_mart = g.building(18, 2, 6, "R")
    d_school = g.building(9, 2, 6, "Q")
    d_h1 = g.building(2, 12, 4, "R")
    g.building(18, 12, 6, "R", door=False)     # 电视台(无门,装饰)
    for x, y in ((7, 6), (16, 6), (7, 12), (16, 11), (10, 12)):
        g.set(x, y, "f")
    g.set(6, 8, "S")
    g.open_exit("W", 8, 9)
    g.open_exit("E", 8, 9)
    g.open_exit("N", 12, 13)
    T("jubilife", "祝庆市", g, exits={"W": ("r202", 28, 8, "right"), "E": ("r203", 1, 8, "left"),
                                    "N": ("r204s", 12, 28, "up")},
      warps=[(d_center, ("jubilife_center", 5, 8, "up")), (d_mart, ("jubilife_mart", 5, 8, "up")),
             (d_school, ("jubilife_school", 5, 7, "up")), (d_h1, ("jubilife_house1", 4, 6, "up"))],
      npcs=[npc(8, 7, "villager", "jubilife_villager", "down", name="市民"),
            npc(16, 10, "youth", "jubilife_youth", "left", name="短裤小子"),
            npc(14, 6, "lady", "dawn_pal", "down", name="小光", hide="met_dawn")],
      signs={(6, 8): "祝庆市\n快乐之城\n神奥地区最大的城市"})
    MAP_LIST.append(center("jubilife", "祝庆市", ("jubilife", 3, 5, "down")))
    MAP_LIST.append(mart("jubilife", "祝庆市", "jubilife", ("jubilife", 19, 5, "down")))

    # ------------------------------------------------------------ 黑金市
    g = Grid(24, 18)
    g.hline(1, 22, 8, "p")
    g.hline(1, 22, 9, "p")
    g.vline(11, 1, 16, "p")
    g.vline(12, 1, 16, "p")
    d_gym = g.building(2, 2, 6, "Q")
    d_museum = g.building(16, 2, 6, "R")
    d_mart = g.building(9, 5, 4, "R")
    d_center = g.building(16, 11, 6, "Y")
    d_h1 = g.building(2, 12, 4, "R")
    for x, y in ((7, 12), (15, 7), (20, 8), (7, 6)):
        g.set(x, y, "f")
    g.rect(21, 7, 23, 10, "C")
    g.rect(22, 8, 23, 9, "c")
    g.set(21, 8, "c")          # 矿坑入口与主路相连
    g.set(21, 9, "c")
    g.set(13, 6, "S")
    g.open_exit("W", 8, 9, "c")
    g.open_exit("S", 11, 12)
    T("oreburgh", "黑金市", g, exits={"W": ("oreburgh_gate_b1", 20, 7, "left"),
                                    "S": ("r207", 11, 1, "up")},
      warps=[(d_gym, ("oreburgh_gym", 7, 10, "up")), (d_museum, ("oreburgh_museum", 5, 6, "up")),
             (d_mart, ("oreburgh_mart", 5, 8, "up")), (d_center, ("oreburgh_center", 5, 8, "up")),
             (d_h1, ("oreburgh_house1", 4, 6, "up")),
             ((22, 8), ("oreburgh_mine_1", 1, 7, "right")), ((22, 9), ("oreburgh_mine_1", 1, 7, "right"))],
      npcs=[npc(7, 11, "hiker", "oreburgh_hiker", "down", name="登山男")],
      signs={(13, 6): "黑金市\n煤炭之城\n道馆馆主:瓢太(岩石系)"})
    MAP_LIST.append(mart("oreburgh", "黑金市", "basic", ("oreburgh", 10, 7, "down")))
    MAP_LIST.append(center("oreburgh", "黑金市", ("oreburgh", 18, 13, "down")))

    # ------------------------------------------------------------ 花苑镇
    g = Grid(22, 14)
    g.vline(10, 1, 12, "p")
    g.vline(11, 1, 12, "p")
    g.hline(1, 20, 6, "p")
    g.hline(1, 20, 7, "p")
    d_shop = g.building(2, 2, 4, "Q")
    d_center = g.building(14, 2, 6, "Y")
    d_mart = g.building(14, 8, 6, "R")
    for x in range(2, 20):
        for y in (4, 10, 11):
            if g.g[y][x] == "." and (x + y) % 3 == 0:
                g.set(x, y, "f")
    g.set(7, 9, "S")
    g.open_exit("S", 10, 11)
    g.open_exit("E", 6, 7)
    T("floaroma", "花苑镇", g, exits={"S": ("r204n", 10, 1, "up"), "E": ("r205s", 1, 7, "left")},
      warps=[(d_shop, ("floaroma_shop", 4, 6, "up")), (d_center, ("floaroma_center", 5, 8, "up")),
             (d_mart, ("floaroma_mart", 5, 8, "up"))],
      npcs=[npc(7, 5, "lady", "floaroma_lady", "down", name="花匠")],
      signs={(7, 9): "花苑镇\n花香四溢的小镇"})
    MAP_LIST.append(center("floaroma", "花苑镇", ("floaroma", 16, 5, "down")))
    MAP_LIST.append(mart("floaroma", "花苑镇", "basic", ("floaroma", 16, 11, "down")))

    # ------------------------------------------------------------ 百代市
    g = Grid(24, 18)
    g.hline(1, 22, 8, "p")
    g.hline(1, 22, 9, "p")
    g.vline(11, 1, 7, "p")
    g.vline(12, 1, 7, "p")
    d_galactic = g.building(2, 2, 6, "R")
    d_bike = g.building(10, 2, 4, "R")
    d_center = g.building(15, 2, 6, "Y")
    d_gym = g.building(2, 11, 6, "Q")
    d_mart = g.building(15, 11, 6, "R")
    g.set(11, 6, "S")
    for x, y in ((9, 6), (14, 6), (9, 13), (14, 14)):
        g.set(x, y, "f")
    g.open_exit("W", 8, 9)
    g.open_exit("E", 8, 9)
    g.open_exit("S", 10, 11)
    T("eterna", "百代市", g, exits={"W": ("eterna_forest", 30, 8, "right"), "E": ("r211w", 1, 8, "left"),
                                  "S": ("r206", 10, 1, "up")},
      warps=[(d_galactic, ("galactic_eterna", 5, 7, "up")), (d_bike, ("eterna_shop", 4, 6, "up")),
             (d_center, ("eterna_center", 5, 8, "up")), (d_gym, ("eterna_gym", 7, 10, "up")),
             (d_mart, ("eterna_mart", 5, 8, "up"))],
      npcs=[npc(5, 9, "rival", "rival_eterna", "right", name="帕尔", hide="beat_rival2"),
            npc(4, 6, "galactic", "galactic_grunt_city", "down", name="银河队手下", hide="eterna_galactic_clear"),
            npc(14, 10, "villager", "eterna_villager", "down", name="市民")],
      signs={(11, 6): "百代市\n古老绿荫之城\n北面矗立着远古宝可梦的雕像"})
    MAP_LIST.append(center("eterna", "百代市", ("eterna", 16, 5, "down")))
    MAP_LIST.append(mart("eterna", "百代市", "jubilife", ("eterna", 16, 13, "down")))

    # ------------------------------------------------------------ 家缘市
    g = Grid(26, 18)
    g.hline(1, 24, 8, "p")
    g.hline(1, 24, 9, "p")
    g.vline(12, 1, 8, "p")
    g.vline(13, 1, 8, "p")
    d_center = g.building(2, 2, 6, "Y")
    d_mart = g.building(9, 2, 6, "R")
    d_gym = g.building(17, 2, 6, "Q")
    d_h1 = g.building(3, 12, 4, "R")
    g.building(9, 12, 6, "R", door=False)      # 华丽大赛会场(装饰)
    d_bebe = g.building(19, 12, 4, "R")
    g.set(12, 10, "S")
    for x, y in ((7, 6), (16, 6), (17, 11)):
        g.set(x, y, "f")
    g.open_exit("W", 8, 9)
    g.open_exit("E", 8, 9)
    g.open_exit("N", 12, 13)
    T("hearthome", "家缘市", g, exits={"W": ("r208", 28, 8, "right"), "N": ("r209", 12, 1, "up"),
                                     "E": ("r212n", 1, 8, "left")},
      warps=[(d_center, ("hearthome_center", 5, 8, "up")), (d_mart, ("hearthome_mart", 5, 8, "up")),
             (d_gym, ("hearthome_gym", 7, 10, "up")), (d_h1, ("hearthome_house1", 4, 6, "up")),
             (d_bebe, ("hearthome_bebe", 4, 6, "up"))],
      npcs=[npc(5, 9, "rival", "rival_hearthome", "right", name="帕尔", hide="beat_rival3"),
            npc(15, 10, "villager", "hearthome_villager", "down", name="市民")],
      signs={(12, 10): "家缘市\n温馨之家\n道馆馆主:梅丽莎(幽灵系)"})
    MAP_LIST.append(center("hearthome", "家缘市", ("hearthome", 3, 5, "down")))
    MAP_LIST.append(mart("hearthome", "家缘市", "mid", ("hearthome", 10, 5, "down")))

    # ------------------------------------------------------------ 随意镇
    g = Grid(22, 14)
    g.vline(10, 1, 12, "p")
    g.vline(11, 1, 12, "p")
    g.hline(2, 20, 7, "p")
    d_center = g.building(3, 2, 6, "Y")
    d_mart = g.building(13, 2, 6, "R")
    d_h1 = g.building(13, 8, 4, "R")
    g.building(3, 8, 6, "Q", door=False)      # 遗迹(装饰)
    g.set(8, 7, "S")
    g.open_exit("S", 10, 11)
    g.open_exit("N", 10, 11)
    T("solaceon", "随意镇", g, exits={"S": ("r210s", 10, 1, "up"), "N": ("r210n", 10, 28, "up")},
      warps=[(d_center, ("solaceon_center", 5, 8, "up")), (d_mart, ("solaceon_mart", 5, 8, "up")),
             (d_h1, ("solaceon_house1", 4, 6, "up"))],
      npcs=[npc(11, 10, "villager", "solaceon_villager", "down", name="村民")],
      signs={(8, 7): "随意镇\n悠闲的乡村\n南:随意遗迹"})
    MAP_LIST.append(center("solaceon", "随意镇", ("solaceon", 4, 5, "down")))
    MAP_LIST.append(mart("solaceon", "随意镇", "mid", ("solaceon", 14, 5, "down")))

    # ------------------------------------------------------------ 帷幕市
    g = Grid(26, 18)
    g.vline(12, 1, 16, "p")
    g.vline(13, 1, 16, "p")
    g.hline(1, 24, 8, "p")
    g.hline(1, 24, 9, "p")
    d_hq = g.building(2, 2, 6, "R")
    d_gym = g.building(10, 2, 6, "Q")
    d_dept = g.building(18, 2, 6, "R")
    d_mart = g.building(2, 11, 6, "R")
    g.building(9, 12, 6, "R", door=False)      # 游戏城(装饰)
    d_center = g.building(18, 11, 6, "Y")
    d_warehouse = g.building(17, 6, 4, "R")  # hmm 仓库在东北角
    g.set(12, 10, "S")
    g.open_exit("S", 12, 13)
    g.open_exit("E", 8, 9)
    T("veilstone", "帷幕市", g, exits={"S": ("r214", 12, 1, "up"), "E": ("r213", 1, 8, "left")},
      warps=[(d_hq, ("galactic_veilstone", 5, 9, "up")), (d_gym, ("veilstone_gym", 7, 10, "up")),
             (d_dept, ("veilstone_dept", 5, 8, "up")), (d_mart, ("veilstone_mart", 5, 8, "up")),
             (d_center, ("veilstone_center", 5, 8, "up")), (d_warehouse, ("veilstone_warehouse", 5, 7, "up"))],
      npcs=[npc(3, 6, "galactic", "galactic_hq_door", "down", name="银河队手下", hide="hq_clear"),
            npc(16, 7, "lady", "dawn_pal", "down", name="小光", show="beat_gym3", hide="warehouse_clear"),
            npc(9, 11, "youth", "veilstone_youth", "right", name="短裤小子")],
      signs={(12, 10): "帷幕市\n面纱之城\n百货商店、银河队基地都在这里"})
    MAP_LIST.append(center("veilstone", "帷幕市", ("veilstone", 20, 13, "down")))
    MAP_LIST.append(mart("veilstone", "帷幕市", "late", ("veilstone", 3, 13, "down")))

    # ------------------------------------------------------------ 湿原市
    g = Grid(22, 16)
    g.vline(10, 1, 14, "p")
    g.vline(11, 1, 14, "p")
    g.hline(1, 20, 8, "p")
    g.hline(1, 20, 9, "p")
    d_gate = g.building(8, 2, 6, "Q")
    d_h1 = g.building(2, 2, 4, "R")
    d_mart = g.building(15, 2, 6, "R")
    d_center = g.building(2, 9, 6, "Y")
    d_gym = g.building(15, 9, 6, "Q")
    g.set(13, 7, "S")
    for x, y in ((7, 12), (14, 12)):
        g.set(x, y, "f")
    g.open_exit("N", 10, 11)
    g.open_exit("E", 8, 9)
    T("pastoria", "湿原市", g, enc="pastoria_city", exits={"N": ("r212e", 10, 28, "up"), "E": ("r213", 28, 8, "right")},
      warps=[(d_gate, ("pastoria_marsh_gate", 5, 6, "up")), (d_h1, ("pastoria_house1", 4, 6, "up")),
             (d_mart, ("pastoria_mart", 5, 8, "up")), (d_center, ("pastoria_center", 5, 8, "up")),
             (d_gym, ("pastoria_gym", 7, 10, "up"))],
      npcs=[npc(9, 10, "rival", "rival_pastoria", "left", name="帕尔", show="badge_fen",
               hide="beat_rival4")],
      signs={(13, 7): "湿原市\n泥泞之城\n北:大湿地  道馆馆主:吉宪(水系)"})
    MAP_LIST.append(center("pastoria", "湿原市", ("pastoria", 3, 11, "down")))
    MAP_LIST.append(mart("pastoria", "湿原市", "mid", ("pastoria", 16, 5, "down")))

    # ------------------------------------------------------------ 水脉市
    g = Grid(24, 16)
    g.hline(1, 22, 8, "p")
    g.hline(1, 22, 9, "p")
    g.vline(11, 1, 8, "p")
    g.vline(12, 1, 8, "p")
    d_gym = g.building(2, 2, 6, "Q")
    g.building(9, 2, 6, "R", door=False)      # 图书馆(装饰)
    d_center = g.building(15, 2, 6, "Y")
    d_mart = g.building(15, 9, 6, "R")
    d_h1 = g.building(2, 10, 4, "R")
    for x in range(2, 22):
        g.set(x, 14, "w")
    g.set(13, 8, "S")
    g.open_exit("E", 8, 9)
    g.open_exit("S", 11, 12, "w")
    T("canalave", "水脉市", g, exits={"E": ("r218", 1, 8, "left"), "S": ("r221", 10, 1, "up")},
      warps=[(d_gym, ("canalave_gym", 7, 10, "up")), (d_center, ("canalave_center", 5, 8, "up")),
             (d_mart, ("canalave_mart", 5, 8, "up")), (d_h1, ("canalave_house1", 4, 6, "up"))],
      npcs=[npc(17, 13, "sailor", "iron_sailor", "down", name="船夫")],
      signs={(13, 8): "水脉市\n运河之城\n道馆馆主:东瓜(钢系)"})
    MAP_LIST.append(center("canalave", "水脉市", ("canalave", 16, 5, "down")))
    MAP_LIST.append(mart("canalave", "水脉市", "late", ("canalave", 16, 11, "down")))

    # ------------------------------------------------------------ 神和镇
    g = Grid(20, 14)
    g.hline(1, 18, 7, "p")
    g.hline(1, 18, 8, "p")
    g.vline(9, 1, 7, "p")
    g.building(9, 1, 4, "Q", door=False)      # 神和遗迹(室外交互)
    d_center = g.building(2, 2, 6, "Y")
    d_mart = g.building(13, 2, 4, "R")
    d_elder = g.building(13, 9, 4, "R")
    g.set(4, 7, "S")
    g.open_exit("W", 7, 8)
    g.open_exit("E", 7, 8)
    T("celestic", "神和镇", g, enc="celestic_town", exits={"W": ("r211e", 28, 7, "right"), "E": ("r210w", 1, 7, "left")},
      warps=[(d_center, ("celestic_center", 5, 8, "up")), (d_mart, ("celestic_mart", 5, 8, "up")),
             (d_elder, ("celestic_elder", 4, 6, "up"))],
      npcs=[npc(10, 4, "boss", "cyrus_celestic", "down", name="赤日", hide="celestic_cyrus"),
            npc(9, 5, "galactic", "galactic_celestic", "up", name="银河队手下", hide="celestic_cyrus"),
            npc(11, 9, "lady", "celestic_lady", "down", name="居民")],
      signs={(4, 7): "神和镇\n传承古老传说的小镇"})
    MAP_LIST.append(center("celestic", "神和镇", ("celestic", 3, 5, "down")))
    MAP_LIST.append(mart("celestic", "神和镇", "mid", ("celestic", 14, 5, "down")))

    # ------------------------------------------------------------ 雪峰市
    g = Grid(22, 16, fill="x", border="T")
    g.vline(10, 1, 14, "p")
    g.vline(11, 1, 14, "p")
    g.hline(1, 20, 8, "p")
    g.hline(1, 20, 9, "p")
    g.building(2, 2, 6, "Q", door=False)      # 雪峰神殿(装饰)
    d_gym = g.building(8, 2, 6, "Q")
    d_h1 = g.building(15, 2, 4, "R")
    d_center = g.building(2, 9, 6, "Y")
    d_mart = g.building(15, 9, 6, "R")
    for x, y in ((7, 7), (14, 7), (7, 13)):
        g.set(x, y, "X")
    g.set(13, 8, "S")
    g.open_exit("S", 10, 11)
    T("snowpoint", "雪峰市", g, exits={"S": ("r217", 10, 28, "up")},
      warps=[(d_gym, ("snowpoint_gym", 7, 10, "up")), (d_h1, ("snowpoint_house1", 4, 6, "up")),
             (d_center, ("snowpoint_center", 5, 8, "up")), (d_mart, ("snowpoint_mart", 5, 8, "up"))],
      npcs=[npc(8, 10, "skier", "snowpoint_villager", "down", name="滑雪客"),
            npc(17, 14, "sailor", "snowpoint_sailor", "down", name="船夫")],
      signs={(13, 8): "雪峰市\n冰雪之城\n道馆馆主:小菘(冰系)"})
    MAP_LIST.append(center("snowpoint", "雪峰市", ("snowpoint", 3, 11, "down")))
    MAP_LIST.append(mart("snowpoint", "雪峰市", "late", ("snowpoint", 16, 11, "down")))

    # ------------------------------------------------------------ 滨海市
    g = Grid(26, 18)
    g.hline(1, 24, 8, "p")
    g.hline(1, 24, 9, "p")
    g.vline(12, 1, 8, "p")
    g.vline(13, 1, 8, "p")
    d_center = g.building(2, 2, 6, "Y")
    d_mart = g.building(9, 2, 6, "R")
    d_gym = g.building(17, 2, 6, "Q")
    d_market = g.building(17, 12, 6, "R")
    g.hline(1, 24, 1, "s")
    g.set(22, 1, "*")
    g.set(12, 10, "S")
    g.rect(0, 0, 25, 0, "w")
    g.open_exit("N", 12, 13, "w")
    g.open_exit("W", 8, 9)
    for x in (2, 7, 15):
        g.set(x, 14, "f")
    T("sunyshore", "滨海市", g, enc="sunyshore_city", exits={"W": ("r222", 28, 8, "right"), "N": ("r223", 12, 28, "up")},
      warps=[(d_center, ("sunyshore_center", 5, 8, "up")), (d_mart, ("sunyshore_mart", 5, 8, "up")),
             (d_gym, ("sunyshore_gym", 7, 10, "up")), (d_market, ("sunyshore_market", 5, 7, "up"))],
      npcs=[npc(8, 10, "youth", "sunyshore_youth", "right", name="短裤小子")],
      signs={(12, 10): "滨海市\n阳光普照的海滨之城\n道馆馆主:电次(电系)"},
      items={(22, 1): (D.item_by_tm(7, hm=True), 1)})
    MAP_LIST.append(center("sunyshore", "滨海市", ("sunyshore", 3, 5, "down")))
    MAP_LIST.append(mart("sunyshore", "滨海市", "late", ("sunyshore", 10, 5, "down")))

    # ------------------------------------------------------------ 宝可梦联盟
    g = Grid(20, 14)
    g.vline(9, 1, 12, "p")
    g.vline(10, 1, 12, "p")
    d_league = g.building(6, 1, 8, "Q")
    for x, y in ((3, 8), (16, 8), (3, 12), (16, 12)):
        g.set(x, y, "f")
    g.open_exit("S", 9, 10)
    T("league", "宝可梦联盟", g, exits={"S": ("victory_road_peak", 9, 6, "down")},
      warps=[(d_league, ("league_gate", 5, 7, "up"))],
      npcs=[npc(5, 6, "officer", "league_officer", "right", name="联盟工作人员")],
      signs={(14, 6): "宝可梦联盟\n神奥联盟总部\n四天王在此等待挑战者"})
    return MAP_LIST
