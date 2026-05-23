# WeChat Sticker Specs

Use these specs when preparing WeChat sticker assets. The platform may change validation rules, so treat this as a packaging baseline and verify in the upload UI when submitting.

## Album Counts

- Album stickers: 8, 16, or 24 images depending on the submission path.
- Keep every main sticker in the same album either static or animated.
- Name main stickers and thumbnails with matching two-digit indexes: `01`, `02`, `03`, ...

## Main Stickers

- Size: `240x240` px.
- Static album format: prefer `PNG`.
- Animated album format: `GIF`.
- Suggested max file size: `500KB` per main sticker.
- Dynamic GIFs must loop forever.
- Sprite-sheet fallback source: 16 frames (`4x4`) at about `70-90ms` per frame, only when sprite mode was explicitly requested or approved as fallback.
- Complex sprite-sheet source: 20 frames (`5x4` or `4x5`) when the motion needs more in-betweens and the final GIF can still fit the size budget.
- For sprite sheets, use 12 frames only for simple motions or tighter file budgets.
- For sprite sheets, use 8 or 4 frames only as compact/preview fallback after accepting less smooth animation; do not treat 8-frame 2x4 output as standard-quality motion.
- Video-based GIF output is not limited to 16/20 frames. Sample 24-48 frames from the MP4 depending on motion complexity and file size.
- Standard-quality animated QC should require at least 12 frames and no visible magenta key-color fringe.
- Keep style unified and scenarios distinct.

## Video-Based Animated Stickers

- Video-based animated stickers may be produced as either transparent GIFs or background GIFs.
- Video-based generation is the default route for new animated sticker requests. Use sprite sheets only by explicit request, approved fallback, or tiny micro-motion cases where video is unnecessary.
- Every new animated run must start with a mode-lock preflight before old project files or old prompts are reused: `animated_source_mode`, `video_input_mode`, `video_model`, `video_audio_policy`, output directory, and `sprite_fallback_approved`.
- Old sprite-sheet jobs, old `preview_not_submission_ready` manifests, and old prompt files do not authorize a new run to use `4x4`/16-frame sprite mode. They are diagnostic evidence only unless the user explicitly asks to reuse that exact project.
- Use Doubao Seedance 1.5 Pro as the default and only video model for this workflow unless the project policy changes.
- Use first-last-frame image-to-video as the default Seedance input mode. Provide a `first_frame` image and a `last_frame` image to constrain the action boundary. Use first-frame-only generation only when an end frame is unavailable, meaningless for the motion, or explicitly chosen.
- First and last frame images must share the same aspect ratio, canvas size, character identity, camera/framing, subject scale, style, and background/key color. Mismatched dimensions or ratios can cause automatic crop/adaptation and should fail production review.
- Before Seedance generation, compare the start/end pair visually. Matching dimensions are not enough: identity, proportions, face/screen details, material, colors, outline thickness, camera, subject scale, baseline, and background/key color should also match.
- Using the exact same file for `first_frame` and `last_frame` is allowed only as an explicit loop-closure choice and must be recorded with `end_frame_same_as_start_approved` plus a reason. Otherwise it is treated as a degraded first-frame-only workflow.
- Seedance sticker videos must be generated without audio: `generate_audio: false`.
- Set `watermark: false` for production sticker videos.
- Keep Ark API keys out of all project files. Use runtime environment variables such as `ARK_API_KEY`.
- A key pasted into chat does not automatically become `$ARK_API_KEY` for tool execution. For security, do not paste secrets into command lines; make the key available through the Codex runtime environment or an approved local secret source, then verify only that it is present.
- The Seedance task API is asynchronous: create task, store task id, poll the query endpoint, download `video_url`, then process frames locally.
- Use `duration` for Seedance 1.5 Pro tasks; do not depend on `frames` for Seedance 1.5 Pro.
- For video mode, sample GIF frames locally after download: 24-32 frames for subtle motion, 36-48 frames for dance/run/spin/complex motion. If file size fails, step down 48 -> 40 -> 36 -> 32 -> 28 -> 24 before accepting compact quality.
- Video-mode production stickers must keep video provenance in `manifest.json`: each main sticker should use `creative_source: "seedance_video"`, `video_input_mode`, `postprocess_input_path` equal to the downloaded MP4, plus `start_frame_source_path`, `end_frame_source_path` for first-last-frame mode, `video_source_path`, `video_task_report_path`, `video_prompt_path`, `keyed_frames_dir`, and `transparent_gif_source`.
- Expanded albums must keep count-sensitive delivery metadata consistent: final directory/archive name, manifest `count`, design note, `metadata.csv`, preview grid, QC report, and expected count should all describe the final count. If an old output folder is reused as the source, record the expansion source and final archive path in the manifest.
- Do not use `image_gen_loop`, a local still-image transform, or a static cutout animation as a silent fallback after Seedance succeeds or fails. If no video candidate passes, regenerate video candidates or mark the run as a production failure.
- Transparent video mode should use a pure green screen source (`#00FF00`) and a keying pass before GIF export.
- Green-screen postprocessing must include despill and final visible-green-spill QC. Production transparent GIFs should have no visible green halo, green background chips, or green edge remnants beyond a tiny quantization tolerance of 1 visible green-spill pixel.
- Keep keyed PNG frames as an auditable intermediate. Final transparent GIFs should be encoded from the keyed RGBA frame sequence, not directly from MP4.
- The final keyed frame folder should contain exactly the selected frame sequence used for the GIF, or use an unambiguous `selected_###.png` naming convention. Do not mix rough keyed frames, extracted RGB frames, and final ping-pong/filtered frames in one audit count.
- `frame_sample_count`, final keyed output frame count, and final GIF frame count should match after every reprocess.
- Apply the same fixed canvas transform to every extracted video frame. Per-frame alpha/bbox crop, recenter, or rescale is not production-safe because it can create center-step and scale-step jitter.
- For video-derived animated stickers, intended large motion is allowed. Do not reject or downsample solely because `visual diff outlier ratio` is high; reject only when the high metric corresponds to visible artifacts such as identity drift, scale breathing, camera movement, frame wrap, text/prop morphing, green spill, or bad loop closure.
- Custom temporal QC profiles for expressive video motion must be named and recorded in the manifest with exact threshold overrides. Edge/keying/artifact checks remain strict and should be fixed by re-keying or regenerating, not by relaxing production QC.
- Candidate video outputs should stay in candidate or preview paths until they pass QC. Production `main/NN.gif`, `thumbs/NN.png`, final `keyed_frames/NN`, and manifest selection fields should describe only the selected passing candidate, or be explicitly marked preview-only.
- Seedance task reports should include normalized top-level status/model/audio/watermark/duration/ratio/resolution/task-id fields plus the raw API responses. Do not rely on ad hoc report patching after generation.
- Use shared, version-checked skill scripts for Seedance and video postprocessing. New helper code should be Python 3.9 compatible and compiled before any paid or long-running API call.
- CorridorKey may be used as an optional external keying tool for green/blue-screen unmixing when available. It requires original RGB frames plus a coarse alpha hint and can recover straight foreground color plus linear alpha for soft edges.
- If CorridorKey is used, force green-screen mode for our green plates and keep the alpha hint, keyed frames, and keying settings with the job output.
- Do not bundle or redistribute CorridorKey code, weights, or paid inference access as part of this skill without license review.
- Background GIF mode may keep a designed background, but it should be labeled as non-transparent and should keep the background stable across frames.
- Background GIF backgrounds must be related to the sticker theme, character world, emotion, or chat scenario. Do not use generic gradients, random scenery, or unrelated decorative backgrounds.
- For background GIF albums, use a shared background system so the pack feels cohesive: consistent palette, recurring motifs, scene vocabulary, depth, and contrast level.

## Emoji / Reward Eligibility

- Do not use Emoji, system/platform emoji, yellow smiley faces, emoji-style reaction icons, or Emoji-derived secondary creations in any submitted asset.
- This applies to main stickers, thumbnails, cover, icon, detail banner, reward guide image, reward thanks image, prompt text, manifest copy, and design briefs.
- WeChat may disable or reject reward eligibility when sticker assets use Emoji-derived material. Treat this as a production QC gate, especially for `banner`, `reward-guide`, and `reward-thanks`.
- Official notice reference: https://mp.weixin.qq.com/s/Hrzilv8oIwjI4YjZqgbFZQ
- Use original pack character expressions and original thematic motifs instead: paws, bones, ribbons, badges, speech bubbles, scene props, abstract bursts, or hand-drawn marks that clearly belong to the sticker pack.

## Flags / National Symbols

- Avoid national flag material in all sticker-pack assets. Do not use real country flags, flag icons, flag stickers, flag-pattern backgrounds, flag-colored patriotic symbols, or recognizable national flag fragments as decoration.
- This applies to main stickers, thumbnails, cover, icon, detail banner, reward guide image, reward thanks image, prompt text, manifest copy, and design briefs.
- Replace flag motifs with non-national, pack-native graphic elements: ribbons, badges, abstract color blocks, confetti, speech bubbles, character props, or original fictional symbols.

## Thumbnails

- Album thumbnail size: `120x120` px.
- Format: `PNG`.
- Suggested max file size: `50KB` per thumbnail.
- One thumbnail per main sticker, with the same index.
- Use the clearest key frame.

## Cover

- File: `cover.png`.
- Size: `240x240` px.
- Format: `PNG`.
- Suggested max file size: `80KB`.
- Transparent background.
- Transparency must be real: do not submit a PNG with an opaque black, dark, white, or colored full-canvas background.
- Use the most recognizable image of the sticker character, preferably front half-body or full-body.

## Chat Panel Icon

- File: `icon.png`.
- Size: `50x50` px.
- Format: `PNG`.
- Suggested max file size: `30KB`.
- Transparent background.
- Transparency must be real: do not submit a PNG with an opaque black, dark, white, or colored full-canvas background.
- Use a clean, recognizable head or simple character mark.

## Detail Banner

- File: `banner.png` or `banner.jpg`.
- Size: `750x400` px.
- Format: `PNG` or `JPG`.
- Suggested max file size: `80KB`.
- Prefer JPG for rich, non-transparent banner art when the PNG version would require heavy palette quantization. Do not reduce a designed banner to a tiny paletted PNG just to hit 80KB.
- Use a lively non-white background.
- Avoid transparent background.
- Include short theme-specific copy by default, integrated into the visual design.
- Keep the image related to the sticker character or story.
- Treat it as a designed horizontal key visual with intentional composition, not a simple character cutout plus text.
- Generate or select source art in the same wide aspect ratio; do not crop a square source in a way that cuts off text, character, or props.
- Final exported image should fill the canvas edge to edge with no white border or letterbox margin.

## Reward Guide Image

- File: `reward-guide.png`, `reward-guide.jpg`, or `reward-guide.gif`.
- Size: `750x560` px.
- Format: `JPG`, `GIF`, or `PNG`.
- Images larger than `500KB` may be compressed by the platform.
- Displayed on the reward amount selection page.
- Purpose: encourage users to send a reward.
- Include short support-oriented theme copy by default.
- Must match the sticker pack style.
- Must not include content unrelated to the stickers.
- Treat it as a polished graphic-design key visual for the reward selection page, not a plain background with post-added text.
- Generate or select source art in the same `750x560` horizontal aspect ratio; do not crop a square source in a way that cuts off text, character, or props.
- Final exported image should fill the canvas edge to edge with no white border or letterbox margin.

## Reward Thanks Image

- File: `reward-thanks.png`, `reward-thanks.jpg`, or `reward-thanks.gif`.
- Size: `750x750` px.
- Format: `JPG`, `GIF`, or `PNG`.
- Images larger than `500KB` may be compressed by the platform.
- Displayed after the user sends a reward.
- Purpose: thank the user and encourage sharing.
- Include short thank-you theme copy by default.
- Must match the sticker pack style.
- Must not include content unrelated to the stickers.
- Treat it as a share-worthy graphic-design key visual, not a plain background with post-added text.
- Generate or select source art in the same square aspect ratio with safe margins; do not zoom-crop key text, character, or props.
- Final exported image should fill the canvas edge to edge with no white border or letterbox margin.

## Text Metadata

- Sticker name: up to 8 Chinese characters; 5 or fewer displays best.
- Description: up to 80 Chinese characters.
- Copyright/author info: up to 10 Chinese characters.
- One-line intro: up to 11 Chinese characters.
- Meaning keyword: up to 4 Chinese characters per sticker.
- Avoid punctuation, emoji characters, rare characters, and duplicated meaning keywords.
