"""Build the isolated CLI distributions from a temporary allowlisted stage."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


PACKAGE_FILES = (
    Path("pyproject.toml"),
    Path("src/design_skills_router/__init__.py"),
    Path("src/design_skills_router/cli.py"),
    Path("tests/test_installed_cli.py"),
)
PLUGIN_FILES = (
    Path("plugin/NOTICE.md"),
    Path("plugin/skills/design-tree/scripts/assistance.py"),
    Path("plugin/skills/design-tree/scripts/contracts.py"),
    Path("plugin/skills/design-tree/scripts/diagnostics.py"),
    Path("plugin/skills/design-tree/scripts/doctor.py"),
    Path("plugin/skills/design-tree/scripts/migration.py"),
    Path("plugin/skills/design-tree/scripts/runner.py"),
    Path("plugin/skills/design-tree/scripts/tree_model.py"),
    Path("plugin/skills/design-tree/scripts/verification.py"),
    Path("plugin/skills/design-tree/references/baseline-lock.json"),
    Path("plugin/skills/design-tree/references/contracts.json"),
    Path("plugin/skills/design-tree/references/tree-v0.4/AUDIT.md"),
    Path("plugin/skills/design-tree/references/tree-v0.4/README.md"),
    Path("plugin/skills/design-tree/references/tree-v0.4/criterion-map.json"),
    Path("plugin/skills/design-tree/references/tree-v0.4/index.html"),
    Path("plugin/skills/design-tree/references/tree-v0.4/rules.json"),
    Path("plugin/skills/design-tree/references/tree-v0.4/skill-inventory.json"),
    Path("plugin/skills/design-tree/references/tree-v0.4/tree.json"),
)


def _copy_regular_file(root: Path, stage: Path, relative: Path) -> None:
    source = root / relative
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"Refusing symlink in build input: {relative}")
    if not source.is_file():
        raise FileNotFoundError(f"Required build input is missing or not a file: {relative}")
    destination = stage / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def _build(root: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="design-skills-router-cli-") as temporary:
        stage = Path(temporary) / "project"
        stage.mkdir()
        for relative in PACKAGE_FILES:
            _copy_regular_file(root / "packages/cli", stage, relative)
        for relative in PLUGIN_FILES:
            _copy_regular_file(root, stage, relative)

        subprocess.run(
            [
                "uv", "--no-config", "build", "--offline", "--no-python-downloads",
                "--python", sys.executable, "--sdist", "--wheel",
                "--out-dir", str(out_dir),
            ],
            cwd=stage,
            check=True,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, type=Path, help="Distribution output directory outside the checkout.")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    output = args.out_dir.expanduser().resolve()
    if output == root or root in output.parents:
        parser.error("--out-dir must be outside the repository checkout")
    try:
        _build(root, output)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"CLI package build failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
