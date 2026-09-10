#!/usr/bin/env python3
"""Plan/state driven production helper for WeChat sticker packs.

This script intentionally does not call image generation. Codex still creates
the creative source images, then records their paths in sticker-plan.json. This
helper owns deterministic production stages: Seedance video tasks, GIF
postprocessing, preview grids, QC, and packaging.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from PIL import Image


SCRIPT_DIR = Path(__file__).resolve().parent
SEEDANCE_SCRIPT = SCRIPT_DIR / "seedance_video_task.py"
GREEN_VIDEO_SCRIPT = SCRIPT_DIR / "process_seedance_green_video.py"
PACK_SCRIPT = SCRIPT_DIR / "wechat_sticker_pack.py"

VIDEO_SOURCE_MODES = {"green_screen_video", "background_video"}
DEFAULT_VIDEO_MODEL = "doubao-seedance-1-5-pro-251215"
FORBIDDEN_MODES = {
    "local_composite_preview",
    "user_reference_local_composite_preview",
    "local_loop",
    "still_loop",
    "image_gen_loop",
    "micro_animation_from_still",
}
FORBIDDEN_CREATIVE_SOURCES = {
    "user_reference_local_composite_preview",
    "user_reference_cutout",
    "local_composite",
    "local_loop",
    "still_loop",
}
OUTPUT_FOLDERS = (
    "raw",
    "main",
    "thumbs",
    "frames",
    "keyed_frames",
    "start_frames",
    "end_frames",
    "video",
    "reports",
    "prompts",
    "candidates",
    "assets",
)
EMOJI_CHARS = tuple(chr(code) for code in range(0x1F600, 0x1F650))
RESTRICTED_TERMS = (
    "emoji",
    "黄脸表情",
    "黄色笑脸",
    "圆脸表情",
    "国旗",
    "旗帜素材",
    "五星红旗",
    "中国国旗",
    "美国国旗",
    "日本国旗",
)
NEGATION_MARKERS = (
    "no ",
    "no_",
    "no-",
    "without ",
    "avoid ",
    "禁止",
    "不要",
    "不得",
    "不能",
    "不可",
    "不使用",
    "避免",
    "无",
)
CREATIVE_DIRECTION_FIELDS = ("target_audience", "relationship_context", "conversation_register")
PERSONA_FIELDS = ("core", "worldview", "social_posture", "signature_reaction", "visual_hook")
CREATIVE_STICKER_FIELDS = (
    "trigger_utterance",
    "surface_message",
    "hidden_emotion",
    "social_move",
    "meme_mechanism",
    "visual_hook",
    "punchline_frame",
    "use_case",
    "portfolio_role",
)
CREATIVE_SCORE_WEIGHTS = {
    "context_fit": 2,
    "emotional_precision": 1,
    "persona_fit": 1,
    "visual_hook": 1,
    "surprise": 1,
    "sendability": 2,
    "social_safety": 1,
}
CREATIVE_MIN_WEIGHTED_SCORE = 32


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def plan_output_dir(plan_path: Path, plan: dict[str, Any]) -> Path:
    value = plan.get("output_dir")
    if value:
        path = Path(str(value))
        return path if path.is_absolute() else (plan_path.parent / path).resolve()
    return plan_path.parent.resolve()


def load_plan_and_state(plan_path: Path, state_path: Path | None) -> tuple[dict[str, Any], dict[str, Any], Path, Path]:
    plan_path = plan_path.resolve()
    plan = read_json(plan_path)
    out_dir = plan_output_dir(plan_path, plan)
    state_path = state_path.resolve() if state_path else out_dir / "run-state.json"
    if state_path.exists():
        state = read_json(state_path)
    else:
        state = new_state(plan_path, plan)
        write_json(state_path, state)
    return plan, state, out_dir, state_path


def new_state(plan_path: Path, plan: dict[str, Any]) -> dict[str, Any]:
    stickers = {}
    for sticker in plan.get("stickers", []):
        index = normalize_index(sticker.get("index"))
        stickers[index] = {"status": "planned", "updated_at": now()}
    return {
        "version": 1,
        "plan_path": str(plan_path.resolve()),
        "created_at": now(),
        "updated_at": now(),
        "stickers": stickers,
        "events": [],
    }


def save_state(state_path: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = now()
    write_json(state_path, state)


def normalize_index(value: Any) -> str:
    if isinstance(value, int):
        return f"{value:02d}"
    text = str(value).strip()
    if text.isdigit():
        return f"{int(text):02d}"
    return text


def sticker_map(plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {normalize_index(item.get("index")): item for item in plan.get("stickers", [])}


def ensure_dirs(out_dir: Path) -> None:
    for name in OUTPUT_FOLDERS:
        (out_dir / name).mkdir(parents=True, exist_ok=True)


def parse_indices(raw: str | None, plan: dict[str, Any]) -> list[str]:
    available = sorted(sticker_map(plan))
    if not raw:
        return available
    result: list[str] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            for value in range(int(start), int(end) + 1):
                result.append(f"{value:02d}")
        else:
            result.append(normalize_index(part))
    return [idx for idx in result if idx in available]


def default_path(out_dir: Path, folder: str, index: str, suffix: str) -> Path:
    return out_dir / folder / f"{index}{suffix}"


def sticker_path(sticker: dict[str, Any], key: str, fallback: Path) -> Path:
    value = sticker.get(key)
    if value:
        return Path(str(value)).expanduser().resolve()
    return fallback.resolve()


def contains_restricted_text(value: Any) -> list[str]:
    text = json.dumps(value, ensure_ascii=False).lower()
    found = []
    if any(char in text for char in EMOJI_CHARS):
        found.append("emoji character")
    for term in RESTRICTED_TERMS:
        start = 0
        needle = term.lower()
        while True:
            index = text.find(needle, start)
            if index < 0:
                break
            prefix = text[max(0, index - 18) : index]
            if not any(marker in prefix for marker in NEGATION_MARKERS):
                found.append(term)
                break
            start = index + len(needle)
    return found


def is_present(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return value is not None


def default_portfolio(count: int) -> dict[str, int]:
    return {
        1: {"utility": 1, "persona": 0, "wildcard": 0},
        8: {"utility": 4, "persona": 3, "wildcard": 1},
        16: {"utility": 8, "persona": 5, "wildcard": 3},
        24: {"utility": 12, "persona": 8, "wildcard": 4},
    }.get(count, {"utility": count, "persona": 0, "wildcard": 0})


def portfolio_roles(count: int) -> list[str]:
    portfolio = default_portfolio(count)
    return [
        *(["utility"] * portfolio["utility"]),
        *(["persona"] * portfolio["persona"]),
        *(["wildcard"] * portfolio["wildcard"]),
    ]


def creative_plan_report(plan: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    results: list[dict[str, Any]] = []
    direction = plan.get("creative_direction")
    if not isinstance(direction, dict):
        direction = {}
        errors.append("creative_direction must be an object")
    for field in CREATIVE_DIRECTION_FIELDS:
        if not is_present(direction.get(field)):
            errors.append(f"creative_direction.{field} is required")

    persona = direction.get("persona") if isinstance(direction.get("persona"), dict) else {}
    if not persona:
        errors.append("creative_direction.persona must be an object")
    for field in PERSONA_FIELDS:
        if not is_present(persona.get(field)):
            errors.append(f"creative_direction.persona.{field} is required")
    fingerprint = persona.get("verbal_fingerprint")
    if not isinstance(fingerprint, list) or len([item for item in fingerprint if is_present(item)]) < 3:
        errors.append("creative_direction.persona.verbal_fingerprint needs at least 3 phrases")

    count = int(plan.get("count", 0))
    portfolio = direction.get("portfolio") if isinstance(direction.get("portfolio"), dict) else {}
    declared_total = sum(int(portfolio.get(role, 0) or 0) for role in ("utility", "persona", "wildcard"))
    if declared_total != count:
        errors.append(f"creative_direction.portfolio totals {declared_total}, expected {count}")
    if count > 1 and int(portfolio.get("persona", 0) or 0) < 1:
        errors.append("album portfolio needs at least one persona sticker")
    if count > 1 and int(portfolio.get("wildcard", 0) or 0) < 1:
        errors.append("album portfolio needs at least one wildcard sticker")

    signatures: dict[str, str] = {}
    role_counts = {"utility": 0, "persona": 0, "wildcard": 0}
    anchors: list[tuple[str, str]] = []
    for index, sticker in sticker_map(plan).items():
        for field in CREATIVE_STICKER_FIELDS:
            if not is_present(sticker.get(field)):
                errors.append(f"{index} {field} is required")

        role = str(sticker.get("portfolio_role") or "")
        if role not in role_counts:
            errors.append(f"{index} invalid portfolio_role: {role}")
        else:
            role_counts[role] += 1

        candidates = sticker.get("concept_candidates")
        if not isinstance(candidates, list) or not candidates:
            candidates = []
            errors.append(f"{index} concept_candidates needs at least one concept")
        valid_candidates = [item for item in candidates if isinstance(item, dict)]
        if len(valid_candidates) != len(candidates):
            errors.append(f"{index} every concept candidate must be an object")
        for candidate in valid_candidates:
            for field in ("concept_id", "meme_mechanism", "visual_hook"):
                if not is_present(candidate.get(field)):
                    errors.append(f"{index} concept candidate {field} is required")
        candidate_ids = [str(item.get("concept_id") or "") for item in valid_candidates]
        if any(not value for value in candidate_ids) or len(candidate_ids) != len(set(candidate_ids)):
            errors.append(f"{index} concept candidate ids must be present and unique")
        selected = str(sticker.get("selected_concept_id") or "")
        if not selected or selected not in candidate_ids:
            errors.append(f"{index} selected_concept_id must match a concept candidate")
        if not is_present(sticker.get("selection_reason")):
            errors.append(f"{index} selection_reason is required")
        if sticker.get("concept_tournament_anchor"):
            anchors.append((index, role))
            if len(candidates) < 3:
                errors.append(f"{index} tournament anchor needs at least 3 concepts")
            candidate_directions = {
                (str(item.get("meme_mechanism") or "").strip(), str(item.get("visual_hook") or "").strip())
                for item in valid_candidates
            }
            if len(candidate_directions) != len(valid_candidates):
                errors.append(f"{index} tournament concepts need materially different mechanism/hook pairs")

        review = sticker.get("creative_review")
        if not isinstance(review, dict):
            review = {}
            errors.append(f"{index} creative_review must be an object")
        weighted_score = 0
        score_valid = True
        for field, weight in CREATIVE_SCORE_WEIGHTS.items():
            value = review.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 5:
                errors.append(f"{index} creative_review.{field} must be an integer from 1 to 5")
                score_valid = False
                continue
            weighted_score += value * weight
        if not is_present(review.get("rationale")):
            errors.append(f"{index} creative_review.rationale is required")
        thresholds_ok = score_valid and all(
            (
                weighted_score >= CREATIVE_MIN_WEIGHTED_SCORE,
                int(review.get("context_fit", 0)) >= 4,
                int(review.get("sendability", 0)) >= 4,
                int(review.get("persona_fit", 0)) >= 3,
                int(review.get("social_safety", 0)) >= 3,
            )
        )
        if score_valid and not thresholds_ok:
            errors.append(f"{index} creative score does not meet production thresholds")
        results.append({"index": index, "portfolio_role": role, "weighted_score": weighted_score, "ok": thresholds_ok})

        signature = "|".join(
            str(sticker.get(field) or "").strip().lower()
            for field in ("trigger_utterance", "surface_message", "social_move")
        )
        if signature in signatures:
            errors.append(f"{index} duplicates the social scenario signature of {signatures[signature]}")
        elif signature.strip("|"):
            signatures[signature] = index

    for role, actual in role_counts.items():
        expected = int(portfolio.get(role, 0) or 0)
        if actual != expected:
            errors.append(f"portfolio role {role} has {actual} stickers, expected {expected}")
    if count > 1:
        anchor_roles = {role for _index, role in anchors}
        if len(anchors) < 2:
            errors.append("album needs at least two concept_tournament_anchor stickers")
        if "utility" not in anchor_roles:
            errors.append("concept tournament needs a utility anchor")
        if not anchor_roles.intersection({"persona", "wildcard"}):
            errors.append("concept tournament needs a persona or wildcard anchor")
    if count > 1 and len(signatures) == count:
        warnings.append("exact social-scenario signatures are unique; still inspect semantic overlap manually")

    return {
        "ok": not errors,
        "framework": "first_principles_sendability_v1",
        "thresholds": {
            "weighted_score": CREATIVE_MIN_WEIGHTED_SCORE,
            "context_fit": 4,
            "sendability": 4,
            "persona_fit": 3,
            "social_safety": 3,
        },
        "errors": errors,
        "warnings": warnings,
        "stickers": results,
    }


def build_video_prompt(plan: dict[str, Any], sticker: dict[str, Any]) -> str:
    theme = plan.get("theme", "")
    character = plan.get("character", "")
    action = sticker.get("action") or sticker.get("scene") or ""
    text = sticker.get("text") or sticker.get("copy") or ""
    mode = plan.get("animated_source_mode", "green_screen_video")
    background = "pure flat #00FF00 green screen background" if mode == "green_screen_video" else "stable theme-related designed background"
    direction = plan.get("creative_direction") if isinstance(plan.get("creative_direction"), dict) else {}
    persona = direction.get("persona") if isinstance(direction.get("persona"), dict) else {}
    lines = [
        "Fixed camera, fixed framing, stable character identity, stable subject scale.",
        "No audio, no watermark, no scene cuts, no text morphing, no camera zoom.",
        f"Target audience: {direction.get('target_audience', '')}",
        f"Relationship context: {direction.get('relationship_context', '')}",
        f"Conversation register: {direction.get('conversation_register', '')}",
        f"Persona core: {persona.get('core', '')}",
        f"Persona worldview: {persona.get('worldview', '')}",
        f"Persona social posture: {persona.get('social_posture', '')}",
        f"Persona signature reaction: {persona.get('signature_reaction', '')}",
        f"Persona visual hook: {persona.get('visual_hook', '')}",
        f"Character: {character}",
        f"Theme: {theme}",
        f"Trigger utterance or event: {sticker.get('trigger_utterance', '')}",
        f"Surface message: {sticker.get('surface_message', '')}",
        f"Hidden emotion: {sticker.get('hidden_emotion', '')}",
        f"Social move: {sticker.get('social_move', '')}",
        f"Meme mechanism: {sticker.get('meme_mechanism', '')}",
        f"Visual hook: {sticker.get('visual_hook', '')}",
        f"Punchline frame: {sticker.get('punchline_frame', '')}",
        f"Sticker action: {action}",
        f"Locked visible text/caption if present: {text}",
        f"Background policy: {background}.",
        "Make the action reveal the relationship between the surface message and hidden emotion.",
        "Create a loop-friendly motion whose final pose returns naturally toward the first frame and whose punchline remains readable as a still.",
    ]
    return "\n".join(line for line in lines if line.split(":", 1)[-1].strip())


def command_text(command: list[str]) -> str:
    return " ".join(command)


def run_checked(command: list[str]) -> None:
    subprocess.run(command, check=True)


def process_background_video(
    video: Path,
    frames_dir: Path,
    gif_path: Path,
    thumb_path: Path,
    sample_count: int,
    source_duration: int,
    frame_duration: int,
    colors: int,
) -> None:
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True, exist_ok=True)
    gif_path.parent.mkdir(parents=True, exist_ok=True)
    thumb_path.parent.mkdir(parents=True, exist_ok=True)
    pattern = frames_dir / "frame_%04d.png"
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(video),
            "-vf",
            "fps=%s/%s,scale=240:240:force_original_aspect_ratio=decrease,pad=240:240:(ow-iw)/2:(oh-ih)/2:color=0xffffff"
            % (sample_count, source_duration),
            "-frames:v",
            str(sample_count),
            str(pattern),
        ],
        check=True,
    )
    frames = [Image.open(path).convert("RGB") for path in sorted(frames_dir.glob("frame_*.png"))]
    if not frames:
        raise SystemExit(f"No frames extracted from {video}")
    paletted = [
        frame.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
        for frame in frames
    ]
    paletted[0].save(
        gif_path,
        save_all=True,
        append_images=paletted[1:],
        loop=0,
        duration=frame_duration,
        disposal=2,
        optimize=False,
    )
    frames[0].resize((120, 120), Image.Resampling.LANCZOS).save(thumb_path)


def cmd_init(args: argparse.Namespace) -> None:
    out_dir = args.output_dir.resolve()
    ensure_dirs(out_dir)
    plan_path = out_dir / "sticker-plan.json"
    state_path = out_dir / "run-state.json"
    if plan_path.exists() and not args.force:
        raise SystemExit(f"Plan already exists: {plan_path}")

    video_mode = args.motion == "animated" and args.animated_source_mode in VIDEO_SOURCE_MODES
    stickers = []
    roles = portfolio_roles(args.count)
    for i in range(1, args.count + 1):
        index = f"{i:02d}"
        stickers.append(
            {
                "index": index,
                "scene": "",
                "text": "",
                "meaning": "",
                "action": "",
                "portfolio_role": roles[i - 1],
                "trigger_utterance": "",
                "surface_message": "",
                "hidden_emotion": "",
                "social_move": "",
                "meme_mechanism": "",
                "visual_hook": "",
                "punchline_frame": "",
                "use_case": "",
                "concept_tournament_anchor": False,
                "concept_candidates": [],
                "selected_concept_id": "",
                "selection_reason": "",
                "creative_review": {
                    "context_fit": None,
                    "emotional_precision": None,
                    "persona_fit": None,
                    "visual_hook": None,
                    "surprise": None,
                    "sendability": None,
                    "social_safety": None,
                    "rationale": "",
                },
                "motion_profile": "single_limb" if args.motion == "animated" else "static",
                "sheet_source_path": "",
                "candidate_id": "",
                "rows": 4,
                "cols": 4,
                "frame_duration_ms": 80,
                "phases": [],
                "locked_elements": [],
                "moving_elements": [],
                "visual_review": {"raw_sheet_ok": False, "notes": ""},
                "start_frame_source_path": str((out_dir / "start_frames" / f"{index}.png").resolve()),
                "end_frame_source_path": str((out_dir / "end_frames" / f"{index}.png").resolve()),
                "video_prompt_path": str((out_dir / "prompts" / f"{index}-video-prompt.txt").resolve()),
            }
        )

    plan = {
        "version": 3,
        "pack_name": args.pack_name,
        "slug": args.slug or out_dir.name,
        "output_dir": str(out_dir),
        "pack_type": "single" if args.count == 1 else "album",
        "count": args.count,
        "motion": args.motion,
        "animated_source_mode": args.animated_source_mode if args.motion == "animated" else None,
        "video_input_mode": "first_last_frame" if video_mode else None,
        "video_model": args.video_model if video_mode else None,
        "video_audio_policy": "silent",
        "video_duration": args.video_duration,
        "video_resolution": args.video_resolution,
        "video_ratio": args.video_ratio,
        "video_sample_count": args.video_sample_count,
        "theme": args.theme,
        "character": args.character,
        "creative_direction": {
            "target_audience": args.target_audience,
            "relationship_context": args.relationship_context,
            "conversation_register": args.conversation_register,
            "persona": {
                "core": "",
                "worldview": "",
                "social_posture": "",
                "signature_reaction": "",
                "verbal_fingerprint": [],
                "visual_hook": "",
            },
            "portfolio": default_portfolio(args.count),
        },
        "status": "creative_planning",
        "stickers": stickers,
        "assets": {
            "cover": {},
            "icon": {},
            "banner": {"copy": "", "design_brief": ""},
            "reward-guide": {"copy": "", "design_brief": ""},
            "reward-thanks": {"copy": "", "design_brief": ""},
        },
    }
    if args.count == 1:
        plan["assets"] = {}
    write_json(plan_path, plan)
    write_json(state_path, new_state(plan_path, plan))
    write_json(
        out_dir / "pipeline-lock.json",
        {
            "created_at": now(),
            "motion": args.motion,
            "animated_source_mode": args.animated_source_mode if args.motion == "animated" else None,
            "video_input_mode": "first_last_frame" if video_mode else None,
            "video_model": args.video_model if video_mode else None,
            "downgrade_requires_user_approval": True,
            "forbidden_without_approval": sorted(FORBIDDEN_MODES),
        },
    )
    print(f"plan={plan_path}")
    print(f"state={state_path}")


def cmd_validate(args: argparse.Namespace) -> None:
    plan, _state, out_dir, _state_path = load_plan_and_state(args.plan, args.state)
    errors: list[str] = []
    count = int(plan.get("count", 0))
    stickers = plan.get("stickers", [])
    if count not in {1, 8, 16, 24}:
        errors.append(f"count must be 1/8/16/24, got {count}")
    if len(stickers) != count:
        errors.append(f"stickers length {len(stickers)} does not match count {count}")
    motion = plan.get("motion")
    if motion not in {"static", "animated"}:
        errors.append(f"invalid motion: {motion}")
    if motion == "animated":
        mode = plan.get("animated_source_mode")
        if mode in FORBIDDEN_MODES:
            errors.append(f"forbidden animated_source_mode without explicit diagnostic approval: {mode}")
        if mode not in VIDEO_SOURCE_MODES and mode != "sprite_sheet":
            errors.append(f"invalid animated_source_mode: {mode}")
        if mode in VIDEO_SOURCE_MODES and plan.get("video_model") != DEFAULT_VIDEO_MODEL:
            errors.append(f"video_model should default to {DEFAULT_VIDEO_MODEL}")
        if args.require_secrets and mode in VIDEO_SOURCE_MODES and not os.environ.get("ARK_API_KEY"):
            errors.append("ARK_API_KEY missing")
    lock_path = out_dir / "pipeline-lock.json"
    if lock_path.exists():
        lock = read_json(lock_path)
        locked_mode = lock.get("animated_source_mode")
        if motion == "animated" and locked_mode in VIDEO_SOURCE_MODES | {"sprite_sheet"} and plan.get("animated_source_mode") != locked_mode:
            errors.append(
                "animated_source_mode changed from locked %s to %s without explicit approval"
                % (locked_mode, plan.get("animated_source_mode"))
            )
    for index, sticker in sticker_map(plan).items():
        source = sticker.get("creative_source")
        if source in FORBIDDEN_CREATIVE_SOURCES:
            errors.append(f"{index} forbidden creative_source without explicit diagnostic approval: {source}")
        post = str(sticker.get("postprocess_input_path") or "")
        if post and "/Desktop/" in post and source not in {"image_gen", "seedance_video"}:
            errors.append(f"{index} postprocess_input_path appears to use a user/Desktop reference: {post}")
    restricted = contains_restricted_text(plan)
    if restricted:
        errors.append("restricted visual-policy text found: " + ", ".join(sorted(set(restricted))))
    if args.require_creative:
        creative_report = creative_plan_report(plan)
        errors.extend(f"creative: {message}" for message in creative_report["errors"])
    if args.require_keyframes and plan.get("animated_source_mode") in VIDEO_SOURCE_MODES:
        for index, sticker in sticker_map(plan).items():
            start = sticker_path(sticker, "start_frame_source_path", default_path(out_dir, "start_frames", index, ".png"))
            end = sticker_path(sticker, "end_frame_source_path", default_path(out_dir, "end_frames", index, ".png"))
            if not start.exists():
                errors.append(f"{index} missing start frame: {start}")
            if not end.exists():
                errors.append(f"{index} missing end frame: {end}")
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
        raise SystemExit(1)
    print(json.dumps({"ok": True, "output_dir": str(out_dir), "count": count, "motion": motion}, ensure_ascii=False))


def cmd_creative_qc(args: argparse.Namespace) -> None:
    plan, _state, out_dir, _state_path = load_plan_and_state(args.plan, args.state)
    report = creative_plan_report(plan)
    report_path = out_dir / args.report_name
    write_json(report_path, report)
    if args.verbose:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        failed = [item["index"] for item in report["stickers"] if not item["ok"]]
        print(
            json.dumps(
                {
                    "ok": report["ok"],
                    "report": str(report_path.resolve()),
                    "error_count": len(report["errors"]),
                    "failed_stickers": failed[:8],
                    "first_errors": report["errors"][:8],
                },
                ensure_ascii=False,
            )
        )
    if not report["ok"]:
        raise SystemExit(1)


def submit_one(
    plan: dict[str, Any],
    out_dir: Path,
    index: str,
    sticker: dict[str, Any],
    state_path: Path,
    state: dict[str, Any],
    dry_run: bool,
) -> tuple[str, int]:
    start = sticker_path(sticker, "start_frame_source_path", default_path(out_dir, "start_frames", index, ".png"))
    end = sticker_path(sticker, "end_frame_source_path", default_path(out_dir, "end_frames", index, ".png"))
    prompt = sticker_path(sticker, "video_prompt_path", out_dir / "prompts" / f"{index}-video-prompt.txt")
    video = sticker_path(sticker, "video_source_path", out_dir / "video" / f"{index}.mp4")
    report = sticker_path(sticker, "video_task_report_path", out_dir / "reports" / f"seedance-task-{index}.json")
    if not start.exists():
        raise FileNotFoundError(f"{index} missing start frame: {start}")
    if not end.exists():
        raise FileNotFoundError(f"{index} missing end frame: {end}")
    if not prompt.exists():
        prompt.parent.mkdir(parents=True, exist_ok=True)
        prompt.write_text(build_video_prompt(plan, sticker), encoding="utf-8")

    command = [
        sys.executable,
        str(SEEDANCE_SCRIPT),
        "--start",
        str(start),
        "--end",
        str(end),
        "--prompt",
        str(prompt),
        "--video-out",
        str(video),
        "--report-out",
        str(report),
        "--model",
        str(plan.get("video_model") or DEFAULT_VIDEO_MODEL),
        "--duration",
        str(plan.get("video_duration") or 5),
        "--resolution",
        str(plan.get("video_resolution") or "480p"),
        "--ratio",
        str(plan.get("video_ratio") or "1:1"),
    ]
    if dry_run:
        print(command_text(command))
        return index, 0

    item = state.setdefault("stickers", {}).setdefault(index, {})
    item.update({"status": "video_running", "updated_at": now(), "video_prompt_path": str(prompt), "video_task_report_path": str(report)})
    save_state(state_path, state)
    result = subprocess.run(command)
    item.update({"updated_at": now(), "video_source_path": str(video), "video_task_report_path": str(report)})
    if result.returncode == 0 and video.exists():
        item["status"] = "video_done"
    else:
        item["status"] = "failed"
    save_state(state_path, state)
    return index, result.returncode


def cmd_submit_videos(args: argparse.Namespace) -> None:
    plan, state, out_dir, state_path = load_plan_and_state(args.plan, args.state)
    if plan.get("motion") != "animated" or plan.get("animated_source_mode") not in VIDEO_SOURCE_MODES:
        raise SystemExit("submit-videos only supports animated video modes")
    if not args.dry_run and not os.environ.get("ARK_API_KEY"):
        raise SystemExit("ARK_API_KEY missing")
    if int(plan.get("version", 1)) >= 2:
        creative_report = creative_plan_report(plan)
        write_json(out_dir / "creative-qc.json", creative_report)
        if not creative_report["ok"]:
            raise SystemExit(
                "creative QC failed before video submission: "
                + "; ".join(creative_report["errors"][:5])
            )
    ensure_dirs(out_dir)
    stickers = sticker_map(plan)
    indices = parse_indices(args.indices, plan)
    if not indices:
        raise SystemExit("No matching indices")
    failures = []
    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as pool:
        futures = [
            pool.submit(submit_one, plan, out_dir, index, stickers[index], state_path, state, args.dry_run)
            for index in indices
        ]
        for future in as_completed(futures):
            index, returncode = future.result()
            print(f"{index}: returncode={returncode}")
            if returncode:
                failures.append(index)
    if failures:
        raise SystemExit("Video task failures: " + ", ".join(failures))


def cmd_process_videos(args: argparse.Namespace) -> None:
    plan, state, out_dir, state_path = load_plan_and_state(args.plan, args.state)
    mode = plan.get("animated_source_mode")
    if mode not in VIDEO_SOURCE_MODES:
        raise SystemExit("process-videos only supports green_screen_video/background_video")
    ensure_dirs(out_dir)
    stickers = sticker_map(plan)
    indices = parse_indices(args.indices, plan)
    failures = []
    sample_count = args.sample_count or int(plan.get("video_sample_count") or 36)
    source_duration = int(plan.get("video_duration") or 5)
    for index in indices:
        sticker = stickers[index]
        video = sticker_path(sticker, "video_source_path", out_dir / "video" / f"{index}.mp4")
        if not video.exists():
            failures.append(f"{index}: missing video {video}")
            continue
        if mode == "green_screen_video":
            command = [
                sys.executable,
                str(GREEN_VIDEO_SCRIPT),
                "--video",
                str(video),
                "--frames-dir",
                str(out_dir / "frames" / index),
                "--keyed-dir",
                str(out_dir / "keyed_frames" / index),
                "--gif",
                str(out_dir / "main" / f"{index}.gif"),
                "--thumb",
                str(out_dir / "thumbs" / f"{index}.png"),
                "--sample-count",
                str(sample_count),
                "--source-duration",
                str(source_duration),
                "--duration",
                str(args.frame_duration),
                "--colors",
                str(args.colors),
            ]
            result = subprocess.run(command)
            returncode = result.returncode
        else:
            try:
                process_background_video(
                    video,
                    out_dir / "frames" / index,
                    out_dir / "main" / f"{index}.gif",
                    out_dir / "thumbs" / f"{index}.png",
                    sample_count,
                    source_duration,
                    args.frame_duration,
                    args.colors,
                )
                returncode = 0
            except Exception as exc:
                print(f"{index}: {exc}")
                returncode = 1
        item = state.setdefault("stickers", {}).setdefault(index, {})
        item.update(
            {
                "updated_at": now(),
                "gif_path": str(out_dir / "main" / f"{index}.gif"),
                "thumb_path": str(out_dir / "thumbs" / f"{index}.png"),
                "keyed_frames_dir": str(out_dir / "keyed_frames" / index) if mode == "green_screen_video" else None,
                "frame_sample_count": sample_count,
                "status": "gif_done" if returncode == 0 else "failed",
            }
        )
        save_state(state_path, state)
        print(f"{index}: returncode={returncode}")
        if returncode:
            failures.append(index)
    if failures:
        raise SystemExit("Video processing failures: " + ", ".join(failures))


def run_logged(command: list[str], log_path: Path) -> None:
    """Preserve full subprocess evidence on disk without flooding the conversation."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise subprocess.CalledProcessError(result.returncode, command)


def cmd_process_sheets(args: argparse.Namespace) -> None:
    plan, state, out_dir, state_path = load_plan_and_state(args.plan, args.state)
    if plan.get("motion") != "animated" or plan.get("animated_source_mode") != "sprite_sheet":
        raise SystemExit("process-sheets requires animated sprite_sheet mode")
    cmd_validate(argparse.Namespace(plan=args.plan, state=args.state,
        require_creative=False, require_secrets=False, require_keyframes=False))
    manifest_path = out_dir / "manifest.json"
    if not manifest_path.exists():
        write_json(manifest_path, plan)
    manifest = read_json(manifest_path)
    if manifest.get("animated_source_mode") != "sprite_sheet":
        raise SystemExit("manifest source mode does not match plan")
    for index in parse_indices(args.indices, plan):
        sticker = sticker_map(plan)[index]
        source = Path(sticker.get("sheet_source_path") or "").expanduser()
        candidate_id = str(sticker.get("candidate_id") or "")
        if not source.is_absolute() or not source.is_file():
            raise SystemExit(f"{index}: sheet_source_path must be an existing absolute file")
        if not candidate_id or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in candidate_id):
            raise SystemExit(f"{index}: provide a unique filename-safe candidate_id")
        review = sticker.get("visual_review") or {}
        if review.get("raw_sheet_ok") is not True or not review.get("notes"):
            raise SystemExit(f"{index}: raw sheet needs visual review and notes")
        rows, cols = int(sticker.get("rows", 4)), int(sticker.get("cols", 4))
        duration = int(sticker.get("frame_duration_ms", 80))
        if rows <= 0 or cols <= 0 or rows * cols < 12 or duration < 20 or duration % 10:
            raise SystemExit(f"{index}: require positive grid, >=12 frames and duration >=20ms in 10ms steps")
        with Image.open(source) as im:
            if im.width < cols or im.height < rows:
                raise SystemExit(f"{index}: grid has more cells than image pixels")
        candidate = out_dir / "raw" / f"{candidate_id}.png"
        inspection = out_dir / "raw" / f"{candidate_id}.inspect.json"
        if candidate.exists() and candidate.read_bytes() != source.read_bytes():
            raise SystemExit(f"{index}: candidate id already belongs to different bytes")
        if source.resolve() != candidate.resolve():
            shutil.copy2(source, candidate)
        entry = state.setdefault("stickers", {}).setdefault(index, {})
        entry.update({"status": "sheet_inspecting", "candidate_id": candidate_id})
        save_state(state_path, state)
        step = "inspect"
        log_path = out_dir / "reports" / f"{candidate_id}-{step}.log"
        try:
            run_logged([sys.executable, str(PACK_SCRIPT), "inspect-sheet", "--input", str(candidate),
                "--output", str(inspection), "--rows", str(rows), "--cols", str(cols), "--reject", "--summary"], log_path)
            step = "promote"
            log_path = out_dir / "reports" / f"{candidate_id}-{step}.log"
            run_logged([sys.executable, str(PACK_SCRIPT), "promote-candidate", "--output-dir", str(out_dir),
                "--index", index, "--candidate-id", candidate_id, "--candidate", str(candidate),
                "--inspect", str(inspection), "--source", str(source), "--manifest", str(manifest_path),
                "--selection-reason", str(review["notes"])], log_path)
            step = "encode"
            log_path = out_dir / "reports" / f"{candidate_id}-{step}.log"
            run_logged([sys.executable, str(PACK_SCRIPT), "process-sticker", "--input", str(out_dir / "raw" / f"{index}.png"),
                "--index", index, "--output-dir", str(out_dir), "--motion", "animated",
                "--rows", str(rows), "--cols", str(cols), "--duration", str(duration),
                "--meaning", str(sticker.get("meaning", ""))], log_path)
        except (subprocess.CalledProcessError, SystemExit) as exc:
            entry.update({"status": "failed", "error": f"{step} failed", "log_path": str(log_path)})
            save_state(state_path, state)
            print(json.dumps({"index": index, "candidate": candidate_id, "ok": False,
                "step": step, "log": str(log_path), "inspection": str(inspection)}, ensure_ascii=False))
            raise
        entry.update({"status": "gif_done", "selected_candidate_id": candidate_id,
            "source_path": str(source), "inspect_path": str(inspection), "playback_review_required": True})
        entry.pop("error", None)
        save_state(state_path, state)
        print(json.dumps({"index": index, "candidate": candidate_id, "status": "gif_done",
            "gif": str(out_dir / "main" / f"{index}.gif"), "playback_review_required": True}))
    print("Sheets processed; review decoded GIF playback before final QC.")


def cmd_make_preview(args: argparse.Namespace) -> None:
    plan, _state, out_dir, _state_path = load_plan_and_state(args.plan, args.state)
    output = args.output or (out_dir / "preview-grid.jpg")
    command = [
        sys.executable,
        str(PACK_SCRIPT),
        "make-preview-grid",
        "--output-dir",
        str(out_dir),
        "--manifest",
        str(args.manifest or out_dir / "manifest.json"),
        "--output",
        str(output),
        "--count",
        str(plan.get("count")),
    ]
    if args.cols:
        command.extend(["--cols", str(args.cols)])
    run_checked(command)
    print(str(output.resolve()))


def cmd_qc(args: argparse.Namespace) -> None:
    plan, _state, out_dir, _state_path = load_plan_and_state(args.plan, args.state)
    command = [
        sys.executable,
        str(PACK_SCRIPT),
        "qc",
        "--output-dir",
        str(out_dir),
        "--expected-count",
        str(plan.get("count")),
        "--motion",
        str(plan.get("motion")),
        "--report-name",
        args.report_name,
        "--summary",
        "--summary-limit",
        str(args.summary_limit),
    ]
    command.extend(["--pack-type", str(plan.get("pack_type", "album"))])
    if args.no_require_manifest:
        command.append("--no-require-manifest")
    run_checked(command)


def cmd_package(args: argparse.Namespace) -> None:
    plan, _state, out_dir, _state_path = load_plan_and_state(args.plan, args.state)
    cmd_validate(argparse.Namespace(plan=args.plan, state=args.state,
        require_creative=False, require_secrets=False, require_keyframes=False))
    cmd_qc(argparse.Namespace(plan=args.plan, state=args.state,
        report_name="qc-report.json", summary_limit=8, no_require_manifest=False))
    archive_base = args.output
    if archive_base is None:
        archive_base = out_dir.with_suffix("")
    archive_base = archive_base.resolve()
    if archive_base.suffix == ".zip":
        archive_base = archive_base.with_suffix("")
    path = shutil.make_archive(str(archive_base), "zip", root_dir=out_dir)
    print(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="Create a production output skeleton, sticker-plan.json, and run-state.json.")
    init.add_argument("--output-dir", required=True, type=Path)
    init.add_argument("--pack-name", required=True)
    init.add_argument("--slug")
    init.add_argument("--count", type=int, choices=[1, 8, 16, 24], required=True)
    init.add_argument("--motion", choices=["static", "animated"], required=True)
    init.add_argument("--animated-source-mode", choices=["green_screen_video", "background_video", "sprite_sheet"], default="sprite_sheet")
    init.add_argument("--video-model", default=DEFAULT_VIDEO_MODEL)
    init.add_argument("--video-duration", type=int, default=5)
    init.add_argument("--video-resolution", default="480p")
    init.add_argument("--video-ratio", default="1:1")
    init.add_argument("--video-sample-count", type=int, default=36)
    init.add_argument("--theme", default="")
    init.add_argument("--character", default="")
    init.add_argument("--target-audience", default="")
    init.add_argument("--relationship-context", default="")
    init.add_argument("--conversation-register", default="")
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=cmd_init)

    validate = subparsers.add_parser("validate", help="Validate plan shape, policy constraints, optional keyframes and secrets.")
    validate.add_argument("--plan", required=True, type=Path)
    validate.add_argument("--state", type=Path)
    validate.add_argument("--require-keyframes", action="store_true")
    validate.add_argument("--require-secrets", action="store_true")
    validate.add_argument("--require-creative", action="store_true")
    validate.set_defaults(func=cmd_validate)

    creative_qc = subparsers.add_parser("creative-qc", help="Validate first-principles sendability, persona, portfolio, and concept review fields.")
    creative_qc.add_argument("--plan", required=True, type=Path)
    creative_qc.add_argument("--state", type=Path)
    creative_qc.add_argument("--report-name", default="creative-qc.json")
    creative_qc.add_argument("--verbose", action="store_true")
    creative_qc.set_defaults(func=cmd_creative_qc)

    submit = subparsers.add_parser("submit-videos", help="Submit first/last-frame Seedance tasks with bounded concurrency.")
    submit.add_argument("--plan", required=True, type=Path)
    submit.add_argument("--state", type=Path)
    submit.add_argument("--indices", help="Comma/range list such as 01,03-06. Defaults to all.")
    submit.add_argument("--concurrency", type=int, default=4)
    submit.add_argument("--dry-run", action="store_true")
    submit.set_defaults(func=cmd_submit_videos)

    process = subparsers.add_parser("process-videos", help="Convert downloaded green-screen MP4 files into transparent GIFs.")
    process.add_argument("--plan", required=True, type=Path)
    process.add_argument("--state", type=Path)
    process.add_argument("--indices", help="Comma/range list such as 01,03-06. Defaults to all.")
    process.add_argument("--sample-count", type=int)
    process.add_argument("--frame-duration", type=int, default=70)
    process.add_argument("--colors", type=int, default=96)
    process.set_defaults(func=cmd_process_videos)

    sheets = subparsers.add_parser("process-sheets", help="Inspect and process image-generated frame sheets.")
    sheets.add_argument("--plan", required=True, type=Path)
    sheets.add_argument("--state", type=Path)
    sheets.add_argument("--indices")
    sheets.set_defaults(func=cmd_process_sheets)

    preview = subparsers.add_parser("make-preview", help="Create preview-grid.jpg through the shared pack script.")
    preview.add_argument("--plan", required=True, type=Path)
    preview.add_argument("--state", type=Path)
    preview.add_argument("--manifest", type=Path)
    preview.add_argument("--output", type=Path)
    preview.add_argument("--cols", type=int, default=4)
    preview.set_defaults(func=cmd_make_preview)

    qc = subparsers.add_parser("qc", help="Run shared QC with compact summary.")
    qc.add_argument("--plan", required=True, type=Path)
    qc.add_argument("--state", type=Path)
    qc.add_argument("--report-name", default="qc-report.json")
    qc.add_argument("--summary-limit", type=int, default=8)
    qc.add_argument("--no-require-manifest", action="store_true")
    qc.set_defaults(func=cmd_qc)

    package = subparsers.add_parser("package", help="Zip the output directory.")
    package.add_argument("--plan", required=True, type=Path)
    package.add_argument("--state", type=Path)
    package.add_argument("--output", type=Path)
    package.set_defaults(func=cmd_package)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except subprocess.CalledProcessError as exc:
        # Expected command failures already have compact output and persisted reports.
        raise SystemExit(exc.returncode) from None


if __name__ == "__main__":
    main()
