"""Versioned, validated multi-track editing-plan contract."""

from __future__ import annotations

import math
from typing import Any


TIMELINE_SCHEMA_VERSION = "1.0"


class TimelineValidationError(ValueError):
    """Raised when an editing timeline is structurally or temporally invalid."""


def validate_timeline(timeline: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(timeline, dict):
        raise TimelineValidationError("Timeline must be a JSON object.")
    _reject_unknown(
        timeline,
        {
            "schema_version",
            "project",
            "reference_style",
            "tracks",
            "provenance",
            "unresolved_requirements",
        },
        "timeline",
    )
    if timeline.get("schema_version") != TIMELINE_SCHEMA_VERSION:
        raise TimelineValidationError("Unsupported timeline schema version.")
    project = timeline.get("project")
    if not isinstance(project, dict):
        raise TimelineValidationError("Timeline project metadata is required.")
    _reject_unknown(
        project,
        {"frame_rate", "width", "height", "duration_seconds", "aspect_ratio", "audio_policy"},
        "project",
    )
    aspect_ratio = project.get("aspect_ratio")
    if not isinstance(aspect_ratio, str) or not aspect_ratio:
        raise TimelineValidationError("Project aspect_ratio must be a non-empty string.")
    for key in ("frame_rate", "duration_seconds"):
        value = project.get(key)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not _is_finite_number(value)
            or value <= 0
        ):
            raise TimelineValidationError(f"Project {key} must be positive.")
    for key in ("width", "height"):
        value = project.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise TimelineValidationError(f"Project {key} must be a positive integer.")
        if value % 2:
            raise TimelineValidationError(
                f"Project {key} must be even for H.264 yuv420p output."
            )
    if (
        "audio_policy" in project
        and project["audio_policy"] != "preserve_source_audio_if_present"
    ):
        raise TimelineValidationError(
            f"Unsupported project audio policy: {project['audio_policy']}"
        )
    tracks = timeline.get("tracks")
    if not isinstance(tracks, list) or not tracks:
        raise TimelineValidationError("Timeline must contain at least one track.")
    seen_tracks: set[str] = set()
    for track in tracks:
        if (
            not isinstance(track, dict)
            or not isinstance(track.get("id"), str)
            or not track["id"]
            or not isinstance(track.get("type"), str)
            or not track["type"]
        ):
            raise TimelineValidationError("Every track needs an id and type.")
        _reject_unknown(track, {"id", "type", "clips"}, f"track {track.get('id', '<unknown>')}")
        if track["id"] in seen_tracks:
            raise TimelineValidationError(f"Duplicate track id: {track['id']}")
        seen_tracks.add(track["id"])
        if track["type"] not in {"video", "audio", "overlay", "caption"}:
            raise TimelineValidationError(f"Unsupported track type: {track['type']}")
        clips = track.get("clips")
        if not isinstance(clips, list):
            raise TimelineValidationError(f"Track {track['id']} must contain a clips array.")
        validated_clips = []
        for clip in clips:
            _validate_clip(clip, project["duration_seconds"], track["type"])
            validated_clips.append(clip)
        previous_end = 0.0
        for clip in sorted(validated_clips, key=lambda item: item["timeline_start_seconds"]):
            if clip["timeline_start_seconds"] < previous_end:
                raise TimelineValidationError(
                    f"Overlapping clips are not supported on track {track['id']}."
                )
            previous_end = clip["timeline_end_seconds"]
    provenance = timeline.get("provenance")
    if not isinstance(provenance, dict):
        raise TimelineValidationError("Timeline provenance metadata is required.")
    if not isinstance(provenance.get("engine"), str) or not provenance["engine"]:
        raise TimelineValidationError("Timeline provenance needs an engine name.")
    if not isinstance(provenance.get("timeline_renderer"), str) or not provenance["timeline_renderer"]:
        raise TimelineValidationError("Timeline provenance needs a timeline_renderer name.")
    if "unresolved_requirements" in timeline and (
        not isinstance(timeline["unresolved_requirements"], list)
        or not all(isinstance(item, str) for item in timeline["unresolved_requirements"])
    ):
        raise TimelineValidationError("unresolved_requirements must be an array of strings.")
    return timeline


def _validate_clip(clip: dict[str, Any], total_duration: float, track_type: str) -> None:
    required = ("id", "timeline_start_seconds", "timeline_end_seconds")
    if (
        not isinstance(clip, dict)
        or any(key not in clip for key in required)
        or not isinstance(clip.get("id"), str)
        or not clip["id"]
    ):
        raise TimelineValidationError("Every timeline clip needs an id and timeline bounds.")
    _reject_unknown(
        clip,
        {
            "id",
            "timeline_start_seconds",
            "timeline_end_seconds",
            "transition_in",
            "mute",
            "source",
            "selection",
        },
        f"clip {clip['id']}",
    )
    start = clip["timeline_start_seconds"]
    end = clip["timeline_end_seconds"]
    if (
        isinstance(start, bool)
        or isinstance(end, bool)
        or not isinstance(start, (int, float))
        or not isinstance(end, (int, float))
        or not _is_finite_number(start)
        or not _is_finite_number(end)
        or end <= start
    ):
        raise TimelineValidationError(f"Invalid timing for clip {clip.get('id', '<unknown>')}.")
    if start < 0 or end > total_duration:
        raise TimelineValidationError(f"Clip {clip['id']} exceeds project duration.")
    if track_type in {"video", "audio"}:
        source = clip.get("source")
        if (
            not isinstance(source, dict)
            or not isinstance(source.get("path"), str)
            or not source["path"]
        ):
            raise TimelineValidationError(f"Media clip {clip['id']} needs a source path.")
        source_start = source.get("in_seconds")
        source_end = source.get("out_seconds")
        if (
            isinstance(source_start, bool)
            or isinstance(source_end, bool)
            or not isinstance(source_start, (int, float))
            or not isinstance(source_end, (int, float))
            or not _is_finite_number(source_start)
            or not _is_finite_number(source_end)
            or source_start < 0
            or source_end <= source_start
        ):
            raise TimelineValidationError(f"Invalid source trim for clip {clip['id']}.")
        _reject_unknown(
            source,
            {"path", "in_seconds", "out_seconds", "identity"},
            f"source for clip {clip['id']}",
        )
        if "identity" in source and source["identity"] is not None and not isinstance(
            source["identity"], str
        ):
            raise TimelineValidationError(f"Clip {clip['id']} source identity must be a string or null.")
    elif "source" in clip:
        raise TimelineValidationError(
            f"Source media is not supported on {track_type} clip {clip['id']}."
        )
    if "selection" in clip:
        selection = clip["selection"]
        if not isinstance(selection, dict):
            raise TimelineValidationError(f"Clip {clip['id']} selection must be an object.")
        _reject_unknown(selection, {"confidence", "reason"}, f"selection for clip {clip['id']}")
        confidence = selection.get("confidence")
        if confidence is not None and (
            isinstance(confidence, bool)
            or not isinstance(confidence, (int, float))
            or not _is_finite_number(confidence)
            or not 0 <= confidence <= 1
        ):
            raise TimelineValidationError(f"Clip {clip['id']} selection confidence must be between 0 and 1.")
        if "reason" in selection and not isinstance(selection["reason"], str):
            raise TimelineValidationError(f"Clip {clip['id']} selection reason must be a string.")
    if "mute" in clip and not isinstance(clip["mute"], bool):
        raise TimelineValidationError(f"Clip {clip['id']} mute must be a boolean.")
    if clip.get("transition_in", "cut") != "cut":
        raise TimelineValidationError(
            f"Unsupported transition on clip {clip['id']}; only hard cuts are supported."
        )


def _is_finite_number(value: int | float) -> bool:
    try:
        return math.isfinite(float(value))
    except (OverflowError, ValueError):
        return False


def _reject_unknown(value: dict[str, Any], allowed: set[str], location: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise TimelineValidationError(
            f"Unsupported field(s) in {location}: {', '.join(unknown)}."
        )


def build_edit_timeline(
    *,
    duration_seconds: float,
    frame_rate: float,
    width: int,
    height: int,
    clips: list[dict[str, Any]],
    reference_style: dict[str, Any],
    unresolved_requirements: list[str],
) -> dict[str, Any]:
    if duration_seconds <= 0 or frame_rate <= 0 or width <= 0 or height <= 0:
        raise TimelineValidationError("Timeline project dimensions and timing must be positive.")
    video_clips = []
    cursor = 0.0
    for index, clip in enumerate(clips, start=1):
        clip_duration = float(clip["duration_seconds"])
        end = min(duration_seconds, cursor + clip_duration)
        if end <= cursor:
            break
        video_clips.append(
            {
                "id": f"clip-{index:04d}",
                "timeline_start_seconds": round(cursor, 3),
                "timeline_end_seconds": round(end, 3),
                "source": {
                    "path": clip["path"],
                    "in_seconds": clip["start_seconds"],
                    "out_seconds": clip["start_seconds"] + (end - cursor),
                    "identity": clip.get("source_id"),
                },
                "selection": {
                    "confidence": clip.get("confidence", 0.0),
                    "reason": clip.get("reason", "Deterministic preliminary ranking; semantic relevance unverified."),
                },
                "transition_in": "cut" if index == 1 else "cut",
            }
        )
        cursor = end
    timeline = {
        "schema_version": TIMELINE_SCHEMA_VERSION,
        "project": {
            "frame_rate": frame_rate,
            "width": width,
            "height": height,
            "duration_seconds": duration_seconds,
            "aspect_ratio": f"{width}:{height}",
            "audio_policy": "preserve_source_audio_if_present",
        },
        "reference_style": reference_style,
        "tracks": [
            {"id": "video-main", "type": "video", "clips": video_clips},
            {"id": "audio-main", "type": "audio", "clips": []},
            {"id": "overlays", "type": "overlay", "clips": []},
            {"id": "captions", "type": "caption", "clips": []},
        ],
        "provenance": {
            "engine": "fablexis-deterministic-analysis",
            "timeline_renderer": "fablexis-ffmpeg",
        },
        "unresolved_requirements": unresolved_requirements,
    }
    return validate_timeline(timeline)
