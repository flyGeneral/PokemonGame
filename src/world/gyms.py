"""神奥 8 个道馆(各有主题机关)与宝可梦联盟(四天王 4 间 + 冠军之间)。

机关:'K' 可碎岩石(碎岩) 'h' 树篱 'L' 拉杆(切换砖块) '^v<>' 箭头滑块 'i' 冰面(滑行)
      '4'-'7' 移动平台(传送) 'w' 水(道馆内不可通行,作为机关的"空位")
"""
from . import Map, Grid, npc
from .routes import tn

MAP_LIST = []


def G(map_id, name, rows, **kw):
    m = Map(map_id, name, rows, indoor=True, **kw)
    MAP_LIST.append(m)
    return m


def gym_rows(inner, w=16, h=12, door_x=7):
    """道馆外壳:G 墙 + g 地板,底部中央门。inner(y, x) → 覆盖图块或 None。"""
    rows = []
    for y in range(h):
        row = ""
        for x in range(w):
            if y == 0 or y == h - 1 or x == 0 or x == w - 1:
                row += "G"
            else:
                row += inner(x, y) or "g"
        rows.append(row)
    rows[h - 1] = rows[h - 1][:door_x] + "D" + rows[h - 1][door_x + 1:]
    return rows


def leader_npc(x, y, script, pal, name):
    return npc(x, y, pal, script, "down", name=name)


def guide_npc(x, y, script):
    return npc(x, y, "prof", script, "down", name="道馆向导")


def build():
    # ================================================================ 1 黑金道馆(岩石) 碎岩
    def oreburgh(x, y):
        if y == 5:
            return "G" if x in (7, 8) else "K"       # 整排岩石,需要碎岩开路
        if y == 8 and x in (5, 6, 9, 10):
            return "K"
        return None
    G("oreburgh_gym", "黑金道馆", gym_rows(oreburgh),
      warps=[((7, 11), ("oreburgh", 3, 5, "down"))],
      npcs=[leader_npc(7, 2, "gym_roark", "leader", "瓢太"),
            guide_npc(4, 9, "guide_roark"),
            tn(4, 3, 196, "down", 2), tn(11, 3, 18, "down", 2)],
      signs={(9, 10): "黑金道馆\n馆主:瓢太\n属性:岩石"})

    # ================================================================ 2 百代道馆(草) 树篱 + 拉杆
    rows = [
        "GGGGGGGGGGGGGGGG",
        "GggggggggggggggG",
        "GggggggggggggggG",
        "GhhhhhhhhhhhhhhG",      # 树篱墙,拉杆打开右侧
        "GggggggggggggggG",
        "GhhhhhhhhhhhhhgG",      # 右侧通道
        "GggggggggggggggG",
        "GghhhhhhhhhhhhhG",      # 左侧通道
        "GggggggggggggggG",
        "GggggggggggggggG",
        "GggggggggSgggggG",
        "GGGGGGGDGGGGGGGG",
    ]
    rows[4] = rows[4][:14] + "L" + rows[4][15:]
    G("eterna_gym", "百代道馆", rows,
      warps=[((7, 11), ("eterna", 3, 13, "down"))],
      npcs=[leader_npc(7, 2, "gym_gardenia", "lady", "菜种"), guide_npc(4, 9, "guide_gardenia"),
            tn(3, 6, 259, "right", 2), tn(12, 8, 301 - 301 + 260, "left", 2)],
      signs={(9, 10): "百代道馆\n馆主:菜种\n属性:草"},
      levers={(14, 4): [(13, 3, "g"), (14, 3, "g")]})

    # ================================================================ 3 帷幕道馆(格斗) 箭头滑块
    arrows = {
        (3, 8): "^", (4, 8): "^", (5, 8): "<", (6, 8): "<", (7, 8): "^", (8, 8): "^", (9, 8): ">", (10, 8): ">",
        (11, 8): "^", (12, 8): "^",
        (3, 6): ">", (4, 6): ">", (5, 6): "v", (6, 6): "v", (7, 6): "^", (8, 6): "<", (9, 6): "<", (10, 6): "v",
        (11, 6): "<", (12, 6): "v",
        (3, 4): "v", (4, 4): "v", (5, 4): ">", (6, 4): ">", (7, 4): "^", (8, 4): "<", (9, 4): "<", (10, 4): "<",
        (11, 4): "<", (12, 4): "^",
    }

    def veilstone(x, y):
        return arrows.get((x, y))
    G("veilstone_gym", "帷幕道馆", gym_rows(veilstone),
      warps=[((7, 11), ("veilstone", 11, 5, "down"))],
      npcs=[leader_npc(7, 2, "gym_maylene", "lass", "阿李"), guide_npc(4, 10, "guide_maylene"),
            tn(12, 2, 128, "left", 2), tn(3, 2, 309, "right", 2)],
      signs={(9, 10): "帷幕道馆\n馆主:阿李\n属性:格斗"})

    # ================================================================ 4 湿原道馆(水) 水位拉杆
    rows = [
        "GGGGGGGGGGGGGGGG",
        "GggggggggggggggG",
        "GggggggggggggggG",
        "GwwwwwwwwwwwwwwG",
        "GwwwwwwwwwwwwwwG",      # 拉杆 2 打开 (7,3)(7,4)
        "GwwggggggggggwwG",      # 中层平台,拉杆 2 在 (3,5)
        "GwwwwwwwwwwwwwwG",
        "GwwwwwwwwwwwwwwG",      # 拉杆 1 打开 (7,6)(7,7)
        "GwwwwwwwwwwwwwwG",
        "GggggggggggggggG",      # 入口层,拉杆 1 在 (2,9)
        "GggggggggSgggggG",
        "GGGGGGGDGGGGGGGG",
    ]
    rows[9] = rows[9][:2] + "L" + rows[9][3:]
    rows[5] = rows[5][:3] + "L" + rows[5][4:]
    G("pastoria_gym", "湿原道馆", rows,
      warps=[((7, 11), ("pastoria", 16, 12, "down"))],
      npcs=[leader_npc(7, 2, "gym_wake", "leader", "吉宪"), guide_npc(4, 10, "guide_wake"),
            tn(5, 5, 401, "down", 2), tn(11, 5, 68, "left", 2), tn(12, 9, 154, "left", 2)],
      signs={(9, 10): "湿原道馆\n馆主:吉宪\n属性:水"},
      levers={(2, 9): [(7, 8, "g"), (7, 7, "g"), (7, 6, "g")], (3, 5): [(7, 4, "g"), (7, 3, "g")]})

    # ================================================================ 5 家缘道馆(幽灵) 算术门
    def hearthome(x, y):
        if y in (4, 7) and x not in (3, 12):
            return "G"
        if y == 4 and x in (3, 12):
            return "G"
        return None
    rows = gym_rows(hearthome)
    m = G("hearthome_gym", "家缘道馆", rows,
          warps=[((7, 11), ("hearthome", 18, 5, "down"))],
          npcs=[leader_npc(7, 2, "gym_fantina", "lady", "梅丽莎"), guide_npc(4, 9, "guide_fantina"),
                tn(12, 9, 170, "left", 2), tn(3, 6, 171, "right", 2),
                npc(3, 4, "villager", "quiz_door_1", "down", name="算术之门"),
                npc(12, 7, "villager", "quiz_door_2", "down", name="算术之门")],
          signs={(9, 10): "家缘道馆\n馆主:梅丽莎\n属性:幽灵"})
    # 把两道横墙改成可穿过的门(NPC 守门):墙上的格子改为 g,由 NPC 站着阻挡
    m.rows[4] = list("GggggggggggggggG")
    m.rows[7] = list("GggggggggggggggG")
    for x in range(1, 15):
        if x != 3:
            m.rows[4][x] = "G"
        if x != 12:
            m.rows[7][x] = "G"
    m.rows[4][3] = "g"
    m.rows[7][12] = "g"

    # ================================================================ 6 水脉道馆(钢) 移动平台
    def canalave(x, y):
        if y in (4, 7) and x not in (7,):
            return "w"
        if y == 5 and x < 12:
            return "w"
        if y == 8 and x > 4:
            return "w"
        return None
    m = G("canalave_gym", "水脉道馆", gym_rows(canalave),
          warps=[((7, 11), ("canalave", 3, 5, "down"))],
          npcs=[leader_npc(7, 2, "gym_byron", "leader", "东瓜"), guide_npc(4, 9, "guide_byron"),
                tn(12, 9, 314, "left", 2), tn(3, 3, 148, "right", 2), tn(13, 2, 445, "left", 2)],
          signs={(9, 10): "水脉道馆\n馆主:东瓜\n属性:钢"})
    # 平台 4(入口右侧)→ 5(上层左侧);6(上层右侧)→ 7(馆主前)
    m.rows[9][12] = "4"
    m.rows[3][2] = "5"
    m.rows[3][13] = "6"
    m.rows[3][7] = "7"
    m.warps[(12, 9)] = ("canalave_gym", 2, 4, "up")
    m.warps[(13, 3)] = ("canalave_gym", 7, 4, "up")

    # ================================================================ 7 雪峰道馆(冰) 冰面滑行
    blocks = {(7, 5), (3, 4), (12, 4), (10, 8), (4, 8), (14, 7), (1, 7)}

    def snowpoint(x, y):
        if (x, y) in blocks:
            return "G"
        if 3 <= y <= 9:
            return "i"
        return None
    G("snowpoint_gym", "雪峰道馆", gym_rows(snowpoint),
      warps=[((7, 11), ("snowpoint", 9, 5, "down"))],
      npcs=[leader_npc(7, 2, "gym_candice", "lady", "小菘"), guide_npc(4, 10, "guide_candice"),
            tn(13, 2, 138, "left", 2), tn(2, 2, 134, "right", 2), tn(13, 10, 268, "left", 2)],
      signs={(9, 10): "雪峰道馆\n馆主:小菘\n属性:冰"})

    # ================================================================ 8 滨海道馆(电) 齿轮拉杆
    rows = [
        "GGGGGGGGGGGGGGGG",
        "GggggggggggggggG",
        "GggggggggggggggG",
        "GwwwwwwwwwwwwwwG",
        "GwwwwwwwwwwwwwwG",      # 拉杆 2 打开第 4 行桥与 (7,3)(7,5)
        "GwwwwwwwwwwwwwwG",
        "GggggggggggggggG",      # 中层平台,拉杆 2 在 (2,6)
        "GwwwwwwwwwwwwwwG",      # 拉杆 1 打开 (13,7)(13,8)
        "GwwwwwwwwwwwwwwG",
        "GggggggggggggggG",      # 入口层,拉杆 1 在 (2,9)
        "GggggggggSgggggG",
        "GGGGGGGDGGGGGGGG",
    ]
    rows[9] = rows[9][:2] + "L" + rows[9][3:]
    rows[6] = rows[6][:2] + "L" + rows[6][3:]
    G("sunyshore_gym", "滨海道馆", rows,
      warps=[((7, 11), ("sunyshore", 18, 5, "down"))],
      npcs=[leader_npc(7, 2, "gym_volkner", "leader", "电次"), guide_npc(4, 10, "guide_volkner"),
            tn(13, 9, 301, "left", 2), tn(4, 9, 302, "right", 2), tn(6, 6, 303, "up", 2)],
      signs={(9, 10): "滨海道馆\n馆主:电次\n属性:电"},
      levers={(2, 9): [(13, 8, "g"), (13, 7, "g")],
              (2, 6): [(7, 5, "g"), (7, 3, "g")] + [(x, 4, "g") for x in range(3, 13)]})
    return MAP_LIST
