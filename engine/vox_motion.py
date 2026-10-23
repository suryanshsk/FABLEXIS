"""Deterministic Fablexis production blueprint engine."""

from __future__ import annotations

import html
import json
import re
import math
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover - dependency fallback is tested through the legacy path
    Image = ImageDraw = ImageFont = None


PALETTE = ["#0B1020", "#F4EBDD", "#F15A4A", "#28B8A6", "#F4C95D"]
FONT = {
    "A": "01110|10001|10001|11111|10001|10001|10001",
    "B": "11110|10001|10001|11110|10001|10001|11110",
    "C": "01111|10000|10000|10000|10000|10000|01111",
    "D": "11110|10001|10001|10001|10001|10001|11110",
    "E": "11111|10000|10000|11110|10000|10000|11111",
    "F": "11111|10000|10000|11110|10000|10000|10000",
    "G": "01111|10000|10000|10111|10001|10001|01111",
    "H": "10001|10001|10001|11111|10001|10001|10001",
    "I": "11111|00100|00100|00100|00100|00100|11111",
    "J": "00111|00010|00010|00010|10010|10010|01100",
    "K": "10001|10010|10100|11000|10100|10010|10001",
    "L": "10000|10000|10000|10000|10000|10000|11111",
    "M": "10001|11011|10101|10101|10001|10001|10001",
    "N": "10001|11001|10101|10011|10001|10001|10001",
    "O": "01110|10001|10001|10001|10001|10001|01110",
    "P": "11110|10001|10001|11110|10000|10000|10000",
    "Q": "01110|10001|10001|10001|10101|10010|01101",
    "R": "11110|10001|10001|11110|10100|10010|10001",
    "S": "01111|10000|10000|01110|00001|00001|11110",
    "T": "11111|00100|00100|00100|00100|00100|00100",
    "U": "10001|10001|10001|10001|10001|10001|01110",
    "V": "10001|10001|10001|10001|10001|01010|00100",
    "W": "10001|10001|10001|10101|10101|11011|10001",
    "X": "10001|10001|01010|00100|01010|10001|10001",
    "Y": "10001|10001|01010|00100|00100|00100|00100",
    "Z": "11111|00001|00010|00100|01000|10000|11111",
    " ": "00000|00000|00000|00000|00000|00000|00000",
}
STYLE_RULES = [
    ("map", "map and timeline", "places, movement, or history"),
    ("data", "geometric infographic", "numbers, systems, or comparisons"),
    ("people", "paper-cut collage", "people, institutions, or lived experience"),
    ("history", "archive and halftone", "historical context or evidence"),
    ("technology", "dimensional diagram", "technical systems or mechanisms"),
]
SUPPORTED_ASSET_SUFFIXES = {".png", ".jpg", ".jpeg", ".svg"}


def _sentences(text: str) -> list[str]:
    clean = re.sub(r"\s+", " ", text.strip())
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", clean) if part.strip()]


def _duration(sentence: str) -> float:
    return max(3.0, round(len(sentence.split()) / 2.5, 1))


def _style_for(sentence: str, index: int = 0, total: int = 1) -> tuple[str, str]:
    lowered = sentence.lower()
    dense = len(sentence.split()) > 12 or any(word in lowered for word in ("compare", "percent", "increase", "decrease", "steps"))
    emotional = any(word in lowered for word in ("why", "matter", "fear", "hope", "human", "judgment"))
    if index == 0:
        return "kinetic typography", "the opening hook needs immediate emphasis and a readable reveal"
    if dense:
        return "geometric infographic", "high information density benefits from an ordered visual hierarchy"
    if emotional:
        return "editorial collage", "an emotional or human question benefits from layered visual context"
    if index == total - 1 and any(word in lowered for word in ("why", "still", "matter", "close", "end")):
        return "editorial collage", "the ending benefits from layered context and a resolved visual motif"
    for keyword, style, reason in STYLE_RULES:
        if keyword in lowered:
            return style, reason
    if any(word in lowered for word in ("why", "because", "problem", "change")):
        return "editorial collage", "a claim or contrast that benefits from layered context"
    return "kinetic typography", "a concise idea that needs a clear visual emphasis"


def _prompt(scene: dict[str, Any], global_style: dict[str, Any]) -> str:
    return (
        f"Create a {scene['aspect_ratio']} editorial explainer scene in {scene['visual_treatment']} style. "
        f"Global palette: {', '.join(global_style['palette'])}. "
        f"Show {scene['visual_concept']} with {scene['composition']}. "
        f"Animate in this order: {scene['animation']}. "
        f"Use {scene['camera']} camera movement. Start with the described quiet setup and end on the focal reveal "
        f"that leads into the next scene. Maintain the shared {global_style['recurring_motif']} motif and "
        f"{global_style['texture']} texture. Use clean shapes and controlled contrast. "
        "No logos, watermarks, unrelated objects, malformed typography, invented numbers, visual clutter, or style drift. "
        "If exact text or data is required, leave a clean overlay area for post-production."
    )


def build_blueprint(text: str, *, mode: str = "production", aspect_ratio: str = "9:16") -> dict[str, Any]:
    """Build a reproducible blueprint from user-provided text."""
    if not text.strip():
        raise ValueError("Input content cannot be empty.")
    sentences = _sentences(text)
    if not sentences:
        raise ValueError("Input content did not contain usable text.")
    total = round(sum(_duration(item) for item in sentences), 1)
    global_style = {
        "palette": PALETTE,
        "typography": "bold condensed display face for hooks, neutral sans-serif for supporting labels",
        "texture": "subtle paper grain with restrained halftone accents",
        "recurring_motif": "a thin coral route line that becomes a reveal mask",
        "motion_rules": ["meaningful reveals", "short readable holds", "shape-matched transitions"],
    }
    scenes: list[dict[str, Any]] = []
    cursor = 0.0
    for index, sentence in enumerate(sentences, 1):
        duration = _duration(sentence)
        style, reason = _style_for(sentence, index - 1, len(sentences))
        concept = f"Make the idea '{sentence[:110]}' tangible using {style}"
        scene = {
            "id": f"scene-{index:02d}",
            "number": index,
            "purpose": "hook" if index == 1 else ("conclusion" if index == len(sentences) else "develop the argument"),
            "narration": sentence,
            "start": round(cursor, 1),
            "end": round(cursor + duration, 1),
            "duration": duration,
            "timing_type": "estimated",
            "aspect_ratio": aspect_ratio,
            "visual_treatment": style,
            "treatment_reason": reason,
            "direction": {
                "tone": "urgent" if index == 1 else ("reflective" if index == len(sentences) else "curious"),
                "information_density": "high" if len(sentence.split()) > 12 else "focused",
                "asset_strategy": "deterministic graphics first; optional local assets validated before use",
            },
            "visual_concept": concept,
            "composition": "one dominant focal subject in the lower third, with supporting labels in a quiet margin",
            "animation": "reveal the focal subject, introduce one supporting element, then resolve into a clear graphic match",
            "camera": "a restrained push-in with a lateral parallax shift",
            "transition": "match the final shape or direction into the next scene",
            "on_screen_text": "Use only a short keyword or exact supplied number; typeset precise copy in post.",
            "sound": "a soft paper movement on the reveal and a restrained tonal accent on the hold",
            "assets": ["background texture", "focal illustration", "short text overlay"],
            "continuity": "Keep the global palette, coral route-line motif, and camera direction.",
            "variation": {
                "layout_variant": ["left-anchor", "center-stack", "right-anchor"][index % 3],
                "motion_variant": ["reveal", "rise", "drift"][index % 3],
            },
            "layout": {
                "safe_margin": 50,
                "focal_area": "center-lower",
                "depth_layers": ["background", "shadow", "focal", "labels"],
            },
            "typography": {
                "display": "pixel editorial",
                "hierarchy": ["scene label", "focal word", "support label"],
                "alignment": "safe-area aligned",
            },
            "transition_spec": {
                "type": "shape-match",
                "duration": 0.4,
                "direction": "forward",
            },
            "render": {
                "fps": 12,
                "width": frame_dimensions(aspect_ratio)[0],
                "height": frame_dimensions(aspect_ratio)[1],
            },
            "prompt": "",
        }
        scene["prompt"] = _prompt(scene, global_style)
        scenes.append(scene)
        cursor += duration

    ledger = [{
        "claim": sentence,
        "status": "user_supplied",
        "source": "input",
        "note": "Verify externally if this claim is consequential.",
    } for sentence in sentences]
    blueprint = {
        "schema_version": "1.0",
        "project": {"name": "Fablexis project", "mode": mode, "aspect_ratio": aspect_ratio},
        "analysis": {
            "thesis": sentences[0],
            "audience": "Inferred from the supplied material; confirm if material to the edit.",
            "hook": sentences[0],
            "assumptions": ["Timing is estimated at approximately 150 words per minute.", "No external research was performed."],
        },
        "global_style": global_style,
        "narrative": {"estimated_duration": total, "scene_count": len(scenes), "arc": ["hook", "development", "conclusion"]},
        "scenes": scenes,
        "evidence_ledger": ledger,
        "editing_blueprint": {
            "assembly": "Align each scene to its narration range and preserve the readable holds.",
            "compositing": "Add exact text, numbers, charts, and captions in post-production.",
            "audio": "Record or import voiceover first, then place restrained transition and emphasis sounds.",
        },
        "quality_control": {
            "status": "needs_review",
            "checks": ["fact verification", "text readability", "continuity", "scene variety", "tool feasibility"],
        },
    }
    validate_blueprint(blueprint)
    return blueprint


def validate_blueprint(blueprint: dict[str, Any]) -> list[str]:
    """Return validation errors; raise ValueError for malformed blueprints."""
    errors: list[str] = []
    if blueprint.get("schema_version") != "1.0":
        errors.append("schema_version must be 1.0")
    scenes = blueprint.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        errors.append("scenes must be a non-empty list")
    else:
        previous_end = 0.0
        for scene in scenes:
            for key in ("id", "narration", "start", "end", "duration", "prompt"):
                if not scene.get(key) and scene.get(key) != 0:
                    errors.append(f"{scene.get('id', 'scene')} is missing {key}")
            if scene.get("start", 0) < previous_end:
                errors.append(f"{scene.get('id', 'scene')} overlaps the previous scene")
            if scene.get("end", 0) <= scene.get("start", 0):
                errors.append(f"{scene.get('id', 'scene')} has invalid timing")
            previous_end = scene.get("end", previous_end)
    if errors:
        raise ValueError("; ".join(errors))
    return errors


def validate_assets(blueprint: dict[str, Any], project_root: Path | None = None) -> list[str]:
    """Validate only explicit user asset paths; descriptive asset requirements are allowed."""
    errors: list[str] = []
    root = project_root or Path.cwd()
    for scene in blueprint.get("scenes", []):
        values = list(scene.get("assets", []))
        values.extend(layer.get("asset", "") for layer in scene.get("layers", []) if layer.get("type") == "asset")
        for value in values:
            candidate = Path(value.get("path", "")) if isinstance(value, dict) else Path(value)
            if candidate.suffix.lower() not in SUPPORTED_ASSET_SUFFIXES:
                continue
            path = candidate if candidate.is_absolute() else root / candidate
            try:
                resolved = path.resolve()
                resolved.relative_to(root.resolve())
            except ValueError as exc:
                raise ValueError(f"{scene.get('id', 'scene')} asset escapes project root: {path}") from exc
            if not path.exists():
                errors.append(f"{scene.get('id', 'scene')} asset not found: {path}")
            elif path.stat().st_size == 0:
                errors.append(f"{scene.get('id', 'scene')} asset is empty: {path}")
            elif path.suffix.lower() == ".svg":
                try:
                    _load_svg_asset(path, (128, 128))
                except (OSError, ValueError, ET.ParseError) as exc:
                    errors.append(f"{scene.get('id', 'scene')} asset is invalid: {path} ({exc})")
            else:
                try:
                    _load_asset(path, (128, 128))
                except (OSError, ValueError) as exc:
                    errors.append(f"{scene.get('id', 'scene')} asset is invalid: {path} ({exc})")
    if errors:
        raise ValueError("; ".join(errors))
    return errors


def _asset_path(value: Any, root: Path) -> Path:
    raw = value.get("path", "") if isinstance(value, dict) else value
    path = Path(raw)
    if path.is_absolute():
        raise ValueError(f"Asset paths must be relative to the project: {path}")
    resolved = (root / path).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"Asset path escapes project root: {path}") from exc
    return resolved


def _color(value: str | None, fallback: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    if not value:
        return fallback
    match = re.fullmatch(r"#([0-9a-fA-F]{6})(?:([0-9a-fA-F]{2}))?", value.strip())
    if not match:
        return fallback
    rgb = tuple(int(match.group(1)[i:i + 2], 16) for i in (0, 2, 4))
    return (*rgb, int(match.group(2), 16) if match.group(2) else 255)


def _load_svg_asset(path: Path, size: tuple[int, int]) -> Any:
    if Image is None:
        raise ValueError("Pillow is required for SVG compositing")
    root = ET.parse(path).getroot()
    source = ET.tostring(root, encoding="unicode")
    if re.search(r"<script\b|(?:href|xlink:href|src)\s*=\s*['\"](?:https?|file):", source, re.IGNORECASE):
        raise ValueError("SVG external resources and scripts are not allowed")
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    viewbox = root.attrib.get("viewBox", "")
    numbers = [float(item) for item in re.findall(r"-?\d+(?:\.\d+)?", viewbox)]
    source_w = numbers[2] if len(numbers) == 4 else float(root.attrib.get("width", size[0]))
    source_h = numbers[3] if len(numbers) == 4 else float(root.attrib.get("height", size[1]))
    sx, sy = size[0] / max(source_w, 1), size[1] / max(source_h, 1)
    def point(value: str, scale: float) -> int:
        return round(float(re.sub(r"[^0-9.+-]", "", value or "0")) * scale)
    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1]
        fill = _color(element.attrib.get("fill"), (0, 0, 0, 0))
        if tag == "rect":
            box = (point(element.attrib.get("x", "0"), sx), point(element.attrib.get("y", "0"), sy),
                   point(element.attrib.get("x", "0"), sx) + point(element.attrib.get("width", "0"), sx),
                   point(element.attrib.get("y", "0"), sy) + point(element.attrib.get("height", "0"), sy))
            draw.rectangle(box, fill=fill)
        elif tag in {"circle", "ellipse"}:
            cx, cy = point(element.attrib.get("cx", "0"), sx), point(element.attrib.get("cy", "0"), sy)
            rx = point(element.attrib.get("r", element.attrib.get("rx", "0")), sx)
            ry = point(element.attrib.get("r", element.attrib.get("ry", "0")), sy)
            draw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=fill)
        elif tag == "line":
            draw.line((point(element.attrib.get("x1", "0"), sx), point(element.attrib.get("y1", "0"), sy),
                       point(element.attrib.get("x2", "0"), sx), point(element.attrib.get("y2", "0"), sy)),
                      fill=fill, width=max(1, point(element.attrib.get("stroke-width", "1"), sx)))
    return canvas


def _load_asset(path: Path, size: tuple[int, int]) -> Any:
    if Image is None:
        raise ValueError("Pillow is required for asset compositing")
    if path.suffix.lower() == ".svg":
        return _load_svg_asset(path, size)
    try:
        with Image.open(path) as source:
            return source.convert("RGBA")
    except OSError as exc:
        raise ValueError(f"Unable to decode asset {path}: {exc}") from exc


def _font_for(scene: dict[str, Any], size: int, weight: str = "regular") -> Any:
    if ImageFont is None:
        return None
    config = scene.get("typography", {})
    configured = config.get("font_file") or config.get(f"{weight}_font_file")
    candidates = [configured] if configured else []
    if os.name == "nt":
        candidates.extend([
            r"C:\Windows\Fonts\segoeuib.ttf" if weight == "bold" else r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\arialbd.ttf" if weight == "bold" else r"C:\Windows\Fonts\arial.ttf",
        ])
    candidates.extend(["DejaVuSans-Bold.ttf" if weight == "bold" else "DejaVuSans.ttf"])
    for candidate in candidates:
        if candidate:
            try:
                return ImageFont.truetype(str(candidate), size)
            except OSError:
                continue
    return ImageFont.load_default()


def _ease(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def _draw_wrapped_text(draw: Any, text: str, box: tuple[int, int, int, int], font: Any,
                       fill: tuple[int, int, int, int], align: str = "left",
                       reveal: float = 1.0, spacing: int = 6) -> None:
    x0, y0, x1, y1 = box
    words, lines, current = text.split(), [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=font) <= max(1, x1 - x0):
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    visible = max(1, math.ceil(len(lines) * max(0.0, min(1.0, reveal)))) if lines else 0
    for index, line in enumerate(lines[:visible]):
        line_width = draw.textlength(line, font=font)
        x = x0 if align == "left" else (x1 - line_width) / 2 if align == "center" else x1 - line_width
        draw.text((x + 2, y0 + index * (font.size + spacing) + 2), line, font=font, fill=(0, 0, 0, 150))
        draw.text((x, y0 + index * (font.size + spacing)), line, font=font, fill=fill)


def _composite_layer(canvas: Any, layer: dict[str, Any], root: Path, progress: float) -> None:
    if layer.get("type") != "asset":
        return
    path = _asset_path(layer.get("asset", layer.get("path", "")), root)
    target = (int(layer.get("width", canvas.width)), int(layer.get("height", canvas.height)))
    asset = _load_asset(path, target)
    fit = layer.get("fit", "contain")
    scale = max(target[0] / asset.width, target[1] / asset.height) if fit == "cover" else min(target[0] / asset.width, target[1] / asset.height)
    resized = asset.resize((max(1, round(asset.width * scale)), max(1, round(asset.height * scale))), Image.Resampling.LANCZOS)
    if fit == "cover":
        left, top = (resized.width - target[0]) // 2, (resized.height - target[1]) // 2
        resized = resized.crop((left, top, left + target[0], top + target[1]))
    x = int(layer.get("x", 0) + layer.get("animate_x", 0) * _ease(progress))
    y = int(layer.get("y", 0) + layer.get("animate_y", 0) * _ease(progress))
    opacity = max(0.0, min(1.0, float(layer.get("opacity", 1.0) + layer.get("animate_opacity", 0) * _ease(progress))))
    if opacity < 1:
        alpha = resized.getchannel("A").point(lambda value: round(value * opacity))
        resized.putalpha(alpha)
    rotation = float(layer.get("rotation", 0))
    if rotation:
        resized = resized.rotate(rotation, resample=Image.Resampling.BICUBIC, expand=True)
    canvas.alpha_composite(resized, (x, y))


def _write_pillow_frames(blueprint: dict[str, Any], directory: Path, *, fps: int,
                         project_root: Path) -> int:
    if Image is None:
        return 0
    ratio = blueprint.get("project", {}).get("aspect_ratio", "9:16")
    width, height = frame_dimensions(ratio)
    count = max(1, round(blueprint["narrative"]["estimated_duration"] * fps))
    for frame in range(count):
        elapsed = frame / fps
        scene = next((item for item in blueprint["scenes"] if item["start"] <= elapsed < item["end"]), blueprint["scenes"][-1])
        progress = min(1.0, max(0.0, (elapsed - scene["start"]) / scene["duration"]))
        base = Image.new("RGBA", (width, height), (11, 16, 32, 255))
        draw = ImageDraw.Draw(base)
        for y in range(height):
            value = round(11 + 8 * y / max(1, height - 1))
            draw.line((0, y, width, y), fill=(value, value + 5, min(48, value + 16), 255))
        treatment = scene["visual_treatment"]
        panel_x = int(50 + progress * 100)
        draw.rectangle((panel_x + 12, 232, panel_x + 252, 612), fill=(5, 8, 18, 220))
        draw.rectangle((panel_x, 220, panel_x + 240, 600), fill=(241, 90, 74, 255))
        foreground = ImageDraw.Draw(base)
        headline = _font_for(scene, 42 if scene["number"] == 1 else 27, "bold")
        label = _font_for(scene, 28, "regular")
        _draw_wrapped_text(foreground, "FABLEXIS" if scene["number"] == 1 else scene["purpose"],
                           (50, 55, width - 50, 145), headline, (244, 235, 221, 255), "left")
        foreground.rectangle((50, 160, width - 50, 166), fill=(241, 90, 74, 255))
        if "geometric infographic" in treatment or "data" in treatment:
            foreground.line((58, 760, 490, 760), fill=(244, 235, 221, 255), width=2)
            foreground.line((58, 470, 58, 760), fill=(244, 235, 221, 255), width=2)
            for index, value in enumerate([.35, .55, .45, .82, .68]):
                bar = round(300 * min(1.0, value + progress * .15))
                foreground.rectangle((70 + index * 82, 760 - bar, 125 + index * 82, 760), fill=(40, 184, 166, 255))
                foreground.text((90 + index * 82, 770), str(index + 1), font=label, fill=(244, 235, 221, 255))
            _draw_wrapped_text(foreground, "DATA / SIGNAL", (70, 815, width - 50, 870), label, (244, 235, 221, 255))
        elif "editorial collage" in treatment or "paper-cut" in treatment or "archive" in treatment:
            foreground.rectangle((panel_x - 24, 255, panel_x + 160, 430), fill=(244, 235, 221, 255))
            foreground.rectangle((panel_x + 90, 390, panel_x + 276, 570), fill=(244, 201, 93, 255))
            _draw_wrapped_text(foreground, "CONTEXT", (panel_x - 8, 290, panel_x + 150, 340), label, (11, 16, 32, 255))
        elif "dimensional diagram" in treatment:
            foreground.ellipse((panel_x + 50, 340, panel_x + 190, 480), fill=(40, 184, 166, 255))
            foreground.line((panel_x + 120, 410, 80, 730), fill=(244, 235, 221, 255), width=6)
            foreground.line((panel_x + 120, 410, 460, 730), fill=(244, 235, 221, 255), width=6)
        else:
            text = " ".join(scene.get("narration", "IDEA").split()[:max(1, round(progress * 4))])
            _draw_wrapped_text(foreground, text, (panel_x + 20, 390, panel_x + 220, 540), _font_for(scene, 35, "bold"), (11, 16, 32, 255))
        for layer in sorted(scene.get("layers", []), key=lambda item: item.get("z", 0)):
            _composite_layer(base, layer, project_root, progress)
        foreground = ImageDraw.Draw(base)
        _draw_wrapped_text(foreground, "FABLEXIS" if scene["number"] == 1 else scene["purpose"],
                           (50, 55, width - 50, 145), headline, (244, 235, 221, 255), "left")
        foreground.rectangle((50, 160, width - 50, 166), fill=(241, 90, 74, 255))
        foreground.text((60 + round(progress * 180), 880), "NEXT", font=_font_for(scene, 36, "bold"), fill=(244, 201, 93, 255))
        image = base.convert("RGB")
        image.save(directory / f"frame_{frame:05d}.ppm", format="PPM")
    return count


def write_markdown(blueprint: dict[str, Any], path: Path) -> None:
    lines = [f"# {blueprint['project']['name']}", "", "## Creative direction", "",
             f"- Thesis: {blueprint['analysis']['thesis']}",
             f"- Estimated duration: {blueprint['narrative']['estimated_duration']} seconds",
             f"- Palette: {', '.join(blueprint['global_style']['palette'])}", "", "## Storyboard", ""]
    for scene in blueprint["scenes"]:
        lines.extend([
            f"### {scene['id']} ({scene['start']}s - {scene['end']}s)",
            f"**Narration:** {scene['narration']}",
            f"**Treatment:** {scene['visual_treatment']} - {scene['treatment_reason']}",
            f"**Visual:** {scene['visual_concept']}",
            f"**Motion:** {scene['animation']}",
            f"**Prompt:** {scene['prompt']}", "",
        ])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_svg(blueprint: dict[str, Any], path: Path) -> None:
    width, height = 1080, 1920
    cards = []
    for index, scene in enumerate(blueprint["scenes"]):
        y = 40 + index * 230
        title = html.escape(f"{scene['id']}  {scene['visual_treatment']}")
        narration = html.escape(scene["narration"][:120])
        cards.append(
            f'<rect x="40" y="{y}" width="1000" height="190" rx="18" fill="#F4EBDD" stroke="#F15A4A" stroke-width="4"/>'
            f'<text x="70" y="{y + 45}" font-family="Arial" font-size="28" font-weight="700" fill="#0B1020">{title}</text>'
            f'<text x="70" y="{y + 90}" font-family="Arial" font-size="22" fill="#0B1020">{narration}</text>'
            f'<text x="70" y="{y + 140}" font-family="Arial" font-size="18" fill="#555">"{html.escape(scene["purpose"])}"  {scene["start"]}s - {scene["end"]}s</text>'
        )
    content = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{max(height, 100 + len(cards) * 230)}" viewBox="0 0 {width} {max(height, 100 + len(cards) * 230)}"><rect width="100%" height="100%" fill="#0B1020"/><text x="40" y="50" font-family="Arial" font-size="30" fill="#F4EBDD">Fablexis storyboard</text>{"".join(cards)}</svg>'
    path.write_text(content, encoding="utf-8")


def write_ppm_frames(
    blueprint: dict[str, Any],
    directory: Path,
    *,
    fps: int = 12,
    project_root: Path | None = None,
) -> int:
    """Write deterministic, dependency-free preview frames for FFmpeg."""
    directory.mkdir(parents=True, exist_ok=True)
    if Image is not None:
        return _write_pillow_frames(blueprint, directory, fps=fps, project_root=project_root or Path.cwd())
    ratio = blueprint.get("project", {}).get("aspect_ratio", "9:16")
    width, height = frame_dimensions(ratio)
    frame_count = max(1, round(blueprint["narrative"]["estimated_duration"] * fps))
    scenes = blueprint["scenes"]
    def draw_rect(pixels: bytearray, x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int]) -> None:
        for y in range(max(0, y0), min(height, y1)):
            start = (y * width + max(0, x0)) * 3
            pixels[start:start + max(0, min(width, x1) - max(0, x0)) * 3] = bytes(color) * max(0, min(width, x1) - max(0, x0))

    def draw_line(pixels: bytearray, x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int], thickness: int = 4) -> None:
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for step in range(steps + 1):
            x = round(x0 + (x1 - x0) * step / steps)
            y = round(y0 + (y1 - y0) * step / steps)
            draw_rect(pixels, x - thickness, y - thickness, x + thickness + 1, y + thickness + 1, color)

    def draw_circle(pixels: bytearray, cx: int, cy: int, radius: int, color: tuple[int, int, int]) -> None:
        radius_squared = radius * radius
        for y in range(max(0, cy - radius), min(height, cy + radius + 1)):
            span = int((radius_squared - (y - cy) ** 2) ** 0.5)
            draw_rect(pixels, cx - span, y, cx + span + 1, y + 1, color)

    def draw_dots(pixels: bytearray, x0: int, y0: int, x1: int, y1: int,
                 spacing: int, radius: int, color: tuple[int, int, int]) -> None:
        for y in range(y0, y1, spacing):
            for x in range(x0, x1, spacing):
                draw_circle(pixels, x, y, radius, color)

    def draw_text(pixels: bytearray, text: str, x: int, y: int, scale: int, color: tuple[int, int, int]) -> None:
        cursor = x
        for char in text.upper()[:28]:
            rows = FONT.get(char, FONT[" "]).split("|")
            for row, pattern in enumerate(rows):
                for col, bit in enumerate(pattern):
                    if bit == "1":
                        draw_rect(pixels, cursor + col * scale, y + row * scale,
                                  cursor + (col + 1) * scale, y + (row + 1) * scale, color)
            cursor += 6 * scale

    def draw_text_fit(pixels: bytearray, text: str, x: int, y: int, max_width: int,
                      preferred_scale: int, color: tuple[int, int, int]) -> None:
        visible = text.upper()[:28]
        scale = min(preferred_scale, max(1, max_width // max(6, len(visible) * 6)))
        draw_text(pixels, visible, x, y, scale, color)

    for frame in range(frame_count):
        elapsed = frame / fps
        scene = next((item for item in scenes if item["start"] <= elapsed < item["end"]), scenes[-1])
        progress = min(1.0, max(0.0, (elapsed - scene["start"]) / scene["duration"]))
        coral = (241, 90, 74)
        navy = (11, 16, 32)
        cream = (244, 235, 221)
        # A subtle vertical gradient gives the flat-color fallback a sense of depth.
        pixels = bytearray()
        for y in range(height):
            mix = y / max(1, height - 1)
            pixels.extend(bytes((
                round(navy[0] + 8 * mix),
                round(navy[1] + 8 * mix),
                round(navy[2] + 14 * mix),
            )) * width)
        draw_text_fit(
            pixels,
            "FABLEXIS" if scene["number"] == 1 else scene["purpose"],
            50,
            70,
            width - 100,
            8,
            cream,
        )
        draw_rect(pixels, 50, 160, 490, 166, coral)
        variant = scene.get("variation", {}).get("layout_variant", "center-stack")
        anchor = {"left-anchor": 0, "center-stack": 90, "right-anchor": 180}.get(variant, 90)
        panel_x = int(20 + anchor + progress * 70)
        treatment = scene["visual_treatment"]
        # Soft shadow and layered panel are shared visual grammar across treatments.
        draw_rect(pixels, panel_x + 12, 232, panel_x + 252, 612, (5, 8, 18))
        draw_rect(pixels, panel_x, 220, panel_x + 240, 600, coral)
        if "geometric infographic" in treatment or "data" in treatment:
            values = [0.35, 0.55, 0.45, 0.82, 0.68]
            draw_line(pixels, 58, 760, 490, 760, cream, 2)
            draw_line(pixels, 58, 470, 58, 760, cream, 2)
            for index, value in enumerate(values):
                bar_height = int(300 * min(1.0, value + progress * 0.15))
                draw_rect(pixels, 70 + index * 82, 760 - bar_height, 125 + index * 82, 760, (40, 184, 166))
                draw_text_fit(pixels, str(index + 1), 90 + index * 82, 775, 40, 3, cream)
            draw_text_fit(pixels, "DATA / SIGNAL", 70, 825, width - 140, 6, cream)
        elif "dimensional diagram" in treatment:
            draw_circle(pixels, panel_x + 120, 410, 70, (40, 184, 166))
            draw_circle(pixels, panel_x + 120, 410, 32, coral)
            draw_line(pixels, panel_x + 120, 410, 80, 730, cream, 3)
            draw_line(pixels, panel_x + 120, 410, 460, 730, cream, 3)
            draw_circle(pixels, 80, 730, 16, (244, 201, 93))
            draw_circle(pixels, 460, 730, 16, (244, 201, 93))
            draw_text_fit(pixels, "LOOP", panel_x + 38, 510, 164, 6, navy)
        elif "editorial collage" in treatment or "paper-cut" in treatment or "archive" in treatment:
            # Three tactile planes: a shadowed backing sheet, a paper card, and a moving cutout.
            draw_rect(pixels, panel_x - 32, 267, panel_x + 168, 450, (5, 8, 18))
            draw_rect(pixels, panel_x - 24, 255, panel_x + 160, 430, cream)
            draw_rect(pixels, panel_x + 98, 398, panel_x + 286, 578, (5, 8, 18))
            draw_rect(pixels, panel_x + 90, 390, panel_x + 276, 570, (244, 201, 93))
            draw_rect(pixels, panel_x + 30, 500, panel_x + 210, 530, coral)
            draw_dots(pixels, panel_x - 8, 350, panel_x + 145, 420, 18, 2, (210, 200, 184))
            draw_text_fit(pixels, "CONTEXT", panel_x - 8, 290, 160, 4, navy)
        elif "map" in treatment or "timeline" in treatment:
            route = [(80, 700), (180, 610), (280, 680), (380, 520), (460, 580)]
            visible = max(2, round(2 + progress * (len(route) - 2)))
            for start, end in zip(route[:visible - 1], route[1:visible]):
                draw_line(pixels, start[0], start[1], end[0], end[1], (244, 201, 93), 5)
            for node_x, node_y in route[:visible]:
                draw_circle(pixels, node_x, node_y, 14, (40, 184, 166))
            draw_text_fit(pixels, "PATH", 70, 790, 180, 6, cream)
        else:
            source = scene.get("narration", "IDEA").split()
            reveal_count = max(1, min(len(source), round(progress * len(source)) + 1))
            draw_text_fit(pixels, " ".join(source[:reveal_count]), panel_x + 20, 400, 200, 5, navy)
        draw_text_fit(pixels, "NEXT", int(60 + progress * 250), 880, width - 80, 5, (244, 201, 93))
        path = directory / f"frame_{frame:05d}.ppm"
        path.write_bytes(f"P6\n{width} {height}\n255\n".encode("ascii") + pixels)
    return frame_count


def frame_dimensions(aspect_ratio: str) -> tuple[int, int]:
    """Return the deterministic raster dimensions for a project aspect ratio."""
    if aspect_ratio == "16:9":
        return 960, 540
    if aspect_ratio == "1:1":
        return 720, 720
    return 540, 960


def write_bmp_frames(
    blueprint: dict[str, Any],
    directory: Path,
    *,
    fps: int = 12,
    project_root: Path | None = None,
) -> int:
    """Write BMP frames for FFmpeg builds without PPM or rawvideo demuxers."""
    directory.mkdir(parents=True, exist_ok=True)
    ratio = blueprint.get("project", {}).get("aspect_ratio", "9:16")
    width, height = frame_dimensions(ratio)
    ppm_dir = directory / "_ppm"
    count = write_ppm_frames(blueprint, ppm_dir, fps=fps, project_root=project_root)
    row_size = (width * 3 + 3) & ~3
    image_size = row_size * height
    for ppm_path in sorted(ppm_dir.glob("frame_*.ppm")):
        payload = ppm_path.read_bytes()
        marker = b"\n255\n"
        offset = payload.find(marker)
        if offset < 0:
            raise ValueError(f"Invalid generated frame: {ppm_path}")
        rgb = payload[offset + len(marker):]
        rows = [
            rgb[y * width * 3:(y + 1) * width * 3]
            for y in range(height)
        ]
        pixels = bytearray()
        padding = bytes(row_size - width * 3)
        for row in reversed(rows):
            bgr = bytearray(len(row))
            for x in range(0, len(row), 3):
                bgr[x:x + 3] = bytes((row[x + 2], row[x + 1], row[x]))
            pixels.extend(bgr)
            pixels.extend(padding)
        file_size = 54 + image_size
        header = bytearray(b"BM")
        header.extend(file_size.to_bytes(4, "little"))
        header.extend((0).to_bytes(4, "little"))
        header.extend((54).to_bytes(4, "little"))
        dib = bytearray()
        dib.extend((40).to_bytes(4, "little"))
        dib.extend(width.to_bytes(4, "little"))
        dib.extend(height.to_bytes(4, "little"))
        dib.extend((1).to_bytes(2, "little"))
        dib.extend((24).to_bytes(2, "little"))
        dib.extend((0).to_bytes(4, "little"))
        dib.extend(image_size.to_bytes(4, "little"))
        dib.extend((2835).to_bytes(4, "little") * 2)
        dib.extend((0).to_bytes(4, "little") * 2)
        (directory / ppm_path.with_suffix(".bmp").name).write_bytes(bytes(header) + bytes(dib) + bytes(pixels))
    return count
