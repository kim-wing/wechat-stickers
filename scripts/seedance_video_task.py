#!/usr/bin/env python3
import argparse
import base64
import json
import os
import http.client
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional


API_BASE = "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks"
RETRYABLE_ERRORS = (
    TimeoutError,
    ConnectionError,
    http.client.RemoteDisconnected,
    http.client.IncompleteRead,
    ssl.SSLError,
    urllib.error.URLError,
)


def data_url(path: Path) -> str:
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    suffix = path.suffix.lower().lstrip(".") or "png"
    if suffix == "jpg":
        suffix = "jpeg"
    return "data:image/%s;base64,%s" % (suffix, data)


def request_json(method: str, url: str, api_key: str, payload: Optional[dict] = None) -> dict:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    last_error: Optional[BaseException] = None
    for attempt in range(1, 5):
        req = urllib.request.Request(url, data=body, method=method)
        req.add_header("Authorization", "Bearer %s" % api_key)
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise SystemExit("HTTP %s: %s" % (exc.code, detail)) from exc
        except RETRYABLE_ERRORS as exc:
            last_error = exc
            if attempt == 4:
                break
            time.sleep(2 ** attempt)
    raise SystemExit("request failed after retries: %s" % last_error)


def download(url: str, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    last_error: Optional[BaseException] = None
    for attempt in range(1, 5):
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                out.write_bytes(resp.read())
            return
        except RETRYABLE_ERRORS as exc:
            last_error = exc
            if attempt == 4:
                break
            time.sleep(2 ** attempt)
    raise SystemExit("download failed after retries: %s" % last_error)


def video_url_from_response(response: dict) -> Optional[str]:
    content = response.get("content") or {}
    if isinstance(content, dict):
        for key in ("video_url", "file_url", "url"):
            value = content.get(key)
            if isinstance(value, str) and value:
                return value
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                value = item.get("video_url") or item.get("file_url") or item.get("url")
                if isinstance(value, str) and value:
                    return value
    return None


def normalized_report(
    task_id: Optional[str],
    created: dict,
    final: dict,
    history: list,
    video_url: Optional[str],
    video_out: Path,
    payload: dict,
) -> dict:
    return {
        "task_id": task_id,
        "status": final.get("status"),
        "model": final.get("model") or payload.get("model"),
        "generate_audio": final.get("generate_audio", payload.get("generate_audio")),
        "watermark": final.get("watermark", payload.get("watermark")),
        "duration": final.get("duration", payload.get("duration")),
        "ratio": final.get("ratio", payload.get("ratio")),
        "resolution": final.get("resolution", payload.get("resolution")),
        "video_url": video_url,
        "downloaded_video_path": str(video_out) if video_url else None,
        "poll_count": len(history),
        "create_response": created,
        "final_response": final,
        "history": history[-5:],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Create and poll a Seedance first-last-frame video task.")
    parser.add_argument("--start", required=True, type=Path)
    parser.add_argument("--end", required=True, type=Path)
    parser.add_argument("--prompt", required=True, type=Path)
    parser.add_argument("--video-out", required=True, type=Path)
    parser.add_argument("--report-out", required=True, type=Path)
    parser.add_argument("--model", default="doubao-seedance-1-5-pro-251215")
    parser.add_argument("--duration", type=int, default=5)
    parser.add_argument("--resolution", default="480p")
    parser.add_argument("--ratio", default="1:1")
    parser.add_argument("--poll-seconds", type=int, default=10)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    args = parser.parse_args()

    api_key = os.environ.get("ARK_API_KEY")
    if not api_key:
        raise SystemExit("ARK_API_KEY missing")

    payload = {
        "model": args.model,
        "content": [
            {"type": "text", "text": args.prompt.read_text(encoding="utf-8")},
            {"type": "image_url", "image_url": {"url": data_url(args.start)}, "role": "first_frame"},
            {"type": "image_url", "image_url": {"url": data_url(args.end)}, "role": "last_frame"},
        ],
        "ratio": args.ratio,
        "resolution": args.resolution,
        "duration": args.duration,
        "generate_audio": False,
        "watermark": False,
    }

    created = request_json("POST", API_BASE, api_key, payload)
    task_id = created.get("id")
    if not isinstance(task_id, str) or not task_id:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(
            json.dumps(normalized_report(None, created, created, [created], None, args.video_out, payload), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        raise SystemExit("Task creation did not return id")

    deadline = time.time() + args.timeout_seconds
    history = [created]
    final = created
    while time.time() < deadline:
        time.sleep(args.poll_seconds)
        final = request_json("GET", "%s/%s" % (API_BASE, task_id), api_key)
        history.append(final)
        status = str(final.get("status", "")).lower()
        if status in {"succeeded", "failed", "cancelled", "expired"}:
            break

    video_url = video_url_from_response(final)
    if str(final.get("status", "")).lower() == "succeeded" and video_url:
        download(video_url, args.video_out)

    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(
        json.dumps(normalized_report(task_id, created, final, history, video_url, args.video_out, payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if str(final.get("status", "")).lower() != "succeeded":
        raise SystemExit("Task ended with status %s" % final.get("status"))
    if not video_url:
        raise SystemExit("Succeeded task did not include video_url")


if __name__ == "__main__":
    main()
