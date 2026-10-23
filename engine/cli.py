"""Command-line interface for Fablexis, with a MotionForge compatibility alias."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from .vox_motion import (
    build_blueprint,
    frame_dimensions,
    validate_blueprint,
    write_markdown,
    write_ppm_frames,
    write_bmp_frames,
    write_svg,
    validate_assets,
)
from .pipeline import run_pipeline


def _project_blueprint(project: Path) -> Path:
    candidate = project / "blueprint.json"
    if not candidate.exists():
        raise SystemExit(f"Project blueprint not found: {candidate}")
    return candidate


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
    create.add_argument("--duration", type=float)
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
        return 0
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
        report = blueprint.get("quality_control", {})
        report["status"] = "passed"
        report["validated_scene_count"] = len(blueprint["scenes"])
        (args.project / "quality-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"QA passed for {len(blueprint['scenes'])} scenes")
        return 0
    if args.command == "export":
        blueprint = _load_blueprint(args.project)
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise SystemExit(
                "FFmpeg is not installed or not on PATH. SVG/HTML preview is available; MP4 was not created."
            )
        output = args.project / "motionforge.mp4"
        with tempfile.TemporaryDirectory(prefix="motionforge-frames-") as frames:
            frame_dir = Path(frames)
            write_bmp_frames(blueprint, frame_dir, project_root=args.project)
            process = subprocess.run(
                [
                    ffmpeg,
                    "-y",
                    "-loglevel",
                    "error",
                    "-framerate",
                    "12",
                    "-i",
                    str(frame_dir / "frame_%05d.bmp"),
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    str(output),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        if process.returncode != 0 or not output.exists() or output.stat().st_size == 0:
            detail = process.stderr.strip() or "FFmpeg returned no diagnostic."
            raise SystemExit(f"MP4 export failed: {detail}")
        ffprobe = shutil.which("ffprobe")
        if ffprobe:
            probe = subprocess.run(
                [ffprobe, "-v", "error", "-show_entries", "format=duration:stream=width,height,r_frame_rate,codec_type",
                 "-of", "json", str(output)],
                capture_output=True, text=True, check=False,
            )
            if probe.returncode != 0:
                raise SystemExit(f"MP4 verification failed: {probe.stderr.strip() or 'ffprobe returned an error.'}")
            media = json.loads(probe.stdout)
            media["audio_present"] = any(
                stream.get("codec_type") == "audio"
                for stream in media.get("streams", [])
            )
            (args.project / "media-report.json").write_text(json.dumps(media, indent=2), encoding="utf-8")
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
