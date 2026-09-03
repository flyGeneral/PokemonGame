"""从 Essentials 镜像(rh-hideout-chinese/pokemon-engine, GitHub)导入官方风格素材。

- 人物行走图 → assets/chars/(RPG Maker XP 4x4 格式切片,1.5x 缩放进游戏)
- 图块集(Outside / Interior general / Gyms interior)→ 按 32px 块坐标切片替换内置图块
- 坐标表是对照原砖人工目视挑选的;素材版权归任天堂/Game Freak,仅限个人本地使用,
  assets/ 已加入 .gitignore。

用法: python3 tools/import_essentials_assets.py
(默认从 /tmp/ess_src 读取缓存;不存在则自动下载)
"""
import json
import os
import shutil
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "assets", "src")
TMP = "/tmp/ess_src"
BASE = ("https://raw.githubusercontent.com/rh-hideout-chinese/pokemon-engine/"
        "master/Graphics")

SHEETS = {
    "Outside": "Tilesets/Outside.png",
    "InteriorGeneral": "Tilesets/Interior%20general.png",
    "Gyms": "Tilesets/Gyms%20interior.png",
    "Doors": "Characters/doors1.png",
}

CHARS = {
    "player":   ["trainer_POKEMONTRAINER_Red.png", "Red.png"],
    "prof":     ["trainer_PROFESSOR.png", "PROFESSOR.png"],
    "leader":   ["trainer_LEADER_Brock.png", "Brock.png"],
    "youth":    ["trainer_YOUNGSTER.png", "Youngster.png"],
    "mom":      ["trainer_AROMALADY.png", "AromaLady.png"],
    "lady":     ["trainer_AROMALADY.png", "AromaLady.png"],
    "villager": ["NPC 05.png", "NPC05.png"],
}

# char → (sheet, 32px块col, 32px块row)。人工对照原砖目视挑选。
TILES = {
    ".":  ("Outside", 1, 1),      # 草地
    ",":  ("Outside", 7, 0),      # 高草
    "p":  ("Outside", 0, 16),     # 土路
    "n":  ("Outside", 0, 16),
    "f":  ("Outside", 0, 102),    # 花丛
    "w0": ("Outside", 6, 90),     # 水面(两帧微动)
    "w1": ("Outside", 6, 89),
    "T":  ("Outside", 1, 56),     # 树冠(成片即森林)
    "F":  ("Outside", 0, 74),     # 灌木篱
    "S":  None,                   # 告示牌保留内置
    "r":  ("Outside", 1, 180),    # 蓝屋顶脊
    "R":  ("Outside", 1, 181),    # 蓝瓦
    "q":  ("Outside", 1, 190),    # 橙屋顶脊(研究所)
    "Q":  ("Outside", 1, 191),    # 橙瓦
    "B":  ("Outside", 3, 192),    # 墙
    "V":  ("Outside", 0, 192),    # 窗
    "D":  ("Outside", 2, 182),    # 门
    "#":  ("InteriorGeneral", 1, 42),   # 室内墙纸
    "o":  ("InteriorGeneral", 1, 28),   # 室内地板
    "m":  ("InteriorGeneral", 2, 86),   # 地垫
    "b":  ("InteriorGeneral", 1, 107),  # 床
    "s":  ("InteriorGeneral", 0, 9),    # 书架
    "t":  ("InteriorGeneral", 0, 1),    # 桌子
    "g":  ("Gyms", 0, 35),              # 道馆地板
    "G":  ("Gyms", 0, 33),              # 道馆墙
}


def ensure_src():
    os.makedirs(SRC, exist_ok=True)
    for name, path in SHEETS.items():
        dest = os.path.join(SRC, f"{name}.png")
        if not os.path.exists(dest):
            for cand in (os.path.join(TMP, f"{name}.png"),):
                if os.path.exists(cand):
                    shutil.copyfile(cand, dest)
                    break
            else:
                url = f"{BASE}/{path}"
                print("下载", url)
                with urllib.request.urlopen(url, timeout=120) as r, open(dest, "wb") as f:
                    f.write(r.read())
    return {n: os.path.join(SRC, f"{n}.png") for n in SHEETS}


def import_chars():
    """切片 XP 4x4 行走图 → assets/chars/<pal>.png(整表)+ chars.json 元数据。"""
    os.makedirs(os.path.join(ROOT, "assets", "chars"), exist_ok=True)
    meta_path = os.path.join(ROOT, "assets", "chars", "chars.json")
    meta = {}
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)
    for pal, names in CHARS.items():
        dest = os.path.join(ROOT, "assets", "chars", f"{pal}.png")
        if os.path.exists(dest):                     # 已导入过
            meta[pal] = {"file": f"{pal}.png", "cols": 4, "rows": 4}
            continue
        src = next((os.path.join(TMP, n) for n in names if os.path.exists(os.path.join(TMP, n))), None)
        if src is None:                              # 缓存没有 → 从镜像下载
            url = f"{BASE}/Characters/{urllib.parse.quote(names[0])}"
            try:
                print("下载", url)
                with urllib.request.urlopen(url, timeout=90) as r, open(dest, "wb") as fo:
                    fo.write(r.read())
            except Exception as e:
                print("下载失败", names[0], e)
                continue
        else:
            shutil.copyfile(src, dest)
        meta[pal] = {"file": f"{pal}.png", "cols": 4, "rows": 4}
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=1)
    print("人物切片:", list(meta))


def main():
    ensure_src()
    import_chars()
    print("完成。图块映射写在 art.TILE_FROM_SHEET(与 TILES 同步),运行时自动替换。")


if __name__ == "__main__":
    sys.exit(main())
