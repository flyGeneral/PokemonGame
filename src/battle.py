"""战斗场景:第四世代式回合制,协程驱动流程。

yield 协议: ("msg",t) ("anim",kind,dur,extra) ("menu",) ("movesel",)
            ("bag",) ("party",mode)
"""
import math
import random

import pygame

from . import settings as S
from . import data
from .mon import stage_multiplier
from .ui import (TextBox, PartyScreen, BagScreen, panel, draw_text, hp_bar, exp_bar,
                 down_arrow, cursor_arrow)

MENU_OPTS = ("战斗", "背包", "精灵", "逃跑")

# 抛球动画分段时长(秒)
BALL_THROW_T = 0.55     # 抛物线飞行
BALL_FLASH_T = 0.30     # 开球白闪+对手吸入
BALL_SHAKE_T = 0.50     # 每次摇动


class Battle:
    def __init__(self, game, enemy_team, trainer_name=None, callback=None, can_run=True,
                 ai_level=1):
        self.game = game
        self.enemies = enemy_team
        self.e_idx = 0
        self.trainer = trainer_name
        self.can_run = can_run
        self.can_catch = trainer_name is None
        self.ai_level = ai_level
        self.turns = 0
        self.callback = callback
        self.p_idx = next((i for i, m in enumerate(game.party) if m.hp > 0), 0)
        self.stages = {"ally": {}, "foe": {}}
        self.run_attempts = 0
        self.textbox = TextBox()
        self.phase = "anim"
        self.anim = None              # (kind, t, dur, extra)
        self.menu_idx = 0
        self.move_idx = 0
        self.party_screen = None
        self.bag_screen = None
        self.done = False
        self.result = None
        self.auto = False             # 测试模式:消息自动推进
        self.intro_t = 0.6
        self.disp = {"ally": None, "foe": None}
        self._flow = self._main_flow()
        self._started = False
        self._advance(None)

    # -------------------------------------------------- 常用引用
    @property
    def ally(self):
        return self.game.party[self.p_idx]

    @property
    def foe(self):
        return self.enemies[self.e_idx]

    # -------------------------------------------------- 流程驱动
    def _advance(self, value):
        try:
            item = self._flow.send(value) if self._started else next(self._flow)
        except StopIteration:
            self._finish()
            return
        self._started = True
        kind = item[0]
        if kind == "msg":
            self.textbox.show(item[1])
            self.phase = "msg"
        elif kind == "anim":
            self.anim = [item[1], 0.0, item[2], item[3] if len(item) > 3 else None]
            self.phase = "anim"
        elif kind == "menu":
            self.menu_idx = 0
            self.phase = "menu"
        elif kind == "movesel":
            self.move_idx = 0
            self.phase = "movesel"
        elif kind == "bag":
            self.bag_screen = BagScreen(self.game, "battle")
            self.phase = "bag"
        elif kind == "party":
            mode = item[1] if len(item) > 1 else "battle"
            self.party_screen = PartyScreen(self.game, mode, current_idx=self.p_idx)
            self.phase = "party"

    def _finish(self):
        self.done = True

    def _end_battle(self, result):
        self.result = result
        self._flow = iter(())      # 让后续 next 直接 StopIteration

    # -------------------------------------------------- 主流程
    def _main_flow(self):
        if self.trainer:
            yield ("msg", f"{self.trainer}想要对决!\n{self.trainer}派出了{self.foe.name}!")
        else:
            yield ("msg", f"野生的{self.foe.name}出现了!")
        yield ("msg", f"去吧!{self.ally.name}!")
        while True:
            act = yield ("menu",)
            if act == "fight":
                r = yield ("movesel",)
                if r == "back":
                    continue
                idx = r[1]
                move = self.ally.moves[idx]
                if move.pp <= 0:
                    yield ("msg", "PP不够了!")
                    continue
                enemy_move = self._ai_pick_move()
                player_first = self._order_first(move.name, enemy_move)
                if player_first:
                    yield from self._turn([("ally", move.name), ("foe", enemy_move)])
                else:
                    yield from self._turn([("foe", enemy_move), ("ally", move.name)])
            elif act == "bag":
                item = yield ("bag",)
                if not item:
                    continue
                yield from self._use_item(item)
            elif act == "party":
                idx = yield ("party",)
                if idx is None:
                    continue
                yield from self._switch_to(idx)
                yield from self._free_turn("foe")
            elif act == "run":
                yield from self._try_run()
            if self.result:
                return

    def _order_first(self, p_move, e_move):
        pp = data.MOVES[p_move].get("priority", 0)
        ep = data.MOVES[e_move].get("priority", 0)
        if pp != ep:
            return pp > ep
        ps = self.ally.stats["spe"] * (0.25 if self.ally.status == "麻痹" else 1)
        es = self.foe.stats["spe"] * (0.25 if self.foe.status == "麻痹" else 1)
        if ps == es:
            return random.random() < 0.5
        return ps > es

    def _turn(self, order):
        self.turns += 1
        for side, move_name in order:
            user = self.ally if side == "ally" else self.foe
            target = self.foe if side == "ally" else self.ally
            if user.hp <= 0 or target.hp <= 0:
                continue
            yield from self._use_move(side, move_name)
            if target.hp <= 0:
                if not (yield from self._faint_flow("foe" if side == "ally" else "ally")):
                    return
        # 回合结束:毒/灼伤
        for side in ("ally", "foe"):
            m = self.ally if side == "ally" else self.foe
            if m.hp > 0 and m.status in ("中毒", "灼伤"):
                dmg = max(1, m.max_hp // 8)
                m.hp = max(0, m.hp - dmg)
                yield ("msg", f"{m.name}受到{'毒' if m.status=='中毒' else '灼伤'}的伤害!")
                yield ("anim", "hit_" + side, 0.35)
                if m.hp <= 0:
                    if not (yield from self._faint_flow(side)):
                        return

    def _use_move(self, side, move_name):
        user = self.ally if side == "ally" else self.foe
        tside = "foe" if side == "ally" else "ally"
        target = self.foe if side == "ally" else self.ally
        md = data.MOVES[move_name]

        if user.status == "睡眠":
            user.sleep_turns -= 1
            if user.sleep_turns > 0:
                yield ("msg", f"{user.name}睡得正香……")
                return
            user.cure_status()
            yield ("msg", f"{user.name}醒过来了!")
        if user.status == "冻结":
            if random.random() < 0.2:
                user.cure_status()
                yield ("msg", f"{user.name}身上的冰融化了!")
            else:
                yield ("msg", f"{user.name}被冻结了,无法动弹!")
                return
        if user.status == "麻痹" and random.random() < 0.25:
            yield ("msg", f"{user.name}身体麻痹,无法动弹!")
            return

        mv = user.moves and next((m for m in user.moves if m.name == move_name), None)
        if mv:
            mv.pp = max(0, mv.pp - 1)
        yield ("msg", f"{user.name}使用了{move_name}!")
        if md["acc"] is not None and random.random() * 100 > md["acc"]:
            yield ("msg", "但是没有命中……")
            return

        if md["cat"] == "变化":
            yield from self._apply_effect(side, md.get("effect"), 100)
            return

        res = user.calc_damage(target, move_name,
                               att_stages=self.stages[side],
                               dfn_stages=self.stages[tside])
        if res["eff"] == 0:
            yield ("msg", f"对{target.name}没有效果……")
            return
        # 连续攻击(2-5 次或指定次数)
        hits = random.randint(*md["multihit"]) if md.get("multihit") else 1
        total_dealt = 0
        landed = 0
        for _ in range(hits):
            if target.hp <= 0:
                break
            dmg = max(1, int(res["damage"] * random.uniform(0.85, 1.15))) if hits > 1 else res["damage"]
            target.hp = max(0, target.hp - dmg)
            total_dealt += dmg
            landed += 1
        yield ("anim", "hit_" + tside, 0.4)
        if hits > 1:
            yield ("msg", f"命中了{landed}次!")
        if res["crit"]:
            yield ("msg", "会心一击!")
        if res["eff"] > 1:
            yield ("msg", "效果拔群!")
        elif res["eff"] < 1:
            yield ("msg", "收效甚微……")
        if target.status == "冻结" and md["type"] == "火":
            target.cure_status()
            yield ("msg", f"{target.name}身上的冰被融化了!")
        if md.get("recoil"):
            rc = max(1, int(total_dealt * md["recoil"]))
            user.hp = max(0, user.hp - rc)
            yield ("msg", f"{user.name}受到了反作用力伤害!")
        if md.get("drain") and total_dealt > 0:
            heal = max(1, int(total_dealt * md["drain"]))
            if user.hp < user.max_hp:
                user.hp = min(user.max_hp, user.hp + heal)
                yield ("msg", f"{user.name}吸取了养分!")
        yield from self._apply_effect(side, md.get("effect"), md.get("effect", {}).get("chance", 100)
                                      if md.get("effect") else 100)

    def _apply_effect(self, side, effect, chance):
        if not effect or random.random() * 100 > chance:
            return
        tside = "foe" if side == "ally" else "ally"
        target = self.foe if side == "ally" else self.ally
        if "stat" in effect:
            key, delta = effect["stat"]
            tgt_side = side if effect.get("target") == "self" else tside
            cur = self.stages[tgt_side].get(key, 0)
            if (delta < 0 and cur <= -6) or (delta > 0 and cur >= 6):
                yield ("msg", "能力已经无法再变化了!")
                return
            self.stages[tgt_side][key] = max(-6, min(6, cur + delta))
            mon = self.ally if tgt_side == "ally" else self.foe
            cn = {"atk": "攻击", "def": "防御", "spa": "特攻", "spd": "特防", "spe": "速度"}[key]
            word = "提高" if delta > 0 else "降低"
            yield ("msg", f"{mon.name}的{cn}{word}了!")
        elif "status" in effect:
            if target.status:
                yield ("msg", f"{target.name}已经处于异常状态了!")
                return
            target.status = effect["status"]
            if target.status == "睡眠":
                target.sleep_turns = random.randint(1, 4)
            word = {"中毒": "中毒了!", "灼伤": "被灼伤了!", "麻痹": "麻痹了!", "睡眠": "睡着了!"}
            yield ("msg", f"{target.name}{word[target.status]}")

    def _faint_flow(self, side):
        """处理濒倒。返回 False 表示战斗已结束。"""
        mon = self.ally if side == "ally" else self.foe
        yield ("anim", "faint_" + side, 0.45)
        yield ("msg", f"{mon.name}倒下了!")
        if side == "foe":
            gain = data.exp_gain(mon, self.trainer is not None)
            msgs, evolve_to = self.ally.gain_exp(gain)
            yield ("msg", f"{self.ally.name}获得了{gain}点经验值!")
            for t in msgs:
                yield ("msg", t)
            if evolve_to:
                old = self.ally.species
                self.ally.evolve_into(evolve_to)
                yield ("msg", f"什么?{self.ally.name}的样子变了!\n{old}进化成了{evolve_to}!")
            if self.trainer and self.e_idx < len(self.enemies) - 1:
                self.e_idx += 1
                self.stages["foe"] = {}
                self.disp["foe"] = None
                yield ("msg", f"{self.trainer}派出了{self.foe.name}!")
                return True
            if self.trainer:
                yield ("msg", f"你战胜了{self.trainer}!")
            self._end_battle("win")
            return False
        # 我方濒倒
        if any(m.hp > 0 for m in self.game.party):
            idx = yield ("party", "forced")
            if idx is not None:
                yield from self._switch_to(idx)
            return True
        yield ("msg", "你已经没有能战斗的精灵了……")
        self._end_battle("lose")
        return False

    def _switch_to(self, idx):
        old = self.ally.name
        self.p_idx = idx
        self.stages["ally"] = {}
        self.disp["ally"] = None
        yield ("msg", f"回来吧,{old}!")
        yield ("msg", f"去吧!{self.ally.name}!")

    def _free_turn(self, side):
        """捕捉失败/逃走失败/换人后,对方 free 行动。"""
        move = self._ai_pick_move()
        yield from self._use_move(side, move)
        target = self.foe if side == "ally" else self.ally
        if target.hp <= 0:
            yield from self._faint_flow("foe" if side == "ally" else "ally")

    def _use_item(self, name):
        from . import data as D
        item = D.ITEMS[name]
        self.game.bag[name] -= 1
        if self.game.bag[name] <= 0:
            del self.game.bag[name]
        if item["kind"] == "ball":
            if not self.can_catch:
                self.game.bag[name] = self.game.bag.get(name, 0) + 1
                yield ("msg", "不能对训练家的精灵扔球!")
                return
            shakes = self.foe.catch_shakes(item["rate"])
            self._thrown_item = name
            yield ("msg", f"你扔出了{name}!")
            dur = BALL_THROW_T + BALL_FLASH_T + BALL_SHAKE_T * shakes + \
                (0.7 if shakes >= 4 else 0.35)
            yield ("anim", "ball", dur, shakes)
            if shakes >= 4:
                yield ("msg", f"太好了!{self.foe.name}被抓住了!")
                if len(self.game.party) < 6:
                    self.game.party.append(self.foe)
                    yield ("msg", f"{self.foe.name}加入了队伍!")
                else:
                    self.game.pc.append(self.foe.to_dict())
                    yield ("msg", f"队伍已满,{self.foe.name}被传送到了电脑里。")
                self._end_battle("caught")
            else:
                yield ("msg", "哎呀!差一点就成功了!")
                yield from self._free_turn("foe")
            return
        m = self.ally
        if item["kind"] == "heal":
            if m.hp <= 0 or m.hp >= m.max_hp:
                yield ("msg", "现在没有效果!")
                self.game.bag[name] = self.game.bag.get(name, 0) + 1
                return
            m.hp = min(m.max_hp, m.hp + item["amount"])
            yield ("msg", f"{m.name}恢复了{item['amount']}点HP!")
        elif item["kind"] == "fullheal":
            m.hp = m.max_hp
            m.cure_status()
            yield ("msg", f"{m.name}完全恢复了!")
        elif item["kind"] == "cure":
            if not m.status:
                yield ("msg", "现在没有效果!")
                self.game.bag[name] = self.game.bag.get(name, 0) + 1
                return
            m.cure_status()
            yield ("msg", f"{m.name}的异常状态被治愈了!")
        yield from self._free_turn("foe")

    def _try_run(self):
        if not self.can_run:
            yield ("msg", "不能从训练家对战中逃走!")
            return
        ps = self.ally.stats["spe"]
        es = max(1, self.foe.stats["spe"])
        f = ps * 128 // es + 30 * self.run_attempts
        self.run_attempts += 1
        if f > 255 or random.randint(0, 255) < f:
            yield ("msg", "成功逃走了!")
            self._end_battle("ran")
        else:
            yield ("msg", "没能逃走!")
            yield from self._free_turn("foe")

    def _ai_pick_move(self):
        """原作式评分 AI:每招 0-100 分,按训练家等级加噪声后取最高。"""
        usable = [m for m in self.foe.moves if m.pp > 0]
        if not usable:
            return "挣扎"
        noise = {0: 45, 1: 20, 2: 8, 3: 3}.get(min(self.ai_level, 3), 20)
        best, best_score = None, None
        for m in usable:
            s = self._score_move(m) + random.uniform(0, noise)
            if best_score is None or s > best_score:
                best, best_score = m, s
        return best.name

    def _score_move(self, move):
        md = data.MOVES[move.name]
        if md["cat"] == "变化":
            eff = md.get("effect") or {}
            if "status" in eff:
                if self.ally.status:
                    return 2
                if eff["status"] == "麻痹" and "电" in self.ally.types:
                    return 0                        # 电系免疫麻痹
                if eff["status"] == "灼伤" and "火" in self.ally.types:
                    return 0
                return 52 if self.turns <= 1 else 22
            if "stat" in eff:
                key, delta = eff["stat"]
                tgt = "ally" if eff.get("target") != "self" else "foe"
                cur = self.stages[tgt].get(key, 0)
                if (delta > 0 and cur >= 6) or (delta < 0 and cur <= -6):
                    return 0
                s = abs(delta) * 18 + (12 if self.turns <= 1 else 0)
                if eff.get("target") == "self":
                    if self.foe.hp < self.foe.max_hp * 0.4:
                        s -= 15                     # 残血不强化
                return s
            return 4
        res = self.foe.calc_damage(self.ally, move.name,
                                   att_stages=self.stages["foe"],
                                   dfn_stages=self.stages["ally"], rng=random)
        if res["eff"] == 0:
            return -1                               # 免疫
        dmg = res["damage"] * (3 if md.get("multihit") else 1)
        s = min(100, int(100 * min(1.2, dmg / max(1, self.ally.hp))))
        if dmg >= self.ally.hp:
            s = 100                                 # 能一击倒下
        elif res["eff"] > 1:
            s = min(100, s + 10)
        return s

    # -------------------------------------------------- 输入
    def handle_event(self, e):
        if e.type != pygame.KEYDOWN or self.done:
            return
        ph = self.phase
        if ph == "msg":
            r = self.textbox.key(e)
            if r:
                self._advance(None)
        elif ph == "menu":
            self._menu_key(e)
        elif ph == "movesel":
            self._move_key(e)
        elif ph == "bag" and self.bag_screen:
            self.bag_screen.key(e)
            if self.bag_screen.done:
                item = self.bag_screen.result
                self.bag_screen = None
                self._advance(item)
        elif ph == "party" and self.party_screen:
            self.party_screen.key(e)
            if self.party_screen.done:
                idx = self.party_screen.result
                self.party_screen = None
                self._advance(idx)

    def _menu_key(self, e):
        if e.key in (pygame.K_UP, pygame.K_w):
            self.menu_idx = (self.menu_idx - 2) % 4
        elif e.key in (pygame.K_DOWN, pygame.K_s):
            self.menu_idx = (self.menu_idx + 2) % 4
        elif e.key in (pygame.K_LEFT, pygame.K_a):
            self.menu_idx = (self.menu_idx - 1) % 4
        elif e.key in (pygame.K_RIGHT, pygame.K_d):
            self.menu_idx = (self.menu_idx + 1) % 4
        elif e.key in (pygame.K_z, pygame.K_RETURN, pygame.K_SPACE):
            self._advance(("fight", "bag", "party", "run")[self.menu_idx])

    def _move_key(self, e):
        n = len(self.ally.moves)
        if e.key in (pygame.K_UP, pygame.K_w):
            self.move_idx = (self.move_idx - 2) % n
        elif e.key in (pygame.K_DOWN, pygame.K_s):
            self.move_idx = (self.move_idx + 2) % n
        elif e.key in (pygame.K_LEFT, pygame.K_a):
            self.move_idx = (self.move_idx - 1) % n
        elif e.key in (pygame.K_RIGHT, pygame.K_d):
            self.move_idx = (self.move_idx + 1) % n
        elif e.key in (pygame.K_x, pygame.K_ESCAPE):
            self._advance("back")
        elif e.key in (pygame.K_z, pygame.K_RETURN, pygame.K_SPACE):
            self._advance(("move", self.move_idx))

    # -------------------------------------------------- 更新
    def update(self, dt):
        self.textbox.update(dt)
        for k in ("ally", "foe"):
            mon = self.ally if k == "ally" else self.foe
            tgt = mon.hp / mon.max_hp
            cur = self.disp[k] if self.disp[k] is not None else tgt
            self.disp[k] = cur + (tgt - cur) * min(1.0, dt * 5)
        if self.phase == "anim" and self.anim:
            self.anim[1] += dt
            if self.anim[1] >= self.anim[2]:
                self.anim = None
                self._advance(None)
        elif self.phase == "msg" and self.auto and self.textbox.wait_key:
            self._advance(None)
        if self.intro_t > 0:
            self.intro_t -= dt

    # -------------------------------------------------- 绘制
    def draw(self, surf):
        assets = self.game.assets
        surf.blit(assets["battle_bg"], (0, 0))
        foe_x = S.WIN_W - 240
        foe_y = 120
        ally_x = 190
        ally_y = S.WIN_H - 130 - 210
        slide = max(0, self.intro_t / 0.6) * 160
        hit = self.anim[0] == "hit_foe" if self.anim else False
        hit_a = self.anim[0] == "hit_ally" if self.anim else False
        flick = 0 if (self.anim and self.anim[0].startswith("hit") and
                      int(self.anim[1] * 24) % 2 == 0) else 1

        ball_anim = self.anim is not None and self.anim[0] == "ball"
        ball_t = self.anim[1] if ball_anim else 0.0
        ball_shakes = (self.anim[3] or 0) if ball_anim else 0
        suck_k = None
        if ball_anim and ball_t > BALL_THROW_T:
            suck_k = min(1.0, (ball_t - BALL_THROW_T) / BALL_FLASH_T)
        show_foe = (self.foe.hp > 0 or (self.anim and self.anim[0] == "faint_foe")) \
            and suck_k != 1.0

        if show_foe:
            img = assets["mons"].get(data.SPECIES[self.foe.species]["art"])
            if img:
                dy = 0
                if self.anim and self.anim[0] == "faint_foe":
                    dy = int(self.anim[1] / self.anim[2] * 60)
                if suck_k is not None:
                    sc = 1.0 - 0.92 * suck_k
                    iw = max(2, int(img.get_width() * sc))
                    ih = max(2, int(img.get_height() * sc))
                    small = pygame.transform.scale(img, (iw, ih))
                    surf.blit(small, (foe_x + 40 - iw // 2, foe_y - ih // 2))
                elif flick or not hit:
                    x = foe_x + int(slide) + (random.randint(-2, 2) if hit else 0)
                    surf.blit(img, (x, foe_y - 40 + dy))
        if ball_anim:
            ball = self.game.assets.get("balls", {}).get(getattr(self, "_thrown_item", "")) \
                or assets["ball"]
            sx0, sy0 = ally_x + 170, ally_y + 60            # 出手点
            ex, ey = foe_x + 30, foe_y + 56                 # 落地位
            if ball_t < BALL_THROW_T:
                k = ball_t / BALL_THROW_T
                x = sx0 + (ex - sx0) * k
                y = sy0 + (ey - sy0) * k - int(math.sin(math.pi * k) * 130)
                img = pygame.transform.rotate(ball, int(540 * k))
                surf.blit(img, (x - img.get_width() // 2, y - img.get_height() // 2))
            else:
                st = ball_t - BALL_THROW_T
                pygame.draw.ellipse(surf, (96, 140, 96), (ex - 15, ey + 7, 30, 9))
                if st < BALL_FLASH_T:
                    k = st / BALL_FLASH_T
                    r = int(6 + k * 40)
                    pygame.draw.circle(surf, (255, 255, 255), (foe_x + 40, foe_y),
                                       r, max(2, int(7 * (1 - k))))
                else:
                    st2 = st - BALL_FLASH_T
                    idx = int(st2 // BALL_SHAKE_T)
                    if idx < ball_shakes:
                        k2 = (st2 % BALL_SHAKE_T) / BALL_SHAKE_T
                        ang = math.sin(math.pi * k2) * 24
                        img = pygame.transform.rotate(ball, ang)
                        surf.blit(img, (ex - img.get_width() // 2,
                                        ey - img.get_height() // 2))
                    else:
                        surf.blit(ball, (ex - ball.get_width() // 2,
                                         ey - ball.get_height() // 2))
                        if ball_shakes >= 4:
                            for dx, dy2, rr in ((-15, -8, 3), (13, -12, 2), (17, 3, 2)):
                                pygame.draw.circle(surf, (255, 214, 90),
                                                   (ex + dx, ey + dy2), rr)
        if self.ally.hp > 0 or (self.anim and self.anim[0] == "faint_ally"):
            img = assets["mons_back"].get(data.SPECIES[self.ally.species]["art"])
            if img:
                back = pygame.transform.scale(img, (int(img.get_width() * 1.35),
                                                    int(img.get_height() * 1.35)))
                dy = 0
                if self.anim and self.anim[0] == "faint_ally":
                    dy = int(self.anim[1] / self.anim[2] * 70)
                if flick or not hit_a:
                    surf.blit(back, (ally_x - int(slide), ally_y + 40 + dy))

        # 信息面板
        f = self.foe
        panel(surf, (24, 24, 340, 92))
        draw_text(surf, f.name, 44, 36, 24)
        draw_text(surf, f"Lv{f.level}", 320, 36, 24, anchor="tr")
        hp_bar(surf, 44, 88, 240, self.disp["foe"] or 1)
        st = f.status_tag
        if st:
            draw_text(surf, st, 330, 74, 20, color=(200, 70, 70))
        a = self.ally
        panel(surf, (S.WIN_W - 400, S.WIN_H - 130 - 150, 376, 138))
        draw_text(surf, a.name, S.WIN_W - 380, S.WIN_H - 130 - 134, 24)
        draw_text(surf, f"Lv{a.level}", S.WIN_W - 44, S.WIN_H - 130 - 134, 24, anchor="tr")
        hp_bar(surf, S.WIN_W - 380, S.WIN_H - 130 - 74, 260, self.disp["ally"] or 1)
        draw_text(surf, f"{a.hp}/{a.max_hp}", S.WIN_W - 60, S.WIN_H - 130 - 56, 20, anchor="tr")
        st = a.status_tag
        if st:
            draw_text(surf, st, S.WIN_W - 60, S.WIN_H - 130 - 134 + 30, 20, color=(200, 70, 70))
        if a.exp is not None:
            need = data.exp_to_next(a.level, a.growth)
            cur = a.exp - data.exp_for_level(a.level, a.growth)
            exp_bar(surf, S.WIN_W - 380, S.WIN_H - 130 - 32, 260, cur / need)

        # 底部文本框与菜单
        self.textbox.draw(surf)
        if self.phase == "menu":
            bx, by = S.WIN_W - 320, S.WIN_H - 130 - 6
            panel(surf, (bx, by, 300, 122), bg=S.C_MENU_BG)
            for i, opt in enumerate(MENU_OPTS):
                ox = bx + 30 + (i % 2) * 150
                oy = by + 16 + (i // 2) * 48
                if i == self.menu_idx:
                    cursor_arrow(surf, ox - 18, oy + 15)
                draw_text(surf, opt, ox, oy, 24)
        elif self.phase == "movesel":
            bx, by = 10, S.WIN_H - 136
            panel(surf, (bx, by, 640, 124), bg=S.C_MENU_BG)
            for i, mv in enumerate(self.ally.moves):
                ox = bx + 30 + (i % 2) * 310
                oy = by + 14 + (i // 2) * 50
                if i == self.move_idx:
                    cursor_arrow(surf, ox - 18, oy + 14)
                draw_text(surf, mv.name, ox, oy, 22)
                if mv.pp <= 0:
                    draw_text(surf, "PP0", ox + 130, oy, 18, color=(200, 70, 70))
            md = data.MOVES[self.ally.moves[self.move_idx].name]
            panel(surf, (660, by, S.WIN_W - 672, 124), bg=S.C_MENU_BG)
            col = S.TYPE_COLOR.get(md["type"], (120, 120, 120))
            pygame.draw.rect(surf, col, (676, by + 14, 64, 28), border_radius=6)
            draw_text(surf, md["type"], 708, by + 18, 20, color=S.C_WHITE, shadow=False, anchor="center")
            draw_text(surf, f"PP {self.ally.moves[self.move_idx].pp}/{self.ally.moves[self.move_idx].max_pp}",
                      676, by + 54, 20)
            draw_text(surf, f"威力 {md['power'] or '—'}  命中 {md['acc'] if md['acc'] is not None else '—'}",
                      676, by + 84, 20)
            draw_text(surf, "X 返回", S.WIN_W - 90, by + 14, 18, color=(90, 110, 140))
        if self.phase == "party" and self.party_screen:
            self.party_screen.draw(surf, self.game.assets["icons"])
        elif self.phase == "bag" and self.bag_screen:
            self.bag_screen.draw(surf)

    # 测试辅助:自动驱动直到需要输入或结束
    def drive_for_test(self, actions):
        """actions: 队列,元素为 ("menu",action) / ("move",idx) / ("bag",item) / ("party",idx)。"""
        guard = 0
        while not self.done and guard < 2000:
            guard += 1
            self.update(0.05)
            if self.phase == "menu" and actions:
                kind, val = actions.pop(0)
                if kind == "menu":
                    self._advance(val)
            elif self.phase == "movesel":
                self._advance(("move", 0)) if not actions or actions[0][0] != "move" \
                    else self._advance(("move", actions.pop(0)[1]))
            elif self.phase == "bag" and actions and actions[0][0] == "bag":
                self._advance(actions.pop(0)[1])
            elif self.phase == "party" and actions and actions[0][0] == "party":
                self._advance(actions.pop(0)[1])
        return self.result
