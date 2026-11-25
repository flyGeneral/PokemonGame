"""遍历全部 NPC 脚本(通过大地图的真实派发路径),确认不会崩溃。

运行: python3 tests/all_scripts_test.py   (smoke_test 末尾也会调用)
"""
import sys, os
sys.path.insert(0, "."); os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
from src import world
from src.game import Game
from src.mon import Mon
GOD = [Mon("烈焰猴", 90, moves=["喷射火焰", "近身战", "雷电拳", "地震"]), Mon("帝王拿波", 90, moves=["冲浪", "冰冻光束", "啄钻", "大地之力"])]
def key(k): return pygame.event.Event(pygame.KEYDOWN, key=k)
def run(ow):
    guard = 0
    while guard < 6000:
        guard += 1
        if len(ow.game.scenes) > 1:
            sc = ow.game.scenes[-1]
            if hasattr(sc, "drive_for_test"):
                sc.auto = True; sc.drive_for_test([])
            elif hasattr(sc, "handle_event"):
                sc.handle_event(key(pygame.K_z))
            ow.game.tick(0.016); continue
        if ow.state == "dialog":
            ow.handle_event(key(pygame.K_z))
            if ow.textbox.choices and ow.textbox.wait_key:
                ow.handle_event(key(pygame.K_z))
            continue
        if ow.state in ("shop", "fly", "starter", "party", "bag", "learn", "badges"):
            if ow.state == "fly":
                ow.fly_screen.done = True; ow.fly_screen.result = None; ow.handle_event(key(pygame.K_x)); continue
            if ow.state == "starter":
                ow.starter.key(key(pygame.K_z), ow.game.assets["icons"]); ow.starter.key(key(pygame.K_z), ow.game.assets["icons"]); ow._starter_done(); continue
            ow.state = "field"; continue
        if ow.fade_t >= 0:
            ow.update(0.1); continue
        if ow.script is None:
            return
def all_scripts():
    g = Game(); g.new_game("D"); ow = g.scenes[0]
    while ow.state == "dialog": ow.handle_event(key(pygame.K_z))
    errors, count = [], 0
    for mid, m in world.MAPS.items():
        for n in m.npcs:
            g.flags = {"starter": True, "starter_name": "草苗龟"}
            g.party = [Mon("烈焰猴", 90, moves=["喷射火焰", "近身战", "雷电拳", "地震"])]
            g.bag = {"全复药": 30, "大师球": 5}
            g.money = 5000
            ow.warp_to(mid, max(1, n["x"] - 1), n["y"], "right")
            ow.state = "field"; ow.script = None; ow.textbox.hide(); ow.safari = None
            g.scenes = [ow]
            try:
                ow._run_npc(n); run(ow); count += 1
            except Exception as e:
                import traceback
                errors.append((mid, n.get("name"), n["script"], repr(e)))
    return count, errors
if __name__ == "__main__":
    count, errors = all_scripts()
    print("scripts ok:", count, "errors:", len(errors))
    for e in errors[:20]: print("  ERR", e)
