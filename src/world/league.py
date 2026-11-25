"""宝可梦联盟:四天王 4 间房间(虫/地面/火/超能力)+ 冠军之间。

每间房:底部入口(上一间的出口),顶部出口(打败本间主人后开启)。"""
from . import Map, Grid, npc

MAP_LIST = []


def room(map_id, name, script, pal, npc_name, back, nxt, kind, sign_text):
    g = Grid(14, 12, fill="#", border="#")
    g.rect(2, 1, 11, 10, "o")
    if kind == "bug":
        for x in range(2, 12, 2):
            g.set(x, 3, "f")
            g.set(x, 8, "f")
    elif kind == "ground":
        for x, y in ((3, 4), (9, 4), (4, 8), (10, 8)):
            g.set(x, y, "m")
    elif kind == "fire":
        for x in range(3, 11, 3):
            g.set(x, 3, "s")
            g.set(x, 8, "s")
    elif kind == "psychic":
        for x, y in ((4, 3), (9, 3), (4, 8), (9, 8)):
            g.set(x, y, "t")
    g.set(6, 11, "D")
    g.set(6, 0, "D")
    npcs_ = [npc(6, 2, pal, script, "down", name=npc_name)]
    nxt_pos = (nxt[0], 6, 6, "down") if nxt[0] == "league_gate" else (nxt[0], 6, 10, "up")
    return Map(map_id, name, g.rows(), indoor=True,
               warps=[((6, 11), (back[0], 6, 1, "down")), ((6, 0), nxt_pos)], npcs=npcs_,
               signs={(2, 10): sign_text})


def build():
    MAP_LIST.append(room("e4_aaron", "四天王 阿柳", "e4_aaron", "e4", "阿柳",
                         ("league_gate", 9, 3, "left"), ("e4_bertha", 6, 10, "up"), "bug",
                         "宝可梦联盟\n四天王之一:阿柳(虫系)"))
    MAP_LIST.append(room("e4_bertha", "四天王 菊野", "e4_bertha", "elder", "菊野",
                         ("e4_aaron", 6, 1, "down"), ("e4_flint", 6, 10, "up"), "ground",
                         "宝可梦联盟\n四天王之一:菊野(地面系)"))
    MAP_LIST.append(room("e4_flint", "四天王 大叶", "e4_flint", "rival", "大叶",
                         ("e4_bertha", 6, 1, "down"), ("e4_lucian", 6, 10, "up"), "fire",
                         "宝可梦联盟\n四天王之一:大叶(火系)"))
    MAP_LIST.append(room("e4_lucian", "四天王 悟松", "e4_lucian", "prof", "悟松",
                         ("e4_flint", 6, 1, "down"), ("champion_room", 6, 10, "up"), "psychic",
                         "宝可梦联盟\n四天王之一:悟松(超能力系)"))
    MAP_LIST.append(room("champion_room", "冠军之间", "champion_cynthia", "champion", "竹兰",
                         ("e4_lucian", 6, 1, "down"), ("league_gate", 6, 6, "down"), "psychic",
                         "宝可梦联盟\n冠军:竹兰"))
    return MAP_LIST
