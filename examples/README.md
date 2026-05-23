# Examples / 案例

English | 中文

These examples are compact public case notes. Preview files are review artifacts only; they are not reusable source art.

这些案例用于展示成熟工作流。预览图只用于说明效果，不是可复用的生产源素材。

## Static Mature Case / 静态成熟案例

Project: `xiaojingling-gemin-magic-stickers`

项目：`xiaojingling-gemin-magic-stickers`

![Xiaojingling Gemin magic static stickers](previews/xiaojingling-gemin-magic-static-preview.jpg)

English summary:

- Type: static 24-pack.
- Character: fluffy white puppy mascot Xiao Jingling Gemin.
- Theme: playful magical daily reactions.
- Workflow: one image-generated creative source per sticker, then deterministic postprocessing for WeChat sizing, thumbnails, metadata, banner, reward assets, preview, and QC.
- Why it is a good reference: strong subject scale, clear text plaques, consistent character identity, varied poses, and full album asset coverage.

中文总结：

- 类型：静态 24 张表情包。
- 角色：奶油白毛绒小狗“小精灵 Gemin”。
- 主题：魔性日常反应。
- 流程：每张表情先生成独立原创图，再用确定性脚本处理微信尺寸、缩略图、元数据、banner、赞赏图、预览图和 QC。
- 参考价值：主体比例足、文字牌清晰、角色一致、姿势差异明显，并包含完整专辑素材。

Prompt shape / 提示词结构：

```text
Use $generate-wechat-stickers to create a static 24-pack WeChat sticker album.
Character: fluffy white puppy named Xiao Jingling Gemin.
Theme: playful magic daily reactions.
Style: cute, expressive, high-readability Chinese sticker text.
Include cover, icon, banner, reward guide, reward thanks, metadata, preview, and QC.
```

```text
使用 $generate-wechat-stickers 生成一套 24 张静态微信表情包。
角色：奶油白毛绒小狗小精灵 Gemin。
主题：魔性日常反应。
风格：可爱、表情夸张、中文文字清晰、主体比例大。
包含封面、icon、banner、赞赏引导图、赞赏致谢图、metadata、预览图和 QC。
```

## Animated Mature Case / 动态成熟案例

Project: `xiaojingling-gemin-game-8-animated-20260521`

项目：`xiaojingling-gemin-game-8-animated-20260521`

Pack preview / 整包预览：

![Xiaojingling Gemin game animated stickers](previews/xiaojingling-gemin-game-animated-preview.jpg)

Single GIF sample / 单张动态 GIF 示例：

![Xiaojingling Gemin game animated sample](previews/xiaojingling-gemin-game-animated-01.gif)

English summary:

- Type: animated 16-pack.
- Character: fluffy white puppy mascot Xiao Jingling Gemin.
- Theme: gaming / squad chat reactions.
- Workflow: generated first/last frame inputs, Seedance video task per sticker, MP4 download, green-screen keying, transparent GIF export, thumbnails, metadata, preview, and QC.
- Why it is a good reference: it records the actual video source chain instead of faking animation from a local still cutout.
- Key manifest fields: `creative_source: seedance_video`, `animated_source_mode: green_screen_video`, `video_input_mode: first_last_frame`, `video_source_path`, `video_task_report_path`, `frame_sample_count`.

中文总结：

- 类型：动态 16 张表情包。
- 角色：奶油白毛绒小狗“小精灵 Gemin”。
- 主题：开黑/游戏嘴替。
- 流程：生成首尾帧，逐张提交 Seedance 视频任务，下载 MP4，绿幕抠像，导出透明 GIF，生成缩略图、metadata、预览图和 QC。
- 参考价值：它记录了真实视频生产链路，而不是从一张本地抠图做假动效。
- 核心 manifest 字段：`creative_source: seedance_video`、`animated_source_mode: green_screen_video`、`video_input_mode: first_last_frame`、`video_source_path`、`video_task_report_path`、`frame_sample_count`。

Prompt shape / 提示词结构：

```text
Use $generate-wechat-stickers to create an animated 16-pack WeChat sticker album.
Character: fluffy white puppy named Xiao Jingling Gemin.
Theme: gaming reactions and squad chat.
Mode: transparent GIF, Seedance first-last-frame video route.
Make one pilot first. Do not fall back to sprite sheet or local still loop without approval.
```

```text
使用 $generate-wechat-stickers 生成一套 16 张动态微信表情包。
角色：奶油白毛绒小狗小精灵 Gemin。
主题：开黑/游戏嘴替。
模式：透明 GIF，走 Seedance 首尾帧视频路线。
先做 1 个 pilot。没有明确批准，不要退回 sprite sheet 或本地静态循环。
```

## Additional Historical Examples / 其他历史案例

### Static Case: Gemin Workplace 24-Pack / 静态：Gemin 职场嘴替 24 张

![Gemin workplace static 24-pack](previews/gemin-workplace-static-24-preview.jpg)

- EN: Strong static workflow reference with production QC `ok: true`, `0 failed`.
- 中文：静态流程参考案例，生产 QC 为 `ok: true`，`0 failed`。

### Animated Draft Case: Fitness 16-Pack / 动态草稿：健身主题 16 张

![Gemin fitness animated draft](previews/gemin-fitness-animated-draft-preview.jpg)

- EN: Useful draft example showing why draft review and submission-ready QC must stay separate.
- 中文：动态草稿案例，用来说明“预览审核”和“提交版 QC”必须分开。

## What These Examples Are Not / 这些案例不是什么

- EN: They are not reusable source art.
- 中文：它们不是可复用源素材。
- EN: They are not a promise that every future pack will pass QC on the first try.
- 中文：它们不代表未来每套表情都能一次通过 QC。
- EN: They should not be used to build new stickers by cropping, copying, or tracing.
- 中文：不要通过裁剪、复制、描摹这些案例来生成新表情。
- EN: They are workflow references for planning, generation, review, and delivery gates.
- 中文：它们是计划、生成、审核和交付门禁的流程参考。
