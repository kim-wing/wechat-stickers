# WeChat Stickers / 微信表情包生成 Skill

根据角色、主题或参考图生成整套微信表情包，支持静态 PNG 和图像连续帧 GIF，以及封面、图标、专辑素材、元数据、预览和质量检查。

## 当前流程

- 静态：逐张生成原创图片，处理尺寸和透明度。
- 动态：生成同一动作的时序帧表，切帧、统一缩放、编码 GIF。
- 优先原生透明 PNG，保留 alpha；旧洋红素材仍可去色处理。
- 整套专辑默认生成封面、图标、横幅、赞赏引导图和赞赏感谢图；只有用户明确要求才省略赞赏图。
- 先验证试样再批量生产，保留来源和失败报告，最终打包前重跑 QC。

不再提供视频生成、视频转 GIF 或相关服务配置。旧项目文件不会被转换成连续帧来源；使用旧版本维护历史任务，或重新生成有来源记录的帧表。

## 安装

```bash
git clone https://github.com/kim-wing/wechat-stickers.git ~/.codex/skills/wechat-stickers
python3 -m pip install -r ~/.codex/skills/wechat-stickers/requirements.txt
```

需要可用的图像生成工具和 Python/Pillow。模型名称和实际能力以运行环境为准。

## 使用

向 Agent 提供角色或参考图、主题、数量和静态/动态要求。支持单张及 8/16/24 张专辑。

在 Skill 目录执行：

```bash
python3 scripts/run_wechat_sticker_pipeline.py init --output-dir /absolute/job --pack-name "工作中" --count 1 --motion animated
```

填写计划、生成并检查原图，记录 `sheet_source_path`、`candidate_id` 和 `visual_review` 后：

```bash
python3 scripts/run_wechat_sticker_pipeline.py process-sheets --plan /absolute/job/sticker-plan.json
python3 scripts/run_wechat_sticker_pipeline.py qc --plan /absolute/job/sticker-plan.json
```

检查实际播放后用 `package` 打包。完整规则见 [SKILL.md](SKILL.md) 和 [连续帧流程](references/sequential-frames.md)。

最新更新：[原生透明 PNG、移除视频备选与赞赏图修复](docs/native-alpha-and-album-assets-update.md)。

## 验证与更新记录

```bash
python3 -m unittest discover -s tests -v
```

[连续帧改造记录](docs/frame-first-update-2026-09-10.md)保留当时的测试结果；其中可选视频路线已在后续更新中移除。

## License

[MIT](LICENSE)
