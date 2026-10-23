import json
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from PIL import Image

from engine.cli import main
from engine.pipeline import OfflineCreativeProvider, run_pipeline
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

    @unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg is not installed")
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


if __name__ == "__main__":
    unittest.main()
