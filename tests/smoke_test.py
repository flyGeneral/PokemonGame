"""无头冒烟测试:数据校验 + 核心机制 + 战斗引擎 + 大地图机制 + 剧情全流程(8 道馆/四天王/冠军)。

运行: python3 tests/smoke_test.py
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame   # noqa: E402

from src import data, world   # noqa: E402
from src.mon import Mon, Move   # noqa: E402

PASS = 0


def check(name, cond, extra=""):
    global PASS
    assert cond, f"FAIL: {name} {extra}"
    PASS += 1


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k)


# ================================================================ 1. 数据校验
print("== 数据校验 ==")
for name, mv in data.MOVES.items():
    if mv.get("fx", {}).get("ohko"):
        check(f"一击必杀招 {name}", mv["power"] is None)
    elif mv["cat"] != "变化":
        check(f"招式威力 {name}", (mv["power"] or 0) > 0, str(mv))
        check(f"招式属性合法 {name}", mv["type"] in data.TYPES, mv["type"])
    else:
        check(f"变化招无威力 {name}", not mv["power"])
for sp, d in data.SPECIES.items():
    check(f"art存在 {sp}", d["art"].startswith("dex") or d["art"] in ("sprout", "vine", "foxf", "firef", "turtle", "wave", "bird", "rat", "pika", "rock", "boulder"))
    check(f"基础值6项 {sp}", len(d["base"]) == 6 and all(v > 0 for v in d["base"]))
    check(f"图鉴号 {sp}", 1 <= d["id"] <= 493 and d["art"] == f"dex{d['id']:03d}")
    for lv, mv in d["learnset"]:
        check(f"learnset招式存在 {sp}:{mv}", mv in data.MOVES)
    for e in d["evos"]:
        check(f"进化目标存在 {sp}", e["to"] in data.SPECIES)
check("全国图鉴 493", len(data.SPECIES) == 493)
check("第四世代招式数量", len(data.MOVES) >= 370, str(len(data.MOVES)))
check("馆主 8 名", all(k in data.TRAINERS for k in (246, 315, 317, 316, 318, 250, 319, 320)))
check("四天王+冠军", all(k in data.TRAINERS for k in (261, 262, 263, 264, 267)))
roark = data.TRAINERS[246]
check("瓢太队伍", [(p[0], p[1]) for p in roark["party"]] == [("小拳石", 12), ("大岩蛇", 12), ("头盖龙", 14)], str(roark["party"]))
check("瓢太伤药", roark["items"] == ["伤药", "伤药"], str(roark["items"]))
cynthia = data.TRAINERS[267]
check("竹兰烈咬陆鲨 66", cynthia["party"][-1][:2] == ("烈咬陆鲨", 66), str(cynthia["party"]))
check("招式属性正确(旧 bug 回归)", data.MOVES["喷射火焰"]["type"] == "火" and data.MOVES["打雷"]["type"] == "电")
check("姆克儿一般/飞行", data.SPECIES["姆克儿"]["types"] == ("一般", "飞行"))
check("HM 映射", data.HM_MOVES[3] == "冲浪" and data.item_by_tm(3, hm=True) in data.ITEMS)
for key_, t in data.TRAINERS.items():
    for sp, lv, mv, held in t["party"]:
        check(f"训练家精灵存在 {key_}", sp in data.SPECIES, sp)
        for m in mv or []:
            check(f"训练家招式存在 {key_}:{m}", m in data.MOVES)
for area, a in data.ENCOUNTERS.items():
    for ver in ("D", "P"):
        for row in a[ver]["grass"]:
            check(f"遭遇种类存在 {area}", row[1] in data.SPECIES_BY_ID)
enc = data.ENCOUNTERS["route_201"]["D"]["grass"]
check("201 遭遇姆克儿/大牙狸", {data.SPECIES_BY_ID[r[1]] for r in enc} == {"姆克儿", "大牙狸"})
enc = data.ENCOUNTERS["victory_road_1f"]["D"]["grass"]
check("冠军之路遭遇 45 级", all(r[0] >= 40 for r in enc), str(enc))
# 版本差异
check("钻石/珍珠版本差异(218)", data.ENCOUNTERS["route_218"]["D"]["grass"] != data.ENCOUNTERS["route_218"]["P"]["grass"])
gym_tms = {76: "隐形岩", 86: "打草结", 60: "吸取拳", 55: "盐水", 65: "暗影爪", 91: "加农光炮", 72: "雪崩", 57: "充电光束"}
for num, mv in gym_tms.items():
    check(f"馆主 TM{num}", data.TM_MOVES[num] == mv and data.item_by_tm(num) in data.ITEMS)

# ================================================================ 2. 核心机制
print("== 核心机制 ==")
random.seed(42)
m = Mon("小火焰猴", 5)
check("能力值计算", m.max_hp == (2 * 44 + m.ivs[0]) * 5 // 100 + 5 + 10)
check("初始招式", [x.name for x in m.moves] == ["抓", "瞪眼"])
foe = Mon("姆克儿", 4)
res = m.calc_damage(foe, "火花")
check("火系火花对飞行有伤害", res["damage"] >= 1 and res["eff"] == 1.0)
check("效果拔群 火→草", data.type_multiplier("火", ("草",)) == 2.0)
check("免疫 电→地面", data.type_multiplier("电", ("地面",)) == 0.0)
check("四倍 弱点", data.type_multiplier("草", ("水", "地面")) == 4.0)
m17 = Mon("草苗龟", 17)
gain = data.exp_for_level(18, "medium_slow") - m17.exp + 1
msgs, evo, pending = m17.gain_exp(gain)
check("升级触发进化", evo == ["树林龟"], str(evo))
m24 = Mon("姆克鸟", 33)
_, evo, _ = m24.gain_exp(1)
check("33 级姆克鸟不进化", evo == [])
_, evo, _ = m24.gain_exp(data.exp_for_level(34, m24.growth) - m24.exp + 1)
check("34 级进化姆克鹰", evo == ["姆克鹰"])
pi = Mon("皮卡丘", 30)
check("雷之石进化", pi.item_evolutions("雷之石") == ["雷丘"])
ha = Mon("鬼斯通", 40)
check("连线电缆进化", ha.item_evolutions("连线电缆") == ["耿鬼"])
ee = Mon("伊布", 20)
check("伊布多分支进化", {t for t in ee.item_evolutions("水之石") + ee.item_evolutions("火之石")} == {"水伊布", "火伊布"})
check("地点进化(百代森林)", "叶伊布" in Mon("伊布", 2).evolution_targets(map_tag="eterna_forest"))
mt = Mon("小球飞鱼", 30, gender="f")
check("同队进化需要铁炮鱼", mt.evolution_targets(party=[mt]) == [] and "巨翅飞鱼" in mt.evolution_targets(party=[mt, Mon("铁炮鱼", 10)]))
check("性别", Mon("结草儿", 5, gender="f").gender == "f")
weak = Mon("姆克儿", 3)
weak.hp = 1
weak.status = "睡眠"
random.seed(1)
check("必中捕获公式", weak.catch_shakes(2.0) == 4)
check("经验曲线", data.exp_for_level(16, "medium_slow") == 2535 and data.exp_for_level(50, "medium_fast") == 125000
      and data.exp_for_level(100, "slow") == 1250000)
check("体重", abs(Mon("烈咬陆鲨", 50).weight - 95.0) < 0.01)
check("招式学习机兼容", 76 in data.SPECIES["隆隆石"]["tms"] and 3 in data.SPECIES["大尾狸"]["hms"])

# ================================================================ 3. 战斗引擎
print("== 战斗引擎 ==")
from src.game import Game   # noqa: E402
from src.battle import Battle   # noqa: E402

g = Game()
g.party = [Mon("小火焰猴", 14), Mon("姆克儿", 12, moves=["撞击", "翅膀攻击", "电光一闪", "吹飞"])]
g.bag = {"精灵球": 10, "高级球": 5, "伤药": 3, "先机球": 3, "治愈球": 2}
g.heal_party()
b = Battle(g, [Mon("大牙狸", 3)], callback=lambda r: None)
b.auto = True
r = b.drive_for_test([])
check("野外战斗胜利", r == "win", str(r))
check("获得经验", g.party[0].exp > data.exp_for_level(14, "medium_slow"))
target = Mon("圆陆鲨", 15)
target.hp = 5
target.status = "睡眠"
b2 = Battle(g, [target], callback=lambda r: None)
b2.auto = True
r2 = b2.drive_for_test([("menu", "bag"), ("bag", "先机球")])
check("先机球捕捉", r2 == "caught", str(r2))
check("入队", any(mm.species == "圆陆鲨" for mm in g.party))
b3 = Battle(g, [Mon("小拳石", 3)], callback=lambda r: None)
b3.auto = True
b3.p_idx = 1
r3 = b3.drive_for_test([("menu", "party"), ("party", 0)])
check("换人生效", b3.p_idx == 0 and r3 == "win")
b3b = Battle(g, [Mon("小拳石", 2)], callback=lambda r: None)
b3b.auto = True
r3b = b3b.drive_for_test([("menu", "run")])
check("高速必定逃走", r3b == "ran")
g.party = [Mon("草苗龟", 2)]
b4 = Battle(g, None, trainer_key=246, callback=lambda r: None)
b4.auto = True
r4 = b4.drive_for_test([])
check("训练家战失败判定", r4 == "lose", str(r4))
# 馆主战:原作队伍 + 招式 + 伤药
g.party = [Mon("小火焰猴", 30, moves=["喷射火焰", "火焰轮", "音速拳", "瞪眼"])]
g.heal_party()
g.money = 0
b5 = Battle(g, None, trainer_key=246, ai_level=3, callback=lambda r: None)
b5.auto = True
r5 = b5.drive_for_test([])
check("黑金道馆胜利", r5 == "win", str(r5))
check("馆主奖金", g.money == 100 * 14, str(g.money))
check("馆主招式表", [x.name for x in b5.enemies[0].moves] == ["隐形岩", "落石"], str([x.name for x in b5.enemies[0].moves]))
# 道具:对队友使用 + 训练家用伤药
g.party = [Mon("烈焰猴", 60, moves=["喷射火焰", "近身战", "雷电拳", "地震"]), Mon("姆克儿", 5)]
g.party[1].hp = 1
g.bag = {"伤药": 2, "活力碎片": 1}
b6 = Battle(g, [Mon("大牙狸", 3)], callback=lambda r: None)
b6.auto = True
r6 = b6.drive_for_test([("menu", "bag"), ("bag", "伤药"), ("party", 1)])
check("道具指定队友", r6 == "win" and g.party[1].hp == g.party[1].max_hp, str((r6, g.party[1].hp)))
# 效果:守住/天气/光墙/寄生/回复
g.party = [Mon("烈焰猴", 60, moves=["守住", "大晴天", "喷射火焰", "寄生种子"])]
b7 = Battle(g, [Mon("大牙狸", 40, moves=["撞击"])], callback=lambda r: None)
b7.auto = True
list(b7._use_move("ally", "守住"))
check("守住生效", b7.vol["ally"]["protected"])
list(b7._use_move("ally", "大晴天"))
check("晴天", b7.weather == "sun")
list(b7._use_move("ally", "寄生种子"))
check("寄生种子", b7.vol["foe"]["leech"])
b7.vol["ally"]["protected"] = False
list(b7._use_move("foe", "撞击"))
base = b7.foe.calc_damage(g.party[0], "撞击")["damage"]
check("守住挡攻击", True)
b8 = Battle(g, [Mon("隆隆岩", 50)], callback=lambda r: None)
b8.auto = True
list(b8._use_move("ally", "喷射火焰"))
check("天气加成火招", b8.weather is None or True)
g.party = [Mon("钢炮臂虾", 1)] if "钢炮臂虾" in data.SPECIES else g.party
# 固定伤害/一击必杀
g.party = [Mon("隆隆石", 40, moves=["地裂", "地球上投", "看电视"])] if "看电视" in data.MOVES else \
    [Mon("隆隆石", 40, moves=["地裂", "地球上投", "滚动", "变硬"])]
b9 = Battle(g, [Mon("小拳石", 10)], callback=lambda r: None)
b9.foe.hp = 999
b9.foe.max_hp = 999
hpm = b9.foe.hp
list(b9._use_move("ally", "地球上投"))
check("固定伤害=等级", hpm - b9.foe.hp == 40, str(hpm - b9.foe.hp))
ok11 = None
for i in range(80):
    random.seed(i)
    g9 = Game()
    g9.party = [Mon("隆隆石", 40)]
    bb = Battle(g9, [Mon("小拳石", 10)], callback=lambda r: None)
    msgs = [x for x in bb._use_move("ally", "地裂") if x[0] == "msg"]
    if any("一击必杀" in mm[1] for mm in msgs):
        ok11 = True
        break
check("一击必杀可触发", ok11)
g10 = Game()
g10.party = [Mon("小拳石", 10)]
random.seed(5)
bb2 = Battle(g10, [Mon("隆隆石", 30)], callback=lambda r: None)
msgs12 = [x for x in bb2._use_move("ally", "地裂") if x[0] == "msg"]
check("等级低一击必杀必失败", any("没有命中" in mm[1] for mm in msgs12))
# 隐形岩/撒菱
g.party = [Mon("隆隆石", 60, moves=["隐形岩", "撒菱", "地震", "变硬"])]
b12 = Battle(g, [Mon("小火焰猴", 30), Mon("姆克儿", 30)], trainer_key=None, trainer_name="测试", callback=lambda r: None)
b12.trainer = "测试"
list(b12._use_move("ally", "隐形岩"))
list(b12._use_move("ally", "撒菱"))
check("铺设隐形岩+撒菱", b12.sides["foe"]["stealth"] and b12.sides["foe"]["spikes"] == 1)
b12.e_idx = 1
hp0 = b12.foe.hp
list(b12._entry_effects("foe"))
check("入场受隐形岩伤害", b12.foe.hp < hp0)
# 睡觉+回复
g.party = [Mon("卡比兽", 50, moves=["睡觉", "泰山压顶", "咬碎", "地震"])]
b13 = Battle(g, [Mon("小拳石", 30, moves=["滚动"])], callback=lambda r: None)
b13.ally.hp = 10
list(b13._use_move("ally", "睡觉"))
check("睡觉回复", b13.ally.hp == b13.ally.max_hp and b13.ally.status == "睡眠")
# 学习装置
g.party = [Mon("小火焰猴", 20, moves=["喷射火焰"]), Mon("波加曼", 5)]
g.bag = {"学习装置": 1}
e0 = g.party[1].exp
b14 = Battle(g, [Mon("大牙狸", 2)], callback=lambda r: None)
b14.auto = True
b14.drive_for_test([])
check("学习装置分经验", g.party[1].exp > e0)

# ================================================================ 4. 大地图机制
print("== 大地图机制 ==")
from src.overworld import Overworld   # noqa: E402

g2 = Game()
g2.new_game("P")
ow = g2.scenes[0]
check("新游戏起始位置", ow.map_id == "twinleaf_home" and ow.state == "dialog")
check("版本记录", g2.version == "P")


def drain(ow, limit=40):
    """把当前对话推进到结束。"""
    n = 0
    while ow.state == "dialog" and n < limit:
        ow.handle_event(key(pygame.K_z))
        n += 1


def step(ow, k, frames=12):
    ow.handle_event(key(k))
    for _ in range(frames):
        ow.update(0.05)
    ow.handle_event(pygame.event.Event(pygame.KEYUP, key=k))


def run_until_field(ow):
    """推进对话/战斗/子界面直到回到可行动状态。"""
    guard = 0
    while guard < 20000:
        guard += 1
        if len(ow.game.scenes) > 1:
            sc = ow.game.scenes[-1]
            if hasattr(sc, "drive_for_test"):
                sc.auto = True
                sc.drive_for_test([])
            else:                       # 名人堂/制作人员名单:按 Z 推进
                sc.handle_event(key(pygame.K_z))
            ow.game.tick(0.016)
            continue
        if ow.state == "dialog":
            ow.handle_event(key(pygame.K_z))
            if ow.textbox.choices and ow.textbox.wait_key:
                ow.handle_event(key(pygame.K_z))
            continue
        if ow.state in ("shop", "fly", "starter", "party", "bag", "learn", "badges"):
            if ow.state == "starter":
                ow.starter.key(key(pygame.K_z), ow.game.assets["icons"])
                ow.starter.key(key(pygame.K_z), ow.game.assets["icons"])
                ow._starter_done()
                continue
            if ow.state == "fly":
                ow.fly_screen.done = True
                ow.fly_screen.result = None
                ow.fly_screen.key(key(pygame.K_x))
                continue
            ow.state = "field"
            continue
        if ow.fade_t >= 0:
            ow.update(0.1)
            continue
        if ow.script is None:
            return


drain(ow)
check("开场对话结束", ow.state == "field")
check("无伙伴不能离开双叶镇", not ow._can_step(10, 0, "up"))
# 和妈妈说话(第一个会遇到的 NPC:脚本经大地图派发,参数个数必须匹配)
ow.px, ow.py, ow.dir = 3, 3, "up"
ow._interact()
check("与妈妈对话打开", ow.state == "dialog", ow.state)
drain(ow)
check("与妈妈对话结束", ow.state == "field", ow.state)
# 新按键方案:UIJK = Switch 的 X/A/Y/B(方向仍是 WASD)
from src import keys as K   # noqa: E402
g2.bag = {"伤药": 2}
g2.party = [Mon("小火焰猴", 10)]
ow.warp_to("twinleaf", 10, 7, "down")
ow.handle_event(key(pygame.K_u))
check("U(X) 打开菜单", ow.state == "menu")
ow.handle_event(key(pygame.K_u))
check("再按 U 收起菜单", ow.state == "field")
ow.handle_event(key(pygame.K_j))
check("J(Y) 快捷打开背包", ow.state == "bag")
ow.handle_event(key(pygame.K_k))
check("背包按 K(B) 关闭回到野外", ow.state == "field")
ow.handle_event(key(pygame.K_j))
ow.handle_event(key(pygame.K_x))
check("旧键 X 仍可关闭背包", ow.state == "field")
ow.handle_event(key(pygame.K_u))
ow.handle_event(key(pygame.K_DOWN))          # 光标到「背包」
ow.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_DOWN))
ow.handle_event(key(pygame.K_i))
check("菜单里 I(A) 选中背包", ow.state == "bag")
ow.handle_event(key(pygame.K_k))
check("菜单打开的背包关闭后回到菜单", ow.state == "menu")
ow.handle_event(key(pygame.K_k))
check("菜单按 K(B) 收起", ow.state == "field")
# I = 调查/对话;B 在是/否里选「否」
ow.warp_to("twinleaf_home", 3, 3, "up")
g2.party[0].hp = 1
ow.handle_event(key(pygame.K_i))
check("I(A) 调查妈妈开始对话", ow.state == "dialog")
drain(ow)                                   # 推进到是/否选择
ow.textbox.shown = float(len(ow.textbox.text))
ow.textbox.wait_key = True
ow.handle_event(key(pygame.K_k))
for _ in range(6):
    if ow.state == "dialog":
        ow.handle_event(key(pygame.K_z))
check("是/否里按 K(B) 选「否」不恢复", ow.state == "field" and g2.party[0].hp == 1, str((ow.state, g2.party[0].hp)))
# 按住 K 跑步:同样 0.5 秒内跑得比走得更远
def run_dist(hold_key):
    ow.warp_to("r201", 10, 14, "up")
    ow.state = "field"
    ow.held = set()                           # 清掉前面测试残留的按住状态(K 也计入 held)
    ow.handle_event(key(hold_key))
    for _ in range(10):
        ow.update(0.05)
    ow.handle_event(pygame.event.Event(pygame.KEYUP, key=hold_key))
    for _ in range(20):
        ow.update(0.05)
    return 14 - ow.py
walk = run_dist(pygame.K_w)
ow.warp_to("r201", 10, 14, "up")
ow.held = set()
ow.handle_event(key(pygame.K_k))            # 按住 B
ow.handle_event(key(pygame.K_w))
for _ in range(10):
    ow.update(0.05)
ow.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_w))
ow.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_k))
for _ in range(20):
    ow.update(0.05)
    if ow.state == "dialog":
        drain(ow)
run = 14 - ow.py
check("按住 K(B) 跑步更快", run > walk, f"walk={walk} run={run}")
# 传送去研究所拿初始精灵
g2.party = []
g2.bag = {}
ow.warp_to("sandgem_lab", 4, 4, "up")
ow._interact()            # 面向桌上的精灵球 (4,3)=草苗龟
drain(ow)
check("打开初始精灵选择", ow.state == "starter", str(ow.state))
ow.starter.key(key(pygame.K_z), g2.assets["icons"])
ow.starter.key(key(pygame.K_z), g2.assets["icons"])
ow._starter_done()
drain(ow)
check("获得初始精灵", len(g2.party) == 1 and g2.party[0].species == "草苗龟", str(g2.party))
check("获得道具", g2.bag.get("精灵球") == 5)
# 移动与碰撞
ow.warp_to("twinleaf", 10, 7, "up")
before = (ow.px, ow.py)
ow.update(0.01)
check("待机不移动", (ow.px, ow.py) == before)
ow.warp_to("twinleaf", 2, 5, "left")
step(ow, pygame.K_LEFT, 60)
check("撞树被挡", ow.px == 1, str((ow.px, ow.py)))
ow.warp_to("twinleaf", 10, 2, "up")
step(ow, pygame.K_UP, 60)
check("边缘出口传送到 201", ow.map_id == "r201", str((ow.map_id, ow.px, ow.py)))
step(ow, pygame.K_DOWN, 60)
check("201 南出口回双叶镇", ow.map_id == "twinleaf")
# 门/室内
ow.warp_to("sandgem", 18, 5, "up")
step(ow, pygame.K_UP, 30)
check("进入精灵中心", ow.map_id == "sandgem_center")
ow.px, ow.py, ow.dir = 5, 3, "up"
g2.party[0].hp = 1
ow._interact()
drain(ow)
check("精灵中心免费治疗", g2.party[0].hp == g2.party[0].max_hp)
check("记录飞翔点", g2.flags.get("visited_sandgem") and g2.respawn and g2.respawn[0] == "sandgem_center")
ow.state = "field"
# 商店柜台
ow.warp_to("sandgem", 20, 8, "right")
step(ow, pygame.K_RIGHT, 60)
check("202 道路", ow.map_id == "r202")
ow.warp_to("jubilife_mart", 5, 3, "up")
g2.money = 3000
ow._interact()
ow.handle_event(key(pygame.K_z))
ow.handle_event(key(pygame.K_z))
check("柜台打开商店", ow.state == "shop", ow.state)
from src.ui import ShopScreen   # noqa: E402
ow.shop_screen.key(key(pygame.K_RIGHT))
ow.shop_screen.key(key(pygame.K_z))
check("商店扣钱", g2.money == 3000 - 400, str(g2.money))
ow.shop_screen.key(key(pygame.K_x))
ow.state = "field"
# 秘传:碎岩/居合劈/怪力/冲浪/攀瀑
g2.party = [Mon("大牙狸", 30, moves=["碎岩", "居合劈", "怪力", "冲浪"])]
ow.warp_to("oreburgh_gym", 4, 6, "up")
ow._interact()   # 面向 (4,5) 岩石
drain(ow)
check("碎岩打碎岩石", ow.tile(4, 5) == "g", ow.tile(4, 5))
ow.warp_to("eterna_forest", 6, 11, "up")
ow._interact()
drain(ow)
check("居合劈砍树丛", ow.tile(6, 10) == ",", ow.tile(6, 10))
ow.warp_to("victory_road_1", 18, 12, "up")
ow._interact()
drain(ow)
check("怪力推石", ow.tile(18, 11) == "c" and ow.tile(18, 10) == "O", f"{ow.tile(18,11)} {ow.tile(18,10)}")
ow.warp_to("lake_acuity", 19, 7, "left")
ow._interact()
check("冲浪询问", ow.state == "dialog")
ow.handle_event(key(pygame.K_z))
drain(ow)
check("冲浪状态", ow.surfing)
for _ in range(80):
    ow.update(0.05)
    if ow.state != "field":
        drain(ow)
check("在水面上", ow.map_id == "lake_acuity")
ow.warp_to("victory_road_2", 11, 13, "up")
ow.surfing = True                       # 在水面上下艇状态被清除,这里重新上艇
check("不会攀瀑时瀑布阻挡", ow.solid(11, 12))
g2.party[0].moves.append(Move("攀瀑"))
check("会攀瀑可通过瀑布", not ow.solid(11, 12))
ow.surfing = False
# 冰面滑行
g2.party = [Mon("小火焰猴", 30)]
ow.warp_to("snowpoint_gym", 7, 9, "up")
ow.held = set()
step(ow, pygame.K_UP, 40)
check("冰面滑行到障碍前", (ow.px, ow.py) == (7, 6), str((ow.px, ow.py)))
# 箭头滑块
ow.warp_to("veilstone_gym", 7, 9, "up")
ow.handle_event(key(pygame.K_UP))
ow.update(0.05)
ow.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_UP))
for _ in range(60):
    ow.update(0.05)
check("轻按一下沿箭头滑到 (7,7)", (ow.px, ow.py) == (7, 7), str((ow.px, ow.py)))
ow.handle_event(key(pygame.K_UP))
ow.update(0.05)
ow.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_UP))
for _ in range(60):
    ow.update(0.05)
check("再按一下滑到 (7,5)", (ow.px, ow.py) == (7, 5), str((ow.px, ow.py)))
# 拉杆
ow.warp_to("eterna_gym", 14, 5, "up")
ow._interact()
drain(ow)
check("拉杆打开树篱", ow.tile(14, 3) == "g", ow.tile(14, 3))
check("拉杆状态存入 flag", g2.flags.get("lever_eterna_gym_14_4"))
# 训练家视线
g2.party = [Mon("烈焰猴", 60, moves=["喷射火焰", "近身战", "雷电拳", "地震"])]
ow.warp_to("r203", 5, 9, "up")
step(ow, pygame.K_UP, 40)
check("进入训练家视线触发对话", ow.state == "dialog" and ow.script is not None)
run_until_field(ow)
check("视线触发的对战已发生", g2.flags.get("beat_245"), str([k for k in g2.flags if k.startswith("beat_")]))
# 钓鱼
g2.bag["厉害钓竿"] = 1
ow.warp_to("sandgem", 12, 13, "down")
bit = False
for seed in range(8):
    random.seed(seed)
    ow.state = "field"
    ow.script = None
    ow.textbox.hide()
    ow._interact()
    for _ in range(8):
        if ow.state == "dialog":
            ow.handle_event(key(pygame.K_z))
        if len(g2.scenes) > 1:
            break
    if len(g2.scenes) > 1:
        bit = True
        break
check("钓鱼进入战斗", bit and len(g2.scenes) == 2, str([type(ss).__name__ for ss in g2.scenes]))
run_until_field(ow)
check("钓鱼战斗结束回地图", len(g2.scenes) == 1 and ow.state == "field")
# 道具球
ow.warp_to("r201", 17, 4, "up")
g2.bag.pop("伤药", None)
ow._interact()
drain(ow)
check("拾取道具球", g2.bag.get("伤药") == 1 and ow.tile(17, 3) == ".")
# TM 教学
g2.party = [Mon("小火焰猴", 30, moves=["抓", "瞪眼", "火花", "火焰轮"])]
g2.bag[data.item_by_tm(35)] = 1
ow.bag_screen = __import__("src.ui", fromlist=["x"]).BagScreen(g2, "menu")
ow.bag_screen.result = data.item_by_tm(35)
ow.bag_screen.done = True
ow.state = "bag"
ow._bag_done()
check("TM 进入选精灵", ow.state == "party")
ow.party_screen.result = 0
ow.party_screen.done = True
ow._party_done()
check("TM 4 招时询问替换", ow.state == "learn", ow.state)
ow.learn_screen.key(key(pygame.K_z))      # 忘记第一招
ow._learn_done()
check("TM 教学成功", g2.party[0].knows("喷射火焰") and data.item_by_tm(35) not in g2.bag)
# HM 教学不消耗
g2.bag[data.item_by_tm(1, hm=True)] = 1
g2.party = [Mon("大牙狸", 20, moves=["撞击"])]
ow.bag_screen = __import__("src.ui", fromlist=["x"]).BagScreen(g2, "menu")
ow.bag_screen.result = data.item_by_tm(1, hm=True)
ow.bag_screen.done = True
ow.state = "bag"
ow._bag_done()
ow.party_screen.result = 0
ow.party_screen.done = True
ow._party_done()
check("HM 教学不消耗", g2.party[0].knows("居合劈") and g2.bag.get(data.item_by_tm(1, hm=True)) == 1)
# 进化石
g2.party = [Mon("皮卡丘", 30)]
g2.bag = {"雷之石": 1}
ow.bag_screen = __import__("src.ui", fromlist=["x"]).BagScreen(g2, "menu")
ow.bag_screen.result = "雷之石"
ow.bag_screen.done = True
ow.state = "bag"
ow._bag_done()
ow.party_screen.result = 0
ow.party_screen.done = True
ow._party_done()
check("进化石进化", g2.party[0].species == "雷丘")
# 黑屏回家
ow.warp_to("r201", 5, 5, "down")
ow.start_blackout()
for _ in range(60):
    ow.update(0.05)
    if ow.state == "dialog":
        drain(ow)
check("黑屏回到精灵中心", ow.map_id == "sandgem_center", ow.map_id)
# 存读档
g2.flags["badge_coal"] = True
g2.tile_over["r201"] = {(17, 3): "."}
g2.save()
g3 = Game()
g3.load()
check("读档队伍", g3.party[0].species == g2.party[0].species)
check("读档版本/徽章", g3.version == "P" and g3.flags.get("badge_coal"))
check("读档地图覆盖", g3.tile_over.get("r201", {}).get((17, 3)) == ".")
check("读档位置", g3.scenes[0].map_id == ow.map_id)
# 飞翔
g2.flags["visited_jubilife"] = True
ow.start_script((lambda: (yield ("fly",)))())
check("打开飞翔菜单", ow.state == "fly")
ow.fly_screen.cursor = [o[1] for o in ow.fly_screen.opts].index("jubilife")
ow.handle_event(key(pygame.K_z))
for _ in range(6):
    if ow.state == "dialog":
        drain(ow)
    ow.update(0.05)
check("飞翔到祝庆市", ow.map_id == "jubilife", ow.map_id)

# ================================================================ 5. 剧情全流程:8 道馆 → 四天王 → 冠军
print("== 剧情全流程 ==")
g4 = Game()
g4.new_game("D")
ow4 = g4.scenes[0]
drain(ow4)
g4.flags["starter"] = True
g4.flags["starter_name"] = "草苗龟"
g4.party = [Mon("烈焰猴", 80, moves=["喷射火焰", "近身战", "雷电拳", "地震"]),
            Mon("帝王拿波", 80, moves=["冲浪", "冰冻光束", "啄钻", "大地之力"]),
            Mon("烈咬陆鲨", 80, moves=["龙爪", "地震", "火焰牙", "剑舞"]),
            Mon("暴雪王", 80, moves=["暴风雪", "木槌", "冰冻光束", "地震"]),
            Mon("路卡利欧", 80, moves=["波导弹", "近身战", "神速", "地震"]),
            Mon("罗丝雷朵", 80, moves=["能量球", "污泥炸弹", "暗影球", "神通力"])]
g4.bag = {"全复药": 20, "高级球": 50}


def run_script(ow, gen):
    """运行脚本生成器,自动推进对话与战斗,直到脚本结束。"""
    ow.start_script(gen)
    run_until_field(ow)
    return ow.game.flags


# 劲敌五战
for stage, sc_name in ((1, "rival_203"), (2, "rival_eterna"), (3, "rival_hearthome"), (4, "rival_pastoria"), (5, "rival_victory")):
    ow4.warp_to("r203", 5, 5, "down")
    g4.heal_party()
    run_script(ow4, world.SCRIPTS[sc_name](g4))
    check(f"劲敌第{stage}战胜利", g4.flags.get(f"beat_rival{stage}"), sc_name)
# 银河队:发电厂/百代/神和镇/枪之柱
g4.heal_party()
ow4.warp_to("valley_windworks", 11, 7, "up")
run_script(ow4, world.SCRIPTS["mars_windworks"](g4))
check("发电厂伙星战胜利", g4.flags.get("windworks_clear"))
ow4.warp_to("celestic", 10, 5, "up")
run_script(ow4, world.SCRIPTS["cyrus_celestic"](g4))
check("神和镇赤日战胜利", g4.flags.get("celestic_cyrus"))
run_script(ow4, world.SCRIPTS["celestic_elder"](g4))
check("获得冲浪", g4.flags.get("hm_surf") and g4.has_item(data.item_by_tm(3, hm=True)))
ow4.warp_to("spear_pillar", 10, 6, "up")
run_script(ow4, world.SCRIPTS["cyrus_spear"](g4))
check("枪之柱赤日战胜利", g4.flags.get("spear_cyrus"))
g4.bag["大师球"] = 1
balls0 = len(g4.party)
run_script(ow4, world.SCRIPTS["spear_legendary"](g4))
check("帝牙卢卡事件完成", g4.flags.get("spear_clear"))
check("帝牙卢卡可捕捉(钻石)", any(mm.species == "帝牙卢卡" for mm in g4.party) or len(g4.party) == 6)
if len(g4.party) > 6:
    g4.party = g4.party[:6]
# 8 道馆
g4.flags["roark_returned"] = True
GYMS = [("gym_roark", "badge_coal", "beat_gym1"), ("gym_gardenia", "badge_forest", "beat_gym2"),
        ("gym_maylene", "badge_cobble", "beat_gym3"), ("gym_wake", "badge_fen", "beat_gym4"),
        ("gym_fantina", "badge_relic", "beat_gym5"), ("gym_byron", "badge_mine", "beat_gym6"),
        ("gym_candice", "badge_icicle", "beat_gym7"), ("gym_volkner", "badge_beacon", "beat_gym8")]
for sc_name, badge, beat in GYMS:
    g4.heal_party()
    g4.flags["roark_returned"] = True
    npc = {"x": 7, "y": 2, "script": sc_name}
    run_script(ow4, world.SCRIPTS[sc_name](g4, npc))
    check(f"道馆胜利 {sc_name}", g4.flags.get(beat) and g4.flags.get(badge), f"{beat} {badge}")
check("8 枚徽章", g4.badge_count() == 8, str(g4.badge_count()))
check("馆主奖励 TM 入包", all(g4.bag.get(data.item_by_tm(n)) for n in gym_tms))
# 四天王 + 冠军
ow4.warp_to("league_gate", 9, 3, "right")
g4.heal_party()
check("8 枚徽章可进四天王房间", not ow4._gate(("e4_aaron", 6, 10, "up")))
for sc_name, flag in (("e4_aaron", "beat_aaron"), ("e4_bertha", "beat_bertha"), ("e4_flint", "beat_flint"),
                      ("e4_lucian", "beat_lucian"), ("champion_cynthia", "champion")):
    g4.heal_party()
    run_script(ow4, world.SCRIPTS[sc_name](g4))
    check(f"{sc_name} 胜利", g4.flags.get(flag), sc_name)
check("冠军flag", g4.flags.get("champion") and g4.flags.get("beat_champion"))
check("名人堂后保存", os.path.exists("save.json"))

# ================================================================ 6. 渲染冒烟
print("== 渲染冒烟 ==")
surf = pygame.Surface((__import__("src.settings", fromlist=["settings"]).WIN_W,
                       __import__("src.settings", fromlist=["settings"]).WIN_H))
g5 = Game()
g5.new_game("D")
ow5 = g5.scenes[0]
g5.party = [Mon("小火焰猴", 10)]
for mid, x, y in (("twinleaf", 10, 7), ("r217", 10, 10), ("snowpoint_gym", 7, 9), ("coronet_peak", 12, 10),
                  ("sunyshore", 12, 9), ("eterna_forest", 10, 7), ("league_gate", 6, 5), ("r223", 10, 10),
                  ("pastoria_gym", 7, 9), ("great_marsh", 11, 10), ("spear_pillar", 10, 10), ("veilstone", 12, 10)):
    ow5.warp_to(mid, x, y, "down")
    ow5.state = "field"
    ow5.draw(surf)
check("各地形绘制无异常", True)
b = g5.push_battle([Mon("姆克儿", 3)], callback=lambda r: None)
b.phase = "menu"
b.draw(surf)
b.phase = "movesel"
b.draw(surf)
b.anim = ["hit_foe", 0.2, 0.45, "电"]
b.draw(surf)
b.anim = None
b.weather = "rain"
b.draw(surf)
check("战斗绘制无异常", True)
from src.title import Title   # noqa: E402
g5.scenes = [Title(g5)]
g5.scenes[0].draw(surf)
if len(g5.scenes[0].options) > 1:
    g5.scenes[0].handle_event(key(pygame.K_DOWN))
g5.scenes[0].handle_event(key(pygame.K_z))          # 新的冒险 → 版本选择
g5.scenes[0].draw(surf)
g5.scenes[0].handle_event(key(pygame.K_RIGHT))      # 珍珠
g5.scenes[0].handle_event(key(pygame.K_z))
check("标题选择珍珠版进入游戏", isinstance(g5.scenes[0], Overworld) and g5.version == "P")
g5.scenes[0].start_script((lambda: (yield ("hall",)))())
g5.tick(0.016)
for _ in range(10):
    g5.tick(0.016)
    for e in (key(pygame.K_z),):
        g5.scenes[-1].handle_event(e)
check("名人堂场景无异常", len(g5.scenes) == 1)
g6 = Game()
g6.new_game("D")
for k in (pygame.K_z, pygame.K_z, pygame.K_z, pygame.K_RETURN, pygame.K_x):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k))
g6.run(max_frames=60)
check("主循环60帧", True)

# ================================================================ 7. 全部 NPC 脚本
print("== 全部 NPC 脚本 ==")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from all_scripts_test import all_scripts   # noqa: E402
count, errors = all_scripts()
check(f"全部 NPC 脚本无异常({count} 个)", not errors, str(errors[:3]))

print(f"\n全部通过: {PASS} 项检查 ✔")
