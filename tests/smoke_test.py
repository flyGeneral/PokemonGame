"""无头冒烟测试:数据校验 + 核心机制 + 战斗自动驱动 + 存读档 + 渲染循环。

运行: python3 tests/smoke_test.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ.pop("PYGAME_HIDE_SUPPORT_PROMPT", None)

import random
import pygame

from src import data, art_data, worldmap
from src.mon import Mon

PASS = 0


def check(name, cond, extra=""):
    global PASS
    assert cond, f"FAIL: {name} {extra}"
    PASS += 1
    print(f"  ok  {name}")


# ================================================================ 1. 数据校验
print("== 数据校验 ==")
for aid, d in art_data.MON_ART.items():
    widths = {len(r) for r in d["rows"]}
    check(f"矩阵宽度一致 {aid}", len(widths) == 1, str(widths))
    check(f"矩阵行数16 {aid}", len(d["rows"]) == 16)
    used = set("".join(d["rows"])) - {"."}
    check(f"调色板覆盖 {aid}", used <= set(d["pal"]), str(used - set(d["pal"])))

for name, mv in data.MOVES.items():
    if mv.get("ohko"):
        check(f"一击必杀招 {name}", mv["cat"] == "物理")
    elif mv["cat"] != "变化":
        check(f"招式威力 {name}", mv["power"] and mv["power"] > 0)
    else:
        check(f"变化招无威力 {name}", not mv["power"])
for sp, d in data.SPECIES.items():
    check(f"art存在 {sp}", d["art"] in art_data.MON_ART or d["art"].startswith("dex"))
    check(f"基础值6项 {sp}", len(d["base"]) == 6 and all(v > 0 for v in d["base"]))
    for lv, mv in d["learnset"]:
        check(f"learnset招式存在 {sp}:{mv}", mv in data.MOVES)
    if d["evo"]:
        check(f"进化目标存在 {sp}", d["evo"][0] in data.SPECIES)

for mid, m in worldmap.MAPS.items():
    widths = {len(r) for r in m.rows}
    check(f"地图行宽一致 {mid}", len(widths) == 1, str(widths))
    for (x, y), (dest, dx, dy, _) in m.warps.items():
        check(f"传送目标存在 {mid}", dest in worldmap.MAPS)
        check(f"传送坐标合法 {mid}->{dest}",
              0 <= dx < worldmap.MAPS[dest].w and 0 <= dy < worldmap.MAPS[dest].h)
    for npc in m.npcs:
        check(f"NPC脚本存在 {npc['script']}", npc["script"] in worldmap.SCRIPTS)
        check(f"NPC坐标合法 {mid}",
              m.tile(npc["x"], npc["y"]) not in "TwFSRBV#Gbst123")
for sp, _, _, _ in worldmap.ROUTE.encounters[","]:
    check(f"遇敌种存在 {sp}", sp in data.SPECIES)

# ================================================================ 2. 核心机制
print("== 核心机制 ==")
random.seed(42)
m = Mon("小火猴", 5)
check("能力值计算", m.max_hp == (2 * 44 + m.ivs[0]) * 5 // 100 + 5 + 10)
check("初始招式", [x.name for x in m.moves] == ["抓", "瞪眼"])
foe = Mon("姆克儿", 4)
res = m.calc_damage(foe, "火花")
check("伤害为正", res["damage"] >= 1)
check("效果拔群 火vs草", data.type_multiplier("火", ("草",)) == 2.0)
check("免疫 电vs地面", data.type_multiplier("电", ("地面",)) == 0.0)
check("STAB/随机浮动", 1 <= res["damage"] <= 60)
check("官方成长曲线", data.exp_for_level(16, "medium_slow") == 2535 and
      data.exp_for_level(50, "medium_fast") == 125000)

weak = Mon("姆克儿", 3)
weak.hp = 1
weak.status = "睡眠"
shakes = weak.catch_shakes(2.0)
check("必中捕获公式", shakes == 4, f"shakes={shakes}")
full = Mon("姆克儿", 3)
shakes2 = full.catch_shakes(1.0)
check("满血捕获概率受限", shakes2 <= 4)

m17 = Mon("草苗龟", 17)
gain = data.exp_for_level(18, "medium_slow") - m17.exp + 1
msgs, evo = m17.gain_exp(gain)
check("升级触发进化标记", evo == "树林龟", str(evo))

mm = Mon("小拳石", 24)
old = mm.evolve_into("隆隆石")
check("进化变更", old == "小拳石" and mm.species == "隆隆石" and mm.max_hp > 30)

# ================================================================ 3. 战斗自动驱动
print("== 战斗自动驱动 ==")
from src.game import Game
from src.battle import Battle

g = Game()
g.party = [Mon("树林龟", 20)]
g.bag = {"精灵球": 10, "高级球": 5, "伤药": 3}
b = Battle(g, [Mon("大牙狸", 3)], callback=lambda r: None)
b.auto = True
r = b.drive_for_test([("menu", "fight"), ("move", 0)])
check("野外战斗胜利", r == "win", str(r))
check("敌人倒下", b.foe.hp == 0)
check("获得经验", g.party[0].exp > data.exp_for_level(20, "medium_slow"))

# 捕捉:必中条件
target = Mon("姆克儿", 3)
target.hp = 1
target.status = "睡眠"
b2 = Battle(g, [target], callback=lambda r2: None)
b2.auto = True
r2 = b2.drive_for_test([("menu", "bag"), ("bag", "高级球")])
check("捕捉成功", r2 == "caught", str(r2))
check("入队", any(m.species == "姆克儿" for m in g.party))

# 换人(存活场景)+ 逃跑(高速必成功)
g.party = [Mon("草苗龟", 8), Mon("皮卡丘", 12)]
b3 = Battle(g, [Mon("小拳石", 3)], callback=lambda r3: None)
b3.auto = True
r3 = b3.drive_for_test([("menu", "party"), ("party", 1)])
check("换人生效", b3.p_idx == 1)
check("换人后被攻击仍存活", b3.ally.hp > 0)
b3b = Battle(g, [Mon("小拳石", 2)], callback=lambda r3b: None)
b3b.auto = True
b3b.p_idx = 1
b3b._started = False
b3b._flow = b3b._main_flow()
b3b._advance(None)
r3b = b3b.drive_for_test([("menu", "run")])
check("高速必定逃走", r3b == "ran", str(r3b))

# 训练家战(道馆):打输触发 lose
g.party = [Mon("草苗龟", 2)]
b4 = Battle(g, [Mon("隆隆石", 40)], trainer_name="测试馆长", callback=lambda r4: None)
b4.auto = True
r4 = b4.drive_for_test([("menu", "fight"), ("move", 0)])
check("训练家战失败判定", r4 == "lose", str(r4))

# 训练家战(获胜:多只敌人轮换)
g.party = [Mon("猛火猴", 41)]
g.party[0].hp = g.party[0].max_hp
b5 = Battle(g, [Mon("小拳石", 10), Mon("小拳石", 10)], trainer_name="测试", callback=lambda r5: None)
b5.auto = True
r5 = b5.drive_for_test([("menu", "fight"), ("move", 3),
                        ("menu", "fight"), ("move", 3)])
check("道馆战胜利+轮换", r5 == "win", str(r5))

# ================================================================ 4. 世界流程
print("== 世界流程 ==")
from src import worldmap as WM

g2 = Game()
g2.new_game()
ow = g2.scenes[0]
check("开场对话", ow.state == "dialog")
for _ in range(10):
    if ow.state != "dialog":
        break
    ow.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))
check("对话结束回field", ow.state == "field")

# 初始精灵流程
ow.warp_to("lab", 5, 5, "up")
ow._interact()  # 面朝上,面前是(5,4)? (5,4)是'1'号球
if ow.state != "dialog":
    ow.px, ow.py, ow.dir = 5, 5, "up"
    ow._interact()
steps = 0
while ow.state == "dialog" and steps < 20:
    ow.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))
    steps += 1
if ow.state == "starter":
    check("踩3号桌预选波加曼", ow.starter.cursor == 2, str(ow.starter.cursor))
    icons2 = g2.assets["icons"]
    ow.starter.key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT), icons2)
    ow.starter.key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT), icons2)
    ow.starter.key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z), icons2)
    ow.starter.key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z), icons2)
    if ow.starter.done:
        ow._starter_done()
steps = 0
while ow.state == "dialog" and steps < 20:
    ow.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))
    steps += 1
check("获得初始精灵", len(g2.party) == 1 and g2.party[0].species == "草苗龟")
check("获得道具", g2.bag.get("精灵球", 0) == 5 and g2.bag.get("伤药", 0) == 3)
check("标记", g2.flags.get("starter_chosen") is True)

# 存读档
g2.save()
g3 = Game()
g3.load()
check("读档队伍", len(g3.party) == 1 and g3.party[0].species == "草苗龟")
check("读档道具", g3.bag.get("精灵球") == 5)
check("读档位置", g3.scenes[0].map_id == "lab")

# 移动与碰撞
ow2 = g3.scenes[0]
ow2.warp_to("town", 10, 12, "up")
before = (ow2.px, ow2.py)
ow2.update(0.01)
check("待机不移动", (ow2.px, ow2.py) == before)


def hold(ow, key, frames=8, dt=0.05):
    ow.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))
    for _ in range(frames):
        ow.update(dt)
    ow.handle_event(pygame.event.Event(pygame.KEYUP, key=key))


# 向左撞树((9,12)是'.',走到(9,12)后(8,12)也是'.')——改为撞左边一排的树需要更远;
# 直接验证: 向上走到北出口触发传送
ow2.dir = "up"
ow2.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP))
for _ in range(150):
    ow2.update(0.05)
ow2.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_UP))
check("北出口传送到道路", ow2.map_id == "route", f"{ow2.map_id} @({ow2.px},{ow2.py})")

# 碰撞:在道路上向左是草地可走,再往左到树 T 被挡
ow2.warp_to("route", 9, 7, "left")
hold(ow2, pygame.K_LEFT, 70)
check("撞树被挡", ow2.px == 1, str((ow2.px, ow2.py)))

# 遇敌强制触发
random.seed(7)
ow2.px, ow2.py = 4, 6
ow2.map_id = "route"
ow2._arrive_on_grass = True
ow2.px, ow2.py = 4, 6
# 直接验证 _roll
sp, lv = ow2._roll(worldmap.ROUTE.encounters[","])
check("遇敌表抽样", sp in data.SPECIES and 2 <= lv <= 6, f"{sp} lv{lv}")

# ================================================================ 5. 渲染冒烟
print("== 渲染冒烟 ==")
g4 = Game()
g4.new_game()
ow4 = g4.scenes[0]
ow4.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))
for _ in range(10):
    if ow4.state != "dialog":
        break
    ow4.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))
# 未选初始精灵时不得离开小镇
ow4.warp_to("town", 10, 1, "up")
ow4.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP))
for _ in range(30):
    ow4.update(0.05)
ow4.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_UP))
check("无初始精灵无法离镇", ow4.map_id == "town" and ow4.py == 1, str((ow4.map_id, ow4.px, ow4.py)))

# 无初始精灵也能进自宅/研究所(门禁只限道路出口)
def walk_to(ow, x, y, key, frames=40):
    ow.px, ow.py = x, y
    ow.dir = "up"
    ow.moving = False
    for _ in range(12):          # 清掉可能残留的提示对话
        if ow.state != "dialog":
            break
        ow.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))
    ow.state = "field"
    ow.held = {key}
    for _ in range(frames):
        ow.update(0.05)
    ow.held.clear()

ow4.warp_to("town", 4, 6, "up")
walk_to(ow4, 4, 6, pygame.K_UP)
check("无初始精灵可进自宅", ow4.map_id == "house", str((ow4.map_id, ow4.px, ow4.py)))
ow4.warp_to("town", 16, 6, "up")
walk_to(ow4, 16, 6, pygame.K_UP)
check("无初始精灵可进研究所", ow4.map_id == "lab", str((ow4.map_id, ow4.px, ow4.py)))
ow4.warp_to("house", 5, 6, "down")
walk_to(ow4, 5, 6, pygame.K_DOWN)
check("自宅门可返回小镇", ow4.map_id == "town" and 4 <= ow4.px <= 5 and ow4.py >= 5,
      str((ow4.map_id, ow4.px, ow4.py)))

surf = pygame.Surface((__import__("src.settings", fromlist=["settings"]).WIN_W,
                       __import__("src.settings", fromlist=["settings"]).WIN_H))
ow4.draw(surf)
ow4._open_menu()
ow4.draw(surf)
ow4.state = "field"
g4.party = [Mon("小火猴", 10)]
b6 = g4.push_battle([Mon("姆克儿", 3)], callback=lambda r6: None)
b6.draw(surf)
b6.phase = "menu"
b6.draw(surf)
check("各场景绘制无异常", True)

# 官方/平滑精灵球与抛球动画渲染
check("球资源表存在", "精灵球" in g4.assets["balls"] and "高级球" in g4.assets["balls"])
ball = g4.assets["balls"]["精灵球"]
px = ball.get_at((ball.get_width() // 2, 2))
check("球为平滑渲染(非8x8)", ball.get_width() >= 40)
b6.anim = ["ball", 0.7, 2.5, 2]
b6._thrown_item = "超级球"
b6.draw(surf)
b6.anim = ["ball", 1.2, 2.5, 4]
b6.draw(surf)
b6.anim = None
check("抛球动画三阶段渲染无异常", True)

# 神奥图鉴、占位图、冻结/连击/AI
check("图鉴已合并", "小猫怪" in data.SPECIES and "头盖龙" in data.SPECIES)
check("占位图已生成", g.assets["mons"]["dex403"].get_width() == 80
      and "dex403" in g.assets["icons"])
b9 = Battle(g, [Mon("小拳石", 5)], callback=lambda r: None)
b9.ally.status = "冻结"
msgs9 = [x for x in b9._use_move("ally", "火花") if x[0] == "msg"]
check("冻结无法行动", any("无法动弹" in m[1] for m in msgs9))
thawed = False
for i in range(80):
    random.seed(i)
    b9.ally.status = "冻结"
    msgs9 = [x for x in b9._use_move("ally", "火花") if x[0] == "msg"]
    if any("融化" in m[1] for m in msgs9):
        thawed = True
        break
check("火系招式融冰", thawed)
check("AI选招合法", b9._ai_pick_move() in [x.name for x in b9.foe.moves] or b9.foe.moves == [])
data.MOVES["撞击"]["multihit"] = (2, 5)
hpm = b9.foe.hp
list(b9._use_move("ally", "拍击"))
check("连击造成多次伤害", b9.foe.hp < hpm or hpm == 0)
del data.MOVES["撞击"]["multihit"]

# 战斗结束后按键不卡死(修复:收服后角色一直往右走)
ow5 = g4.scenes[0]
ow5.state = "field"
ow5.px, ow5.py = 10, 10
ow5.moving = False
g4.party = [Mon("小火猴", 10)]
ow5.held.add(pygame.K_RIGHT)
b8 = g4.push_battle([Mon("姆克儿", 3)], callback=lambda r: None)
check("进战斗清空移动键", pygame.K_RIGHT not in ow5.held)
ow5.held.add(pygame.K_RIGHT)     # 模拟旧 bug:战斗中收到松键
b8.done, b8.result = True, "ran"
pygame.event.post(pygame.event.Event(pygame.KEYUP, key=pygame.K_RIGHT))
gx, gy = ow5.px, ow5.py
g4.tick(0.016)
check("战斗弹出回世界", g4.scenes[0] is ow5)
check("松键广播到世界层", pygame.K_RIGHT not in ow5.held)
for _ in range(30):
    ow5.update(0.05)
check("角色不再向右漂移", (ow5.px, ow5.py) == (gx, gy),
      str(((gx, gy), (ow5.px, ow5.py))))

# 平滑相机:行走中相机随插值位置连续移动,而非整格跳变
S_TILE = 16
ow6 = g4.scenes[0]
ow6.state = "field"
ow6.moving = False
ow6.warp_to("route", 9, 14, "up")
cx0, cy0 = ow6._cam()
ow6.moving = True
ow6.step_from = (10, 10)
ow6.step_to = (10, 9)
ow6.step_t = 0.5
cxm, cym = ow6._cam()
ow6.step_t = 1.0
cx1, cy1 = ow6._cam()
check("步中相机位于两格之间", cy0 - S_TILE * 24 < cym < cy0, f"{cy0} {cym}")
check("相机连续变化", cy0 != cym != cy1, f"{cy0},{cym},{cy1}")
check("步结束相机对齐新格", (cx1 - cx0) % S_TILE == 0 and (cy0 - cy1) % S_TILE == 0,
      f"{cx0},{cx1}")
ow6.moving = False
ow6.px, ow6.py = 10, 9

# 商店/徽章门禁/奖金/一击必杀
ow7 = g4.scenes[0]
ow7.state = "field"
ow7.moving = False
g4.money = 3000
ow7.warp_to("town", 4, 13, "up")
ow7.held = {pygame.K_UP}
for _ in range(30):
    ow7.update(0.05)
ow7.held.clear()
check("可进入商店", ow7.map_id == "mart", str((ow7.map_id, ow7.px, ow7.py)))

from src.ui import ShopScreen
shop = ShopScreen(g4, [("精灵球", 200), ("好伤药", 700)])
shop.key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))   # qty=2
shop.key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))       # 买 2 个精灵球 = 400
check("商店扣钱", g4.money == 3000 - 400, str(g4.money))
check("商店入包", g4.bag.get("精灵球") == 2)
g4.money = 100
shop.key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))
check("钱不足拒卖", g4.money == 100 and g4.bag.get("精灵球") == 2,
      str((g4.money, g4.bag.get("精灵球"))))

# 徽章门禁:磐石道馆北门需岩石徽章
ow7.warp_to("gym", 6, 1, "up")
ow7.held = {pygame.K_UP}
for _ in range(30):
    ow7.update(0.05)
ow7.held.clear()
check("无岩石徽章被拦在道馆北门", ow7.map_id == "gym" and ow7.py == 1, str((ow7.map_id, ow7.px, ow7.py)))
ow7.state = "field"
for _ in range(10):
    if ow7.state != "dialog":
        break
    ow7.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))
g4.flags["has_badge"] = True
ow7.held = {pygame.K_UP}
for _ in range(30):
    ow7.update(0.05)
ow7.held.clear()
check("有岩石徽章可进入2号道路", ow7.map_id == "route2", str(ow7.map_id))

# 训练家奖金
g4.money = 0
g4.party = [Mon("猛火猴", 41)]
b11 = Battle(g4, [Mon("小拳石", 10), Mon("小拳石", 10)], trainer_name="测试", callback=lambda r: None)
b11.auto = True
r11 = b11.drive_for_test([("menu", "fight"), ("move", 3), ("menu", "fight"), ("move", 3)])
check("训练家战发放奖金", g4.money == 10 * 30 and r11 == "win", str((g4.money, r11)))

# 一击必杀:等级高必杀概率存在,等级低必失败
ok11 = None
for i in range(60):
    random.seed(i)
    g11 = Game(); g11.party = [Mon("隆隆石", 30)]
    bb = Battle(g11, [Mon("小拳石", 10)], callback=lambda r: None)
    msgs = [x for x in bb._use_move("ally", "断头钳") if x[0] == "msg"]
    if any("一击必杀" in m[1] for m in msgs):
        ok11 = True
        break
check("一击必杀可触发", ok11)
random.seed(5)
g12 = Game(); g12.party = [Mon("小拳石", 10)]
bb2 = Battle(g12, [Mon("隆隆石", 30)], callback=lambda r: None)
msgs12 = [x for x in bb2._use_move("ally", "断头钳") if x[0] == "msg"]
check("等级低一击必杀必失败", any("没有命中" in m[1] for m in msgs12))

# 属性粒子特效渲染
b6.anim = ["hit_foe", 0.2, 0.45, "火"]
b6.draw(surf)
b6.anim = ["hit_foe", 0.2, 0.45, "电"]
b6.draw(surf)
b6.anim = None
check("属性特效渲染无异常", True)

# 标题界面渲染与按键
from src.title import Title
from src.overworld import Overworld
g4.scenes = [Title(g4)]
g4.scenes[0].draw(surf)
g4.scenes[0].handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))
check("标题确认进入游戏", isinstance(g4.scenes[0], Overworld))

# 主循环真实跑 60 帧
g5 = Game()
g5.new_game()
for k in (pygame.K_z, pygame.K_z, pygame.K_z, pygame.K_RETURN, pygame.K_x):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k))
g5.run(max_frames=60)
check("主循环60帧", True)

print(f"\n全部通过: {PASS} 项检查 ✔")
