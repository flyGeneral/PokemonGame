"""神奥地区地图数据包:Map 类、图例、室内模板、注册表。

子模块:towns(城镇) routes(道路) dungeons(洞窟/设施) gyms(道馆) league(联盟) interiors(室内) scripts(对话/事件)

图例(室外): '.'草 ','高草 'p'路 'n'路口边缘 'w'水 'W'瀑布 'f'花 'T'树 'F'栅栏 'S'告示牌
            'R'蓝顶 'Q'橙顶 'Y'红顶 'B'墙 'V'窗 'D'门 's'沙滩 'x'雪地 'X'深雪 'm'山岩 'v'崖壁
            'c'洞窟地面 'C'洞窟墙 'i'冰面 '^v<>'箭头滑块 'K'可碎岩石 'J'树丛 'O'怪力石
            '*'道具球 'L'拉杆 'h'树篱 'r'攀岩壁(不可用) '_'木桥
     (室内): '#'墙 'o'地板 'm'地垫 'E'出口垫 'b'床 's'书架 't'桌 '1/2/3'球桌
            'P'电脑 'N'护士柜台 'M'商店柜台 'g'道馆地板 'G'道馆墙 'A'-'D'平台(传送)
            'H'上行楼梯 'I'下行楼梯
"""
SOLID = set("TwFSRBVQYmvC KhJ O* LhrG#Zbt123PNM")
WALKABLE_EDGE = set(".pnfsxXcioc_^<>4567w")   # 可作为地图边缘出口的图块(含室内/洞窟地面)
INDOOR_IDS = set()


class Map:
    def __init__(self, map_id, name, rows, warps=(), exits=None, npcs=(), enc=None, signs=None,
                 items=None, cave=False, tag=None, indoor=False, levers=None, rules=None, music=None,
                 encounter_rate=None, safari=False):
        self.id = map_id
        self.name = name
        self.rows = [list(r) for r in rows]
        assert len({len(r) for r in rows}) == 1, f"地图 {map_id} 行宽不一致"
        self.w = len(rows[0])
        self.h = len(rows)
        self.warps = {tuple(k): v for k, v in warps}
        self.exits = exits or {}
        self.npcs = [dict(n) for n in npcs]
        self.enc = enc
        self.signs = dict(signs or {})
        self.items = dict(items or {})
        for (sx, sy) in self.signs:          # 告示牌/道具球自动落到地图上
            self.rows[sy][sx] = "S"
        for (ix, iy) in self.items:
            self.rows[iy][ix] = "*"
        self.cave = cave
        self.tag = tag
        self.indoor = indoor
        self.levers = dict(levers or {})
        self.rules = dict(rules or {})           # 传送门禁:(x,y) → (flag, 提示)
        self.music = music
        self.encounter_rate = encounter_rate
        self.safari = safari
        if indoor:
            INDOOR_IDS.add(map_id)

    def tile(self, x, y, over=None):
        """图块;over 为 (x,y)→char 的覆盖层(打碎的岩石/推动的石头/拾取的道具/拉杆)。"""
        if not (0 <= x < self.w and 0 <= y < self.h):
            return "#" if self.indoor else "T"
        if over and (x, y) in over:
            return over[(x, y)]
        return self.rows[y][x]

    def solid(self, x, y, over=None, surfing=False):
        if not (0 <= x < self.w and 0 <= y < self.h):
            return True
        t = self.tile(x, y, over)
        if surfing:
            if t == "w":
                return False
            return t in SOLID
        return t in SOLID

    def npc_at(self, x, y, visible=None):
        for n in self.npcs:
            if n["x"] == x and n["y"] == y and (visible is None or visible(n)):
                return n
        return None

    def apply_exits(self):
        """把 exits={side: (dest, x, y, facing)} 展开为边缘所有可行走图块的传送。"""
        for side, dest in self.exits.items():
            if side == "N":
                cells = [(x, 0) for x in range(self.w) if self.rows[0][x] in WALKABLE_EDGE]
            elif side == "S":
                cells = [(x, self.h - 1) for x in range(self.w) if self.rows[self.h - 1][x] in WALKABLE_EDGE]
            elif side == "W":
                cells = [(0, y) for y in range(self.h) if self.rows[y][0] in WALKABLE_EDGE]
            else:
                cells = [(self.w - 1, y) for y in range(self.h) if self.rows[y][self.w - 1] in WALKABLE_EDGE]
            for c in cells:
                self.warps[c] = dest


class Grid:
    """室外地图构建器:矩形/线条/房屋,生成等宽 ASCII 行。"""

    def __init__(self, w, h, fill=".", border="T"):
        self.w, self.h = w, h
        self.g = [[fill] * w for _ in range(h)]
        if border:
            for x in range(w):
                self.g[0][x] = self.g[h - 1][x] = border
            for y in range(h):
                self.g[y][0] = self.g[y][w - 1] = border

    def set(self, x, y, c):
        self.g[y][x] = c

    def rect(self, x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.g[y][x] = c

    def hline(self, x0, x1, y, c):
        self.rect(x0, y, x1, y, c)

    def vline(self, x, y0, y1, c):
        self.rect(x, y0, x, y1, c)

    def building(self, x, y, w, roof, door_dx=None, wall="B", window="V", door=True):
        """3 行建筑:屋顶 / 墙+窗 / 墙+门。返回门坐标(door=False 时无门,返回 None)。"""
        door_dx = w // 2 if door_dx is None else door_dx
        self.rect(x, y, x + w - 1, y, roof)
        for yy in (y + 1, y + 2):
            for xx in range(x, x + w):
                self.g[yy][xx] = wall if xx in (x, x + w - 1) else window
        if not door:
            return None
        self.set(x + door_dx, y + 2, "D")
        return (x + door_dx, y + 2)

    def open_exit(self, side, a, b, c="p"):
        """在地图边缘打开出口:side ∈ N/S/E/W,a..b 为沿边缘的坐标范围。"""
        if side == "N":
            self.rect(a, 0, b, 0, c)
        elif side == "S":
            self.rect(a, self.h - 1, b, self.h - 1, c)
        elif side == "W":
            self.rect(0, a, 0, b, c)
        else:
            self.rect(self.w - 1, a, self.w - 1, b, c)

    def rows(self):
        return ["".join(r) for r in self.g]


def grass(g, patches):
    """铺设高草丛矩形。"""
    for x0, y0, x1, y1 in patches:
        g.rect(x0, y0, x1, y1, ",")


def trees(g, spots):
    for x, y in spots:
        g.set(x, y, "T")


def npc(x, y, pal, script, direction="down", trainer=None, sight=0, name=None, show=None, hide=None, legend=None):
    d = {"x": x, "y": y, "pal": pal, "script": script, "dir": direction, "sight": sight}
    if trainer is not None:
        d["trainer"] = trainer
    if name:
        d["name"] = name
    if show:
        d["show"] = show          # 仅当 flag 为真时显示
    if hide:
        d["hide"] = hide          # flag 为真时隐藏
    if legend:
        d["legend"] = legend      # 传说中的宝可梦:flag 为真时隐藏,成为冠军后(未捕捉)重新现身
    return d


def edge_exit(dest, x, y, facing):
    return (dest, x, y, facing)


MAPS = {}


def register(*maps):
    for m in maps:
        assert m.id not in MAPS, m.id
        MAPS[m.id] = m
    return maps


# 出生点(双叶镇自宅二楼简化为一楼):真砂镇研究所领取初始精灵
START = ("twinleaf_home", 4, 5, "down")

# 飞翔目的地:(地图, x, y, 朝向, 显示名) —— 均为精灵中心门口
FLY_SPOTS = {
    "twinleaf": ("twinleaf", 11, 7, "down", "双叶镇"),
    "sandgem": ("sandgem", 14, 9, "down", "真砂镇"),
    "jubilife": ("jubilife", 8, 10, "down", "祝庆市"),
    "oreburgh": ("oreburgh", 6, 11, "down", "黑金市"),
    "floaroma": ("floaroma", 16, 9, "down", "花苑镇"),
    "eterna": ("eterna", 6, 10, "down", "百代市"),
    "hearthome": ("hearthome", 7, 10, "down", "家缘市"),
    "solaceon": ("solaceon", 11, 7, "down", "随意镇"),
    "veilstone": ("veilstone", 7, 12, "down", "帷幕市"),
    "pastoria": ("pastoria", 5, 9, "down", "湿原市"),
    "canalave": ("canalave", 6, 10, "down", "水脉市"),
    "celestic": ("celestic", 12, 9, "down", "神和镇"),
    "snowpoint": ("snowpoint", 7, 10, "down", "雪峰市"),
    "sunyshore": ("sunyshore", 7, 10, "down", "滨海市"),
    "league": ("league", 7, 6, "up", "宝可梦联盟"),
}

# 版本差异:(显示名, 神兽)
VERSIONS = {"D": ("钻石", "帝牙卢卡"), "P": ("珍珠", "帕路奇亚")}
SCRIPTS = {}


def finalize():
    for m in MAPS.values():
        m.apply_exits()
    # 室内回到室外的落点 = 门外一格,自动与室外门坐标保持一致
    for m in MAPS.values():
        if m.indoor:
            continue
        for (x, y), (dest, dx, dy, f) in m.warps.items():
            dm = MAPS[dest]
            if not dm.indoor:
                continue
            for (ix, iy), (t, tx, ty, tf) in list(dm.warps.items()):
                if t == m.id and m.tile(x, y) == "D":
                    dm.warps[(ix, iy)] = (m.id, x, y + 1, "down")


# ---- 子模块在常量定义后导入(scripts 需要 VERSIONS 等)
from .interiors import center, mart, house, get_special, SHOP_STOCK, tm_stock   # noqa: F401,E402
from . import towns, routes, dungeons, gyms, league, interiors   # noqa: F401,E402
from .scripts import SCRIPTS                                     # noqa: F401,E402

register(*towns.build(), *routes.build(), *dungeons.build(), *gyms.build(), *league.build(),
         *get_special())
finalize()
MAP_IDS = sorted(MAPS)
# 飞翔落点 = 各城镇精灵中心门口
for _town, _spot in list(FLY_SPOTS.items()):
    _m = MAPS.get(_town)
    if not _m:
        continue
    for (x, y), (dest, *_r) in _m.warps.items():
        if dest == f"{_town}_center":
            FLY_SPOTS[_town] = (_town, x, y + 1, "down", _spot[4])
