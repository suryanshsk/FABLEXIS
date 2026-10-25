"""Deterministic local video metadata, sampling, and shot analysis."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


REPORT_SCHEMA_VERSION = "1.0"
_PTS_RE = re.compile(r"pts_time:(?P<time>[0-9]+(?:\.[0-9]+)?)")


class MediaAnalysisError(RuntimeError):
    """Raised when local media analysis cannot produce a valid result."""


def _require_file(path: Path) -> Path:
    path = path.expanduser()
    if not path.exists():
        raise MediaAnalysisError(f"Input media does not exist: {path}")
    if not path.is_file():
        raise MediaAnalysisError(f"Input media is not a file: {path}")
    if path.stat().st_size == 0:
        raise MediaAnalysisError(f"Input media is empty: {path}")
    return path.resolve()


def _run(command: list[str], *, timeout: int, tool: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command, capture_output=True, text=True, check=False, timeout=timeout
        )
    except FileNotFoundError as exc:
        raise MediaAnalysisError(f"{tool} is not installed or not on PATH.") from exc
    except subprocess.TimeoutExpired as exc:
        raise MediaAnalysisError(f"{tool} timed out while analyzing the media.") from exc


def probe_video(path: Path, *, ffprobe: str | None = None, timeout: int = 30) -> dict[str, Any]:
    """Return stable FFprobe metadata for a local video."""
    source = _require_file(path)
    executable = ffprobe or shutil.which("ffprobe")
    if not executable:
        raise MediaAnalysisError("FFprobe is not installed or not on PATH.")
    process = _run(
        [
            executable,
            "-v",
            "error",
            "-show_entries",
            (
                "format=format_name,duration,size,bit_rate:"
                "stream=index,codec_type,codec_name,pix_fmt,width,height,"
                "avg_frame_rate,r_frame_rate,nb_frames,time_base,sample_aspect_ratio,"
                "display_aspect_ratio,bit_rate,start_time:stream_tags=rotate"
            ),
            "-of",
            "json",
            str(source),
        ],
        timeout=timeout,
        tool="FFprobe",
    )
    if process.returncode != 0:
        detail = process.stderr.strip() or "FFprobe returned an error."
        raise MediaAnalysisError(f"Could not read media metadata: {detail}")
    try:
        payload = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise MediaAnalysisError("FFprobe returned invalid JSON metadata.") from exc
    streams = payload.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video_stream is None:
        raise MediaAnalysisError("Input media has no video stream.")
    format_data = payload.get("format", {})
    return {
        "source": {
            "name": source.name,
            "path": str(source),
            "size_bytes": source.stat().st_size,
            "sha256": _sha256(source),
        },
        "format": {
            "name": format_data.get("format_name"),
            "duration_seconds": _number(format_data.get("duration")),
            "size_bytes": _integer(format_data.get("size")),
            "bit_rate": _integer(format_data.get("bit_rate")),
        },
        "video": _stream_metadata(video_stream),
        "audio": [
            _audio_metadata(stream)
            for stream in streams
            if stream.get("codec_type") == "audio"
        ],
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _number(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _integer(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _stream_metadata(stream: dict[str, Any]) -> dict[str, Any]:
    fps = _frame_rate(stream.get("avg_frame_rate"))
    nominal_fps = _frame_rate(stream.get("r_frame_rate"))
    return {
        "index": stream.get("index"),
        "codec": stream.get("codec_name"),
        "pixel_format": stream.get("pix_fmt"),
        "width": stream.get("width"),
        "height": stream.get("height"),
        "average_frame_rate": fps,
        "nominal_frame_rate": nominal_fps,
        "variable_frame_rate": bool(fps and nominal_fps and fps != nominal_fps),
        "frame_count": _integer(stream.get("nb_frames")),
        "pixel_aspect_ratio": stream.get("sample_aspect_ratio"),
        "display_aspect_ratio": stream.get("display_aspect_ratio"),
        "time_base": stream.get("time_base"),
        "start_time": _number(stream.get("start_time")),
        "rotation": _integer(stream.get("tags", {}).get("rotate")),
        "bit_rate": _integer(stream.get("bit_rate")),
    }


def _audio_metadata(stream: dict[str, Any]) -> dict[str, Any]:
    return {
        "index": stream.get("index"),
        "codec": stream.get("codec_name"),
        "sample_rate": stream.get("sample_rate"),
        "channels": stream.get("channels"),
        "time_base": stream.get("time_base"),
        "start_time": _number(stream.get("start_time")),
        "bit_rate": _integer(stream.get("bit_rate")),
    }


def _frame_rate(value: Any) -> float | None:
    if not value or value in {"0/0", "N/A"}:
        return None
    try:
        numerator, denominator = str(value).split("/", 1)
        denominator_value = float(denominator)
        return round(float(numerator) / denominator_value, 6) if denominator_value else None
    except (ValueError, TypeError):
        return None


def sample_frames(
    path: Path,
    output_dir: Path,
    *,
    timestamps: list[float],
    width: int = 320,
    height: int = 180,
    ffmpeg: str | None = None,
    timeout: int = 30,
) -> list[dict[str, Any]]:
    """Extract deterministic thumbnails at requested timestamps."""
    source = _require_file(path)
    executable = ffmpeg or shutil.which("ffmpeg")
    if not executable:
        raise MediaAnalysisError("FFmpeg is not installed or not on PATH.")
    if width <= 0 or height <= 0:
        raise MediaAnalysisError("Thumbnail dimensions must be positive.")
    output_dir.mkdir(parents=True, exist_ok=True)
    samples: list[dict[str, Any]] = []
    for index, timestamp in enumerate(sorted(set(max(0.0, float(t)) for t in timestamps))):
        target = output_dir / f"frame_{index:04d}_{timestamp:.3f}.jpg"
        temporary = target.with_suffix(".tmp.jpg")
        process = _run(
            [
                executable,
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{timestamp:.3f}",
                "-i",
                str(source),
                "-frames:v",
                "1",
                "-vf",
                f"scale={width}:{height}",
                "-q:v",
                "2",
                str(temporary),
            ],
            timeout=timeout,
            tool="FFmpeg",
        )
        if process.returncode != 0 or not temporary.exists() or temporary.stat().st_size == 0:
            temporary.unlink(missing_ok=True)
            continue
        temporary.replace(target)
        samples.append({"timestamp_seconds": timestamp, "path": target})
    if not samples:
        raise MediaAnalysisError("FFmpeg could not extract any readable video frames.")
    return samples


def detect_scene_boundaries(
    path: Path,
    *,
    threshold: float = 0.35,
    ffmpeg: str | None = None,
    timeout: int = 60,
) -> list[float]:
    """Estimate visual cut timestamps using FFmpeg's scene filter."""
    source = _require_file(path)
    executable = ffmpeg or shutil.which("ffmpeg")
    if not executable:
        raise MediaAnalysisError("FFmpeg is not installed or not on PATH.")
    if not 0.0 < threshold <= 1.0:
        raise MediaAnalysisError("Scene threshold must be greater than 0 and at most 1.")
    process = _run(
        [
            executable,
            "-hide_banner",
            "-i",
            str(source),
            "-vf",
            f"select='gt(scene\\,{threshold})',showinfo",
            "-an",
            "-f",
            "null",
            "-",
        ],
        timeout=timeout,
        tool="FFmpeg",
    )
    if process.returncode != 0:
        detail = process.stderr.strip() or "FFmpeg scene detection failed."
        raise MediaAnalysisError(f"Could not detect scene boundaries: {detail}")
    return sorted(set(round(float(match.group("time")), 3) for match in _PTS_RE.finditer(process.stderr)))


def build_shot_index(
    duration: float,
    boundaries: list[float],
    thumbnails: list[dict[str, Any]],
    source_id: str,
) -> list[dict[str, Any]]:
    """Build stable, non-overlapping shot records from estimated cuts."""
    if duration <= 0:
        raise MediaAnalysisError("Video duration must be positive.")
    points = [0.0] + sorted(set(max(0.0, min(duration, point)) for point in boundaries)) + [duration]
    points = [point for index, point in enumerate(points) if index == 0 or point > points[index - 1]]
    shots = []
    for index, (start, end) in enumerate(zip(points, points[1:]), start=1):
        if end <= start:
            continue
        midpoint = (start + end) / 2
        thumbnail = min(
            thumbnails,
            key=lambda item: abs(item["timestamp_seconds"] - midpoint),
            default=None,
        )
        shots.append(
            {
                "id": f"shot-{index:04d}",
                "source_id": source_id,
                "start_seconds": round(start, 3),
                "end_seconds": round(end, 3),
                "duration_seconds": round(end - start, 3),
                "thumbnail": str(thumbnail["path"]) if thumbnail else None,
                "boundary_type": "estimated_visual_cut" if index > 1 else "source_start",
            }
        )
    return shots


def _font() -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", 16)
    except OSError:
        return ImageFont.load_default()


def build_contact_sheets(
    thumbnails: list[dict[str, Any]],
    output_dir: Path,
    *,
    columns: int = 4,
    sheet_size: int = 16,
) -> list[Path]:
    """Create labeled chronological contact sheets."""
    if columns <= 0 or sheet_size <= 0:
        raise MediaAnalysisError("Contact-sheet columns and size must be positive.")
    output_dir.mkdir(parents=True, exist_ok=True)
    sheets: list[Path] = []
    font = _font()
    for sheet_index in range(0, len(thumbnails), sheet_size):
        group = thumbnails[sheet_index : sheet_index + sheet_size]
        first_image = Image.open(group[0]["path"]).convert("RGB")
        width, height = first_image.size
        label_height = 28
        rows = (len(group) + columns - 1) // columns
        canvas = Image.new("RGB", (columns * width, rows * (height + label_height)), "#111827")
        draw = ImageDraw.Draw(canvas)
        for offset, item in enumerate(group):
            image = Image.open(item["path"]).convert("RGB")
            x = (offset % columns) * width
            y = (offset // columns) * (height + label_height)
            canvas.paste(image, (x, y))
            draw.text((x + 6, y + height + 5), f"{item['timestamp_seconds']:.2f}s", fill="#ffffff", font=font)
        target = output_dir / f"contact-sheet-{sheet_index // sheet_size + 1:03d}.jpg"
        canvas.save(target, quality=90)
        sheets.append(target)
    return sheets


def analyze_video(
    path: Path,
    output_dir: Path,
    *,
    interval: float = 5.0,
    max_frames: int = 24,
    thumbnail_width: int = 320,
    thumbnail_height: int = 180,
    scene_threshold: float = 0.35,
    ffmpeg: str | None = None,
    ffprobe: str | None = None,
) -> dict[str, Any]:
    """Run the complete deterministic local analysis workflow."""
    if interval <= 0 or max_frames <= 0:
        raise MediaAnalysisError("Sampling interval and maximum frames must be positive.")
    metadata = probe_video(path, ffprobe=ffprobe)
    duration = metadata["format"]["duration_seconds"]
    if not duration or duration <= 0:
        raise MediaAnalysisError("Video duration is unavailable or invalid.")
    last_timestamp = max(0.0, duration - 0.001)
    timestamps = [min(last_timestamp, index * interval) for index in range(max_frames)]
    timestamps = sorted(set(timestamps))
    thumbnails_dir = output_dir / "frames"
    sampled = sample_frames(
        path,
        thumbnails_dir,
        timestamps=timestamps,
        width=thumbnail_width,
        height=thumbnail_height,
        ffmpeg=ffmpeg,
    )
    boundaries = detect_scene_boundaries(path, threshold=scene_threshold, ffmpeg=ffmpeg)
    shots = build_shot_index(duration, boundaries, sampled, metadata["source"]["sha256"][:16])
    sheets = build_contact_sheets(sampled, output_dir / "contact-sheets")
    relative = lambda value: str(Path(value).relative_to(output_dir)).replace("\\", "/")
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "source": {**metadata["source"], "path": metadata["source"]["name"]},
        "media": {key: value for key, value in metadata.items() if key != "source"},
        "settings": {
            "sampling_interval_seconds": interval,
            "max_frames": max_frames,
            "thumbnail": {"width": thumbnail_width, "height": thumbnail_height},
            "scene_threshold": scene_threshold,
        },
        "sampling_timestamps_seconds": [item["timestamp_seconds"] for item in sampled],
        "scene_boundaries_seconds": boundaries,
        "shots": [{**shot, "thumbnail": relative(shot["thumbnail"]) if shot["thumbnail"] else None} for shot in shots],
        "artifacts": {
            "frames": [relative(item["path"]) for item in sampled],
            "contact_sheets": [relative(sheet) for sheet in sheets],
        },
        "warnings": [
            "Shot boundaries are estimated visual cuts, not semantic scene understanding.",
            "No subject, face, speech, emotion, or object recognition was performed.",
        ],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "analysis-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
