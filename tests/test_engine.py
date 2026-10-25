import json
import shutil
import struct
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from PIL import Image

from engine.blueprint_export import BlueprintExportError, export_blueprint
from engine.cli import main
from engine.pipeline import OfflineCreativeProvider, run_pipeline
from engine.media_analysis import MediaAnalysisError, analyze_video, probe_video
from engine.reference_analysis import analyze_reference, analyze_footage, build_edit_plan
from engine.timeline import TimelineValidationError, validate_timeline
from engine.timeline_renderer import TimelineRenderError, render_timeline
from engine.vox_motion import (
    build_blueprint,
    frame_dimensions,
    validate_assets,
    validate_blueprint,
    write_bmp_frames,
    write_ppm_frames,
    write_svg,
)


class BlueprintTests(unittest.TestCase):
    def test_shared_agent_skill_and_claude_adapter_exist(self):
        root = Path(__file__).parents[1]
        shared = root / ".agents" / "skills" / "fablexis" / "SKILL.md"
        adapter = root / ".claude" / "skills" / "fablexis" / "SKILL.md"
        readme = (root / "README.md").read_text(encoding="utf-8")
        skill_text = shared.read_text(encoding="utf-8")
        self.assertTrue(shared.exists())
        self.assertTrue(adapter.exists())
        self.assertIn("name: fablexis", skill_text)
        self.assertIn(".agents/skills/fablexis/SKILL.md", adapter.read_text(encoding="utf-8"))
        self.assertIn("fablexis edit-plan", skill_text)
        self.assertIn("fablexis render-timeline", skill_text)
        self.assertIn("fablexis verify-output", skill_text)
        self.assertIn("gemini skills list", readme)
        self.assertIn("untrusted workspace", readme)
        self.assertIn("No model was installed", readme)

    @unittest.skipUnless(
        shutil.which("ffmpeg") and shutil.which("ffprobe"),
        "FFmpeg and FFprobe are required for media-analysis integration tests",
    )
    def test_analyzes_local_video_and_writes_relative_report(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "clip with spaces.mp4"
            output = root / "analysis"
            process = subprocess.run(
                [
                    shutil.which("ffmpeg"),
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=red:s=160x90:r=4:d=1",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=blue:s=160x90:r=4:d=1",
                    "-filter_complex",
                    "[0:v][1:v]concat=n=2:v=1:a=0,format=yuv420p",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    str(source),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(process.returncode, 0, process.stderr)
            metadata = probe_video(source)
            self.assertEqual(metadata["video"]["width"], 160)
            report = analyze_video(
                source,
                output,
                interval=0.5,
                max_frames=6,
                thumbnail_width=80,
                thumbnail_height=45,
                scene_threshold=0.2,
            )
            self.assertEqual(report["schema_version"], "1.0")
            self.assertEqual(len(report["artifacts"]["frames"]), 4)
            self.assertGreaterEqual(len(report["shots"]), 2)
            self.assertTrue(report["artifacts"]["contact_sheets"])
            self.assertTrue((output / "analysis-report.json").exists())
            self.assertTrue(all(not Path(path).is_absolute() for path in report["artifacts"]["frames"]))
            self.assertTrue(all((output / path).exists() for path in report["artifacts"]["frames"]))

    def test_media_analysis_reports_missing_ffprobe(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / "missing.mp4"
            source.write_bytes(b"not media")
            with self.assertRaises(MediaAnalysisError) as error:
                probe_video(source, ffprobe="missing-ffprobe")
            self.assertIn("FFprobe is not installed", str(error.exception))

    def test_timeline_validation_rejects_malformed_timing_and_dimensions(self):
        timeline = {
            "schema_version": "1.0",
            "project": {"frame_rate": 24, "width": 160, "height": 90, "duration_seconds": 2, "aspect_ratio": "16:9"},
            "tracks": [{"id": "video", "type": "video", "clips": [{
                "id": "one", "timeline_start_seconds": 0, "timeline_end_seconds": 1,
                "source": {"path": "clip.mp4", "in_seconds": 0, "out_seconds": 1},
            }]}],
            "provenance": {"engine": "test", "timeline_renderer": "fablexis-ffmpeg"},
        }
        self.assertIs(validate_timeline(timeline), timeline)
        invalid_trim = json.loads(json.dumps(timeline))
        invalid_trim["tracks"][0]["clips"][0]["source"]["out_seconds"] = float("nan")
        with self.assertRaises(TimelineValidationError):
            validate_timeline(invalid_trim)
        odd_width = json.loads(json.dumps(timeline))
        odd_width["project"]["width"] = 161
        with self.assertRaises(TimelineValidationError):
            validate_timeline(odd_width)
        unsorted = json.loads(json.dumps(timeline))
        unsorted["tracks"][0]["clips"].append({
            "id": "earlier", "timeline_start_seconds": 1, "timeline_end_seconds": 2,
            "source": {"path": "clip.mp4", "in_seconds": 1, "out_seconds": 2},
        })
        unsorted["tracks"][0]["clips"].reverse()
        self.assertIs(validate_timeline(unsorted), unsorted)
        unsupported_volume = json.loads(json.dumps(timeline))
        unsupported_volume["tracks"][0]["clips"][0]["volume"] = 0.5
        with self.assertRaisesRegex(TimelineValidationError, "Unsupported field"):
            validate_timeline(unsupported_volume)

    def test_timeline_renderer_cleans_temporary_output_after_encoder_failure(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.mp4").write_bytes(b"placeholder source")
            timeline = {
                "schema_version": "1.0",
                "project": {"frame_rate": 24, "width": 160, "height": 90, "duration_seconds": 1, "aspect_ratio": "16:9"},
                "tracks": [{"id": "video", "type": "video", "clips": [{
                    "id": "clip", "timeline_start_seconds": 0, "timeline_end_seconds": 1,
                    "source": {"path": "source.mp4", "in_seconds": 0, "out_seconds": 1},
                }]}],
                "provenance": {"engine": "test", "timeline_renderer": "fablexis-ffmpeg"},
            }
            probe_result = subprocess.CompletedProcess(
                args=["ffprobe"],
                returncode=0,
                stdout=json.dumps({
                    "format": {"duration": "1", "duration_seconds": 1},
                    "streams": [{
                        "index": 0,
                        "codec_type": "video",
                        "codec_name": "h264",
                        "width": 160,
                        "height": 90,
                        "avg_frame_rate": "24/1",
                        "r_frame_rate": "24/1",
                    }],
                }),
                stderr="",
            )
            encode_failure = subprocess.CompletedProcess(
                args=["ffmpeg"],
                returncode=1,
                stdout="",
                stderr="synthetic encoder failure",
            )
            output = root / "failed.mp4"
            with patch(
                "engine.timeline_renderer.subprocess.run",
                side_effect=[probe_result, encode_failure],
            ):
                with self.assertRaisesRegex(TimelineRenderError, "synthetic encoder failure"):
                    render_timeline(
                        timeline,
                        output,
                        project_root=root,
                        ffmpeg="fake-ffmpeg",
                        ffprobe="fake-ffprobe",
                    )
            self.assertFalse(output.exists())
            self.assertEqual(list(root.glob(".failed.fablexis-*")), [])

@unittest.skipUnless(
    shutil.which("ffmpeg") and shutil.which("ffprobe"),
    "FFmpeg and FFprobe are required for timeline-rendering integration tests",
)
class TimelineRendererIntegrationTests(unittest.TestCase):
    @unittest.skipUnless(
        shutil.which("ffmpeg") and shutil.which("ffprobe"),
        "FFmpeg and FFprobe are required for timeline-rendering integration tests",
    )
    def test_renders_ordered_clips_with_gap_and_normalizes_output(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for name, color in (("first clip.mp4", "red"), ("second.mp4", "blue")):
                path = root / name
                command = [
                        shutil.which("ffmpeg"), "-y", "-hide_banner", "-loglevel", "error",
                    ]
                if color == "red":
                    command.extend([
                        "-f", "lavfi", "-i", "color=c=yellow:s=320x180:r=8:d=0.5",
                        "-f", "lavfi", "-i", "color=c=red:s=320x180:r=8:d=1",
                        "-f", "lavfi", "-i", "color=c=green:s=320x180:r=8:d=0.5",
                        "-filter_complex",
                        "[0:v][1:v][2:v]concat=n=3:v=1:a=0,format=yuv420p",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path),
                    ])
                else:
                    command.extend([
                        "-f", "lavfi", "-i", f"color=c={color}:s=320x180:r=8:d=2",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path),
                    ])
                process = subprocess.run(command, capture_output=True, text=True, check=False)
                self.assertEqual(process.returncode, 0, process.stderr)
            timeline = {
                "schema_version": "1.0",
                "project": {
                    "frame_rate": 10, "width": 160, "height": 90,
                    "duration_seconds": 2.5, "aspect_ratio": "16:9",
                },
                "tracks": [{
                    "id": "video-main", "type": "video", "clips": [
                        {
                            "id": "second", "timeline_start_seconds": 1.5,
                            "timeline_end_seconds": 2.5,
                            "source": {"path": "second.mp4", "in_seconds": 0.5, "out_seconds": 1.5},
                        },
                        {
                            "id": "first", "timeline_start_seconds": 0,
                            "timeline_end_seconds": 1,
                            "source": {"path": "first clip.mp4", "in_seconds": 0.5, "out_seconds": 1.5},
                        },
                    ],
                }],
                "provenance": {"engine": "test", "timeline_renderer": "fablexis-ffmpeg"},
            }
            output = root / "rendered.mp4"
            media = render_timeline(timeline, output, project_root=root)
            self.assertTrue(output.exists())
            self.assertGreater(output.stat().st_size, 0)
            video = next(stream for stream in media["streams"] if stream["codec_type"] == "video")
            self.assertEqual(video["codec_name"], "h264")
            self.assertEqual((video["width"], video["height"]), (160, 90))
            self.assertEqual(video["avg_frame_rate"], "10/1")
            self.assertEqual(video["pix_fmt"], "yuv420p")
            self.assertAlmostEqual(float(media["format"]["duration"]), 2.5, places=1)
            for timestamp, expected in ((0.25, (253, 0, 0)), (1.25, (0, 0, 0)), (1.75, (0, 0, 254))):
                frame = root / f"frame-{timestamp}.png"
                process = subprocess.run(
                    [
                        shutil.which("ffmpeg"), "-y", "-hide_banner", "-loglevel", "error",
                        "-ss", str(timestamp), "-i", str(output), "-frames:v", "1", str(frame),
                    ],
                    capture_output=True, text=True, check=False,
                )
                self.assertEqual(process.returncode, 0, process.stderr)
                pixel = Image.open(frame).convert("RGB").getpixel((80, 45))
                self.assertTrue(
                    all(abs(pixel[index] - expected[index]) < 18 for index in range(3)),
                    (timestamp, pixel, expected),
                )

    @unittest.skipUnless(
        shutil.which("ffmpeg") and shutil.which("ffprobe"),
        "FFmpeg and FFprobe are required for timeline-rendering integration tests",
    )
    def test_render_timeline_cli_accepts_edit_plan_wrapper(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "clip.mp4"
            process = subprocess.run(
                [
                    shutil.which("ffmpeg"), "-y", "-hide_banner", "-loglevel", "error",
                    "-f", "lavfi", "-i", "color=c=red:s=160x90:r=8:d=1",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source),
                ],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(process.returncode, 0, process.stderr)
            document = {
                "schema_version": "1.0",
                "timeline": {
                    "schema_version": "1.0",
                    "project": {"frame_rate": 8, "width": 160, "height": 90, "duration_seconds": 1, "aspect_ratio": "16:9"},
                    "tracks": [{"id": "video", "type": "video", "clips": [{
                        "id": "clip", "timeline_start_seconds": 0, "timeline_end_seconds": 1,
                        "source": {"path": "clip.mp4", "in_seconds": 0, "out_seconds": 1},
                    }]}],
                    "provenance": {"engine": "test", "timeline_renderer": "fablexis-ffmpeg"},
                },
            }
            plan_path = root / "editing-plan.json"
            plan_path.write_text(json.dumps(document), encoding="utf-8")
            output = root / "rendered.mp4"
            with patch(
                "sys.argv",
                [
                    "fablexis", "render-timeline", str(plan_path),
                    "--project-root", str(root), "--output", str(output),
                ],
            ):
                self.assertEqual(main(), 0)
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 0)

    def test_cli_end_to_end_analysis_edit_plan_render_and_quality_report(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            repo = Path(__file__).parents[1]
            ffmpeg = shutil.which("ffmpeg")
            sources = (
                (root / "clip red.mp4", "red"),
                (root / "clip blue λ.mp4", "blue"),
            )
            for source, color in sources:
                process = subprocess.run(
                    [
                        ffmpeg, "-y", "-nostdin", "-hide_banner", "-loglevel", "error",
                        "-f", "lavfi", "-i", f"color=c={color}:s=160x90:r=8:d=2",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source),
                    ],
                    capture_output=True, text=True, check=False,
                )
                self.assertEqual(process.returncode, 0, process.stderr)
            reference = root / "reference.mp4"
            process = subprocess.run(
                [
                    ffmpeg, "-y", "-nostdin", "-hide_banner", "-loglevel", "error",
                    "-f", "lavfi", "-i", "color=c=white:s=160x90:r=8:d=4",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(reference),
                ],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(process.returncode, 0, process.stderr)

            def cli(*arguments: object) -> str:
                process = subprocess.run(
                    [sys.executable, "-m", "engine.cli", *(str(argument) for argument in arguments)],
                    cwd=repo,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(process.returncode, 0, process.stderr)
                return process.stdout

            for index, (source, _) in enumerate(sources, start=1):
                cli(
                    "analyze-video", source, "--output", root / f"analysis-{index}",
                    "--interval", "1", "--max-frames", "4",
                )
            cli(
                "analyze-reference", reference,
                "--output", root / "reference-analysis",
                "--interval", "1", "--max-frames", "4",
            )
            plan_dir = root / "edit plan"
            cli(
                "edit-plan", "--reference", reference,
                "--footage", *(source for source, _ in sources),
                "--duration", "4", "--output", plan_dir,
            )
            plan_path = plan_dir / "editing-plan.json"
            document = json.loads(plan_path.read_text(encoding="utf-8"))
            timeline = document["timeline"]
            self.assertEqual(len(timeline["tracks"][0]["clips"]), 2)
            cli("validate-timeline", plan_path)
            output = root / "final render.mp4"
            cli(
                "render-timeline", plan_path,
                "--project-root", root,
                "--output", output,
            )
            verified = json.loads(cli("verify-output", output))
            self.assertEqual(verified["quality"]["status"], "passed")
            quality_path = output.with_name("final render.quality-report.json")
            quality = json.loads(quality_path.read_text(encoding="utf-8"))
            self.assertEqual(quality["status"], "passed")
            self.assertEqual(quality["media"]["quality"]["status"], "passed")
            self.assertTrue(all(quality["media"]["quality"]["checks"].values()))
            self.assertNotIn(str(root), quality_path.read_text(encoding="utf-8"))

            for clip in sorted(
                timeline["tracks"][0]["clips"],
                key=lambda item: item["timeline_start_seconds"],
            ):
                timeline_time = (
                    clip["timeline_start_seconds"] + clip["timeline_end_seconds"]
                ) / 2
                source_time = (
                    clip["source"]["in_seconds"] + clip["source"]["out_seconds"]
                ) / 2
                output_frame = root / f"render-{clip['id']}.png"
                source_frame = root / f"source-{clip['id']}.png"
                for media_path, timestamp, frame_path in (
                    (output, timeline_time, output_frame),
                    (Path(clip["source"]["path"]), source_time, source_frame),
                ):
                    process = subprocess.run(
                        [
                            ffmpeg, "-y", "-nostdin", "-hide_banner", "-loglevel", "error",
                            "-ss", str(timestamp), "-i", str(media_path),
                            "-frames:v", "1", str(frame_path),
                        ],
                        capture_output=True, text=True, check=False,
                    )
                    self.assertEqual(process.returncode, 0, process.stderr)
                with Image.open(output_frame) as rendered, Image.open(source_frame) as original:
                    rendered_pixel = rendered.convert("RGB").getpixel((80, 45))
                    original_pixel = original.convert("RGB").getpixel((80, 45))
                self.assertTrue(
                    all(abs(rendered_pixel[channel] - original_pixel[channel]) < 20 for channel in range(3)),
                    (clip["id"], rendered_pixel, original_pixel),
                )

    @unittest.skipUnless(
        shutil.which("ffmpeg") and shutil.which("ffprobe"),
        "FFmpeg and FFprobe are required for timeline-rendering integration tests",
    )
    def test_timeline_renderer_supports_portrait_and_cleans_failed_output(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "portrait.mp4"
            process = subprocess.run(
                [
                    shutil.which("ffmpeg"), "-y", "-hide_banner", "-loglevel", "error",
                    "-f", "lavfi", "-i", "color=c=green:s=90x160:r=6:d=1",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source),
                ],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(process.returncode, 0, process.stderr)
            timeline = {
                "schema_version": "1.0",
                "project": {"frame_rate": 6, "width": 90, "height": 160, "duration_seconds": 1, "aspect_ratio": "9:16"},
                "tracks": [{"id": "video", "type": "video", "clips": [{
                    "id": "portrait", "timeline_start_seconds": 0, "timeline_end_seconds": 1,
                    "source": {"path": "portrait.mp4", "in_seconds": 0, "out_seconds": 1},
                }]}],
                "provenance": {"engine": "test", "timeline_renderer": "fablexis-ffmpeg"},
            }
            media = render_timeline(timeline, root / "portrait-output.mp4", project_root=root)
            self.assertEqual((media["streams"][0]["width"], media["streams"][0]["height"]), (90, 160))
            self.assertFalse(media["audio_present"])
            failed = root / "failed.mp4"
            with self.assertRaises(TimelineRenderError):
                render_timeline(timeline, failed, project_root=root, crf=99)
            self.assertFalse(failed.exists())
            self.assertFalse(list(root.glob(".failed.fablexis-*")))

    @unittest.skipUnless(
        shutil.which("ffmpeg") and shutil.which("ffprobe"),
        "FFmpeg and FFprobe are required for timeline-rendering integration tests",
    )
    def test_timeline_renderer_reports_missing_tools_and_bad_source_trim(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.mp4"
            process = subprocess.run(
                [
                    shutil.which("ffmpeg"), "-y", "-hide_banner", "-loglevel", "error",
                    "-f", "lavfi", "-i", "color=c=green:s=90x160:r=6:d=1",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source),
                ],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(process.returncode, 0, process.stderr)
            timeline = {
                "schema_version": "1.0",
                "project": {"frame_rate": 6, "width": 90, "height": 160, "duration_seconds": 1, "aspect_ratio": "9:16"},
                "tracks": [{"id": "video", "type": "video", "clips": [{
                    "id": "clip", "timeline_start_seconds": 0, "timeline_end_seconds": 1,
                    "source": {"path": "source.mp4", "in_seconds": 0, "out_seconds": 1},
                }]}],
                "provenance": {"engine": "test", "timeline_renderer": "fablexis-ffmpeg"},
            }
            with self.assertRaisesRegex(TimelineRenderError, "FFprobe is not installed"):
                render_timeline(
                    timeline, root / "missing-probe.mp4", project_root=root, ffprobe="missing-ffprobe"
                )
            with self.assertRaisesRegex(TimelineRenderError, "FFmpeg is not installed"):
                render_timeline(
                    timeline, root / "missing-ffmpeg.mp4", project_root=root, ffmpeg="missing-ffmpeg"
                )
            invalid_trim = json.loads(json.dumps(timeline))
            invalid_trim["tracks"][0]["clips"][0]["source"]["in_seconds"] = 0.5
            invalid_trim["tracks"][0]["clips"][0]["source"]["out_seconds"] = 1.5
            with self.assertRaisesRegex(TimelineRenderError, "trim exceeds media duration"):
                render_timeline(invalid_trim, root / "bad-trim.mp4", project_root=root)
            self.assertFalse((root / "missing-probe.mp4").exists())
            self.assertFalse((root / "missing-ffmpeg.mp4").exists())
            self.assertFalse((root / "bad-trim.mp4").exists())
            self.assertFalse(list(root.glob(".*.fablexis-*")))

    @unittest.skipUnless(
        shutil.which("ffmpeg") and shutil.which("ffprobe"),
        "FFmpeg and FFprobe are required for timeline audio integration tests",
    )
    def test_timeline_renderer_preserves_audio_and_supports_mute(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "with-audio.mp4"
            process = subprocess.run(
                [
                    shutil.which("ffmpeg"), "-y", "-hide_banner", "-loglevel", "error",
                    "-f", "lavfi", "-i", "color=c=orange:s=160x90:r=6:d=1",
                    "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=1",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
                    str(source),
                ],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(process.returncode, 0, process.stderr)
            def timeline(mute: bool) -> dict:
                return {
                    "schema_version": "1.0",
                    "project": {"frame_rate": 6, "width": 160, "height": 90, "duration_seconds": 1, "aspect_ratio": "16:9"},
                    "tracks": [{"id": "video", "type": "video", "clips": [{
                        "id": "audio-clip", "timeline_start_seconds": 0, "timeline_end_seconds": 1,
                        "source": {"path": "with-audio.mp4", "in_seconds": 0, "out_seconds": 1},
                        "mute": mute,
                    }]}],
                    "provenance": {"engine": "test", "timeline_renderer": "fablexis-ffmpeg"},
                }
            with_audio = render_timeline(timeline(False), root / "with-audio-output.mp4", project_root=root)
            muted = render_timeline(timeline(True), root / "muted-output.mp4", project_root=root)
            self.assertTrue(with_audio["audio_present"])
            self.assertFalse(muted["audio_present"])

    @unittest.skipUnless(
        shutil.which("ffmpeg") and shutil.which("ffprobe"),
        "FFmpeg and FFprobe are required for timeline audio integration tests",
    )
    def test_timeline_renderer_synchronizes_mixed_audio_and_silent_clips(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for name, inputs in (
                (
                    "with-audio.mp4",
                    ["-f", "lavfi", "-i", "color=c=red:s=160x90:r=8:d=1",
                     "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=0.5",
                     "-c:a", "aac"],
                ),
                (
                    "silent.mp4",
                    ["-f", "lavfi", "-i", "color=c=blue:s=160x90:r=8:d=1"],
                ),
            ):
                process = subprocess.run(
                    [
                        shutil.which("ffmpeg"), "-y", "-hide_banner", "-loglevel", "error",
                        *inputs, "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        str(root / name),
                    ],
                    capture_output=True, text=True, check=False,
                )
                self.assertEqual(process.returncode, 0, process.stderr)
            timeline = {
                "schema_version": "1.0",
                "project": {"frame_rate": 8, "width": 160, "height": 90, "duration_seconds": 2, "aspect_ratio": "16:9"},
                "tracks": [{"id": "video", "type": "video", "clips": [
                    {
                        "id": "sound", "timeline_start_seconds": 0, "timeline_end_seconds": 1,
                        "source": {"path": "with-audio.mp4", "in_seconds": 0, "out_seconds": 1},
                    },
                    {
                        "id": "silent", "timeline_start_seconds": 1, "timeline_end_seconds": 2,
                        "source": {"path": "silent.mp4", "in_seconds": 0, "out_seconds": 1},
                    },
                ]}],
                "provenance": {"engine": "test", "timeline_renderer": "fablexis-ffmpeg"},
            }
            output = root / "mixed-audio.mp4"
            media = render_timeline(timeline, output, project_root=root)
            self.assertTrue(media["audio_present"])
            audio = next(stream for stream in media["streams"] if stream["codec_type"] == "audio")
            self.assertEqual(audio["codec_name"], "aac")
            self.assertAlmostEqual(float(audio["duration"]), 2, delta=0.15)
            silent_audio = subprocess.run(
                [
                    shutil.which("ffmpeg"), "-hide_banner", "-loglevel", "error",
                    "-ss", "1.3", "-t", "0.4", "-i", str(output), "-vn",
                    "-ac", "1", "-ar", "8000", "-f", "s16le", "pipe:1",
                ],
                capture_output=True, check=False,
            )
            self.assertEqual(silent_audio.returncode, 0, silent_audio.stderr.decode(errors="replace"))
            samples = [
                int.from_bytes(silent_audio.stdout[index:index + 2], "little", signed=True)
                for index in range(0, len(silent_audio.stdout), 2)
            ]
            rms = (sum(sample * sample for sample in samples) / max(1, len(samples))) ** 0.5
            self.assertLess(rms, 200)

    def test_timeline_renderer_rejects_invalid_sources_overlaps_and_transitions(self):
        timeline = {
            "schema_version": "1.0",
            "project": {"frame_rate": 12, "width": 160, "height": 90, "duration_seconds": 2, "aspect_ratio": "16:9"},
            "tracks": [{"id": "video", "type": "video", "clips": [
                {
                    "id": "one", "timeline_start_seconds": 0, "timeline_end_seconds": 1,
                    "source": {"path": "missing.mp4", "in_seconds": 0, "out_seconds": 1},
                },
                {
                    "id": "two", "timeline_start_seconds": 0.5, "timeline_end_seconds": 2,
                    "source": {"path": "missing.mp4", "in_seconds": 0, "out_seconds": 1.5},
                },
            ]}],
            "provenance": {"engine": "test", "timeline_renderer": "fablexis-ffmpeg"},
        }
        with TemporaryDirectory() as directory:
            missing_source = json.loads(json.dumps(timeline))
            missing_source["tracks"][0]["clips"] = missing_source["tracks"][0]["clips"][:1]
            with self.assertRaisesRegex(TimelineRenderError, "source does not exist"):
                render_timeline(
                    missing_source,
                    Path(directory) / "missing-source.mp4",
                    project_root=Path(directory),
                )
            with self.assertRaises(TimelineRenderError):
                render_timeline(timeline, Path(directory) / "out.mp4", project_root=Path(directory))
        with self.assertRaises(TimelineValidationError):
            validate_timeline(timeline)

    @unittest.skipUnless(
        shutil.which("ffmpeg") and shutil.which("ffprobe"),
        "FFmpeg and FFprobe are required for timeline-rendering integration tests",
    )
    def test_timeline_renderer_rejects_unsupported_tracks_and_transitions(self):
        base = {
            "schema_version": "1.0",
            "project": {"frame_rate": 24, "width": 160, "height": 90, "duration_seconds": 1, "aspect_ratio": "16:9"},
            "tracks": [{
                "id": "video", "type": "video", "clips": [{
                    "id": "clip", "timeline_start_seconds": 0, "timeline_end_seconds": 1,
                    "source": {"path": "missing.mp4", "in_seconds": 0, "out_seconds": 1},
                }],
            }],
            "provenance": {"engine": "test", "timeline_renderer": "fablexis-ffmpeg"},
        }
        with TemporaryDirectory() as directory:
            root = Path(directory)
            transition = json.loads(json.dumps(base))
            transition["tracks"][0]["clips"][0]["transition_in"] = "fade"
            with self.assertRaisesRegex(TimelineRenderError, "only hard cuts"):
                render_timeline(transition, root / "transition.mp4", project_root=root)
            overlay = json.loads(json.dumps(base))
            overlay["tracks"].append({
                "id": "overlay", "type": "overlay", "clips": [{
                    "id": "overlay-clip", "timeline_start_seconds": 0, "timeline_end_seconds": 1,
                }],
            })
            with self.assertRaisesRegex(TimelineRenderError, "overlay tracks are not composited"):
                render_timeline(overlay, root / "overlay.mp4", project_root=root)
            audio = json.loads(json.dumps(base))
            audio["tracks"].append({
                "id": "audio", "type": "audio", "clips": [{
                    "id": "audio-clip",
                    "timeline_start_seconds": 0,
                    "timeline_end_seconds": 1,
                    "source": {"path": "sound.wav", "in_seconds": 0, "out_seconds": 1},
                }],
            })
            with self.assertRaisesRegex(TimelineRenderError, "Standalone audio tracks"):
                render_timeline(audio, root / "audio-track.mp4", project_root=root)

class EngineBehaviorTests(unittest.TestCase):
    @unittest.skipUnless(
        shutil.which("ffmpeg") and shutil.which("ffprobe"),
        "FFmpeg and FFprobe are required for reference-analysis integration tests",
    )
    def test_reference_analysis_and_edit_plan_are_reproducible(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / "reference portrait.mp4"
            footage = root / "footage unicode \u03bb.mp4"
            for target, size, colors in (
                (reference, "120x200", ("red", "blue")),
                (footage, "160x90", ("green", "yellow")),
            ):
                process = subprocess.run(
                    [
                        shutil.which("ffmpeg"), "-y",
                        "-f", "lavfi", "-i", f"color=c={colors[0]}:s={size}:r=4:d=1",
                        "-f", "lavfi", "-i", f"color=c={colors[1]}:s={size}:r=4:d=1",
                        "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0,format=yuv420p",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(target),
                    ],
                    capture_output=True, text=True, check=False,
                )
                self.assertEqual(process.returncode, 0, process.stderr)
            reference_report = analyze_reference(reference, root / "ref", interval=0.5, max_frames=4, scene_threshold=0.2)
            footage_report = analyze_footage([footage], root / "footage", interval=0.5, max_frames=4)
            plan = build_edit_plan(reference_report, footage_report, target_duration=2)
            self.assertEqual(reference_report["schema_version"], "1.0")
            self.assertEqual(reference_report["style"]["framing"]["orientation"], "portrait")
            self.assertTrue(plan["timeline"]["tracks"])
            self.assertEqual(plan["timeline"]["provenance"]["timeline_renderer"], "fablexis-ffmpeg")
            self.assertEqual(validate_timeline(plan["timeline"]), plan["timeline"])
            self.assertEqual(plan["timeline"]["tracks"][0]["clips"][0]["source"]["path"], str(footage.resolve()))
            rendered = render_timeline(
                plan["timeline"],
                root / "edit-plan-render.mp4",
                project_root=root,
            )
            self.assertEqual(rendered["streams"][0]["codec_name"], "h264")
            with self.assertRaises(TimelineValidationError):
                invalid = json.loads(json.dumps(plan["timeline"]))
                invalid["tracks"][0]["clips"] = [{
                    "id": "bad", "timeline_start_seconds": 0, "timeline_end_seconds": 3,
                    "source": {"path": "x", "in_seconds": 0, "out_seconds": 3},
                }]
                validate_timeline(invalid)

    def test_builds_timed_scenes_and_prompts(self):
        blueprint = build_blueprint("A map shows the journey. Data reveals the change.")
        self.assertEqual(len(blueprint["scenes"]), 2)
        self.assertLess(blueprint["scenes"][0]["end"], blueprint["scenes"][1]["end"])
        self.assertIn("No logos", blueprint["scenes"][0]["prompt"])
        self.assertEqual(blueprint["scenes"][0]["render"]["fps"], 12)
        self.assertEqual(blueprint["scenes"][0]["layout"]["safe_margin"], 50)

    def test_rejects_empty_input(self):
        with self.assertRaises(ValueError):
            build_blueprint(" ")

    def test_writes_svg(self):
        blueprint = build_blueprint("A paper-cut story begins.")
        with TemporaryDirectory() as directory:
            output = Path(directory) / "storyboard.svg"
            write_svg(blueprint, output)
            self.assertTrue(output.exists())
            self.assertIn("<svg", output.read_text(encoding="utf-8"))

    def test_validation_rejects_overlapping_scenes(self):
        blueprint = build_blueprint("First. Second.")
        blueprint["scenes"][1]["start"] = 0
        with self.assertRaises(ValueError):
            validate_blueprint(blueprint)

    def test_writes_animation_frames_with_expected_count(self):
        blueprint = build_blueprint("A title starts. Data changes. The story closes.")
        with TemporaryDirectory() as directory:
            count = write_ppm_frames(blueprint, Path(directory), fps=2)
            self.assertEqual(count, round(blueprint["narrative"]["estimated_duration"] * 2))
            first = Path(directory) / "frame_00000.ppm"
            self.assertTrue(first.exists())
            self.assertTrue(first.read_bytes().startswith(b"P6\n540 960\n255\n"))

    def test_scene_treatments_produce_distinct_rendered_frames(self):
        blueprint = build_blueprint(
            "Ideas become systems. Data reveals the pattern. Technology makes the loop visible. "
            "History gives the context. A map shows the path. Why does judgment matter? The loop closes."
        )
        treatments = {scene["visual_treatment"] for scene in blueprint["scenes"]}
        self.assertGreaterEqual(len(treatments), 5)
        with TemporaryDirectory() as directory:
            write_ppm_frames(blueprint, Path(directory), fps=1)
            frames = sorted(Path(directory).glob("frame_*.ppm"))
            self.assertGreaterEqual(len(frames), 7)
            self.assertGreater(len({frame.read_bytes() for frame in frames}), 3)

    def test_scene_variation_and_asset_validation(self):
        blueprint = build_blueprint("Hook. Data reveals a pattern. Why does context matter?")
        self.assertEqual(blueprint["scenes"][0]["visual_treatment"], "kinetic typography")
        self.assertNotEqual(
            blueprint["scenes"][0]["variation"]["layout_variant"],
            blueprint["scenes"][1]["variation"]["layout_variant"],
        )
        with TemporaryDirectory() as directory:
            root = Path(directory)
            asset = root / "texture.svg"
            asset.write_text("<svg/>", encoding="utf-8")
            blueprint["scenes"][0]["assets"] = [str(asset)]
            self.assertEqual(validate_assets(blueprint, root), [])
            blueprint["scenes"][0]["assets"] = [str(root / "missing.png")]
            with self.assertRaises(ValueError):
                validate_assets(blueprint, root)

    def test_composites_png_jpeg_and_safe_svg_layers(self):
        blueprint = build_blueprint("A visual asset scene.")
        with TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "assets"
            assets.mkdir()
            Image.new("RGBA", (40, 40), (255, 0, 0, 128)).save(assets / "transparent.png")
            Image.new("RGB", (40, 40), (0, 255, 0)).save(assets / "photo.jpg")
            (assets / "diagram.svg").write_text(
                '<svg width="40" height="40"><rect x="0" y="0" width="40" height="40" fill="#0000ff"/></svg>',
                encoding="utf-8",
            )
            blueprint["scenes"][0]["assets"] = [
                "assets/transparent.png", "assets/photo.jpg", "assets/diagram.svg"
            ]
            blueprint["scenes"][0]["layers"] = [
                {"type": "asset", "asset": "assets/photo.jpg", "x": 0, "y": 0, "width": 80, "height": 80, "z": 1},
                {"type": "asset", "asset": "assets/transparent.png", "x": 20, "y": 20, "width": 80, "height": 80, "opacity": 0.5, "z": 2},
                {"type": "asset", "asset": "assets/diagram.svg", "x": 100, "y": 0, "width": 80, "height": 80, "z": 3},
            ]
            self.assertEqual(validate_assets(blueprint, root), [])
            output = root / "frames"
            write_ppm_frames(blueprint, output, fps=1, project_root=root)
            rendered = Image.open(output / "frame_00000.ppm").convert("RGB")
            self.assertNotEqual(rendered.getpixel((10, 10)), (11, 21, 27))
            self.assertGreater(rendered.getpixel((110, 10))[2], rendered.getpixel((110, 10))[0])

    def test_asset_compositing_is_deterministic_and_rejects_external_svg(self):
        blueprint = build_blueprint("A visual asset scene.")
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "bad.svg").write_text(
                '<svg><image href="https://example.invalid/image.png"/></svg>', encoding="utf-8"
            )
            blueprint["scenes"][0]["assets"] = ["bad.svg"]
            with self.assertRaises(ValueError):
                validate_assets(blueprint, root)

    def test_asset_validation_rejects_corrupt_raster(self):
        blueprint = build_blueprint("A visual asset scene.")
        with TemporaryDirectory() as directory:
            root = Path(directory)
            corrupt = root / "broken.png"
            corrupt.write_bytes(b"not an image")
            blueprint["scenes"][0]["assets"] = [str(corrupt)]
            with self.assertRaises(ValueError) as error:
                validate_assets(blueprint, root)
            self.assertIn("asset is invalid", str(error.exception))

    def test_offline_pipeline_writes_staged_production_report(self):
        with TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            report = run_pipeline(
                "A strong opening. Data reveals a pattern. Technology connects the system. The story closes.",
                project,
                ffmpeg=None,
                ffprobe=None,
            )
            self.assertEqual(report["provider"]["mode"], "offline")
            self.assertEqual(report["status"], "partial")
            self.assertTrue((project / "blueprint.json").exists())
            self.assertTrue((project / "storyboard.svg").exists())
            stages = {stage["stage"] for stage in report["stages"]}
            self.assertIn("asset_planning", stages)
            self.assertIn("mp4_export", stages)

    def test_pipeline_duration_scaling_is_deterministic(self):
        with TemporaryDirectory() as directory:
            first = run_pipeline("One. Two. Three.", Path(directory) / "a", duration=12, ffmpeg=None)
            second = run_pipeline("One. Two. Three.", Path(directory) / "b", duration=12, ffmpeg=None)
            self.assertEqual(first["provider"], second["provider"])
            self.assertEqual(
                json.loads((Path(directory) / "a" / "blueprint.json").read_text(encoding="utf-8")),
                json.loads((Path(directory) / "b" / "blueprint.json").read_text(encoding="utf-8")),
            )

    def test_frame_dimensions_follow_project_aspect_ratio(self):
        blueprint = build_blueprint("A landscape title.", aspect_ratio="16:9")
        with TemporaryDirectory() as directory:
            write_ppm_frames(blueprint, Path(directory), fps=1)
            self.assertTrue((Path(directory) / "frame_00000.ppm").read_bytes().startswith(b"P6\n960 540\n255\n"))
        self.assertEqual(frame_dimensions("1:1"), (720, 720))

    def test_writes_ffmpeg_compatible_bmp_frames(self):
        blueprint = build_blueprint("A title.")
        with TemporaryDirectory() as directory:
            write_bmp_frames(blueprint, Path(directory), fps=1)
            self.assertTrue((Path(directory) / "frame_00000.bmp").read_bytes().startswith(b"BM"))

    def test_cli_plan_and_preview_pipeline(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "brief.md"
            project = root / "project"
            source.write_text("A title starts. Data changes. The story closes.", encoding="utf-8")
            import sys
            old_argv = sys.argv
            try:
                sys.argv = ["motionforge", "brief", str(source), "--project", str(project)]
                self.assertEqual(main(), 0)
                sys.argv = ["motionforge", "preview", str(project)]
                self.assertEqual(main(), 0)
            finally:
                sys.argv = old_argv
            self.assertTrue((project / "storyboard.svg").exists())
            self.assertTrue((project / "blueprint.json").exists())

    def test_create_cli_returns_failure_when_pipeline_export_fails(self):
        with TemporaryDirectory() as directory:
            with patch(
                "sys.argv",
                ["fablexis", "create", "--idea", "A title.", "--project", str(Path(directory) / "project")],
            ), patch(
                "engine.cli.run_pipeline",
                return_value={"status": "failed"},
            ):
                self.assertEqual(main(), 1)

    def test_create_cli_rejects_non_positive_or_non_finite_duration(self):
        for duration in ("0", "-1", "nan", "inf"):
            with self.subTest(duration=duration), patch(
                "sys.argv",
                [
                    "fablexis", "create", "--idea", "A title.",
                    "--duration", duration,
                ],
            ):
                with self.assertRaises(SystemExit) as error:
                    main()
                self.assertEqual(error.exception.code, 2)

    def test_export_reports_missing_ffmpeg_without_creating_video(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "brief.md"
            project = root / "project"
            source.write_text("A title starts. The story closes.", encoding="utf-8")
            import sys
            old_argv = sys.argv
            try:
                sys.argv = ["motionforge", "brief", str(source), "--project", str(project)]
                main()
                sys.argv = ["motionforge", "export", str(project)]
                with patch("engine.cli.shutil.which", return_value=None):
                    with self.assertRaises(SystemExit) as error:
                        main()
            finally:
                sys.argv = old_argv
            self.assertIn("FFmpeg", str(error.exception))
            self.assertFalse((project / "motionforge.mp4").exists())

    def test_blueprint_export_failure_preserves_previous_output_and_cleans_temp(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            blueprint = build_blueprint("A title starts. The story closes.")
            output = root / "motionforge.mp4"
            output.write_bytes(b"previous verified output")

            def write_test_frame(_blueprint, frame_dir, **_kwargs):
                frame = bytearray(70)
                frame[:2] = b"BM"
                struct.pack_into("<ii", frame, 18, 2, 2)
                (frame_dir / "frame_00000.bmp").write_bytes(frame)
                return 1

            with patch(
                "engine.blueprint_export.write_bmp_frames",
                side_effect=write_test_frame,
            ), patch(
                "engine.blueprint_export.subprocess.run",
                return_value=subprocess.CompletedProcess(
                    args=["fake-ffmpeg"],
                    returncode=1,
                    stdout="",
                    stderr="synthetic encoder failure",
                ),
            ):
                with self.assertRaisesRegex(
                    BlueprintExportError, "synthetic encoder failure"
                ):
                    export_blueprint(
                        blueprint,
                        root,
                        output,
                        ffmpeg="fake-ffmpeg",
                        ffprobe="fake-ffprobe",
                    )
            self.assertEqual(output.read_bytes(), b"previous verified output")
            self.assertEqual(list(root.glob(".motionforge.fablexis-*.mp4")), [])

    def test_blueprint_export_reports_missing_ffprobe_before_writing(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            blueprint = build_blueprint("A title starts. The story closes.")
            with patch("engine.blueprint_export.shutil.which", return_value=None):
                with self.assertRaisesRegex(BlueprintExportError, "FFprobe"):
                    export_blueprint(
                        blueprint,
                        root,
                        root / "motionforge.mp4",
                        ffmpeg="fake-ffmpeg",
                    )
            self.assertFalse((root / "motionforge.mp4").exists())
            self.assertEqual(list(root.glob(".motionforge.fablexis-*")), [])

    def test_pipeline_failure_does_not_report_stale_mp4_as_exported(self):
        with TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            project.mkdir()
            output = project / "motionforge.mp4"
            output.write_bytes(b"stale output")
            with patch(
                "engine.pipeline.export_blueprint",
                side_effect=BlueprintExportError("synthetic export failure"),
            ):
                report = run_pipeline(
                    "A strong opening. Data reveals a pattern. The story closes.",
                    project,
                    ffmpeg="fake-ffmpeg",
                    ffprobe="fake-ffprobe",
                )
            self.assertEqual(report["status"], "failed")
            self.assertIsNone(report["outputs"]["mp4"])
            self.assertEqual(output.read_bytes(), b"stale output")
            quality = json.loads((project / "quality-report.json").read_text(encoding="utf-8"))
            self.assertEqual(quality["status"], "failed")
            self.assertFalse(quality["checks"]["media_verification"])

    @unittest.skipUnless(
        shutil.which("ffmpeg") and shutil.which("ffprobe"),
        "FFmpeg and FFprobe are required for blueprint-export integration tests",
    )
    def test_export_creates_real_mp4_when_ffmpeg_is_available(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "brief.md"
            project = root / "project"
            source.write_text("A title starts. Data changes. The story closes.", encoding="utf-8")
            import sys
            old_argv = sys.argv
            try:
                sys.argv = ["motionforge", "brief", str(source), "--project", str(project)]
                main()
                sys.argv = ["motionforge", "export", str(project)]
                self.assertEqual(main(), 0)
            finally:
                sys.argv = old_argv
            output = project / "motionforge.mp4"
            self.assertTrue(output.exists())
            self.assertGreater(output.stat().st_size, 0)
            media = json.loads((project / "media-report.json").read_text(encoding="utf-8"))
            self.assertEqual(media["quality"]["status"], "passed")


if __name__ == "__main__":
    unittest.main()
