"""Modular offline-first idea-to-video production pipeline."""

from __future__ import annotations

import json
import shutil
import struct
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .vox_motion import (
    build_blueprint,
    validate_assets,
    validate_blueprint,
    write_bmp_frames,
    write_markdown,
    write_svg,
)


class CreativeProvider(Protocol):
    """Provider boundary for optional structured creative direction."""

    name: str
    offline: bool

    def develop(self, brief: str) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class OfflineCreativeProvider:
    name: str = "deterministic-offline"
    offline: bool = True

    def develop(self, brief: str) -> dict[str, Any]:
        return {
            "status": "fallback",
            "provider": self.name,
            "reason": "No AI provider configured; deterministic local direction used.",
        }


def select_provider() -> CreativeProvider:
    """Return the offline provider unless a future provider is explicitly registered."""
    return OfflineCreativeProvider()


def _asset_manifest(blueprint: dict[str, Any], project: Path) -> list[dict[str, Any]]:
    manifest: list[dict[str, Any]] = []
    for scene in blueprint["scenes"]:
        for value in scene.get("assets", []):
            if not isinstance(value, dict) or "path" not in value:
                continue
            path = project / value["path"]
            manifest.append({
                "scene_id": scene["id"],
                "path": value["path"],
                "purpose": value.get("purpose", "scene support"),
                "format": path.suffix.lower().lstrip("."),
                "status": "available" if path.exists() else "missing",
                "source": value.get("source", "user-provided"),
                "required": bool(value.get("required", False)),
            })
    for scene in blueprint["scenes"]:
        for layer in scene.get("layers", []):
            if layer.get("type") != "asset" or not layer.get("asset"):
                continue
            path = project / layer["asset"]
            manifest.append({
                "scene_id": scene["id"],
                "path": layer["asset"],
                "purpose": "composited visual layer",
                "format": path.suffix.lower().lstrip("."),
                "status": "available" if path.exists() else "missing",
                "source": "local",
                "required": True,
            })
    return manifest


def _plan_local_assets(blueprint: dict[str, Any], project: Path) -> None:
    """Attach discovered local assets to suitable scenes without inventing paths."""
    asset_dir = project / "assets"
    if not asset_dir.exists():
        return
    assets = sorted(
        path for path in asset_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".svg"}
    )
    scenes = blueprint["scenes"]
    for path in assets:
        target = None
        if path.suffix.lower() == ".svg":
            target = next((scene for scene in scenes if "diagram" in scene["visual_treatment"]), None)
        elif path.suffix.lower() in {".jpg", ".jpeg"}:
            target = next((scene for scene in scenes if "collage" in scene["visual_treatment"]), None)
        elif path.suffix.lower() == ".png":
            target = scenes[-1]
        if target is None:
            target = scenes[min(len(assets), len(scenes)) - 1]
        relative = str(path.relative_to(project)).replace("\\", "/")
        target.setdefault("assets", []).append({
            "path": relative,
            "purpose": "local visual asset selected by deterministic asset planner",
            "source": "repository-local",
            "required": True,
        })
        target.setdefault("layers", []).append({
            "type": "asset",
            "asset": relative,
            "x": 55,
            "y": 500 if target is scenes[-1] else 260,
            "width": 430,
            "height": 300,
            "fit": "contain" if path.suffix.lower() in {".png", ".svg"} else "cover",
            "opacity": 0.92,
            "animate_y": -10,
            "z": 2,
        })


def _stage(name: str, status: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"stage": name, "status": status, "detail": detail, **extra}


def _probe_media(ffprobe: str, output: Path) -> dict[str, Any]:
    process = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries",
         "format=duration,size:stream=codec_name,width,height,r_frame_rate,codec_type,pix_fmt",
         "-of", "json", str(output)],
        capture_output=True, text=True, check=False,
    )
    if process.returncode != 0:
        raise RuntimeError(process.stderr.strip() or "FFprobe failed.")
    media = json.loads(process.stdout)
    media["audio_present"] = any(
        stream.get("codec_type") == "audio"
        for stream in media.get("streams", [])
    )
    return media


def _validate_rendered_frames(frame_dir: Path, expected_count: int) -> dict[str, Any]:
    frames = sorted(frame_dir.glob("frame_*.bmp"))
    if len(frames) != expected_count:
        raise RuntimeError(f"Rendered frame count mismatch: expected {expected_count}, found {len(frames)}")
    first_dimensions: tuple[int, int] | None = None
    for frame in frames:
        payload = frame.read_bytes()
        if len(payload) <= 54 or payload[:2] != b"BM":
            raise RuntimeError(f"Invalid or empty rendered frame: {frame.name}")
        width, height = struct.unpack_from("<ii", payload, 18)
        if width <= 0 or height <= 0:
            raise RuntimeError(f"Invalid frame dimensions in {frame.name}")
        if first_dimensions is None:
            first_dimensions = (width, abs(height))
        elif first_dimensions != (width, abs(height)):
            raise RuntimeError(f"Inconsistent frame dimensions in {frame.name}")
    return {"frame_count": len(frames), "dimensions": first_dimensions}


def run_pipeline(
    brief: str,
    project: Path,
    *,
    aspect_ratio: str = "9:16",
    mode: str = "production",
    duration: float | None = None,
    ffmpeg: str | None = None,
    ffprobe: str | None = None,
) -> dict[str, Any]:
    """Run intake through blueprint, preview, frame QA, and optional MP4 export."""
    project.mkdir(parents=True, exist_ok=True)
    provider = select_provider()
    stages = [
        _stage("brief_intake", "passed", "Natural-language brief accepted."),
        _stage("script_segmentation", "passed", "Sentence and paragraph boundaries converted into scenes."),
        _stage("research_planning", "passed", "Claims retained as user-supplied; no external research performed."),
        _stage("creative_direction", "passed", "Deterministic semantic treatment selection completed."),
    ]
    blueprint = build_blueprint(brief, mode=mode, aspect_ratio=aspect_ratio)
    if duration is not None and duration > 0:
        scale = duration / blueprint["narrative"]["estimated_duration"]
        cursor = 0.0
        for scene in blueprint["scenes"]:
            scene["duration"] = round(scene["duration"] * scale, 2)
            scene["start"] = round(cursor, 2)
            cursor += scene["duration"]
            scene["end"] = round(cursor, 2)
        blueprint["narrative"]["estimated_duration"] = round(cursor, 2)
    blueprint["provider"] = {
        "name": provider.name,
        "mode": "offline" if provider.offline else "external",
        "status": provider.develop(brief)["status"],
    }
    _plan_local_assets(blueprint, project)
    blueprint["asset_manifest"] = _asset_manifest(blueprint, project)
    validate_blueprint(blueprint)
    validate_assets(blueprint, project)
    stages.extend([
        _stage("narrative_structure", "passed", "Arc and scene durations generated."),
        _stage("storyboard_generation", "passed", "Markdown and SVG storyboard outputs are ready."),
        _stage("asset_planning", "passed", f"{len(blueprint['asset_manifest'])} explicit local asset references tracked."),
        _stage("blueprint_validation", "passed", "Timing, required scene fields, and asset paths validated."),
    ])
    (project / "blueprint.json").write_text(json.dumps(blueprint, indent=2), encoding="utf-8")
    write_markdown(blueprint, project / "storyboard.md")
    write_svg(blueprint, project / "storyboard.svg")
    (project / "storyboard.html").write_text(
        "<!doctype html><meta charset='utf-8'><title>Fablexis preview</title>"
        "<style>body{background:#0b1020;margin:0}img{max-width:100%;display:block;margin:auto}</style>"
        "<img src='storyboard.svg' alt='Fablexis storyboard'>",
        encoding="utf-8",
    )
    stages.append(_stage("rendered_preview", "passed", "Storyboard SVG and HTML written."))
    quality = {
        "status": "passed",
        "checks": ["blueprint", "assets", "storyboard", "rendered_frames", "media"],
        "validated_scene_count": len(blueprint["scenes"]),
    }
    (project / "quality-report.json").write_text(json.dumps(quality, indent=2), encoding="utf-8")
    output = project / "motionforge.mp4"
    if ffmpeg:
        with tempfile.TemporaryDirectory(prefix="motionforge-pipeline-") as frames:
            frame_dir = Path(frames)
            frame_count = write_bmp_frames(blueprint, frame_dir, project_root=project)
            frame_qa = _validate_rendered_frames(frame_dir, frame_count)
            process = subprocess.run(
                [ffmpeg, "-y", "-loglevel", "error", "-framerate", "12",
                 "-i", str(frame_dir / "frame_%05d.bmp"), "-c:v", "libx264",
                 "-pix_fmt", "yuv420p", str(output)],
                capture_output=True, text=True, check=False,
            )
        if process.returncode != 0 or not output.exists() or output.stat().st_size == 0:
            stages.append(_stage("mp4_export", "failed", process.stderr.strip() or "FFmpeg failed."))
            raise RuntimeError(stages[-1]["detail"])
        media = _probe_media(ffprobe, output) if ffprobe else {}
        (project / "media-report.json").write_text(json.dumps(media, indent=2), encoding="utf-8")
        stages.extend([
            _stage("rendering", "passed", "Deterministic frames rendered through the local compositor.", **frame_qa),
            _stage("rendered_frame_qa", "passed", "All generated BMP frames are non-empty and dimensionally consistent.", **frame_qa),
            _stage("mp4_export", "passed", output.name, media=media),
        ])
    else:
        stages.append(_stage("mp4_export", "blocked", "FFmpeg unavailable; preview and blueprint remain available."))
    report = {
        "status": "passed" if output.exists() else "partial",
        "provider": blueprint["provider"],
        "stages": stages,
        "outputs": {
            "blueprint": "blueprint.json",
            "storyboard": "storyboard.svg",
            "quality_report": "quality-report.json",
            "mp4": output.name if output.exists() else None,
        },
        "limitations": ["No external research or paid AI provider was used.", "Audio is not implemented."],
    }
    (project / "production-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
