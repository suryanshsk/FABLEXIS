"""Repository validation without third-party dependencies."""

from pathlib import Path
import json
from engine.vox_motion import validate_blueprint

ROOT = Path(__file__).parent
REQUIRED = ["SKILL.md", "README.md", "references/visual-styles.md", "references/quality-control.md"]

for relative in REQUIRED:
    path = ROOT / relative
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        raise SystemExit(f"Missing required file: {relative}")

skill_files = [ROOT / "SKILL.md", *sorted((ROOT / "skills").glob("*/SKILL.md"))]
for skill_file in skill_files:
    content = skill_file.read_text(encoding="utf-8")
    if not content.startswith("---\n") or "\nname:" not in content or "\ndescription:" not in content:
        raise SystemExit(f"Invalid skill metadata: {skill_file.relative_to(ROOT)}")

sample = ROOT / "examples" / "ipo-blueprint.json"
validate_blueprint(json.loads(sample.read_text(encoding="utf-8")))
print("Repository validation passed.")
