---
name: wechat-stickers
description: "Design and generate socially usable WeChat sticker packs from characters, themes, or reference images. Use for static stickers, image-generated sequential-frame GIFs, optional video-derived animation, album assets, metadata, and delivery QC."
---

# WeChat Stickers

## First principles

A sticker performs a social action. Start with who sends it, to whom, after what message, and what emotion or response it conveys. Animation should make that response clearer: anticipation, reaction, payoff, recovery. More frames, more movement, and a newer model are not evidence of a better sticker.

Separate three decisions:
1. **Intent:** sending situation, character behavior, exact copy, punchline.
2. **Motion:** what changes over time and what must remain invariant.
3. **Transport:** generated sheet → frames → GIF, or optional video → frames → GIF.

Default animated transport is image-generated sequential frames (`animated_source_mode: sprite_sheet`, retained for script compatibility). This is a primary production route, not a downgrade requiring permission. Use the available image-generation tool with the user's chosen model where selectable; do not invent a model parameter or claim GPT Image 2.5 was used when the tool does not report it. Capability improvements justify trying this route, not skipping visual validation.

Choose Seedance only for an explicit video request or when a pilot demonstrates that continuous complex motion needs it. Read [references/video-workflow.md](references/video-workflow.md) only for that route. Existing video projects retain their chosen mode. Record an intentional mode change; never substitute a static transform for generated motion.

## Plan and pilot

Read [references/net-sense-framework.md](references/net-sense-framework.md) for character/social concepts, [references/prompt-rules.md](references/prompt-rules.md) for art and layout. Use [references/emotion-presets.md](references/emotion-presets.md) only when scenarios are missing.

Infer static/animated, single/album, count, character, style, intended use and text from the request. State a reasonable album-count assumption if needed. Preserve the user's supplied choices without asking again. Single stickers do not need album assets.

Use a fresh named output directory. Run commands from this skill directory:

```bash
python3 scripts/run_wechat_sticker_pipeline.py init --output-dir /absolute/job --pack-name "表情名称" --count 8 --motion animated
```

Fill `sticker-plan.json`: creative direction, utility/persona/wildcard portfolio, each sticker's trigger utterance, hidden emotion, social move, visual hook, punchline and use case. For albums compare concepts for one utility and one persona/wildcard anchor, then run `creative-qc --plan /absolute/job/sticker-plan.json`. For a single sticker keep planning proportional; do not fabricate a whole portfolio.

Produce and review pilot animation before batching. Lock identity from a good reference and test a second distinctive social reaction before locking a whole album. Save prompt, tool-reported model (or unknown), reference paths, candidate id and original output path. `run-state.json` records deterministic progress; files and manifests, not chat memory, determine the selected source.

## Sequential-frame animation

Read [references/sequential-frames.md](references/sequential-frames.md) before generating animation. For a single test GIF, use the compact plan and targeted failure diagnosis there; do not load album/video references. It defines the frame contract, prompt, processing commands and review criteria.

Plan a single readable action with fixed camera, identity, palette, body proportions, background and caption. Generate all phases together in an equal-cell sheet where possible. A sheet is one sticker's timeline, never a pack of unrelated expressions. Specify chronological row-major ordering, safe cell margins and a loop-compatible final phase.

Start with 12 or 16 frames according to action and available per-cell resolution. These are practical presets for the existing conservative QC, not platform requirements or guarantees of smoothness. A short hold may need fewer frames; a walk may need more. Do not inflate counts with duplicate frames. Lower-count production needs a documented matching QC profile across inspection and final QC; the default pipeline currently requires at least 12 frames.

Generate artwork with image generation. Local code may split, key, uniformly scale, encode and audit it; it must not synthesize the character's performance from a still. Use the same transform across the sequence so normalization does not erase intended motion or create jitter. Do not blend inconsistent frames to hide morphing.

If a candidate fails, diagnose identity, phase ordering, grid geometry, typography, keying, or loop timing separately. Repair/regenerate from the locked reference and full motion contract. After two failed revisions of the same idea, change the motion design or report the specific blocker; avoid an unbounded retry loop. A new model name alone is not a reason to regenerate an entire album.

## Static stickers and album assets

Generate one complete artwork per static sticker, with a distinct pose and expression. Exact short Chinese text may be integrated when requested; use a consistent text policy. If local typography is necessary, record it as a separate deterministic layer and preserve the generated source. Do not replace every sticker with the same reference cutout plus captions.

```bash
python3 scripts/wechat_sticker_pack.py process-sticker --input /absolute/source.png --index 1 --output-dir /absolute/job --motion static --meaning "收到"
```

For albums, read [references/wechat-spec.md](references/wechat-spec.md) before asset creation and packaging. Generate cover, icon, banner and requested reward assets with the same identity. Design banner/reward typography, background and composition together, at the target aspect ratio. Use `make-asset` for deterministic conversion. Keep original sources and record their provenance in `manifest.json`.

Retain the pack's existing no-system-emoji and no-national-flags submission design conventions; do not confuse these conventions with universal content rules. Check current platform requirements when claiming submission readiness. Do not claim that technical QC guarantees platform acceptance.

## Review and delivery

Inspect the contact sheet for identity, edge clipping and pose order, then inspect the actual decoded GIF over several loops at 240px on light and dark backgrounds. A contact sheet cannot prove timing or loop closure. Reject unwanted morphing, caption wobble, palette flicker, transparent holes, key-color rims and abrupt seams. Check the punchline is readable at chat size and the motion adds useful expression.

Technical metrics flag suspicious motion; they do not understand intentional squash, anticipation or exaggeration. Investigate a flagged frame before simplifying. Never hide a failed default report by overwriting it with relaxed thresholds. Record any justified custom profile and retain both reports.

Use `make-metadata`, `make-preview-grid`, and pipeline `qc` for shared processing. QC must cover the current files, selected source, raw inspection, dimensions, byte limits, animation and required album assets. `package` reruns standard QC and stops on failure. Visually approve animation before packaging; mark unfinished work as draft and keep failed candidates separate.

Report the preview, actual source route/model if known, QC outcome and deliverable path. Do not describe script tests as evidence of generative quality, or a failed draft as a finished pack. Keep full prompts and reports on disk; use compact summaries in chat.
