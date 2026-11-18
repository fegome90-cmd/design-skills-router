"""Check source snapshots, plugin bytes and the canonical HTML against their manifests."""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor"
EXTERNAL = VENDOR / "externas"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def check(ok, path):
    if not ok:
        raise SystemExit(f"No coincide con el manifiesto: {path}")


def verify_snapshot(base, files):
    expected = set()
    for entry in files:
        path = base / entry["path"]
        data = path.read_bytes()
        expected.add(path)
        check(len(data) == entry["bytes"], path)
        check(hashlib.sha256(data).hexdigest() == entry["sha256"], path)
        header = b"blob " + str(len(data)).encode("ascii") + b"\0"
        check(hashlib.sha1(header + data).hexdigest() == entry["git_blob"], path)
        if os.name == "posix":
            check(bool(path.stat().st_mode & 0o100) == (entry["mode"] == "100755"), path)
    check(expected == {p for p in base.rglob("*") if p.is_file()}, base)


if __name__ == "__main__":
    own_manifest = VENDOR / "my-skills-manifest.json"
    external_manifest = EXTERNAL / "external-sources-manifest.json"
    missing = [p.relative_to(ROOT).as_posix() for p in (own_manifest, external_manifest) if not p.is_file()]
    if missing:
        raise SystemExit(
            "tools/verify_sources.py requiere el checkout completo con vendor/ "
            f"(faltan: {', '.join(missing)}). En el checkout público ejecuta: "
            "python3 -B plugin/skills/design-tree/scripts/runner.py verify-package "
            "y python3 -B plugin/skills/design-tree/scripts/doctor.py --format json."
        )
    own = load(own_manifest)
    external = load(external_manifest)
    verify_snapshot(VENDOR / own["snapshot_root"], own["files"])
    for snapshot in external["sources"]:
        verify_snapshot(EXTERNAL / snapshot["path"], snapshot["files"])
    plugin = load(ROOT / "plugin/PACKAGE-HASHES.json")
    for name, sha in plugin.items():
        check(hashlib.sha256((ROOT / "plugin" / name).read_bytes()).hexdigest() == sha, name)
    golden = ROOT / "release/design-router-pizarra-v1.3.html"
    check(hashlib.sha256(golden.read_bytes()).hexdigest() ==
          "c07323286b8cf2c285049527c676f19f2d3016fadf078ac47a40e41683eb119e", golden)
    print(f"Verificados: {len(own['files'])} archivos propios, {external['counts']['files']} "
          f"externos, {len(plugin)} del manifiesto del plugin y pizarra v1.3.")
