# Sequential frames → GIF

## Motion contract

Write these fields per sticker before image generation:
- `action`: one social reaction, such as a reluctant nod after being assigned work.
- `locked_elements`: identity, body proportions, camera, baseline, props and exact caption.
- `moving_elements`: head/paw/eyelids or one coherent full-body action.
- `phases`: rest → anticipation → payoff → recovery, with explicit frame ranges.
- `rows`, `cols`, `frame_duration_ms`: equal-cell geometry and timing (default 4×4, 80ms).
- `loop`: final phase leads naturally into the first, without duplicating the endpoint.
- `sheet_source_path`, `candidate_id`: original generated output and stable candidate identity.

Choose frame count from the action's phases and desired duration. Check source width/cols and height/rows leave enough pixels for a clean 240px sticker. A larger grid at the same source resolution can reduce quality. The model may ignore exact geometry; inspect the result instead of trusting the prompt. Do not blindly divide a sheet with irregular gutters or missing cells.

The current deterministic path accepts equal-cell sheets, not arbitrary directories of independent images. If generation returns separate frames, request an equal-cell sheet or implement and test an explicit ordered-frame adapter first; do not relabel files as a sheet.

## Prompt template

> Create ONE animation timeline for [character], using the supplied reference for identity. A precise [rows] by [cols] equal-cell sheet, read left-to-right then top-to-bottom. Each cell shows the next moment of [action], not a different sticker concept. [Frame ranges and phases]. Lock [elements]. Only [moving elements] change. Fixed camera and consistent scale. Leave at least 10% safe padding within every cell for the entire motion. No visible grid lines, numbering, gutters or labels. Flat #FF00FF background with no shading; no magenta in the character. [Exact caption, or no text]. Last phase returns naturally toward the first; do not repeat the first frame at the end. Clear silhouette and expressive face at chat size.

Use the original character reference plus the approved pilot when the tool supports multiple references. When repairing, supply the sheet and identity reference, name the defective phase, and preserve the complete sequence contract. Do not chain edits solely from the previous defective frame: that can accumulate identity drift.

## Deterministic processing

After visual review of the raw sheet, put its original absolute tool-output path in the sticker's `sheet_source_path`, set a new `candidate_id` (for example `01-candidate-001`), and record `visual_review` with `raw_sheet_ok: true` and concrete notes. Do not mark this from technical metrics alone.

```bash
python3 scripts/run_wechat_sticker_pipeline.py validate --plan /absolute/job/sticker-plan.json
python3 scripts/run_wechat_sticker_pipeline.py process-sheets --plan /absolute/job/sticker-plan.json --indices 01
```

The command copies the original bytes, inspects the raw sequence, records candidate provenance, and calls the existing shared GIF processor. It does not invoke image generation or manufacture in-between frames. A processed GIF is still awaiting playback review; `gif_done` does not mean submission-ready. If an earlier GIF exists and a new candidate fails, consult state and do not present the old GIF as the new candidate.

For direct diagnosis:

```bash
python3 scripts/wechat_sticker_pack.py inspect-sheet --input /absolute/sheet.png --rows 4 --cols 4 --output /absolute/inspect.json --reject --summary
```

Default inspection and final QC retain the existing conservative minimum of 12 frames and motion thresholds. These are local heuristics, not proof that 8 frames cannot work. Do not lower only one stage or pad frames to satisfy them. A future compact-motion profile must consistently cover raw inspection, processing, final QC and recorded review.

## Acceptance

Review actual playback: gesture meaning, phase order, stable identity/props/text, deliberate timing, clean loop, and edges on both light/dark backgrounds. Count and dimensions are only technical checks. Decode the GIF, because palette/transparency encoding can introduce artifacts absent from source PNGs. Keep useful expressive deformation; reject unintended scale breathing and camera drift. Use a shared canvas transform, never independently crop and resize each pose.

For a failed pilot, change one cause at a time: clearer phase table for ordering; stronger identity reference for morphing; simpler composition or fewer larger cells for crowded geometry; regenerate text or use a fixed documented caption layer for wobble. Keep original candidates and inspection reports. Do not rescue an incoherent sheet by taking one cell and applying local bounce/rotation.

## Capability evidence

OpenAI's [Images 2.5 announcement](https://openai.com/index/introducing-chatgpt-images-2-5/) and [Flare model documentation](https://developers.openai.com/api/docs/models/gpt-image-2.5-flare) were checked on 2026-09-10. Model quality/editing improvements motivate a frame-first pilot, but do not establish guaranteed temporal coherence or native GIF output. Record the actual runtime model only when exposed. This skill's acceptance criteria remain independent of model branding.

## Efficient diagnosis (cat-fishing pilot)

The tested tool returned 1254×1254 despite a 2048×2048 request. Read actual dimensions once. The splitter already rounds proportional cell boundaries; exact divisibility is unnecessary. Verify equal visual cells, no gutters and safe margins, not a requested pixel count. Do not rescale the source merely to satisfy a divisibility check.

Use a compact prompt: character/style → ONE action → grid/order → phase ranges → locked elements → background/margins. Avoid repeated adjectives and contradictory instructions. A blink is brief with a longer open-eye hold; specify neighboring phases, not sixteen independently worded pictures. A frame sheet is not guaranteed to register perfectly, even when editing a prior sheet.

After `process-sheets`, read the compact result only. Full inspect/promote/encode logs live in `reports/`. On failure, open the named inspect log: it includes absolute center/difference values and `review_pairs` (three strongest transitions plus last→first). Inspect those pairs at final size before deciding to regenerate. High ratios during long still holds are clues, not automatic proof of a false positive. The cat pilot's seam still differed visibly; retain failed reports and do not relax thresholds simply to pass it.

Use one raw-sheet visual review and one decoded-GIF playback review. Reinspect individual frames only where the summary points. A decoded contact sheet verifies edges/identity but cannot verify playback; if playback was not observed, say so. Do not report imagined playback observations.

Reuse the original prompt file and change only the diagnosed constraint for a retry. Keep candidate ids and immutable original sources. Do not repeatedly dump skills, full JSON, all frames, or stack traces into context. Do not skip final QC, shrink output resolution, reduce frame count, or manufacture in-betweens merely to save tokens.
