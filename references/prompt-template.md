# 生图提示词模板（小鹿版）

每张图单独生成，走脚本管线（`scripts/xiaolu_gen.py` + ARK Seedream + 标准像垫图），不要把多张图拼在一起。

脚本里已锁死 STYLE_PROMPT（风格 DNA + 小鹿角色描述 + 配色 + 约束），调用时只需要填内容变量。

## 调用模板

```bash
PYTHONUTF8=1 ARK_API_KEY=<key> python scripts/xiaolu_gen.py \
  --topic "{配图主题}" \
  --structure "{结构类型：Workflow/系统局部/前后对比/角色状态/概念隐喻/方法分层/地图路线/小漫画分镜}" \
  --core-idea "{这张图要表达的核心意思}" \
  --composition "{CHAR_LOCK 前缀}+{具体画面：小鹿在哪里、正在做什么、主要物件、信息如何流动}" \
  --elements "{元素1} / {元素2} / {元素3}" \
  --labels "{标注1} / {标注2} / {标注3}" \
  --ref-image "<skill>/assets/小鹿-标准像-v1.png"
```

## CHAR_LOCK 角色锁定前缀（composition 开头必带）

```text
画面主角必须严格保持参考图中小鹿角色的全部外形：
幼年梅花小鹿、奶呼呼短幼体型、紫底白星星睡帽、紫色睡衣粉色蕾丝包边、
鹿角粉色蝴蝶结、爱心腮红、圆黑豆豆眼，
三点白只能画在鼻梁上（鼻子正上方、两眼之间），额头必须保持纯棕色、
绝对不能在额头上画任何白点，全脸白点总数不超过3个，
角色长相与参考图完全一致，只改变动作和场景。
小鹿用双手专注参与核心动作，不强塞弯月抱枕。
小鹿身体后方绝对不能画出尾巴。
整体油画棒蜡笔肌理、低饱和马卡龙配色、浅奶油色背景、大量留白。
```

## 批量生成

参照项目 `scripts/batch_examples.py` 的模式：

- 复用 `xiaolu_gen.py` 的 `gen_one`（PYTHONPATH 指向 scripts 目录）
- 每张 concept 定义 topic/structure/core-idea/composition/elements/labels
- composition 统一拼 CHAR_LOCK 前缀
- 支持按编号重跑单张（哪张不满意补哪张，不整套重来）
- 后台运行，逐张落盘到 `assets/<批次名>/`

## 局部修正提示

某张图角色特征跑偏时，重跑该张并在 composition 里针对性加强约束（见 `xiaolu-ip.md` 的陷阱对照表）。重跑 1-2 次仍压不住的顽固细节（如额头白点），改用 PIL 后处理直接修掉——确定性操作，100% 可控。
