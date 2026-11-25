"""洞窟/森林/设施:黑金闸口、黑金炭坑、荒芜小道、谷间发电厂、百代森林、丧失塔、天冠山、
枪之柱、大湿地、钢铁岛、冠军之路。"""
from .. import data as D
from . import Map, Grid, npc, grass
from .routes import tn

MAP_LIST = []


def Dn(map_id, name, g, enc=None, **kw):
    kw.setdefault("cave", True)
    m = Map(map_id, name, g.rows(), enc=enc, **kw)
    MAP_LIST.append(m)
    return m


def Out(map_id, name, g, enc=None, **kw):
    m = Map(map_id, name, g.rows(), enc=enc, **kw)
    MAP_LIST.append(m)
    return m


def cave(w, h, floor="c", wall="C"):
    g = Grid(w, h, fill=wall, border=wall)
    return g


def corridor(g, pts, floor="c"):
    """沿折线开凿走廊:pts 为依次经过的点,相邻点之间为直线。"""
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 == x1:
            g.rect(x0 - 1, min(y0, y1), x0 + 1, max(y0, y1), floor)
        else:
            g.rect(min(x0, x1), y0 - 1, max(x0, x1), y0 + 1, floor)


def build():
    # ------------------------------------------------------------ 黑金闸口
    g = cave(28, 14)
    corridor(g, [(1, 7), (24, 7)])
    g.rect(6, 4, 10, 10, "c")
    g.rect(16, 3, 20, 11, "c")
    g.set(8, 6, "K")
    g.set(18, 9, "K")
    g.set(24, 7, "I")
    g.open_exit("W", 7, 8, "c")
    Dn("oreburgh_gate_1", "黑金闸口", g, "oreburgh_gate_1f",
       exits={"W": ("r203", 28, 8, "right")},
       warps=[((24, 7), ("oreburgh_gate_b1", 2, 7, "right"))],
       npcs=[tn(12, 8, 195, "down", 3)],
       items={(17, 4): ("精灵球", 2)})
    g = cave(28, 14)
    corridor(g, [(1, 7), (26, 7)])
    g.rect(8, 3, 14, 11, "c")
    g.rect(10, 6, 13, 8, "w")
    g.rect(18, 4, 23, 10, "c")
    g.set(20, 6, "K")
    g.set(22, 8, "K")
    g.set(1, 7, "H")
    g.open_exit("E", 7, 8, "c")
    Dn("oreburgh_gate_b1", "黑金闸口 地下1层", g, "oreburgh_gate_b1f",
       exits={"E": ("oreburgh", 1, 8, "left")},
       warps=[((1, 7), ("oreburgh_gate_1", 23, 7, "left"))],
       items={(23, 5): ("解毒药", 1), (9, 4): ("伤药", 1)})

    # ------------------------------------------------------------ 黑金炭坑
    g = cave(20, 16)
    corridor(g, [(1, 7), (16, 7)])
    g.rect(5, 4, 9, 10, "c")
    g.rect(11, 3, 15, 11, "c")
    for x, y in ((6, 6), (13, 9), (8, 8)):
        g.set(x, y, "K")
    g.set(16, 7, "I")
    g.open_exit("W", 7, 8, "c")
    Dn("oreburgh_mine_1", "黑金炭坑", g, "oreburgh_mine_1f",
       exits={"W": ("oreburgh", 22, 8, "right")},
       warps=[((16, 7), ("oreburgh_mine_b1", 2, 7, "right"))],
       npcs=[npc(7, 5, "hiker", "mine_worker", "down", name="矿工")],
       items={(14, 4): ("力量强化", 1)})
    g = cave(20, 16)
    corridor(g, [(1, 7), (17, 7)])
    g.rect(4, 3, 16, 12, "c")
    g.set(1, 7, "H")
    for x, y in ((7, 5), (12, 10), (9, 9)):
        g.set(x, y, "K")
    Dn("oreburgh_mine_b1", "黑金炭坑 地下1层", g, "oreburgh_mine_b1f",
       warps=[((1, 7), ("oreburgh_mine_1", 15, 7, "left"))],
       npcs=[npc(6, 6, "hiker", "mine_hiker_hm", "down", name="登山男"),
             npc(14, 6, "leader", "roark_mine", "down", name="瓢太", hide="roark_returned"),
             tn(11, 11, 18, "up", 3)],
       items={(16, 4): ("好伤药", 1), (5, 11): ("解毒药", 1)})

    # ------------------------------------------------------------ 荒芜小道
    g = cave(20, 14)
    corridor(g, [(10, 1), (10, 12)])
    g.rect(3, 4, 16, 9, "c")
    g.rect(4, 5, 8, 8, "w")
    g.open_exit("S", 10, 11, "c")
    g.open_exit("N", 10, 11, "c")
    Dn("ravaged_path", "荒芜小道", g, "ravaged_path",
       exits={"S": ("r204s", 10, 28, "down"), "N": ("r204n", 10, 28, "up")},
       items={(15, 5): ("好伤药", 1), (3, 8): ("解眠药", 1)})

    # ------------------------------------------------------------ 谷间发电厂
    g = Grid(20, 14)
    g.hline(1, 18, 7, "p")
    g.hline(1, 18, 8, "p")
    d_ww = g.building(8, 2, 8, "R")
    g.open_exit("W", 7, 8)
    grass(g, [(2, 2, 6, 5), (13, 10, 17, 12)])
    Out("valley_windworks", "谷间发电厂", g, "valley_windworks",
        exits={"W": ("r205s", 28, 8, "right")},
        warps=[(d_ww, ("valley_windworks_in", 5, 6, "up"))],
        rules={d_ww: ("windworks_clear", "门被锁住了。\n银河队的人好像在里面捣乱。")},
        npcs=[npc(9, 6, "galactic", "galactic_ww1", "down", name="银河队手下", hide="windworks_clear"),
              npc(13, 6, "galactic", "galactic_ww2", "down", name="银河队手下", hide="windworks_clear"),
              npc(11, 6, "commander", "mars_windworks", "down", name="伙星", hide="windworks_clear")],
        signs={(3, 6): "谷间发电厂\n为神奥地区供应电力"})
    Out("valley_windworks_in", "谷间发电厂 内部", Grid(10, 7, fill="o", border="#"), indoor=True,
        warps=[((5, 6), ("valley_windworks", 12, 5, "down"))],
        npcs=[npc(2, 2, "scientist", "windworks_scientist", "down", name="研究员")])
    MAP_LIST[-1].rows = [list(r) for r in [
        "##########", "#o......t#", "#o......o#", "#o.t..t.o#", "#o......o#", "#oooEEEoo#", "#####D####"]]

    # ------------------------------------------------------------ 百代森林
    g = Grid(32, 16)
    g.hline(1, 30, 7, "p")
    g.hline(1, 30, 8, "p")
    for x0, y0, x1, y1 in [(1, 1, 30, 5), (1, 10, 30, 14)]:
        g.rect(x0, y0, x1, y1, ",")
    for x in range(2, 30, 3):
        g.set(x, 3, "T")
        g.set(x + 1, 12, "T")
    g.set(6, 10, "J")          # 可砍的树丛(捷径)
    g.set(24, 3, "J")
    g.open_exit("W", 7, 8)
    g.open_exit("E", 8, 9)
    Out("eterna_forest", "百代森林", g, "eterna_forest", tag="eterna_forest",
        exits={"W": ("r205e", 10, 28, "up"), "E": ("eterna", 1, 8, "left")},
        npcs=[npc(29, 8, "champion", "cynthia_forest", "left", name="竹兰", hide="met_cynthia_forest"),
              tn(6, 6, 20, "down", 3), tn(12, 9, 205, "up", 3), tn(19, 6, 206, "down", 3),
              tn(25, 9, 259, "up", 3)],
        signs={(3, 9): "百代森林\n光线昏暗的森林"},
        items={(30, 1): ("好伤药", 1), (2, 14): ("解眠药", 1), (16, 13): ("精灵球", 3)})

    # ------------------------------------------------------------ 丧失塔
    g = Grid(12, 14, fill="#", border="#")
    g.rect(2, 2, 9, 12, "o")
    g.set(5, 13, "D")
    g.set(2, 2, "H")
    Out("lost_tower_1", "丧失塔", g, "lost_tower_1f", indoor=True, cave=False,
        warps=[((5, 13), ("r209", 5, 13, "down")), ((2, 2), ("lost_tower_top", 2, 12, "up"))],
        npcs=[npc(8, 4, "lady", "lost_tower_lady", "down", name="扫墓人")])
    g = Grid(12, 14, fill="#", border="#")
    g.rect(2, 2, 9, 12, "o")
    g.set(2, 12, "H")
    g.set(9, 2, "*")
    Out("lost_tower_top", "丧失塔 顶层", g, "lost_tower_5f", indoor=True, cave=False,
        warps=[((2, 12), ("lost_tower_1", 2, 3, "down"))],
        npcs=[npc(5, 4, "elder", "lost_tower_elder", "down", name="老婆婆")],
        items={(9, 2): (D.item_by_tm(4, hm=True), 1)})

    # ------------------------------------------------------------ 天冠山(南)
    g = cave(20, 30)
    corridor(g, [(10, 28), (10, 16), (5, 16), (5, 10), (10, 10), (10, 2), (18, 2)])
    g.rect(4, 5, 15, 12, "c")
    g.rect(12, 18, 17, 23, "c")
    g.set(12, 3, "I")
    g.open_exit("S", 10, 11, "c")
    g.open_exit("N", 17, 18, "c")
    Dn("coronet_south", "天冠山", g, "mt_coronet_1f_route_207",
       exits={"S": ("r207", 10, 28, "down"), "N": ("r208", 28, 8, "right")},
       warps=[((12, 3), ("coronet_west", 2, 4, "right"))],
       npcs=[tn(8, 8, 443, "down", 3), tn(15, 20, 74, "left", 3)],
       items={(16, 6): ("好伤药", 1), (14, 22): ("解毒药", 1)})

    # ------------------------------------------------------------ 天冠山(西):211 西入口、218 海侧入口、通往山顶
    g = cave(28, 20)
    corridor(g, [(1, 4), (6, 4), (6, 8), (26, 8)])
    corridor(g, [(1, 8), (6, 8)])
    g.rect(6, 2, 12, 10, "c")
    g.rect(13, 2, 15, 9, "c")              # 通往上山楼梯
    g.rect(14, 12, 26, 17, "c")
    g.rect(13, 8, 26, 13, "w")             # 通往 218 的水面,需要冲浪
    g.set(14, 2, "I")
    g.set(1, 4, "H")
    g.set(9, 6, "K")
    g.open_exit("W", 8, 9, "c")
    g.open_exit("E", 14, 15, "w")
    Dn("coronet_west", "天冠山", g, "mt_coronet_1f_route_211",
       exits={"W": ("r211w", 28, 8, "right"), "E": ("r218", 28, 8, "left")},
       warps=[((1, 4), ("coronet_south", 11, 3, "left")), ((14, 2), ("coronet_peak", 2, 22, "right"))],
       items={(24, 16): ("暗之石", 1), (7, 9): ("高级球", 1)})

    # ------------------------------------------------------------ 天冠山(东):211 东入口
    g = cave(28, 14)
    corridor(g, [(26, 7), (10, 7), (10, 3), (2, 3)])
    g.rect(8, 2, 14, 10, "c")
    g.set(2, 3, "I")
    g.open_exit("E", 7, 8, "c")
    Dn("coronet_east", "天冠山", g, "mt_coronet_1f_route_216",
       exits={"E": ("r211e", 1, 7, "left")},
       warps=[((2, 3), ("coronet_peak", 20, 22, "left"))],
       items={(13, 9): ("全复药", 1)})

    # ------------------------------------------------------------ 天冠山 山顶
    g = cave(24, 26)
    corridor(g, [(2, 22), (2, 14), (12, 14), (12, 25)])
    corridor(g, [(12, 14), (12, 2), (10, 2)])
    corridor(g, [(12, 18), (20, 18), (20, 22)])
    g.rect(6, 6, 18, 12, "c")
    g.rect(8, 7, 16, 11, "w")
    g.set(2, 22, "H")
    g.set(20, 22, "H")
    for x in range(8, 17):
        g.set(x, 3, "x")
    g.open_exit("N", 11, 12, "x")
    Dn("coronet_peak", "天冠山 山顶", g, "mt_coronet_exterior_snowfall",
       exits={"N": ("spear_pillar", 10, 1, "up")},
       warps=[((2, 22), ("coronet_west", 13, 2, "down")), ((20, 22), ("coronet_east", 3, 2, "down"))],
       npcs=[tn(8, 12, 132, "down", 3), tn(16, 12, 135, "left", 3)],
       items={(17, 12): ("全复药", 1), (7, 12): ("高级球", 1)})

    # ------------------------------------------------------------ 枪之柱
    g = Grid(20, 14, fill="o", border="C")
    for x in range(2, 18, 3):
        g.set(x, 2, "C")
        g.set(x, 11, "C")
    g.open_exit("S", 10, 11, "o")
    Out("spear_pillar", "枪之柱", g, cave=True, exits={"S": ("coronet_peak", 12, 24, "down")},
        npcs=[npc(6, 6, "galactic", "galactic_spear_1", "right", name="银河队手下", hide="spear_cyrus"),
              npc(13, 6, "galactic", "galactic_spear_2", "left", name="银河队手下", hide="spear_cyrus"),
              npc(10, 5, "boss", "cyrus_spear", "down", name="赤日", hide="spear_cyrus"),
              npc(10, 3, "legendary", "spear_legendary", "down", name="???", show="spear_cyrus",
                  hide="spear_clear")],
        signs={(4, 9): "枪之柱\n神奥神话的中心。\n这里流传着时间与空间的传说。"})

    # ------------------------------------------------------------ 大湿地
    g = Grid(24, 20)
    for x0, y0, x1, y1 in [(1, 1, 22, 6), (1, 9, 10, 18), (14, 9, 22, 18)]:
        g.rect(x0, y0, x1, y1, ",")
    g.vline(11, 7, 18, "p")
    g.vline(12, 7, 18, "p")
    g.hline(11, 12, 1, "p")
    g.hline(11, 12, 19, "p")
    g.rect(3, 10, 8, 13, "w")
    g.rect(15, 11, 20, 14, "w")
    g.open_exit("S", 11, 12)
    Out("great_marsh", "大湿地", g, "great_marsh_area_3", safari=True, cave=False,
        exits={"S": ("pastoria_marsh_gate", 8, 4, "left")},
        items={(21, 2): ("高级球", 1), (2, 17): ("好伤药", 1)},
        signs={(13, 17): "大湿地\n湿原市的狩猎地带。\n在这里只能投掷狩猎球。"})

    # ------------------------------------------------------------ 钢铁岛
    g = cave(24, 18)
    corridor(g, [(22, 9), (12, 9), (12, 3), (4, 3)])
    g.rect(4, 3, 18, 14, "c")
    g.rect(8, 7, 15, 11, "c")
    g.open_exit("E", 9, 10, "c")
    Dn("iron_island", "钢铁岛", g, "iron_island_1f",
       exits={"E": ("canalave", 17, 13, "down")},
       npcs=[npc(6, 4, "youth", "riley", "down", name="亚玄"),
             tn(10, 10, 503, "down", 3), tn(16, 13, 845, "left", 3)],
       items={(20, 5): ("金属膜", 1), (5, 13): ("全复药", 1)})

    # ------------------------------------------------------------ 冠军之路
    g = cave(24, 26)
    corridor(g, [(12, 24), (12, 20), (5, 20), (5, 14), (12, 14), (18, 14), (18, 4), (20, 4)])
    g.rect(4, 12, 19, 16, "c")
    g.rect(16, 3, 21, 8, "c")
    g.set(12, 22, "K")
    g.set(5, 17, "K")
    g.set(18, 11, "O")
    g.set(18, 9, "c")
    g.set(20, 4, "I")
    g.open_exit("S", 12, 13, "c")
    Dn("victory_road_1", "冠军之路", g, "victory_road_1f",
       exits={"S": ("r224", 10, 14, "down")},
       warps=[((20, 4), ("victory_road_2", 2, 3, "right"))],
       npcs=[tn(8, 15, 225, "down", 3), tn(15, 15, 231, "left", 3), tn(18, 6, 444, "left", 3)],
       items={(4, 13): ("全复药", 1), (20, 12): ("活力块", 1), (21, 3): (D.item_by_tm(59), 1)})
    g = cave(24, 26)
    corridor(g, [(2, 3), (8, 3), (8, 8), (12, 8), (12, 11)])
    g.rect(6, 6, 18, 13, "c")
    g.rect(7, 14, 17, 23, "w")
    g.rect(10, 11, 13, 13, "c")
    g.set(11, 12, "W")
    g.set(12, 12, "W")
    g.rect(10, 5, 13, 6, "c")
    g.rect(10, 1, 13, 5, "c")
    g.set(2, 3, "H")
    g.open_exit("N", 11, 12, "c")
    Dn("victory_road_2", "冠军之路", g, "victory_road_2f",
       exits={"N": ("victory_road_peak", 12, 7, "up")},
       warps=[((2, 3), ("victory_road_1", 19, 4, "left"))],
       npcs=[tn(10, 8, 226, "down", 3), tn(16, 12, 227, "left", 3), tn(8, 13, 228, "down", 3)],
       items={(17, 7): ("全复药", 1), (7, 22): ("高级球", 1)})
    g = Grid(24, 14)
    g.rect(2, 2, 21, 11, "c")
    g.rect(9, 11, 12, 12, "p")
    g.open_exit("S", 10, 11, "c")
    g.open_exit("N", 9, 10)
    Out("victory_road_peak", "冠军之路 出口", g, cave=True,
        exits={"S": ("victory_road_2", 11, 23, "down"), "N": ("league", 9, 5, "down")},
        npcs=[npc(12, 5, "rival", "rival_victory", "left", name="帕尔", show="badge_beacon",
                  hide="beat_rival5")],
        signs={(3, 3): "前方就是宝可梦联盟。\n四天王与冠军在那里等候。"})
    return MAP_LIST
