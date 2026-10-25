"""Command-line interface for Fablexis, with a MotionForge compatibility alias."""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .blueprint_export import BlueprintExportError, export_blueprint
from .vox_motion import (
    build_blueprint,
    validate_blueprint,
    write_markdown,
    write_svg,
    validate_assets,
)
from .pipeline import run_pipeline
from .media_analysis import MediaAnalysisError, analyze_video
from .reference_analysis import analyze_footage, analyze_reference, build_edit_plan
from .timeline import TimelineValidationError, validate_timeline
from .timeline_renderer import TimelineRenderError, render_timeline, verify_mp4


def _positive_duration(value: str) -> float:
    try:
        duration = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("duration must be a number") from exc
    if not math.isfinite(duration) or duration <= 0:
        raise argparse.ArgumentTypeError("duration must be a finite positive number")
    return duration


def _project_blueprint(project: Path) -> Path:
    candidate = project / "blueprint.json"
    if not candidate.exists():
        raise SystemExit(f"Project blueprint not found: {candidate}")
    return candidate


def _write_json_atomically(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        prefix=f".{path.stem}.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    os.close(descriptor)
    temporary = Path(name)
    try:
        temporary.write_text(json.dumps(document, indent=2), encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _load_blueprint(project: Path) -> dict:
    try:
        blueprint = json.loads(_project_blueprint(project).read_text(encoding="utf-8"))
        validate_blueprint(blueprint)
        validate_assets(blueprint, project)
        return blueprint
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise SystemExit(f"Invalid Fablexis project '{project}': {exc}") from exc


def _write_project(input_path: Path, output: Path, mode: str, aspect_ratio: str) -> None:
    text = input_path.read_text(encoding="utf-8")
    blueprint = build_blueprint(text, mode=mode, aspect_ratio=aspect_ratio)
    output.mkdir(parents=True, exist_ok=True)
    (output / "blueprint.json").write_text(json.dumps(blueprint, indent=2), encoding="utf-8")
    write_markdown(blueprint, output / "storyboard.md")
    (output / "quality-report.json").write_text(
        json.dumps(blueprint["quality_control"], indent=2), encoding="utf-8"
    )
    print(f"Created {output / 'blueprint.json'}")


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(prog="fablexis")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Create a project with a starter brief")
    init.add_argument("project", type=Path)
    doctor = sub.add_parser("doctor", help="Check optional local rendering dependencies")
    brief = sub.add_parser("brief", help="Build a project from a natural-language brief")
    brief.add_argument("input", type=Path)
    brief.add_argument("--project", type=Path, default=Path("out"))
    brief.add_argument("--mode", choices=["quick", "director", "production"], default="production")
    brief.add_argument("--aspect-ratio", default="9:16")
    create = sub.add_parser("create", help="Run the complete offline-first idea-to-video pipeline")
    source = create.add_mutually_exclusive_group(required=True)
    source.add_argument("--idea")
    source.add_argument("--script", type=Path)
    create.add_argument("--project", type=Path, default=Path("out"))
    create.add_argument("--duration", type=_positive_duration)
    create.add_argument("--aspect-ratio", default="9:16")
    create.add_argument("--mode", choices=["quick", "director", "production"], default="production")
    plan = sub.add_parser("plan", help="Build a blueprint from a text or Markdown input")
    plan.add_argument("input", type=Path)
    plan.add_argument("--output", type=Path, default=Path("out"))
    plan.add_argument("--mode", choices=["quick", "director", "production"], default="production")
    plan.add_argument("--aspect-ratio", default="9:16")
    for name in ("storyboard", "preview", "qa", "export"):
        command = sub.add_parser(name, help=f"{name.capitalize()} a project")
        command.add_argument("project", type=Path)
    render = sub.add_parser("render", help="Render a blueprint storyboard preview")
    render.add_argument("blueprint", type=Path)
    render.add_argument("--output", type=Path, default=Path("out"))
    validate = sub.add_parser("validate", help="Validate a blueprint JSON file")
    validate.add_argument("blueprint", type=Path)
    analyze = sub.add_parser("analyze-video", help="Analyze local video metadata, frames, and estimated cuts")
    analyze.add_argument("input", type=Path)
    analyze.add_argument("--output", type=Path)
    analyze.add_argument("--interval", type=float, default=5.0)
    analyze.add_argument("--max-frames", type=int, default=24)
    analyze.add_argument("--thumbnail-width", type=int, default=320)
    analyze.add_argument("--thumbnail-height", type=int, default=180)
    analyze.add_argument("--scene-threshold", type=float, default=0.35)
    reference = sub.add_parser("analyze-reference", help="Analyze a reference video's measurable visual style")
    reference.add_argument("input", type=Path)
    reference.add_argument("--output", type=Path, default=Path("analysis/reference"))
    reference.add_argument("--interval", type=float, default=2.0)
    reference.add_argument("--max-frames", type=int, default=24)
    reference.add_argument("--scene-threshold", type=float, default=0.35)
    edit = sub.add_parser("edit-plan", help="Create an explainable reference-to-footage editing plan")
    edit.add_argument("--reference", type=Path, required=True)
    edit.add_argument("--footage", type=Path, nargs="+", required=True)
    edit.add_argument("--output", type=Path, default=Path("analysis/edit-plan"))
    edit.add_argument("--duration", type=float)
    edit.add_argument("--width", type=int)
    edit.add_argument("--height", type=int)
    render_timeline_command = sub.add_parser(
        "render-timeline", help="Render a validated multi-clip timeline to MP4"
    )
    render_timeline_command.add_argument("timeline", type=Path)
    render_timeline_command.add_argument(
        "--output", type=Path, required=True, help="Destination MP4 path"
    )
    render_timeline_command.add_argument(
        "--project-root", type=Path, help="Root directory allowed to contain source footage"
    )
    render_timeline_command.add_argument(
        "--crf", type=int, default=18, help="H.264 quality (0-51; lower is higher quality)"
    )
    render_timeline_command.add_argument(
        "--timeout", type=int, default=180, help="Per-process timeout in seconds"
    )
    validate_timeline_command = sub.add_parser(
        "validate-timeline", help="Validate a timeline JSON file or edit-plan wrapper"
    )
    validate_timeline_command.add_argument("timeline", type=Path)
    verify_output_command = sub.add_parser(
        "verify-output", help="Verify an MP4 with FFprobe and decode representative frames"
    )
    verify_output_command.add_argument("output", type=Path)
    verify_output_command.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    if args.command == "init":
        args.project.mkdir(parents=True, exist_ok=True)
        brief_path = args.project / "brief.md"
        if not brief_path.exists():
            brief_path.write_text(
                "# My Fablexis video\n\nDescribe the idea, audience, facts, and desired outcome here.\n",
                encoding="utf-8",
            )
        print(f"Initialized {args.project} with {brief_path}")
        return 0
    if args.command == "doctor":
        ffmpeg = shutil.which("ffmpeg")
        ffprobe = shutil.which("ffprobe")
        print("Python: available")
        if ffmpeg:
            version = subprocess.run([ffmpeg, "-version"], capture_output=True, text=True, check=False)
            print(f"FFmpeg: {ffmpeg} ({version.stdout.splitlines()[0] if version.stdout else 'version unavailable'})")
        else:
            print("FFmpeg: missing (MP4 export unavailable)")
        print(f"FFprobe: {ffprobe or 'missing (media verification unavailable)'}")
        print("Local SVG/HTML preview: available")
        return 0
    if args.command == "analyze-video":
        output = args.output or Path("analysis") / args.input.stem
        try:
            report = analyze_video(
                args.input,
                output,
                interval=args.interval,
                max_frames=args.max_frames,
                thumbnail_width=args.thumbnail_width,
                thumbnail_height=args.thumbnail_height,
                scene_threshold=args.scene_threshold,
                ffmpeg=shutil.which("ffmpeg"),
                ffprobe=shutil.which("ffprobe"),
            )
        except MediaAnalysisError as exc:
            raise SystemExit(f"Video analysis failed: {exc}") from exc
        print(f"Analyzed {args.input}")
        print(f"Report: {output / 'analysis-report.json'}")
        print(f"Frames: {len(report['artifacts']['frames'])}; shots: {len(report['shots'])}")
        return 0
    if args.command == "analyze-reference":
        try:
            report = analyze_reference(
                args.input,
                args.output,
                interval=args.interval,
                max_frames=args.max_frames,
                scene_threshold=args.scene_threshold,
                ffmpeg=shutil.which("ffmpeg"),
                ffprobe=shutil.which("ffprobe"),
            )
        except MediaAnalysisError as exc:
            raise SystemExit(f"Reference analysis failed: {exc}") from exc
        print(f"Reference report: {args.output / 'reference-style-report.json'}")
        print(f"Shots: {report['style']['pacing']['shot_count']}")
        return 0
    if args.command == "edit-plan":
        try:
            reference_dir = args.output / "reference"
            footage_dir = args.output / "footage"
            reference_report = analyze_reference(
                args.reference, reference_dir, ffmpeg=shutil.which("ffmpeg"), ffprobe=shutil.which("ffprobe")
            )
            footage_reports = analyze_footage(
                args.footage, footage_dir, ffmpeg=shutil.which("ffmpeg"), ffprobe=shutil.which("ffprobe")
            )
            plan = build_edit_plan(
                reference_report,
                footage_reports,
                target_duration=args.duration,
                width=args.width,
                height=args.height,
            )
            args.output.mkdir(parents=True, exist_ok=True)
            (args.output / "editing-plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
        except (MediaAnalysisError, ValueError, KeyError) as exc:
            raise SystemExit(f"Editing plan failed: {exc}") from exc
        print(f"Editing plan: {args.output / 'editing-plan.json'}")
        print(f"Selected clips: {len(plan['selected_clips'])}; alternatives: {len(plan['candidate_alternatives'])}")
        return 0
    if args.command in {"render-timeline", "validate-timeline"}:
        try:
            document = json.loads(args.timeline.read_text(encoding="utf-8-sig"))
            timeline = document
            if (
                isinstance(document, dict)
                and "project" not in document
                and "tracks" not in document
                and isinstance(document.get("timeline"), dict)
            ):
                timeline = document["timeline"]
            if args.command == "validate-timeline":
                validate_timeline(timeline)
                clip_count = sum(
                    len(track["clips"]) for track in timeline["tracks"]
                )
                print(
                    f"Valid timeline: {len(timeline['tracks'])} tracks, "
                    f"{clip_count} clips, {timeline['project']['duration_seconds']} seconds"
                )
                return 0
            if args.output.resolve() == args.timeline.resolve():
                raise TimelineRenderError(
                    "Output path must not overwrite the timeline JSON file."
                )
            media = render_timeline(
                timeline,
                args.output,
                project_root=args.project_root or args.timeline.parent,
                ffmpeg=shutil.which("ffmpeg"),
                ffprobe=shutil.which("ffprobe"),
                crf=args.crf,
                timeout=args.timeout,
            )
        except (OSError, json.JSONDecodeError, TimelineRenderError) as exc:
            raise SystemExit(f"Timeline render failed: {exc}") from exc
        except TimelineValidationError as exc:
            raise SystemExit(f"Timeline validation failed: {exc}") from exc
        quality_report = {
            "schema_version": "1.0",
            "status": media["quality"]["status"],
            "output": args.output.name,
            "project": {
                key: timeline["project"][key]
                for key in ("width", "height", "frame_rate", "duration_seconds")
            },
            "media": media,
        }
        report_path = args.output.with_name(f"{args.output.stem}.quality-report.json")
        _write_json_atomically(report_path, quality_report)
        print(f"Rendered timeline: {args.output}")
        print(f"Quality report: {report_path}")
        print(f"Media: {json.dumps(media, sort_keys=True)}")
        return 0
    if args.command == "verify-output":
        try:
            media = verify_mp4(
                args.output,
                ffmpeg=shutil.which("ffmpeg"),
                ffprobe=shutil.which("ffprobe"),
                timeout=args.timeout,
            )
        except (OSError, TimelineRenderError) as exc:
            raise SystemExit(f"Output verification failed: {exc}") from exc
        print(json.dumps({"output": args.output.name, **media}, sort_keys=True))
        return 0
    if args.command == "brief":
        _write_project(args.input, args.project, args.mode, args.aspect_ratio)
        return 0
    if args.command == "create":
        text = args.idea if args.idea is not None else args.script.read_text(encoding="utf-8")
        report = run_pipeline(
            text,
            args.project,
            aspect_ratio=args.aspect_ratio,
            mode=args.mode,
            duration=args.duration,
            ffmpeg=shutil.which("ffmpeg"),
            ffprobe=shutil.which("ffprobe"),
        )
        print(f"Production {report['status']}: {args.project / 'production-report.json'}")
        return 1 if report["status"] == "failed" else 0
    if args.command == "plan":
        _write_project(args.input, args.output, args.mode, args.aspect_ratio)
        return 0
    if args.command in {"storyboard", "preview"}:
        blueprint = _load_blueprint(args.project)
        write_svg(blueprint, args.project / "storyboard.svg")
        (args.project / "storyboard.html").write_text(
            "<!doctype html><meta charset='utf-8'><title>Fablexis preview</title>"
            "<style>body{background:#0b1020;margin:0}img{max-width:100%;display:block;margin:auto}</style>"
            "<img src='storyboard.svg' alt='Storyboard preview'>",
            encoding="utf-8",
        )
        print(f"Preview written to {args.project}")
        return 0
    if args.command == "qa":
        blueprint = _load_blueprint(args.project)
        report = {
            "schema_version": "1.0",
            "scope": "blueprint and local asset validation",
            "status": "passed",
            "checks": {"blueprint": True, "assets": True},
            "validated_scene_count": len(blueprint["scenes"]),
            "limitations": ["Rendered video is not checked unless motionforge.mp4 exists."],
        }
        output = args.project / "motionforge.mp4"
        if output.is_file():
            ffprobe = shutil.which("ffprobe")
            ffmpeg = shutil.which("ffmpeg")
            if not ffprobe or not ffmpeg:
                report["status"] = "partial"
                report["checks"]["rendered_media"] = False
                report["failure"] = "FFmpeg and FFprobe are required to verify rendered media."
            else:
                try:
                    media = verify_mp4(output, ffmpeg=ffmpeg, ffprobe=ffprobe)
                    video = next(
                        stream for stream in media["streams"]
                        if stream.get("codec_type") == "video"
                    )
                    expected = blueprint["scenes"][0]["render"]
                    if (video["width"], video["height"]) != (
                        expected["width"], expected["height"]
                    ):
                        raise TimelineRenderError(
                            "Rendered dimensions do not match the blueprint."
                        )
                except TimelineRenderError as exc:
                    report["status"] = "failed"
                    report["checks"]["rendered_media"] = False
                    report["failure"] = str(exc)
                else:
                    report["checks"]["rendered_media"] = True
                    report["media"] = media
                    report["limitations"].append(
                        "Automated metadata and frame-decode checks do not replace visual review."
                    )
        else:
            report["status"] = "partial"
            report["checks"]["rendered_media"] = False
            report["failure"] = "No motionforge.mp4 exists; only blueprint and assets were checked."
        _write_json_atomically(args.project / "quality-report.json", report)
        print(f"Blueprint QA {report['status']} for {len(blueprint['scenes'])} scenes")
        return 1 if report["status"] == "failed" else 0
    if args.command == "export":
        blueprint = _load_blueprint(args.project)
        output = args.project / "motionforge.mp4"
        ffmpeg = shutil.which("ffmpeg")
        ffprobe = shutil.which("ffprobe")
        try:
            media, frame_qa = export_blueprint(
                blueprint,
                args.project,
                output,
                ffmpeg=ffmpeg,
                ffprobe=ffprobe,
            )
        except BlueprintExportError as exc:
            raise SystemExit(f"MP4 export failed: {exc}") from exc
        media["frame_qa"] = frame_qa
        _write_json_atomically(args.project / "media-report.json", media)
        print(f"Exported {output}")
        return 0
    blueprint = json.loads(args.blueprint.read_text(encoding="utf-8"))
    validate_blueprint(blueprint)
    if args.command == "render":
        args.output.mkdir(parents=True, exist_ok=True)
        write_svg(blueprint, args.output / "storyboard.svg")
        (args.output / "storyboard.html").write_text(
            "<!doctype html><meta charset='utf-8'><title>Fablexis storyboard</title>"
            "<style>body{background:#0b1020;margin:0}img{max-width:100%;display:block;margin:auto}</style>"
            "<img src='storyboard.svg' alt='Storyboard preview'>", encoding="utf-8")
        print(f"Rendered {args.output / 'storyboard.svg'}")
    else:
        print(f"Valid blueprint: {len(blueprint['scenes'])} scenes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
