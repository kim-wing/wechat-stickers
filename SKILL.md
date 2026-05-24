---
name: wechat-stickers
description: "Generate, postprocess, and package WeChat sticker packs from character or theme prompts. Use when Codex needs to create WeChat sticker album assets, single sticker assets, animated GIF stickers, static stickers, thumbnails, cover image, chat panel icon, detail banner, reward guide image, reward thanks image, meaning keywords, submission metadata, or QC reports for WeChat Sticker Open Platform style delivery."
---

# WeChat Stickers

Use this skill for WeChat sticker packs and WeChat-ready sticker assets.

For game sprites, animation sheets, RPG units, projectiles, or combat effects, use `generate2dsprite` instead.

## Workflow

### Production Pipeline Contract

For real 8/16/24-pack production, especially animated albums, use a plan/state driven pipeline instead of ad hoc long-thread orchestration.

- Before generating paid or batch assets, create or update `sticker-plan.json` in the job output directory. This file is the source of truth for `pack_name`, `slug`, `count`, `motion`, `animated_source_mode`, `video_input_mode`, `video_model`, `theme`, `character`, sticker list, copy, meanings, start/end frame paths, video prompt paths, and album asset source paths.
- Also create `run-state.json` in the same job output directory. It tracks each sticker's current stage: planned, keyframes_ready, video_submitted/running, video_done, gif_done, qc_done, failed. Do not rely on chat memory, folder mtime, `find | head`, or old manifests to decide what to process next.
- Use `scripts/run_wechat_sticker_pipeline.py init` to create the output skeleton, starter plan, and state file. Use its later subcommands for deterministic stages whenever the needed source files already exist.
- For animated Seedance runs, the standard deterministic path is:
  1. `init`
  2. generate 1-2 pilot start/end frames with `image_gen`
  3. write those paths into `sticker-plan.json`
  4. `validate --require-secrets`
  5. `submit-videos` for the pilot
  6. `process-videos` for the pilot
  7. visually review pilot MP4/GIF/contact sheet
  8. generate remaining start/end frames
  9. batch `submit-videos` with bounded concurrency
  10. `process-videos`
  11. generate cover/icon/banner/reward assets
  12. `make-preview`
  13. `qc`
  14. `package` only after the intended QC level is clear
- The pipeline may not silently switch an animated run from Seedance video to sprite-sheet, still-loop, local transform, or old project artifacts. If Seedance is unavailable, stop and record the blocker.
- Time, token cost, API cost, or desire to finish in the current turn is not approval to downgrade. If the selected animated mode is Seedance video and the estimated run is expensive or slow, stop after `init` or the pilot plan and ask the user whether to continue, reduce count, switch to static, or explicitly accept a lower-quality preview. Do not decide this alone.
- Do not write pack-specific local composite generators such as `make_<pack>_pack.py` that extract the user reference image, paste text, and create final `main/` stickers. A pack-specific script may only organize plan/state files or call shared skill scripts; it may not create creative sticker art.
- `local_composite_preview`, `user_reference_local_composite_preview`, `still_loop`, `local_loop`, and similar modes are not valid production or draft-review modes for this skill unless the user explicitly requests a diagnostic mockup. If used for diagnosis, do not place outputs in canonical `main/`, do not package a zip, and do not describe it as a generated sticker pack.
- Every final `main/NN.gif` in `green_screen_video` or `background_video` mode must derive from the selected MP4 recorded in `run-state.json` and in `manifest.json`. Do not overwrite it with a local still loop or a locally animated cutout.
- For new animated requests, never start with `4x4`, `16 frames`, sprite grids, or sheet processing unless the current `sticker-plan.json` explicitly sets `animated_source_mode: "sprite_sheet"` and the user approved that fallback.
- Treat old folders and old thread artifacts as diagnostic evidence only. They cannot override the current `sticker-plan.json`.
- Keep the plan compact in chat. Full prompts, task reports, and QC reports live on disk. In chat, report only the pilot result, batch status counts, preview path, QC summary, and final archive path.
- Separate review intent from submission intent:
  - Draft review may stop after `make-preview` plus a compact QC summary.
  - Submission-ready delivery requires the final production `qc` report to be current, `ok: true`, and based on the last file mutations.
- For token control, do not open every generated image or video. Build one preview grid/contact sheet, then inspect individual assets only when the preview or QC points to a specific index.
- Generate banner, reward guide, reward thanks, cover, and icon while Seedance jobs are running when possible; do not wait for all GIFs unless character identity is still unresolved.

1. Infer the pack plan from the user request:
   - `pack_type`: `album` | `single`
   - `count`: `8` | `16` | `24` for albums
   - `motion`: `static` | `animated`
   - `character`: recurring visual identity
   - `style`: visual treatment
   - `emotion_set`: `everyday` | `work` | `cute` | `sarcastic` | `custom`
   - `motion_profile`: `micro_expression` | `head_only` | `single_limb` | `prop_only` | `controlled_full_body` for animated stickers
   - `animated_source_mode`: `green_screen_video` | `background_video` | `sprite_sheet`; default to Seedance video mode for animated stickers unless the user explicitly asks for sprite sheets or the video route is unavailable
   - `video_input_mode`: `first_last_frame` | `first_frame`; default to `first_last_frame` for Seedance video mode
   - `video_model`: for video-based animation, use only Doubao Seedance 1.5 Pro unless the user explicitly changes the policy
   - `video_audio_policy`: always `silent`; set `generate_audio: false` for Seedance video tasks
   - `reward_assets`: include by default for albums unless the user says not to
   - `emoji_policy`: always `no_emoji`; do not use Unicode emoji, system/platform emoji, yellow smiley faces, round reaction icons, or Emoji-derived secondary creation in any asset
   - `flag_policy`: always `no_national_flags`; do not use real country flags, flag icons, flag stickers, flag-pattern backgrounds, flag-colored patriotic symbols, or recognizable national flag fragments in any asset
   - If the user asks for a "表情包" but does not specify `single` vs album count, ask or state a clear assumption before generating. Do not silently downgrade an ambiguous pack request into one single sticker.
   - If the user already specified a full album count or explicitly asked to start with choices, offer `8 / 16 / 24` and `static / animated` before generation.
   - If `motion` is `animated`, choose a video source mode by default:
     - `green_screen_video` for transparent animated stickers.
     - `background_video` for animated stickers with a designed theme-related background.
     - Use `sprite_sheet` only when the user explicitly requests sprite sheets, when Seedance/Ark access is unavailable and the user approves fallback, or when the motion is so tiny that sprite-sheet generation is clearly cheaper and safer.
   - If Seedance video mode is selected but `ARK_API_KEY` is not available at runtime, stop and ask for the environment variable or explicit approval to fall back to sprite-sheet mode. Do not silently switch back to sprite sheets.
   - A key pasted into chat is not the same thing as a runtime environment variable. Do not copy a pasted key into shell commands, inline env assignments, prompts, manifests, reports, or scripts. Ask the user to make `ARK_API_KEY` available to the Codex process or an approved local secret source, then verify only with a present/missing check.
   - If Seedance video is created but fails visual/QC review, regenerate another Seedance candidate or stop with a clear production failure. Do not replace the deliverable with a local still-image loop, `image_gen_loop`, canvas/PIL transform, sprite fallback, or static cutout animation unless the user explicitly approves that downgrade.
   - For Seedance video mode, plan and generate both a locked `start_frame` and `end_frame` by default. Use first-frame-only generation only when the action has no meaningful endpoint, the end frame repeatedly causes worse identity drift, or the user explicitly chooses first-frame mode.
   - If the start and end frame are intentionally the same image for loop closure, record `end_frame_same_as_start_approved: true` and `end_frame_same_as_start_reason`. Do not silently use the same file for both roles as a shortcut.
   - Mode-lock preflight is mandatory before reading old project folders, writing prompts, or generating anything for a new animated request. Record the current run's `motion`, `animated_source_mode`, `video_input_mode`, `video_model`, `video_audio_policy`, output directory, and whether `sprite_fallback_approved` is true or false. The default for a new animated request is `green_screen_video` or `background_video` with `video_input_mode: "first_last_frame"`.
   - Old job folders, old manifests, old prompts, and old Codex thread artifacts are evidence for diagnosis only. They must not become the source of truth for a new run's `animated_source_mode`, `rows`, `cols`, frame count, prompt pattern, selected candidate, or creative source unless the user explicitly says to reuse that exact project.
   - If you open an old manifest whose `status` is `preview`, `preview_not_submission_ready`, `diagnostic`, or `mockup`, treat it as a cautionary example, not a template. After inspecting it, reset the current plan back to the mode-lock preflight before generating.
   - Do not mention, plan, or begin `4x4`, `16 frames`, `sprite_sheet`, `wide strip`, `grid`, or sheet-processing commands in a new animated request until one of these is true: the user explicitly requested sprite sheets; `ARK_API_KEY` or Seedance access is unavailable and the user approved fallback; or a video-mode production attempt failed and the user approved sprite fallback.

2. Read only the needed references:
   - Read [references/wechat-spec.md](references/wechat-spec.md) before packaging or QC.
   - Read [references/prompt-rules.md](references/prompt-rules.md) before writing image prompts.
   - Read [references/emotion-presets.md](references/emotion-presets.md) when the user did not provide a full sticker list.
   - Keep context lean: use `rg`, targeted `sed`, or section-specific reads. Do not dump the full skill, full prompt rules, full script help, full inspect JSON, or full QC report into the conversation unless debugging that exact file format.

### Token-Efficient Mode

Use token-efficient mode by default for sticker generation. Full artifacts should be written to disk; terminal output should be short summaries.

- Use `inspect-sheet --output raw/NN-candidate-XXX.inspect.json --summary` instead of `inspect-sheet ... > file; cat file`.
- Use `qc --summary --summary-limit 8` instead of `qc ...; cat qc-report.json`.
- Do not print full per-frame `metrics`, full `passed` arrays, full manifests, long prompts, or all generated image paths. Print only `ok`, failed count, first failed items, candidate id, dimensions, frame count, bytes, and final paths.
- Do not display every generated image/GIF/video in chat during normal production. Build one contact sheet with `make-preview-grid`, show or link that, and keep individual media paths on disk for inspection only when needed.
- For batch albums, generate and inspect one pilot first. Do not generate all 8/16/24 sheets until the pilot pattern passes.
- Reuse a compact base prompt and vary only scene/action/meaning per sticker. Store full prompts in `prompts/`; show only the short scene table in chat.
- Avoid calling `--help` for every subcommand during production runs. The commands are documented below.
- If a command fails, summarize the failure from the saved report rather than pasting the entire report.
- Use shared utility commands for routine artifacts: `make-metadata` for `metadata.csv` and `make-preview-grid` for contact sheets. Do not write one-off Python snippets for these in a production run.

### Static Fast Mode

Use static fast mode by default for static 8/16/24 sticker albums. This mode absorbs the parts that worked well in the strong static packs: single-image pilot, one production image per sticker, image-generated integrated text when readable, compact scene tables, shared postprocessing, contact-sheet review, and one final QC gate.

- Start with a compact sticker table: `index`, `scene`, exact `text`, `meaning`, `pose/action`, optional `prop`. Keep main-sticker text short, usually 2-6 Chinese characters. Longer lines should be split intentionally in the generated design or avoided.
- Generate one finished pilot sticker first. The pilot prompt should request a complete static sticker composition: recurring character, distinct pose/expression, exact short Chinese text, integrated high-contrast plaque/lettering, pure `#FF00FF` background, clean silhouette, no shadow/glow, generous margin, and phone-size readability.
- Process the pilot with `process-sticker --motion static`, then run `qc --motion static --pack-type single --no-require-manifest --summary`. Inspect the pilot visually before spending more image calls.
- If the pilot works, lock its visual identity with `style_lock_source_path` or `character_lock_source_path`, then generate the remaining stickers using the same compact base prompt and only vary scene/action/text/meaning.
- Prefer `image_generated_composition` for static text packs when the image model renders the text well. This is the fastest high-quality path: one imagegen call per sticker, no local typography, postprocess only for transparency, sizing, thumbnails, metadata, preview, and QC.
- Use `approved_static_text_composite` only when exact Chinese text remains unreliable after regeneration or when the user explicitly prefers a local typography layer. It must start from image-generated text-free character art for each sticker, not from a user reference cutout.
- Do not generate a 24-up production sheet. Do not use a single pose board as the production source. One production sticker needs one original imagegen source file.
- Reuse good album assets from the same character/style only when they already match the new pack and the manifest source audit remains valid. Otherwise generate cover/icon/banner/reward assets after the main pilot locks the character.
- Create a `preview-grid` or `contact-sheet` after batch processing so the full pack can be judged quickly for character consistency, subject scale, text readability, and repeated poses. This is a review aid, not a production source.
- For static albums, final main assets should be `main/NN.png`. Static one-frame GIF output is legacy behavior and should not be used for new packs.
- Keep all source prompts in `prompts/`, but show only the compact sticker table and QC summary in chat.

### Pack Expansion Mode

Use expansion mode when growing an existing 8-pack into 16 or 24 stickers.

- Decide whether the existing directory remains the source pack or becomes the final expanded pack before generating new stickers. If the count changes, the final deliverable directory and archive name must match the final count, or `manifest.json` must explicitly record `expanded_from_count`, `expanded_to_count`, `source_pack_dir`, and `final_archive_path`.
- Do not leave a 16/24-pack only inside a folder whose name says `8` unless it is clearly marked as the source directory and the final zip/archive carries the correct count. Prefer creating a new final folder such as `<slug>-16-animated-YYYYMMDD/` and copying or linking the reused assets.
- Update all count-sensitive metadata after expansion: `count`, `design_note`, sticker list, `metadata.csv`, `preview-grid`, QC report name, and final archive name. Do not leave copy like "8-pack" in a 16-pack manifest.
- Reuse cover/icon/banner/reward assets only when they still represent the expanded pack. If the theme or character direction changed, regenerate them; if reused, record an `asset_reuse_reason` in the manifest.
- Generate expansion stickers in a compact batch table first, then run Seedance in controlled batches. Keep a `batch_plan` or notes file that maps index -> text/meaning/motion/source frame/video/report so later resume does not require reading the whole conversation.
- For batch Seedance jobs, cap active long-running tasks to a manageable group, usually 4-8 at a time, unless the API quota and local polling are known to handle more. Record each task id/report path before starting the next batch.

3. Write a pack manifest:
   - Use 8, 16, or 24 distinct chat scenarios for an album.
   - Keep the same character and style across all main stickers.
   - Assign each sticker a short meaning keyword.
   - Include cover, icon, banner, reward guide, and reward thanks assets for a complete album.
   - Write theme-specific copy for `banner`, `reward-guide`, and `reward-thanks` by default.
   - Write a `design_brief` for `banner`, `reward-guide`, and `reward-thanks` describing layout, visual hierarchy, typography treatment, background system, character placement, props, palette, and mood.
   - Do not use Emoji or Emoji-derived material anywhere in the manifest, prompts, or output assets. This includes Unicode emoji characters, system/platform emoji, yellow smiley faces, round reaction icons, emoji-style decorations, WeChat/QQ-like built-in expression symbols, and copy or briefs that ask for `emoji style`.
   - Do not use national flag material anywhere in the manifest, prompts, or output assets. This includes real country flags, flag icons, flag stickers, flag-pattern backgrounds, flag-colored patriotic symbols, and recognizable national flag fragments.
   - Banner, reward guide, and reward thanks are reward-sensitive assets. Use only the original pack character and original thematic graphic motifs; Emoji-derived material can cause reward activation to be rejected or closed.
   - Generate one `cover-icon-source` character artwork for both cover and chat panel icon by default. Use the same image-generated source file for `cover` and `icon`, then crop/fit it differently; this keeps the album identity consistent.
   - For `cover` and `icon`, the source art must be transparent-extraction-ready on pure `#FF00FF` or already transparent. Do not generate or accept a black, dark, white, or colored full-canvas background.
   - If cover and icon use different generated sources, manifest must set `cover_icon_identity_match_approved: true` on the icon and explain the visual match in `cover_icon_identity_match_reason`.
   - Record the intended creative source for every asset as `image_gen`, not `local_composite`.
   - Record `image_gen_source_path` for every sticker and album asset; it must point to the actual image file created by Codex image generation under `.codex/generated_images/<thread-id>/<file>`.
   - Do not create hand-named folders inside `.codex/generated_images` such as `generated_images/my-pack/01.png` and treat them as imagegen outputs. Those are local derivatives, not creative source files.
   - Record `postprocess_input_path` for every sticker and album asset. By default it must be the same generated file, or an exact byte-for-byte copy of it. For `approved_static_text_composite`, it may be the derived composed file only when the manifest records `typography_overlay_approved: true`, `typography_overlay_reason`, and `original_raw_path`.
   - Use a distinct `image_gen_source_path` for each main sticker.
   - For animated stickers, record candidate selection fields: `generation_candidates`, `selected_candidate_id`, `selected_inspect_path`, and `selection_reason`.
   - A selected animated candidate must have a passing inspect JSON (`ok: true`) and that inspect JSON's `input` must match the final `postprocess_input_path`.
   - For animated packs, set `motion_profile` for every sticker. For video modes, allow expressive full-body motion after one pilot MP4 passes visual and GIF QC. For sprite-sheet fallback, default to `micro_expression`, `head_only`, or `single_limb`; use `controlled_full_body` only after a pilot sheet proves stable.
   - For video-based animated packs, set `animated_source_mode`, `video_input_mode`, `video_model`, `start_frame_source_path`, `end_frame_source_path` for first-last-frame mode, `video_source_path`, `keying_mode`, `alpha_hint_path` when used, `keyed_frames_dir`, and `transparent_gif_source`.
   - For video-based animated stickers, set `creative_source: "seedance_video"` on each main sticker and set `postprocess_input_path` to the downloaded MP4 used for frame extraction. Also record `video_task_report_path` pointing to the saved Ark/Seedance task JSON. The image-generated start/end frames are identity inputs, not the final creative motion source.
   - Add `locked_elements` for every animated sticker. At minimum lock body, feet/baseline, text, and props unless that element is the only intended moving part.
   - If a generated example, pilot, or style/character source is approved or used as the visual direction, record it as `style_lock_source_path` or `character_lock_source_path` in the manifest. Production stickers must continue from this generated identity; do not fall back to cutting out the user reference image.

Minimal manifest shape:

```json
{
  "pack_name": "毛茸茸小狗日常",
  "count": 8,
  "motion": "animated",
  "stickers": [
    {
      "index": "01",
      "scene": "打招呼",
      "action": "小狗挥爪跳动",
      "motion_profile": "single_limb",
      "locked_elements": ["body", "feet", "tail", "text", "props"],
      "meaning": "你好",
      "creative_source": "image_gen",
      "image_gen_source_path": "$CODEX_HOME/generated_images/<thread-id>/01-b.png",
      "postprocess_input_path": "/path/to/out/raw/01.png",
      "generation_candidates": [
        {
          "candidate_id": "01-candidate-001",
          "image_gen_source_path": "$CODEX_HOME/generated_images/<thread-id>/01-a.png",
          "raw_path": "/path/to/out/raw/01-candidate-001.png",
          "inspect_path": "/path/to/out/raw/01-candidate-001.inspect.json",
          "inspect_ok": false
        },
        {
          "candidate_id": "01-candidate-002",
          "image_gen_source_path": "$CODEX_HOME/generated_images/<thread-id>/01-b.png",
          "raw_path": "/path/to/out/raw/01-candidate-002.png",
          "inspect_path": "/path/to/out/raw/01-candidate-002.inspect.json",
          "inspect_ok": true
        }
      ],
      "selected_candidate_id": "01-candidate-002",
      "selected_inspect_path": "/path/to/out/raw/01.inspect.json",
      "selection_reason": "latest passing candidate; passes the motion checks for the selected animated source mode"
    }
  ],
  "assets": {
    "banner": {
      "copy": "毛茸茸小狗日常",
      "design_brief": "横向主视觉，左侧大标题融入奶油色标签，右侧小狗跳起挥爪，背景是柔和色块、爪印图案和圆形节奏，整体像一张完整表情包宣传横幅",
      "creative_source": "image_gen",
      "image_gen_source_path": "$CODEX_HOME/generated_images/<thread-id>/banner.png",
      "postprocess_input_path": "$CODEX_HOME/generated_images/<thread-id>/banner.png"
    },
    "reward-guide": {
      "copy": "给小狗一点鼓励",
      "design_brief": "750x560 赞赏选择页主视觉，小狗捧着小骨头站在中心偏下，文案在上方拱形标题区，周围有爱心、爪印、礼物和柔和色块，版式温暖有层次",
      "creative_source": "image_gen",
      "image_gen_source_path": "$CODEX_HOME/generated_images/<thread-id>/reward-guide.png",
      "postprocess_input_path": "$CODEX_HOME/generated_images/<thread-id>/reward-guide.png"
    },
    "reward-thanks": {
      "copy": "谢谢你的喜欢",
      "design_brief": "750x750 致谢页主视觉，小狗鞠躬感谢，文案作为上方手写标题，背景有礼花、丝带、爪印和圆形色块，整体适合分享",
      "creative_source": "image_gen",
      "image_gen_source_path": "$CODEX_HOME/generated_images/<thread-id>/reward-thanks.png",
      "postprocess_input_path": "$CODEX_HOME/generated_images/<thread-id>/reward-thanks.png"
    },
    "cover": {
      "creative_source": "image_gen",
      "image_gen_source_path": "$CODEX_HOME/generated_images/<thread-id>/cover-icon-source.png",
      "postprocess_input_path": "$CODEX_HOME/generated_images/<thread-id>/cover-icon-source.png"
    },
    "icon": {
      "creative_source": "image_gen",
      "image_gen_source_path": "$CODEX_HOME/generated_images/<thread-id>/cover-icon-source.png",
      "postprocess_input_path": "$CODEX_HOME/generated_images/<thread-id>/cover-icon-source.png"
    }
  }
}
```

For static stickers using `approved_static_text_composite`, add these fields to each affected sticker:

```json
{
  "typography_overlay": true,
  "typography_overlay_approved": true,
  "typography_overlay_reason": "exact Chinese wording required; shared static composer integrated plaque with character",
  "original_raw_path": "/path/to/out/raw-original/01.png",
  "postprocess_input_path": "/path/to/out/composed/01.png"
}
```

For video-mode animated stickers, the main sticker record should look like this instead of the sprite-sheet candidate-audit shape:

```json
{
  "index": "01",
  "scene": "机器人跳机械舞",
  "action": "固定镜头机械锁舞",
  "motion_profile": "controlled_full_body",
  "animated_source_mode": "green_screen_video",
  "video_input_mode": "first_last_frame",
  "creative_source": "seedance_video",
  "video_model": "doubao-seedance-1-5-pro-251215",
  "video_audio_policy": "silent",
  "start_frame_source_path": "$CODEX_HOME/generated_images/<thread-id>/01-start.png",
  "end_frame_source_path": "$CODEX_HOME/generated_images/<thread-id>/01-end.png",
  "video_source_path": "/path/to/out/video/01.mp4",
  "postprocess_input_path": "/path/to/out/video/01.mp4",
  "video_task_report_path": "/path/to/out/reports/seedance-task-01.json",
  "video_prompt_path": "/path/to/out/prompts/01-video-prompt.txt",
  "keying_mode": "local_green_screen_key",
  "keyed_frames_dir": "/path/to/out/keyed_frames/01",
  "transparent_gif_source": "/path/to/out/main/01.gif",
  "frame_sample_count": 36
}
```

4. Generate raw art:
   - Use built-in `image_gen` for all creative raw images.
   - Prefer one raw image generation per sticker.
   - After each generation, find the saved PNG under `$CODEX_HOME/generated_images` or `$HOME/.codex/generated_images` and record that exact path in `manifest.json`.
   - The saved imagegen path should be the original file in the thread's generated-images directory, for example `$CODEX_HOME/generated_images/<thread-id>/ig_....png`. Do not move local composites into `.codex/generated_images` to satisfy the source audit.
   - When a generated example already works, use it as a style/character lock for follow-up prompts or production derivations. The production source chain must start from generated art, not from the original reference photo.
   - Use that saved generated PNG directly as the postprocessing input, or copy it unchanged and record the copy as `postprocess_input_path`. The only exception is `approved_static_text_composite`, where `postprocess_input_path` may point to the derived composed image and `original_raw_path` must point to the untouched image-generated artwork.
   - For animated stickers, default to video generation first. Use Seedance 1.5 Pro first-last-frame image-to-video whenever possible: create a locked start frame and loop-compatible end frame with imagegen, pass them to Seedance as `role: "first_frame"` and `role: "last_frame"`, then convert the MP4 into either transparent GIF (`green_screen_video`) or non-transparent GIF (`background_video`).
   - For sprite-sheet fallback only, prefer a smooth `4x4` sheet per sticker: 16 frames.
   - `green_screen_video` mode is the default for transparent animated stickers, especially for motions that work poorly as sprite sheets: dance, run, spin, hop, bow, cheer, and expressive full-body loops.
   - For video-based animation, use only Doubao Seedance 1.5 Pro by default. Use the Ark video-generation task API endpoint `POST https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks`, with the model ID from the active Volcengine Ark model list for Seedance 1.5 Pro, such as `doubao-seedance-1-5-pro-251215` when available.
   - Never write the Ark API key into prompts, manifests, scripts, generated reports, zip files, shell history, or skill docs. Read it from an environment variable such as `ARK_API_KEY` at runtime.
   - Do not treat a pasted chat message as usable credential injection. Tool calls do not automatically inherit chat text as `$ARK_API_KEY`, and copying the key into a command would persist it in session logs. If the environment check reports missing, stop before calling Seedance.
   - Seedance video requests for sticker production must be silent: set `generate_audio: false`. Also set `watermark: false`.
   - Seedance first-last-frame request shape: include two `image_url` content items, one with `role: "first_frame"` and one with `role: "last_frame"`. The two images must share the same canvas size, aspect ratio, character identity, style, camera, scale, and background/key color. If their aspect ratios differ, the service may crop/adapt the last frame, which is not acceptable for sticker production.
   - First/last-frame consistency gate: before calling Seedance, create a small contact sheet or side-by-side preview of the two input frames and check that character identity, proportions, face/screen details, material, colors, outline thickness, camera, subject scale, baseline, and green/background color match. If they do not match, regenerate the end frame from the locked start-frame identity instead of hoping Seedance will reconcile them.
   - Minimal Seedance first-last-frame payload shape:

```json
{
  "model": "doubao-seedance-1-5-pro-251215",
  "content": [
    {"type": "text", "text": "fixed camera, stable character identity, loop-friendly motion, pure green screen, no audio"},
    {"type": "image_url", "image_url": {"url": "data:image/png;base64,<start>"}, "role": "first_frame"},
    {"type": "image_url", "image_url": {"url": "data:image/png;base64,<end>"}, "role": "last_frame"}
  ],
  "ratio": "1:1",
  "resolution": "480p",
  "duration": 5,
  "generate_audio": false,
  "watermark": false
}
```

   - Seedance task creation is asynchronous: create the task, save the task id, poll the task-query API until success/failure, download `video_url`, then continue with frame extraction, keying or background processing, GIF encoding, and QC.
   - For Seedance 1.5 Pro, do not rely on `frames` because the documented task API does not support it for this model. Use `duration` for the MP4 generation.
   - Video-based animation must not inherit sprite-sheet frame limits. Do not force video mode into 16 or 20 frames. Sample the downloaded MP4 adaptively for GIF output: default 24-48 frames, 24-32 for light motion, 36-48 for dance/run/spin/complex motion, and reduce frame count only when file size or true temporal artifact QC requires it. Do not reduce sampling or motion just because intended large action raises visual-diff metrics.
   - For video mode, try higher smoothness first, then reduce in this order when the GIF exceeds size limits: 48 -> 40 -> 36 -> 32 -> 28 -> 24 frames. Avoid going below 24 frames unless the user explicitly accepts compact/preview quality.
   - Never overwrite a video-derived production GIF with a still-image loop after Seedance succeeds. If the video postprocess result is weak, keep it in a candidate/preview location, generate a new Seedance candidate, or report failure. A final animated sticker in `green_screen_video` or `background_video` mode must be derived from the selected MP4 and keyed/video frames.
   - Before writing a new video candidate's `main/`, `thumbs/`, or `keyed_frames/NN`, clear or use a fresh candidate-specific directory. Do not leave stale keyed frames from an earlier MP4; the final GIF frame count and keyed frame set must describe the same selected video candidate.
   - Keep intermediate extracted RGB frames, rough keyed frames, and selected final keyed frames in separate folders or with unambiguous names. `keyed_frames/NN` should contain only the final RGBA frame sequence used to encode the GIF, or final frames named `selected_###.png`. Do not mix raw keyed frames and selected/ping-pong frames in the same audit folder.
   - `frame_sample_count`, the final keyed frame count, and the final GIF frame count must match. If reprocessing changes sample count, ping-pong count, outlier filtering, or selected frames, update the manifest and rerun QC.
   - Video postprocessing must use one fixed canvas transform for the entire MP4. Do not crop each frame to its alpha/bbox and recenter or rescale independently; that converts tiny keying noise or subject motion into large center-step and scale-step jitter. Use fixed `scale/pad/crop` from the source video, then key and resize every full frame identically.
   - Failed video candidates must stay in candidate or preview paths until they pass QC. Do not leave a failed candidate in production `main/NN.gif`, `thumbs/NN.png`, or final `keyed_frames/NN` unless the manifest status is explicitly `preview_not_submission_ready` and QC is rerun with that status. Promote only a passing selected video candidate into production paths.
   - After any manifest edit, `frame_sample_count` change, status change, candidate copy, report normalization, GIF re-encode, preview relocation, count expansion, metadata generation, or archive packaging, rerun QC and cite only that latest QC report. Do not leave a stale `qc-report.json` that describes an older manifest or older GIF. For preview-only delivery, write a separate preview QC/report or rerun production QC after marking `status: "preview_not_submission_ready"` so the failure reason is current and honest.
   - If video-mode temporal thresholds are intentionally relaxed for expressive Seedance motion, name the report accordingly and record the QC profile in the manifest, for example `qc_profile: "seedance_video_expressive"` plus the exact threshold overrides. Never rename a relaxed report to `*-ok.json` unless the report itself is actually `ok: true`, the threshold changes are recorded, and edge/keying checks remain strict.
   - Do not relax edge, green-spill, magenta-fringe, text/prop morphing, frame-wrap, or asset-dimension checks to make a video pack pass. Fix those by re-keying, regenerating, or marking the run as not production-ready.
   - In `green_screen_video` mode, generate or provide start/end frames with a pure flat green screen background (`#00FF00`) and a clean opaque subject. Avoid green/cyan subject colors, green rim lighting, shadows, smoke, glow, motion blur, translucent loose hairs, or background texture.
   - The end frame should be a controlled pose target, not a surprise new illustration. For loops, make the end frame either nearly identical to the start frame or a pose that returns naturally to the start after the GIF loop. For actions like waving, dancing, bowing, running in place, cheering, nodding, and spinning, first-last-frame mode is the default because it constrains the action boundary better than first-frame-only generation.
   - Generate first and last frames as separate imagegen originals or as explicitly imagegen-edited variants, and record both source paths. Do not create the end frame by locally warping, rotating, moving limbs, or editing pixels unless it is clearly marked as a non-production planning sketch.
   - Do not add visible anchor pixels, corner dots, guide marks, or artificial bbox handles to frames to improve automated stabilization or QC metrics. Stabilization must use alpha/bbox measurement without changing visible sticker art.
   - If an existing MP4 is reused for reprocessing variants, record `video_reuse_reason` and keep the variant in a candidate/preview folder unless the original Seedance task, prompt, frame inputs, manifest, and final QC all describe the selected result.
   - The video prompt must demand fixed camera, fixed framing, fixed character identity, no scene/background changes, no moving text, no shadows on the green screen, and a loop-friendly action whose final frame returns close to the start frame.
   - Seedance task reports must be normalized when they are first written: include top-level `task_id`, `status`, `model`, `generate_audio`, `watermark`, `duration`, `ratio`, `resolution`, `video_url` when available, `downloaded_video_path`, and keep raw API responses under `create_response` and `final_response`. Do not patch task reports later just to satisfy QC; fix the task writer or QC reader.
   - Use shared skill scripts for Seedance submission, video extraction, green-screen keying, GIF encoding, metadata, and QC. Do not create pack-specific production scripts such as `seedance_task.py` or `process_green_video.py` inside a job folder unless the output is labeled diagnostic/mockup. If a new helper is truly needed, add it to the skill's `scripts/` area, keep it Python 3.9 compatible, and run `python3 -m py_compile` before any paid or long-running API call.
   - Green-screen cleanup must include chroma key plus despill. Remove green pixels aggressively, clamp residual green channel near matte edges back toward the foreground's red/blue channels, threshold very low alpha out before GIF quantization, and re-encode through the shared GIF path. After keying, run a visible-green-spill audit; production transparent GIFs from `green_screen_video` should have at most 1 visible green-spill pixel after GIF quantization.
   - For transparent output from video, prefer CorridorKey-assisted keying when available. CorridorKey is designed for green/blue-screen unmixing: it predicts straight foreground color plus a linear alpha channel and can preserve hair, motion blur, and translucent edges better than simple RGB threshold keying.
   - CorridorKey requires the RGB green-screen footage plus a coarse alpha hint. Generate the alpha hint with a rough chroma key, BiRefNet, GVM, VideoMaMa, or another rough matte tool; the hint should isolate the subject broadly without expanding far into the background.
   - Force CorridorKey screen color to green for our `#00FF00` workflow when the tool is used (`--screen-color green`) instead of relying on auto-detection.
   - Treat CorridorKey as an optional local external tool, not a bundled dependency. Do not vendor, repackage, redistribute, or expose CorridorKey as a paid API/inference service from this skill. Check its license and attribution requirements before commercial integration.
   - If CorridorKey is unavailable, use the built-in green-screen keyer as fallback, but label the result lower-confidence and inspect edge flicker carefully.
   - `background_video` mode is allowed when the user wants a designed animated GIF with background. It should not be described as transparent. Keep the same background and camera stable across frames.
   - In `background_video` mode, the background must be theme-linked: it should support the sticker's character, story, emotion, season, location, prop world, or chat scenario. Do not use generic gradients, random rooms, abstract decoration, or unrelated scenery just to fill the canvas.
   - For a background GIF album, define a shared background system before generation: palette, recurring motifs, scene vocabulary, depth level, and how much the background may vary per sticker. Backgrounds should feel like the same pack universe while still matching each sticker's specific scenario.
   - For complex sprite-sheet motion, consider `5x4` or `4x5` 20-frame sheets, then reduce colors or simplify motion if file size is too large.
   - Generate and inspect a 1-2 sticker pilot before batch-generating the whole pack.
   - For animated stickers, keep a candidate registry instead of overwriting `raw/NN.png` during iteration. Save each generated sheet as `raw/NN-candidate-001.png`, `raw/NN-candidate-002.png`, and so on, with matching `raw/NN-candidate-001.inspect.json`.
   - Inspect every candidate sheet immediately. Record every candidate in `manifest.json` under that sticker's `generation_candidates`, including candidate id, `image_gen_source_path`, copied `raw_path`, `inspect_path`, `inspect_ok`, and key temporal metrics.
   - Promote only a passing candidate to production: copy the chosen candidate to `raw/NN.png`, copy its inspect JSON to `raw/NN.inspect.json`, and set `postprocess_input_path` to the promoted raw path or the selected candidate raw path.
   - Prefer `scripts/wechat_sticker_pack.py promote-candidate` for promotion instead of manual `cp`. It refuses to promote a candidate whose inspect JSON is not `ok: true`, verifies the inspect input matches the candidate file, copies the candidate into `raw/NN.png`, writes a production `raw/NN.inspect.json` whose `input` points to `raw/NN.png`, and updates the manifest selection fields.
   - Select the latest passing candidate by default. If choosing an older passing candidate for visual quality, write a concrete `selection_reason` and include the later candidate metrics. Never choose an older failed candidate because a later candidate is worse.
   - If no candidate passes `inspect-sheet --reject`, stop or deliver only a clearly marked preview. Do not create a production GIF.
   - For a user-requested generation, production is the default goal. Do not stop after only one or two failed candidates and present a preview as the main result. For a single animated sticker, try at least three improved candidates or stop with a clear production failure unless the user explicitly accepts preview-only output.
   - Preview outputs from failed candidates must live in a separate preview folder, such as `out-preview/` or `preview/`. Do not place preview GIFs in the production `main/`, `thumbs/`, `frames/`, or canonical `raw/NN.png` paths of the deliverable folder.
   - When making diagnostic preview variants from a failed but visually strong raw sheet, always generate and preserve an unedited `preview-original/` first. Do not let later cleanup variants replace or hide it.
   - If the user says a specific preview variant is best, treat that as the visual-preference source of truth for preview delivery. Record it as the recommended preview even if another variant has slightly better automated metrics.
   - For preview variants, compare both visual quality and metrics. Automated QC can rank stability, but it cannot judge whether energy effects, character appeal, pose, silhouette, or humor were lost by cleanup.
   - Never choose sprite sources by `find | head`, file mtime, directory order, memory, or visual vibe alone. The selection must be tied to `selected_candidate_id` and a passing `selected_inspect_path`.
   - Use `3x4` or 12 frames only for simple motions when file size is tight.
   - Use `2x4`, `1x4`, or `2x2` only as preview/compact fallback after the user explicitly accepts less smooth animation. Do not use 2x4 as the default for a high-quality pack.
   - For animated prompts, describe one simple cyclic action with a fixed camera, fixed baseline, stable character proportions, stable prop identity, and a frame-by-frame motion arc.
   - Use tiered motion admission instead of a blanket micro-animation limit. Default to low-degree-of-freedom motion for risky sprite-sheet fallback cases, but allow `controlled_full_body` when the sticker is simple enough to pilot safely. In Seedance/video mode, larger `controlled_full_body` motion is allowed when the pilot is visually coherent.
   - For Seedance/video mode, `controlled_full_body` is allowed for simple, single-subject, no-text or text-free-motion stickers such as running in place, dancing, jumping, spinning, bowing, cheering, waving, clapping, rolling, or dramatic reaction poses. Do not constrain these to tiny motion. Prompt for fixed camera, fixed baseline, stable body mass, stable head/face, stable subject scale, clean background/key color, and a loop-friendly action boundary.
   - For sprite-sheet fallback only, keep `controlled_full_body` more constrained: fixed 4x4 grid, fixed baseline, fixed body mass, fixed head size, generous cell padding, and a simple cyclic limb/body arc.
   - For sprite-sheet text stickers, stickers with large props, stickers with caption plaques, or scenes with multiple objects, default back to `micro_expression`, `head_only`, or `single_limb` unless a pilot proves the more complex motion meets the dog-run gold reference. In Seedance/video mode, use the video artifact gate instead: keep text static and allow larger character motion only if identity, scale, camera, props, key/background, and loop remain stable.
   - For text sticker packs, make the text/plaque completely static. In Seedance/video mode the character may still perform a larger readable action if the text area remains locked and the action does not obscure it; in sprite fallback, animate only one local region by default.
   - Keep uncontrolled full-body movement out of sprite-sheet fallback. In Seedance/video mode, full-body movement is allowed when it is purposeful and visually coherent; reject only camera drift, identity drift, scale breathing, text/prop morphing, or broken loop continuity.
   - Treat props as static anchors by default. Backpacks, chairs, tents, cups, maps, umbrellas, sunglasses, signs, and captions should not change size, angle, or position frame to frame.
   - Avoid asking the model to do several motions at once in one sticker, such as bounce, eat, sparkle, move text, and change expression all simultaneously.
   - If a main animated sticker includes text, require the text to stay in the same position, size, style, and wording across all frames.
   - Prefer motion arcs that can loop cleanly: rest, anticipation, action, follow-through, recovery, and final easing frame close to frame 1.
   - For transparent extraction, require a clean opaque sticker silhouette on pure `#FF00FF`: no drop shadows, glow, smoke, semi-transparent loose hairs, magenta/purple outlines, or soft contact shadows touching the background.
   - If the character is fuzzy, keep the fuzzy texture inside the silhouette; avoid individual wispy hairs fading into the magenta background.
   - Generate banner, reward guide, and reward thanks images as designed key visuals, not as simple resized stickers with post-added text.
   - Include the manifest copy directly in the generated banner, reward guide, and reward thanks artwork by default.
   - Include the full `design_brief` in each banner/reward image prompt; never prompt only with the copy text.
   - Generate banner/reward source art in the target aspect ratio from the start: `750x400` for banner, `750x560` for reward guide, `750x750` for reward thanks. Do not generate a square source and then crop it into a non-square reward/banner asset.
   - For banner and reward assets, keep all critical content inside a safe central area: title/copy, character face, hands/paws, props, and call-to-action marks must not sit near the crop boundary.
   - Explicitly ban Emoji in every image prompt: no Unicode emoji, no yellow smiley faces, no round reaction icons, no system/platform expression symbols, no Emoji-derived secondary creation.
   - Explicitly ban national flag material in every image prompt: no real country flags, no flag icons, no flag stickers, no flag-pattern backgrounds, no flag-colored patriotic symbols, no recognizable national flag fragments.
   - For banner/reward visuals, replace emoji-like decorations with pack-native motifs such as the original character, paws, bones, ribbons, badges, speech bubbles, abstract bursts, scene props, or hand-drawn marks that clearly belong to the sticker theme.
   - Replace flag-like decorations with non-national, pack-native graphic devices such as ribbons, badges, abstract color blocks, confetti, speech bubbles, character props, fictional pennants, or original symbols.
   - Keep the solid magenta `#FF00FF` background for assets that need transparent extraction.
   - For static text stickers, two production workflows are allowed:
     - `image_generated_composition`: image generation creates the finished character, expression, text plaque, and readable text. If the generated raw image is visually good and readable, preserve it.
     - `approved_static_text_composite`: image generation creates the high-resolution character/pose artwork without final text, then the shared postprocessor/composer adds a premium integrated text plaque. This is allowed when exact Chinese wording matters or the user approves the faster text-overlay workflow.
   - For static fast mode, try `image_generated_composition` first. The good static reference packs worked because the model generated character, pose, prop, and text plaque as one designed sticker image, then local processing only normalized the asset.
   - Do not use 8/16/24-in-one production contact sheets for static sticker albums. Generate one production artwork per sticker, or use a 2x2 sheet only for early concept exploration. A large batch sheet makes every subject small, lowers apparent pixel quality, and causes blind crop failures when the character is not centered in each cell.
   - In `approved_static_text_composite`, preserve the image-generated art before text in `raw-original/` or `preview-original/`, record `typography_overlay_approved: true`, `typography_overlay_reason`, and `original_raw_path`, and keep the composed result auditable in the manifest.
   - The composed sticker must be one compact visual unit: character and text plaque visually touch, overlap, or tuck together. Avoid a tiny character floating far above detached text, large empty gaps, or sparse compositions.
   - Target a strong `240x240` read: the visible combined character-plus-text bbox should usually occupy about 70-92% of canvas height and 70-92% of canvas width after fitting. Character artwork should remain high resolution and large enough to read on phone screens.
   - Text treatment must look designed, not like default PIL text: use a rounded plaque or integrated label shape, confident CJK font, thick readable fill, stroke or shadow, consistent palette, careful padding, and at most 1-2 short lines.
   - If local text composition is used, run `qc --motion static` with static layout QC enabled. Regenerate or recompose when QC reports tiny visible bbox, a too-small primary character component, large character/text separation, low fill ratio, edge contact, magenta fringe, or full-canvas artifacts.

5. Postprocess locally:
   - Use `scripts/wechat_sticker_pack.py process-sticker` for each main sticker.
   - Use `scripts/wechat_sticker_pack.py inspect-sheet` on each animated raw sheet before `process-sticker`.
   - Save each raw-sheet inspection as `raw/NN.inspect.json`. Final QC requires these files by default and requires every animated raw inspection to be `ok: true`.
   - For animated stickers, final QC also requires a candidate audit by default: `selected_candidate_id`, `selected_inspect_path`, and `generation_candidates` must be present in `manifest.json`; the selected inspect must be `ok: true`; and its `input` must match the postprocessing input.
   - Reject and regenerate raw sheets when `inspect-sheet` reports scale drift, center drift, center-step outliers, per-frame scale jumps, visual-diff outliers, loop mismatch, edge spill, thin edge bleed components, or magenta fringe.
   - If the GIF shows feet, props, text, or other lower-cell content appearing at the top of the canvas, treat it as adjacent-cell bleed from the raw sheet. Check `inspect-sheet` for `max_edge_pixels`, `max_edge_bleed_components`, `max_thin_top_sliver_components`, and per-frame `edge_bleed_boxes` / `thin_top_sliver_boxes`; regenerate the sheet with larger cell margins and fixed baseline.
   - `process-sticker` now runs raw-sheet preflight by default for animated grids. If preflight fails, do not bypass it for production output; use `--no-reject-raw-sheet` only to create diagnostic previews.
   - `process-sticker --no-reject-raw-sheet` is guarded by the script and should only write to a directory whose path includes `preview`, `diagnostic`, `mockup`, or `scratch`.
   - Any relaxed preview QC must use `qc --report-name qc-report-preview.json` and must not overwrite the production `qc-report.json`. A preview QC report with `ok: true` is not evidence that the pack is production-ready.
   - If `qc-report-preview.json` has `ok: false`, call the result a diagnostic preview only. Do not describe it as usable, ready, generated, complete, or suitable for chat use.
   - For diagnostic preview comparison, run preview QC for every variant including `preview-original`, then present a compact comparison table: variant path, visual note, `ok`, failed count, frame count, bytes, and recommendation. Do not recommend a cleanup variant solely because it removed more pixels or reduced file size.
   - Do not mask QC failures with shell constructs like `; cat qc-report...`, `|| true`, or later successful commands before a user-facing answer. If a QC command exits nonzero, treat the output as failed even if a following `cat` command succeeds.
   - Never ship a sticker generated from a raw sheet that failed `inspect-sheet --reject`. A failed raw sheet means regenerate, not stabilize harder, splice frames, or accept a "preview" version.
   - Do not create production GIFs by reordering, duplicating, or selecting only the "best" row from a failed sheet. That breaks the creative-source audit, often destroys loop intent, and can hide failures without solving motion quality.
   - Do not manually copy a candidate sprite into `raw/NN.png` for production. Use `promote-candidate` so a failed candidate cannot be promoted silently.
   - Do not create production GIFs by taking a single still cell or stable frame from a generated sprite sheet and locally adding tiny bounce, blink, scale, or offset loops. If a sprite sheet was generated, the production GIF must be based on that sheet's generated sequence frames after the sheet passes inspection.
   - Exporting PNG frames from the final GIF does not prove the GIF used the generated sprite sequence. The raw generated sheet, `raw/NN.inspect.json`, `frames/NN/*.png`, and `main/NN.gif` must form one auditable chain.
   - The postprocessor can remove thin disconnected edge slivers with its default edge-bleed cleanup, but this is a salvage aid, not a substitute for a clean raw sheet. It cannot repair frames where the character itself is cropped by a cell boundary.
   - For animated stickers, use `process-sticker --stabilize-position` by default after a sheet passes raw inspection. The default is center-anchor median stabilization, which removes camera/encoding jitter while preserving the generated artwork.
   - For FrameRonin-style jitter control, treat stabilization as a fixed-canvas normalization pass: first split the passed raw sheet into full RGBA frames, keep every output frame at exactly `240x240`, then align each frame by a measured alpha anchor (`center`, `bottom`, or `feet`) rather than by visual guessing. This is appropriate for mild whole-subject drift, not for changed poses or redrawn props.
   - Use `--stabilize-anchor center --stabilize-mode median` for controlled run-in-place or similar cyclic full-body pilots when the raw sheet has already passed `inspect-sheet`. The accepted dog-run pilot is the gold reference: 16 frames, no edge spill, no top sliver, no magenta fringe, `center_drift 4.5`, `center_step_outlier_ratio 2.40`, `scale_step_ratio_max 1.03`, `diff_outlier_ratio 1.29`, `loop_diff_ratio 0.94`, final GIF `240x240`, 16 frames, 321KB, QC `0 failed`.
   - Treat the dog-run gold reference as the minimum visual bar for any "smooth motion" claim. A generated sprite sheet with raw `ok: false`, `diff_outlier_ratio > 1.6`, `loop_diff_ratio > 1.35`, edge spill, top sliver, text morphing, or prop redraw does not meet this bar even if it has 16 frames and looks usable as a still sheet.
   - Use `--stabilize-anchor bottom --stabilize-mode median` when the feet or contact baseline must feel planted. Use `--stabilize-anchor feet` only when the alpha silhouette has clear lower contact points and the result is visually better than `bottom`.
   - If the action is a foot-planted bow, jump, sit, or stomp, use `--stabilize-anchor bottom --stabilize-mode smooth` only when center anchoring visibly harms the motion.
   - If processed PNG frames are stable but the GIF still appears to jump, suspect GIF transparency quantization. The shared encoder protects low-alpha foreground pixels and prevents the transparent palette index from eating the subject; do not write custom GIF exporters that skip this.
   - For video-based transparent GIFs, extract frames, key them to RGBA, normalize every frame onto the same `240x240` canvas, align by alpha anchor, remove green spill, and then encode through the shared GIF path. Do not encode straight from MP4 to GIF without a keyed-frame QC pass.
   - For green-screen video outputs, QC must include visible green-spill detection in addition to magenta fringe detection. Any visible green halo/background remnant above the tiny quantization tolerance means reprocess with stronger key/despill or regenerate a cleaner green-screen video.
   - The postprocessor uses soft chroma keying by default. If old outputs show dirty magenta edges, reprocess from the original image-generated raw sheet with current defaults before judging the source image.
   - Final main sticker QC must report `visible magenta fringe pixels 0 <= 0`. Any visible magenta/purple key-color rim in the final transparent PNG or GIF is a failed cutout.
   - Treat temporal failures as source-generation failures first. Do not accept a sheet just because size, frame count, transparency, and file size pass.
   - For sprite-sheet fallback, if QC fails on `visual diff outlier ratio` or `loop diff ratio` while edge/fringe checks pass, simplify the generation prompt rather than tuning postprocessing. Regenerate one motion tier simpler: `controlled_full_body` -> `single_limb` -> `head_only` -> `micro_expression`.
   - For Seedance/video mode, a high `visual diff outlier ratio` alone is not a failure and must not trigger automatic downgrade to micro-animation. Large intentional motion is acceptable when the MP4/GIF is visually coherent: fixed camera, stable identity, stable subject scale, no non-intentional redraw, no text/prop morphing, no frame wrap, no green spill, and a usable loop. Use visual inspection plus these concrete artifact checks before deciding to regenerate.
   - If a sheet shows stable center but visible redraw jitter, use a more static prompt with the exact locked-elements list repeated in every frame description. Stabilization can align the body box, but it cannot stop the model from redrawing a different chair, backpack, face, paw shape, or text plaque.
   - Use stabilization only for mild accidental camera jitter or GIF encoding jitter. Do not use it to hide pose swaps, prop morphing, text morphing, or scale breathing; regenerate instead.
   - Use `scripts/wechat_sticker_pack.py make-asset` for cover, icon, banner, reward guide, and reward thanks images.
   - For cover and icon, use the same `raw/cover-icon-source.png` input unless there is an explicit visual reason not to. The icon should be a tighter head/face crop of the same character source, not a separately imagined character.
   - For cover and icon, inspect the raw source before making assets. If it has a black/dark/white/colored full-canvas background instead of pure `#FF00FF` or real transparency, regenerate it. A PNG with an opaque black background is a failed transparent asset.
   - Production QC rejects transparent album assets whose visible pixels fill nearly the whole canvas or whose opaque dark pixels indicate a black background. If cover/icon fail this, regenerate from a clean transparent-ready source.
   - For banner, reward guide, and reward thanks, the asset maker uses cover-fill by default. Do not use contain/letterbox fitting for these assets, and do not allow white borders around the final image.
   - Before `make-asset` for banner/reward images, inspect the generated source dimensions and composition. If a non-square asset source is square, portrait, or places text/character near the edge, regenerate at the correct aspect ratio instead of cropping important content off.
   - For non-transparent album assets, preserve true color. Do not quantize banner/reward images into tiny paletted PNGs to pass file-size checks; this causes obvious desaturation, posterization, and fuzzy character damage.
   - Detail banner has a tight 80KB budget. Use `make-asset --kind banner` with the default `--asset-format auto`, which exports `banner.jpg` instead of a low-color PNG. If JPEG still exceeds the size budget or looks poor, regenerate a flatter graphic-design banner with fewer gradients and fur-detail texture rather than shipping an oversized asset.
   - Reward guide and reward thanks have a 500KB platform compression threshold. If either exceeds 500KB, export as high-quality JPG or regenerate a cleaner flatter design; do not leave oversized PNGs in the final folder.
   - Use local scripts only after the raw creative image exists.
   - Do not write pack-specific local drawing/compositing scripts to create the character art or fake an image-generation result.
   - For static main stickers, local typography is allowed only through the approved static text composite workflow above. Do not use one-off PIL/ImageDraw/canvas scripts with default fonts, arbitrary placement, or undocumented crop decisions.
   - Never make the final static album by blindly cropping a 24-up image sheet. If a contact sheet was used for ideas, regenerate the chosen sticker as its own full-size raw image before production composition.
   - Use `scripts/wechat_sticker_pack.py qc` before final delivery. For static packs, keep `--require-static-layout-qc` enabled; it rejects outputs where the combined visible sticker is too small, the primary character component is too small, the character/text blocks are detached, the layout is too sparse, edges are touched, the canvas is fully opaque, or magenta fringe remains.

6. Return a complete output folder:
   - Static packs: `main/01.png`, `main/02.png`, ...
   - Animated packs: `main/01.gif`, `main/02.gif`, ...
   - `thumbs/01.png`, `thumbs/02.png`, ...
   - `cover.png`
   - `icon.png`
   - `banner.png`
   - `reward-guide.png`
   - `reward-thanks.png`
   - `manifest.json`
   - `metadata.csv`
   - `qc-report.json`
   - `prompts/`
   - Use a unique job-scoped output directory, for example `new-year-happy-sticker/` or `new-year-happy-preview/`. Do not create generic root-level `raw/`, `main/`, `thumbs/`, `frames/`, `prompts/`, or `out-preview/` folders in the current workspace for a real task.

7. Final delivery gate:
   - Immediately before any final user-facing delivery claim, rerun `scripts/wechat_sticker_pack.py qc` with default checks enabled.
   - Open `qc-report.json` and confirm `ok: true` and `failed: []`.
   - If delivering an expanded pack, verify directory name, archive name, manifest `count`, `metadata.csv` row count, preview grid, and final QC expected count all agree.
   - The default production QC rejects manifests whose `status` is `preview`, `preview_not_submission_ready`, `diagnostic`, or `mockup`. Do not bypass this with `--allow-preview-status` for final delivery.
   - The default production QC rejects Unicode emoji characters and restricted visual-policy terms, including emoji and national-flag terms, in `manifest.json` and `prompts/`. If it fails, remove or rewrite the source prompt/copy and regenerate affected assets; do not submit assets that used emoji-like or national-flag visuals.
   - The default production QC rejects cover/icon files that still have full-canvas opaque backgrounds, especially black or dark backgrounds. Passing dimensions and file size is not enough for transparent assets.
   - If `ok` is not true, do not say the pack is complete, WeChat-ready, accepted, or QC-passed. Report the failed checks and continue regenerating or stop with a clear failure state.
   - Do not rely on an older `qc-report.json` after any file, manifest, asset, or script change. Rerun QC after the last mutation.
   - Do not package `.DS_Store`, temporary logs, failed QC reports as the only cited report, or source-only scratch folders into the final archive unless they are intentionally part of the audit bundle.
   - Do not create or preserve an alternate local script path that bypasses the shared postprocessor for production art. Any `/tmp/*.py`, PIL/ImageDraw script, canvas script, or pack-specific generator that creates main sticker art, banner, reward guide, or reward thanks is a diagnostic/mockup only and must not be represented as final output.
   - Do not start a long-running Seedance task and then leave the turn without either waiting for completion, recording the task id/report path, or clearly marking the run as incomplete. If interrupted or resumed, first check whether a pending video task/report exists before starting another paid candidate.

## Agent Rules

- Decide the sticker list yourself when the user provides only a character or theme.
- Use user-provided images as references only, unless the user explicitly says to convert that exact image into a sticker.
- When the user provides a reference image, inspect it visually and translate it into written character/style anchors; do not pass that image path into sticker processing commands.
- Do not create the pack by cutting out a user-provided image, resizing it, or adding text with local scripts.
- If a generated example has been created, do not ignore it and restart from the user-provided image. The generated example becomes the visual source of truth unless the user rejects it.
- For every main sticker, banner, reward guide, and reward thanks asset, first create a new raw image with `image_gen`; then use local scripts only for deterministic sizing, transparency cleanup, thumbnail export, metadata, and QC.
- If the only available visual input is a user image, describe it as a reference in the `image_gen` prompt and regenerate the asset in the chosen pack style.
- `process-sticker --input` and `make-asset --input` should receive image-generated raw files, not user-uploaded reference files.
- The file passed to `process-sticker --input` or `make-asset --input` must match the asset's `postprocess_input_path` in `manifest.json`.
- For animated packs, never batch-process uninspected sheets. Inspect 1-2 pilot sheets first, then inspect every later raw sheet before final GIF export.
- For animated packs, inspect both the raw sheet and the processed GIF. A GIF can pass dimensions and still fail motion quality.
- For new animated sticker requests, do not start by proposing a 4x4 sprite sheet. Start with Seedance `green_screen_video` or `background_video` unless the user explicitly asked for sprite sheets or approved fallback.
- Before any new animated generation, state or write a compact mode lock. If the lock says video mode, do not inspect or reuse old sprite prompts as the current prompt template.
- Do not let an old `preview_not_submission_ready` sprite manifest, old `raw/NN.png`, old `prompts/NN.prompt.txt`, or previous "dog-run" sprite example override the current video-mode default. Diagnostic reads are allowed; mode inheritance is not.
- For video-based animated packs, inspect the MP4 visually before keying, then inspect the keyed PNG frame sequence before GIF export. Reject videos with background color drift, shadows, green spill, identity drift, text morphing, camera zoom, frame wrap, or loop jumps. Do not reject solely because the intended action is large or because `visual diff outlier ratio` is around 2 when the movement is coherent.
- For green-screen video mode, keep both outputs when useful: a transparent GIF from keyed frames and a background GIF preview from the source video. Name them explicitly so the transparent and background versions cannot be confused.
- For background GIF mode, inspect whether the background is relevant to the theme and emotion. Reject generic or unrelated backgrounds even if the motion is smooth and the file passes technical QC.
- For any motion more complex than `micro_expression`, create a single pilot first and keep the pilot folder with `raw/`, `frames/`, `main/`, `thumbs/`, `prompts/`, `manifest.json`, `raw/*.inspect.json`, and `qc-report.json` so the motion decision is auditable.
- For sprite-sheet `controlled_full_body`, the pilot is mandatory. If the pilot reaches the dog-run gold reference and final QC has `0 failed`, allow that motion tier for similar stickers in the same pack. If it fails, step down the motion ladder: `controlled_full_body` -> `single_limb` -> `head_only` -> `micro_expression`.
- For Seedance/video `controlled_full_body`, the pilot is still mandatory, but the dog-run sprite-sheet visual-diff thresholds are not the admission gate. Keep or regenerate based on visible artifacts: identity drift, scale breathing, camera movement, green-screen contamination, text/prop morphing, bad loop closure, or discontinuous jump cuts. If those are absent, large action is allowed.
- If every raw `*.inspect.json` is `ok: false`, stop the run and regenerate prompts or lower the motion profile. Do not continue into packaging.
- If a raw sheet has visible pose swaps, scale breathing, center-step outliers, visual-diff outliers, loop mismatch, crossed cell edges, text morphing, or inconsistent props, regenerate the raw sheet instead of trying to fix it in code.
- If a candidate raw sprite is much worse than the dog-run gold reference, stop and regenerate instead of accepting "close enough." Example red flags from failed pilots: `center_step_outlier_ratio` around 3-5, `diff_outlier_ratio` around 2.3-2.8, `loop_diff_ratio` around 2.0-2.6, or any `max_edge_pixels` / `max_thin_top_sliver_components` above 0.
- If a raw sheet passes inspection but shows mild whole-subject drift in preview, process with `--stabilize-position` and compare the processed GIF. If QC passes and the visual motion is smoother, use the stabilized output; if stabilization makes the intended motion stiff, wrong-footed, or cropped, regenerate with a clearer prompt.
- Do not use `--no-reject-raw-sheet`, row-picking, first-row reuse, manual frame duplication, or "stable-frame" reassembly for production outputs. These are diagnostic tactics only and must not appear in a final manifest.
- Do not replace a failed animated sheet with a locally animated still cutout just to pass dimensions, frame count, or file-size QC. That is a preview/mockup, not a production WeChat animated sticker.
- If a processed GIF appears to wrap a foot, cup, tail, subtitle, or lower-row fragment onto the top edge, inspect the raw 4x4 cells and the QC `thin top sliver components` result. This almost always means the previous row crossed the cell boundary; regenerate with stronger margin constraints instead of accepting the GIF.
- If a processed GIF has visible magenta fringe, reprocess with the current soft chroma-key defaults. If fringe remains, regenerate with a cleaner silhouette prompt.
- If processed PNG frames look stable but the final GIF jumps, reprocess with the shared `save_gif` path instead of a custom exporter. Transparent palette holes can remove low-alpha foreground pixels and create fake jumps.
- If cover or icon shows a black/dark background after export, treat it as a source-generation failure. Regenerate a shared cover/icon source on pure `#FF00FF` with a clean opaque character silhouette; do not accept an opaque PNG just because dimensions pass.
- If the main sticker needs exact Chinese text, prefer keeping the text static and the character animated. If image generation makes the text wobble, morph, or shift across frames, regenerate without animated text or ask whether a stable local typography layer is acceptable.
- For static text stickers, if image generation already produced a good readable text composition, do not replace it with local typography. If exact local typography is used, it must follow `approved_static_text_composite`, preserve the original raw art, integrate the text plaque with the character, and pass static layout QC.
- Do not accept 8-frame / 2x4 animation for standard-quality output. Use it only with explicit compact-mode acceptance and run QC with `--allow-compact-motion`.
- Keep animated text, props, face marks, clothing, and key silhouette anchors stable across frames unless that exact element is the intended action.
- Prefer micro-animation ideas only for sprite fallback, exact-text stickers, prop-heavy stickers, or high-risk multi-object scenes. For Seedance/video mode, expressive full-body actions such as run, dance, hop, bow, spin, and cheer are allowed after the video pilot is visually coherent and passes concrete artifact checks.
- For packs with Chinese text inside the sticker, never animate the text or caption plaque. Keep the readable text area as the visual anchor. In Seedance/video mode, the character can still use larger motion around or beside the locked text when it remains readable; in sprite fallback, prefer a small local character detail.
- Do not discard a usable `image_gen` result and replace it with a local photo cutout workflow.
- Do not create a static sticker album from one 8/16/24-up generated sheet and then blindly crop cells. Production static stickers need one image-generated artwork per sticker, unless every sheet cell has already passed subject bbox, edge, and layout QC.
- Do not make the whole pack from one repeated cutout plus small icons, pose jitters, or local text overlays.
- Do not create a custom PIL/canvas "generator" for the artistic part of the pack; pack-specific scripts may only organize files, call the shared postprocessor, or create previews.
- Do not force the user to provide exact counts unless the intended output is ambiguous.
- Keep album packs internally consistent: same character identity, same rendering style, same line weight, same palette family, and comparable subject scale.
- Make stickers visibly different from each other in pose, expression, prop, or scene.
- Use Chinese meaning keywords for WeChat submission unless the user requests another language.
- Avoid text inside main sticker images unless the user explicitly requests text stickers.
- Banner, reward guide, and reward thanks images should include short theme-specific Chinese copy by default.
- For banner and reward assets, prioritize graphic design quality: composition, hierarchy, rhythm, background shapes, props, color blocking, and coherent story.
- Before generating banner or reward assets, write an explicit design brief; the prompt must describe the whole graphic system, not just the text.
- Never use Unicode emoji, system/platform emoji, yellow smiley faces, round reaction icons, or Emoji-derived secondary creation in main stickers, cover, icon, banner, reward guide, reward thanks, metadata, prompts, or design briefs.
- Never use national flags, flag icons, flag stickers, flag-pattern backgrounds, flag-colored patriotic symbols, or recognizable national flag fragments in main stickers, cover, icon, banner, reward guide, reward thanks, metadata, prompts, or design briefs.
- Do not create banner or reward assets by placing a character on a plain background and adding text afterward.
- Do not generate banner or reward assets from prompts like only `"写上 XXX"` or `"一张有 XXX 文字的图"`; those are insufficient.
- Make typography part of the generated design direction for banner and reward assets; do not rely on late-stage overlay text as the main design.
- If readable Chinese text is required and image generation cannot render it reliably, stop and ask whether local typography overlay is acceptable; do not silently switch to overlay text.
- For text stickers, make each image visually different; trivial shake/zoom variations are weak for review.
- Never use copyrighted characters, celebrity likenesses, existing sticker IP, platform UI, or unrelated decorative content unless the user provides rights and asks for it.
- Treat file-size limits as QC thresholds, not guaranteed acceptance; if a generated GIF is too large, first reduce colors or simplify motion, then fall back to fewer frames if needed.

## Failure Patterns To Avoid

Reject these workflows even if they produce files that pass dimension QC:

- One `image_gen` concept board is generated, then ignored.
- One good generated example is shown, then production is built from the user reference image cutout plus local text.
- A new animated sticker request defaults to 4x4 sprite-sheet generation even though Seedance video mode is available.
- A new animated sticker request reads an old `preview_not_submission_ready` sprite project, old manifest, or old sprite prompt and then proposes `4x4`, `16 frames`, or sheet processing before completing the Seedance mode-lock preflight.
- A local script saves cutouts or composites into a hand-named `.codex/generated_images/<pack-name>/` folder and records those as `image_gen_source_path`.
- The final pack is made from the user's original photo or one cutout of it.
- Every sticker uses the same body pose with only local text, emoji-like icons, checkmarks, hearts, or tiny decorations changed.
- Any sticker, banner, reward guide, reward thanks, cover, icon, prompt, manifest copy, or design brief uses Unicode emoji, yellow smiley faces, round reaction icons, system/platform expression symbols, or Emoji-derived secondary creation. This can block or close WeChat reward eligibility.
- Any sticker, banner, reward guide, reward thanks, cover, icon, prompt, manifest copy, or design brief uses real country flags, flag icons, flag stickers, flag-pattern backgrounds, flag-colored patriotic symbols, or recognizable national flag fragments.
- A high-quality animated pack is generated as 2x4 / 8-frame sheets and then treated as finished.
- A 2x4 sheet is locally tweened or frame-blended to fake smoothness instead of regenerating a proper 16-frame sheet.
- A failed raw sheet is packaged with `--no-reject-raw-sheet`, or the output is assembled from only the "good" row / "stable" frames of a failed sheet.
- A failed raw sheet is processed into a preview GIF and stored in the production `main/` / `raw/NN.png` paths, making the folder look deliverable.
- A relaxed preview QC run overwrites `qc-report.json`, leaving a passing report in the production report slot.
- A relaxed or custom-threshold QC report is renamed to look like an unqualified production pass without recording `qc_profile` and the exact threshold overrides in `manifest.json`.
- A preview QC report has `ok: false`, but the result is described as usable, ready, generated, complete, or suitable for chat use.
- A QC command fails, but the shell command ends with `cat`, `find`, `ls`, or `|| true`, causing the overall command to look successful.
- `preview-original` is generated from the strongest raw sheet, but later cleanup variants hide it, omit its QC, or get recommended without side-by-side comparison.
- A cleanup/crop/no-energy variant is chosen because metrics or file size improved, even though it removed the character appeal, main action, energy effect, or user-preferred look.
- Full `inspect-sheet` JSON, full `qc-report.json`, full `--help` output, full prompt files, per-file media listings, or embedded preview/base64 payloads are printed into chat during normal generation. These belong on disk; use summaries and contact sheets in terminal output.
- A production run writes ad hoc Python snippets for routine `metadata.csv`, preview grid, or packaging tasks instead of using shared script commands.
- A full 8/16/24 animated album is generated before a single pilot sprite pattern passes, wasting image calls and context.
- The workspace root gets generic `raw/`, `main/`, `thumbs/`, `frames/`, `prompts/`, or `out-preview/` folders instead of a named job output directory.
- A new test reuses an old job directory such as `robot-mechanical-dance/`, overwriting prior `video/`, `main/`, `manifest.json`, `qc-report.json`, or local scripts. Use a fresh timestamped or theme-specific output directory for every generation run.
- An 8-pack is expanded to 16 or 24 stickers in place, but the final folder name, archive name, manifest `design_note`, `metadata.csv`, preview grid, or QC expected count still describes the old count.
- A request for a "表情包" is ambiguous, but the workflow silently creates only one sticker and returns it as the requested pack.
- Only one or two candidates fail, then the workflow stops and presents a failed-motion preview as the main deliverable instead of continuing toward a production candidate or reporting production failure.
- Several sprite sheets are generated, but the final GIF is made from an earlier failed sheet because `raw/NN.png` was overwritten or picked by directory order instead of a passing `selected_candidate_id`.
- `manifest.json` lacks `generation_candidates`, `selected_candidate_id`, or `selected_inspect_path` for an animated sticker.
- `manifest.json` records an `image_gen_source_path` but `postprocess_input_path` points to an edited, spliced, or reassembled file that is not byte-for-byte identical, unless this is an approved static text composite with `typography_overlay_approved`, `typography_overlay_reason`, and `original_raw_path`.
- QC has any failed items for main sticker format, static layout, animated motion, manifest audit, banner bytes, reward-guide bytes, or reward-thanks bytes, but the folder is treated as deliverable.
- In sprite-sheet fallback, every animated sticker moves the whole body, redraws props, or changes multiple regions at once. Seedance/video mode may use larger motion, but still must keep identity, camera, scale, text, props, and loop continuity stable.
- A text sticker animates the caption/plaque together with the character or lets text wobble/morph. The caption/text area should stay locked; Seedance/video mode may animate the character around it when readability survives.
- The final main sticker PNG/GIF has visible magenta/purple key-color rim, dirty halo, hard background chips, or edge spill.
- A green-screen video GIF has visible green halo, green spill, background patches, alpha holes, or flickering keyed edges.
- A first-last-frame Seedance request uses the exact same start image as `last_frame` without explicit loop-closure approval and reason.
- A Seedance MP4 is reused with `--video` or similar for a new candidate without recording `video_reuse_reason`, candidate id, and the unchanged source task provenance.
- Rough keyed frames, extracted RGB frames, and selected ping-pong/final frames are mixed in one `keyed_frames/NN` folder, so the audited frame count no longer matches the final GIF.
- `frame_sample_count`, selected keyed output frame count, and final GIF frame count diverge after reprocessing.
- Video frames are keyed, alpha-cropped, and re-centered independently per frame, causing artificial center-step/scale-step jitter even when the MP4 motion is mild.
- A failed video candidate is repeatedly reprocessed into `main/NN.gif`, leaving a production-looking file while QC remains `ok: false`.
- A Seedance task report is hand-edited after generation to add missing top-level status/model/audio fields instead of being written in normalized form by the task runner.
- A per-job `seedance_task.py`, `process_green_video.py`, or similar production helper is created inside the output folder and becomes the actual workflow instead of a shared, tested skill script.
- A long-running Seedance candidate is launched, then the thread ends or is interrupted without a recorded final status, leaving the next run unsure whether a paid task already exists.
- More Seedance tasks are launched in parallel than can be tracked, leaving many running sessions with no compact index -> task/report map.
- Production frames contain visible anchor pixels, bbox corner dots, guide marks, or artificial stabilization handles.
- A video-based transparent GIF was created directly from MP4 without preserving keyed PNG frames, alpha hint, keying settings, and QC report.
- A background GIF uses a generic gradient, random interior, random landscape, abstract wallpaper, or unrelated decorative scene that does not support the pack theme or the sticker's emotion/scenario.
- Processed PNG frames are stable, but a custom GIF export introduces transparent holes or frame-to-frame bbox jumps.
- Banner, reward guide, or reward thanks images have white margins, letterbox bars, or a plain white border caused by contain fitting.
- Banner, reward guide, or reward thanks images are made by cropping a square or wrong-aspect source, cutting off the character, title, props, or call-to-action content.
- Banner, reward guide, or reward thanks images are plain color backgrounds with a pasted character and text.
- Banner, reward guide, or reward thanks images are visibly posterized, desaturated, or reduced to a tiny color palette by PNG quantization.
- Banner, reward guide, or reward thanks prompts contain only copy text and no layout/design brief.
- A custom local script paints the artistic content instead of processing `image_gen` output.
- The final report says QC passed but the creative-source rule was not followed.
- The assistant gives a final success message without rerunning QC after the last output mutation.
- `qc-report.json` has `ok: false`, missing `ok`, or non-empty `failed`, but the result is described as complete or ready.
- Banner, reward guide, reward thanks, cover, icon, or main sticker art is made by PIL/ImageDraw/canvas/local drawing and then described as image-generated artwork.
- Cover or icon is a PNG but still has a black, dark, white, or colored full-canvas background. Transparent album assets must actually contain transparent pixels around the character.
- A good image-generated static sticker is overwritten with a local text plaque, local caption, or ImageDraw typography layer, causing text/image misalignment or covering the character.
- Static sticker raw art is treated like a layout template instead of a finished image: the workflow clears part of the image, redraws text, or crops from multi-image sheets without a visual approval gate.

## Script Quick Start

Default animated mode preflight:

- New animated request: choose `green_screen_video` for transparent GIF or `background_video` for theme-background GIF.
- Set `video_input_mode: "first_last_frame"` unless the user explicitly chose first-frame only.
- Check `ARK_API_KEY` at runtime before any sprite-sheet prompt is written.
- The runtime check must not reveal the key: print only `present` or `missing`. If missing, ask the user to set `ARK_API_KEY` for the Codex process; do not paste or export the secret in a logged command.
- Create imagegen start/end frames, compare them side by side, submit Seedance with `generate_audio: false`, download MP4, extract/key frames, then encode GIF.
- If video access fails, stop and ask for approval before using sprite-sheet fallback.

Seedance shared-script path, use this instead of creating pack-local task or green-screen processors:

```bash
python3 scripts/seedance_video_task.py \
  --start out/start_frames/01.png \
  --end out/end_frames/01.png \
  --prompt out/prompts/01-video-prompt.txt \
  --video-out out/video/01-candidate-001.mp4 \
  --report-out out/reports/seedance-task-01-candidate-001.json \
  --duration 4 \
  --resolution 720p \
  --ratio 1:1

python3 scripts/process_seedance_green_video.py \
  --video out/video/01-candidate-001.mp4 \
  --frames-dir out/frames/01-candidate-001 \
  --keyed-dir out/keyed_frames/01-candidate-001 \
  --gif out/candidates/01-candidate-001.gif \
  --thumb out/candidates/01-candidate-001-thumb.png \
  --sample-count 36
```

After this, run QC on the candidate. Promote to `main/NN.gif`, `thumbs/NN.png`, final `keyed_frames/NN`, and manifest selection fields only after the candidate passes.

Routine album helpers, use these instead of one-off Python snippets:

```bash
python3 scripts/wechat_sticker_pack.py make-metadata \
  --output-dir out \
  --manifest out/manifest.json \
  --motion animated

python3 scripts/wechat_sticker_pack.py make-preview-grid \
  --output-dir out \
  --manifest out/manifest.json \
  --cols 4 \
  --output out/preview-grid.jpg
```

Sprite-sheet fallback quick start, only after explicit fallback approval:

Inspect and process an animated `4x4` raw sheet into numbered main GIF and thumbnail:

```bash
python3 scripts/wechat_sticker_pack.py inspect-sheet \
  --input out/raw/01-candidate-001.png \
  --output out/raw/01-candidate-001.inspect.json \
  --rows 4 \
  --cols 4 \
  --summary \
  --reject

python3 scripts/wechat_sticker_pack.py promote-candidate \
  --output-dir out \
  --index 1 \
  --candidate-id 01-candidate-001 \
  --candidate out/raw/01-candidate-001.png \
  --inspect out/raw/01-candidate-001.inspect.json \
  --source $CODEX_HOME/generated_images/<thread-id>/01.png \
  --manifest out/manifest.json

python3 scripts/wechat_sticker_pack.py process-sticker \
  --input out/raw/01.png \
  --index 1 \
  --output-dir out \
  --motion animated \
  --rows 4 \
  --cols 4 \
  --meaning "开心" \
  --duration 80
```

Standard stabilization pass:

```bash
python3 scripts/wechat_sticker_pack.py process-sticker \
  --input raw/01.png \
  --index 1 \
  --output-dir out \
  --motion animated \
  --rows 4 \
  --cols 4 \
  --meaning "开心" \
  --duration 80 \
  --stabilize-position
```

If `inspect-sheet` fails on `center_step_outlier_ratio`, `scale_step_ratio_max`, `diff_outlier_ratio`, or `loop_diff_ratio`, regenerate the raw sheet with a simpler motion prompt. These failures usually mean the model changed the pose, prop, text, or character shape too abruptly.

Use bottom-anchor smoothing only for foot-planted motion:

```bash
python3 scripts/wechat_sticker_pack.py process-sticker \
  --input raw/01.png \
  --index 1 \
  --output-dir out \
  --motion animated \
  --rows 4 \
  --cols 4 \
  --meaning "开心" \
  --duration 80 \
  --stabilize-position \
  --stabilize-anchor bottom \
  --stabilize-mode smooth
```

After processing, run QC and reject the GIF if temporal checks still fail:

```bash
python3 scripts/wechat_sticker_pack.py qc \
  --output-dir out \
  --expected-count 16 \
  --motion animated \
  --min-frames 12 \
  --summary
```

Only for explicitly accepted compact/preview animation:

```bash
python3 scripts/wechat_sticker_pack.py qc \
  --output-dir out-preview \
  --expected-count 8 \
  --motion animated \
  --min-frames 8 \
  --allow-compact-motion \
  --no-require-manifest \
  --no-require-candidate-audit \
  --no-require-raw-inspection \
  --report-name qc-report-preview.json \
  --summary
```

Process a static sticker:

```bash
python3 scripts/wechat_sticker_pack.py process-sticker \
  --input raw/01.png \
  --index 1 \
  --output-dir out \
  --motion static \
  --meaning "收到"
```

This writes `main/01.png` for static packs. Animated packs write `main/01.gif`.

Create album assets:

```bash
python3 scripts/wechat_sticker_pack.py make-asset --kind cover --input raw/cover-icon-source.png --output-dir out
python3 scripts/wechat_sticker_pack.py make-asset --kind icon --input raw/cover-icon-source.png --output-dir out --fit-scale 1.15 --align center
python3 scripts/wechat_sticker_pack.py make-asset --kind banner --input raw/banner.png --output-dir out
python3 scripts/wechat_sticker_pack.py make-asset --kind reward-guide --input raw/reward-guide.png --output-dir out
python3 scripts/wechat_sticker_pack.py make-asset --kind reward-thanks --input raw/reward-thanks.png --output-dir out
```

Run QC for a full album:

```bash
python3 scripts/wechat_sticker_pack.py qc --output-dir out --expected-count 16 --motion animated --min-frames 12 --summary
```

Run QC for a single sticker:

```bash
python3 scripts/wechat_sticker_pack.py qc --output-dir out --expected-count 1 --pack-type single --motion animated --min-frames 12 --summary
```
