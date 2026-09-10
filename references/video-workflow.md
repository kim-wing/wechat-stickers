# Optional video route

Use when requested or chosen after an evidence-based pilot comparison. Video can help with continuous full-body motion; it adds a video service, extraction and keying, and does not guarantee identity or loop stability.

Initialize explicitly with `--animated-source-mode green_screen_video` (transparent) or `background_video` (designed background). Seedance model/runtime setup is documented in [../docs/seedance-ark-setup.md](../docs/seedance-ark-setup.md). Check ARK_API_KEY only for this route; never print secret values.

Use imagegen to create matching start/end keyframes. Fix identity, camera, scale, baseline and caption; choose a loop-compatible endpoint. Record whether the endpoint intentionally matches the start. Save sources and prompt paths in the plan. Use silent video (`generate_audio: false`); record task id before polling so retries do not submit duplicate paid jobs.

```bash
python3 scripts/run_wechat_sticker_pipeline.py validate --plan /absolute/job/sticker-plan.json --require-keyframes --require-secrets
python3 scripts/run_wechat_sticker_pipeline.py submit-videos --plan /absolute/job/sticker-plan.json --indices 01 --concurrency 1
python3 scripts/run_wechat_sticker_pipeline.py process-videos --plan /absolute/job/sticker-plan.json --indices 01
```

Inspect pilot playback and keyed edges before batch submission. Preserve task reports, MP4, extracted/keyed PNG frames and selection provenance. Use shared video scripts, never hand-edit reports to fake successful generation. A failed video remains a failed candidate; switching route requires updating the project plan/lock and respecting any explicit user choice. Ordinary new image-frame runs do not need video access or fallback approval.
