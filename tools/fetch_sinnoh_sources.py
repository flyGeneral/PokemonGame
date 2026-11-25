"""抓取 gen_sinnoh_data.py 需要的全部原始数据到 /tmp/pkdp(仅重建数据时需要网络)。

来源:
  1. pret/pokediamond 稀疏克隆          → /tmp/pkdp/pd   (精灵/招式/进化/训练家/道具/遭遇表 JSON+NARC)
  2. Xzonn/PokemonChineseTranslationRevise 中文文本 → /tmp/pkdp/xz_text (DP/zh_Hans 576 个 json)
  3. PokeAPI CSV(官方简中名、体重)        → /tmp/pkdp/*.csv
  4. PokeAPI location-area(神奥全部区域遭遇,用于把二进制遭遇表对齐到道路) → /tmp/pkdp/sinnoh_encounters.json

用法: python3 tools/fetch_sinnoh_sources.py
"""
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

DST = "/tmp/pkdp"
PD = os.path.join(DST, "pd")
XZ = os.path.join(DST, "xz_text")
PD_SPARSE = ["files/poketool", "files/fielddata/encountdata", "files/itemtool/itemdata", "include", "arm9/src"]
RAW = "https://raw.githubusercontent.com/"
API = "https://api.github.com/repos/"
CSVS = ["pokemon.csv", "move_names.csv", "pokemon_species_names.csv", "item_names.csv", "type_names.csv"]
XZ_REPO = "Xzonn/PokemonChineseTranslationRevise"
UA = {"User-Agent": "sinnoh-data-fetch/1.0"}


def get(url, retries=6, timeout=60):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:      # noqa: BLE001
            last = e
            time.sleep(2 + 2 * i)
    raise RuntimeError(f"{url}: {last}")


def fetch_json(url):
    return json.loads(get(url))


def clone_pokediamond():
    if os.path.exists(os.path.join(PD, "files/poketool/waza/waza_tbl.json")):
        print("pokediamond 已存在,跳过")
        return
    os.makedirs(DST, exist_ok=True)
    subprocess.check_call(["git", "clone", "--filter=blob:none", "--no-checkout", "--depth", "1",
                           "https://github.com/pret/pokediamond.git", PD])
    subprocess.check_call(["git", "-C", PD, "sparse-checkout", "init", "--cone"])
    subprocess.check_call(["git", "-C", PD, "sparse-checkout", "set"] + PD_SPARSE)
    subprocess.check_call(["git", "-C", PD, "checkout"])


def fetch_xzonn():
    os.makedirs(XZ, exist_ok=True)
    listing = fetch_json(API + XZ_REPO + "/contents/texts/DP/zh_Hans")
    entries = [e for e in listing if e["type"] == "file" and e["name"].endswith(".json")]

    def one(e):
        dest = os.path.join(XZ, e["name"])
        if os.path.exists(dest) and os.path.getsize(dest) == e["size"]:
            return True
        for host in (RAW + XZ_REPO + "/master/texts/DP/zh_Hans/",
                     "https://fastly.jsdelivr.net/gh/" + XZ_REPO + "@master/texts/DP/zh_Hans/"):
            try:
                data = get(host + e["name"], retries=2, timeout=30)
                if len(data) == e["size"]:
                    open(dest, "wb").write(data)
                    return True
            except Exception:      # noqa: BLE001
                continue
        return False

    with ThreadPoolExecutor(12) as ex:
        res = list(ex.map(one, entries))
    print(f"Xzonn 中文文本 {sum(res)}/{len(entries)}")
    if sum(res) != len(entries):
        raise SystemExit("部分文本下载失败,请重试")


def fetch_csvs():
    for name in CSVS:
        dest = os.path.join(DST, name)
        if os.path.exists(dest) and os.path.getsize(dest) > 100:
            continue
        open(dest, "wb").write(get(RAW + "PokeAPI/pokeapi/master/data/v2/csv/" + name))
        print("csv", name)


def fetch_pokeapi_encounters():
    out = os.path.join(DST, "sinnoh_encounters.json")
    if os.path.exists(out):
        return
    region = fetch_json("https://pokeapi.co/api/v2/region/4/")
    areas = []
    for loc in region["locations"]:
        lid = loc["url"].rstrip("/").split("/")[-1]
        d = fetch_json(f"https://pokeapi.co/api/v2/location/{lid}/")
        for a in d["areas"]:
            areas.append({"location": loc["name"], "area": a["name"],
                          "id": a["url"].rstrip("/").split("/")[-1]})
        time.sleep(0.1)
    json.dump(areas, open(os.path.join(DST, "sinnoh_areas.json"), "w"))
    enc = {}
    for i, a in enumerate(areas):
        d = fetch_json(f"https://pokeapi.co/api/v2/location-area/{a['id']}/")
        lst = []
        for e in d.get("pokemon_encounters", []):
            for v in e["version_details"]:
                for det in v["encounter_details"]:
                    lst.append({"species": e["pokemon"]["name"], "species_url": e["pokemon"]["url"],
                                "version": v["version"]["name"], "method": det["method"]["name"],
                                "min": det["min_level"], "max": det["max_level"], "chance": det["chance"]})
        enc[a["id"]] = {"location": a["location"], "area": a["area"], "encounters": lst}
        if i % 20 == 0:
            print("encounters", i, "/", len(areas))
        time.sleep(0.15)
    json.dump(enc, open(out, "w"), ensure_ascii=False)
    print("encounters", len(enc))


if __name__ == "__main__":
    clone_pokediamond()
    fetch_csvs()
    fetch_xzonn()
    fetch_pokeapi_encounters()
    print("完成:", DST)
    sys.exit(0)
