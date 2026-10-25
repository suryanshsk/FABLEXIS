"""Explainable reference-style and source-footage analysis."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageStat

from .media_analysis import MediaAnalysisError, analyze_video
from .timeline import build_edit_timeline


REFERENCE_REPORT_VERSION = "1.0"


def _frame_features(output_dir: Path, paths: list[str]) -> dict[str, Any]:
    brightness: list[float] = []
    contrast: list[float] = []
    saturation: list[float] = []
    changes: list[float] = []
    previous: Image.Image | None = None
    for relative in paths:
        image = Image.open(output_dir / relative).convert("RGB")
        stat = ImageStat.Stat(image)
        brightness.append(round(sum(stat.mean) / 3 / 255, 4))
        contrast.append(round(sum(stat.stddev) / 3 / 255, 4))
        hsv = image.convert("HSV")
        saturation.append(round(ImageStat.Stat(hsv).mean[1] / 255, 4))
        if previous is not None:
            current = image.resize(previous.size)
            difference = sum(
                abs(a - b)
                for a, b in zip(previous.tobytes(), current.tobytes())
            ) / (len(previous.tobytes()) * 255)
            changes.append(round(difference, 4))
        previous = image
    return {
        "brightness_mean": round(sum(brightness) / len(brightness), 4) if brightness else None,
        "contrast_mean": round(sum(contrast) / len(contrast), 4) if contrast else None,
        "saturation_mean": round(sum(saturation) / len(saturation), 4) if saturation else None,
        "visual_change_mean": round(sum(changes) / len(changes), 4) if changes else 0.0,
        "visual_change_max": round(max(changes), 4) if changes else 0.0,
        "methodology": "Mean RGB/HSV statistics and normalized pixel differences between sampled thumbnails.",
        "confidence": "measured_from_samples",
    }


def _graphic_region_estimate(output_dir: Path, paths: list[str]) -> dict[str, Any]:
    counts = {"top": 0, "middle": 0, "bottom": 0}
    for relative in paths:
        image = Image.open(output_dir / relative).convert("L")
        width, height = image.size
        bands = {
            "top": image.crop((0, 0, width, height // 3)),
            "middle": image.crop((0, height // 3, width, (height * 2) // 3)),
            "bottom": image.crop((0, (height * 2) // 3, width, height)),
        }
        for name, band in bands.items():
            values = list(band.getdata())
            if values and (max(values) - min(values) > 100):
                counts[name] += 1
    detected = [name for name, count in counts.items() if count >= max(1, len(paths) // 3)]
    return {
        "possible_regions": detected,
        "methodology": "Band-level luminance range heuristic; text and graphic identity are not recognized.",
        "confidence": "low_heuristic",
        "limitations": "Cannot distinguish typography, graphics, faces, or objects.",
    }


def analyze_reference(
    reference: Path,
    output_dir: Path,
    *,
    interval: float = 2.0,
    max_frames: int = 24,
    scene_threshold: float = 0.35,
    ffmpeg: str | None = None,
    ffprobe: str | None = None,
) -> dict[str, Any]:
    report = analyze_video(
        reference,
        output_dir,
        interval=interval,
        max_frames=max_frames,
        scene_threshold=scene_threshold,
        ffmpeg=ffmpeg,
        ffprobe=ffprobe,
    )
    features = _frame_features(output_dir, report["artifacts"]["frames"])
    duration = report["media"]["format"]["duration_seconds"]
    shots = report["shots"]
    shot_durations = [shot["duration_seconds"] for shot in shots]
    video = report["media"]["video"]
    aspect = (
        round(video["width"] / video["height"], 4)
        if video.get("width") and video.get("height")
        else None
    )
    style = {
        "framing": {
            "width": video.get("width"),
            "height": video.get("height"),
            "aspect_ratio": aspect,
            "orientation": (
                "portrait" if aspect and aspect < 1
                else "landscape" if aspect and aspect > 1
                else "square" if aspect else "unknown"
            ),
            "methodology": "Measured from FFprobe video dimensions.",
            "confidence": "measured",
        },
        "pacing": {
            "shot_count": len(shots),
            "mean_shot_duration_seconds": round(sum(shot_durations) / len(shot_durations), 3) if shots else None,
            "median_shot_duration_seconds": round(sorted(shot_durations)[len(shot_durations) // 2], 3) if shots else None,
            "cuts_per_minute": round(max(0, len(shots) - 1) / duration * 60, 3) if duration else None,
            "opening_hook_duration_seconds": round(min(shot_durations[0], 3.0), 3) if shot_durations else None,
            "methodology": "Estimated visual-cut shot index from FFmpeg scene detection.",
            "confidence": "estimated_visual_boundaries",
        },
        "image_characteristics": features,
        "graphic_regions": _graphic_region_estimate(output_dir, report["artifacts"]["frames"]),
        "transitions": {
            "classification": "hard_cut_only",
            "methodology": "Scene detector reports visual changes; transition type is not identified.",
            "confidence": "low",
            "limitations": "Dissolves, wipes, motion transitions, and narrative rhythm are not classified.",
        },
        "structure": {
            "duration_seconds": duration,
            "rhythm": "fast" if len(shots) and duration / len(shots) < 2 else "measured",
            "methodology": "Derived only from measured duration and estimated shot count.",
            "confidence": "estimated",
        },
    }
    result = {
        "schema_version": REFERENCE_REPORT_VERSION,
        "report_type": "reference_style",
        "source": report["source"],
        "media": report["media"],
        "analysis_settings": report["settings"],
        "style": style,
        "source_analysis": {
            "shot_boundaries_seconds": report["scene_boundaries_seconds"],
            "shots": report["shots"],
        },
        "artifacts": report["artifacts"],
        "warnings": report["warnings"],
    }
    (output_dir / "reference-style-report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def analyze_footage(
    footage: list[Path],
    output_dir: Path,
    *,
    interval: float = 2.0,
    max_frames: int = 12,
    ffmpeg: str | None = None,
    ffprobe: str | None = None,
) -> list[dict[str, Any]]:
    results = []
    for index, source in enumerate(footage, start=1):
        current = output_dir / f"source-{index:03d}"
        report = analyze_video(
            source,
            current,
            interval=interval,
            max_frames=max_frames,
            ffmpeg=ffmpeg,
            ffprobe=ffprobe,
        )
        features = _frame_features(current, report["artifacts"]["frames"])
        results.append({
            "source": {
                **report["source"],
                "absolute_path": str(source.expanduser().resolve()),
            },
            "media": report["media"],
            "features": features,
            "shots": report["shots"],
            "artifacts": report["artifacts"],
        })
    return results


def build_edit_plan(
    reference_report: dict[str, Any],
    footage_reports: list[dict[str, Any]],
    *,
    target_duration: float | None = None,
    width: int | None = None,
    height: int | None = None,
) -> dict[str, Any]:
    target_duration = target_duration or reference_report["media"]["format"]["duration_seconds"]
    reference_video = reference_report["media"]["video"]
    width = width or reference_video["width"]
    height = height or reference_video["height"]
    target_style = reference_report["style"]
    target_brightness = target_style["image_characteristics"]["brightness_mean"] or 0.5
    candidates = []
    for source in footage_reports:
        brightness = source["features"]["brightness_mean"] or 0.5
        for shot in source["shots"]:
            score = max(0.0, 1.0 - abs(brightness - target_brightness))
            candidates.append({
                "path": source["source"].get(
                    "absolute_path", source["source"]["path"]
                ),
                "source_id": source["source"]["sha256"][:16],
                **shot,
                "confidence": round(score * 0.5, 3),
                "reason": "Preliminary brightness similarity only; semantic relevance is unavailable.",
            })
    candidates.sort(key=lambda item: (-item["confidence"], item["path"], item["id"]))
    selected = candidates[: max(1, min(len(candidates), math.ceil(target_duration / 3)))] if candidates else []
    unresolved = [
        "Semantic subject and narrative relevance require human or vision-model review.",
        "Overlay/caption compositing and transitions are not supported by the current renderer.",
    ]
    timeline = build_edit_timeline(
        duration_seconds=target_duration,
        frame_rate=reference_video.get("average_frame_rate") or 24,
        width=width,
        height=height,
        clips=selected,
        reference_style=target_style,
        unresolved_requirements=unresolved,
    )
    return {
        "schema_version": "1.0",
        "report_type": "editing_plan",
        "reference_style": target_style,
        "target": {"duration_seconds": target_duration, "width": width, "height": height},
        "selected_clips": selected,
        "candidate_alternatives": candidates[len(selected):],
        "assumptions": [
            "Candidates are ranked by deterministic brightness similarity, not semantic meaning.",
            "Timeline sources retain their absolute local paths; project-root must contain all footage.",
        ],
        "confidence": "low_preliminary_ranking",
        "unresolved_requirements": unresolved,
        "timeline": timeline,
    }
