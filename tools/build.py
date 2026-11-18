"""Reconstruct the current board, its offline variant and the source map.

The board is assembled in a temporary directory (board -> plugin map -> offline)
and only the current version is written to the output. The historical v1.2 and
the golden v1.3 in release/ are never overwritten: tools/verify_sources.py pins
the v1.3 hash and evidence/ records both.
"""
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.4"
BOARD = f"design-router-pizarra-v{VERSION}.html"
OFFLINE = f"design-router-pizarra-v{VERSION}-offline.html"
MAP = "design-router-mapa-fuentes.json"
FROZEN = ("design-router-pizarra-v1.2.html", "design-router-pizarra-v1.3.html",
          "design-router-pizarra-v1.3-offline.html")
# assemble_map.py titles its output as v1.3; the current build renames it.
ASSEMBLED_TITLE = "Design Skills Router · Mapa del plugin v1.3"


def run(*args):
    subprocess.run([sys.executable, "-B", *map(str, args)], cwd=ROOT, check=True)


def frozen_hashes(output: Path) -> dict:
    return {name: hashlib.sha256((output / name).read_bytes()).hexdigest()
            for name in FROZEN if (output / name).exists()}


def build(output: Path, release: bool) -> None:
    output.mkdir(parents=True, exist_ok=True)
    before = frozen_hashes(output)
    with tempfile.TemporaryDirectory(prefix="design-router-build-") as tmp:
        staging = Path(tmp)
        run("board/build.py", "--output", staging / "design-router-pizarra-v1.2.html")
        if release:
            run("map/extract_tree.py")  # keeps map/tree_data.json in sync with the plugin
        run("map/assemble_map.py", "--output-dir", staging)
        board = (staging / "design-router-pizarra-v1.3.html").read_text(encoding="utf-8")
        if board.count(ASSEMBLED_TITLE) != 1:
            raise SystemExit(f"Título esperado no encontrado una sola vez: {ASSEMBLED_TITLE}")
        board = board.replace(ASSEMBLED_TITLE, f"Design Skills Router · Mapa del plugin v{VERSION}")
        (output / BOARD).write_text(board, encoding="utf-8")
        shutil.copyfile(staging / MAP, output / MAP)
    run("offline/build_offline.py", output / BOARD, output / OFFLINE)
    if frozen_hashes(output) != before:
        raise SystemExit("El build modificó una pizarra congelada (v1.2 o v1.3).")
    print(f"v{VERSION}: {output / BOARD}\nv{VERSION} offline: {output / OFFLINE}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path,
                        help="Write artifacts to a separate directory for local preview")
    args = parser.parse_args()
    build(args.output_dir.resolve() if args.output_dir else ROOT / "release", args.output_dir is None)
