"""室内地图:精灵中心/友好商店/民宅模板,以及研究所、学校、银河队基地等特殊室内。

坐标约定:门 'D' 在底部中央 (5,8),出口垫 'E' 在 (5,7)。back = (室外地图, x, y, 朝向)。
"""
from .. import data as D
from . import Map, npc, register

# ---------------------------------------------------------------- 商店库存
SHOP_STOCK = {
    "basic": [("精灵球", 200), ("伤药", 300), ("解毒药", 100), ("解麻药", 200)],
    "jubilife": [("精灵球", 200), ("伤药", 300), ("超级球", 600), ("好伤药", 700), ("解毒药", 100),
                 ("解麻药", 200), ("解眠药", 250), ("灼伤药", 250), ("解冻药", 250), ("巢穴球", 1000),
                 ("除虫喷雾", 350)],
    "mid": [("精灵球", 200), ("超级球", 600), ("伤药", 300), ("好伤药", 700), ("厉害伤药", 1200),
            ("解毒药", 100), ("解麻药", 200), ("解眠药", 250), ("灼伤药", 250), ("解冻药", 250),
            ("全复药", 600), ("活力碎片", 1500), ("巢穴球", 1000), ("捕网球", 1000), ("黑暗球", 1000),
            ("除虫喷雾", 350), ("白银喷雾", 500), ("离洞绳", 550)],
    "late": [("超级球", 600), ("高级球", 1200), ("厉害伤药", 1200), ("全满药", 2500), ("全复药", 3000),
             ("活力碎片", 1500), ("活力块", 4000), ("万灵药", 600), ("ＰＰ单项小补剂", 1200),
             ("黑暗球", 1000), ("先机球", 1000), ("计时球", 1000), ("重复球", 1000), ("治愈球", 300),
             ("力量强化", 500), ("防御强化", 550), ("速度强化", 350), ("命中强化", 950),
             ("白银喷雾", 500), ("黄金喷雾", 700), ("离洞绳", 550)],
    "league": [("高级球", 1200), ("厉害伤药", 1200), ("全满药", 2500), ("全复药", 3000), ("活力碎片", 1500),
               ("活力块", 4000), ("万灵药", 600), ("ＰＰ单项小补剂", 1200), ("计时球", 1000), ("先机球", 1000)],
    "stones": [("雷之石", 2100), ("火之石", 2100), ("水之石", 2100), ("叶之石", 2100), ("光之石", 2100),
               ("暗之石", 2100), ("觉醒之石", 2100), ("日之石", 2100), ("月之石", 2100)],
    "hold": [("王者之证", 100), ("金属膜", 100), ("龙之鳞片", 2100), ("护具", 2100), ("电力增幅器", 2100),
             ("熔岩增幅器", 2100), ("升级数据", 2100), ("可疑补丁", 2100), ("灵界之布", 2100),
             ("锐利之爪", 2100), ("锐利之牙", 2100), ("连线电缆", 2100), ("美丽鳞片", 3000)],
    "tms": None,        # 在 tm_stock() 中按道具数据生成
}


def tm_stock():
    if SHOP_STOCK["tms"] is None:
        from .. import data
        want = [4, 6, 9, 11, 13, 14, 16, 17, 18, 20, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33,
                34, 35, 36, 37, 38, 39, 40, 42, 44, 45, 47, 51, 52, 53, 56, 58, 59, 61, 62, 64, 65,
                66, 68, 69, 70, 71, 72, 73, 74, 75, 76, 78, 79, 80, 81, 84, 85, 86, 87, 88, 89, 91]
        lst = []
        for num in want:
            name = data.item_by_tm(num)
            if name:
                lst.append((name, data.ITEMS[name]["price"] or 3000))
        SHOP_STOCK["tms"] = lst
    return SHOP_STOCK["tms"]


# ---------------------------------------------------------------- 模板
def center(town_id, town_name, back):
    """精灵中心:护士柜台 'N'(3..6,2),电脑 'P'(8,1)。"""
    rows = [
        "##########",
        "#o......P#",
        "#o.NNNN.o#",
        "#o......o#",
        "#o......o#",
        "#o......o#",
        "#o......o#",
        "#oooEEEoo#",
        "#####D####",
    ]
    return Map(f"{town_id}_center", f"{town_name}精灵中心", rows, warps=[((5, 8), back)],
               npcs=[npc(4, 1, "nurse", "nurse", "down")], indoor=True)


def mart(town_id, town_name, stock, back):
    rows = [
        "##########",
        "#o..M...Z#",
        "#o.MMMM.Z#",
        "#o......o#",
        "#Z......Z#",
        "#o......o#",
        "#o......o#",
        "#oooEEEoo#",
        "#####D####",
    ]
    stock_list = SHOP_STOCK[stock] if isinstance(stock, str) else stock
    m = Map(f"{town_id}_mart", f"{town_name}友好商店", rows, warps=[((5, 8), back)], indoor=True)
    m.stock = stock_list
    return m


def house(town_id, n, back, npc_def=None, name="民宅", layout=0):
    rows = [
        "#########",
        "#o.....Z#",
        "#ob....o#",
        "#o.....o#",
        "#o.....o#",
        "#o.....o#",
        "#oooEEoo#",
        "####D####",
    ]
    if layout == 1:
        rows = [
            "#########",
            "#Z.....t#",
            "#o.....o#",
            "#o.....o#",
            "#o.....b#",
            "#o.....o#",
            "#oooEEoo#",
            "####D####",
        ]
    npcs = [npc_def] if npc_def else []
    return Map(f"{town_id}_house{n}", name, rows, warps=[((4, 7), back)], npcs=npcs, indoor=True)


# ---------------------------------------------------------------- 特殊室内
def build_special():
    """研究所、学校、银河队基地、百货、市场等;返回地图列表。"""
    maps = []
    # 双叶镇自宅(玩家):一楼
    maps.append(Map("twinleaf_home", "自宅", [
        "##########",
        "#Z......b#",
        "#o......o#",
        "#o.t..t.o#",
        "#o......o#",
        "#o......o#",
        "#oooEEEoo#",
        "#####D####",
    ], warps=[((5, 7), ("twinleaf", 3, 14, "down"))],
        npcs=[npc(3, 2, "mom", "mom", "down")], indoor=True))
    # 双叶镇劲敌家
    maps.append(Map("twinleaf_rival", "劲敌的家", [
        "##########",
        "#Z......b#",
        "#o......o#",
        "#o.t..t.o#",
        "#o......o#",
        "#o......o#",
        "#oooEEEoo#",
        "#####D####",
    ], warps=[((5, 7), ("twinleaf", 3, 4, "down"))],
        npcs=[npc(6, 2, "lady", "rival_mom", "down"), npc(2, 4, "villager", "rival_dad", "right")],
        indoor=True))
    # 双叶镇另一户
    maps.append(Map("twinleaf_house1", "民宅", [
        "#########",
        "#o.....Z#",
        "#ob....o#",
        "#o.....o#",
        "#o.....o#",
        "#oooEEoo#",
        "####D####",
    ], warps=[((4, 6), ("twinleaf", 17, 4, "down"))],
        npcs=[npc(2, 3, "villager", "twinleaf_villager", "down")], indoor=True))
    # 真砂镇研究所(山梨博士)
    maps.append(Map("sandgem_lab", "山梨博士的研究所", [
        "############",
        "#ZZ......ZZ#",
        "#o........o#",
        "#o..123...o#",      # 桌上三只精灵球 (4,3)(5,3)(6,3)
        "#oooooooooo#",
        "#oooooooooo#",
        "#oooEEEEooo#",
        "#####D######",
    ], warps=[((5, 7), ("sandgem", 16, 9, "down"))],
        npcs=[npc(5, 2, "prof", "prof", "down"), npc(8, 2, "scientist", "aide", "down")], indoor=True))
    # 真砂镇民宅
    maps.append(Map("sandgem_house1", "民宅", [
        "#########",
        "#Z.....t#",
        "#o.....o#",
        "#o.....o#",
        "#o.....b#",
        "#oooEEoo#",
        "####D####",
    ], warps=[((4, 6), ("sandgem", 5, 6, "down"))],
        npcs=[npc(2, 3, "villager", "sandgem_villager", "down")], indoor=True))
    # 祝庆市训练家学校
    maps.append(Map("jubilife_school", "训练家学校", [
        "##########",
        "#Z......Z#",
        "#o......o#",
        "#o.t..t.o#",
        "#o......o#",
        "#o.t..t.o#",
        "#oooEEooo#",
        "#####D####",
    ], warps=[((5, 7), ("jubilife", 18, 3, "down"))],
        npcs=[npc(5, 2, "scientist", "school_teacher", "down"),
              npc(2, 5, "youth", "school_kid", "right", trainer=None)], indoor=True))
    # 祝庆市民宅
    maps.append(Map("jubilife_house1", "民宅", [
        "#########",
        "#o.....Z#",
        "#ob....o#",
        "#o.....o#",
        "#o.....o#",
        "#oooEEoo#",
        "####D####",
    ], warps=[((4, 6), ("jubilife", 5, 9, "down"))],
        npcs=[npc(2, 3, "villager", "jubilife_villager", "down")], indoor=True))
    # 黑金市民宅(送学习装置的博士助手在此)
    maps.append(Map("oreburgh_house1", "民宅", [
        "#########",
        "#o.....Z#",
        "#ob....o#",
        "#o.....o#",
        "#o.....o#",
        "#oooEEoo#",
        "####D####",
    ], warps=[((4, 6), ("oreburgh", 15, 7, "down"))],
        npcs=[npc(2, 3, "scientist", "aide_exp_share", "down")], indoor=True))
    # 黑金炭坑博物馆(简化:化石讲解)
    maps.append(Map("oreburgh_museum", "炭坑博物馆", [
        "##########",
        "#Z......Z#",
        "#o.t..t.o#",
        "#o......o#",
        "#o.t..t.o#",
        "#oooEEooo#",
        "#####D####",
    ], warps=[((5, 6), ("oreburgh", 9, 5, "down"))],
        npcs=[npc(5, 2, "scientist", "museum_guide", "down")], indoor=True))
    # 花苑镇花店
    maps.append(Map("floaroma_shop", "花店", [
        "#########",
        "#f.....f#",
        "#o.....o#",
        "#o.f.f.o#",
        "#o.....o#",
        "#oooEEoo#",
        "####D####",
    ], warps=[((4, 6), ("floaroma", 4, 5, "down"))],
        npcs=[npc(2, 2, "lady", "flower_shop", "down")], indoor=True))
    # 百代市自行车店(银河队事件后送自行车)
    maps.append(Map("eterna_shop", "自行车店", [
        "#########",
        "#Z.....t#",
        "#o.....o#",
        "#o.....o#",
        "#o.....o#",
        "#oooEEoo#",
        "####D####",
    ], warps=[((4, 6), ("eterna", 16, 5, "down"))],
        npcs=[npc(2, 3, "villager", "bike_shop", "down")], indoor=True))
    # 百代银河队基地
    maps.append(Map("galactic_eterna", "银河队百代基地", [
        "###########",
        "#C.......C#",
        "#.........#",
        "#C.......C#",
        "#.........#",
        "#C.......C#",
        "#oooEEEEoo#",
        "#####D#####",
    ], warps=[((5, 7), ("eterna", 19, 7, "down"))], indoor=True, cave=True,
        npcs=[npc(5, 5, "galactic", "galactic_et_1", "down", name="银河队手下"),
              npc(5, 3, "galactic", "galactic_et_2", "down", name="银河队手下"),
              npc(5, 1, "commander", "jupiter_eterna", "down", name="岁星")]))
    # 家缘市 宝可表公司/民宅/丝绒(伊布)
    maps.append(Map("hearthome_bebe", "丝绒的家", [
        "#########",
        "#o.....Z#",
        "#ob....o#",
        "#o.....o#",
        "#o.....o#",
        "#oooEEoo#",
        "####D####",
    ], warps=[((4, 6), ("hearthome", 20, 7, "down"))],
        npcs=[npc(2, 3, "lady", "bebe", "down")], indoor=True))
    maps.append(Map("hearthome_house1", "民宅", [
        "#########",
        "#Z.....t#",
        "#o.....o#",
        "#o.....o#",
        "#o.....b#",
        "#oooEEoo#",
        "####D####",
    ], warps=[((4, 6), ("hearthome", 4, 7, "down"))],
        npcs=[npc(2, 3, "villager", "hearthome_villager", "down")], indoor=True))
    # 帷幕百货(3 个柜台:道具/学习机/进化道具)
    maps.append(Map("veilstone_dept", "帷幕百货", [
        "############",
        "#o..MM.....#",
        "#o.MMMMM...#",
        "#o.........#",
        "#o..MM.....#",
        "#o.MMMMM...#",
        "#o.........#",
        "#oooEEEEooo#",
        "#####D######",
    ], warps=[((5, 8), ("veilstone", 18, 5, "down"))], indoor=True))
    # 帷幕银河队仓库
    maps.append(Map("veilstone_warehouse", "银河队仓库", [
        "##########",
        "#C..*...C#",
        "#........#",
        "#C......C#",
        "#........#",
        "#C......C#",
        "#o......o#",
        "#####D####",
    ], warps=[((5, 7), ("veilstone", 21, 2, "down"))], indoor=True, cave=True,
        items={(4, 1): (D.item_by_tm(2, hm=True), 1)},
        npcs=[npc(5, 5, "galactic", "galactic_wh_1", "down", name="银河队手下"),
              npc(5, 3, "galactic_f", "galactic_wh_2", "down", name="银河队手下")]))
    # 帷幕银河队总部
    maps.append(Map("galactic_veilstone", "银河队总部", [
        "############",
        "#C........C#",
        "#..........#",
        "#C...CC...C#",
        "#..........#",
        "#C...CC...C#",
        "#..........#",
        "#C........C#",
        "#o........o#",
        "#####D######",
    ], warps=[((5, 9), ("veilstone", 3, 2, "down"))], indoor=True, cave=True,
        npcs=[npc(5, 7, "galactic", "galactic_hq_1", "down", name="银河队手下"),
              npc(7, 5, "galactic_f", "galactic_hq_2", "down", name="银河队手下"),
              npc(7, 4, "galactic", "galactic_hq_3", "left", name="银河队手下"),
              npc(6, 2, "commander", "saturn_hq", "down", name="镇星")]))
    # 湿原大湿地入口
    maps.append(Map("pastoria_marsh_gate", "大湿地入口", [
        "##########",
        "#o......o#",
        "#o.NNNN.o#",
        "#o......o#",
        "#o......oD",
        "#oooEEooo#",
        "#####D####",
    ], warps=[((5, 6), ("pastoria", 11, 1, "down")), ((9, 4), ("great_marsh", 10, 16, "up"))],
        npcs=[npc(4, 1, "clerk", "marsh_clerk", "down")], indoor=True))
    # 神和镇长老家
    maps.append(Map("celestic_elder", "长老家", [
        "#########",
        "#Z.....t#",
        "#o.....o#",
        "#o.....o#",
        "#o.....b#",
        "#oooEEoo#",
        "####D####",
    ], warps=[((4, 6), ("celestic", 14, 8, "down"))],
        npcs=[npc(2, 2, "elder", "celestic_elder", "down")], indoor=True))
    # 滨海市场(进化石)
    maps.append(Map("sunyshore_market", "滨海市场", [
        "############",
        "#o.MMMM...Z#",
        "#o........Z#",
        "#Z.........#",
        "#o.MMMM....#",
        "#o.........#",
        "#oooEEEEooo#",
        "#####D######",
    ], warps=[((5, 7), ("sunyshore", 18, 12, "down"))], indoor=True))
    # 名胜区湖畔大酒店(简化:休息)
    maps.append(Map("lakefront_hotel", "湖畔大酒店", [
        "############",
        "#o.NNNN...b#",
        "#o........b#",
        "#o.........#",
        "#o.........#",
        "#oooEEEEooo#",
        "#####D######",
    ], warps=[((5, 6), ("valor_lakefront", 20, 6, "down"))], indoor=True))
    # 水脉市民宅 / 雪峰市民宅
    maps.append(Map("canalave_house1", "民宅", [
        "#########",
        "#Z.....t#",
        "#o.....o#",
        "#o.....o#",
        "#o.....b#",
        "#oooEEoo#",
        "####D####",
    ], warps=[((4, 6), ("canalave", 16, 6, "down"))],
        npcs=[npc(2, 3, "villager", "canalave_villager", "down")], indoor=True))
    maps.append(Map("snowpoint_house1", "民宅", [
        "#########",
        "#o.....Z#",
        "#ob....o#",
        "#o.....o#",
        "#o.....o#",
        "#oooEEoo#",
        "####D####",
    ], warps=[((4, 6), ("snowpoint", 16, 7, "down"))],
        npcs=[npc(2, 3, "villager", "snowpoint_villager", "down")], indoor=True))
    # 黑金市民宅 2 / 湿原市民宅 / 随意镇民宅
    maps.append(Map("pastoria_house1", "民宅", [
        "#########",
        "#o.....Z#",
        "#ob....o#",
        "#o.....o#",
        "#o.....o#",
        "#oooEEoo#",
        "####D####",
    ], warps=[((4, 6), ("pastoria", 4, 6, "down"))],
        npcs=[npc(2, 3, "villager", "pastoria_villager", "down")], indoor=True))
    maps.append(Map("solaceon_house1", "民宅", [
        "#########",
        "#Z.....t#",
        "#o.....o#",
        "#o.....o#",
        "#o.....b#",
        "#oooEEoo#",
        "####D####",
    ], warps=[((4, 6), ("solaceon", 16, 6, "down"))],
        npcs=[npc(2, 3, "villager", "solaceon_villager", "down")], indoor=True))
    # 宝可梦联盟大门(挑战四天王前恢复)
    # (左侧是友好商店柜台,与原作联盟大楼一致:挑战四天王前可以补给)
    maps.append(Map("league_gate", "宝可梦联盟", [
        "############",
        "#o..N.....P#",
        "#o.NNNN....#",
        "#o........D#",
        "#o..Z......#",
        "#o.MM......#",
        "#oooEEEEooo#",
        "#####D######",
    ], warps=[((5, 7), ("league", 9, 7, "down")), ((10, 3), ("e4_aaron", 6, 10, "up"))],
        npcs=[npc(5, 1, "nurse", "nurse", "down"),
              npc(2, 4, "officer", "league_gate_guard", "right")], indoor=True))
    by_id = {m.id: m for m in maps}
    by_id["sunyshore_market"].stock = SHOP_STOCK["stones"]
    by_id["league_gate"].stock = SHOP_STOCK["league"]
    by_id["veilstone_dept"].counters = [(2, "late"), (5, "tms")]   # (柜台行, 库存键)
    return maps


SPECIAL_MAPS = None


def get_special():
    global SPECIAL_MAPS
    if SPECIAL_MAPS is None:
        SPECIAL_MAPS = build_special()
    return SPECIAL_MAPS
