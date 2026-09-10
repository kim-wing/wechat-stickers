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
- Default image-frame route: plan an ordered 12/16-frame equal-cell sheet, then verify actual motion and loop quality. See [sequential-frames.md](sequential-frames.md).
- Frame count and timing are animation-design choices, not platform specifications. Existing scripts use a conservative 12-frame minimum; a compact profile must be applied consistently and documented.
- Generated frames require clean edges and readable playback.
- Keep style unified and scenarios distinct.

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
