"""世界数据校验:传送目标、NPC/告示/道具坐标、脚本存在、地图连通性、道馆可解性。

运行: python3 tests/world_test.py
"""
import os
import sys
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["SDL_VIDEODRIVER"] = "dummy"

from src import data, world   # noqa: E402
from src.world import SOLID   # noqa: E402

PASS = 0
FAILS = []


def check(name, cond, extra=""):
    global PASS
    if cond:
        PASS += 1
    else:
        FAILS.append(f"FAIL: {name} {extra}")


# ---------------------------------------------------------------- 1. 传送
for mid, m in world.MAPS.items():
    widths = {len(r) for r in m.rows}
    check(f"地图行宽一致 {mid}", len(widths) == 1, str(widths))
    for (x, y), (dest, dx, dy, facing) in m.warps.items():
        check(f"传送目标存在 {mid}", dest in world.MAPS, f"{(x, y)} -> {dest}")
        if dest not in world.MAPS:
            continue
        dm = world.MAPS[dest]
        check(f"传送坐标合法 {mid}->{dest}", 0 <= dx < dm.w and 0 <= dy < dm.h, f"{(dx, dy)}")
        t = dm.tile(dx, dy)
        check(f"传送落点可行走 {mid}->{dest}@{dx},{dy}", t not in SOLID or t == "w", f"tile={t}")
        check(f"传送源是出口图块 {mid}@{x},{y}",
              m.tile(x, y) in "DnHIwcd._p ,xXs4567i<>^v" or m.tile(x, y) == "o", f"{m.tile(x, y)}")
    for npc in m.npcs:
        check(f"NPC脚本存在 {mid}:{npc['script']}",
              npc["script"] in world.SCRIPTS or npc["script"] == "trainer"
              or (isinstance(npc["script"], tuple) and npc["script"][0] in world.SCRIPTS))
        if npc["script"] == "trainer":
            check(f"NPC训练家存在 {mid}", npc["trainer"] in data.TRAINERS, str(npc["trainer"]))
        check(f"NPC坐标合法 {mid}", 0 <= npc["x"] < m.w and 0 <= npc["y"] < m.h)
        t = m.tile(npc["x"], npc["y"])
        check(f"NPC站在可行走格 {mid}@{npc['x']},{npc['y']}", t not in "TwFSRBVQY#GChKJObZt123PNML" or t == "w",
              f"{t}")
    for (x, y) in m.signs:
        check(f"告示牌坐标 {mid}@{x},{y}", m.tile(x, y) == "S", m.tile(x, y))
    for (x, y) in m.items:
        check(f"道具球坐标 {mid}@{x},{y}", m.tile(x, y) == "*", m.tile(x, y))
    if m.enc:
        check(f"遭遇区域存在 {mid}", m.enc in data.ENCOUNTERS, m.enc)
    if getattr(m, "stock", None):
        for name, _ in m.stock:
            check(f"商店商品存在 {mid}", name in data.ITEMS, name)
    for (lx, ly), tiles in m.levers.items():
        check(f"拉杆坐标 {mid}@{lx},{ly}", m.tile(lx, ly) == "L", m.tile(lx, ly))

# ---------------------------------------------------------------- 2. 连通性(忽略门禁)
adj = {mid: set() for mid in world.MAPS}
for mid, m in world.MAPS.items():
    for (x, y), (dest, *_ ) in m.warps.items():
        adj[mid].add(dest)
seen = {"twinleaf_home"}
q = deque([("twinleaf_home", 0)])
while q:
    cur, d = q.popleft()
    for nxt in adj[cur]:
        if nxt not in seen:
            seen.add(nxt)
            q.append((nxt, d + 1))
script_only = {"fight_area", "fight_area_center", "fight_area_mart", "iron_island",   # 经船夫/剧情传送
               "r225", "r226", "r227", "r228", "r229", "r230"}
unreachable = set(world.MAPS) - seen - script_only
check("所有地图可达(忽略门禁)", not unreachable, str(sorted(unreachable)))
print(f"  可达地图 {len(seen)}/{len(world.MAPS)}")

# ---------------------------------------------------------------- 2b. 图内连通性
# 从每个入口(其它地图传送进来的落点)出发,应能到达本图所有出口、NPC/告示/道具/拉杆的相邻格。
# 秘传障碍(K/J/O)和水面按可通行处理;忽略 NPC 本身的阻挡。
entries = {mid: set() for mid in world.MAPS}
for mid, m in world.MAPS.items():
    for (x, y), (dest, dx, dy, f) in m.warps.items():
        entries[dest].add((dx, dy))
entries[world.START[0]].add((world.START[1], world.START[2]))
entries["iron_island"].add((21, 9))            # 船夫脚本传送的落点
entries["fight_area"].add((10, 10))
for mid, m in world.MAPS.items():
    over = {}                                   # 假设拉杆都已拉动
    for (lx, ly), tiles in m.levers.items():
        for tx, ty, ch in tiles:
            over[(tx, ty)] = ch
    starts = [e for e in entries[mid] if not m.solid(*e, over) or m.tile(e[0], e[1], over) in "wW"]
    if not starts:
        check(f"图内有可行走入口 {mid}", False, str(entries[mid]))
        continue
    seen = set(starts)
    q = deque(starts)
    while q:
        x, y = q.popleft()
        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < m.w and 0 <= ny < m.h) or (nx, ny) in seen:
                continue
            if m.solid(nx, ny, over) and m.tile(nx, ny, over) not in "KJOwW":
                continue
            if any(n["x"] == nx and n["y"] == ny and not str(n["script"]).startswith("quiz_door")
                   for n in m.npcs):
                continue                                   # NPC(含已打败仍站着的训练家)是实体;算术之门会被传送穿过
            seen.add((nx, ny))
            q.append((nx, ny))
    for (x, y) in m.warps:
        check(f"出口可达 {mid}@{x},{y}", (x, y) in seen, m.tile(x, y))
    for n in m.npcs:
        adj = [(n["x"] + dx, n["y"] + dy) for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0))]
        check(f"NPC可对话 {mid}:{n.get('name') or n['script']}", any(a in seen for a in adj), str((n["x"], n["y"])))
    for (x, y) in list(m.signs) + list(m.items) + list(m.levers):
        adj = [(x + dx, y + dy) for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0))]
        check(f"可交互 {mid}@{x},{y}", any(a in seen for a in adj), m.tile(x, y))

# ---------------------------------------------------------------- 3. 关键落点
for spot, (mp, x, y, facing, name) in world.FLY_SPOTS.items():
    m = world.MAPS[mp]
    check(f"飞翔落点 {name}", m.tile(x, y) not in SOLID, m.tile(x, y))


# ---------------------------------------------------------------- 4. 道馆可解性
def bfs_gym(mid, start, goals, blocked_extra=()):
    m = world.MAPS[mid]
    over = {}
    for (lx, ly), tiles in m.levers.items():     # 假设所有拉杆都已拉动
        for tx, ty, ch in tiles:
            over[(tx, ty)] = ch
    # 简化:忽略冰面/箭头的滑行,只看静态连通性
    seen = {start}
    q = deque([start])
    while q:
        x, y = q.popleft()
        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < m.w and 0 <= ny < m.h) or (nx, ny) in seen or (nx, ny) in blocked_extra:
                continue
            if m.tile(nx, ny, over) in "GhJw#L":
                continue                                   # 拉杆本身是实体,不能穿过
            seen.add((nx, ny))
            q.append((nx, ny))
    return any(g in seen for g in goals)


# 目标 = 馆主(7,2) 周围可站位的格子(任一可达即可与馆主对话)
NEAR_LEADER = [(6, 2), (8, 2), (7, 1), (7, 3)]
GYM_CHECK = {mid: ((7, 9), NEAR_LEADER) for mid in
             ("oreburgh_gym", "eterna_gym", "veilstone_gym", "pastoria_gym", "hearthome_gym",
              "canalave_gym", "snowpoint_gym", "sunyshore_gym")}
for mid, (start, goals) in GYM_CHECK.items():
    if mid == "canalave_gym":
        # 移动平台:入口层 → 平台 A → 上层左侧 → 走到平台 C → 馆主前
        check("道馆可解(机关全开) canalave_gym",
              bfs_gym(mid, start, [(12, 9)]) and bfs_gym(mid, (2, 4), [(13, 3)]) and bfs_gym(mid, (7, 4), goals))
        continue
    check(f"道馆可解(机关全开) {mid}", bfs_gym(mid, start, goals))
# 不拉动拉杆时应不可达(机关确实起作用)
for mid in ("eterna_gym", "pastoria_gym", "sunyshore_gym"):
    m = world.MAPS[mid]
    seen = {(7, 9)}
    q = deque([(7, 9)])
    while q:
        x, y = q.popleft()
        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < m.w and 0 <= ny < m.h) or (nx, ny) in seen or m.tile(nx, ny) in "GhKJw#L":
                continue
            seen.add((nx, ny))
            q.append((nx, ny))
    check(f"道馆机关未开时不可达 {mid}", not any(g in seen for g in NEAR_LEADER))

for f in FAILS[:40]:
    print(f)
print(f"\n世界校验: {PASS} 项通过, {len(FAILS)} 项失败" + (" ✔" if not FAILS else ""))
if FAILS:
    sys.exit(1)
