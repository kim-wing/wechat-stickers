# Seedance / Volcengine Ark Setup

English | 中文

This skill uses Volcengine Ark's video generation API for high-quality animated WeChat stickers.

这个 Skill 使用火山方舟视频生成 API 来制作高质量动态微信表情。

Default model policy / 默认模型策略：

- EN: Use Doubao Seedance 1.5 Pro for animated sticker video generation.
- 中文：动态表情默认使用豆包 Seedance 1.5 Pro。
- EN: Prefer first-last-frame image-to-video.
- 中文：优先使用首尾帧图生视频。
- EN: Generate silent videos with `generate_audio: false`.
- 中文：生成无声视频，设置 `generate_audio: false`。
- EN: Disable watermark with `watermark: false`.
- 中文：关闭水印，设置 `watermark: false`。
- EN: Read the API key from `ARK_API_KEY`.
- 中文：从环境变量 `ARK_API_KEY` 读取 API Key。

## 1. Create Or Log In To A Volcengine Account / 创建或登录火山引擎账号

Ark product page / 火山方舟产品页：

https://www.volcengine.com/product/ark

EN: The product page advertises trial/free benefits and links to the Ark console. Free quota and resource-package policies can change, so always check the official pages before planning a large batch.

中文：产品页会展示试用、免费额度或资源包入口，并提供方舟控制台入口。免费额度和资源包政策会变化，批量生成前请以官方页面和控制台为准。

## 2. Check Free Quota Or Resource Package Availability / 查看免费额度或资源包

Official pages / 官方页面：

- Free inference quota / 免费推理额度：https://www.volcengine.com/docs/82379/1399514
- Seedance resource package rules / Seedance 资源包规则：https://www.volcengine.com/docs/82379/2191775
- Model pricing / product page / 模型计费与产品页：https://www.volcengine.com/product/ark

Important notes / 注意事项：

- EN: Free quota is account-, project-, model-, region-, and campaign-dependent.
- 中文：免费额度可能与账号、项目、模型、地域和活动有关。
- EN: Some video models or packages may require opening the service, topping up, buying a package, or meeting account conditions.
- 中文：部分视频模型或资源包可能需要开通服务、充值、购买资源包或满足账号条件。
- EN: This repository cannot guarantee free Seedance availability. Treat the official console as the source of truth.
- 中文：本仓库不能保证任何账号都能免费使用 Seedance，请以火山方舟控制台为准。

## 3. Open The Seedance Model / 开通 Seedance 模型

In the Ark console / 在方舟控制台中：

1. EN: Choose the `cn-beijing` Ark region if you are using the default endpoint in this skill.
   中文：如果使用本 Skill 默认 endpoint，请选择 `cn-beijing` 方舟地域。
2. EN: Open the model management or model opening page.
   中文：进入模型管理或模型开通页面。
3. EN: Search for Doubao Seedance 1.5 Pro.
   中文：搜索豆包 Seedance 1.5 Pro。
4. EN: Open the model service or endpoint required by your account.
   中文：按账号要求开通模型服务或 endpoint。
5. EN: Confirm the model ID shown in the console.
   中文：确认控制台显示的 Model ID。

Current default model ID / 当前默认模型 ID：

```text
doubao-seedance-1-5-pro-251215
```

EN: If the console shows a newer model ID, pass it to the pipeline with `--video-model` or update `sticker-plan.json`.

中文：如果控制台显示了更新的模型 ID，可以通过 `--video-model` 传入，或更新 `sticker-plan.json`。

## 4. Create An API Key / 创建 API Key

Official guide / 官方指南：

https://www.volcengine.com/docs/82379/1541594

Recommended steps / 推荐步骤：

1. EN: Open the Ark API Key management page from the console.
   中文：从控制台进入 Ark API Key 管理页面。
2. EN: Select the correct project space.
   中文：选择正确的项目空间。
3. EN: Create an API Key.
   中文：创建 API Key。
4. EN: Optionally restrict the key to the specific model/endpoint and IP range.
   中文：可选：限制 API Key 可访问的模型、endpoint 或 IP 范围。
5. EN: Store the key in a local secret manager or environment variable.
   中文：把 Key 存在本地密钥管理器或环境变量里。

Never commit the key to GitHub.

不要把 API Key 提交到 GitHub。

## 5. Configure The Runtime Environment / 配置运行环境

For the current shell / 当前 shell：

```bash
export ARK_API_KEY="your_api_key_here"
```

EN: For Codex Desktop, make sure the process that runs tool commands can see `ARK_API_KEY`. A key pasted into chat is not a runtime environment variable.

中文：如果使用 Codex Desktop，需要确保运行工具命令的进程能读取到 `ARK_API_KEY`。把 Key 粘贴到聊天里不等于设置了环境变量。

Check presence without revealing the value / 只检查是否存在，不打印 Key：

```bash
test -n "$ARK_API_KEY" && echo "ARK_API_KEY_PRESENT" || echo "ARK_API_KEY_MISSING"
```

## 6. Smoke Test The Pipeline / 跑一个最小测试

Initialize a small animated job / 初始化一个小型动态任务：

```bash
python3 scripts/run_wechat_sticker_pipeline.py init \
  --output-dir ./out/seedance-smoke \
  --pack-name "Seedance Smoke Test" \
  --count 8 \
  --motion animated \
  --animated-source-mode green_screen_video \
  --theme "simple mascot wave" \
  --character "small original mascot"
```

After Codex image generation creates `start_frames/01.png` and `end_frames/01.png`, validate:

当 Codex 图像生成创建好 `start_frames/01.png` 和 `end_frames/01.png` 后，执行检查：

```bash
python3 scripts/run_wechat_sticker_pipeline.py validate \
  --plan ./out/seedance-smoke/sticker-plan.json \
  --require-keyframes \
  --require-secrets
```

Submit one pilot video / 提交一个 pilot 视频：

```bash
python3 scripts/run_wechat_sticker_pipeline.py submit-videos \
  --plan ./out/seedance-smoke/sticker-plan.json \
  --indices 01 \
  --concurrency 1
```

Convert the MP4 to GIF / 把 MP4 转 GIF：

```bash
python3 scripts/run_wechat_sticker_pipeline.py process-videos \
  --plan ./out/seedance-smoke/sticker-plan.json \
  --indices 01 \
  --sample-count 36
```

Review the pilot before starting 8/16/24 stickers.

先审核 pilot，再开始生成 8 / 16 / 24 张整包。

## 7. Troubleshooting / 排错

`ARK_API_KEY missing`

EN: The key is not visible to the command runtime. Export it in the shell or configure it in the environment that launches Codex.

中文：命令运行环境读取不到 Key。需要在 shell 里 export，或在启动 Codex 的环境里配置。

HTTP 401 / 403

EN: The key may be invalid, restricted to another project, missing model permission, or not allowed from your IP.

中文：Key 可能无效、属于其他项目、没有模型权限，或当前 IP 不被允许。

Task succeeds but no video URL / 任务成功但没有 video URL

EN: Save the task report and inspect the final API response. The API schema or model output format may have changed.

中文：保存任务报告并检查最终 API 响应。可能是 API 结构或模型输出格式变了。

Green-screen keying is dirty / 绿幕抠像不干净

EN: Regenerate start/end frames with a flatter `#00FF00` background, no green subject colors, no shadows, no glow, and a clean opaque silhouette.

中文：重新生成首尾帧，要求纯平 `#00FF00` 背景，主体不要有绿色/青色、阴影、发光或透明毛边。

Video motion is good but GIF is too large / 视频动作不错但 GIF 太大

EN: Try fewer samples in this order: 48, 40, 36, 32, 28, 24. Avoid going below 24 for standard-quality animated stickers.

中文：按顺序降低采样帧数：48、40、36、32、28、24。标准质量动态表情尽量不要低于 24 帧。
