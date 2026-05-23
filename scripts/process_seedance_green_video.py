#!/usr/bin/env python3
import argparse
import shutil
import subprocess
from pathlib import Path

from PIL import Image


def key_green(img: Image.Image) -> Image.Image:
    rgba = img.convert("RGBA")
    out = []
    for r, g, b, _a in rgba.getdata():
        green_score = g - max(r, b)
        if g > 150 and green_score > 45:
            alpha = max(0, min(255, int(255 - green_score * 3.2)))
        elif g > 120 and green_score > 25:
            alpha = max(0, min(255, int(255 - green_score * 1.8)))
        else:
            alpha = 255
        if alpha < 24:
            out.append((255, 0, 254, 0))
            continue
        if green_score > 10:
            g = min(g, int((r + b) / 2) + 8)
        out.append((r, g, b, alpha))
    rgba.putdata(out)
    return rgba


def fixed_fit_240(img: Image.Image) -> Image.Image:
    return img.resize((240, 240), Image.Resampling.LANCZOS)


def save_transparent_gif(frames, path: Path, duration: int, colors: int, alpha_threshold: int) -> None:
    key = (255, 0, 254)
    width, height = frames[0].size
    stacked = Image.new("RGB", (width, height * len(frames)), key)
    masks = []
    for i, frame in enumerate(frames):
        rgba = frame.convert("RGBA")
        alpha = rgba.getchannel("A")
        rgb = Image.new("RGB", rgba.size, key)
        src = rgba.load()
        dst = rgb.load()
        for y in range(height):
            for x in range(width):
                r, g, b, a = src[x, y]
                if a >= alpha_threshold:
                    dst[x, y] = (r, g, b)
        stacked.paste(rgb, (0, i * height))
        masks.append(alpha)

    paletted = stacked.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
    palette = paletted.getpalette()
    palette_size = len(palette) // 3
    key_index = min(
        range(palette_size),
        key=lambda idx: (palette[idx * 3] - key[0]) ** 2
        + (palette[idx * 3 + 1] - key[1]) ** 2
        + (palette[idx * 3 + 2] - key[2]) ** 2,
    )

    parts = []
    for i, mask in enumerate(masks):
        part = paletted.crop((0, i * height, width, (i + 1) * height))
        alpha = mask.point(lambda a: 255 if a >= alpha_threshold else 0)
        part.paste(key_index, mask=alpha.point(lambda a: 0 if a else 255))
        part.info["transparency"] = key_index
        part.info["duration"] = duration
        part.info["disposal"] = 2
        parts.append(part)
    path.parent.mkdir(parents=True, exist_ok=True)
    parts[0].save(path, save_all=True, append_images=parts[1:], loop=0, duration=duration, disposal=2, transparency=key_index, optimize=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract, key, and encode a Seedance green-screen MP4 as a transparent GIF.")
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--frames-dir", required=True, type=Path)
    parser.add_argument("--keyed-dir", required=True, type=Path)
    parser.add_argument("--gif", required=True, type=Path)
    parser.add_argument("--thumb", required=True, type=Path)
    parser.add_argument("--sample-count", type=int, default=32)
    parser.add_argument("--source-duration", type=int, default=5)
    parser.add_argument("--duration", type=int, default=70)
    parser.add_argument("--colors", type=int, default=96)
    parser.add_argument("--alpha-threshold", type=int, default=112)
    args = parser.parse_args()

    for folder in (args.frames_dir, args.keyed_dir):
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True, exist_ok=True)
    args.thumb.parent.mkdir(parents=True, exist_ok=True)

    pattern = args.frames_dir / "frame_%04d.png"
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(args.video),
            "-vf",
            "fps=%s/%s,scale=360:360:force_original_aspect_ratio=decrease,pad=360:360:(ow-iw)/2:(oh-ih)/2:color=0x00ff00"
            % (args.sample_count, args.source_duration),
            "-frames:v",
            str(args.sample_count),
            str(pattern),
        ],
        check=True,
    )

    processed = []
    for idx, frame_path in enumerate(sorted(args.frames_dir.glob("frame_*.png")), 1):
        keyed = fixed_fit_240(key_green(Image.open(frame_path)))
        out = args.keyed_dir / ("selected_%03d.png" % idx)
        keyed.save(out)
        processed.append(keyed)
    if not processed:
        raise SystemExit("No frames extracted")
    save_transparent_gif(processed, args.gif, args.duration, args.colors, args.alpha_threshold)
    processed[0].resize((120, 120), Image.Resampling.LANCZOS).save(args.thumb)


if __name__ == "__main__":
    main()
