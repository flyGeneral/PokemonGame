"""渲染关键场景截图 → /tmp/screens/ 用于人工检查。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
from src.game import Game
from src.battle import Battle
from src.mon import Mon
from src.title import Title

os.makedirs("/tmp/screens", exist_ok=True)
g = Game()
pygame.display.set_mode((960, 624))  # 确保真实 screen
g.screen = pygame.display.get_surface()


def snap(name):
    pygame.image.save(g.screen, f"/tmp/screens/{name}.png")
    print("saved", name)


# 1. 标题
g.scenes = [Title(g)]
g.tick(1 / 60)
snap("1_title")

# 2. 小镇 + 对话
g.new_game()
g.scenes[0].draw(g.screen)
g.tick(1 / 60)
snap("2_intro_dialog")

# 3. 小镇(与玩家反馈相同机位:路口处)
ow = g.scenes[0]
for _ in range(6):
    ow.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))
ow.warp_to("town", 10, 4, "down")
ow.state = "field"
ow.tick_t = 0
ow.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
for _ in range(4):
    g.tick(1 / 60)
ow.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_DOWN))
g.tick(1 / 60)
snap("3_town")

# 4. 初始精灵选择界面
g.party = []
ow.warp_to("lab", 5, 5, "up")
ow.state = "dialog"
from src.worldmap import SCRIPTS
ow.start_script(SCRIPTS["prof"](g))
ow.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))  # 完成打字
ow.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))  # 前进 → 打开选择
if ow.state == "starter":
    g.tick(1 / 60)
    snap("4_starter")
    ow.starter.done = False
    ow.starter.result = None
    ow.state = "field"   # 不真的选择,方便后续截图

# 5. 战斗画面(菜单)
g.party = [Mon("小火猴", 12)]
g.bag = {"精灵球": 5, "伤药": 2}
b = g.push_battle([Mon("小猫怪", 5)], callback=lambda r: None, ai_level=2)
for _ in range(50):
    b.update(1 / 30)
b.phase = "menu"
b.draw(g.screen)
snap("5_battle_menu")

# 6. 战斗招式选择
b.phase = "movesel"
b.draw(g.screen)
snap("6_battle_moves")

# 7. 自宅内部 + 8. 道馆 + 9. 道路
g.scenes = [ow]   # 弹出战斗层
ow.warp_to("house", 4, 4, "down")
ow.state = "field"
g.tick(1 / 60)
snap("7_house")
ow.warp_to("gym", 6, 5, "up")
g.party = [Mon("猛火猴", 20)]
g.tick(1 / 60)
snap("8_gym")
ow.warp_to("route", 9, 9, "up")
g.tick(1 / 60)
snap("9_route")
# 10. 小镇(三栋建筑) 11. 商店内部 12. 商店 UI
g.money = 3000
ow.warp_to("town", 10, 12, "up")
g.tick(1 / 60)
snap("10_town3")
ow.warp_to("mart", 5, 6, "up")
g.tick(1 / 60)
snap("11_mart")
ow.px, ow.py = 4, 5
ow.dir = "up"
ow._interact()
g.tick(1 / 60)
snap("12_shop")
print("done")
