# 宝可梦 钻石·珍珠 · 神奥地区复刻

用 **Python + Pygame** 从零实现的《宝可梦 钻石/珍珠》神奥地区复刻:
**8 个道馆 → 四天王 → 冠军竹兰** 的完整流程,外加劲敌五战、银河队事件与可捕捉的传说宝可梦。
机制按第四世代公式复刻;精灵/招式/训练家/遭遇表数值来自反编译工程的原作数据,
官方简中译名,像素美术为程序生成或可选的官方风格素材(见下文)。

## 快速开始

```bash
python3 -m pip install pygame numpy      # macOS 镜像: -i https://pypi.tuna.tsinghua.edu.cn/simple
python3 main.py
```

首次进入选「新的冒险」→ 选择 **钻石 / 珍珠** 版本(决定专属精灵与枪之柱的传说宝可梦:
帝牙卢卡 / 帕路奇亚),在真砂镇研究所从山梨博士处领取草苗龟 / 小火焰猴 / 波加曼。

按键按 Nintendo Switch / DS 手柄的菱形布局放在右手 **U I J K** 上(与原作《钻石/珍珠》的 A/B/X/Y 一致):

| 键 | 手柄键 | 作用 |
|---|---|---|
| **I** | A | 确定 · 对话 · 调查(面对岩石/树丛/水面使用秘传招式) |
| **K** | B | 取消 · 返回 · 收起菜单;**按住跑步**(是/否选择里按 B = 选「否」) |
| **U** | X | 打开菜单(精灵 / 背包 / 徽章 / 飞翔 / 存档),再按一次收起 |
| **J** | Y | 快捷打开背包(战斗中也是背包) |
| 方向键 / WASD | 十字键 | 移动 · 光标 |

兼容旧键:Z / 空格 / 回车 = A,X / Esc = B,回车在野外 = 菜单,Shift 或字母 B 按住 = 跑步(测试与 RL 环境仍在用)。
按键映射集中定义在 `src/keys.py`。

## 游戏流程(忠实原作顺序)

| # | 地点 | 馆主 | 属性 | 队伍等级 | 徽章 / 奖励 |
|---|---|---|---|---|---|
| 1 | 黑金市 | 瓢太 | 岩石 | 12 / 12 / 14 | 煤炭徽章 / TM76 隐形岩 |
| 2 | 百代市 | 菜种 | 草 | 19 / 19 / 22 | 森林徽章 / TM86 打草结 |
| 3 | 帷幕市 | 阿李 | 格斗 | 27 / 27 / 30 | 圆石徽章 / TM60 吸取拳 |
| 4 | 湿原市 | 吉宪 | 水 | 27 / 27 / 30 | 沼泽徽章 / TM55 盐水 |
| 5 | 家缘市 | 梅丽莎 | 幽灵 | 32 / 34 / 36 | 遗迹徽章 / TM65 暗影爪(需 4 枚徽章后她才归来) |
| 6 | 水脉市 | 东瓜 | 钢 | 36 / 36 / 39 | 矿山徽章 / TM91 加农光炮 |
| 7 | 雪峰市 | 小菘 | 冰 | 38 / 38 / 40 / 42 | 冰河徽章 / TM72 雪崩 |
| 8 | 滨海市 | 电次 | 电 | 46 / 47 / 47 / 49 | 灯塔徽章 / TM57 充电光束 |
| E4 | 宝可梦联盟 | 阿柳 → 菊野 → 大叶 → 悟松 | 虫 / 地面 / 火 / 超能力 | 53~63 | — |
| 冠军 | 冠军之间 | 竹兰 | 混合 | 60~66(烈咬陆鲨 Lv66) | 名人堂 |

- **道馆机关**:碎岩开路、树篱 + 时钟拉杆、箭头滑块、水位拉杆、算术之门、移动平台、冰面滑行、齿轮拉杆
- **剧情**:劲敌帕尔 5 战;银河队:谷间发电厂(伙星)→ 百代基地 → 神和镇(赤日)→ 枪之柱(赤日 + 神兽);
  三湖守护者(由克希 / 艾姆利多 / 亚克诺姆)在枪之柱事件后可捕捉
- **秘传招式地图使用**:居合劈(百代森林)· 飞翔(帷幕仓库)· 冲浪(神和镇)· 怪力(丧失塔)· 碎岩(黑金炭坑)· 攀瀑(滨海市)
- **原作数值**:30 条道路的野生表(钻石/珍珠各一套)、二进制遭遇表解码、训练家队伍/招式/携带树果/伤药
- 成为冠军后可继续游玩,雪峰市船夫可前往战斗区(225~230 号道路,Lv 50+)

## 已实现系统

格子移动/碰撞/门传送、**冲浪**/攀瀑/碎岩/居合劈/怪力推石/钓鱼、冰面与箭头滑行、拉杆机关、
训练家视线触发、道具球、商店(按城镇进货,帷幕百货卖学习机,滨海市场卖进化石)、精灵中心、
黑屏回最近中心、飞翔、徽章盒、**TM/HM 教学**、进化石/通讯/亲密度/地点/同队进化、
回合制战斗(18 系克制、物/特分伤、STAB、暴击、命中等级、优先度、畏缩、混乱、
中毒/剧毒/灼伤/麻痹/睡眠/冻结、能力等级、天气、光墙/反射壁、神秘守护、撒菱/隐形岩/毒菱、
寄生种子/扎根/水流环、守住、蓄力、固定/可变威力、连续攻击、一击必杀、树果、训练家伤药)、
第四世代伤害/经验/捕获公式、学习装置、多种精灵球(先机/计时/黑暗/捕网/巢穴/重复/治愈/大师)、
大湿地(狩猎球模式)、6 只队伍 + PC、存读档、**名人堂 + 制作人员名单**。

## 项目结构

```
main.py                   入口(python3 main.py,SMOKE 无头 240 帧)
src/
  data.py                 属性克制表 + 数据访问层(合并下面生成的数据)
  data_dex.py             全国图鉴 493(生成):种族值/属性/捕获率/成长/体重/升级招式/进化/TM 兼容
  data_moves.py           第四世代 467 招式(生成):属性/分类/威力/命中/PP/优先度 + 引擎效果标记
  data_items.py           道具(生成):精灵球/药品/学习机/进化道具/重要道具,TM/HM → 招式
  data_trainers.py        849 名训练家(生成):职业/姓名/队伍/招式/携带物/伤药/奖金
  data_encounters.py      144 个区域 × 钻石/珍珠 的草丛/冲浪/碎岩/钓竿遭遇表(生成)
  mon.py                  精灵实例:能力值、经验/进化、伤害、捕获
  battle.py               战斗引擎(协程流程、效果系统、原作式评分 AI、训练家道具)
  overworld.py            大地图:移动/滑行/秘传/钓鱼/视线/脚本/菜单/名人堂
  world/                  神奥地图包: towns / routes / dungeons / gyms / league / interiors / scripts
  keys.py                 按键映射(UIJK = Switch 的 X/A/Y/B,兼容 Z/X/回车)
  ui.py / art.py / title.py / game.py
tools/
  fetch_sinnoh_sources.py 抓取原始数据到 /tmp/pkdp(pokediamond 稀疏克隆 + Xzonn 中文文本 + PokeAPI)
  gen_sinnoh_data.py      重新生成 src/data_*.py
  sim_progression.py      等级曲线模拟(--exp 解析估算 / 默认真实战斗)
  fetch_all_sprites.py    官方第四世代贴图(正面/背面/图标,gitignore)
  import_essentials_assets.py  人物行走图 + 图块集(gitignore)
  screenshot_demo.py      关键场景截图 → /tmp/screens/
  run_random_agent.py / train_ppo.py   强化学习环境基线
tests/
  world_test.py           世界数据:传送/坐标/脚本/连通性/道馆可解性
  smoke_test.py           数据 + 机制 + 战斗 + 大地图 + **剧情全流程(8 道馆 → 四天王 → 冠军)** + 渲染
```

## 测试

```bash
python3 tests/world_test.py     # 4100+ 项:地图/传送/NPC/脚本/连通性/道馆机关
python3 tests/smoke_test.py     # 14700+ 项:含自动打完全部 8 道馆、四天王、冠军
python3 tools/sim_progression.py --exp 15   # 查看等级曲线估算
```

## 数据来源(重要)

| 内容 | 来源 | 说明 |
|---|---|---|
| 精灵/招式/进化/成长/训练家/道具/遭遇表数值 | [pret/pokediamond](https://github.com/pret/pokediamond) 反编译工程(`files/poketool/*`、`files/fielddata/encountdata/*`、`arm9/src/itemtool.c`) | 由 `tools/gen_sinnoh_data.py` 编译进 `src/data_*.py`;遭遇表为 NARC 二进制解码(106 个 u32:行走率 + 12 草丛槽 + 雷达段 + 冲浪/碎岩/三钓竿各 5 槽) |
| 官方简中译名 | [Xzonn/PokemonChineseTranslationRevise](https://github.com/Xzonn/PokemonChineseTranslationRevise)(CC BY-NC-SA 3.0)+ PokeAPI | **仅采用名称**(精灵/招式/道具/训练家/地名/道馆);对白为本项目原创 |
| 体重/区域对齐 | [PokeAPI](https://pokeapi.co) | `pokemon.csv`、`location-area` |
| 精灵贴图(可选) | [PokeAPI/sprites](https://github.com/PokeAPI/sprites) 第四世代画风 | `assets/mons/`,`python3 tools/fetch_all_sprites.py --backs` |
| 人物行走图 / 图块集(可选) | Essentials 素材镜像(rh-hideout-chinese/pokemon-engine) | `assets/chars/`、`assets/src/`,`python3 tools/import_essentials_assets.py` |

- 全部素材已加入 `.gitignore`,不会提交或分发;删除 `assets/` 即回退到程序生成的原创像素画
- 宝可梦版权归 Nintendo / Creatures / GAME FREAK 所有,本项目仅供个人学习,**请勿公开分发整合后的游戏**
- 对白为原创改写,不含汉化补丁文本;重建数据:`python3 tools/fetch_sinnoh_sources.py && python3 tools/gen_sinnoh_data.py`

## 强化学习环境

`envs/pokemon_env.py` 暴露 Gym 风格接口(7 个离散动作、降采样画面 + 状态向量、探索奖励),
观测含徽章数/8,episode 在获得徽章时 terminated。`python3 tools/run_random_agent.py 2000` 为随机基线。

## 后续可做

特性/道具持有/天气延长 · 双打 · 宝可表/华丽大赛 · 图鉴 UI · 音效 BGM · 更大的原作比例地图
