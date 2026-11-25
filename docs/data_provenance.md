# 数据来源与重建说明

本项目的所有数值数据都由 `tools/gen_sinnoh_data.py` 生成到 `src/data_*.py`,不依赖网络运行游戏。
重建命令:

```bash
python3 tools/fetch_sinnoh_sources.py    # 抓取原始数据到 /tmp/pkdp(约 20 MB + PokeAPI 查询)
python3 tools/gen_sinnoh_data.py         # 重新生成 src/data_{dex,moves,items,trainers,encounters}.py
```

## 原始输入

| 文件 | 来源 | 用途 |
|---|---|---|
| `pd/files/poketool/personal/personal.json` | pret/pokediamond | 种族值、属性、捕获率、经验产量、成长曲线、性别比例、TM/HM 兼容 |
| `pd/files/poketool/personal/wotbl.json` | 同上 | 钻石/珍珠 升级招式表 |
| `pd/files/poketool/personal/evo.json` | 同上 | 进化方式(等级/石头/通讯/亲密度/地点/同队) |
| `pd/files/poketool/personal/growtbl.json` | 同上 | 6 条官方经验曲线 |
| `pd/files/poketool/waza/waza_tbl.json` | 同上 | 467 个招式的第四世代属性/分类/威力/命中/PP/优先度/效果 |
| `pd/files/poketool/trainer/trdata.json` | 同上 | 849 名训练家的职业/姓名/队伍/招式/携带物/伤药 |
| `pd/files/fielddata/encountdata/{d,p}_enc_data/*.bin` | 同上 | 钻石/珍珠各 183 张 NARC 遭遇表 |
| `pd/files/itemtool/itemdata/item_data.json` | 同上 | 道具价格/分类/效果 |
| `pd/arm9/src/itemtool.c` | 同上 | TM01-92 / HM01-08 → 招式表 |
| `pd/include/constants/*.h` | 同上 | 枚举编号 ↔ 标识符 |
| `xz_text/*.json` | Xzonn/PokemonChineseTranslationRevise | 官方简中名(精灵/招式/道具/训练家/地名/道馆/属性) |
| `move_names.csv` `pokemon_species_names.csv` | PokeAPI | 官方简中名(优先于汉化文本) |
| `pokemon.csv` | PokeAPI | 体重 |
| `sinnoh_encounters.json` | PokeAPI location-area | 把二进制遭遇表对齐到具体道路 |

## 遭遇表二进制格式(每文件 106 个 u32)

```
[0]     行走遇敌率           [1..24]  草丛 12 槽 × (等级, 种类)
[25..50] 宝可追踪/双插槽等(未使用)
[51]    冲浪率  [52..61]  冲浪 5 槽 × (等级打包 min<<8|max, 种类)
[62]    碎岩率  [63..72]  碎岩 5 槽
[73]    破旧钓竿率 [74..83]  5 槽
[84]    好钓竿率 [85..94]  5 槽
[95]    厉害钓竿率 [96..105] 5 槽
```
草丛槽权重 20/20/10/10/10/10/5/5/5/4/4/1,水与钓竿 60/30/5/4/1。

## 处理规则

- 招式:引擎无法表达的变化招(替身/双倍奉还/接棒等 88 个)从数据中剔除;伤害招式的次要效果映射为
  引擎效果标记(见 `gen_sinnoh_data.py` 的 `EFFECT_FX`),其余按纯伤害处理
- 进化:通讯进化用「连线电缆」、美丽度用「美丽鳞片」替代;昼夜亲密度进化用日之石/月之石替代
- 道具:只保留引擎支持的球/药品/学习机/进化道具/重要道具;道具编号以 `items.h` 为准
- 名称:仅采用官方译名(名称不受版权保护),对白为本项目原创
