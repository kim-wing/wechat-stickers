# Seedance / Volcengine Ark Setup

This skill uses Volcengine Ark's video generation API for high-quality animated WeChat stickers.

Default model policy:

- Use Doubao Seedance 1.5 Pro for animated sticker video generation.
- Use first-last-frame image-to-video when possible.
- Generate silent videos: `generate_audio: false`.
- Disable watermark: `watermark: false`.
- Read the API key from `ARK_API_KEY`.

## 1. Create Or Log In To A Volcengine Account

Go to the Ark product page:

https://www.volcengine.com/product/ark

The product page advertises trial/free benefits and links to the Ark console. Free quota and resource-package policies can change, so always check the official pages before planning a large batch.

## 2. Check Free Quota Or Resource Package Availability

Official pages:

- Free inference quota: https://www.volcengine.com/docs/82379/1399514
- Seedance resource package rules: https://www.volcengine.com/docs/82379/2191775
- Model pricing / product page: https://www.volcengine.com/product/ark

Important notes:

- Free quota is account-, project-, model-, region-, and campaign-dependent.
- Some video models or resource packages may require opening the service, topping up, buying a package, or meeting account conditions.
- This repository cannot guarantee free Seedance availability. Treat the official console as the source of truth.

## 3. Open The Seedance Model

In the Ark console:

1. Choose the `cn-beijing` Ark region if you are using the default endpoint in this skill.
2. Open the model management / model opening page.
3. Search for Doubao Seedance 1.5 Pro.
4. Open the model service or endpoint required by your account.
5. Confirm the model ID shown in the console.

The current default used by this skill is:

```text
doubao-seedance-1-5-pro-251215
```

If the console shows a newer model ID, pass it to the pipeline with `--video-model` or update `sticker-plan.json`.

## 4. Create An API Key

Official guide:

https://www.volcengine.com/docs/82379/1541594

Recommended steps:

1. Open the Ark API Key management page from the console.
2. Select the correct project space.
3. Create an API Key.
4. Optionally restrict the key to the specific model/endpoint and your IP range.
5. Store the key in a local secret manager or environment variable.

Never commit the key to GitHub.

## 5. Configure The Runtime Environment

For the current shell:

```bash
export ARK_API_KEY="your_api_key_here"
```

For Codex Desktop, make sure the process that runs tool commands can see `ARK_API_KEY`. A key pasted into chat is not a runtime environment variable.

Check presence without revealing the value:

```bash
test -n "$ARK_API_KEY" && echo "ARK_API_KEY_PRESENT" || echo "ARK_API_KEY_MISSING"
```

## 6. Smoke Test The Pipeline

Initialize a small animated job:

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

```bash
python3 scripts/run_wechat_sticker_pipeline.py validate \
  --plan ./out/seedance-smoke/sticker-plan.json \
  --require-keyframes \
  --require-secrets
```

Submit one pilot video:

```bash
python3 scripts/run_wechat_sticker_pipeline.py submit-videos \
  --plan ./out/seedance-smoke/sticker-plan.json \
  --indices 01 \
  --concurrency 1
```

Convert the MP4 to GIF:

```bash
python3 scripts/run_wechat_sticker_pipeline.py process-videos \
  --plan ./out/seedance-smoke/sticker-plan.json \
  --indices 01 \
  --sample-count 36
```

Review the pilot before starting 8/16/24 stickers.

## 7. Troubleshooting

`ARK_API_KEY missing`

The key is not visible to the command runtime. Export it in the shell or configure it in the environment that launches Codex.

HTTP 401 / 403

The key may be invalid, restricted to another project, missing model permission, or not allowed from your IP.

Task succeeds but no video URL

Save the task report and inspect the final API response. The API schema or model output format may have changed.

Green-screen keying is dirty

Regenerate start/end frames with a flatter `#00FF00` background, no green subject colors, no shadows, no glow, and a clean opaque silhouette.

Video motion is good but GIF is too large

Try fewer samples in this order: 48, 40, 36, 32, 28, 24. Avoid going below 24 for standard-quality animated stickers.
