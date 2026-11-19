"""Link each semantic identity to its working-tree files and pinned upstream sources."""
import hashlib
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def source(url):
    owner, repo, kind, revision, *parts = unquote(urlsplit(url).path).strip("/").split("/")
    if kind != "blob" or len(revision) != 40:
        raise ValueError(f"Se requiere URL a un blob fijado: {url}")
    parent = Path("vendor") if owner == "fegome90-cmd" else Path("vendor/externas/sources")
    path = parent.joinpath(owner, repo, revision, *parts)
    content = (ROOT / path).read_bytes()
    blob = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
    return {"url": url, "path": path.as_posix(), "commit": revision, "git_blob": blob}


def main():
    if not (ROOT / "vendor").is_dir():
        raise SystemExit(
            "tools/index_skills.py requiere el checkout completo con vendor/ "
            "para regenerar vendor/index.json y docs/skills.md."
        )
    graph = load("board/src/relaciones/datos.json")
    baseline = load("plugin/skills/design-tree/references/tree-v0.4/skill-inventory.json")
    inventory = {skill["id"]: skill for skill in baseline["skills"]}
    rows = []
    table = ["# Índice local de skills", "",
             "Cada fila corresponde a un nodo semántico. Los enlaces abren la fuente exacta de cada catálogo. "
             "Las dos columnas pueden apuntar a revisiones distintas de la misma skill.", "",
             "| Skill y repositorio | Pizarra | Inventario del plugin | Estado en el grafo |",
             "| --- | --- | --- | --- |"]
    for node in graph["nodes"]:
        board = source(node["source"])
        baseline_entry = inventory.get(node["id"])
        plugin = source(baseline_entry["source_url"]) if baseline_entry else None
        rows.append({"id": node["id"], "label": node["label"], "status": node["status"],
                     "owners": node["owners"], "board": board, "plugin_inventory": plugin})
        def link(entry):
            return f"[{entry['commit'][:8]}](<../{entry['path']}>)" if entry else "—"
        table.append(f"| `{node['id']}` | {link(board)} | {link(plugin)} | {node['status']} |")
    assert len(rows) == graph["counts"]["unique_skills"]
    assert set(inventory) <= {r["id"] for r in rows}
    (ROOT / "vendor/index.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (ROOT / "docs/skills.md").write_text("\n".join(table) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
