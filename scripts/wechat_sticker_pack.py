#!/usr/bin/env python3
"""Postprocess generated art into WeChat sticker pack assets."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import shutil
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageChops, ImageSequence, ImageStat


MAGENTA = (255, 0, 255)
TRANSPARENT = (0, 0, 0, 0)
VISIBLE_ALPHA_THRESHOLD = 8
GIF_ALPHA_THRESHOLD = VISIBLE_ALPHA_THRESHOLD
GENERATED_IMAGE_THREAD_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
EMOJI_RE = re.compile(r"[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F]")
RESTRICTED_VISUAL_POLICY_TERMS = (
    "emoji",
    "emoji-style",
    "emoji style",
    "reaction emoji",
    "smiley face",
    "yellow smiley",
    "表情符号",
    "系统表情",
    "平台表情",
    "微信emoji",
    "微信表情符号",
    "黄脸表情",
    "黄色笑脸",
    "圆脸表情",
    "黄豆表情",
    "流汗黄豆",
    "笑哭表情",
    "哭笑表情",
    "捂脸表情",
    "emoji风格",
    "emoji二创",
    "二次创作emoji",
    "二创emoji",
    "national flag",
    "country flag",
    "state flag",
    "flag icon",
    "flag motif",
    "flag material",
    "flags",
    "国旗",
    "国家旗帜",
    "旗帜素材",
    "旗子素材",
    "小旗子",
    "小旗",
    "五星红旗",
    "中国国旗",
    "美国国旗",
    "日本国旗",
    "英国国旗",
    "米字旗",
    "星条旗",
    "太阳旗",
    "欧盟旗",
)
VIDEO_SOURCE_MODES = {"green_screen_video", "background_video"}
FORBIDDEN_ANIMATED_SOURCE_MODES = {
    "image_gen_loop",
    "local_loop",
    "still_loop",
    "single_still_loop",
    "image_transform_loop",
    "local_transform_loop",
    "micro_animation_from_still",
}
ALLOWED_CREATIVE_SOURCES = {"image_gen", "seedance_video"}
NEGATED_VISUAL_POLICY_MARKERS = (
    "no ",
    "no_",
    "no-",
    "without ",
    "avoid ",
    "avoid_",
    "not using ",
    "禁止",
    "不要",
    "无",
    "不得",
    "不能",
    "不可",
    "不使用",
    "避免",
)

ASSET_SPECS = {
    "cover": {"filename": "cover.png", "size": (240, 240), "limit": 80 * 1024, "transparent": True},
    "icon": {"filename": "icon.png", "size": (50, 50), "limit": 30 * 1024, "transparent": True},
    "banner": {"filename": "banner.png", "size": (750, 400), "limit": 80 * 1024, "transparent": False},
    "reward-guide": {"filename": "reward-guide.png", "size": (750, 560), "limit": 500 * 1024, "transparent": False},
    "reward-thanks": {"filename": "reward-thanks.png", "size": (750, 750), "limit": 500 * 1024, "transparent": False},
}


def magenta_distance(pixel: tuple[int, int, int]) -> float:
    r, g, b = pixel
    return math.sqrt((r - 255) ** 2 + g**2 + (b - 255) ** 2)


def clamp_byte(value: float) -> int:
    return max(0, min(255, round(value)))


def smoothstep(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


def remove_magenta(img: Image.Image, threshold: int = 80, softness: int = 96) -> Image.Image:
    rgba = img.convert("RGBA")
    pixels = rgba.load()
    width, height = rgba.size
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if not a:
                continue
            distance = magenta_distance((r, g, b))
            if distance <= threshold:
                pixels[x, y] = TRANSPARENT
                continue
            if softness > 0 and distance < threshold + softness:
                matte = smoothstep((distance - threshold) / softness)
                new_alpha = clamp_byte(a * matte)
                if new_alpha <= 2:
                    pixels[x, y] = TRANSPARENT
                    continue
                alpha_fraction = max(new_alpha / 255, 0.05)
                # Estimate the original foreground color from magenta-background antialiasing.
                fg_r = (r - (1 - alpha_fraction) * MAGENTA[0]) / alpha_fraction
                fg_g = (g - (1 - alpha_fraction) * MAGENTA[1]) / alpha_fraction
                fg_b = (b - (1 - alpha_fraction) * MAGENTA[2]) / alpha_fraction
                pixels[x, y] = (clamp_byte(fg_r), clamp_byte(fg_g), clamp_byte(fg_b), new_alpha)
    return clean_magenta_fringe(rgba)


def is_magenta_fringe(r: int, g: int, b: int) -> bool:
    return r >= 150 and b >= 120 and g <= 135 and r - g >= 55 and b - g >= 45


def is_green_screen_spill(r: int, g: int, b: int) -> bool:
    return g > 80 and g > r + 35 and g > b + 35


def has_transparent_neighbor(pixels, width: int, height: int, x: int, y: int) -> bool:
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height and pixels[nx, ny][3] == 0:
                return True
    return False


def clean_magenta_fringe(img: Image.Image, passes: int = 3) -> Image.Image:
    rgba = img.convert("RGBA")
    for _ in range(passes):
        pixels = rgba.load()
        width, height = rgba.size
        to_clear: list[tuple[int, int]] = []
        for y in range(height):
            for x in range(width):
                r, g, b, a = pixels[x, y]
                if a == 0 or not is_magenta_fringe(r, g, b):
                    continue
                if has_transparent_neighbor(pixels, width, height, x, y):
                    to_clear.append((x, y))
        for x, y in to_clear:
            pixels[x, y] = TRANSPARENT
    return rgba


def alpha_bbox(img: Image.Image) -> tuple[int, int, int, int] | None:
    alpha = img.convert("RGBA").getchannel("A")
    visible = alpha.point(lambda value: 255 if value >= VISIBLE_ALPHA_THRESHOLD else 0)
    return visible.getbbox()


def alpha_components(img: Image.Image, min_alpha: int = VISIBLE_ALPHA_THRESHOLD) -> list[tuple[int, tuple[int, int, int, int]]]:
    rgba = img.convert("RGBA")
    alpha = rgba.getchannel("A")
    width, height = rgba.size
    visited = bytearray(width * height)
    components: list[tuple[int, tuple[int, int, int, int]]] = []

    for start_y in range(height):
        for start_x in range(width):
            start_index = start_y * width + start_x
            if visited[start_index] or alpha.getpixel((start_x, start_y)) < min_alpha:
                continue

            stack = [(start_x, start_y)]
            visited[start_index] = 1
            area = 0
            x0 = x1 = start_x
            y0 = y1 = start_y
            while stack:
                x, y = stack.pop()
                area += 1
                x0 = min(x0, x)
                y0 = min(y0, y)
                x1 = max(x1, x + 1)
                y1 = max(y1, y + 1)
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if nx < 0 or ny < 0 or nx >= width or ny >= height:
                        continue
                    index = ny * width + nx
                    if visited[index] or alpha.getpixel((nx, ny)) < min_alpha:
                        continue
                    visited[index] = 1
                    stack.append((nx, ny))
            components.append((area, (x0, y0, x1, y1)))
    return components


def is_thin_edge_bleed_component(
    component: tuple[int, tuple[int, int, int, int]],
    image_size: tuple[int, int],
    edge_px: int = 2,
    max_area_ratio: float = 0.025,
    max_thickness_ratio: float = 0.055,
) -> bool:
    area, box = component
    x0, y0, x1, y1 = box
    width, height = image_size
    touches_edge = x0 <= edge_px or y0 <= edge_px or x1 >= width - edge_px or y1 >= height - edge_px
    if not touches_edge:
        return False

    component_width = x1 - x0
    component_height = y1 - y0
    max_area = max(16, int(width * height * max_area_ratio))
    max_thickness = max(4, int(max(width, height) * max_thickness_ratio))
    is_thin = component_width <= max_thickness or component_height <= max_thickness
    return area <= max_area and is_thin


def edge_bleed_components(img: Image.Image) -> list[tuple[int, tuple[int, int, int, int]]]:
    rgba = img.convert("RGBA")
    return [
        component
        for component in alpha_components(rgba)
        if is_thin_edge_bleed_component(component, rgba.size)
    ]


def is_thin_top_sliver_component(
    component: tuple[int, tuple[int, int, int, int]],
    image_size: tuple[int, int],
    top_band_ratio: float = 0.24,
    max_area_ratio: float = 0.025,
    max_thickness_ratio: float = 0.055,
) -> bool:
    area, box = component
    x0, y0, x1, y1 = box
    width, height = image_size
    component_width = x1 - x0
    component_height = y1 - y0
    max_area = max(16, int(width * height * max_area_ratio))
    max_thickness = max(4, int(max(width, height) * max_thickness_ratio))
    min_width = max(48, int(width * 0.18), component_height * 4)
    return (
        y0 <= int(height * top_band_ratio)
        and area <= max_area
        and component_height <= max_thickness
        and component_width >= min_width
    )


def thin_top_sliver_components(img: Image.Image) -> list[tuple[int, tuple[int, int, int, int]]]:
    rgba = img.convert("RGBA")
    return [
        component
        for component in alpha_components(rgba)
        if is_thin_top_sliver_component(component, rgba.size)
    ]


def remove_edge_bleed_components(frames: list[Image.Image]) -> list[Image.Image]:
    cleaned_frames: list[Image.Image] = []
    for frame in frames:
        rgba = frame.convert("RGBA")
        components = edge_bleed_components(rgba)
        if not components:
            cleaned_frames.append(rgba)
            continue
        pixels = rgba.load()
        for _, box in components:
            x0, y0, x1, y1 = box
            for y in range(y0, y1):
                for x in range(x0, x1):
                    if pixels[x, y][3] >= VISIBLE_ALPHA_THRESHOLD:
                        pixels[x, y] = TRANSPARENT
        cleaned_frames.append(rgba)
    return cleaned_frames


def fit_on_canvas(
    img: Image.Image,
    size: tuple[int, int],
    fit_scale: float,
    align: str,
    transparent: bool,
    background: tuple[int, int, int, int] = (255, 255, 255, 255),
) -> Image.Image:
    rgba = img.convert("RGBA")
    bbox = alpha_bbox(rgba)
    if bbox:
        rgba = rgba.crop(bbox)

    canvas_bg = TRANSPARENT if transparent else background
    canvas = Image.new("RGBA", size, canvas_bg)
    if rgba.width <= 0 or rgba.height <= 0:
        return canvas

    max_w = max(1, int(size[0] * fit_scale))
    max_h = max(1, int(size[1] * fit_scale))
    scale = min(max_w / rgba.width, max_h / rgba.height)
    new_size = (max(1, round(rgba.width * scale)), max(1, round(rgba.height * scale)))
    resized = rgba.resize(new_size, Image.Resampling.LANCZOS)

    x = (size[0] - new_size[0]) // 2
    if align in {"bottom", "feet"}:
        y = size[1] - new_size[1] - max(0, int(size[1] * (1 - fit_scale) * 0.45))
    else:
        y = (size[1] - new_size[1]) // 2
    canvas.alpha_composite(resized, (x, y))
    return canvas


def fill_canvas(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    rgba = img.convert("RGBA")
    if rgba.width <= 0 or rgba.height <= 0:
        return Image.new("RGBA", size, (255, 255, 255, 255))
    scale = max(size[0] / rgba.width, size[1] / rgba.height)
    new_size = (max(1, round(rgba.width * scale)), max(1, round(rgba.height * scale)))
    resized = rgba.resize(new_size, Image.Resampling.LANCZOS)
    left = max(0, (resized.width - size[0]) // 2)
    top = max(0, (resized.height - size[1]) // 2)
    return resized.crop((left, top, left + size[0], top + size[1]))


def union_bbox(frames: list[Image.Image]) -> tuple[int, int, int, int] | None:
    boxes = [alpha_bbox(frame) for frame in frames]
    boxes = [box for box in boxes if box]
    if not boxes:
        return None
    return (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )


def fit_frames_on_canvas(
    frames: list[Image.Image],
    size: tuple[int, int],
    fit_scale: float,
    align: str,
    preserve_motion: bool,
) -> list[Image.Image]:
    if not frames:
        return []
    if not preserve_motion or len(frames) == 1:
        return [fit_on_canvas(frame, size, fit_scale, align, transparent=True) for frame in frames]

    bbox = union_bbox(frames)
    if not bbox:
        return [Image.new("RGBA", size, TRANSPARENT) for _ in frames]

    cropped = [frame.convert("RGBA").crop(bbox) for frame in frames]
    crop_w = max(1, bbox[2] - bbox[0])
    crop_h = max(1, bbox[3] - bbox[1])
    max_w = max(1, int(size[0] * fit_scale))
    max_h = max(1, int(size[1] * fit_scale))
    scale = min(max_w / crop_w, max_h / crop_h)
    new_size = (max(1, round(crop_w * scale)), max(1, round(crop_h * scale)))
    paste_x = (size[0] - new_size[0]) // 2
    if align in {"bottom", "feet"}:
        paste_y = size[1] - new_size[1] - max(0, int(size[1] * (1 - fit_scale) * 0.45))
    else:
        paste_y = (size[1] - new_size[1]) // 2

    out: list[Image.Image] = []
    for frame in cropped:
        resized = frame.resize(new_size, Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", size, TRANSPARENT)
        canvas.alpha_composite(resized, (paste_x, paste_y))
        out.append(canvas)
    return out


def split_grid(img: Image.Image, rows: int, cols: int) -> list[Image.Image]:
    rgba = img.convert("RGBA")
    frames: list[Image.Image] = []
    for row in range(rows):
        for col in range(cols):
            box = (
                round(col * rgba.width / cols),
                round(row * rgba.height / rows),
                round((col + 1) * rgba.width / cols),
                round((row + 1) * rgba.height / rows),
            )
            frames.append(rgba.crop(box))
    return frames


def median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def alpha_composite_shifted(canvas_size: tuple[int, int], frame: Image.Image, offset: tuple[int, int]) -> Image.Image:
    dx, dy = offset
    src = frame.convert("RGBA")
    canvas = Image.new("RGBA", canvas_size, TRANSPARENT)
    src_x = max(0, -dx)
    src_y = max(0, -dy)
    dst_x = max(0, dx)
    dst_y = max(0, dy)
    width = min(src.width - src_x, canvas.width - dst_x)
    height = min(src.height - src_y, canvas.height - dst_y)
    if width <= 0 or height <= 0:
        return canvas
    crop = src.crop((src_x, src_y, src_x + width, src_y + height))
    canvas.alpha_composite(crop, (dst_x, dst_y))
    return canvas


def frame_anchor(frame: Image.Image, anchor: str) -> tuple[float, float] | None:
    box = alpha_bbox(frame)
    if not box:
        return None
    x0, y0, x1, y1 = box
    if anchor in {"bottom", "feet"}:
        return ((x0 + x1) / 2, float(y1))
    return ((x0 + x1) / 2, (y0 + y1) / 2)


def circular_smooth_points(points: list[tuple[float, float]], window: int) -> list[tuple[float, float]]:
    if not points:
        return []
    window = max(1, window)
    if window % 2 == 0:
        window += 1
    radius = window // 2
    smoothed: list[tuple[float, float]] = []
    for index in range(len(points)):
        xs: list[float] = []
        ys: list[float] = []
        for offset in range(-radius, radius + 1):
            point = points[(index + offset) % len(points)]
            xs.append(point[0])
            ys.append(point[1])
        smoothed.append((sum(xs) / len(xs), sum(ys) / len(ys)))
    return smoothed


def stabilize_frame_positions(
    frames: list[Image.Image],
    strength: float,
    anchor: str,
    mode: str,
    window: int,
) -> list[Image.Image]:
    if not frames:
        return []
    anchors = [frame_anchor(frame, anchor) for frame in frames]
    valid = [point for point in anchors if point]
    if not valid:
        return frames
    if mode == "median":
        target_points = [(median([point[0] for point in valid]), median([point[1] for point in valid]))] * len(frames)
    else:
        fallback = (median([point[0] for point in valid]), median([point[1] for point in valid]))
        target_points = circular_smooth_points([point or fallback for point in anchors], window)
    stabilized: list[Image.Image] = []
    for frame, current, target in zip(frames, anchors, target_points):
        if not current:
            stabilized.append(frame)
            continue
        offset = (round((target[0] - current[0]) * strength), round((target[1] - current[1]) * strength))
        stabilized.append(alpha_composite_shifted(frame.size, frame, offset))
    return stabilized


def iter_input_frames(path: Path, rows: int, cols: int, threshold: int, key_softness: int) -> list[Image.Image]:
    img = Image.open(path)
    if getattr(img, "is_animated", False):
        return [remove_magenta(frame.convert("RGBA"), threshold, key_softness) for frame in ImageSequence.Iterator(img)]
    cleaned = remove_magenta(img.convert("RGBA"), threshold, key_softness)
    if rows * cols > 1:
        return [remove_magenta(frame, threshold, key_softness) for frame in split_grid(cleaned, rows, cols)]
    return [cleaned]


def save_gif(frames: list[Image.Image], path: Path, duration: int, colors: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not frames:
        raise ValueError("No frames to save.")
    key = (255, 0, 254)
    width, height = frames[0].size
    stacked = Image.new("RGB", (width, height * len(frames)), key)
    for index, frame in enumerate(frames):
        rgba = frame.convert("RGBA")
        rgb = Image.new("RGB", rgba.size, key)
        rgb.paste(
            rgba.convert("RGB"),
            mask=rgba.getchannel("A").point(lambda value: 255 if value >= GIF_ALPHA_THRESHOLD else 0),
        )
        stacked.paste(rgb, (0, index * height))

    paletted = stacked.convert(
        "P",
        palette=Image.Palette.ADAPTIVE,
        colors=max(2, min(256, colors)),
        dither=Image.Dither.NONE,
    )
    palette = list(paletted.getpalette() or [])
    while len(palette) < 256 * 3:
        palette.append(0)
    key_index = min(
        range(256),
        key=lambda idx: (palette[idx * 3] - key[0]) ** 2
        + (palette[idx * 3 + 1] - key[1]) ** 2
        + (palette[idx * 3 + 2] - key[2]) ** 2,
    )
    if key_index != 0:
        trans = bytes.maketrans(bytes([0, key_index]), bytes([key_index, 0]))
        paletted = Image.frombytes("P", paletted.size, paletted.tobytes().translate(trans))
        for channel in range(3):
            palette[channel], palette[key_index * 3 + channel] = palette[key_index * 3 + channel], palette[channel]
        paletted.putpalette(palette)

    palette_colors = [
        (idx, palette[idx * 3], palette[idx * 3 + 1], palette[idx * 3 + 2])
        for idx in range(1, max(2, min(256, colors)))
    ]
    out_frames = []
    for index, source in enumerate(frames):
        out_frame = paletted.crop((0, index * height, width, (index + 1) * height))
        # Never let an opaque foreground pixel use the transparent palette index.
        rgba = source.convert("RGBA")
        out_pixels = out_frame.load()
        src_pixels = rgba.load()
        alpha = rgba.getchannel("A")
        for y in range(height):
            for x in range(width):
                r, g, b, a = src_pixels[x, y]
                if a >= GIF_ALPHA_THRESHOLD and out_pixels[x, y] == 0:
                    nearest = min(
                        palette_colors,
                        key=lambda item: (item[1] - r) ** 2 + (item[2] - g) ** 2 + (item[3] - b) ** 2,
                    )[0]
                    out_pixels[x, y] = nearest
        to_clear: list[tuple[int, int]] = []
        for y in range(height):
            for x in range(width):
                palette_index = out_pixels[x, y]
                if palette_index == 0:
                    continue
                r = palette[palette_index * 3]
                g = palette[palette_index * 3 + 1]
                b = palette[palette_index * 3 + 2]
                if not is_magenta_fringe(r, g, b):
                    continue
                near_transparent = False
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < width and 0 <= ny < height and alpha.getpixel((nx, ny)) < GIF_ALPHA_THRESHOLD:
                            near_transparent = True
                            break
                    if near_transparent:
                        break
                if near_transparent:
                    to_clear.append((x, y))
        for x, y in to_clear:
            out_pixels[x, y] = 0
        out_frames.append(out_frame)
    out_frames[0].save(
        path,
        save_all=True,
        append_images=out_frames[1:],
        loop=0,
        duration=duration,
        disposal=2,
        transparency=0,
        background=0,
    )


def save_png(img: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG", optimize=True)


def save_jpeg(img: Image.Image, path: Path, quality: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rgba = img.convert("RGBA")
    background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    background.alpha_composite(rgba)
    background.convert("RGB").save(path, "JPEG", quality=quality, optimize=True, progressive=True, subsampling=0)


def nontransparent_asset_format(kind: str, requested: str) -> str:
    if requested != "auto":
        return requested
    return "jpg" if kind == "banner" else "png"


def asset_output_path(output_dir: Path, kind: str, fmt: str) -> Path:
    filename = Path(str(ASSET_SPECS[kind]["filename"]))
    if fmt in {"jpg", "jpeg"}:
        return output_dir / filename.with_suffix(".jpg")
    return output_dir / filename.with_suffix(".png")


def existing_asset_path(output_dir: Path, kind: str) -> Path:
    filename = Path(str(ASSET_SPECS[kind]["filename"]))
    if kind == "banner":
        candidates = [
            output_dir / filename.with_suffix(".jpg"),
            output_dir / filename.with_suffix(".jpeg"),
            output_dir / filename,
            output_dir / filename.with_suffix(".png"),
            output_dir / filename.with_suffix(".gif"),
        ]
    else:
        candidates = [
            output_dir / filename,
            output_dir / filename.with_suffix(".jpg"),
            output_dir / filename.with_suffix(".jpeg"),
            output_dir / filename.with_suffix(".png"),
            output_dir / filename.with_suffix(".gif"),
        ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def is_preview_output_dir(path: Path) -> bool:
    preview_terms = {"preview", "diagnostic", "diagnostics", "mockup", "scratch"}
    normalized_parts = {part.lower() for part in path.expanduser().parts}
    name_tokens = set(path.name.lower().replace("_", "-").split("-"))
    return bool(preview_terms & (normalized_parts | name_tokens))


def numbered(index: int) -> str:
    if index < 1 or index > 99:
        raise ValueError("--index must be between 1 and 99.")
    return f"{index:02d}"


def update_metadata(out_dir: Path, row: dict[str, str]) -> None:
    path = out_dir / "metadata.csv"
    existing: list[dict[str, str]] = []
    if path.exists():
        with path.open("r", encoding="utf-8", newline="") as fh:
            existing = list(csv.DictReader(fh))
    existing = [item for item in existing if item.get("index") != row["index"]]
    existing.append(row)
    existing.sort(key=lambda item: item.get("index", ""))
    with path.open("w", encoding="utf-8", newline="") as fh:
        fieldnames = ["index", "meaning", "motion", "main", "thumb"]
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(existing)


def cmd_process_sticker(args: argparse.Namespace) -> None:
    out_dir = args.output_dir
    idx = numbered(args.index)
    if args.motion == "animated" and args.rows * args.cols > 1 and not args.reject_raw_sheet:
        if not is_preview_output_dir(out_dir):
            raise SystemExit(
                "--no-reject-raw-sheet is diagnostic-only. Use an output directory whose path includes "
                "'preview', 'diagnostic', 'mockup', or 'scratch' so failed raw sheets cannot be mistaken "
                "for production output."
            )
    frames = iter_input_frames(args.input, args.rows, args.cols, args.threshold, args.key_softness)
    if args.motion == "animated" and args.rows * args.cols > 1 and args.reject_raw_sheet:
        metrics = frame_metrics(frames)
        temporal = temporal_metrics(frames, metrics)
        cell_width = frames[0].width if frames else 1
        failures: list[str] = []
        max_edge_pixels = max((int(item["edge_pixels"]) for item in metrics), default=0)
        max_edge_bleed = max((int(item["edge_bleed_components"]) for item in metrics), default=0)
        max_top_slivers = max((int(item["thin_top_sliver_components"]) for item in metrics), default=0)
        if max_edge_pixels > args.max_raw_edge_pixels:
            failures.append(f"edge pixels {max_edge_pixels} > {args.max_raw_edge_pixels}")
        if max_edge_bleed > args.max_raw_edge_bleed_components:
            failures.append(f"thin edge bleed components {max_edge_bleed} > {args.max_raw_edge_bleed_components}")
        if max_top_slivers > args.max_raw_thin_top_sliver_components:
            failures.append(f"thin top sliver components {max_top_slivers} > {args.max_raw_thin_top_sliver_components}")
        if float(temporal["center_step_max"]) > args.max_raw_center_step * max(cell_width, 1):
            failures.append(
                f"center step {float(temporal['center_step_max']):.3f} > "
                f"{args.max_raw_center_step * max(cell_width, 1):.3f}"
            )
        if float(temporal["center_step_outlier_ratio"]) > args.max_raw_center_step_outlier_ratio:
            failures.append(
                f"center step outlier ratio {float(temporal['center_step_outlier_ratio']):.3f} > "
                f"{args.max_raw_center_step_outlier_ratio}"
            )
        if float(temporal["scale_step_ratio_max"]) > args.max_raw_scale_step_ratio:
            failures.append(f"scale step ratio {float(temporal['scale_step_ratio_max']):.3f} > {args.max_raw_scale_step_ratio}")
        if float(temporal["diff_outlier_ratio"]) > args.max_raw_diff_outlier_ratio:
            failures.append(f"visual diff outlier ratio {float(temporal['diff_outlier_ratio']):.3f} > {args.max_raw_diff_outlier_ratio}")
        if float(temporal["loop_diff_ratio"]) > args.max_raw_loop_diff_ratio:
            failures.append(f"loop diff ratio {float(temporal['loop_diff_ratio']):.3f} > {args.max_raw_loop_diff_ratio}")
        if failures:
            raise SystemExit(
                "Raw animated sheet failed preflight; regenerate before packaging. "
                + "; ".join(failures)
                + ". Run inspect-sheet for frame-level details, or use --no-reject-raw-sheet only for diagnostics."
            )
    if args.motion == "animated" and args.clean_edge_bleed:
        frames = remove_edge_bleed_components(frames)
    if args.motion == "static":
        frames = frames[:1]
    processed = fit_frames_on_canvas(
        frames,
        (240, 240),
        args.fit_scale,
        args.align,
        preserve_motion=args.preserve_motion and args.motion == "animated",
    )
    if args.motion == "animated" and args.stabilize_position:
        processed = stabilize_frame_positions(
            processed,
            args.stabilize_strength,
            args.stabilize_anchor,
            args.stabilize_mode,
            args.stabilize_window,
        )

    frame_dir = out_dir / "frames" / idx
    for frame_index, frame in enumerate(processed, start=1):
        save_png(frame, frame_dir / f"{frame_index:02d}.png")

    if args.motion == "static":
        main_path = out_dir / "main" / f"{idx}.png"
        save_png(processed[0], main_path)
    else:
        main_path = out_dir / "main" / f"{idx}.gif"
        save_gif(processed, main_path, args.duration, args.colors)

    thumb_frame = processed[min(max(args.thumb_frame - 1, 0), len(processed) - 1)]
    thumb = fit_on_canvas(thumb_frame, (120, 120), args.fit_scale, "center", transparent=True)
    thumb_path = out_dir / "thumbs" / f"{idx}.png"
    save_png(thumb, thumb_path)

    update_metadata(
        out_dir,
        {
            "index": idx,
            "meaning": args.meaning or "",
            "motion": args.motion,
            "main": str(main_path.relative_to(out_dir)),
            "thumb": str(thumb_path.relative_to(out_dir)),
        },
    )
    print(str(main_path.resolve()))


def cmd_make_asset(args: argparse.Namespace) -> None:
    spec = ASSET_SPECS[args.kind]
    img = Image.open(args.input).convert("RGBA")
    if args.remove_magenta or spec["transparent"]:
        img = remove_magenta(img, args.threshold, args.key_softness)
    transparent = bool(spec["transparent"])
    background = tuple(args.background)
    if transparent or args.asset_fit == "contain":
        fitted = fit_on_canvas(
            img,
            tuple(spec["size"]),
            args.fit_scale,
            args.align,
            transparent=transparent,
            background=background,
        )
    else:
        fitted = fill_canvas(img, tuple(spec["size"]))
    fmt = "png" if transparent else nontransparent_asset_format(args.kind, args.asset_format)
    out_path = asset_output_path(args.output_dir, args.kind, fmt)
    if fmt in {"jpg", "jpeg"}:
        save_jpeg(fitted, out_path, args.jpeg_quality)
    else:
        save_png(fitted, out_path)
    print(str(out_path.resolve()))


def manifest_stickers(path: Path) -> list[dict[str, object]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    stickers = data.get("stickers", [])
    if not isinstance(stickers, list):
        raise SystemExit("manifest stickers must be a list.")
    return [item for item in stickers if isinstance(item, dict)]


def cmd_make_metadata(args: argparse.Namespace) -> None:
    out_dir = args.output_dir
    manifest_path = args.manifest or out_dir / "manifest.json"
    stickers = manifest_stickers(manifest_path)
    rows: list[dict[str, str]] = []
    for sticker in sorted(stickers, key=lambda item: int(item.get("index", 0))):
        index = numbered(int(sticker.get("index", 0)))
        motion = str(sticker.get("motion") or args.motion)
        main_ext = "gif" if motion == "animated" else "png"
        rows.append(
            {
                "index": index,
                "meaning": str(sticker.get("meaning") or sticker.get("text") or ""),
                "motion": motion,
                "main": f"main/{index}.{main_ext}",
                "thumb": f"thumbs/{index}.png",
            }
        )
    path = args.output or out_dir / "metadata.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        fieldnames = ["index", "meaning", "motion", "main", "thumb"]
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(str(path.resolve()))


def cmd_make_preview_grid(args: argparse.Namespace) -> None:
    out_dir = args.output_dir
    manifest_path = args.manifest or out_dir / "manifest.json"
    stickers = manifest_stickers(manifest_path)
    count = args.count or len(stickers)
    if count < 1:
        raise SystemExit("No stickers found for preview grid.")
    cols = args.cols
    rows = math.ceil(count / cols)
    sheet = Image.new("RGB", (cols * args.cell_size, rows * args.cell_size), tuple(args.background))
    for offset in range(count):
        idx = numbered(offset + 1)
        thumb_path = out_dir / "thumbs" / f"{idx}.png"
        if not thumb_path.exists():
            raise SystemExit(f"Missing thumbnail: {thumb_path}")
        thumb = Image.open(thumb_path).convert("RGBA").resize((args.thumb_size, args.thumb_size), Image.Resampling.LANCZOS)
        x = (offset % cols) * args.cell_size + (args.cell_size - args.thumb_size) // 2
        y = (offset // cols) * args.cell_size + (args.cell_size - args.thumb_size) // 2
        card = Image.new("RGB", (args.thumb_size, args.thumb_size), (255, 255, 255))
        sheet.paste(card, (x, y))
        sheet.paste(thumb, (x, y), thumb)
    path = args.output or out_dir / "preview-grid.jpg"
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path, quality=args.jpeg_quality, optimize=True)
    print(str(path.resolve()))


def frame_metrics(frames: list[Image.Image]) -> list[dict[str, object]]:
    metrics: list[dict[str, object]] = []
    for index, frame in enumerate(frames, start=1):
        rgba = frame.convert("RGBA")
        bbox = rgba.getbbox()
        edge_pixels = 0
        fringe_pixels = 0
        if bbox:
            alpha = rgba.getchannel("A")
            pixels = rgba.load()
            width, height = rgba.size
            for x in range(width):
                for y in (0, 1, 2, height - 3, height - 2, height - 1):
                    if 0 <= y < height and alpha.getpixel((x, y)) >= VISIBLE_ALPHA_THRESHOLD:
                        edge_pixels += 1
            for y in range(height):
                for x in (0, 1, 2, width - 3, width - 2, width - 1):
                    if 0 <= x < width and alpha.getpixel((x, y)) >= VISIBLE_ALPHA_THRESHOLD:
                        edge_pixels += 1
            for y in range(height):
                for x in range(width):
                    r, g, b, a = pixels[x, y]
                    if (
                        a >= VISIBLE_ALPHA_THRESHOLD
                        and is_magenta_fringe(r, g, b)
                        and has_transparent_neighbor(pixels, width, height, x, y)
                    ):
                        fringe_pixels += 1
            bleed_components = edge_bleed_components(rgba)
            top_sliver_components = thin_top_sliver_components(rgba)
            x0, y0, x1, y1 = bbox
            metrics.append(
                {
                    "frame": index,
                    "bbox": [x0, y0, x1, y1],
                    "bbox_width": x1 - x0,
                    "bbox_height": y1 - y0,
                    "center": [(x0 + x1) / 2, (y0 + y1) / 2],
                    "edge_pixels": edge_pixels,
                    "edge_bleed_components": len(bleed_components),
                    "edge_bleed_boxes": [list(box) for _, box in bleed_components],
                    "thin_top_sliver_components": len(top_sliver_components),
                    "thin_top_sliver_boxes": [list(box) for _, box in top_sliver_components],
                    "magenta_fringe_pixels": fringe_pixels,
                }
            )
        else:
            metrics.append(
                {
                    "frame": index,
                    "bbox": None,
                    "bbox_width": 0,
                    "bbox_height": 0,
                    "center": [0, 0],
                    "edge_pixels": edge_pixels,
                    "edge_bleed_components": 0,
                    "edge_bleed_boxes": [],
                    "thin_top_sliver_components": 0,
                    "thin_top_sliver_boxes": [],
                    "magenta_fringe_pixels": fringe_pixels,
                }
            )
    return metrics


def frame_diff_mean(a: Image.Image, b: Image.Image) -> float:
    diff = ImageChops.difference(a.convert("RGBA"), b.convert("RGBA"))
    stat = ImageStat.Stat(diff)
    return sum(float(value) for value in stat.mean) / len(stat.mean)


def temporal_metrics(frames: list[Image.Image], metrics: list[dict[str, object]]) -> dict[str, object]:
    if len(frames) < 2:
        return {
            "center_steps": [],
            "center_step_median": 0.0,
            "center_step_max": 0.0,
            "center_step_outlier_ratio": 0.0,
            "center_loop_step": 0.0,
            "scale_step_ratio_max": 0.0,
            "diff_means": [],
            "diff_mean_median": 0.0,
            "diff_mean_max": 0.0,
            "diff_outlier_ratio": 0.0,
            "loop_diff_mean": 0.0,
            "loop_diff_ratio": 0.0,
        }

    centers = [item["center"] for item in metrics]
    widths = [float(item["bbox_width"]) for item in metrics]
    heights = [float(item["bbox_height"]) for item in metrics]
    center_steps: list[float] = []
    scale_step_ratios: list[float] = []
    diff_means: list[float] = []
    for index in range(len(frames) - 1):
        c1 = centers[index]
        c2 = centers[index + 1]
        center_steps.append(math.dist((float(c1[0]), float(c1[1])), (float(c2[0]), float(c2[1]))))
        width_ratio = max(widths[index], widths[index + 1]) / max(1.0, min(widths[index], widths[index + 1]))
        height_ratio = max(heights[index], heights[index + 1]) / max(1.0, min(heights[index], heights[index + 1]))
        scale_step_ratios.append(max(width_ratio, height_ratio))
        diff_means.append(frame_diff_mean(frames[index], frames[index + 1]))

    first_center = centers[0]
    last_center = centers[-1]
    center_loop_step = math.dist(
        (float(last_center[0]), float(last_center[1])),
        (float(first_center[0]), float(first_center[1])),
    )
    loop_diff_mean = frame_diff_mean(frames[-1], frames[0])
    center_step_median = median(center_steps)
    diff_mean_median = median(diff_means)
    return {
        "center_steps": center_steps,
        "center_step_median": center_step_median,
        "center_step_max": max(center_steps, default=0.0),
        "center_step_outlier_ratio": max(center_steps, default=0.0) / max(center_step_median, 1.0),
        "center_loop_step": center_loop_step,
        "scale_step_ratio_max": max(scale_step_ratios, default=0.0),
        "diff_means": diff_means,
        "diff_mean_median": diff_mean_median,
        "diff_mean_max": max(diff_means, default=0.0),
        "diff_outlier_ratio": max(diff_means, default=0.0) / max(diff_mean_median, 0.01),
        "loop_diff_mean": loop_diff_mean,
        "loop_diff_ratio": loop_diff_mean / max(diff_mean_median, 0.01),
    }


def inspect_summary(payload: dict[str, object]) -> dict[str, object]:
    temporal = payload.get("temporal") if isinstance(payload.get("temporal"), dict) else {}
    return {
        "ok": payload.get("ok"),
        "input": payload.get("input"),
        "rows": payload.get("rows"),
        "cols": payload.get("cols"),
        "frames": payload.get("frames"),
        "width_ratio": round(float(payload.get("width_ratio", 0.0)), 3),
        "height_ratio": round(float(payload.get("height_ratio", 0.0)), 3),
        "center_drift": round(float(payload.get("center_drift", 0.0)), 3),
        "max_edge_pixels": payload.get("max_edge_pixels"),
        "max_edge_bleed_components": payload.get("max_edge_bleed_components"),
        "max_thin_top_sliver_components": payload.get("max_thin_top_sliver_components"),
        "max_magenta_fringe_pixels": payload.get("max_magenta_fringe_pixels"),
        "center_step_outlier_ratio": round(float(temporal.get("center_step_outlier_ratio", 0.0)), 3),
        "scale_step_ratio_max": round(float(temporal.get("scale_step_ratio_max", 0.0)), 3),
        "diff_outlier_ratio": round(float(temporal.get("diff_outlier_ratio", 0.0)), 3),
        "loop_diff_ratio": round(float(temporal.get("loop_diff_ratio", 0.0)), 3),
    }


def cmd_inspect_sheet(args: argparse.Namespace) -> None:
    frames = iter_input_frames(args.input, args.rows, args.cols, args.threshold, args.key_softness)
    metrics = frame_metrics(frames)
    temporal = temporal_metrics(frames, metrics)
    widths = [int(item["bbox_width"]) for item in metrics if int(item["bbox_width"]) > 0]
    heights = [int(item["bbox_height"]) for item in metrics if int(item["bbox_height"]) > 0]
    centers = [item["center"] for item in metrics if int(item["bbox_width"]) > 0]
    width_ratio = (max(widths) / min(widths)) if widths else 0
    height_ratio = (max(heights) / min(heights)) if heights else 0
    center_drift = 0.0
    if centers:
        xs = [float(item[0]) for item in centers]
        ys = [float(item[1]) for item in centers]
        center_drift = max(max(xs) - min(xs), max(ys) - min(ys))
    max_edge_pixels = max((int(item["edge_pixels"]) for item in metrics), default=0)
    max_edge_bleed_components = max((int(item["edge_bleed_components"]) for item in metrics), default=0)
    max_thin_top_sliver_components = max((int(item["thin_top_sliver_components"]) for item in metrics), default=0)
    max_fringe_pixels = max((int(item["magenta_fringe_pixels"]) for item in metrics), default=0)
    cell = Image.open(args.input).size
    cell_width = cell[0] // args.cols
    ok = (
        len(frames) >= args.min_frames
        and width_ratio <= args.max_scale_ratio
        and height_ratio <= args.max_scale_ratio
        and center_drift <= args.max_center_drift * max(cell_width, 1)
        and max_edge_pixels <= args.max_edge_pixels
        and max_edge_bleed_components <= args.max_edge_bleed_components
        and max_thin_top_sliver_components <= args.max_thin_top_sliver_components
        and max_fringe_pixels <= args.max_fringe_pixels
        and float(temporal["center_step_max"]) <= args.max_center_step * max(cell_width, 1)
        and float(temporal["center_step_outlier_ratio"]) <= args.max_center_step_outlier_ratio
        and float(temporal["scale_step_ratio_max"]) <= args.max_scale_step_ratio
        and float(temporal["diff_outlier_ratio"]) <= args.max_diff_outlier_ratio
        and float(temporal["loop_diff_ratio"]) <= args.max_loop_diff_ratio
    )
    payload = {
        "ok": ok,
        "input": str(args.input),
        "rows": args.rows,
        "cols": args.cols,
        "frames": len(frames),
        "width_ratio": width_ratio,
        "height_ratio": height_ratio,
        "center_drift": center_drift,
        "max_edge_pixels": max_edge_pixels,
        "max_edge_bleed_components": max_edge_bleed_components,
        "max_thin_top_sliver_components": max_thin_top_sliver_components,
        "max_magenta_fringe_pixels": max_fringe_pixels,
        "temporal": temporal,
        "metrics": metrics,
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    stdout_payload = inspect_summary(payload) if args.summary else payload
    print(json.dumps(stdout_payload, indent=2, ensure_ascii=False))
    if not ok and args.reject:
        raise SystemExit(1)


def cmd_promote_candidate(args: argparse.Namespace) -> None:
    index = f"{args.index:02d}"
    out_dir = args.output_dir
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    candidate_path = args.candidate.expanduser()
    inspect_path = args.inspect.expanduser()
    if not candidate_path.exists() or not candidate_path.is_file():
        raise SystemExit(f"candidate does not exist or is not a file: {candidate_path}")
    if not inspect_path.exists() or not inspect_path.is_file():
        raise SystemExit(f"inspect JSON does not exist or is not a file: {inspect_path}")

    inspect_data = read_json_object(inspect_path)
    if inspect_data is None:
        raise SystemExit(f"inspect JSON is not a readable object: {inspect_path}")
    if inspect_data.get("ok") is not True:
        raise SystemExit(f"candidate inspect is not ok; refusing to promote: {inspect_path}")
    inspected_input = inspect_data.get("input")
    if not isinstance(inspected_input, str) or resolve_for_compare(Path(inspected_input)) != resolve_for_compare(candidate_path):
        raise SystemExit(f"inspect input does not match candidate: {inspect_path}")

    source_path = args.source.expanduser() if args.source else None
    if source_path is not None:
        if not source_path.exists() or not source_path.is_file():
            raise SystemExit(f"source does not exist or is not a file: {source_path}")
        if not is_generated_image_path(source_path):
            raise SystemExit(f"source is not under generated_images: {source_path}")
        if file_sha256(source_path) != file_sha256(candidate_path):
            raise SystemExit("source and candidate are not byte-for-byte identical")

    promoted_raw = raw_dir / f"{index}.png"
    promoted_inspect = raw_dir / f"{index}.inspect.json"
    shutil.copy2(candidate_path, promoted_raw)
    promoted_inspect_data = dict(inspect_data)
    promoted_inspect_data["input"] = str(promoted_raw.resolve())
    promoted_inspect_data["promoted_from_candidate_input"] = str(candidate_path.resolve())
    promoted_inspect.write_text(json.dumps(promoted_inspect_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    manifest_path = args.manifest or (out_dir / "manifest.json")
    if args.update_manifest:
        if not manifest_path.exists():
            raise SystemExit(f"manifest does not exist: {manifest_path}")
        manifest = read_json_object(manifest_path)
        if manifest is None:
            raise SystemExit(f"manifest is not a readable object: {manifest_path}")
        stickers = manifest.get("stickers")
        if not isinstance(stickers, list):
            raise SystemExit("manifest stickers must be a list")
        sticker = None
        for item in stickers:
            if isinstance(item, dict) and str(item.get("index")).zfill(2) == index:
                sticker = item
                break
        if sticker is None:
            raise SystemExit(f"manifest has no sticker index {index}")

        if source_path is not None:
            sticker["image_gen_source_path"] = str(source_path.resolve())
        elif not isinstance(sticker.get("image_gen_source_path"), str):
            raise SystemExit("--source is required when manifest sticker has no image_gen_source_path")
        sticker["creative_source"] = "image_gen"
        sticker["postprocess_input_path"] = str(promoted_raw.resolve())
        sticker["selected_candidate_id"] = args.candidate_id
        sticker["selected_inspect_path"] = str(promoted_inspect.resolve())
        sticker["selection_reason"] = args.selection_reason

        candidates = sticker.get("generation_candidates")
        if not isinstance(candidates, list):
            candidates = []
            sticker["generation_candidates"] = candidates
        candidate_record = {
            "candidate_id": args.candidate_id,
            "image_gen_source_path": str(source_path.resolve()) if source_path is not None else sticker.get("image_gen_source_path"),
            "raw_path": str(candidate_path.resolve()),
            "inspect_path": str(inspect_path.resolve()),
            "inspect_ok": True,
            "frames": inspect_data.get("frames"),
            "temporal": inspect_data.get("temporal"),
        }
        for pos, existing in enumerate(candidates):
            if isinstance(existing, dict) and existing.get("candidate_id") == args.candidate_id:
                candidates[pos] = candidate_record
                break
        else:
            candidates.append(candidate_record)
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    payload = {
        "promoted_raw": str(promoted_raw.resolve()),
        "promoted_inspect": str(promoted_inspect.resolve()),
        "candidate_id": args.candidate_id,
        "manifest": str(manifest_path.resolve()) if args.update_manifest else None,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def image_info(path: Path) -> dict[str, object]:
    with Image.open(path) as img:
        return {
            "file": str(path),
            "size": list(img.size),
            "bytes": path.stat().st_size,
            "format": img.format,
            "animated": bool(getattr(img, "is_animated", False)),
            "frames": int(getattr(img, "n_frames", 1)),
        }


def gif_frame_quality(path: Path) -> dict[str, object]:
    max_edge_pixels = 0
    max_edge_bleed_components = 0
    max_thin_top_sliver_components = 0
    max_visible_fringe_pixels = 0
    max_visible_green_spill_pixels = 0
    full_canvas_frames = 0
    frames: list[Image.Image] = []
    with Image.open(path) as img:
        for frame in ImageSequence.Iterator(img):
            rgba = frame.convert("RGBA")
            frames.append(rgba)
            bbox = rgba.getbbox()
            if bbox == (0, 0, rgba.width, rgba.height):
                full_canvas_frames += 1
            alpha = rgba.getchannel("A")
            edge_pixels = 0
            visible_fringe_pixels = 0
            visible_green_spill_pixels = 0
            pixels = rgba.load()
            width, height = rgba.size
            for x in range(width):
                for y in (0, 1, 2, height - 3, height - 2, height - 1):
                    if 0 <= y < height and alpha.getpixel((x, y)) >= VISIBLE_ALPHA_THRESHOLD:
                        edge_pixels += 1
            for y in range(height):
                for x in (0, 1, 2, width - 3, width - 2, width - 1):
                    if 0 <= x < width and alpha.getpixel((x, y)) >= VISIBLE_ALPHA_THRESHOLD:
                        edge_pixels += 1
            for y in range(height):
                for x in range(width):
                    r, g, b, a = pixels[x, y]
                    if (
                        a >= VISIBLE_ALPHA_THRESHOLD
                        and is_magenta_fringe(r, g, b)
                        and has_transparent_neighbor(pixels, width, height, x, y)
                    ):
                        visible_fringe_pixels += 1
                    if a >= VISIBLE_ALPHA_THRESHOLD and is_green_screen_spill(r, g, b):
                        visible_green_spill_pixels += 1
            max_edge_pixels = max(max_edge_pixels, edge_pixels)
            max_edge_bleed_components = max(max_edge_bleed_components, len(edge_bleed_components(rgba)))
            max_thin_top_sliver_components = max(
                max_thin_top_sliver_components,
                len(thin_top_sliver_components(rgba)),
            )
            max_visible_fringe_pixels = max(max_visible_fringe_pixels, visible_fringe_pixels)
            max_visible_green_spill_pixels = max(max_visible_green_spill_pixels, visible_green_spill_pixels)
    return {
        "max_edge_pixels": max_edge_pixels,
        "max_edge_bleed_components": max_edge_bleed_components,
        "max_thin_top_sliver_components": max_thin_top_sliver_components,
        "max_visible_fringe_pixels": max_visible_fringe_pixels,
        "max_visible_green_spill_pixels": max_visible_green_spill_pixels,
        "full_canvas_frames": full_canvas_frames,
        "temporal": temporal_metrics(frames, frame_metrics(frames)) if frames else {},
    }


def static_frame_layout_quality(path: Path) -> dict[str, object]:
    with Image.open(path) as img:
        rgba = next(ImageSequence.Iterator(img)).convert("RGBA")
    bbox = alpha_bbox(rgba)
    canvas_area = rgba.width * rgba.height
    components = sorted(alpha_components(rgba), key=lambda item: item[0], reverse=True)
    large_components = [
        (area, component_bbox)
        for area, component_bbox in components
        if canvas_area and area / canvas_area >= 0.03
    ]
    quality: dict[str, object] = {
        "has_visible_content": bbox is not None,
        "visible_bbox": list(bbox) if bbox else None,
        "visible_width_ratio": 0.0,
        "visible_height_ratio": 0.0,
        "visible_bbox_area_ratio": 0.0,
        "visible_bbox_fill_ratio": 0.0,
        "visible_pixel_ratio": 0.0,
        "large_component_count": len(large_components),
        "largest_component_height_ratio": 0.0,
        "largest_component_width_ratio": 0.0,
        "largest_component_area_ratio": 0.0,
        "largest_two_component_vertical_gap_ratio": 0.0,
    }
    if large_components:
        largest_area, largest_bbox = max(
            large_components,
            key=lambda item: (item[1][3] - item[1][1], item[0]),
        )
        quality.update(
            {
                "largest_component_height_ratio": (largest_bbox[3] - largest_bbox[1]) / rgba.height if rgba.height else 0.0,
                "largest_component_width_ratio": (largest_bbox[2] - largest_bbox[0]) / rgba.width if rgba.width else 0.0,
                "largest_component_area_ratio": largest_area / canvas_area if canvas_area else 0.0,
            }
        )
    if len(large_components) >= 2:
        first = large_components[0][1]
        second = large_components[1][1]
        vertical_gap = max(0, max(first[1], second[1]) - min(first[3], second[3]))
        quality["largest_two_component_vertical_gap_ratio"] = vertical_gap / rgba.height if rgba.height else 0.0
    if bbox is None:
        return quality

    left, top, right, bottom = bbox
    bbox_width = max(0, right - left)
    bbox_height = max(0, bottom - top)
    bbox_area = bbox_width * bbox_height
    alpha = rgba.getchannel("A")
    visible_pixels = 0
    for y in range(top, bottom):
        for x in range(left, right):
            if alpha.getpixel((x, y)) >= VISIBLE_ALPHA_THRESHOLD:
                visible_pixels += 1

    quality.update(
        {
            "visible_width_ratio": bbox_width / rgba.width if rgba.width else 0.0,
            "visible_height_ratio": bbox_height / rgba.height if rgba.height else 0.0,
            "visible_bbox_area_ratio": bbox_area / canvas_area if canvas_area else 0.0,
            "visible_bbox_fill_ratio": visible_pixels / bbox_area if bbox_area else 0.0,
            "visible_pixel_ratio": visible_pixels / canvas_area if canvas_area else 0.0,
        }
    )
    return quality


def transparent_asset_quality(path: Path) -> dict[str, object]:
    with Image.open(path) as img:
        rgba = next(ImageSequence.Iterator(img)).convert("RGBA")
    total = rgba.width * rgba.height
    visible_pixels = 0
    opaque_dark_pixels = 0
    alpha = rgba.getchannel("A")
    pixels = rgba.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, a = pixels[x, y]
            if alpha.getpixel((x, y)) >= VISIBLE_ALPHA_THRESHOLD:
                visible_pixels += 1
            if a >= 250 and r <= 35 and g <= 35 and b <= 35:
                opaque_dark_pixels += 1
    return {
        "visible_pixel_ratio": visible_pixels / total if total else 0.0,
        "transparent_pixel_ratio": 1.0 - (visible_pixels / total if total else 0.0),
        "opaque_dark_pixel_ratio": opaque_dark_pixels / total if total else 0.0,
    }


def add_check(report: dict[str, object], ok: bool, message: str) -> None:
    key = "passed" if ok else "failed"
    report[key].append(message)


def check_file(
    report: dict[str, object],
    path: Path,
    expected_size: tuple[int, int],
    max_bytes: int | None,
    formats: Iterable[str],
) -> None:
    if not path.exists():
        add_check(report, False, f"Missing {path.name}")
        return
    info = image_info(path)
    report["files"].append(info)
    add_check(report, tuple(info["size"]) == expected_size, f"{path.name} dimensions {info['size']} expected {expected_size}")
    if max_bytes is not None:
        add_check(report, int(info["bytes"]) <= max_bytes, f"{path.name} bytes {info['bytes']} <= {max_bytes}")
    add_check(report, str(info["format"]).upper() in set(formats), f"{path.name} format {info['format']} in {sorted(formats)}")


def white_edge_fractions(path: Path) -> dict[str, float]:
    with Image.open(path) as img:
        rgba = img.convert("RGBA")
    width, height = rgba.size

    def whiteish(pixel: tuple[int, int, int, int]) -> bool:
        r, g, b, a = pixel
        return a > 0 and r >= 245 and g >= 245 and b >= 245

    if width <= 0 or height <= 0:
        return {"top": 0.0, "bottom": 0.0, "left": 0.0, "right": 0.0}
    return {
        "top": sum(whiteish(rgba.getpixel((x, 0))) for x in range(width)) / width,
        "bottom": sum(whiteish(rgba.getpixel((x, height - 1))) for x in range(width)) / width,
        "left": sum(whiteish(rgba.getpixel((0, y))) for y in range(height)) / height,
        "right": sum(whiteish(rgba.getpixel((width - 1, y))) for y in range(height)) / height,
    }


def has_white_border(path: Path, threshold: float) -> bool:
    fractions = white_edge_fractions(path)
    return all(value >= threshold for value in fractions.values())


def iter_text_fields(value: object, prefix: str = "manifest") -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        yield prefix, value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield from iter_text_fields(child, f"{prefix}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_text_fields(child, f"{prefix}[{index}]")


def has_unnegated_policy_term(text: str, term: str) -> bool:
    lowered = text.lower()
    lowered_term = term.lower()
    start = 0
    while True:
        index = lowered.find(lowered_term, start)
        if index < 0:
            return False
        prefix = lowered[max(0, index - 28) : index]
        if not any(marker in prefix for marker in NEGATED_VISUAL_POLICY_MARKERS):
            return True
        start = index + len(lowered_term)


def visual_policy_findings(value: object, limit: int = 20) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    unicode_findings: list[dict[str, object]] = []
    term_findings: list[dict[str, object]] = []
    for field_path, text in iter_text_fields(value):
        chars = sorted(set(EMOJI_RE.findall(text)))
        if chars and len(unicode_findings) < limit:
            unicode_findings.append({"path": field_path, "chars": "".join(chars)})

        matched_terms = [term for term in RESTRICTED_VISUAL_POLICY_TERMS if has_unnegated_policy_term(text, term)]
        if matched_terms and len(term_findings) < limit:
            term_findings.append({"path": field_path, "terms": matched_terms[:5]})
    return unicode_findings, term_findings


def check_no_restricted_visual_policy(report: dict[str, object], label: str, value: object) -> None:
    unicode_findings, term_findings = visual_policy_findings(value)
    add_check(
        report,
        not unicode_findings,
        f"{label} has no Unicode emoji characters; found {unicode_findings}",
    )
    add_check(
        report,
        not term_findings,
        f"{label} has no restricted visual-policy terms; found {term_findings}",
    )


def check_prompt_files_no_restricted_visual_policy(report: dict[str, object], prompts_dir: Path) -> None:
    if not prompts_dir.exists():
        return
    prompt_payload: dict[str, str] = {}
    for path in sorted(prompts_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".txt", ".md", ".json"}:
            continue
        try:
            prompt_payload[str(path.relative_to(prompts_dir))] = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            prompt_payload[str(path.relative_to(prompts_dir))] = path.read_text(encoding="utf-8", errors="ignore")
    if prompt_payload:
        check_no_restricted_visual_policy(report, "prompt files", prompt_payload)


def iter_manifest_items(manifest: dict[str, object]) -> list[tuple[str, dict[str, object]]]:
    items: list[tuple[str, dict[str, object]]] = []
    stickers = manifest.get("stickers")
    if isinstance(stickers, list):
        for index, item in enumerate(stickers, start=1):
            if isinstance(item, dict):
                label = str(item.get("index") or f"sticker-{index:02d}")
                items.append((label, item))

    for asset_key in ("assets", "album_assets"):
        assets = manifest.get(asset_key)
        if isinstance(assets, dict):
            for label, item in assets.items():
                if isinstance(item, dict):
                    items.append((str(label), item))
                else:
                    items.append((str(label), {"creative_source": None}))
        elif isinstance(assets, list):
            for index, item in enumerate(assets, start=1):
                if isinstance(item, dict):
                    label = str(item.get("kind") or item.get("name") or f"asset-{index:02d}")
                    items.append((label, item))
    return items


def is_generated_image_path(path: Path) -> bool:
    return "generated_images" in path.parts


def is_original_image_gen_output_path(path: Path) -> bool:
    parts = path.expanduser().parts
    try:
        generated_index = parts.index("generated_images")
    except ValueError:
        return False
    if len(parts) != generated_index + 3:
        return False
    thread_dir = parts[generated_index + 1]
    return bool(GENERATED_IMAGE_THREAD_RE.match(thread_dir))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_image_gen_source_path(report: dict[str, object], label: str, item: dict[str, object]) -> Path | None:
    raw_path = item.get("image_gen_source_path")
    add_check(report, isinstance(raw_path, str) and bool(raw_path.strip()), f"{label} has image_gen_source_path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None

    source_path = Path(raw_path).expanduser()
    add_check(report, source_path.is_absolute(), f"{label} image_gen_source_path is absolute")
    add_check(report, source_path.exists(), f"{label} image_gen_source_path exists")
    add_check(report, source_path.is_file(), f"{label} image_gen_source_path is a file")
    add_check(report, is_generated_image_path(source_path), f"{label} image_gen_source_path is under generated_images")
    add_check(
        report,
        is_original_image_gen_output_path(source_path),
        f"{label} image_gen_source_path is an original imagegen output in generated_images/<thread-id>/<file>",
    )
    return source_path


def check_image_gen_path_field(report: dict[str, object], label: str, item: dict[str, object], field: str) -> Path | None:
    raw_path = item.get(field)
    add_check(report, isinstance(raw_path, str) and bool(raw_path.strip()), f"{label} has {field}")
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None

    source_path = Path(raw_path).expanduser()
    add_check(report, source_path.is_absolute(), f"{label} {field} is absolute")
    add_check(report, source_path.exists(), f"{label} {field} exists")
    add_check(report, source_path.is_file(), f"{label} {field} is a file")
    add_check(report, is_generated_image_path(source_path), f"{label} {field} is under generated_images")
    add_check(
        report,
        is_original_image_gen_output_path(source_path),
        f"{label} {field} is an original imagegen output in generated_images/<thread-id>/<file>",
    )
    return source_path


def image_size_for_qc(path: Path | None) -> tuple[int, int] | None:
    if path is None or not path.exists() or not path.is_file():
        return None
    try:
        with Image.open(path) as img:
            return img.size
    except Exception:
        return None


def check_postprocess_input_path(
    report: dict[str, object],
    label: str,
    item: dict[str, object],
    source_path: Path | None,
    allow_derived_input: bool = False,
) -> Path | None:
    raw_path = item.get("postprocess_input_path")
    add_check(report, isinstance(raw_path, str) and bool(raw_path.strip()), f"{label} has postprocess_input_path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None

    input_path = Path(raw_path).expanduser()
    add_check(report, input_path.is_absolute(), f"{label} postprocess_input_path is absolute")
    add_check(report, input_path.exists(), f"{label} postprocess_input_path exists")
    add_check(report, input_path.is_file(), f"{label} postprocess_input_path is a file")
    if (
        source_path
        and source_path.exists()
        and input_path.exists()
        and source_path.is_file()
        and input_path.is_file()
        and not allow_derived_input
    ):
        add_check(
            report,
            file_sha256(source_path) == file_sha256(input_path),
            f"{label} postprocess_input_path matches image_gen_source_path",
        )
    elif allow_derived_input:
        add_check(report, True, f"{label} postprocess_input_path may be approved typography composite")
    return input_path


def check_path_field(
    report: dict[str, object],
    label: str,
    item: dict[str, object],
    field: str,
    expect_file: bool = True,
) -> Path | None:
    raw_path = item.get(field)
    add_check(report, isinstance(raw_path, str) and bool(raw_path.strip()), f"{label} has {field}")
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None

    path = Path(raw_path).expanduser()
    add_check(report, path.is_absolute(), f"{label} {field} is absolute")
    add_check(report, path.exists(), f"{label} {field} exists")
    if expect_file:
        add_check(report, path.is_file(), f"{label} {field} is a file")
    else:
        add_check(report, path.is_dir(), f"{label} {field} is a directory")
    return path


def count_png_files(path: Path | None) -> int:
    if path is None or not path.exists() or not path.is_dir():
        return 0
    return len([child for child in path.iterdir() if child.is_file() and child.suffix.lower() == ".png"])


def count_keyed_output_frames(path: Path | None) -> int:
    if path is None or not path.exists() or not path.is_dir():
        return 0
    selected = sorted(child for child in path.iterdir() if child.is_file() and re.match(r"^selected_\d+\.png$", child.name))
    if selected:
        return len(selected)
    numbered = sorted(child for child in path.iterdir() if child.is_file() and re.match(r"^\d+\.png$", child.name))
    if numbered:
        return len(numbered)
    return count_png_files(path)


def frame_count_for_image(path: Path | None) -> int:
    if path is None or not path.exists() or not path.is_file():
        return 0
    try:
        with Image.open(path) as img:
            return int(getattr(img, "n_frames", 1))
    except Exception:
        return 0


def check_seedance_video_source(
    report: dict[str, object],
    label: str,
    item: dict[str, object],
    manifest: dict[str, object],
    postprocess_input_path: Path | None,
) -> None:
    model = str(item.get("video_model") or manifest.get("video_model") or "")
    add_check(report, "seedance-1-5-pro" in model.lower(), f"{label} video_model is Seedance 1.5 Pro")

    audio_policy = str(item.get("video_audio_policy") or manifest.get("video_audio_policy") or "").lower()
    add_check(report, audio_policy == "silent", f"{label} video_audio_policy is silent")

    video_input_mode = str(item.get("video_input_mode") or manifest.get("video_input_mode") or "first_last_frame").lower()
    add_check(
        report,
        video_input_mode in {"first_last_frame", "first_frame"},
        f"{label} video_input_mode is first_last_frame or first_frame",
    )
    start_frame_path = check_image_gen_path_field(report, label, item, "start_frame_source_path")
    end_frame_path: Path | None = None
    if video_input_mode == "first_last_frame":
        end_frame_path = check_image_gen_path_field(report, label, item, "end_frame_source_path")
        start_size = image_size_for_qc(start_frame_path)
        end_size = image_size_for_qc(end_frame_path)
        if start_size is not None and end_size is not None:
            add_check(report, start_size == end_size, f"{label} start/end frame sizes match: {start_size} == {end_size}")
        if start_frame_path is not None and end_frame_path is not None:
            same_start_end = resolve_for_compare(start_frame_path) == resolve_for_compare(end_frame_path)
            same_approved = item.get("end_frame_same_as_start_approved") is True
            same_reason = item.get("end_frame_same_as_start_reason")
            add_check(
                report,
                not same_start_end or same_approved,
                f"{label} identical start/end frames are explicitly approved",
            )
            if same_start_end:
                add_check(
                    report,
                    isinstance(same_reason, str) and bool(same_reason.strip()),
                    f"{label} identical start/end frames have a loop-closure reason",
                )
    else:
        fallback_reason = item.get("first_frame_only_reason") or manifest.get("first_frame_only_reason")
        add_check(
            report,
            isinstance(fallback_reason, str) and bool(fallback_reason.strip()),
            f"{label} first-frame-only mode has explicit reason",
        )

    video_source_path = check_path_field(report, label, item, "video_source_path", expect_file=True)
    if video_source_path is not None and postprocess_input_path is not None:
        add_check(
            report,
            resolve_for_compare(postprocess_input_path) == resolve_for_compare(video_source_path),
            f"{label} postprocess_input_path matches video_source_path",
        )

    prompt_path = check_path_field(report, label, item, "video_prompt_path", expect_file=True)
    if prompt_path is not None and prompt_path.exists():
        try:
            prompt_text = prompt_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            prompt_text = prompt_path.read_text(encoding="utf-8", errors="ignore")
        unicode_findings, term_findings = visual_policy_findings(prompt_text)
        add_check(report, not unicode_findings, f"{label} video prompt has no Unicode emoji characters; found {unicode_findings}")
        add_check(report, not term_findings, f"{label} video prompt has no unnegated restricted visual-policy terms; found {term_findings}")

    task_report_raw = (
        item.get("video_task_report_path")
        or item.get("seedance_task_report_path")
        or item.get("ark_task_report_path")
    )
    task_item = dict(item)
    if isinstance(task_report_raw, str):
        task_item["video_task_report_path"] = task_report_raw
    task_report_path = check_path_field(report, label, task_item, "video_task_report_path", expect_file=True)
    task_report = read_json_object(task_report_path) if task_report_path is not None else None
    add_check(report, task_report is not None, f"{label} video_task_report_path is readable JSON object")
    if task_report is not None:
        add_check(report, task_report.get("status") == "succeeded", f"{label} Seedance task status is succeeded")
        report_model = str(task_report.get("model") or "")
        add_check(report, "seedance-1-5-pro" in report_model.lower(), f"{label} Seedance task model is 1.5 Pro")
        add_check(report, task_report.get("generate_audio") is False, f"{label} Seedance task generate_audio is false")
        add_check(report, task_report.get("watermark") is not True, f"{label} Seedance task watermark is not true")

    keyed_frames_dir = check_path_field(report, label, item, "keyed_frames_dir", expect_file=False)
    keyed_frame_count = count_keyed_output_frames(keyed_frames_dir)
    add_check(report, keyed_frame_count >= 24, f"{label} keyed output frame count {keyed_frame_count} >= 24 for video mode")

    gif_path = check_path_field(report, label, item, "transparent_gif_source", expect_file=True)
    gif_frames = frame_count_for_image(gif_path)
    add_check(report, gif_frames >= 24, f"{label} final GIF frames {gif_frames} >= 24 for video mode")
    if keyed_frame_count and gif_frames:
        add_check(report, keyed_frame_count == gif_frames, f"{label} keyed output frame count {keyed_frame_count} matches final GIF frames {gif_frames}")
    frame_sample_count = item.get("frame_sample_count")
    if isinstance(frame_sample_count, int):
        add_check(report, keyed_frame_count == frame_sample_count, f"{label} keyed output frame count {keyed_frame_count} matches frame_sample_count {frame_sample_count}")
        add_check(report, gif_frames == frame_sample_count, f"{label} final GIF frames {gif_frames} match frame_sample_count {frame_sample_count}")

    if str(item.get("local_loop_fallback") or "").lower() in {"true", "1", "yes"}:
        add_check(report, False, f"{label} does not use local_loop_fallback")
    if item.get("image_loop_source_path") or item.get("still_loop_source_path"):
        add_check(report, False, f"{label} has no still-image loop source path in video mode")


def read_json_object(path: Path) -> dict[str, object] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def resolve_for_compare(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def manifest_uses_video_mode(path: Path) -> bool:
    manifest = read_json_object(path)
    if manifest is None:
        return False
    if str(manifest.get("motion") or "").lower() != "animated":
        return False
    manifest_source_mode = str(manifest.get("animated_source_mode") or "").lower()
    stickers = manifest.get("stickers")
    if not isinstance(stickers, list):
        return manifest_source_mode in VIDEO_SOURCE_MODES
    for item in stickers:
        if not isinstance(item, dict):
            continue
        item_source_mode = str(item.get("animated_source_mode") or manifest_source_mode).lower()
        if item_source_mode in VIDEO_SOURCE_MODES or item.get("creative_source") == "seedance_video":
            return True
    return False


def manifest_uses_green_screen_video(path: Path) -> bool:
    manifest = read_json_object(path)
    if manifest is None:
        return False
    manifest_source_mode = str(manifest.get("animated_source_mode") or "").lower()
    if manifest_source_mode == "green_screen_video":
        return True
    stickers = manifest.get("stickers")
    if not isinstance(stickers, list):
        return False
    for item in stickers:
        if not isinstance(item, dict):
            continue
        if str(item.get("animated_source_mode") or manifest_source_mode).lower() == "green_screen_video":
            return True
    return False


def is_approved_static_text_overlay(item: dict[str, object]) -> bool:
    overlay_keys = (
        "local_text_overlay",
        "typography_overlay",
        "local_typography",
        "post_added_text",
        "image_draw_text",
    )
    overlay_used = any(bool(item.get(key)) for key in overlay_keys)
    return overlay_used and item.get("typography_overlay_approved") is True


def check_animated_candidate_audit(
    report: dict[str, object],
    label: str,
    item: dict[str, object],
    source_path: Path | None,
    postprocess_input_path: Path | None,
) -> None:
    candidate_id = item.get("selected_candidate_id")
    add_check(
        report,
        isinstance(candidate_id, str) and bool(candidate_id.strip()),
        f"{label} has selected_candidate_id",
    )

    raw_inspect_path = item.get("selected_inspect_path")
    add_check(
        report,
        isinstance(raw_inspect_path, str) and bool(raw_inspect_path.strip()),
        f"{label} has selected_inspect_path",
    )
    inspect_path: Path | None = None
    inspect_data: dict[str, object] | None = None
    if isinstance(raw_inspect_path, str) and raw_inspect_path.strip():
        inspect_path = Path(raw_inspect_path).expanduser()
        add_check(report, inspect_path.is_absolute(), f"{label} selected_inspect_path is absolute")
        add_check(report, inspect_path.exists(), f"{label} selected_inspect_path exists")
        add_check(report, inspect_path.is_file(), f"{label} selected_inspect_path is a file")
        if inspect_path.exists() and inspect_path.is_file():
            inspect_data = read_json_object(inspect_path)
            add_check(report, inspect_data is not None, f"{label} selected_inspect_path is readable JSON object")
            if inspect_data is not None:
                add_check(report, inspect_data.get("ok") is True, f"{label} selected candidate inspect ok is true")
                inspected_input = inspect_data.get("input")
                if isinstance(inspected_input, str) and postprocess_input_path is not None:
                    add_check(
                        report,
                        resolve_for_compare(Path(inspected_input)) == resolve_for_compare(postprocess_input_path),
                        f"{label} selected_inspect_path input matches postprocess_input_path",
                    )

    candidates = item.get("generation_candidates")
    add_check(report, isinstance(candidates, list) and bool(candidates), f"{label} has generation_candidates")
    if not isinstance(candidates, list) or not candidates:
        return

    candidate_items = [candidate for candidate in candidates if isinstance(candidate, dict)]
    selected_index: int | None = None
    selected_candidate: dict[str, object] | None = None
    for index, candidate in enumerate(candidate_items):
        if candidate.get("candidate_id") == candidate_id:
            selected_index = index
            selected_candidate = candidate
            break

    add_check(report, selected_candidate is not None, f"{label} selected_candidate_id exists in generation_candidates")
    if selected_candidate is None:
        return

    selected_source = selected_candidate.get("image_gen_source_path")
    if isinstance(selected_source, str) and source_path is not None:
        add_check(
            report,
            resolve_for_compare(Path(selected_source)) == resolve_for_compare(source_path),
            f"{label} selected candidate source matches image_gen_source_path",
        )

    later_passing: list[str] = []
    if selected_index is not None:
        for candidate in candidate_items[selected_index + 1 :]:
            inspect_candidate_path = candidate.get("inspect_path")
            if not isinstance(inspect_candidate_path, str) or not inspect_candidate_path.strip():
                continue
            candidate_inspect = read_json_object(Path(inspect_candidate_path).expanduser())
            if candidate_inspect and candidate_inspect.get("ok") is True:
                later_passing.append(str(candidate.get("candidate_id") or inspect_candidate_path))
    selection_reason = item.get("selection_reason")
    has_reason = isinstance(selection_reason, str) and bool(selection_reason.strip())
    add_check(
        report,
        not later_passing or has_reason,
        f"{label} no later passing candidate ignored without selection_reason; later passing {later_passing}",
    )


def check_manifest(
    report: dict[str, object],
    path: Path,
    require_candidate_audit: bool = True,
    allow_preview_status: bool = False,
) -> None:
    if not path.exists():
        add_check(report, False, f"Missing manifest.json for creative source audit")
        return
    add_check(report, True, "manifest.json exists")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        add_check(report, False, f"manifest.json is readable JSON: {exc}")
        return
    if not isinstance(manifest, dict):
        add_check(report, False, "manifest.json top level is an object")
        return
    check_no_restricted_visual_policy(report, "manifest", manifest)
    check_prompt_files_no_restricted_visual_policy(report, path.parent / "prompts")
    motion = str(manifest.get("motion") or "").lower()
    manifest_source_mode = str(manifest.get("animated_source_mode") or "").lower()
    if motion == "animated":
        recorded_source_modes = [manifest_source_mode] if manifest_source_mode else []
        stickers_for_mode = manifest.get("stickers")
        if isinstance(stickers_for_mode, list):
            for sticker in stickers_for_mode:
                if isinstance(sticker, dict):
                    item_source_mode = str(sticker.get("animated_source_mode") or "").lower()
                    if item_source_mode:
                        recorded_source_modes.append(item_source_mode)
        add_check(
            report,
            bool(recorded_source_modes),
            "animated_source_mode is recorded on manifest or animated stickers",
        )
        forbidden_modes = [mode for mode in recorded_source_modes if mode in FORBIDDEN_ANIMATED_SOURCE_MODES]
        add_check(
            report,
            not forbidden_modes,
            f"animated_source_mode is production source, not still/local loop: {forbidden_modes}",
        )
    status = manifest.get("status")
    if isinstance(status, str) and status.strip():
        preview_statuses = {"preview", "preview_not_submission_ready", "diagnostic", "mockup"}
        add_check(
            report,
            allow_preview_status or status.strip().lower() not in preview_statuses,
            f"manifest status is production-deliverable, not {status!r}",
        )
    processing_notes = manifest.get("processing_notes")
    if isinstance(processing_notes, str) and processing_notes.strip():
        normalized_notes = processing_notes.lower()
        bypass_terms = [
            "--no-reject-raw-sheet",
            "no-reject-raw-sheet",
            "first row",
            "stable row",
            "第一排",
            "稳定帧",
            "重排",
            "可预览版本",
            "bypass",
        ]
        matched_terms = [term for term in bypass_terms if term in normalized_notes]
        add_check(
            report,
            not matched_terms,
            f"processing_notes contain no production bypass terms; matched {matched_terms}",
        )
    items = iter_manifest_items(manifest)
    add_check(report, bool(items), "manifest has sticker or asset items")
    for label, item in items:
        source = item.get("creative_source")
        add_check(report, source in ALLOWED_CREATIVE_SOURCES, f"{label} creative_source is one of {sorted(ALLOWED_CREATIVE_SOURCES)}")
        if source == "image_gen":
            source_path = check_image_gen_source_path(report, label, item)
            check_postprocess_input_path(
                report,
                label,
                item,
                source_path,
                allow_derived_input=is_approved_static_text_overlay(item),
            )
        elif source == "seedance_video":
            postprocess_input_path = check_postprocess_input_path(report, label, item, None)
            check_seedance_video_source(report, label, item, manifest, postprocess_input_path)

    sticker_source_paths: list[str] = []
    stickers = manifest.get("stickers")
    if isinstance(stickers, list):
        for index, item in enumerate(stickers, start=1):
            label = str(item.get("index") or f"{index:02d}") if isinstance(item, dict) else f"{index:02d}"
            if isinstance(item, dict) and isinstance(item.get("image_gen_source_path"), str):
                sticker_source_paths.append(str(Path(str(item["image_gen_source_path"])).expanduser()))
            if motion == "animated" and isinstance(item, dict):
                item_source_mode = str(item.get("animated_source_mode") or manifest_source_mode).lower()
                add_check(
                    report,
                    item_source_mode not in FORBIDDEN_ANIMATED_SOURCE_MODES,
                    f"{label} animated_source_mode is not still/local loop: {item_source_mode!r}",
                )
                if item_source_mode in VIDEO_SOURCE_MODES:
                    add_check(
                        report,
                        item.get("creative_source") == "seedance_video",
                        f"{label} video-mode creative_source is seedance_video",
                    )
            if str(manifest.get("motion")) == "static" and isinstance(item, dict):
                overlay_used = is_approved_static_text_overlay(item) or any(
                    bool(item.get(key))
                    for key in (
                        "local_text_overlay",
                        "typography_overlay",
                        "local_typography",
                        "post_added_text",
                        "image_draw_text",
                    )
                )
                overlay_approved = item.get("typography_overlay_approved") is True
                add_check(
                    report,
                    not overlay_used or overlay_approved,
                    f"{label} local text overlay is explicitly approved",
                )
                if overlay_used:
                    reason = item.get("typography_overlay_reason")
                    original = item.get("original_raw_path") or item.get("raw_original_path")
                    add_check(
                        report,
                        isinstance(reason, str) and bool(reason.strip()),
                        f"{label} local text overlay has reason",
                    )
                    add_check(
                        report,
                        isinstance(original, str) and bool(original.strip()),
                        f"{label} local text overlay preserves original raw path",
                    )
            if require_candidate_audit and str(manifest.get("motion")) == "animated" and isinstance(item, dict):
                if item.get("creative_source") == "image_gen":
                    source_path = check_image_gen_source_path(report, label, item)
                    postprocess_input_path = check_postprocess_input_path(report, label, item, source_path)
                    check_animated_candidate_audit(report, label, item, source_path, postprocess_input_path)
                else:
                    add_check(report, True, f"{label} animated candidate audit is replaced by video provenance audit")
    add_check(
        report,
        len(set(sticker_source_paths)) == len(sticker_source_paths),
        "main stickers use distinct image_gen_source_path values",
    )

    assets = manifest.get("assets") or manifest.get("album_assets")
    if isinstance(assets, dict):
        cover_item = assets.get("cover")
        icon_item = assets.get("icon")
        if isinstance(cover_item, dict) and isinstance(icon_item, dict):
            cover_source = cover_item.get("image_gen_source_path")
            icon_source = icon_item.get("image_gen_source_path")
            same_source = (
                isinstance(cover_source, str)
                and isinstance(icon_source, str)
                and resolve_for_compare(Path(cover_source)) == resolve_for_compare(Path(icon_source))
            )
            override = icon_item.get("cover_icon_identity_match_approved") is True
            add_check(
                report,
                same_source or override,
                "cover and icon share one character source image, or icon identity match is explicitly approved",
            )
            if not same_source and override:
                reason = icon_item.get("cover_icon_identity_match_reason")
                add_check(
                    report,
                    isinstance(reason, str) and bool(reason.strip()),
                    "icon identity-match override has reason",
                )
        for key in ("banner", "reward-guide", "reward-thanks"):
            item = assets.get(key) or assets.get(key.replace("-", "_"))
            has_copy = isinstance(item, dict) and isinstance(item.get("copy"), str) and bool(str(item["copy"]).strip())
            add_check(report, has_copy, f"{key} has theme copy")
            brief = item.get("design_brief") if isinstance(item, dict) else None
            has_brief = isinstance(brief, str) and len(brief.strip()) >= 40
            add_check(report, has_brief, f"{key} has design_brief")


def check_raw_sheet_inspection(report: dict[str, object], out_dir: Path, index: str, args: argparse.Namespace) -> None:
    inspect_path = out_dir / "raw" / f"{index}.inspect.json"
    add_check(report, inspect_path.exists(), f"raw/{index}.inspect.json exists")
    if not inspect_path.exists():
        return
    try:
        data = json.loads(inspect_path.read_text(encoding="utf-8"))
    except Exception as exc:
        add_check(report, False, f"raw/{index}.inspect.json is readable JSON: {exc}")
        return
    if not isinstance(data, dict):
        add_check(report, False, f"raw/{index}.inspect.json top level is an object")
        return

    input_path = data.get("input")
    if isinstance(input_path, str) and input_path.strip():
        expected_raw = (out_dir / "raw" / f"{index}.png").resolve()
        try:
            actual_raw = Path(input_path).expanduser().resolve()
        except Exception:
            actual_raw = Path(input_path).expanduser()
        add_check(report, actual_raw == expected_raw, f"raw/{index}.inspect.json input matches raw/{index}.png")

    add_check(report, data.get("ok") is True, f"raw/{index}.inspect.json ok is true")
    add_check(report, int(data.get("frames", 0)) >= args.min_frames, f"raw/{index}.inspect.json frames {data.get('frames', 0)} >= {args.min_frames}")
    add_check(
        report,
        int(data.get("max_edge_pixels", 0)) <= args.max_gif_edge_pixels,
        f"raw/{index}.inspect.json max edge pixels {data.get('max_edge_pixels', 0)} <= {args.max_gif_edge_pixels}",
    )
    add_check(
        report,
        int(data.get("max_edge_bleed_components", 0)) <= args.max_gif_edge_bleed_components,
        f"raw/{index}.inspect.json edge bleed components {data.get('max_edge_bleed_components', 0)} <= {args.max_gif_edge_bleed_components}",
    )
    add_check(
        report,
        int(data.get("max_thin_top_sliver_components", 0)) <= args.max_gif_thin_top_sliver_components,
        f"raw/{index}.inspect.json thin top sliver components {data.get('max_thin_top_sliver_components', 0)} <= {args.max_gif_thin_top_sliver_components}",
    )
    add_check(
        report,
        int(data.get("max_magenta_fringe_pixels", 0)) <= args.max_visible_fringe_pixels,
        f"raw/{index}.inspect.json magenta fringe pixels {data.get('max_magenta_fringe_pixels', 0)} <= {args.max_visible_fringe_pixels}",
    )
    temporal = data.get("temporal") if isinstance(data.get("temporal"), dict) else {}
    add_check(
        report,
        float(temporal.get("center_step_outlier_ratio", 0.0)) <= args.max_center_step_outlier_ratio,
        f"raw/{index}.inspect.json center step outlier ratio {temporal.get('center_step_outlier_ratio', 0.0):.3f} <= {args.max_center_step_outlier_ratio}",
    )
    add_check(
        report,
        float(temporal.get("scale_step_ratio_max", 0.0)) <= args.max_scale_step_ratio,
        f"raw/{index}.inspect.json max per-frame scale step {temporal.get('scale_step_ratio_max', 0.0):.3f} <= {args.max_scale_step_ratio}",
    )
    add_check(
        report,
        float(temporal.get("diff_outlier_ratio", 0.0)) <= args.max_diff_outlier_ratio,
        f"raw/{index}.inspect.json visual diff outlier ratio {temporal.get('diff_outlier_ratio', 0.0):.3f} <= {args.max_diff_outlier_ratio}",
    )
    add_check(
        report,
        float(temporal.get("loop_diff_ratio", 0.0)) <= args.max_loop_diff_ratio,
        f"raw/{index}.inspect.json loop diff ratio {temporal.get('loop_diff_ratio', 0.0):.3f} <= {args.max_loop_diff_ratio}",
    )


def cmd_qc(args: argparse.Namespace) -> None:
    out_dir = args.output_dir
    report: dict[str, object] = {"passed": [], "failed": [], "files": []}
    main_dir = out_dir / "main"
    thumb_dir = out_dir / "thumbs"
    manifest_path = args.manifest or (out_dir / "manifest.json")
    video_mode_qc = args.motion == "animated" and manifest_uses_video_mode(manifest_path)
    green_screen_video_qc = args.motion == "animated" and manifest_uses_green_screen_video(manifest_path)

    main_extension = ".png" if args.motion == "static" else ".gif"
    main_formats = {"PNG"} if args.motion == "static" else {"GIF"}
    main_files = sorted(main_dir.glob(f"*{main_extension}"))
    unexpected_main_files = sorted(
        path.name
        for path in main_dir.glob("*")
        if path.is_file() and path.suffix.lower() in {".png", ".gif"} and path.suffix.lower() != main_extension
    )
    thumb_files = sorted(thumb_dir.glob("*.png"))
    add_check(report, len(main_files) == args.expected_count, f"main count {len(main_files)} expected {args.expected_count}")
    add_check(report, not unexpected_main_files, f"main directory has no wrong-format files for {args.motion}: {unexpected_main_files}")
    add_check(report, len(thumb_files) == args.expected_count, f"thumb count {len(thumb_files)} expected {args.expected_count}")

    expected_names = [f"{i:02d}" for i in range(1, args.expected_count + 1)]
    add_check(report, [p.stem for p in main_files] == expected_names, "main filenames are consecutive two-digit indexes")
    add_check(report, [p.stem for p in thumb_files] == expected_names, "thumb filenames are consecutive two-digit indexes")

    for path in main_files:
        check_file(report, path, (240, 240), args.main_limit_kb * 1024, main_formats)
        if args.motion == "static" and args.require_static_layout_qc:
            quality = gif_frame_quality(path)
            layout = static_frame_layout_quality(path)
            add_check(
                report,
                bool(layout["has_visible_content"]),
                f"{path.name} has visible sticker content",
            )
            add_check(
                report,
                float(layout["visible_width_ratio"]) >= args.min_static_visible_width_ratio,
                f"{path.name} visible width ratio {layout['visible_width_ratio']:.3f} >= {args.min_static_visible_width_ratio}",
            )
            add_check(
                report,
                float(layout["visible_height_ratio"]) >= args.min_static_visible_height_ratio,
                f"{path.name} visible height ratio {layout['visible_height_ratio']:.3f} >= {args.min_static_visible_height_ratio}",
            )
            add_check(
                report,
                float(layout["visible_bbox_area_ratio"]) >= args.min_static_visible_bbox_area_ratio,
                f"{path.name} visible bbox area ratio {layout['visible_bbox_area_ratio']:.3f} >= {args.min_static_visible_bbox_area_ratio}",
            )
            add_check(
                report,
                float(layout["visible_bbox_fill_ratio"]) >= args.min_static_bbox_fill_ratio,
                f"{path.name} visible bbox fill ratio {layout['visible_bbox_fill_ratio']:.3f} >= {args.min_static_bbox_fill_ratio}",
            )
            add_check(
                report,
                float(layout["largest_component_height_ratio"]) >= args.min_static_primary_component_height_ratio,
                f"{path.name} primary component height ratio {layout['largest_component_height_ratio']:.3f} >= {args.min_static_primary_component_height_ratio}",
            )
            add_check(
                report,
                float(layout["largest_two_component_vertical_gap_ratio"]) <= args.max_static_large_component_vertical_gap_ratio,
                f"{path.name} largest component vertical gap ratio {layout['largest_two_component_vertical_gap_ratio']:.3f} <= {args.max_static_large_component_vertical_gap_ratio}",
            )
            add_check(
                report,
                int(quality["max_edge_pixels"]) <= args.max_gif_edge_pixels,
                f"{path.name} max edge pixels {quality['max_edge_pixels']} <= {args.max_gif_edge_pixels}",
            )
            add_check(
                report,
                int(quality["max_edge_bleed_components"]) <= args.max_gif_edge_bleed_components,
                f"{path.name} thin edge bleed components {quality['max_edge_bleed_components']} <= {args.max_gif_edge_bleed_components}",
            )
            add_check(
                report,
                int(quality["max_thin_top_sliver_components"]) <= args.max_gif_thin_top_sliver_components,
                f"{path.name} thin top sliver components {quality['max_thin_top_sliver_components']} <= {args.max_gif_thin_top_sliver_components}",
            )
            add_check(
                report,
                int(quality["max_visible_fringe_pixels"]) <= args.max_visible_fringe_pixels,
                f"{path.name} visible magenta fringe pixels {quality['max_visible_fringe_pixels']} <= {args.max_visible_fringe_pixels}",
            )
            if green_screen_video_qc:
                add_check(
                    report,
                    int(quality["max_visible_green_spill_pixels"]) <= args.max_visible_green_spill_pixels,
                    f"{path.name} visible green spill pixels {quality['max_visible_green_spill_pixels']} <= {args.max_visible_green_spill_pixels}",
                )
            add_check(report, int(quality["full_canvas_frames"]) == 0, f"{path.name} has no full-canvas opaque frames")
        if args.motion == "animated":
            if args.require_raw_inspection and not video_mode_qc:
                check_raw_sheet_inspection(report, out_dir, path.stem, args)
            elif args.require_raw_inspection and video_mode_qc:
                add_check(report, True, f"{path.name} skips raw sprite-sheet inspection for video-mode source")
            info = image_info(path)
            add_check(report, int(info["frames"]) >= args.min_frames, f"{path.name} frames {info['frames']} >= {args.min_frames}")
            quality = gif_frame_quality(path)
            add_check(
                report,
                int(quality["max_edge_pixels"]) <= args.max_gif_edge_pixels,
                f"{path.name} max edge pixels {quality['max_edge_pixels']} <= {args.max_gif_edge_pixels}",
            )
            add_check(
                report,
                int(quality["max_edge_bleed_components"]) <= args.max_gif_edge_bleed_components,
                f"{path.name} thin edge bleed components {quality['max_edge_bleed_components']} <= {args.max_gif_edge_bleed_components}",
            )
            add_check(
                report,
                int(quality["max_thin_top_sliver_components"]) <= args.max_gif_thin_top_sliver_components,
                f"{path.name} thin top sliver components {quality['max_thin_top_sliver_components']} <= {args.max_gif_thin_top_sliver_components}",
            )
            add_check(
                report,
                int(quality["max_visible_fringe_pixels"]) <= args.max_visible_fringe_pixels,
                f"{path.name} visible magenta fringe pixels {quality['max_visible_fringe_pixels']} <= {args.max_visible_fringe_pixels}",
            )
            if green_screen_video_qc:
                add_check(
                    report,
                    int(quality["max_visible_green_spill_pixels"]) <= args.max_visible_green_spill_pixels,
                    f"{path.name} visible green spill pixels {quality['max_visible_green_spill_pixels']} <= {args.max_visible_green_spill_pixels}",
                )
            add_check(report, int(quality["full_canvas_frames"]) == 0, f"{path.name} has no full-canvas opaque frames")
            temporal = quality.get("temporal") if isinstance(quality.get("temporal"), dict) else {}
            if not args.allow_compact_motion:
                add_check(report, int(info["frames"]) >= 12, f"{path.name} frames {info['frames']} >= 12 for standard-quality motion")
            add_check(
                report,
                float(temporal.get("center_step_outlier_ratio", 0.0)) <= args.max_center_step_outlier_ratio,
                f"{path.name} center step outlier ratio {temporal.get('center_step_outlier_ratio', 0.0):.3f} <= {args.max_center_step_outlier_ratio}",
            )
            add_check(
                report,
                float(temporal.get("scale_step_ratio_max", 0.0)) <= args.max_scale_step_ratio,
                f"{path.name} max per-frame scale step {temporal.get('scale_step_ratio_max', 0.0):.3f} <= {args.max_scale_step_ratio}",
            )
            add_check(
                report,
                float(temporal.get("diff_outlier_ratio", 0.0)) <= args.max_diff_outlier_ratio,
                f"{path.name} visual diff outlier ratio {temporal.get('diff_outlier_ratio', 0.0):.3f} <= {args.max_diff_outlier_ratio}",
            )
            add_check(
                report,
                float(temporal.get("loop_diff_ratio", 0.0)) <= args.max_loop_diff_ratio,
                f"{path.name} loop diff ratio {temporal.get('loop_diff_ratio', 0.0):.3f} <= {args.max_loop_diff_ratio}",
            )
    for path in thumb_files:
        check_file(report, path, (120, 120), args.thumb_limit_kb * 1024, {"PNG"})

    if args.pack_type == "album":
        for kind, spec in ASSET_SPECS.items():
            if kind.startswith("reward") and not args.require_reward:
                continue
            asset_path = existing_asset_path(out_dir, kind)
            check_file(
                report,
                asset_path,
                tuple(spec["size"]),
                int(spec["limit"]),
                {"PNG", "JPEG", "JPG", "GIF"},
            )
            if bool(spec["transparent"]) and asset_path.exists():
                transparent_quality = transparent_asset_quality(asset_path)
                add_check(
                    report,
                    float(transparent_quality["visible_pixel_ratio"]) <= args.max_transparent_asset_visible_pixel_ratio,
                    f"{asset_path.name} transparent asset visible pixel ratio {transparent_quality['visible_pixel_ratio']:.3f} <= {args.max_transparent_asset_visible_pixel_ratio}",
                )
                add_check(
                    report,
                    float(transparent_quality["opaque_dark_pixel_ratio"]) <= args.max_transparent_asset_dark_pixel_ratio,
                    f"{asset_path.name} opaque dark background pixel ratio {transparent_quality['opaque_dark_pixel_ratio']:.3f} <= {args.max_transparent_asset_dark_pixel_ratio}",
                )
            if not bool(spec["transparent"]) and asset_path.exists():
                fractions = white_edge_fractions(asset_path)
                add_check(
                    report,
                    not has_white_border(asset_path, args.max_white_border_edge_fraction),
                    f"{asset_path.name} has no full white border; edge fractions {fractions}",
                )

    meta_path = out_dir / "metadata.csv"
    add_check(report, meta_path.exists(), "metadata.csv exists")
    if meta_path.exists():
        with meta_path.open("r", encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        add_check(report, len(rows) == args.expected_count, f"metadata rows {len(rows)} expected {args.expected_count}")
        meanings = [row.get("meaning", "") for row in rows]
        add_check(report, all(meanings), "all stickers have meaning keywords")
        add_check(report, len(set(meanings)) == len(meanings), "meaning keywords are unique")

    if args.require_manifest:
        check_manifest(
            report,
            manifest_path,
            require_candidate_audit=args.require_candidate_audit,
            allow_preview_status=args.allow_preview_status,
        )

    report["ok"] = not bool(report["failed"])
    report_path = out_dir / args.report_name
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    if args.summary:
        summary = {
            "ok": report["ok"],
            "report": str(report_path.resolve()),
            "passed_count": len(report["passed"]),
            "failed_count": len(report["failed"]),
            "failed": report["failed"][: args.summary_limit],
            "files": report["files"],
        }
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(str(report_path.resolve()))
    if report["failed"]:
        raise SystemExit(1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    sticker = subparsers.add_parser("process-sticker", help="Create main PNG/GIF, thumbnail, and frame PNGs.")
    sticker.add_argument("--input", required=True, type=Path)
    sticker.add_argument("--index", required=True, type=int)
    sticker.add_argument("--output-dir", required=True, type=Path)
    sticker.add_argument("--motion", choices=["static", "animated"], default="animated")
    sticker.add_argument("--rows", type=int, default=1)
    sticker.add_argument("--cols", type=int, default=1)
    sticker.add_argument("--meaning", default="")
    sticker.add_argument("--duration", type=int, default=100)
    sticker.add_argument("--colors", type=int, default=128)
    sticker.add_argument("--threshold", type=int, default=80)
    sticker.add_argument("--key-softness", type=int, default=96)
    sticker.add_argument("--fit-scale", type=float, default=0.86)
    sticker.add_argument("--align", choices=["center", "bottom", "feet"], default="center")
    sticker.add_argument("--thumb-frame", type=int, default=1)
    sticker.add_argument("--preserve-motion", action=argparse.BooleanOptionalAction, default=True)
    sticker.add_argument("--reject-raw-sheet", action=argparse.BooleanOptionalAction, default=True)
    sticker.add_argument("--clean-edge-bleed", action=argparse.BooleanOptionalAction, default=True)
    sticker.add_argument("--max-raw-edge-pixels", type=int, default=0)
    sticker.add_argument("--max-raw-edge-bleed-components", type=int, default=0)
    sticker.add_argument("--max-raw-thin-top-sliver-components", type=int, default=0)
    sticker.add_argument("--max-raw-center-step", type=float, default=0.055)
    sticker.add_argument("--max-raw-center-step-outlier-ratio", type=float, default=2.5)
    sticker.add_argument("--max-raw-scale-step-ratio", type=float, default=1.08)
    sticker.add_argument("--max-raw-diff-outlier-ratio", type=float, default=1.6)
    sticker.add_argument("--max-raw-loop-diff-ratio", type=float, default=1.35)
    sticker.add_argument("--stabilize-position", action=argparse.BooleanOptionalAction, default=False)
    sticker.add_argument("--stabilize-strength", type=float, default=1.0)
    sticker.add_argument("--stabilize-anchor", choices=["center", "bottom", "feet"], default="center")
    sticker.add_argument("--stabilize-mode", choices=["smooth", "median"], default="median")
    sticker.add_argument("--stabilize-window", type=int, default=5)
    sticker.set_defaults(func=cmd_process_sticker)

    asset = subparsers.add_parser("make-asset", help="Create cover, icon, banner, or reward assets.")
    asset.add_argument("--kind", required=True, choices=sorted(ASSET_SPECS))
    asset.add_argument("--input", required=True, type=Path)
    asset.add_argument("--output-dir", required=True, type=Path)
    asset.add_argument("--threshold", type=int, default=80)
    asset.add_argument("--key-softness", type=int, default=96)
    asset.add_argument("--fit-scale", type=float, default=0.9)
    asset.add_argument("--align", choices=["center", "bottom", "feet"], default="center")
    asset.add_argument("--asset-fit", choices=["cover", "contain"], default="cover")
    asset.add_argument("--asset-format", choices=["auto", "png", "jpg", "jpeg"], default="auto")
    asset.add_argument("--jpeg-quality", type=int, default=86)
    asset.add_argument("--remove-magenta", action="store_true")
    asset.add_argument("--background", type=int, nargs=4, default=(255, 255, 255, 255))
    asset.set_defaults(func=cmd_make_asset)

    metadata = subparsers.add_parser("make-metadata", help="Generate metadata.csv from manifest sticker records.")
    metadata.add_argument("--output-dir", required=True, type=Path)
    metadata.add_argument("--manifest", type=Path)
    metadata.add_argument("--output", type=Path)
    metadata.add_argument("--motion", choices=["static", "animated"], default="animated")
    metadata.set_defaults(func=cmd_make_metadata)

    preview = subparsers.add_parser("make-preview-grid", help="Generate a compact thumbnail contact sheet.")
    preview.add_argument("--output-dir", required=True, type=Path)
    preview.add_argument("--manifest", type=Path)
    preview.add_argument("--output", type=Path)
    preview.add_argument("--count", type=int)
    preview.add_argument("--cols", type=int, default=4)
    preview.add_argument("--cell-size", type=int, default=140)
    preview.add_argument("--thumb-size", type=int, default=120)
    preview.add_argument("--jpeg-quality", type=int, default=92)
    preview.add_argument("--background", type=int, nargs=3, default=(245, 245, 245))
    preview.set_defaults(func=cmd_make_preview_grid)

    inspect = subparsers.add_parser("inspect-sheet", help="Inspect a raw animated sheet before processing.")
    inspect.add_argument("--input", required=True, type=Path)
    inspect.add_argument("--output", type=Path, help="Write the full inspection JSON to this path.")
    inspect.add_argument("--summary", action=argparse.BooleanOptionalAction, default=False, help="Print only compact metrics to stdout.")
    inspect.add_argument("--rows", required=True, type=int)
    inspect.add_argument("--cols", required=True, type=int)
    inspect.add_argument("--threshold", type=int, default=80)
    inspect.add_argument("--key-softness", type=int, default=96)
    inspect.add_argument("--min-frames", type=int, default=12)
    inspect.add_argument("--max-scale-ratio", type=float, default=1.18)
    inspect.add_argument("--max-center-drift", type=float, default=0.12)
    inspect.add_argument("--max-center-step", type=float, default=0.055)
    inspect.add_argument("--max-center-step-outlier-ratio", type=float, default=2.5)
    inspect.add_argument("--max-edge-pixels", type=int, default=0)
    inspect.add_argument("--max-edge-bleed-components", type=int, default=0)
    inspect.add_argument("--max-thin-top-sliver-components", type=int, default=0)
    inspect.add_argument("--max-fringe-pixels", type=int, default=24)
    inspect.add_argument("--max-scale-step-ratio", type=float, default=1.08)
    inspect.add_argument("--max-diff-outlier-ratio", type=float, default=1.6)
    inspect.add_argument("--max-loop-diff-ratio", type=float, default=1.35)
    inspect.add_argument("--reject", action="store_true")
    inspect.set_defaults(func=cmd_inspect_sheet)

    promote = subparsers.add_parser("promote-candidate", help="Promote a passing animated sheet candidate to raw/NN.png.")
    promote.add_argument("--output-dir", required=True, type=Path)
    promote.add_argument("--index", required=True, type=int)
    promote.add_argument("--candidate-id", required=True)
    promote.add_argument("--candidate", required=True, type=Path)
    promote.add_argument("--inspect", required=True, type=Path)
    promote.add_argument("--source", type=Path, help="Original image_gen source path; must match candidate bytes.")
    promote.add_argument("--manifest", type=Path)
    promote.add_argument("--update-manifest", action=argparse.BooleanOptionalAction, default=True)
    promote.add_argument(
        "--selection-reason",
        default="latest passing candidate promoted by promote-candidate",
    )
    promote.set_defaults(func=cmd_promote_candidate)

    qc = subparsers.add_parser("qc", help="Validate a processed WeChat sticker output folder.")
    qc.add_argument("--output-dir", required=True, type=Path)
    qc.add_argument("--expected-count", required=True, type=int)
    qc.add_argument("--pack-type", choices=["album", "single"], default="album")
    qc.add_argument("--motion", choices=["static", "animated"], default="animated")
    qc.add_argument("--report-name", default="qc-report.json")
    qc.add_argument("--summary", action=argparse.BooleanOptionalAction, default=False, help="Print compact QC summary instead of only the report path.")
    qc.add_argument("--summary-limit", type=int, default=8)
    qc.add_argument("--main-limit-kb", type=int, default=500)
    qc.add_argument("--thumb-limit-kb", type=int, default=50)
    qc.add_argument("--min-frames", type=int, default=12)
    qc.add_argument("--max-gif-edge-pixels", type=int, default=0)
    qc.add_argument("--max-gif-edge-bleed-components", type=int, default=0)
    qc.add_argument("--max-gif-thin-top-sliver-components", type=int, default=0)
    qc.add_argument("--max-visible-fringe-pixels", type=int, default=0)
    qc.add_argument("--max-visible-green-spill-pixels", type=int, default=1)
    qc.add_argument("--max-white-border-edge-fraction", type=float, default=0.98)
    qc.add_argument("--max-transparent-asset-visible-pixel-ratio", type=float, default=0.98)
    qc.add_argument("--max-transparent-asset-dark-pixel-ratio", type=float, default=0.05)
    qc.add_argument("--require-static-layout-qc", action=argparse.BooleanOptionalAction, default=True)
    qc.add_argument("--min-static-visible-width-ratio", type=float, default=0.58)
    qc.add_argument("--min-static-visible-height-ratio", type=float, default=0.62)
    qc.add_argument("--min-static-visible-bbox-area-ratio", type=float, default=0.36)
    qc.add_argument("--min-static-bbox-fill-ratio", type=float, default=0.16)
    qc.add_argument("--min-static-primary-component-height-ratio", type=float, default=0.42)
    qc.add_argument("--max-static-large-component-vertical-gap-ratio", type=float, default=0.08)
    qc.add_argument("--allow-compact-motion", action=argparse.BooleanOptionalAction, default=False)
    qc.add_argument("--max-center-step-outlier-ratio", type=float, default=2.5)
    qc.add_argument("--max-scale-step-ratio", type=float, default=1.08)
    qc.add_argument("--max-diff-outlier-ratio", type=float, default=1.6)
    qc.add_argument("--max-loop-diff-ratio", type=float, default=1.35)
    qc.add_argument("--require-raw-inspection", action=argparse.BooleanOptionalAction, default=True)
    qc.add_argument("--manifest", type=Path)
    qc.add_argument("--require-manifest", action=argparse.BooleanOptionalAction, default=True)
    qc.add_argument("--require-candidate-audit", action=argparse.BooleanOptionalAction, default=True)
    qc.add_argument("--allow-preview-status", action=argparse.BooleanOptionalAction, default=False)
    qc.add_argument("--require-reward", action=argparse.BooleanOptionalAction, default=True)
    qc.set_defaults(func=cmd_qc)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
