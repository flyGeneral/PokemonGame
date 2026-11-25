"""等级曲线模拟:用真实战斗引擎跑一遍主线训练家 + 若干野生精灵,输出各道馆前的队伍等级。

用法: python3 tools/sim_progression.py [初始精灵] [每条道路野生对战数]
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["SDL_VIDEODRIVER"] = "dummy"

from src import data   # noqa: E402
from src.game import Game   # noqa: E402
from src.mon import Mon   # noqa: E402

# 主线顺序:(阶段名, 道路遭遇区域, 野生对数, 训练家 id 列表, 道馆训练家 key)
STAGES = [
    ("出发→黑金", ["route_201", "route_202", "route_203"], 6, [9, 3, 11, 13, 12, 245, 342, 345, 355, 247], None),
    ("黑金道馆", ["oreburgh_gate_1f", "oreburgh_mine_1f"], 6, [195, 18], 246),
    ("→花苑/发电厂", ["route_204_south", "ravaged_path", "route_204_north", "route_205_south"], 6,
     [4, 7, 14, 204, 21, 244, 196, 297, 298, 295], None),
    ("→百代森林/百代", ["route_205_east", "eterna_forest"], 8, [17, 377, 456, 20, 205, 206, 259, 471], None),
    ("百代道馆", [], 0, [], 315),
    ("→天冠山→家缘", ["route_211_west", "mt_coronet_1f_route_211", "mt_coronet_1f_route_207", "route_208"], 8,
     [326, 451, 36, 78, 443, 74, 37, 38, 44, 33, 83], None),
    ("→随意镇→帷幕", ["route_209", "lost_tower_1f", "route_210_south", "route_210_west", "route_210_north",
                  "route_215"], 10,
     [34, 35, 41, 76, 49, 82, 45, 260, 348, 379, 474, 113, 120, 273, 278, 287, 94, 96, 119,
      66, 67, 72, 80, 266, 330], None),
    ("帷幕道馆", [], 0, [], 317),
    ("→213/湿原", ["route_213", "route_212_north", "route_212_east"], 8,
     [105, 106, 43, 328, 339, 84, 85, 531, 92, 93, 111, 715], None),
    ("湿原道馆", [], 0, [], 316),
    ("劲敌+家缘道馆", ["route_212_north", "route_209"], 4, [477], 318),
    ("→神和镇", ["route_210_west", "route_211_east", "mt_coronet_1f_route_216"], 8, [388, 283, 634, 403], None),
    ("→218→水脉", ["mt_coronet_1f_route_211", "route_218"], 8, [664, 669, 153, 392], None),
    ("水脉道馆", [], 0, [], 250),
    ("→216/217→雪峰", ["route_210_north", "route_216", "route_217"], 12,
     [136, 144, 135, 132, 139, 140, 141, 143, 145], None),
    ("雪峰道馆", [], 0, [], 319),
    ("→222→滨海", ["route_222"], 8, [636, 673, 234, 677], None),
    ("滨海道馆", [], 0, [], 320),
    ("→冠军之路", ["sea_route_223", "route_224", "victory_road_1f", "victory_road_2f"], 12,
     [191, 184, 597, 602, 305, 564, 574, 397, 225, 231, 444, 226, 227, 228, 481], None),
    ("四天王·冠军", [], 0, [], 267),
]


def fight(game, enemies, key=None):
    """自动战斗:玩家按引擎评分选最优招式(相当于会玩的人类),输了也无惩罚地继续。"""
    from src.battle import Battle
    b = Battle(game, enemies, trainer_key=key, ai_level=2, callback=lambda r: None)
    b.auto = True
    guard = 0
    while not b.done and guard < 3000:
        guard += 1
        b.update(0.05)
        if b.phase == "menu":
            b._advance("fight")
        elif b.phase == "movesel":
            best = max(range(len(b.ally.moves)), key=lambda i: b._score_move(b.ally.moves[i]) + i * 1e-3)
            b._advance(("move", best))
        elif b.phase == "party":
            b._advance(next((i for i, m in enumerate(game.party) if m.hp > 0), None))
        elif b.phase == "learnmove":
            b._advance(0)
        elif b.phase == "bag":
            b._advance(None)
    r = b.result
    b.resolve_pending_evolution()
    game.heal_party()
    return r


def run(starter, wild_n, seed=0):
    random.seed(seed)
    g = Game()
    g.party = [Mon(starter, 5)]
    g.bag = {}
    rows = []
    def wild(table):
        total = sum(r[-1] for r in table)
        rr = random.random() * total
        row = table[-1]
        for row in table:
            rr -= row[-1]
            if rr <= 0:
                break
        fight(g, [Mon(data.SPECIES_BY_ID[row[1]], row[0])])

    def grind(table, times):
        for _ in range(times):
            wild(table)

    last_table = data.ENCOUNTERS["route_201"]["D"]["grass"]
    for name, areas, n, trainers, gym in STAGES:
        for area in areas:
            enc = data.ENCOUNTERS.get(area)
            if not enc or not enc["D"]["grass"]:
                continue
            last_table = enc["D"]["grass"]
            grind(last_table, n)
        for key in trainers + ([gym] if gym else []):
            for attempt in range(40):           # 打输就像玩家一样刷野生精灵练级后再来
                if fight(g, None, key) == "win":
                    break
                grind(last_table, 4)
        top = max(p[1] for p in data.TRAINERS[gym]["party"]) if gym else None
        rows.append((name, g.party[0].species, g.party[0].level, top))
    return rows


def exp_curve(wild_n=15, team=3):
    """解析估算:每个阶段可获得的全部训练家经验 + 野生经验,平均分给 team 只精灵。"""
    growth = "medium_slow"

    def level_for(exp):
        lv = 1
        while lv < 100 and exp >= data.exp_for_level(lv + 1, growth):
            lv += 1
        return lv

    acc = data.exp_for_level(5, growth)
    print(f"经验估算:每区域 {wild_n} 场野生,队伍 {team} 只平分经验(无学习装置)")
    print(f"{'阶段':<14}{'队伍等级':>10}{'馆主最高等级':>14}{'评价':>8}")
    for name, areas, n, trainers, gym in STAGES:
        exp = 0
        for key in trainers:
            for sp, lv, mv, held in data.TRAINERS[key]["party"]:
                exp += data.SPECIES[sp]["base_exp"] * lv // 7 * 1.5
        for area in areas:
            enc = data.ENCOUNTERS.get(area)
            if not enc or not enc["D"]["grass"]:
                continue
            table = enc["D"]["grass"]
            avg = sum(r[0] * r[-1] for r in table) / sum(r[-1] for r in table)
            sp = data.SPECIES_BY_ID[table[0][1]]
            exp += wild_n * data.SPECIES[sp]["base_exp"] * avg / 7
        acc += exp / team
        top = max(p[1] for p in data.TRAINERS[gym]["party"]) if gym else None
        lv = level_for(acc)
        verdict = ""
        if top:
            verdict = "偏低" if lv < top - 4 else "偏高" if lv > top + 6 else "合适"
        print(f"{name:<14}{lv:>10}{(top or ''):>14}{verdict:>8}")


if __name__ == "__main__":
    if "--exp" in sys.argv:
        exp_curve(int(sys.argv[sys.argv.index("--exp") + 1]) if len(sys.argv) > sys.argv.index("--exp") + 1 and sys.argv[sys.argv.index("--exp") + 1].isdigit() else 15)
        sys.exit(0)
    starter = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in data.SPECIES else "草苗龟"
    wild_n = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    print(f"初始精灵 {starter},每区域野生对战 {wild_n} 场,自动选招,打输则刷级重来(单只精灵,无学习装置)")
    print(f"{'阶段':<14}{'队伍':<8}{'等级':>6}{'馆主/天王最高等级':>16}")
    for name, sp, lv, top in run(starter, wild_n):
        print(f"{name:<14}{sp:<8}{lv:>6}{(top or ''):>16}")
