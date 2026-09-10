# Prompt rules

Use generated artwork as the creative source. References establish identity and style; they are not a single cutout to repeat throughout the pack.

For each prompt specify the sending situation, hidden emotion, character-specific response, visible punchline, exact requested copy, composition, palette and silhouette. At 240px the expression must remain legible without zooming. Keep captions short and fixed over animation. Avoid unintended labels, frame numbers, grid lines, watermarks and unrelated decoration.

For animation use [sequential-frames.md](sequential-frames.md). Default to one temporally ordered sheet per sticker, with identity and layout locked. Use [video-workflow.md](video-workflow.md) only when video is selected. Do not inherit transport, grid dimensions or failed candidates from unrelated old projects.

For transparent stickers use true alpha if reliably provided; otherwise request a flat key color absent from the character (the existing sheet keyer expects #FF00FF). No shadows, gradients or glow on the key background. Keep safe margins around every pose. A character containing magenta needs a compatible transparency route rather than destructive magenta removal.

Use image-generated integrated text when it is correct and readable. If text fails, regenerate or keep a documented separate caption layer that stays identical on every frame. Do not draw replacement character art locally. Preserve the existing album convention excluding system emoji and national flags.

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
