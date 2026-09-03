"""下载官方精灵球道具图标到 assets/balls/(可选,网络可用时运行)。

来源 PokeAPI/sprites;assets/balls/ 已 gitignore,仅个人本地使用。
游戏在文件存在时自动启用,否则使用内置程序化平滑球。

用法: python3 tools/fetch_balls.py
"""
import os
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "balls")

BALLS = ["poke-ball.png", "great-ball.png", "ultra-ball.png", "master-ball.png"]
HOSTS = [
    "https://cdn.jsdelivr.net/gh/PokeAPI/sprites@master/sprites/items/",
    "https://fastly.jsdelivr.net/gh/PokeAPI/sprites@master/sprites/items/",
    "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/",
]


def main():
    os.makedirs(OUT, exist_ok=True)
    todo = [b for b in BALLS if not os.path.exists(os.path.join(OUT, b))]
    for rnd in range(10):
        for b in list(todo):
            for h in HOSTS:
                try:
                    with urllib.request.urlopen(h + b, timeout=25) as r:
                        data = r.read()
                    if data[:4] == b"\x89PNG":
                        with open(os.path.join(OUT, b), "wb") as f:
                            f.write(data)
                        print("获取", b)
                        todo.remove(b)
                        break
                except Exception:
                    time.sleep(1)
        if not todo:
            break
        time.sleep(5)
    print("完成:", sorted(set(BALLS) - set(todo)), "未获取:", todo or "无")
    return 0


if __name__ == "__main__":
    sys.exit(main())
