"""渲染关键场景截图 → /tmp/screens/ 用于人工检查。

用法: python3 tools/screenshot_demo.py
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame   # noqa: E402

from src.game import Game   # noqa: E402
from src.mon import Mon   # noqa: E402
from src.title import Title   # noqa: E402
from src import data, world   # noqa: E402

os.makedirs("/tmp/screens", exist_ok=True)
g = Game()
pygame.display.set_mode((960, 624))
g.screen = pygame.display.get_surface()
KEY = lambda k: pygame.event.Event(pygame.KEYDOWN, key=k)   # noqa: E731


def snap(name):
    pygame.image.save(g.screen, f"/tmp/screens/{name}.png")
    print("saved", name)


def field(ow, mid, x, y, facing="down"):
    ow.warp_to(mid, x, y, facing)
    ow.state = "field"
    ow.script = None
    ow.textbox.hide()
    g.tick(1 / 60)


# 1. 标题 + 版本选择
g.scenes = [Title(g)]
g.tick(1 / 60)
snap("01_title")
g.scenes[0].handle_event(KEY(pygame.K_z))
g.tick(1 / 60)
snap("02_version")

# 2. 开场 + 研究所 + 初始精灵
g.new_game("D")
ow = g.scenes[0]
g.tick(1 / 60)
snap("03_intro")
while ow.state == "dialog":
    ow.handle_event(KEY(pygame.K_z))
g.flags["starter"] = True
g.flags["starter_name"] = "小火焰猴"
g.party = [Mon("小火焰猴", 12, moves=["抓", "瞪眼", "火花", "火焰轮"]), Mon("姆克儿", 10), Mon("大牙狸", 8)]
field(ow, "sandgem_lab", 4, 4, "up")
ow._interact()
ow.handle_event(KEY(pygame.K_z))
ow.handle_event(KEY(pygame.K_z))
if ow.state == "starter":
    g.tick(1 / 60)
    snap("04_starter")
    ow.starter.done = False
    ow.starter.result = None
    ow.starter.key(KEY(pygame.K_x), g.assets["icons"])
    ow.state = "field"

# 3. 各地地形
for name, mid, x, y in (("05_twinleaf", "twinleaf", 10, 7), ("06_jubilife", "jubilife", 12, 10),
                        ("07_route201", "r201", 10, 12), ("08_oreburgh_gym", "oreburgh_gym", 7, 9),
                        ("09_eterna_forest", "eterna_forest", 10, 7), ("10_coronet", "coronet_west", 10, 8),
                        ("11_r217_snow", "r217", 10, 12), ("12_snowpoint_gym", "snowpoint_gym", 7, 9),
                        ("13_veilstone", "veilstone", 12, 10), ("14_pastoria_marsh", "great_marsh", 11, 12),
                        ("15_sunyshore", "sunyshore", 12, 9), ("16_victory_road", "victory_road_2", 10, 8),
                        ("17_spear_pillar", "spear_pillar", 10, 10), ("18_league", "league", 9, 7),
                        ("19_center", "jubilife_center", 5, 5), ("20_mart", "jubilife_mart", 5, 5),
                        ("21_lake_surf", "lake_acuity", 15, 7), ("22_r223_water", "r223", 10, 10)):
    field(ow, mid, x, y)
    if name.startswith("21"):
        ow.surfing = True
    g.tick(1 / 60)
    snap(name)
    ow.surfing = False

# 4. 菜单 / 徽章 / 背包
field(ow, "veilstone", 12, 10)
ow._open_menu()
g.tick(1 / 60)
snap("23_menu")
ow.state = "field"
g.flags[data.BADGES[0][0]] = True
g.flags[data.BADGES[1][0]] = True
g.bag = {"精灵球": 10, "高级球": 5, "伤药": 3, data.item_by_tm(76): 1, data.item_by_tm(3, hm=True): 1, "学习装置": 1}
ow.bag_screen = __import__("src.ui", fromlist=["x"]).BagScreen(g, "menu")
ow.state = "bag"
g.tick(1 / 60)
snap("24_bag")

# 5. 战斗
random.seed(1)
g.party = [Mon("烈焰猴", 46, moves=["喷射火焰", "火焰轮", "音速拳", "瞪眼"])]
b = g.push_battle(None, trainer_key=320, ai_level=3, callback=lambda r: None)
for _ in range(60):
    b.update(1 / 30)
b.phase = "menu"
b.draw(g.screen)
snap("25_battle_volkner")
b.phase = "movesel"
b.draw(g.screen)
snap("26_battle_moves")
b.phase = "anim"
b.anim = ["hit_foe", 0.25, 0.45, "电"]
b.draw(g.screen)
snap("27_battle_fx")

# 6. 道馆拉杆 / 冰面 / 箭头
field(ow, "eterna_gym", 14, 5, "up")
ow._interact()
ow.handle_event(KEY(pygame.K_z))
ow.handle_event(KEY(pygame.K_z))
ow.handle_event(KEY(pygame.K_z))
g.tick(1 / 60)
snap("28_lever")
field(ow, "snowpoint_gym", 7, 7)
snap("29_ice")
print("done")
