"""FFmpeg renderer for validated Fablexis multi-clip timelines."""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import tempfile
from fractions import Fraction
from pathlib import Path
from typing import Any

from PIL import Image, ImageStat

from .media_analysis import MediaAnalysisError, probe_video
from .timeline import TimelineValidationError, validate_timeline


class TimelineRenderError(RuntimeError):
    """Raised when a timeline cannot be rendered into a verified MP4."""


def render_timeline(
    timeline: dict[str, Any],
    output: Path,
    *,
    project_root: Path | None = None,
    ffmpeg: str | None = None,
    ffprobe: str | None = None,
    timeout: int = 180,
    crf: int = 18,
) -> dict[str, Any]:
    """Render sequential video clips, preserving explicit gaps as black frames."""
    try:
        validate_timeline(timeline)
    except TimelineValidationError as exc:
        raise TimelineRenderError(f"Invalid timeline: {exc}") from exc
    if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
        raise TimelineRenderError("Render timeout must be a positive integer.")
    if isinstance(crf, bool) or not isinstance(crf, int) or not 0 <= crf <= 51:
        raise TimelineRenderError("CRF must be an integer between 0 and 51.")
    executable = ffmpeg or shutil.which("ffmpeg")
    if not executable:
        raise TimelineRenderError("FFmpeg is not installed or not on PATH.")
    probe_executable = ffprobe or shutil.which("ffprobe")
    if not probe_executable:
        raise TimelineRenderError("FFprobe is not installed or not on PATH.")

    project = timeline["project"]
    video_tracks = [track for track in timeline["tracks"] if track["type"] == "video"]
    if len(video_tracks) != 1 or not video_tracks[0]["clips"]:
        raise TimelineRenderError("Timeline must contain exactly one non-empty video track.")
    for track in timeline["tracks"]:
        if track["type"] == "audio" and track["clips"]:
            raise TimelineRenderError(
                "Standalone audio tracks are not implemented; use source audio on video clips."
            )
        if track["type"] in {"overlay", "caption"} and track["clips"]:
            raise TimelineRenderError(
                f"Non-empty {track['type']} tracks are not composited by this renderer."
            )

    root = (project_root or Path.cwd()).expanduser().resolve()
    clips = sorted(
        video_tracks[0]["clips"],
        key=lambda clip: clip["timeline_start_seconds"],
    )
    inputs: list[dict[str, Any]] = []
    has_audio = False
    frame_tolerance = max(0.05, 0.5 / float(project["frame_rate"]))
    for clip in clips:
        if clip.get("transition_in", "cut") != "cut":
            raise TimelineRenderError(
                f"Unsupported transition on clip {clip['id']}; only hard cuts are supported."
            )
        source_path = _resolve_source(root, clip["source"]["path"])
        metadata = _probe(source_path, probe_executable, timeout=timeout)
        source_duration = metadata["format"]["duration_seconds"]
        source_start = float(clip["source"]["in_seconds"])
        source_end = float(clip["source"]["out_seconds"])
        timeline_duration = float(clip["timeline_end_seconds"]) - float(
            clip["timeline_start_seconds"]
        )
        if source_duration is None or source_end > source_duration + frame_tolerance:
            raise TimelineRenderError(
                f"Clip {clip['id']} source trim exceeds media duration: {source_path}"
            )
        if abs((source_end - source_start) - timeline_duration) > frame_tolerance:
            raise TimelineRenderError(
                f"Clip {clip['id']} source duration and timeline duration differ."
            )
        clip_audio = bool(metadata["audio"]) and not clip.get("mute", False)
        has_audio = has_audio or clip_audio
        inputs.append(
            {
                "clip": clip,
                "path": source_path,
                "audio": clip_audio,
            }
        )

    output = Path(output).expanduser()
    if output.suffix.lower() != ".mp4":
        raise TimelineRenderError("Timeline output path must use the .mp4 extension.")
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise TimelineRenderError(f"Could not create output directory: {exc}") from exc
    resolved_output = output.resolve()
    if any(resolved_output == item["path"] for item in inputs):
        raise TimelineRenderError("Output path must not overwrite source footage.")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.stem}.fablexis-",
        suffix=".mp4",
        dir=output.parent,
    )
    os.close(descriptor)
    temporary_output = Path(temporary_name)
    try:
        command = _build_command(
            executable,
            inputs,
            project,
            temporary_output,
            has_audio=has_audio,
            crf=crf,
        )
        try:
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout,
            )
        except FileNotFoundError as exc:
            raise TimelineRenderError("FFmpeg is not installed or not on PATH.") from exc
        except OSError as exc:
            raise TimelineRenderError(f"Could not start FFmpeg: {exc}") from exc
        if process.returncode != 0:
            detail = process.stderr.strip() or "FFmpeg returned no diagnostic."
            raise TimelineRenderError(
                f"FFmpeg could not encode the MP4 (check encoder support): {detail}"
            )
        if not temporary_output.exists() or temporary_output.stat().st_size == 0:
            raise TimelineRenderError("FFmpeg did not produce a non-empty output.")
        media = _probe_media(probe_executable, temporary_output, timeout=timeout)
        _verify_output(media, project, has_audio)
        visual_qa = _verify_representative_frames(
            executable,
            temporary_output,
            float(project["duration_seconds"]),
            float(project["frame_rate"]),
            output.parent,
            clips=clips,
            timeout=timeout,
        )
        media["quality"] = {
            "status": "passed",
            "checks": {
                "file_nonempty": True,
                "video_stream": True,
                "h264_codec": True,
                "dimensions": True,
                "frame_rate": True,
                "pixel_format": True,
                "duration": True,
                "audio_policy": True,
                "audio_video_sync": True,
                "representative_frames_decoded": True,
                "explicit_gaps_black": all(
                    sample["expected_black"] is not False
                    for sample in visual_qa
                    if sample["kind"] == "gap"
                ),
            },
            "visual_samples": visual_qa,
            "limitations": [
                "Representative frames were decoded and explicit gaps checked for black; semantic visual review was not performed."
            ],
        }
        temporary_output.replace(output)
        return media
    except subprocess.TimeoutExpired as exc:
        raise TimelineRenderError("FFmpeg timed out while rendering or verifying the timeline.") from exc
    finally:
        temporary_output.unlink(missing_ok=True)


def verify_mp4(
    output: Path,
    *,
    ffmpeg: str | None = None,
    ffprobe: str | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    """Verify an existing MP4 and decode representative frames."""
    output = Path(output).expanduser()
    if not output.exists() or not output.is_file() or output.stat().st_size == 0:
        raise TimelineRenderError(f"Output MP4 is missing or empty: {output.name}")
    executable = ffmpeg or shutil.which("ffmpeg")
    if not executable:
        raise TimelineRenderError("FFmpeg is not installed or not on PATH.")
    probe_executable = ffprobe or shutil.which("ffprobe")
    if not probe_executable:
        raise TimelineRenderError("FFprobe is not installed or not on PATH.")
    media = _probe_media(probe_executable, output, timeout=timeout)
    video = next(
        (stream for stream in media["streams"] if stream.get("codec_type") == "video"),
        None,
    )
    if video is None:
        raise TimelineRenderError("Output does not contain a video stream.")
    if (
        isinstance(video.get("width"), bool)
        or not isinstance(video.get("width"), int)
        or video["width"] <= 0
        or isinstance(video.get("height"), bool)
        or not isinstance(video.get("height"), int)
        or video["height"] <= 0
    ):
        raise TimelineRenderError("Output video dimensions are unavailable or invalid.")
    duration = _parse_positive(video.get("duration")) or _parse_positive(
        media.get("format", {}).get("duration")
    )
    frame_rate = _parse_rate(video.get("avg_frame_rate") or video.get("r_frame_rate"))
    if duration is None or frame_rate is None:
        raise TimelineRenderError("Output duration or frame rate is unavailable.")
    project = {
        "width": video.get("width"),
        "height": video.get("height"),
        "frame_rate": frame_rate,
        "duration_seconds": duration,
    }
    _verify_output(media, project, bool(media["audio_present"]))
    visual_qa = _verify_representative_frames(
        executable,
        output,
        duration,
        frame_rate,
        output.parent,
        timeout=timeout,
    )
    media["quality"] = {
        "status": "passed",
        "checks": {
            "file_nonempty": True,
            "video_stream": True,
            "h264_codec": True,
            "dimensions": True,
            "frame_rate": True,
            "pixel_format": True,
            "duration": True,
            "audio_codec_and_sync": True,
            "representative_frames_decoded": True,
        },
        "visual_samples": visual_qa,
        "limitations": [
            "The file was checked for metadata and frame decodability; semantic visual review was not performed."
        ],
    }
    return media


def _parse_positive(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) and parsed > 0 else None


def _resolve_source(root: Path, value: str) -> Path:
    candidate = Path(value).expanduser()
    resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise TimelineRenderError(
            f"Timeline source must remain inside the project root: {value}"
        ) from exc
    if not resolved.exists() or not resolved.is_file():
        raise TimelineRenderError(f"Timeline source does not exist: {value}")
    return resolved


def _probe(path: Path, ffprobe: str, *, timeout: int) -> dict[str, Any]:
    try:
        return probe_video(path, ffprobe=ffprobe, timeout=timeout)
    except MediaAnalysisError as exc:
        raise TimelineRenderError(f"Could not inspect source clip {path}: {exc}") from exc


def _build_command(
    ffmpeg: str,
    inputs: list[dict[str, Any]],
    project: dict[str, Any],
    output: Path,
    *,
    has_audio: bool,
    crf: int,
) -> list[str]:
    width = int(project["width"])
    height = int(project["height"])
    fps = float(project["frame_rate"])
    args = [ffmpeg, "-y", "-nostdin", "-hide_banner", "-loglevel", "error"]
    for item in inputs:
        args.extend(["-i", str(item["path"])])
    filters: list[str] = []
    video_labels: list[str] = []
    audio_labels: list[str] = []
    cursor = 0.0
    segment_index = 0
    for input_index, item in enumerate(inputs):
        clip = item["clip"]
        start = float(clip["timeline_start_seconds"])
        end = float(clip["timeline_end_seconds"])
        if start > cursor:
            gap = start - cursor
            filters.append(
                f"color=c=black:s={width}x{height}:r={fps:.6f}:d={gap:.6f},"
                f"format=yuv420p,setpts=PTS-STARTPTS[v{segment_index}]"
            )
            if has_audio:
                filters.append(
                    f"anullsrc=r=48000:cl=stereo,atrim=duration={gap:.6f},"
                    f"asetpts=PTS-STARTPTS[a{segment_index}]"
                )
                audio_labels.append(f"[a{segment_index}]")
            video_labels.append(f"[v{segment_index}]")
            segment_index += 1
        source = clip["source"]
        source_start = float(source["in_seconds"])
        source_end = float(source["out_seconds"])
        duration = source_end - source_start
        filters.append(
            f"[{input_index}:v]setpts=PTS-STARTPTS,"
            f"trim=start={source_start:.6f}:end={source_end:.6f},"
            f"setpts=PTS-STARTPTS,scale=w='trunc(iw*sar/2)*2':h=ih,"
            f"setsar=1,scale={width}:{height}:"
            f"force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"setsar=1,fps={fps:.6f},format=yuv420p[v{segment_index}]"
        )
        video_labels.append(f"[v{segment_index}]")
        if has_audio:
            if item["audio"]:
                filters.append(
                    f"[{input_index}:a]asetpts=PTS-STARTPTS,"
                    f"atrim=start={source_start:.6f}:end={source_end:.6f},"
                    f"asetpts=PTS-STARTPTS,"
                    f"aresample=48000,aformat=sample_rates=48000:"
                    f"channel_layouts=stereo,apad=whole_dur={duration:.6f},"
                    f"atrim=duration={duration:.6f}"
                    f"[a{segment_index}]"
                )
            else:
                filters.append(
                    f"anullsrc=r=48000:cl=stereo,atrim=duration={duration:.6f},"
                    f"asetpts=PTS-STARTPTS[a{segment_index}]"
                )
            audio_labels.append(f"[a{segment_index}]")
        cursor = end
        segment_index += 1
    total = float(project["duration_seconds"])
    if cursor < total:
        gap = total - cursor
        filters.append(
            f"color=c=black:s={width}x{height}:r={fps:.6f}:d={gap:.6f},"
            f"format=yuv420p,setpts=PTS-STARTPTS[v{segment_index}]"
        )
        video_labels.append(f"[v{segment_index}]")
        if has_audio:
            filters.append(
                f"anullsrc=r=48000:cl=stereo,atrim=duration={gap:.6f},"
                f"asetpts=PTS-STARTPTS[a{segment_index}]"
            )
            audio_labels.append(f"[a{segment_index}]")
    filters.append(
        "".join(video_labels) + f"concat=n={len(video_labels)}:v=1:a=0[vout]"
    )
    if has_audio:
        filters.append(
            "".join(audio_labels) + f"concat=n={len(audio_labels)}:v=0:a=1[aout]"
        )
    args.extend(["-filter_complex", ";".join(filters), "-map", "[vout]"])
    if has_audio:
        args.extend(["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"])
    args.extend(
        [
            "-t",
            f"{total:.6f}",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            str(crf),
            "-threads",
            "1",
            "-pix_fmt",
            "yuv420p",
            "-fps_mode",
            "cfr",
            "-movflags",
            "+faststart",
            "-f",
            "mp4",
            str(output),
        ]
    )
    return args


def _probe_media(ffprobe: str, output: Path, *, timeout: int) -> dict[str, Any]:
    try:
        process = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                (
                    "format=format_name,duration,size:"
                    "stream=codec_name,codec_type,width,height,r_frame_rate,"
                    "avg_frame_rate,pix_fmt,duration"
                ),
                "-of",
                "json",
                str(output),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise TimelineRenderError("FFprobe is not installed or not on PATH.") from exc
    except OSError as exc:
        raise TimelineRenderError(f"Could not start FFprobe: {exc}") from exc
    if process.returncode != 0:
        raise TimelineRenderError(
            f"Output verification failed: {process.stderr.strip() or 'FFprobe returned an error.'}"
        )
    try:
        media = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise TimelineRenderError("FFprobe returned invalid output metadata.") from exc
    if (
        not isinstance(media, dict)
        or not isinstance(media.get("streams"), list)
        or not all(isinstance(stream, dict) for stream in media["streams"])
    ):
        raise TimelineRenderError("FFprobe returned incomplete output metadata.")
    media["audio_present"] = any(
        stream.get("codec_type") == "audio" for stream in media["streams"]
    )
    return media


def _verify_output(media: dict[str, Any], project: dict[str, Any], has_audio: bool) -> None:
    streams = media.get("streams", [])
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    if video is None or video.get("codec_name") != "h264":
        raise TimelineRenderError("Output does not contain the required H.264 video stream.")
    if (video.get("width"), video.get("height")) != (
        int(project["width"]),
        int(project["height"]),
    ):
        raise TimelineRenderError("Output dimensions do not match the timeline.")
    if video.get("pix_fmt") != "yuv420p":
        raise TimelineRenderError("Output pixel format is not yuv420p.")
    expected_rate = float(project["frame_rate"])
    actual_rate = _parse_rate(video.get("avg_frame_rate") or video.get("r_frame_rate"))
    if actual_rate is None or not math.isclose(actual_rate, expected_rate, abs_tol=0.01):
        raise TimelineRenderError("Output frame rate does not match the timeline.")
    format_info = media.get("format", {})
    if not isinstance(format_info, dict) or "mp4" not in str(format_info.get("format_name", "")):
        raise TimelineRenderError("Output is not an MP4 container.")
    try:
        duration = float(format_info.get("duration", 0))
    except (TypeError, ValueError) as exc:
        raise TimelineRenderError("Output duration is missing or invalid.") from exc
    tolerance = max(0.15, 1 / expected_rate)
    if abs(duration - float(project["duration_seconds"])) > tolerance:
        raise TimelineRenderError("Output duration does not match the timeline.")
    audio_streams = [stream for stream in streams if stream.get("codec_type") == "audio"]
    if bool(audio_streams) != has_audio:
        raise TimelineRenderError("Output audio presence does not match the timeline policy.")
    if has_audio:
        audio = audio_streams[0]
        if audio.get("codec_name") != "aac":
            raise TimelineRenderError("Output audio is not encoded as AAC.")
        audio_duration = audio.get("duration")
        if audio_duration is None:
            raise TimelineRenderError("Output audio duration is unavailable for synchronization checks.")
        try:
            audio_duration_value = float(audio_duration)
        except (TypeError, ValueError) as exc:
            raise TimelineRenderError("Output audio duration is invalid.") from exc
        if abs(audio_duration_value - duration) > tolerance:
            raise TimelineRenderError("Output audio and video durations are not synchronized.")


def _parse_rate(value: str | None) -> float | None:
    try:
        return float(Fraction(value)) if value else None
    except (ValueError, ZeroDivisionError):
        return None


def _verify_representative_frames(
    ffmpeg: str,
    output: Path,
    duration: float,
    frame_rate: float,
    temp_root: Path,
    *,
    clips: list[dict[str, Any]] | None = None,
    timeout: int,
) -> list[dict[str, Any]]:
    timeline_samples: dict[float, str] = {
        0.0: "representative",
        duration / 2: "representative",
        max(0.0, duration - 1.5 / frame_rate): "representative",
    }
    if clips is not None:
        cursor = 0.0
        for clip in clips:
            start = float(clip["timeline_start_seconds"])
            end = float(clip["timeline_end_seconds"])
            if start > cursor:
                timeline_samples[(cursor + start) / 2] = "gap"
            timeline_samples[(start + end) / 2] = "clip"
            cursor = end
        if cursor < duration:
            timeline_samples[(cursor + duration) / 2] = "gap"
    samples = sorted(timeline_samples.items())
    try:
        with tempfile.TemporaryDirectory(prefix=".fablexis-frame-qa-", dir=temp_root) as temp_dir:
            results: list[dict[str, Any]] = []
            for index, (timestamp, kind) in enumerate(samples):
                frame = Path(temp_dir) / f"frame-{index}.png"
                process = subprocess.run(
                    [
                        ffmpeg,
                        "-y",
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-ss",
                        f"{timestamp:.6f}",
                        "-i",
                        str(output),
                        "-an",
                        "-frames:v",
                        "1",
                        str(frame),
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=timeout,
                )
                if process.returncode != 0 or not frame.is_file() or frame.stat().st_size == 0:
                    raise TimelineRenderError(
                        "Representative output frame could not be extracted: "
                        f"{process.stderr.strip() or 'FFmpeg produced no frame.'}"
                    )
                try:
                    with Image.open(frame) as image:
                        image.load()
                        rgb = image.convert("RGB")
                        mean_rgb = tuple(
                            round(channel_mean, 2)
                            for channel_mean in ImageStat.Stat(rgb).mean
                        )
                except (OSError, Image.DecompressionBombError) as exc:
                    raise TimelineRenderError(
                        "Representative output frame is unreadable."
                    ) from exc
                mean_luma = sum(mean_rgb) / 3
                expected_black = (
                    mean_luma <= 24 if kind == "gap" else None
                )
                if kind == "gap" and not expected_black:
                    raise TimelineRenderError(
                        f"Expected black gap at {timestamp:.3f}s is not black in the output."
                    )
                results.append(
                    {
                        "timestamp_seconds": round(timestamp, 3),
                        "kind": kind,
                        "readable": True,
                        "mean_rgb": mean_rgb,
                        "expected_black": expected_black,
                    }
                )
            return results
    except FileNotFoundError as exc:
        raise TimelineRenderError("FFmpeg is not installed or not on PATH.") from exc
    except OSError as exc:
        raise TimelineRenderError(f"Could not verify rendered frames: {exc}") from exc
