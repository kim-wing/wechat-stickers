# Generate WeChat Stickers

A Codex skill for generating WeChat sticker packs from a character, theme, or reference image.

It supports:

- Static WeChat sticker albums: 8, 16, or 24 stickers.
- Animated WeChat sticker albums through Doubao Seedance video generation.
- WeChat album assets: cover, chat icon, banner, reward guide image, reward thanks image, thumbnails, metadata, preview grid, and QC reports.
- Guardrails for common failure modes: reference-image cutout misuse, silent fallback to sprite sheets, dirty green-screen keying, Emoji/flag policy issues, stale candidate selection, and non-current QC reports.

The skill is designed for Codex Desktop / Codex CLI style workflows. It gives the agent a production playbook plus deterministic scripts for packaging and checking assets.

## Repository Contents

```text
generate-wechat-stickers/
├── SKILL.md
├── agents/openai.yaml
├── references/
│   ├── emotion-presets.md
│   ├── prompt-rules.md
│   └── wechat-spec.md
├── scripts/
│   ├── run_wechat_sticker_pipeline.py
│   ├── seedance_video_task.py
│   ├── process_seedance_green_video.py
│   └── wechat_sticker_pack.py
├── docs/
│   └── seedance-ark-setup.md
└── examples/
    ├── README.md
    └── previews/
```

## Requirements

- Python 3.9+
- Pillow
- ffmpeg on `PATH`
- Codex image generation capability for creative source images
- Volcengine Ark API Key for Seedance animated video mode

Install Python dependency:

```bash
python3 -m pip install -r requirements.txt
```

Check ffmpeg:

```bash
ffmpeg -version
```

## Install As A Codex Skill

Clone this repository into your Codex skills directory:

```bash
mkdir -p "$HOME/.codex/skills"
git clone https://github.com/<your-org>/generate-wechat-stickers.git \
  "$HOME/.codex/skills/generate-wechat-stickers"
```

Restart Codex, then ask:

```text
Use $generate-wechat-stickers to create a 16-pack animated WeChat sticker album.
```

## Seedance API Setup

Animated sticker generation uses the Volcengine Ark video generation API with Doubao Seedance 1.5 Pro by default.

Set your key as an environment variable:

```bash
export ARK_API_KEY="your_api_key_here"
```

Do not paste real keys into prompts, scripts, manifests, reports, command history, or GitHub issues.

See [docs/seedance-ark-setup.md](docs/seedance-ark-setup.md) for official setup links, free quota notes, model opening steps, and a smoke test.

## Basic Usage

### Static Pack

Prompt Codex with:

```text
Use $generate-wechat-stickers to create a static 24-pack WeChat sticker album.
Character: a fluffy white puppy named Gemin.
Theme: workplace reactions.
Style: cute, clean, high-readability Chinese sticker text.
Include cover, icon, banner, reward guide, and reward thanks images.
```

Expected final main assets:

```text
main/01.png ... main/24.png
thumbs/01.png ... thumbs/24.png
cover.png
icon.png
banner.png
reward-guide.png
reward-thanks.png
manifest.json
metadata.csv
preview-grid.jpg
qc-report.json
```

### Animated Pack With Seedance

Prompt Codex with:

```text
Use $generate-wechat-stickers to create an animated 8-pack WeChat sticker album.
Character: a tiny robot mascot.
Theme: daily encouragement.
Mode: transparent GIF, Seedance first-last-frame video route.
Make one pilot first before generating the whole pack.
```

The pipeline should create:

```text
sticker-plan.json
run-state.json
pipeline-lock.json
start_frames/
end_frames/
video/
main/
thumbs/
reports/
preview-grid.jpg
qc-report.json
```

### Deterministic Pipeline Commands

The skill uses image generation for creative source art. The scripts handle deterministic production stages after source files exist.

Initialize a job:

```bash
python3 scripts/run_wechat_sticker_pipeline.py init \
  --output-dir ./out/gemin-fighting-16-animated \
  --pack-name "Gemin Fighting Diary" \
  --count 16 \
  --motion animated \
  --animated-source-mode green_screen_video \
  --theme "positive puppy encouragement" \
  --character "fluffy white puppy mascot"
```

Validate before paid video calls:

```bash
python3 scripts/run_wechat_sticker_pipeline.py validate \
  --plan ./out/gemin-fighting-16-animated/sticker-plan.json \
  --require-keyframes \
  --require-secrets
```

Submit Seedance videos:

```bash
python3 scripts/run_wechat_sticker_pipeline.py submit-videos \
  --plan ./out/gemin-fighting-16-animated/sticker-plan.json \
  --indices 01-04 \
  --concurrency 4
```

Convert green-screen MP4 files to transparent GIF:

```bash
python3 scripts/run_wechat_sticker_pipeline.py process-videos \
  --plan ./out/gemin-fighting-16-animated/sticker-plan.json \
  --indices 01-04 \
  --sample-count 36
```

Preview, QC, and package:

```bash
python3 scripts/run_wechat_sticker_pipeline.py make-preview \
  --plan ./out/gemin-fighting-16-animated/sticker-plan.json

python3 scripts/run_wechat_sticker_pipeline.py qc \
  --plan ./out/gemin-fighting-16-animated/sticker-plan.json

python3 scripts/run_wechat_sticker_pipeline.py package \
  --plan ./out/gemin-fighting-16-animated/sticker-plan.json
```

## Safety And Policy Guardrails

This skill deliberately rejects several tempting shortcuts:

- Do not make a pack by cutting out a user reference image and adding text.
- Do not silently downgrade Seedance animation into local still loops.
- Do not use Emoji-derived visual material in stickers, banner, or reward assets.
- Do not use national flags or flag-like fragments.
- Do not package failed preview assets as production-ready deliverables.
- Do not commit API keys, task URLs with secrets, raw private references, or large generated job folders.

## Examples

See [examples/README.md](examples/README.md) for recent static and animated case notes with preview images.

## Official Links

- Volcengine Ark product page: https://www.volcengine.com/product/ark
- Ark API Key guide: https://www.volcengine.com/docs/82379/1541594
- Ark video generation API reference: https://www.volcengine.com/docs/82379/1520757
- Ark free inference quota page: https://www.volcengine.com/docs/82379/1399514
- Seedance resource package rules: https://www.volcengine.com/docs/82379/2191775

## License

MIT. See [LICENSE](LICENSE).
