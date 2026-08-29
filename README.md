# 星钻精灵 · Stardrop Monsters

一个用 **Python + Pygame** 从零实现的宝可梦**珍珠·钻石**风格致敬 Demo。
战斗/捕获等核心机制按第四世代公式复刻,精灵、像素美术、地图均为原创或代码生成,
不包含任何官方版权素材(支持自行下载官方图替换,见下文)。

## 快速开始

```bash
python3 -m pip install pygame numpy      # macOS 镜像: -i https://pypi.tuna.tsinghua.edu.cn/simple
python3 main.py
```

## 操作

| 按键 | 作用 |
|---|---|
| 方向键 / WASD | 移动 · 光标 |
| Z / 空格 | 确认 · 对话 · 调查 |
| X / 回车 | 取消 · 打开菜单 |
| Esc | 关闭菜单/界面 |

## 游戏流程(垂直切片)

1. 开场后前往**研究所**,与榆木博士对话,从草/火/水三只初始精灵中选择伙伴(获得精灵球×5、伤药×3)
2. 北上**1号道路**:草丛遇敌(麻雀雏/啮齿鼠/电鼠/小岩蛇)、与短裤少年对战
3. 尽头的**磐石道馆**挑战馆长岩间(小岩蛇 Lv12 + 岩铠兽 Lv14)
4. 胜利获得**岩石徽章** —— Demo 目标达成,可继续练级/捕捉/进化

已实现系统:格子移动与碰撞、门传送、草丛随机遇敌、四方向行走 NPC、
对话/选择支脚本、回合制战斗(18 系属性克制、物理/特殊分伤、STAB、暴击、命中、优先度、
中毒/灼伤/麻痹/睡眠、能力等级)、第四世代**伤害公式**与**捕获率公式**、
等级/经验/升级学招/进化、背包(伤药/好伤药/全复药/解毒药/三种球)、
6 只队伍 + PC 存储、换人/逃跑(世代四公式)、存档读档、黑屏回家、队伍整理。

## 项目结构

```
main.py               入口(python3 main.py,--headless 无头模式)
src/
  settings.py         常量与配色(窗口 960x624,3 倍像素)
  data.py             属性克制表 / 25 个招式 / 11 只精灵 / 道具 / 经验曲线
  mon.py              精灵实例:能力值、伤害、捕获(第四世代公式)
  art_data.py         原创精灵 16x16 像素矩阵
  art.py              图块/人物程序化生成 + 外部素材覆盖接口
  worldmap.py         5 张地图(小镇/道路/自宅/研究所/道馆)+ NPC + 对话脚本
  overworld.py        世界场景:移动/遇敌/交互/菜单/初始选择
  battle.py           战斗场景(协程驱动流程)
  ui.py               中文字体/文本框/队伍/背包界面
  title.py / game.py  标题、场景栈、存档
envs/pokemon_env.py   Gym 风格强化学习环境
tools/
  render_art.py       美术自检图(精灵/人物/图块 contact sheet)
  screenshot_demo.py  关键场景截图
  run_random_agent.py 随机基线智能体
  train_ppo.py        Stable Baselines3 PPO 训练(可选)
tests/smoke_test.py   无头冒烟测试(200+ 项断言)
```

## 测试

```bash
python3 tests/smoke_test.py     # 数据校验 + 战斗/捕捉/存档/渲染,共 206 项断言
```

## 强化学习环境(参考 PokemonRedExperiments)

设计借鉴 [PWhiddy/PokemonRedExperiments](https://github.com/PWhiddy/PokemonRedExperiments)(MIT,
用强化学习玩宝可梦红)的核心思路,但无需模拟器——游戏本身就是 Python 对象:

| PokemonRedExperiments | 本项目 |
|---|---|
| PyBoy 模拟器 + 读 RAM | 直接读游戏对象状态 |
| 手柄离散动作(↑↓←→ A B START) | 相同的 7 个离散动作,帧跳执行 |
| V2 坐标探索奖励 | 相同:新格子 +0.5 / 重访衰减 / 等级·捕捉·徽章奖励 / 步数惩罚 |
| TensorBoard + 直播地图 | TensorBoard(可选)+ 探索热力图 PNG |

```bash
# 随机基线(无需任何 RL 依赖)
python3 tools/run_random_agent.py 2000

# PPO 训练(可选依赖)
python3 -m pip install stable-baselines3 torch tensorboard
python3 tools/train_ppo.py 100000     # 训练
python3 tools/train_ppo.py play       # 回放训练好的模型
```

观测 = 降采样画面(78x120x3 uint8)+ 状态向量(位置/地图/HP/等级/徽章/球数/进度),
安装 gymnasium 后自动暴露标准 spaces;episode 在获得徽章时 terminated。
随机基线几乎原地打转(与原项目现象一致),需要 PPO + 探索奖励才能学会
出门 → 选精灵 → 练级 → 打道馆的完整流程。

## 素材说明(重要)

为贴近原作观感,游戏使用官方风格素材(均通过公开 GitHub 仓库获取,已加入
`.gitignore`,不会提交/分发,仅供个人本地学习试玩):

| 内容 | 来源 | 位置 |
|---|---|---|
| 精灵战斗图(正面/背面/图标) | [PokeAPI/sprites](https://github.com/PokeAPI/sprites) 第四世代钻石珍珠画风 | `assets/mons/` |
| 人物行走图(主角/博士/馆主/少年/村民) | Essentials 素材镜像(rh-hideout-chinese/pokemon-engine)`Graphics/Characters` | `assets/chars/` |
| 户外/室内/道馆图块集、门 | 同上 `Graphics/Tilesets`(Outside / Interior general / Gyms interior)+ `Graphics/Characters/doors1` | `assets/src/` |

重建/补全素材:

```bash
python3 tools/fetch_official_sprites.py      # 精灵图(自动镜像重试)
python3 tools/import_essentials_assets.py    # 人物+图块(缓存于 /tmp/ess_src 时直接复用)
```

- 图块替换坐标表在 `src/art.py` 的 `TILE_FROM_SHEET`(32px 块 + 子砖模式,人工目视挑选)
- 精灵图与名称版权归 Nintendo / Creatures / Game Freak 所有,**请勿公开分发整合后的游戏**
- 删除 `assets/` 下对应目录即回退到内置原创像素画(可自由分发)
- 没有找到官方对应的零散部件(告示牌/床)保留程序生成

## 后续路线

- 更多地图/剧情/训练家(道馆战 AI 已支持多只轮换)
- 特性/道具效果/天气
- 图鉴 UI
- 音效与 BGM
- RL:课程学习起点(类似原项目的 .state 存档)、对战脚本智能体
