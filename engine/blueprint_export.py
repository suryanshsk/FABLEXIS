"""Verified, atomic MP4 export for deterministic blueprint frames."""

from __future__ import annotations

import math
import os
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .timeline_renderer import TimelineRenderError, verify_mp4
from .vox_motion import validate_assets, validate_blueprint, write_bmp_frames


BLUEPRINT_FRAME_RATE = 12


class BlueprintExportError(RuntimeError):
    """Raised when blueprint frames cannot be exported to a verified MP4."""


def export_blueprint(
    blueprint: dict[str, Any],
    project: Path,
    output: Path,
    *,
    ffmpeg: str | None = None,
    ffprobe: str | None = None,
    timeout: int = 180,
    crf: int = 18,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Render and verify a blueprint without damaging a previous successful export."""
    validate_blueprint(blueprint)
    project = Path(project).expanduser().resolve()
    validate_assets(blueprint, project)
    if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
        raise BlueprintExportError("Export timeout must be a positive integer.")
    if isinstance(crf, bool) or not isinstance(crf, int) or not 0 <= crf <= 51:
        raise BlueprintExportError("CRF must be an integer between 0 and 51.")
    ffmpeg = ffmpeg or shutil.which("ffmpeg")
    ffprobe = ffprobe or shutil.which("ffprobe")
    if not ffmpeg:
        raise BlueprintExportError("FFmpeg is not installed or not on PATH.")
    if not ffprobe:
        raise BlueprintExportError("FFprobe is not installed or not on PATH.")

    output = Path(output).expanduser()
    if output.suffix.lower() != ".mp4":
        raise BlueprintExportError("Blueprint export path must use the .mp4 extension.")
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise BlueprintExportError(f"Could not create output directory: {exc}") from exc
    output_resolved = output.resolve()
    protected_paths = _blueprint_asset_paths(blueprint, project)
    if output_resolved in protected_paths:
        raise BlueprintExportError("Output path must not overwrite a blueprint source asset.")

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.stem}.fablexis-",
        suffix=".mp4",
        dir=output.parent,
    )
    os.close(descriptor)
    temporary_output = Path(temporary_name)
    try:
        with tempfile.TemporaryDirectory(prefix="fablexis-blueprint-frames-") as frame_temp:
            frame_dir = Path(frame_temp)
            try:
                frame_count = write_bmp_frames(
                    blueprint,
                    frame_dir,
                    fps=BLUEPRINT_FRAME_RATE,
                    project_root=project,
                )
                frame_qa = _validate_frames(frame_dir, frame_count)
                process = subprocess.run(
                    [
                        ffmpeg,
                        "-y",
                        "-nostdin",
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-framerate",
                        str(BLUEPRINT_FRAME_RATE),
                        "-i",
                        str(frame_dir / "frame_%05d.bmp"),
                        "-frames:v",
                        str(frame_count),
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
                        str(temporary_output),
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=timeout,
                )
            except FileNotFoundError as exc:
                raise BlueprintExportError("FFmpeg is not installed or not on PATH.") from exc
            except subprocess.TimeoutExpired as exc:
                raise BlueprintExportError("FFmpeg timed out while exporting the blueprint.") from exc
            except OSError as exc:
                raise BlueprintExportError(f"Could not render blueprint frames: {exc}") from exc
            if process.returncode != 0:
                detail = process.stderr.strip() or "FFmpeg returned no diagnostic."
                raise BlueprintExportError(f"FFmpeg could not encode the MP4: {detail}")
        if not temporary_output.exists() or temporary_output.stat().st_size == 0:
            raise BlueprintExportError("FFmpeg did not produce a non-empty MP4.")
        try:
            media = verify_mp4(
                temporary_output,
                ffmpeg=ffmpeg,
                ffprobe=ffprobe,
                timeout=min(timeout, 60),
            )
        except TimelineRenderError as exc:
            raise BlueprintExportError(f"Export verification failed: {exc}") from exc
        video = next(
            stream for stream in media["streams"] if stream.get("codec_type") == "video"
        )
        expected_width = int(blueprint["scenes"][0]["render"]["width"])
        expected_height = int(blueprint["scenes"][0]["render"]["height"])
        expected_duration = frame_count / BLUEPRINT_FRAME_RATE
        if (video["width"], video["height"]) != (expected_width, expected_height):
            raise BlueprintExportError("Export dimensions do not match the blueprint.")
        actual_rate = _parse_rate(video.get("avg_frame_rate") or video.get("r_frame_rate"))
        if actual_rate is None or not math.isclose(
            actual_rate, BLUEPRINT_FRAME_RATE, abs_tol=0.01
        ):
            raise BlueprintExportError("Export frame rate does not match the blueprint.")
        actual_duration = float(media["format"]["duration"])
        if abs(actual_duration - expected_duration) > max(
            0.15, 1 / BLUEPRINT_FRAME_RATE
        ):
            raise BlueprintExportError("Export duration does not match the rendered frames.")
        if media["audio_present"]:
            raise BlueprintExportError("Blueprint export unexpectedly contains audio.")
        media["quality"]["checks"].update(
            {
                "blueprint_dimensions": True,
                "blueprint_frame_rate": True,
                "blueprint_duration": True,
                "silent_output_policy": True,
            }
        )
        media["quality"]["limitations"].append(
            "Frame decoding was checked; semantic visual review was not performed."
        )
        temporary_output.replace(output)
        return media, frame_qa
    finally:
        temporary_output.unlink(missing_ok=True)


def _validate_frames(frame_dir: Path, expected_count: int) -> dict[str, Any]:
    frames = sorted(frame_dir.glob("frame_*.bmp"))
    if expected_count <= 0 or len(frames) != expected_count:
        raise BlueprintExportError(
            f"Rendered frame count mismatch: expected {expected_count}, found {len(frames)}."
        )
    dimensions: tuple[int, int] | None = None
    for frame in frames:
        try:
            payload = frame.read_bytes()
        except OSError as exc:
            raise BlueprintExportError(f"Could not read rendered frame {frame.name}: {exc}") from exc
        if len(payload) <= 54 or payload[:2] != b"BM":
            raise BlueprintExportError(f"Invalid or empty rendered frame: {frame.name}")
        width, height = struct.unpack_from("<ii", payload, 18)
        current = (width, abs(height))
        if width <= 0 or height == 0 or width % 2 or abs(height) % 2:
            raise BlueprintExportError(f"Invalid H.264 frame dimensions in {frame.name}.")
        if dimensions is None:
            dimensions = current
        elif dimensions != current:
            raise BlueprintExportError(f"Inconsistent rendered frame dimensions in {frame.name}.")
    return {"frame_count": len(frames), "dimensions": dimensions}


def _blueprint_asset_paths(blueprint: dict[str, Any], project: Path) -> set[Path]:
    paths = set()
    for scene in blueprint["scenes"]:
        for asset in scene.get("assets", []):
            value = asset.get("path") if isinstance(asset, dict) else asset
            if isinstance(value, str):
                paths.add((project / value).resolve())
        for layer in scene.get("layers", []):
            if layer.get("type") == "asset" and isinstance(layer.get("asset"), str):
                paths.add((project / layer["asset"]).resolve())
    return paths


def _parse_rate(value: str | None) -> float | None:
    try:
        from fractions import Fraction

        return float(Fraction(value)) if value else None
    except (ValueError, ZeroDivisionError):
        return None
