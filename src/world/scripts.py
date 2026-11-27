"""对话与事件脚本(生成器协议)。

yield 协议:
  ("msg",t) ("yesno",) ("choice",[..]) ("starter",) ("heal",) ("give",item,n) ("flag",k,v=True)
  ("shop",stock) ("trainer",key,display=None,ai=2) → "win"/"lose"/"ran"
  ("wild",species,level) ("legendary",species,level,flag) ("warp",map,x,y,facing) ("fade",sec)
  ("badge",flag) ("fly",) ("hall",) ("money",n) ("tm",num) ("hm",num) ("quiz",q,[opts],correct) → bool
  ("hide",) 隐藏当前 NPC ("credits",) 制作人员名单
"""
from .. import data as D
from . import VERSIONS

SCRIPTS = {}


def sc(name):
    def deco(fn):
        SCRIPTS[name] = fn
        return fn
    return deco


def rival_key(stage, starter):
    """劲敌帕尔的队伍取决于玩家的初始精灵:草→火 火→水 水→草。"""
    base = {1: (247, 248, 249), 2: (470, 471, 472), 3: (473, 474, 475),
            4: (476, 477, 478), 5: (479, 480, 481)}[stage]
    idx = {"草苗龟": 1, "小火焰猴": 2, "波加曼": 0}[starter]
    return base[idx]


CLASS_LINES = {
    "YOUNGSTER": ("喂!那边的小伙伴!\n来一场对战吧!", "呜哇,输了!"),
    "LASS": ("等一下!\n让我看看你的实力!", "呜……我输了。"),
    "BUG_CATCHER": ("我的虫系伙伴可是很强的!", "虫儿们……对不起。"),
    "CAMPER": ("野营的对战,来吧!", "露营以失败告终……"),
    "PICNICKER": ("要不要来一场愉快的对战?", "愉快……不过输了。"),
    "HIKER": ("嘿咻嘿咻……来比一场吧!", "嘿咻,输了嘿咻。"),
    "FISHERMAN": ("钓鱼太多无聊了,对战吧!", "鱼跑了,我也输了。"),
    "AROMA_LADY": ("闻闻这花香……然后来对战!", "花香依旧,胜负已定。"),
    "BATTLE_GIRL": ("我的拳头可不会留情!", "好拳法!"),
    "BLACK_BELT": ("oola!来一决胜负吧!", "oola……"),
    "ACE_TRAINER_M": ("你是很强的训练家吧?让我看看!", "败得心服口服!"),
    "ACE_TRAINER_F": ("相遇即是缘分,来对战吧!", "你真的很强。"),
    "PSYCHIC_M": ("我预感……你会赢。不对,是我会赢!", "预感应验了……"),
    "PSYCHIC_F": ("让我用超能力看看你的实力!", "看不透呢……"),
    "WORKER": ("休息时间来一场对战!", "回去继续干活了……"),
    "SCIENTIST": ("用对战来验证我的理论!", "理论需要修正……"),
    "SCHOOL_KID_M": ("实践比课本更重要!对战吧!", "回去好好学习……"),
    "SCHOOL_KID_F": ("来吧,课堂上学的招式!", "呜,老师教的不够……"),
    "SWIMMER_M": ("哗啦哗啦!来比一场吧!", "哗啦……"),
    "SWIMMER_F": ("要不要一起游泳顺便对战?", "……"),
    "SKIER_M": ("从雪坡上冲下来,然后对战!", "滑得太快了……"),
    "SKIER_F": ("雪地对战,来吧!", "冷得发抖……"),
    "SAILOR": ("海员的对决,来!", "返航了……"),
    "JOGGER": ("跑步顺便对战,来!", "跑不动了……"),
    "BIRD_KEEPER": ("我的鸟儿们想活动活动!", "鸟儿们累了……"),
    "NINJA_BOY": ("忍者的对决!", "忍……"),
    "COLLECTOR": ("我的收藏可是很厉害的!", "收藏败北……"),
    "RUIN_MANIAC": ("遗迹前的对决!", "遗迹的教诲……"),
    "GUITARIST": ("用音波震慑你!", "走音了……"),
    "POLICEMAN": ("站住!来一场正当的对战!", "执行完毕……"),
    "BEAUTY": ("来一场优雅的对战吧?", "优雅地认输。"),
    "RICH_BOY": ("用钱堆出来的实力,见识一下!", "钱不是万能的……"),
    "LADY": ("我的宝可梦可是名贵的!", "名贵的输了……"),
    "GENTLEMAN": ("绅士地对决吧。", "绅士地认输。"),
    "TUBER_M": ("来玩水顺便对战吧!", "呛水了……"),
    "TUBER_F": ("浮在水上对战!", "沉下去了……"),
    "VETERAN": ("年轻人,让我看看你的本事!", "后生可畏!"),
    "DRAGON_TAMER": ("龙之对决!", "龙低头了……"),
    "GALACTIC": ("银河队在执行任务,别挡路!", "呜……可恶!"),
    "GALACTIC_F": ("银河队的行动不容妨碍!", "可恶……"),
    "POKEFAN_M": ("看看我最爱的宝可梦!", "呜,我的孩子……"),
    "POKEFAN_F": ("我的宝可梦最可爱!", "输了也可爱。"),
    "ARTIST": ("把对战化为一幅画!", "画砸了……"),
    "PARASOL_LADY": ("阳伞下来一场对战?", "太阳太大了……"),
    "COWGIRL": ("牧场对决!", "牧场输啦……"),
    "IDOL": ("偶像的对决!", "粉丝都看不下去了……"),
    "PKMN_RANGER_M": ("守护自然的巡林员,来!", "自然输了……"),
    "PKMN_RANGER_F": ("和巡林员来一场对战!", "守护不了了……"),
    "INTERVIEWERS": ("采访一下!对战吧!", "采访失败……"),
    "DOUBLE_TEAM": ("双人组合的对决!", "配合失误……"),
    "BREEDER": ("培育家的实力!", "培育失败……"),
}


def class_of(key):
    return D.TRAINERS[key]["raw"].replace("TRAINER_CLASS_", "")


def trainer_lines(key):
    raw = class_of(key)
    return CLASS_LINES.get(raw, ("来一场对战吧!", "我输了……"))


@sc("trainer")
def sc_trainer(g, npc):
    key = npc["trainer"]
    t = D.TRAINERS[key]
    flag = f"beat_{key}"
    if g.flags.get(flag):
        pre, post = trainer_lines(key)
        yield ("msg", f"{t['cls']} {t['name']}:{post}")
        return
    pre, post = trainer_lines(key)
    yield ("msg", f"{t['cls']} {t['name']}:{pre}")
    r = yield ("trainer", key)
    if r != "win":
        return
    g.flags[flag] = True
    yield ("msg", f"{t['cls']} {t['name']}:{post}")


# ================================================================ 通用
@sc("nurse")
def sc_nurse(g):
    yield ("msg", "欢迎来到精灵中心!\n需要为您的精灵恢复体力吗?")
    r = yield ("yesno",)
    if r == 0:
        yield ("heal",)
        yield ("msg", "您的精灵已经恢复了活力!\n期待您再次光临。")
        ow = g._overworld()
        if ow:
            town = "league" if ow.map_id == "league_gate" else \
                (ow.map_id[:-7] if ow.map_id.endswith("_center") else ow.map_id)
            g.flags[f"visited_{town}"] = True
            g.respawn = (ow.map_id, ow.px, ow.py, ow.dir)
    else:
        yield ("msg", "好的,需要时再来找我。")


@sc("shop")
def sc_shop(g, stock):
    yield ("msg", "欢迎光临!慢慢挑,不买也没关系。")
    yield ("shop", stock)
    yield ("msg", "感谢惠顾,欢迎再来。")


@sc("mom")
def sc_mom(g):
    if not g.flags.get("starter"):
        yield ("msg", "妈妈:山梨博士在真砂镇的研究所等你呢。\n从北边的201号道路一直走就到。")
        return
    yield ("msg", "妈妈:出门前要好好照顾你的精灵哦。\n要休息一会儿吗?")
    r = yield ("yesno",)
    if r == 0:
        yield ("heal",)
        yield ("msg", "你的精灵们恢复了活力!\n妈妈:路上小心。")
    else:
        yield ("msg", "妈妈:加油哦。")


@sc("rival_mom")
def sc_rival_mom(g):
    if g.flags.get("starter"):
        yield ("msg", "帕尔的妈妈:那孩子又跑出去了……\n你见到他的话,让他别太着急。")
    else:
        yield ("msg", "帕尔的妈妈:帕尔一大早就跑去真砂镇了。\n真是坐不住啊。")


@sc("rival_dad")
def sc_rival_dad(g):
    yield ("msg", "帕尔的爸爸:帕尔总是冒冒失失的,\n但有一颗不服输的心。")


@sc("prof")
def sc_prof(g):
    if g.flags.get("starter"):
        if g.badge_count() >= 8:
            yield ("msg", f"山梨博士:{g.version_name}……不,是神奥的传说。\n去宝可梦联盟吧,那里有你在等待。")
        else:
            yield ("msg", "山梨博士:精灵的强弱关键在于属性相性。\n多和训练家对战,积攒经验吧!")
        return
    yield ("msg", "山梨博士:哦哦,你就是……\n正好,我这里有三只精灵,选一只做你的伙伴吧。")
    pick = yield ("starter",)
    if not pick:
        yield ("msg", "山梨博士:不着急,想好了再来。")
        return
    g.flags["starter"] = True
    g.flags["starter_name"] = pick
    yield ("msg", f"山梨博士:{pick}就交给你了!\n好好珍惜这段旅程。")
    yield ("give", "精灵球", 5)
    yield ("msg", "(获得了 精灵球×5)")
    yield ("msg", "山梨博士:北边201号道路通往双叶镇,\n东边202号道路通往祝庆市。\n先去祝庆市看看吧。")


@sc("ball")
def sc_ball(g):
    yield from sc_prof(g)


@sc("aide")
def sc_aide(g):
    yield ("msg", "助手:博士研究的是神奥地区的宝可梦。\n图鉴的完成就拜托你了。")


@sc("aide_exp_share")
def sc_aide_exp(g):
    if g.flags.get("badge_coal") and not g.flags.get("got_exp_share"):
        yield ("msg", "博士的助手:听说你拿到了煤炭徽章!\n这个给你,是博士托我转交的。")
        yield ("give", "学习装置", 1)
        yield ("msg", "(获得了 学习装置!)\n放在背包里,不出战的精灵也能分到经验值。")
        g.flags["got_exp_share"] = True
    elif g.flags.get("starter"):
        yield ("msg", "博士的助手:拿到煤炭徽章后,\n博士说有东西要交给你。")
    else:
        yield ("msg", "博士的助手:博士在真砂镇的研究所。")


@sc("school_teacher")
def sc_teacher(g):
    yield ("msg", "老师:属性相性是对战的基础。\n火克草,草克水,水克火。\n攻击招式还分物理和特殊两类。")


@sc("school_kid")
def sc_school_kid(g):
    yield ("msg", "学生:我在这里学习对战的基础!\n听说黑金市的道馆馆主很强。")


@sc("museum_guide")
def sc_museum(g):
    yield ("msg", "讲解员:黑金市因煤炭而兴盛。\n这里展示着古代宝可梦的化石。")


@sc("flower_shop")
def sc_flower_shop(g):
    yield ("msg", "花匠:花苑镇的花一年四季都开着。\n给精灵带上花,心情也会变好哦。")


@sc("bike_shop")
def sc_bike_shop(g):
    if g.flags.get("eterna_galactic_clear") and not g.flags.get("got_bike"):
        yield ("msg", "店主:听说你赶走了银河队!\n这辆自行车送给你了!")
        yield ("give", "自行车", 1)
        yield ("msg", "(获得了 自行车!)\n本作中按住 B/Shift 即可跑步,效果相同。")
        g.flags["got_bike"] = True
    else:
        yield ("msg", "店主:百代市的银河队真让人头疼……")


@sc("bebe")
def sc_bebe(g):
    if g.flags.get("badge_relic") and not g.flags.get("got_eevee"):
        yield ("msg", "丝绒:你拿到了遗迹徽章呀!\n这只伊布送给你,要好好珍惜它。")
        yield ("give_pokemon", "伊布", 20)
        yield ("msg", "(获得了 伊布!)")
        g.flags["got_eevee"] = True
    else:
        yield ("msg", "丝绒:伊布能进化成很多种样子,\n真是不可思议的宝可梦。")


# ================================================================ 城镇闲聊
def _progress_line(g):
    b = g.badge_count()
    if not g.flags.get("starter"):
        return "你还没有伙伴精灵呢。\n去真砂镇的研究所找山梨博士吧!"
    steps = ["黑金市的岩石道馆怎么样?", "百代市的菜种馆长很难对付吧?",
             "帷幕市的阿李馆长是格斗系的高手!", "湿原市的吉宪馆长很豪爽吧?",
             "家缘市的梅丽莎馆长,幽灵系很棘手!", "水脉市的东瓜馆长,钢系防御超高!",
             "雪峰市的小菘馆长,冰系很强!", "滨海市的电次馆长在等你!",
             "你已经收集了全部 8 枚徽章!\n去宝可梦联盟挑战四天王吧!"]
    return steps[min(b, 8)]


@sc("twinleaf_villager")
def sc_twinleaf_villager(g):
    if not g.flags.get("starter"):
        yield ("msg", "村民:真砂镇的山梨博士\n在研究神奥地区的宝可梦。")
    else:
        yield ("msg", "村民:你出发了啊!\n双叶镇永远是你的家。")


@sc("sandgem_villager")
def sc_sandgem_villager(g):
    yield ("msg", f"居民:{_progress_line(g)}")


@sc("jubilife_villager")
def sc_jubilife_villager(g):
    if g.flags.get("badge_cobble") and not g.flags.get("got_vs_seeker"):
        yield ("msg", "市民:你拿到圆石徽章了呀!\n这个对战搜寻器送给你,\n能让打败过的训练家再战一场。")
        yield ("give", "对战搜寻器", 1)
        g.flags["got_vs_seeker"] = True
        yield ("msg", "(获得了 对战搜寻器!\n在背包中使用即可让道路训练家重新应战。)")
        return
    yield ("msg", "市民:祝庆市有神奥最大的商店。\n训练家学校也在北边。")


@sc("jubilife_youth")
def sc_jubilife_youth(g):
    yield ("msg", "短裤小子:203号道路上有个人一直在找对手,\n好像叫帕尔。")


@sc("dawn_pal")
def sc_dawn_pal(g):
    g.flags["met_dawn"] = True
    yield ("msg", "小光:我是山梨博士的助手小光。\n祝庆市往东是203号道路,\n再过去就是黑金市了。")


@sc("oreburgh_hiker")
def sc_oreburgh_hiker(g):
    if not g.flags.get("badge_coal"):
        yield ("msg", "登山男:馆长瓢太在黑金炭坑里。\n先去炭坑找他吧。")
    else:
        yield ("msg", "登山男:拿到煤炭徽章了?\n往南207号道路,翻过天冠山就是家缘市。")


@sc("floaroma_lady")
def sc_floaroma_lady(g):
    yield ("msg", "花匠:东边205号道路的桥上\n有个可疑的人挡着路……")


@sc("eterna_villager")
def sc_eterna_villager(g):
    yield ("msg", "市民:百代市的东边是211号道路,\n穿过天冠山可以到神和镇。")


@sc("hearthome_villager")
def sc_hearthome_villager(g):
    if g.badge_count() >= 4:
        yield ("msg", "市民:梅丽莎馆长回来了!\n幽灵系的道馆,可要小心。")
    else:
        yield ("msg", "市民:梅丽莎馆长出门了……\n听说要拿到 4 枚徽章她才回来。")


@sc("solaceon_villager")
def sc_solaceon_villager(g):
    yield ("msg", "村民:北边210号道路雾很大,\n带好解麻药再走吧。")


@sc("veilstone_youth")
def sc_veilstone_youth(g):
    yield ("msg", "短裤小子:百货商店 2 楼卖招式学习机!\n道馆馆主阿李就在北边。")


@sc("galactic_grunt_city")
def sc_galactic_city(g):
    yield ("msg", "银河队手下:这座楼被我们银河队征用了!\n识相的就别进来!")


@sc("galactic_hq_door")
def sc_galactic_hq_door(g):
    if g.badge_count() >= 7:
        yield ("msg", "银河队手下:什么?!你竟然打败了雪峰道馆……\n好,让你见识银河队的真正实力!")
        r = yield ("trainer", 515)
        if r != "win":
            return
        g.flags["beat_515"] = True
        g.flags["hq_door_open"] = True
        yield ("msg", "银河队手下:呜……进去吧,\n反正老大会收拾你的。")
        yield ("hide",)
    else:
        yield ("msg", "银河队手下:这里禁止进入!\n(先拿到 7 枚徽章再说吧。)")


@sc("celestic_lady")
def sc_celestic_lady(g):
    yield ("msg", "居民:神和镇传承着神奥的创世传说。\n长老就住在东边。")


@sc("snowpoint_villager")
def sc_snowpoint_villager(g):
    yield ("msg", "滑雪客:雪峰道馆的冰面会滑,\n小心别撞到墙!")


@sc("sunyshore_youth")
def sc_sunyshore_youth(g):
    yield ("msg", "短裤小子:电次馆长最近没什么干劲……\n不知道你能不能让他提起兴趣。")


@sc("league_officer")
def sc_league_officer(g):
    if g.flags.get("champion"):
        yield ("msg", "联盟工作人员:冠军,欢迎回来!")
    else:
        yield ("msg", "联盟工作人员:前方是宝可梦联盟。\n四天王与冠军竹兰在等候真正的挑战者。")


@sc("league_gate_guard")
def sc_league_guard(g):
    if g.badge_count() >= 8:
        yield ("msg", "工作人员:已确认 8 枚徽章。\n四天王就在前方,请先休息好吧。")
    else:
        yield ("msg", "工作人员:只有集齐 8 枚徽章的训练家\n才能挑战四天王。")


@sc("lost_tower_lady")
def sc_lost_tower_lady(g):
    yield ("msg", "扫墓人:丧失塔里安息着很多宝可梦……\n晚上能听到奇怪的声音。")


@sc("lost_tower_elder")
def sc_lost_tower_elder(g):
    yield ("msg", "老婆婆:塔顶那个东西\n是给有缘人准备的。")


@sc("gate_222")
def sc_gate_222(g):
    if g.flags.get("spear_clear"):
        yield ("msg", "警察:天冠山的事件解决了。\n滨海市在前面,去吧。")
    else:
        yield ("msg", "警察:前面现在是禁止通行!\n天冠山上发生了大事件。")


@sc("gate_228")
def sc_gate_228(g):
    if g.flags.get("champion"):
        yield ("msg", "研究员:这条通往228号道路的路\n现在可以通行了。")
        g.flags["open_228"] = True
    else:
        yield ("msg", "研究员:这条路正在调查中,禁止通行。")


@sc("lake_verity_lady")
def sc_lake_verity_lady(g):
    yield ("msg", "游客:心齐湖里住着\n掌管感情的宝可梦……")


@sc("iron_sailor")
def sc_iron_sailor(g):
    yield ("msg", "船夫:要不要坐船去钢铁岛?\n那里能遇到稀有的宝可梦。")
    r = yield ("yesno",)
    if r == 0:
        yield ("fade", 0.6)
        yield ("warp", "iron_island", 21, 9, "left")
        yield ("msg", "船夫:回程的时候,\n从东边的出口出来就能坐船回去。")
    else:
        yield ("msg", "船夫:随时欢迎。")


@sc("riley")
def sc_riley(g):
    yield ("msg", "亚玄:钢铁岛的矿工们说\n这里有神秘的宝可梦出没。\n路卡利欧就是在这里遇到的。")


@sc("snowpoint_sailor")
def sc_snowpoint_sailor(g):
    if g.flags.get("champion"):
        yield ("msg", "船夫:联盟冠军!要不要去战斗区?\n那里的宝可梦可都是高手级别的。")
        r = yield ("yesno",)
        if r == 0:
            yield ("fade", 0.6)
            yield ("warp", "fight_area", 10, 10, "up")
    else:
        yield ("msg", "船夫:成为冠军之后,\n带你去一个特别的地方。")


@sc("fight_area_sailor")
def sc_fight_area_sailor(g):
    yield ("msg", "船夫:要回神奥本土吗?")
    r = yield ("yesno",)
    if r == 0:
        yield ("fade", 0.6)
        yield ("warp", "snowpoint", 17, 13, "down")


@sc("windworks_scientist")
def sc_windworks_scientist(g):
    if g.flags.get("windworks_clear"):
        yield ("msg", "研究员:谢谢你赶走了银河队!\n风车又转起来了。")
        if not g.flags.get("got_ww_gift"):
            yield ("give", "好伤药", 3)
            yield ("msg", "(获得了 好伤药×3)")
            g.flags["got_ww_gift"] = True
    else:
        yield ("msg", "研究员:银河队把这里占领了……")


@sc("mine_worker")
def sc_mine_worker(g):
    yield ("msg", "矿工:黑金炭坑的地下\n就是馆长瓢太平时锻炼的地方。")


@sc("mine_hiker_hm")
def sc_mine_hiker(g):
    if g.flags.get("starter") and not g.flags.get("hm_rock_smash"):
        yield ("msg", "登山男:你在找馆长吧?\n这个给你,秘传学习器06「碎岩」。")
        yield ("hm", 6)
        g.flags["hm_rock_smash"] = True
        yield ("msg", "(获得了 秘传学习器06!)\n教会精灵后,可以打碎裂开的岩石。")
    else:
        yield ("msg", "登山男:碎岩在对战中也很实用,\n能降低对手的防御。")


@sc("roark_mine")
def sc_roark_mine(g):
    yield ("msg", "瓢太:哦?你是来挑战道馆的?\n让我看看……好,我这就回去。\n在道馆等我!")
    g.flags["roark_returned"] = True


@sc("galactic_205")
def sc_galactic_205(g):
    yield ("msg", "银河队手下:这座桥现在归银河队管!\n想过的话,先去发电厂问问我们的伙星大人吧!")
    yield ("msg", "(桥被挡住了。\n先去东边的谷间发电厂看看。)")


@sc("galactic_ww1")
def sc_galactic_ww1(g):
    yield ("msg", "银河队手下:发电厂是我们的了!")
    r = yield ("trainer", 297)
    if r != "win":
        return
    g.flags["beat_297"] = True
    yield ("msg", "银河队手下:呜……伙星大人会替我报仇的!")
    yield ("hide",)


@sc("galactic_ww2")
def sc_galactic_ww2(g):
    yield ("msg", "银河队手下:别想过去!")
    r = yield ("trainer", 298)
    if r != "win":
        return
    g.flags["beat_298"] = True
    yield ("msg", "银河队手下:可恶……")
    yield ("hide",)


@sc("mars_windworks")
def sc_mars_windworks(g):
    if g.flags.get("windworks_clear"):
        return
    yield ("msg", "伙星:你就是那个碍事的小鬼?\n银河队伙星,让你见识一下实力!")
    r = yield ("trainer", 295, "银河队干部 伙星", 3)
    if r != "win":
        return
    g.flags["windworks_clear"] = True
    yield ("msg", "伙星:哼,算你厉害……\n不过银河队的计划不会就此停止!")
    yield ("hide",)
    yield ("msg", "(挡住桥的银河队手下离开了。)")


@sc("cynthia_forest")
def sc_cynthia_forest(g):
    yield ("msg", "竹兰:你好,我是竹兰。\n在研究神奥的神话。")
    yield ("msg", "竹兰:这个给你,秘传学习器01「居合劈」。\n砍断挡路的树丛会很方便。")
    yield ("hm", 1)
    g.flags["hm_cut"] = True
    g.flags["met_cynthia_forest"] = True
    yield ("msg", "(获得了 秘传学习器01!)\n竹兰:前面就是百代市了。加油。")


# ================================================================ 劲敌 帕尔
def _rival_battle(g, stage, flag, intro, outro):
    if g.flags.get(flag):
        yield ("msg", "帕尔:下次我一定会赢的!")
        return
    key = rival_key(stage, g.flags.get("starter_name", "草苗龟"))
    yield ("msg", intro)
    r = yield ("trainer", key, "宝可梦训练家 帕尔", 2)
    if r != "win":
        return
    g.flags[flag] = True
    yield ("msg", outro)
    return True


@sc("rival_203")
def sc_rival_203(g):
    yield from _rival_battle(g, 1, "beat_rival1",
                             "帕尔:哦!是你!\n正好,让我试试新伙伴的实力!",
                             "帕尔:什么嘛,我居然输了!\n……好吧,下次一定赢!\n我要去黑金市的道馆!")


@sc("rival_eterna")
def sc_rival_eterna(g):
    yield from _rival_battle(g, 2, "beat_rival2",
                             "帕尔:你也到百代市了!\n来,比一场看看谁进步更快!",
                             "帕尔:呜……又输了!\n我去看看银河队在干什么,\n你也小心点!")


@sc("rival_hearthome")
def sc_rival_hearthome(g):
    yield from _rival_battle(g, 3, "beat_rival3",
                             "帕尔:家缘市的道馆馆长不在……\n真没劲,先跟你比一场!",
                             "帕尔:可恶,又输了!\n我要去帷幕市了,\n听说那里的馆长很强!")


@sc("rival_pastoria")
def sc_rival_pastoria(g):
    yield ("msg", "帕尔:你拿到沼泽徽章了?\n那正好,来比一场!")
    key = rival_key(4, g.flags.get("starter_name", "草苗龟"))
    r = yield ("trainer", key, "宝可梦训练家 帕尔", 2)
    if r != "win":
        return
    g.flags["beat_rival4"] = True
    yield ("msg", "帕尔:呜哇,完全不是对手……\n咦,那边是不是吉宪馆长?")
    yield ("msg", "吉宪:哈哈哈!年轻人的对战真精彩!\n小鬼,你 next 该去家缘市了。\n梅丽莎馆长回来了!")
    yield ("msg", "竹兰:……继续努力。\n(帕尔跑向了帷幕市。)")
    g.flags["wake_scene"] = True


@sc("rival_victory")
def sc_rival_victory(g):
    yield ("msg", "帕尔:你也是来挑战联盟的吧!\n在进去之前,来一场真正的对决!")
    key = rival_key(5, g.flags.get("starter_name", "草苗龟"))
    r = yield ("trainer", key, "宝可梦训练家 帕尔", 3)
    if r != "win":
        return
    g.flags["beat_rival5"] = True
    yield ("msg", "帕尔:……我输了。但你也不轻松吧?\n四天王比这还要厉害,做好准备!\n先去休息,我在联盟等你!")
    yield ("hide",)


# ================================================================ 银河队事件
@sc("galactic_celestic")
def sc_galactic_celestic(g):
    yield ("msg", "银河队手下:长老在里面,\n有本事就进去看看啊!")


@sc("cyrus_celestic")
def sc_cyrus_celestic(g):
    yield ("msg", "赤日:……你是谁?\n无需多说。我讨厌战斗,\n但妨碍银河队计划的人必须清除。")
    r = yield ("trainer", 403, "银河队老大 赤日", 3)
    if r != "win":
        return
    g.flags["celestic_cyrus"] = True
    yield ("msg", "赤日:……有意思。\n但 spirit 是没有意义的。\n银河队的计划,不会因你而止步。")
    yield ("hide",)
    yield ("msg", "(赤日离开了。\n去看看长老怎么样了吧。)")


@sc("celestic_elder")
def sc_celestic_elder(g):
    if not g.flags.get("celestic_cyrus"):
        if g.badge_count() >= 5:
            yield ("msg", "长老:我的孙女竹兰也是训练家……\n最近镇上来了些奇怪的人。")
        else:
            yield ("msg", "长老:神和镇传承着\n时间与空间的古老传说。")
        return
    if not g.flags.get("hm_surf"):
        yield ("msg", "长老:刚才谢谢你。\n这个给你,秘传学习器03「冲浪」。\n它能在水面上前进。")
        yield ("hm", 3)
        g.flags["hm_surf"] = True
        yield ("msg", "(获得了 秘传学习器03!)\n长老:西边的水脉市,\n东边的天冠山……水路会让你的旅程更广阔。")
    else:
        yield ("msg", "长老:竹兰说她要去看看天冠山……\n你也要小心银河队。")


@sc("galactic_spear_1")
def sc_galactic_spear_1(g):
    yield ("msg", "银河队手下:老大正在举行仪式!\n不许靠近!")
    r = yield ("trainer", 833)
    if r != "win":
        return
    yield ("msg", "银河队手下:呜……老大,抱歉!")
    yield ("hide",)


@sc("galactic_spear_2")
def sc_galactic_spear_2(g):
    yield ("msg", "银河队手下:别想过去!")
    r = yield ("trainer", 834)
    if r != "win":
        return
    yield ("msg", "银河队手下:可恶……")
    yield ("hide",)


@sc("cyrus_spear")
def sc_cyrus_spear(g):
    yield ("msg", "赤日:……你追到这里来了。\n这个世界是残缺的,\n我要用传说的宝可梦创造新的世界。")
    yield ("msg", "赤日:挡路的话,就消失吧!")
    r = yield ("trainer", 404, "银河队老大 赤日", 3)
    if r != "win":
        return
    g.flags["spear_cyrus"] = True
    yield ("msg", "赤日:……我输了吗。\n但仪式已经完成。\n看吧,神奥的传说现身了!")
    yield ("hide",)
    yield ("fade", 1.0)
    yield ("msg", "天空裂开了……!\n传说中掌控"
           + ("时间" if g.version == "D" else "空间") + "的宝可梦出现了!")
    yield ("msg", "(与传说中的宝可梦对峙!\n它是可以被捕捉的——多准备一些精灵球吧。)")


@sc("spear_legendary")
def sc_spear_legendary(g):
    name = VERSIONS[g.version][1]
    first = not g.flags.get("spear_clear")
    yield ("msg", f"{name}发出了耀眼的光芒!" if first else f"{name}再次出现在石柱顶端!")
    r = yield ("legendary", name, 47, "spear_clear")
    if r == "caught":
        yield ("msg", f"{name}被平息了……\n天空中恢复了平静。")
    elif r == "win":
        yield ("msg", f"{name}倒下了,然后消失在光芒中……\n(成为冠军后,它似乎还会在这里现身。)")
    elif r == "lose":
        return
    else:
        yield ("msg", f"{name}回到了光芒之中……")
        return
    if first:
        yield ("msg", "小光:太好了……\n天冠山恢复了平静。\n滨海市的道路应该也开通了!")


# ================================================================ 三湖守护者
def _lake(g, species, flag, title):
    if g.flags.get(flag) and (g.flags.get(flag + "_caught") or not g.flags.get("champion")):
        yield ("msg", f"湖面恢复了平静。")
        return
    if g.flags.get(flag):
        yield ("msg", f"湖面再次涌起波澜……\n{title}再次现身了!")
    else:
        yield ("msg", f"{title}静静地注视着你……")
    r = yield ("legendary", species, 50, flag)
    if r == "caught":
        yield ("msg", f"{species}加入了队伍!\n湖面上泛起了温柔的涟漪。")
    elif r == "win":
        yield ("msg", f"{species}沉入了湖底……\n(成为冠军后,它似乎还会在湖底现身。)")


@sc("lake_uxie_verity")
def sc_lake_verity(g):
    yield from _lake(g, "艾姆利多", "lake_emesprit", "掌管感情的艾姆利多")


@sc("lake_azelf")
def sc_lake_azelf(g):
    yield from _lake(g, "亚克诺姆", "lake_azelf", "掌管意志的亚克诺姆")


@sc("lake_uxie")
def sc_lake_uxie(g):
    yield from _lake(g, "由克希", "lake_uxie", "掌管知识的由克希")


# ================================================================ 道馆
GYM_DATA = {
    "roark": (246, "黑金道馆馆主 瓢太", "badge_coal", "煤炭徽章", 76, "beat_gym1",
              "瓢太:我是黑金道馆的瓢太!\n我的岩石队伍坚硬如磐,来吧!",
              "瓢太:好!你的信念比岩石更坚硬!\n煤炭徽章归你了。",
              "瓢太:煤炭徽章能让精灵使出「碎岩」……\n这个招式学习机也拿去吧。"),
    "gardenia": (315, "百代道馆馆主 菜种", "badge_forest", "森林徽章", 86, "beat_gym2",
                 "菜种:我是菜种,最喜欢森林和草系精灵!\n让我看看你和精灵的羁绊!",
                 "菜种:输了……你的羁绊比我的森林更深!\n森林徽章归你了。",
                 "菜种:这个招式学习机是「打草结」。\n对手越重威力越大哦!"),
    "maylene": (317, "帷幕道馆馆主 阿李", "badge_cobble", "圆石徽章", 60, "beat_gym3",
                "阿李:我是阿李!\n用拳头和心灵来对话吧!",
                "阿李:好胜负!你的心灵像圆石一样坚定。\n圆石徽章归你了。",
                "阿李:「吸取拳」能吸取对手的体力。\n收下吧。"),
    "wake": (316, "湿原道馆馆主 吉宪", "badge_fen", "沼泽徽章", 55, "beat_gym4",
             "吉宪:哇哈哈哈!我是吉宪!\n我的水系队伍会让你透不过气!",
             "吉宪:痛快!你赢了我这个大人物!\n沼泽徽章归你了!",
             "吉宪:拿着,「盐水」!\n对手体力越少威力越大。"),
    "fantina": (318, "家缘道馆馆主 梅丽莎", "badge_relic", "遗迹徽章", 65, "beat_gym5",
                "梅丽莎:Bonjour!我是梅丽莎!\n幽灵的舞台开始了!",
                "梅丽莎:C'est fini!你赢得了遗迹徽章!\n太精彩了!",
                "梅丽莎:「暗影爪」是幽灵系的 physical 招式,\n给你了。"),
    "byron": (250, "水脉道馆馆主 东瓜", "badge_mine", "矿山徽章", 91, "beat_gym6",
              "东瓜:嘎哈哈哈!我是东瓜!\n我的钢系宝可梦防御铁壁!",
              "东瓜:好!你的攻击穿透了钢铁!\n矿山徽章归你了!",
              "东瓜:「加农光炮」是钢系的特殊招式。\n去钢铁岛看看吧。"),
    "candice": (319, "雪峰道馆馆主 小菘", "badge_icicle", "冰河徽章", 72, "beat_gym7",
                "小菘:我是小菘! focused and fiery!\n冰系的我要燃起来了!",
                "小菘:focused……你赢了!\n冰河徽章归你了!",
                "小菘:「雪崩」在后出手时威力翻倍。\n收下吧!"),
    "volkner": (320, "滨海道馆馆主 电次", "badge_beacon", "灯塔徽章", 57, "beat_gym8",
                "电次:……你看起来有点意思。\n让我久违地认真一场吧!",
                "电次:……我输了。好久没有这种感觉了。\n灯塔徽章归你了。你一定能成为冠军。",
                "电次:「充电光束」有几率提升特攻。\n北边223号水路通往宝可梦联盟。"),
}


def _gym(g, npc, kind, pre_gate=None):
    key, display, badge, badge_name, tm, beat, intro, win, tm_line = GYM_DATA[kind]
    if g.flags.get(beat):
        yield ("msg", win.split("\n")[0])
        return
    if pre_gate and not pre_gate():
        yield ("msg", pre_gate.text)
        return
    yield ("msg", intro)
    r = yield ("trainer", key, display, 3)
    if r != "win":
        return
    g.flags[beat] = True
    yield ("msg", win)
    yield ("badge", badge)
    yield ("msg", f"(获得了{badge_name}!)")
    yield ("tm", tm)
    yield ("msg", tm_line)


@sc("gym_roark")
def sc_gym_roark(g, npc):
    if not g.flags.get("roark_returned"):
        yield ("msg", "瓢太:馆长现在在黑金炭坑里。")
        return
    yield from _gym(g, npc, "roark")


@sc("gym_gardenia")
def sc_gym_gardenia(g, npc):
    yield from _gym(g, npc, "gardenia")


@sc("gym_maylene")
def sc_gym_maylene(g, npc):
    yield from _gym(g, npc, "maylene")


@sc("gym_wake")
def sc_gym_wake(g, npc):
    yield from _gym(g, npc, "wake")


@sc("gym_fantina")
def sc_gym_fantina(g, npc):
    if g.badge_count() < 4:
        yield ("msg", f"梅丽莎:现在还没有登台的兴致……\n拿到 4 枚徽章再来吧。(目前 {g.badge_count()} 枚)")
        return
    yield from _gym(g, npc, "fantina")


@sc("gym_byron")
def sc_gym_byron(g, npc):
    yield from _gym(g, npc, "byron")


@sc("gym_candice")
def sc_gym_candice(g, npc):
    yield from _gym(g, npc, "candice")


@sc("gym_volkner")
def sc_gym_volkner(g, npc):
    yield from _gym(g, npc, "volkner")


GUIDES = {
    "guide_roark": "向导:瓢太馆长是岩石系!\n水系和草系的招式很有效。\n路上的岩石可以用碎岩打碎。",
    "guide_gardenia": "向导:菜种馆长是草系!\n火系和飞行系占优。\n拉动时钟机关,树篱就会打开。",
    "guide_maylene": "向导:阿李馆长是格斗系!\n飞行系和超能力系克制她。\n地上的箭头会推着你走。",
    "guide_wake": "向导:吉宪馆长是水系!\n电系和草系很有效。\n拉动拉杆可以改变水位。",
    "guide_fantina": "向导:梅丽莎馆长是幽灵系。\n恶系和幽灵系的招式克制她,\n一般系和格斗系招式无效!\n答对算术题才能穿过门。",
    "guide_byron": "向导:东瓜馆长是钢系!\n火系、格斗系和地面系有效。\n踩上平台会传送到别处。",
    "guide_candice": "向导:小菘馆长是冰系!\n火系、格斗系和岩石系克制她。\n冰面上会一直滑到撞墙为止。",
    "guide_volkner": "向导:电次馆长是电系!\n地面系招式克制他,电系招式对他无效。\n拉动拉杆让齿轮转动,桥就会出现。",
}


def _make_guide(name, text):
    @sc(name)
    def _g(g):
        yield ("msg", text)
    return _g


for _name, _text in GUIDES.items():
    _make_guide(_name, _text)


# ================================================================ 算术门(家缘道馆)
@sc("quiz_door_1")
def sc_quiz_door_1(g):
    ow = g._overworld()
    if ow and ow.py < 4:                       # 从馆主一侧往回走:直接放行
        yield ("msg", "你穿过了算术之门,回到了入口一侧。")
        yield ("warp", "hearthome_gym", 3, 5, "down")
        return
    yield ("msg", "算术之门:「3 + 5 × 2 = ?」")
    r = yield ("quiz", "算术之门:「3 + 5 × 2 = ?」", ["13", "16", "10"], 0)
    if r:
        yield ("msg", "回答正确!门打开了。")
        yield ("warp", "hearthome_gym", 3, 3, "up")
    else:
        yield ("msg", "回答错误……被送回了入口。")
        yield ("warp", "hearthome_gym", 7, 9, "up")


@sc("quiz_door_2")
def sc_quiz_door_2(g):
    ow = g._overworld()
    if ow and ow.py < 7:
        yield ("msg", "你穿过了算术之门,回到了入口一侧。")
        yield ("warp", "hearthome_gym", 12, 8, "down")
        return
    r = yield ("quiz", "算术之门:「16 ÷ 4 + 7 = ?」", ["9", "11", "13"], 1)
    if r:
        yield ("msg", "回答正确!门打开了。")
        yield ("warp", "hearthome_gym", 12, 6, "up")
    else:
        yield ("msg", "回答错误……被送回了入口。")
        yield ("warp", "hearthome_gym", 7, 9, "up")


# ================================================================ 大湿地
@sc("marsh_clerk")
def sc_marsh_clerk(g):
    yield ("msg", "大湿地接待员:进入大湿地需要 500 元,\n可以在里面投掷 30 个狩猎球。\n要进入吗?")
    r = yield ("yesno",)
    if r != 0:
        yield ("msg", "接待员:欢迎再来。")
        return
    if g.money < 500:
        yield ("msg", "接待员:钱不够……")
        return
    g.money -= 500
    if not g.flags.get("got_hm_defog"):
        yield ("give", D.item_by_tm(5, hm=True), 1)
        g.flags["got_hm_defog"] = True
        yield ("msg", "(获得了 秘传学习器05「清除浓雾」!)")
    yield ("msg", "(进入了大湿地!)\n在草丛里只能投掷狩猎球,不能对战。")
    yield ("warp", "great_marsh", 11, 17, "up")


# ================================================================ 四天王 & 冠军
E4 = {
    "e4_aaron": (261, "四天王 阿柳", "beat_aaron", "beat_bertha",
                 "阿柳:我是四天王阿柳。\n虫系宝可梦的美丽与强大,让你见识一下!",
                 "阿柳:好……你的实力在虫群之上。\n去吧,下一位是菊野。"),
    "e4_bertha": (262, "四天王 菊野", "beat_bertha", "beat_flint",
                  "菊野:我是菊野。\n大地般厚重的队伍,接得住吗?",
                  "菊野:好年轻人……你踏过了大地。\n下一位,大叶。"),
    "e4_flint": (263, "四天王 大叶", "beat_flint", "beat_lucian",
                 "大叶:我是大叶!燃烧吧,我的火焰!",
                 "大叶:燃尽了……你好样的!\n悟松在等你。"),
    "e4_lucian": (264, "四天王 悟松", "beat_lucian", "beat_champion",
                  "悟松:我是悟松。\n来吧,让我看看你的心灵。",
                  "悟松:……你的心灵超过了我的想象。\n冠军竹兰在等着你。"),
}


def _make_e4(name, key, display, flag, nxt, intro, outro):
    @sc(name)
    def _e4(g):
        if g.flags.get(flag):
            yield ("msg", outro.split("\n")[0])
            return
        yield ("msg", intro)
        r = yield ("trainer", key, display, 3)
        if r != "win":
            return
        g.flags[flag] = True
        yield ("msg", outro)
    return _e4


for _n, _args in E4.items():
    _make_e4(_n, *_args)


@sc("champion_cynthia")
def sc_champion_cynthia(g):
    if g.flags.get("champion"):
        yield ("msg", "竹兰:冠军,又见面了。\n神奥的传说还会继续。")
        return
    yield ("msg", "竹兰:我是竹兰。\n为了这一刻,我和我的伙伴们一直在等待。\n来吧,全力一战!")
    r = yield ("trainer", 267, "冠军 竹兰", 3)
    if r != "win":
        return
    g.flags["beat_champion"] = True
    yield ("msg", "竹兰:……你很强。\n你的伙伴们信任你,你也信任它们。\n这份羁绊,就是冠军的证明。")
    yield ("hall",)
    g.flags["champion"] = True
    yield ("msg", "(你成为了神奥联盟的冠军!\n之后仍可继续冒险,捕捉更多宝可梦。)")
    yield ("credits",)


# ================================================================ 拉杆(道馆机关)
@sc("lever")
def sc_lever(g, npc):
    yield ("msg", "拉杆被拉动了……")
    yield ("toggle", npc["x"], npc["y"])


def all_scripts():
    return SCRIPTS


@sc("canalave_villager")
def sc_canalave_villager(g):
    yield ("msg", "市民:水脉市的图书馆很有名,\n渡船还能去钢铁岛。")


@sc("pastoria_villager")
def sc_pastoria_villager(g):
    yield ("msg", "村民:大湿地里能遇到\n外面见不到的宝可梦哦。")


# ================================================================ 银河队:百代基地 / 帷幕仓库 / 总部
def _grunt(g, key, flag, intro, outro, extra_flags=()):
    yield ("msg", intro)
    r = yield ("trainer", key)
    if r != "win":
        return
    g.flags[flag] = True
    for f in extra_flags:
        g.flags[f] = True
    yield ("msg", outro)
    yield ("hide",)


@sc("galactic_et_1")
def sc_galactic_et_1(g):
    yield from _grunt(g, 410, "beat_410", "银河队手下:这里是银河队百代基地!\n想进去先过我这关!",
                       "银河队手下:呜……岁星大人会替我报仇的!")


@sc("galactic_et_2")
def sc_galactic_et_2(g):
    yield from _grunt(g, 412, "beat_412", "银河队手下:别想再往前一步!",
                       "银河队手下:可恶……")


@sc("jupiter_eterna")
def sc_jupiter_eterna(g):
    if g.flags.get("eterna_galactic_clear"):
        return
    yield ("msg", "岁星:呵呵,你就是那个在发电厂捣乱的小鬼?\n银河队干部岁星,让我看看你的本事。")
    r = yield ("trainer", 406, "银河队干部 岁星", 3)
    if r != "win":
        return
    g.flags["eterna_galactic_clear"] = True
    yield ("msg", "岁星:哼,算你厉害。\n不过百代市已经没有我们需要的东西了,撤!")
    yield ("hide",)
    yield ("msg", "(银河队离开了百代市。\n自行车店的店主应该会感谢你。)")


@sc("galactic_wh_1")
def sc_galactic_wh_1(g):
    yield from _grunt(g, 835, "beat_835", "银河队手下:仓库重地,闲人免进!",
                       "银河队手下:呜……二号的伙计会收拾你的!")


@sc("galactic_wh_2")
def sc_galactic_wh_2(g):
    yield from _grunt(g, 836, "beat_836", "银河队手下:你打败了我的搭档?\n那就别想活着走出去!",
                       "银河队手下:怎么可能……\n秘传学习器也随你吧!",
                       extra_flags=("warehouse_clear",))


@sc("galactic_hq_1")
def sc_galactic_hq_1(g):
    yield from _grunt(g, 509, "beat_509", "银河队手下:这里是银河队总部!\n只有拿到 7 枚徽章的训练家才配进来!",
                       "银河队手下:竟然……")


@sc("galactic_hq_2")
def sc_galactic_hq_2(g):
    yield from _grunt(g, 510, "beat_510", "银河队手下:老大正在天冠山准备仪式!\n不会让你碍事的!",
                       "银河队手下:可恶……镇星大人!")


@sc("galactic_hq_3")
def sc_galactic_hq_3(g):
    yield from _grunt(g, 512, "beat_512", "银河队手下:站住!\n银河队的计划不容妨碍!",
                       "银河队手下:计划……才不会因此结束……")


@sc("saturn_hq")
def sc_saturn_hq(g):
    if g.flags.get("hq_clear"):
        return
    yield ("msg", "镇星:我是银河队干部镇星。\n老大已经前往枪之柱,\n想追上去,先过我这关!")
    r = yield ("trainer", 408, "银河队干部 镇星", 3)
    if r != "win":
        return
    g.flags["hq_clear"] = True
    yield ("msg", "镇星:……你赢了。\n枪之柱就在天冠山顶。\n去亲眼看看银河队的计划吧。")
    yield ("hide",)
    yield ("msg", "(银河队总部安静了下来。\n接下来去天冠山顶的枪之柱。)")
