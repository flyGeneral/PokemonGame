"""从 PokeAPI/sprites 公开仓库下载官方第四世代(钻石/珍珠)风格精灵图。

仅用于个人本地学习试玩,版权归 Nintendo/Creatures/Game Freak,
assets/mons/ 已加入 .gitignore,不会被提交或分发。

用法: python3 tools/fetch_official_sprites.py
"""
import os
import shutil
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "mons")

# art_id -> 全国图鉴编号(第四世代珍珠/钻石画风)
DEX = {
    "sprout": 387,   # 草苗龟 Turtwig
    "vine": 388,     # 树苗龟 Grotle
    "foxf": 390,     # 小火猴 Chimchar
    "firef": 391,    # 猛火猴 Monferno
    "turtle": 393,   # 波加曼 Piplup
    "wave": 394,     # 波皇子 Prinplup
    "bird": 396,     # 姆克儿 Starly
    "rat": 399,      # 大牙狸 Bidoof
    "pika": 25,      # 皮卡丘 Pikachu
    "rock": 74,      # 小拳石 Geodude
    "boulder": 75,   # 隆隆石 Graveler
}

HOSTS = [
    "https://raw.githubusercontent.com/PokeAPI/sprites/master/"
    "sprites/pokemon/versions/generation-iv/diamond-pearl/{sub}{dex}.png",
    "https://cdn.jsdelivr.net/gh/PokeAPI/sprites@master/"
    "sprites/pokemon/versions/generation-iv/diamond-pearl/{sub}{dex}.png",
    "https://fastly.jsdelivr.net/gh/PokeAPI/sprites@master/"
    "sprites/pokemon/versions/generation-iv/diamond-pearl/{sub}{dex}.png",
]


def fetch(sub, dex, dest):
    for tmpl in HOSTS:
        url = tmpl.format(sub=sub, dex=dex)
        try:
            with urllib.request.urlopen(url, timeout=25) as r:
                data = r.read()
            if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) > 200:
                with open(dest, "wb") as f:
                    f.write(data)
                return len(data), url.split("/")[2]
        except Exception:
            continue
    return 0, None


def main():
    os.makedirs(OUT, exist_ok=True)
    ok, fail = 0, []
    for art_id, dex in DEX.items():
        got_front = got_back = 0
        p_front = os.path.join(OUT, f"{art_id}.png")
        p_icon = os.path.join(OUT, f"icon_{art_id}.png")
        p_back = os.path.join(OUT, f"back_{art_id}.png")
        got_front, host = fetch("", dex, p_front)
        if got_front:
            got_back, _ = fetch("back/", dex, p_back)
            shutil.copyfile(p_front, p_icon)
            ok += 1
            print(f"  ✔ {art_id:8s} #{dex:<4d} front={got_front}B back={got_back or '-'}B  ({host})")
        else:
            fail.append(art_id)
            print(f"  ✘ {art_id:8s} #{dex} 下载失败,将保留内置原创像素画")
    print(f"\n完成: {ok}/{len(DEX)} 只。失败: {fail or '无'}")
    return 0 if not fail else 1


if __name__ == "__main__":
    sys.exit(main())
