"""批量下载全图鉴官方贴图(第四世代钻石珍珠画风)。

下载 assets/mons/dexNNN.png(正面)、back_dexNNN.png(背面)、icon_dexNNN.png(图标)。
仅个人本地使用,已 gitignore。断点续传:已存在的文件自动跳过。

用法: python3 tools/fetch_all_sprites.py [--backs]
"""
import os
import shutil
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "mons")

HOSTS = [
    "https://cdn.jsdelivr.net/gh/PokeAPI/sprites@master/sprites/pokemon/versions/generation-iv/diamond-pearl/",
    "https://fastly.jsdelivr.net/gh/PokeAPI/sprites@master/sprites/pokemon/versions/generation-iv/diamond-pearl/",
    "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/versions/generation-iv/diamond-pearl/",
]


def dex_ids():
    sys.path.insert(0, ROOT)
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    from src import data
    ids = set()
    for sp in data.SPECIES.values():
        if sp["art"].startswith("dex"):
            ids.add(int(sp["art"][3:]))
    return sorted(ids)


def fetch(url, dest):
    for h in HOSTS:
        try:
            with urllib.request.urlopen(h + url, timeout=25) as r:
                data = r.read()
            if data[:4] == b"\x89PNG":
                with open(dest, "wb") as f:
                    f.write(data)
                return True
        except Exception:
            pass
        time.sleep(0.4)
    return False


def main():
    want_backs = "--backs" in sys.argv
    ids = dex_ids()
    todo = []
    for d in ids:
        name = f"dex{d:03d}"
        if not os.path.exists(os.path.join(OUT, name + ".png")):
            todo.append((d, name + ".png", ""))
        if not os.path.exists(os.path.join(OUT, "icon_" + name + ".png")):
            todo.append((d, "icon_" + name + ".png", None))
        if want_backs and not os.path.exists(os.path.join(OUT, "back_" + name + ".png")):
            todo.append((d, "back_" + name + ".png", "back/"))
    print(f"需下载 {len(todo)} 个文件(共 {len(ids)} 只精灵)")
    fail = []
    for i, (d, fname, sub) in enumerate(todo):
        dest = os.path.join(OUT, fname)
        if sub is None:      # 图标 = 正面图副本,正面缺失时跳过(下轮再补)
            front = os.path.join(OUT, f"dex{d:03d}.png")
            if os.path.exists(front):
                shutil.copyfile(front, dest)
                print(f"[{i+1}/{len(todo)}] {fname}(复制)")
            continue
        if fetch(f"{sub}{d}.png", dest):
            print(f"[{i+1}/{len(todo)}] {fname}")
        else:
            fail.append(fname)
            print(f"失败 {fname}", file=sys.stderr)
        time.sleep(0.3)
    print(f"\n完成。失败 {len(fail)} 个", fail[:20] if fail else "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
