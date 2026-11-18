"""Reconstruye el visor histórico v0.4 con los datos canónicos del plugin."""

import argparse
from hashlib import sha256
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory


HERE = Path(__file__).resolve().parent
ORIGINAL = HERE / "original"
DEFAULT_BASELINE = HERE.parent / "plugin" / "skills/design-tree/references/tree-v0.4"
BUILD_DATA = ("tree.json", "rules.json", "skill-inventory.json", "criterion-map.json")
CHECKS = {
    "regressions": ("tests/check_regressions.py", "."),
    "model": ("-m", "pytest", "-q"),
    "browser": ("tests/check_browser.py",),
}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def verify_original(baseline):
    manifest = (ORIGINAL / "SHA256SUMS.txt").read_text(encoding="utf-8")
    for line in manifest.splitlines():
        expected, relative = line.split("  ", 1)
        path = ORIGINAL / relative
        if not path.is_file():
            path = baseline / relative
        if not path.is_file() or digest(path) != expected:
            raise ValueError(f"El archivo difiere del ZIP original: {relative}")


def build(baseline, output, verify, checks):
    if output.is_relative_to(baseline) or output.is_relative_to(ORIGINAL):
        raise ValueError("El destino debe quedar fuera de las fuentes y del baseline")
    if verify:
        verify_original(baseline)
    with TemporaryDirectory(prefix="decision-tree-v04-") as temporary:
        work = Path(temporary)
        shutil.copytree(ORIGINAL, work, dirs_exist_ok=True)
        for name in BUILD_DATA:
            shutil.copyfile(baseline / name, work / name)
        subprocess.run([sys.executable, "build.py"], cwd=work, check=True)
        generated = work / "index.html"
        if verify and generated.read_bytes() != (baseline / "index.html").read_bytes():
            raise ValueError("El resultado difiere del visor canónico incluido en el plugin")
        for name in checks:
            subprocess.run([sys.executable, *CHECKS[name]], cwd=work, check=True)
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(generated, output)
        print(f"{digest(output)}  {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--output", type=Path, default=HERE / "release/index.html")
    parser.add_argument("--verify-original", action="store_true", help="Comprueba el manifiesto histórico y exige un visor binariamente idéntico")
    parser.add_argument("--check", choices=CHECKS, action="append", default=[], help="Ejecuta una prueba original. Se puede repetir.")
    args = parser.parse_args()
    try:
        build(args.baseline.resolve(), args.output.resolve(), args.verify_original, args.check)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
