# WeChat Sticker Prompt Rules

Use these rules when writing prompts for raw image generation.

## Source Policy

Use Codex image generation for the creative source art. User-provided images are visual references by default, not final production inputs.

Do not turn a supplied image directly into a sticker pack by cropping, cutout extraction, resizing, or adding local text. Only do exact-image conversion when the user explicitly asks for that.

When a user provides an image as a character or style reference, inspect it and convert it into textual anchors such as species, silhouette, material, color, expression, and mood. Then write prompts that say to create a new original sticker-pack character inspired by those broad traits, and regenerate each sticker, banner, reward guide, and reward thanks asset with `image_gen`.

Do not include the reference image path in local processing commands. The only file paths that should be passed to sticker postprocessing are raw files created from Codex image generation output.

Every generated sticker and album asset must have an `image_gen_source_path` in `manifest.json` that points to the actual saved Codex image-generation file under `.codex/generated_images/<thread-id>/<file>`.

Do not create a hand-named folder inside `.codex/generated_images` and fill it with locally composed PNGs. A path like `.codex/generated_images/my-pack/01.png` is a local derivative unless it was actually written by the image generation tool in the active thread directory.

Every generated sticker and album asset must also have `postprocess_input_path`. It must be the same file as `image_gen_source_path`, or an exact byte-for-byte copy, except for `approved_static_text_composite`, where it may be the derived composed file if the manifest records `typography_overlay_approved: true`, `typography_overlay_reason`, and `original_raw_path`. This prevents a workflow that records a generated reference image but secretly processes the user's uploaded image.

Do not use Emoji or Emoji-derived material anywhere in the pack. This includes Unicode emoji characters, system/platform emoji, emoji-style yellow faces, round reaction icons, smiley-face symbols, WeChat/QQ-like built-in expressions, and prompts that ask for `emoji style` decoration. WeChat reward assets can be rejected or have reward eligibility closed for Emoji secondary creation.

Avoid national flag material anywhere in the pack. Do not use real country flags, flag icons, flag stickers, flag-pattern backgrounds, flag-colored patriotic symbols, or recognizable national flag fragments in main stickers, cover, icon, banner, reward guide, reward thanks, prompts, copy, metadata, or design briefs.

For dynamic stickers, default to video-based motion generation, not sprite sheets. Use `green_screen_video` for transparent GIFs and `background_video` for theme-background GIFs. Use `sprite_sheet` only when the user explicitly asks for it, when Seedance/Ark access is unavailable and the user approves fallback, or when the motion is a tiny controlled micro-motion.

Before writing any animated prompt for a new run, lock the mode in the current manifest or notes: `animated_source_mode`, `video_input_mode`, `video_model`, `video_audio_policy`, output directory, and whether `sprite_fallback_approved` is true. Do not write sprite-sheet wording until the lock allows it.

Old project folders, old manifests, old prompt files, and old Codex thread outputs are diagnosis material only. Do not inherit their `4x4`, `16-frame`, `wide strip`, `rows`, `cols`, candidate, or prompt format for a new animated request unless the user explicitly asks to reuse that exact project. A `preview_not_submission_ready` manifest is especially a warning, not a template.

For Seedance video mode, default to first-last-frame image-to-video. Generate a start frame and a loop-compatible end frame with imagegen, then submit them as `role: "first_frame"` and `role: "last_frame"`. Use first-frame-only generation only when the end frame has no useful meaning, repeatedly increases identity drift, or the user explicitly chooses first-frame mode.

Before calling Seedance, inspect the start/end frame pair side by side. The character identity, proportions, face/screen details, material, colors, outline thickness, camera, subject scale, baseline, and green/background color must match. If the pair is inconsistent, regenerate the end frame from the locked start-frame identity; do not rely on Seedance to merge two different character designs.

If the same image is intentionally used for both `first_frame` and `last_frame`, record that as an explicit loop-closure choice with `end_frame_same_as_start_approved: true` and a reason. Otherwise, first-last-frame mode must use a real generated end pose. Do not use the start image as the last frame just to satisfy the API shape.

If a Seedance video candidate is generated but the visual result fails, do not silently downgrade the final sticker to `image_gen_loop`, a local still-image transform, or a cutout bounce/rotation loop. Regenerate Seedance with a simpler prompt or mark production as failed. A video-mode deliverable must remain auditable from MP4 -> extracted/keyed frames -> GIF.

For text stickers, prefer visual expression over text. If exact Chinese text readability is critical, either generate finished integrated text in the image model or use the approved static text composite workflow. Never silently replace image-generated sticker design with a cheap local caption; the local text layer must be deliberate, integrated, manifest-recorded, and QC-checked.

## Main Sticker Prompt Rules

Always specify:

- A single recurring original character or character pair.
- Clear emotional intent and chat scenario.
- Simple readable pose and expression.
- Transparent-background-ready artwork on solid flat `#FF00FF` background.
- Centered subject, full silhouette visible, no cropping.
- Leave comfortable margin on all sides.
- Same art style, line weight, palette, and character proportions across the whole pack.
- No UI, no platform logos, no unrelated objects, no copyrighted characters.
- No Emoji, no Unicode emoji characters, no system/platform emoji, no emoji-style yellow smiley faces, no round reaction icons, and no Emoji-derived secondary creation.
- No national flags, flag icons, flag stickers, flag-pattern backgrounds, flag-colored patriotic symbols, or recognizable national flag fragments.
- For transparent assets, use a clean opaque sticker silhouette. Do not use drop shadows, glow, smoke, translucent edge effects, wispy hairs fading into the background, magenta/purple outlines, or contact shadows on the `#FF00FF` key background.
- Avoid colors close to `#FF00FF` on the outer edge of the character. Purple or pink accents are safer inside the silhouette, away from the transparent boundary.

For animated stickers:

- Two animated source modes are allowed:
  - `green_screen_video`: default for transparent animated stickers; Seedance creates a short green-screen clip from first/last frames, then frames are keyed into a transparent GIF.
  - `background_video`: default when the user wants a non-transparent animated GIF with a theme-related background; Seedance should still use first/last frames by default.
  - `sprite_sheet`: fallback/special request mode; image generation creates a 4x4 or similar frame sheet, then the local processor extracts frames.
- For new animated sticker requests, start by planning `green_screen_video` or `background_video`. Do not propose `4x4` sprite sheets first unless the user asked for sprite sheets or the video route is unavailable.
- If a previous thread or old folder contains a sprite prompt, translate only the useful motion idea into video-mode language. Do not copy its sheet/grid wording into the new prompt.
- For `sprite_sheet`, prefer a smooth `4x4` sheet: exactly 16 equal cells, 4 rows by 4 columns.
- For complex `sprite_sheet` motion, use a 20-frame `5x4` or `4x5` sheet if file size allows, then reduce colors or simplify motion during packaging.
- For `sprite_sheet`, use `3x4` only for simple motions when the action can remain smooth with 12 frames.
- For `sprite_sheet`, use `2x4`, `1x4`, or `2x2` only as preview/compact fallback after the user explicitly accepts less smooth animation. Do not use 2x4 for standard-quality pack output.
- For video modes, do not apply the 16/20-frame sprite-sheet limit. Sample GIF frames adaptively from the downloaded MP4: 24-32 frames for light motion, 36-48 frames for dance/run/spin/complex motion, and reduce frame count only when file size or true temporal artifacts require it. Do not reduce sampling or downgrade motion merely because intended large action raises visual-diff metrics.
- Choose the smallest motion profile that communicates the emotion:
  - `micro_expression`: only blink, pupils, mouth, blush, sweat drop, or tiny sparkle changes.
  - `head_only`: head tilts or nods subtly while body, paws, feet, tail, props, and text remain unchanged.
  - `single_limb`: exactly one paw, ear, or tail moves; torso, feet, face proportions, props, and text remain unchanged.
  - `prop_only`: one small prop moves while the character remains unchanged.
  - `controlled_full_body`: one simple cyclic body action such as run-in-place, dance, hop, bow, spin-in-place, or cheer; allowed for Seedance/video mode after a visually coherent pilot, and for sprite-sheet fallback only after a pilot reaches the dog-run gold reference.
- Use tiered admission rather than a blanket micro-animation limit. Default to `micro_expression`, `head_only`, or `single_limb` for sprite-sheet fallback, exact-text stickers, prop-heavy stickers, or multi-object scenes. For Seedance/video mode, try expressive `controlled_full_body` when the subject is simple enough to keep identity, scale, text, props, and baseline stable.
- `controlled_full_body` admission requirements for video mode: single subject, one cyclic action, no moving caption text, no moving large prop, fixed camera, fixed baseline, stable face/head/body mass, clean key/background, and a visually coherent loop. A high visual-diff ratio by itself is acceptable when it reflects intended large motion rather than redraw/jump artifacts.
- If a video `controlled_full_body` pilot fails because of identity drift, scale breathing, camera movement, green-screen contamination, text/prop morphing, frame wrap, or discontinuous jump cuts, regenerate the video prompt or frames. Step down the motion ladder only when the user wants safer/smaller motion or repeated video candidates fail for the same artifact.
- Build motion with clear in-betweens: rest, anticipation, action, follow-through, recovery, and a final easing frame that is close to frame 1.
- Use one simple cyclic action per sticker. Do not combine several changes at once, such as bounce plus eating plus sparkles plus moving text.
- Avoid jump cuts; each frame should change only slightly from the previous frame and should follow a visible motion arc.
- Keep the camera locked, the floor/baseline fixed, and the character's core body size stable.
- Keep props visually identical across frames unless the prop movement is the main action.
- Keep eyes, mouth, ears, hands, clothing, and accessories from morphing randomly.
- If text appears in the animated sticker, keep the wording, placement, size, style, and color identical in every frame. Only the character should animate unless the user specifically requests animated text.
- One-line animated prompts are not enough. For Seedance/video mode, each prompt must include the video mode, first/last-frame role, motion profile, intended action, explicit locked elements, fixed camera/framing, loop requirement, subject scale/baseline constraints, and green-screen or theme-background constraints. For sprite-sheet fallback, also include grid/cell layout, margin, cell-edge constraints, and frame-by-frame arc.
- For text stickers, lock the whole caption plaque by default. In Seedance/video mode the character can still perform a larger action around or beside the locked text if readability remains strong; in sprite-sheet fallback, the safest motion is one local change: blink, side-eye, mouth open/close, small head tilt, one paw lift, or one sweat/sparkle mark.
- Avoid animating chairs, tents, backpacks, maps, umbrellas, sunglasses, signs, cups, bowls, and large props. If props are present, write that they are static anchors and must not rotate, resize, redraw, or change position.
- For exact Chinese text stickers, prefer static text with animated character motion. If the image model cannot keep text stable across frames, regenerate without animated text or use an approved stable typography layer in postprocessing.
- Keep the same subject size, camera, and baseline throughout the video or sheet. For sprite-sheet fallback this applies to every cell.
- For Seedance/video controlled full-body motion, keep the same identity, head size, body mass, camera, subject scale, and baseline throughout the clip, but allow expressive actions such as running, dancing, jumping, spinning, bowing, cheering, waving, clapping, rolling, or dramatic reaction poses. The motion should be purposeful and loop-friendly, not tiny by default.
- For sprite-sheet controlled full-body motion, keep the motion simpler and cell-safe: one cyclic action, same baseline, same body mass, limited torso movement, and clean return to frame 1.
- No borders or grid lines.
- For sprite-sheet fallback, no body part, prop, shadow, text, or effect may cross cell edges. Leave enough empty `#FF00FF` padding inside every cell so feet, cups, tails, subtitles, and motion marks never touch the cell boundary.
- For sprite-sheet fallback, prevent adjacent-cell bleed: the bottom of one row must not enter the top of the next row, and the right side of one cell must not enter the left side of the next cell. If any thin strip from a neighboring frame appears along a cell edge, the sheet must be regenerated.
- Keep motion readable at `240x240`.
- Prefer expressive video actions when using Seedance: run, dance, hop, spin, bow, clap, cheer, wave, peek, panic reaction, dramatic sigh, roll, or playful full-body reaction. Prefer smaller local changes only for sprite fallback or text/prop-heavy cases.
- For loops, make the last frame naturally return to the first frame.
- For sprite-sheet fallback, generate 1-2 pilot sheets first and inspect them before batch generation. Regenerate if the sheet changes scale, drifts position, has center-step outliers, has per-frame scale jumps, has visual-diff outliers, swaps pose abruptly, changes props/text unexpectedly, crosses cell edges, fails to loop, or leaves visible chroma-key fringe.
- Preserve every generated pilot as a named candidate. Use `raw/NN-candidate-001.png`, `raw/NN-candidate-002.png`, etc., with matching inspect JSON files, and record the candidate list in `manifest.json`.
- Promote only a candidate whose inspect JSON has `ok: true`. The production `raw/NN.png`, `raw/NN.inspect.json`, `main/NN.gif`, and manifest selection fields must all point back to the same selected candidate.
- Use `promote-candidate` for production promotion instead of manual copy. Manual `cp` is allowed only for preserving candidate files, not for choosing the production source.
- Keep failed-candidate previews out of the production folder. If a failed candidate is processed for visual review, write it to a separate preview output directory and run relaxed QC with `--report-name qc-report-preview.json` so it cannot overwrite production `qc-report.json`.
- If preview QC still has `ok: false`, label it diagnostic only; it is not a usable sticker preview and should not be presented as the generated result.
- For failed but visually strong sheets, always keep `preview-original/` before making cleanup variants. Cleanup can reduce edge/size problems but may destroy the best-looking action.
- If the user prefers `preview-original` or another named preview variant, record that preference and recommend that variant for preview review even if automated metrics are worse.
- Compare preview variants side by side: original, cleanup/crop, no-effect, stabilized, and any other derivative. Do not rank by metrics alone; include character appeal, action readability, retained effects, and user preference.
- When the task is to generate a sticker rather than merely preview one, keep regenerating improved candidates until a production candidate passes or the run is explicitly stopped as a production failure. Do not present a failed-motion preview as the completed result after only one or two failed candidates.
- Keep all raw, prompt, preview, and output folders under a named job directory. Avoid generic workspace-root folders such as `raw/`, `main/`, `thumbs/`, `frames/`, `prompts/`, or `out-preview/`.
- Keep terminal output compact. Write full inspect/QC JSON and prompts to files, then use `--summary` output or a short extracted summary in chat.
- Use shared helpers for routine output files: `make-metadata` for `metadata.csv` and `make-preview-grid` for the thumbnail contact sheet. Do not create these with ad hoc Python snippets during production runs.
- For expanded albums, keep folder name, archive name, manifest `count`, design note, `metadata.csv`, preview grid, and final QC expected count consistent with the final sticker count. If reusing an old 8-pack directory as the source, record `expanded_from_count`, `expanded_to_count`, and `source_pack_dir`.
- For album generation, do not batch-generate all stickers until one pilot prompt pattern has passed raw inspect and final QC.
- Select the latest passing candidate by default. Choosing an older passing candidate is allowed only with a concrete `selection_reason`; choosing an older failed candidate is never allowed.
- Do not overwrite `raw/NN.png` while trying candidates. Do not choose a final sprite by `find`, file order, mtime, or memory. The final source must be auditable via `selected_candidate_id`, `selected_inspect_path`, and `generation_candidates`.
- If a pilot fails, do not package it and do not salvage it by selecting only the best row or duplicating stable frames. Rewrite the prompt and regenerate a new complete sheet.
- If a sprite sheet has been generated, the final GIF must use that generated sequence after the raw sheet passes inspection. Do not crop one still cell from the sheet and locally animate bounce, blink, scale, offset, or opacity to imitate motion.
- After processing, QC the GIF. Regenerate or reprocess if it has any visible magenta fringe, dirty halo, background chips, full-canvas opaque frames, or fewer than 12 frames for standard-quality motion.
- If PNG frames look stable but GIF playback jumps, use the shared packer GIF encoder. Do not export GIFs with a custom quantizer that can map low-alpha foreground pixels to the transparent palette index.

For `green_screen_video` mode:

- Use Doubao Seedance 1.5 Pro for video generation by default.
- Seedance sticker videos must be silent: set `generate_audio: false`. Also set `watermark: false`.
- Keep the Ark API key out of all prompts, manifests, reports, generated files, and logs. Read it from `ARK_API_KEY` or another runtime-only secret source.
- Do not use a key pasted into chat as if it were an environment variable. Codex tool processes only see runtime env/secrets, not arbitrary chat text. Never paste the key into a command line to "fix" this, because commands are logged.
- Seedance task API is asynchronous. Save the task id, poll for completion, download the generated MP4, then extract frames and continue through keying/GIF QC.
- Use `duration`, not `frames`, for Seedance 1.5 Pro tasks.
- After downloading the MP4, sample the final GIF frames locally. Start with 36-48 frames for expressive full-body motion and 24-32 frames for subtle motion. If the GIF exceeds WeChat size limits, step down 48 -> 40 -> 36 -> 32 -> 28 -> 24 before lowering visual quality or accepting compact output.
- Record video provenance in the manifest: `creative_source: "seedance_video"`, `postprocess_input_path` equal to the downloaded MP4 path, `video_source_path`, `video_task_report_path`, `video_prompt_path`, `keyed_frames_dir`, and `transparent_gif_source`. Do not set video-mode production stickers to `creative_source: "image_gen"` just to pass an older source audit.
- Use fresh output folders per selected video candidate, or clear `keyed_frames/NN` before writing frames. Stale frames from an older candidate can make QC/auditing lie about what the final GIF used.
- Keep rough keyed frames and selected/ping-pong frames separate. The auditable final keyed frame folder should represent exactly the frames used for GIF encoding, and its count should match both `frame_sample_count` and the final GIF frame count.
- Use one fixed geometry transform for all frames in a video candidate. Never crop to each frame's alpha/bbox and recenter/rescale each frame independently; this creates artificial jitter and scale breathing. If framing is wrong, re-extract with fixed video-level scale/pad/crop or regenerate the MP4.
- Keep failed video candidates out of final production paths. Write candidate GIFs and keyed frames under candidate/preview paths, then promote into `main/NN.gif`, `thumbs/NN.png`, and final `keyed_frames/NN` only after QC passes or after explicitly marking the manifest as `preview_not_submission_ready`.
- Rerun QC after the final manifest edit, count expansion, metadata generation, preview grid update, archive packaging, and after any GIF re-encode or preview copy. The final answer must cite a QC report produced after the final manifest and GIF state. Stale reports are not evidence.
- If expressive Seedance motion needs custom temporal QC thresholds, record a named `qc_profile` and exact threshold overrides in the manifest and use a matching report name. Do not relax edge bleed, green spill, magenta fringe, frame wrap, text/prop morphing, dimensions, file size, or asset checks to make a production pack pass.
- Seedance task reports should be normalized when written, with top-level `status`, `model`, `generate_audio`, `watermark`, `duration`, `ratio`, `resolution`, `task_id`, and downloaded video path. Keep raw API responses too, but do not hand-edit reports after the fact to satisfy QC.
- Production Seedance submission and video postprocessing should use shared skill scripts, not one-off job-folder scripts. One-off scripts are diagnostic unless moved into the skill scripts area, made Python 3.9 compatible, and compiled before running paid API calls.
- Use first/last-frame video generation only after a static character identity is locked.
- Start and end frames must use pure flat green screen `#00FF00`, not a gradient, floor, studio, or green-tinted scene.
- For first-last-frame mode, both frames must have identical canvas size, aspect ratio, character identity, camera, subject scale, style, and background/key color. Generate the end frame as an imagegen original or imagegen-edited variant, not a local warp/rotation/pixel edit.
- The end frame must be a controlled action boundary: close enough to the start for looping, or a clear intermediate endpoint that returns naturally to the first frame. For waving, dancing, bowing, running in place, cheering, nodding, and spinning, use first-last-frame mode before trying first-frame-only generation.
- Keep the subject away from green/cyan colors, especially at the silhouette edge. Avoid green accessories, green clothing, green rim light, green props, transparent green effects, or neon green highlights.
- Prompt the video model for fixed camera, fixed framing, fixed character scale, stable face, stable body mass, no background change, no shadows on the green screen, no glow, no smoke, no motion blur, no text movement, and no prop morphing.
- For looped GIFs, make the final pose close to the first pose. If using separate end frame, it should be loop-compatible, not a completely different pose.
- If the sticker contains Chinese text, keep text outside the video motion or on a static plaque; video models often morph text.
- Extract keyed PNG frames before GIF export. Do not go straight from MP4 to GIF.
- Do not add visible anchor pixels, corner dots, bbox guide marks, or other artificial pixels to stabilize QC. If bbox stabilization is needed, compute anchors from alpha and write no visible guide marks into production frames.
- Green-screen cleanup must use chroma key plus despill: remove background green, suppress residual green halos by clamping edge green toward foreground red/blue, threshold tiny-alpha pixels before GIF quantization, then re-encode through the shared transparent GIF path. Run visible-green-spill QC after encoding; green-screen production GIFs should have at most 1 visible green-spill pixel after GIF quantization.
- Prefer CorridorKey-assisted keying when available for transparent output. It uses green/blue-screen unmixing with a coarse alpha hint to recover foreground color and alpha, which is better for soft edges than RGB threshold alone.
- CorridorKey needs two inputs per frame: the original green-screen RGB frame and a coarse alpha hint. The hint may come from rough chroma keying, BiRefNet, GVM, VideoMaMa, or another rough matte.
- Use `--screen-color green` for our green-screen workflow when running CorridorKey. If CorridorKey is unavailable, use the local green-screen keyer as fallback and treat edge QC more strictly.
- Do not bundle CorridorKey code or weights into this skill. Use it as an optional local external tool and respect its license, attribution, and paid API/software integration restrictions.

For `background_video` mode:

- The background must be designed for the sticker theme and the specific emotion/scenario. It should explain or amplify what the character is doing.
- Before generating a background GIF album, define a shared background system: palette, recurring motifs, scene vocabulary, depth level, and allowed variation per sticker.
- Use backgrounds from the character's world: study desk for exam packs, office desk for workplace packs, kitchen/tableware for eating packs, travel landmarks or luggage for travel packs, seasonal props for holiday packs, or story-specific scenery for custom themes.
- Keep the background stable across frames. Do not let the room, landscape, props, or lighting morph while the character moves.
- Avoid generic gradients, random rooms, abstract wallpapers, unrelated landscapes, stock-photo-like scenery, or decorative backgrounds that do not match the pack theme.
- Keep background contrast lower than the character and text. It should support readability, not compete with the sticker subject.

Good video-mode animated prompt pattern:

- "Video mode: green_screen_video. First and last frames are the same character on pure #00FF00 green screen. Generate an expressive loop-friendly dance with fixed camera, fixed character scale, stable face, no shadows, no smoke, no glow, no motion blur, no text movement, and final pose close to first pose."
- "Video input mode: first_last_frame. Use the first image as `first_frame` and the second image as `last_frame`. Keep the same character, same camera, same 1:1 canvas, same scale, same pure #00FF00 green screen, and interpolate only the intended arm wave between them."
- "Video mode: background_video. Theme: exam study puppy. Background: cozy study desk with notebooks, pencil cup, desk lamp, and small exam papers in the same soft pack palette. Keep background locked and slightly lower contrast while the puppy celebrates passing a quiz."
- "Motion profile: head_only. Only the head tilts 4-6 degrees left then returns. The body, feet, tail, text plaque, backpack, and all props remain locked while the camera and scale stay fixed."
- "Motion profile: micro_expression. Only eyes blink and mouth changes slightly. No body movement, no paw movement, no prop movement, no text movement."
- "Motion profile: controlled_full_body_run. A puppy runs in place with fixed camera, fixed body mass, fixed head size, fixed baseline, stable face, and no background drift. Legs cycle clearly, ears and tail follow through naturally, and the final pose returns close to the first pose for a seamless GIF loop."

Sprite-sheet fallback prompt pattern, only after explicit fallback approval:

- "Create a 4x4 16-frame looping sheet. The character stays on the same baseline and keeps the same body size. Frames 1-2 are rest, 3-4 anticipation, 5-8 main action, 9-12 follow-through, 13-16 return smoothly to frame 1. Keep the bowl/text/prop identical across frames except for the intended small movement."
- "Use pure flat #FF00FF background only. The character is fully opaque with a clean sticker edge; no shadow, glow, smoke, transparent fur wisps, magenta rim, or background texture."
- "Motion profile: head_only. Only the head tilts 4-6 degrees left then returns. The body, feet, tail, text plaque, backpack, and all props are identical in every cell."
- "Motion profile: single_limb. Only the right paw raises slightly and lowers. Keep torso, head size, feet position, tail, prop, and caption exactly fixed."
- "Motion profile: controlled_full_body_run. A small puppy runs in place with fixed camera, fixed body mass, fixed head size, and fixed baseline. Only legs cycle, with tiny ear and tail follow-through. Torso center may bob only very slightly. Frames 1-4 right-leg forward, 5-8 passing position, 9-12 left-leg forward, 13-16 smooth return to frame 1."

Weak animated prompt pattern:

- "小狗旅行动态文字表情，motion_profile=micro_expression，背景#FF00FF，锁定 body/text/props." This lists constraints but does not specify a frame arc, exact moving pixels, loop behavior, margin, or how locked elements should remain identical.
- "Make it excitedly eating, bouncing, sparkling, changing expression, with large text." This asks for too many simultaneous changes and often creates jumpy frames.
- "Make it furry with soft hairs fading into the background." This often creates dirty chroma-key edges.
- "Make the text bounce and redraw differently in every frame." This often creates text jitter and unstable GIF bounding boxes.
- "Make the dog rock in a chair with a tent and moving caption." This tends to redraw the chair, tent, body pose, and text at the same time.
- "Make it chew, blink, wag tail, bounce, and move the bowl." Too many regions change, so the GIF will usually shimmer even after stabilization.
- "Green screen video with cinematic lighting, green glow, soft shadow, motion blur, and floating text." This makes the key dirty and causes alpha flicker.
- "Use first and last frames with different crops, different character scale, different background colors, or unrelated poses." This invites cropping, identity drift, and jump cuts.
- "Accept a green-screen GIF because the action looks good even though green halo/background pixels remain." This fails transparent sticker quality; reprocess with stronger key/despill or regenerate.
- "Background video with a beautiful gradient / random cafe / random landscape." This creates a generic background that does not support the sticker theme or chat scenario.

## Motion Simplification Ladder

For sprite-sheet fallback, when a pilot or final GIF fails `visual diff outlier ratio` or `loop diff ratio`, regenerate with a simpler profile instead of trying to fix it in post:

1. Replace `controlled_full_body` with `single_limb`.
2. Replace `single_limb` with `head_only`.
3. Replace `head_only` with `micro_expression`.
4. Remove or freeze large props.
5. Remove animated text; keep text as a static plaque, or ask whether a local stable typography layer is acceptable.

For Seedance/video mode, do not apply this ladder solely because `visual diff outlier ratio` is high. Large movement is normal for video-derived stickers. Regenerate or simplify only when the high metric corresponds to visible non-intentional artifacts such as identity drift, scale breathing, camera zoom, prop/text morphing, frame wrap, broken loop closure, green spill, or abrupt jump cuts.

## FrameRonin-Inspired Stabilization Pattern

Use this only after the raw sheet passes `inspect-sheet --reject`.

The accepted dog-run pilot is the quality reference for smooth motion:

- raw sheet: `ok: true`, 16 frames, `center_drift 4.5`, `max_edge_pixels 0`, `max_edge_bleed_components 0`, `max_thin_top_sliver_components 0`, `max_magenta_fringe_pixels 0`
- temporal: `center_step_outlier_ratio 2.40`, `scale_step_ratio_max 1.03`, `diff_outlier_ratio 1.29`, `loop_diff_ratio 0.94`
- final GIF: `240x240`, 16 frames, about `321KB`, QC `0 failed`

Use this as a practical gold bar. A raw sheet that fails `inspect-sheet`, or has `diff_outlier_ratio > 1.6`, `loop_diff_ratio > 1.35`, edge spill, top sliver, text morphing, or prop redraw is not close to the dog-run result and must be regenerated, not stabilized into production.

1. Keep every processed frame on a full fixed `240x240` RGBA canvas.
2. Measure an alpha-based anchor per frame: `center` for floating/run-in-place motion, `bottom` for planted feet, or `feet` only when the lower contact points are clean.
3. Align frames toward the median anchor using `process-sticker --stabilize-position`.
4. Re-run final GIF QC and inspect the GIF visually.
5. Accept stabilization only when it removes mild whole-subject drift while preserving the intended action.

Recommended commands:

```bash
python3 scripts/wechat_sticker_pack.py process-sticker \
  --input raw/01.png \
  --index 1 \
  --output-dir out \
  --motion animated \
  --rows 4 \
  --cols 4 \
  --meaning "跑步" \
  --duration 80 \
  --stabilize-position \
  --stabilize-anchor center \
  --stabilize-mode median
```

Use `--stabilize-anchor bottom --stabilize-mode median` when the baseline is more important than the center point. If the action is a bow, jump, sit, stomp, or other foot-planted motion and median alignment feels stiff, try `--stabilize-mode smooth`.

Never use these as production fixes:

- `--no-reject-raw-sheet`
- `image_gen_loop`, `local_loop`, or still-image transform fallback after a Seedance video attempt
- first-row-only loops
- duplicating a few stable frames into 16 frames
- manually reordering frames from a failed sheet
- editing `postprocess_input_path` to a derived file while keeping the original `image_gen_source_path`, unless it is an approved static text composite with `typography_overlay_approved`, `typography_overlay_reason`, and `original_raw_path`
- extracting frames from the final GIF and presenting them as proof that the generated raw sprite sequence was used
- single-cell still cutout plus local micro-animation when a raw 4x4 sheet already exists
- PIL/ImageDraw/canvas-generated banner, reward guide, reward thanks, cover, icon, or main sticker art presented as image-generated production artwork
- a final delivery claim without a fresh QC run whose report has `ok: true` and an empty `failed` list

Recommended sprite-sheet fallback replacements when repeated sheet candidates fail:

- walking, bouncing, rocking, lying down then sitting up -> tiny head tilt or blink
- chewing with bowl movement -> mouth-only chew, bowl locked
- waving both paws -> one paw only
- chair/tent/backpack scene movement -> static props plus side-eye or blink
- excited sparkle bounce -> static character plus one or two small sparkles

For static stickers:

- Generate one production artwork per sticker on `#FF00FF`. Do not generate an 8/16/24-up production sheet and blindly crop it into final stickers.
- If the text is image-generated, generate one finished sticker including the character, expression, text plaque, and text when the user asked for text stickers.
- If exact Chinese text will be added locally, generate a high-resolution text-free character/pose artwork first, then compose text with the approved static text composite workflow.
- Keep expression and silhouette strong enough to read at phone size.
- Treat a good static generation as finished artwork. Postprocessing should cut out the magenta background and fit it into `240x240`, not casually redraw the layout.
- Approved local typography is not a loose caption. It must use an integrated plaque/label shape, professional CJK font, thick readable text fill, stroke or shadow, consistent palette, and careful padding.
- Keep the character and text as one compact composition: plaque touching, overlapping, or tucked under/near the character. Avoid a small dog far from a detached caption with empty space between them.
- Fit the final combined character-plus-text composition large enough for WeChat: the visible bbox should usually fill roughly 70-92% of the `240x240` canvas in width and height, with no edge contact.
- If generated Chinese text is bad, either regenerate with shorter wording, larger text, stronger contrast, and simpler plaque layout, or use the approved static text composite workflow while preserving an untouched original comparison.
- Run static layout QC after composition. Fail and fix outputs with tiny visible bbox, too-small primary character component, detached character/text blocks, low bbox fill ratio, magenta fringe, edge contact, or full-canvas artifacts.

Strong static prompt pattern:

- "Create one finished static WeChat sticker illustration, square canvas. Character: [locked original character identity]. Scene: [specific pose/action/emotion]. Include the exact simplified Chinese text: `[TEXT]` as large readable integrated sticker lettering on a high-contrast rounded comic plaque near the lower third, not covering the face. Use one compact composition where character and text feel connected."
- "Style: cute Chinese meme sticker, cohesive pack character, bold expression, clean opaque silhouette, phone-size readability, consistent palette and line weight."
- "Canvas: pure flat #FF00FF background only for chroma-key transparency, centered subject, full silhouette visible, generous margin, no shadow, no glow, no smoke, no transparent wispy fur, no magenta or purple outline, no border, no watermark, no emoji, no yellow smiley, no system emoji symbols, no national flags or flag icons."

Weak static prompt pattern:

- "Make 24 stickers in one sheet." This makes subjects small, causes crop errors, and loses production auditability.
- "Use this uploaded image and add text." This falls back to reference cutout instead of generating a new sticker-pack character.
- "Same dog, different words." This creates a weak pack with repeated pose and local-text dependence.
- "Put the text somewhere." This often produces detached or low-quality typography.

## Text Policy

Default to no text inside main sticker images unless the user asks for text stickers.

Default to theme-specific Chinese copy inside banner, reward guide, and reward thanks images. The copy must be part of the generated graphic design, integrated into the composition with intentional typography.

Do not put Unicode emoji characters in sticker text, asset copy, metadata, or prompts. Do not ask the model to draw emoji-like symbols. Use original pack-specific expressions and hand-drawn motifs instead.

Do not use flag symbols or ask for flag-like decoration in sticker text, asset copy, metadata, or prompts. If the pack needs celebration, travel, sports, festival, or cheering energy, use fictional pennants, ribbons, confetti, badges, abstract color blocks, or pack-specific props that do not resemble a real national flag.

When the user asks for text stickers:

- Keep the wording short.
- Use high-contrast lettering.
- Make the character, pose, or graphic action differ for every sticker.
- Avoid relying on trivial movement only.
- Prefer image-generated integrated text for static stickers when it is readable and attractive.
- Use approved static text composite when exact text matters, but start from text-free generated character art and make the text plaque part of the design. Do not place a second local caption over already generated text.
- Do a 1-2 sticker pilot before batching 8/16/24 static text compositions. Check subject size, text proximity, phone-size readability, and QC before generating the rest.
- After a pilot succeeds, reuse the same base prompt and vary only scene/action/text/meaning. This keeps style consistent and speeds up the rest of the pack.

## Generated Example Lock

When a generated example, pilot, or character source is visually accepted or used as the basis for the pack, treat it as the lock source:

- Record the original imagegen path as `style_lock_source_path` or `character_lock_source_path`.
- Use its identity, proportions, palette, and rendering style in later prompts.
- Do not use the user reference image as the production subject after the generated example exists.
- Do not make the final pack by extracting the user reference image and adding local text just because it is faster.
- If the generated example is not good enough, regenerate the example first, then continue from the new generated source.

## Album Asset Prompt Rules

Treat banner, reward guide, and reward thanks images as finished graphic-design key visuals. They should feel like cohesive promotional illustrations for the sticker pack, with intentional composition, visual hierarchy, designed negative space, color blocking, background motifs, related props, and a clear mood.

Do not solve these assets by simply placing the character on a plain background or adding late overlay text. Ask the image model to integrate the copy as part of the layout and keep it secondary to the visual idea.

Generate album asset sources in the final target aspect ratio from the start: banner as a wide `750x400` composition, reward guide as a horizontal `750x560` composition, and reward thanks as a square `750x750` composition. Do not generate a square source for reward guide or banner and then crop it into the target size. Keep text, faces, hands/paws, props, and reward cues inside a central safe area with generous margin.

Never use Emoji, yellow smiley faces, round emoji reaction icons, or platform/system expression symbols as decoration in banner, reward guide, or reward thanks assets. These images are especially sensitive because Emoji-derived material can prevent reward activation. Replace them with original motifs from the pack world: character poses, paws, bones, ribbons, badges, speech bubbles, abstract bursts, or scene props that match the theme.

Never use national flags, flag icons, flag-pattern backgrounds, or recognizable country-flag fragments in banner, reward guide, or reward thanks assets. Replace them with original graphic-design devices from the pack world: non-national ribbons, badges, abstract color blocks, confetti, speech bubbles, character props, or fictional symbols.

Before generating these assets, write a design brief. The prompt must include:

- Layout: where the character, title/copy, props, and focal areas sit.
- Visual hierarchy: primary focal point, secondary details, readable copy area.
- Typography: style, weight, integration with shapes or labels.
- Background system: patterns, color blocks, scene fragments, motifs.
- Theme props: objects related to the character or pack scenario.
- Palette and mood: emotional tone and contrast.

Prompts that only ask for a phrase or a character plus text are not acceptable.

Cover:

- Use the most recognizable front-facing version of the character.
- Generate a single cover/icon source artwork by default and use it for both `cover.png` and `icon.png`.
- Transparent `#FF00FF` extraction background.
- The raw source must not have a black, dark, white, or colored full-canvas background. If the generated source is not on pure `#FF00FF` or already transparent, regenerate before making cover/icon.
- No text.

Icon:

- Use a simplified head or clear face mark cropped/fitted from the same cover/icon source artwork by default.
- Do not generate a separate icon character unless there is a deliberate reason and the manifest records `cover_icon_identity_match_approved: true` with a reason.
- Transparent `#FF00FF` extraction background.
- The exported icon must have real transparent pixels around the head/mark. Do not accept an opaque PNG with black/dark background.
- No white outline if the platform icon should remain crisp.
- No text.

Banner:

- Generate exact `750x400` composition.
- Use a wide source composition from image generation; do not crop from square art.
- Keep title/copy and character face inside the central safe area, away from all edges.
- Include short theme copy by default, such as the pack name or a punchy one-line phrase.
- Integrate the copy into the generated design with clean, readable Chinese typography.
- Use the design brief to create a complete horizontal poster-like layout, not just text on a background.
- Use a lively designed background that contrasts with WeChat white UI.
- Create a horizontal key visual with clear foreground, midground, background, and readable focal point.
- Use graphic shapes, pattern motifs, scene fragments, props, and color blocks that match the pack personality.
- Show the pack character and story; make it feel like a small campaign visual, not a pasted sticker.
- Avoid transparent background.
- Fill the full image edge to edge. Do not create white borders, letterbox bars, framed margins, or a poster sitting on a white canvas.

Reward guide:

- Generate exact `750x560` composition.
- Use a horizontal `750x560` source composition from image generation; do not crop from square art.
- Keep the support copy, character face/body, props, and reward cue fully inside the central safe area.
- Include a short support-oriented line by default, such as `给小狗一点鼓励`, adapted to the pack theme.
- Integrate the copy into the generated design with warm, readable Chinese typography.
- Use the design brief to create a complete reward-selection visual, not just a support phrase.
- Create a polished reward-prompt key visual for the reward amount selection page.
- Show the character inviting, cheering, bowing, presenting a small thank-you prop, or otherwise encouraging support.
- Use warm composition, visual hierarchy, related props, and designed background elements to make the image feel generous and charming.
- Match the pack style.
- Avoid unrelated content and avoid hard selling.
- Fill the full image edge to edge. Do not create white borders, letterbox bars, framed margins, or a poster sitting on a white canvas.

Reward thanks:

- Generate exact `750x750` composition.
- Use a square source composition with generous safe margins, not a zoomed crop from a larger scene.
- Keep thank-you copy, character face/body, and share-worthy visual moment fully inside the safe area.
- Include a short thank-you line by default, such as `谢谢你的喜欢`, adapted to the pack theme.
- Integrate the copy into the generated design with sincere, readable Chinese typography.
- Use the design brief to create a complete thank-you/share visual, not just a thank-you phrase.
- Create a polished thank-you key visual for the post-reward page.
- Show the character sincerely thanking the user, celebrating, or sharing warmth.
- Use celebratory composition, thoughtful props, designed background elements, and a share-worthy visual moment.
- Match the pack style.
- Avoid unrelated content.
- Fill the full image edge to edge. Do not create white borders, letterbox bars, framed margins, or a poster sitting on a white canvas.

## Prompt Pattern

1. State asset type and dimensions or sheet grid.
2. Describe the recurring character identity.
3. Describe the emotion, scenario, and motion frames.
4. Restate consistency, containment, and phone-size readability.
5. Restate background and text policy constraints.
