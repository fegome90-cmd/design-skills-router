import hashlib
import json
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1] / "plugin"
SKILL = "skills/design-tree"
REFERENCE = f"{SKILL}/references"
BASELINE = f"{REFERENCE}/tree-v0.4"
TREE_FILE = f"{BASELINE}/tree.json"
RULES_FILE = f"{BASELINE}/rules.json"
CRITERION_FILE = f"{BASELINE}/criterion-map.json"
INVENTORY_FILE = f"{BASELINE}/skill-inventory.json"
CONTRACTS_FILE = f"{REFERENCE}/contracts.json"
LOCK_FILE = f"{REFERENCE}/baseline-lock.json"
EXPANDER_FILE = f"{SKILL}/scripts/tree_model.py"

sys.path.insert(0, str(PLUGIN / SKILL / "scripts"))
from tree_model import expand_model, flatten


def load(file):
    return json.loads((PLUGIN / file).read_text(encoding="utf-8"))


def key(value):
    return str(value).replace("~", "~0").replace("/", "~1")


def digest(file):
    return hashlib.sha256((PLUGIN / file).read_bytes()).hexdigest()


def located(record, file, pointer):
    return {**record, "file": file, "pointer": pointer}


def extract():
    tree = load(TREE_FILE)
    lock = load(LOCK_FILE)
    contracts = load(CONTRACTS_FILE)
    plugin = load("plugin.json")
    rule_data = load(RULES_FILE)
    criterion_data = load(CRITERION_FILE)
    inventory = load(INVENTORY_FILE)
    nodes, edges, requirements = [], [], []
    index = {}
    templated_by = defaultdict(list)
    criterion_by_rule = {record["rule"]: (row, record) for row, record in enumerate(criterion_data)}
    relations_by_node = defaultdict(list)
    for relation in contracts["relations"]:
        for node_id in relation["applies_to"]:
            relations_by_node[node_id].append(relation["id"])

    def edge(source, target, kind, label, pointer):
        return located(dict(source=source, target=target, kind=kind, label=label), TREE_FILE, pointer)

    def walk(node, pointer, template=None):
        node_id = node["id"]
        kind = node["kind"]
        info = dict(id=node_id, kind=kind, layer="baseline", template=template)
        if kind == "instance":
            target = node["template_ref"]
            info.update(title=f"Instancia de {target}", summary="Expande la definición compartida con el prefijo y el contexto declarados.")
            info.update({k: v for k, v in node.items() if k not in ("id", "kind")})
            edges.append(edge(node_id, target, "template_ref", "Referencia a definición", pointer + "/template_ref"))
            templated_by[target].append(node_id)
        else:
            info.update(
                title=node["title"],
                summary=node.get("reason") or node.get("criterion") or node["title"],
                requires=node.get("requires", []),
                rules=node.get("rule_ids", []),
                skills=node.get("skills", []),
                contracts=relations_by_node[node_id],
            )
            fields = ("criterion", "output", "applies_to", "proposal_status", "decision_summary_required",
                      "terminal_status", "evaluation_status", "assessment_axis", "adoption_contract",
                      "candidate_key", "instance_scope", "evidence_refs")
            info.update({name: node[name] for name in fields if name in node})
            for row, prerequisite in enumerate(info["requires"]):
                requirements.append(edge(node_id, prerequisite, "requires", "Prerrequisito", pointer + f"/requires/{row}"))
        info = located(info, TREE_FILE, pointer)
        assert node_id not in index
        nodes.append(info)
        index[node_id] = info
        for row, child in enumerate(node.get("children", [])):
            child_pointer = pointer + f"/children/{row}"
            target = child["node"]["id"]
            relation = "alternative" if kind == "decision" else "all_branch"
            assert kind in ("decision", "all")
            edges.append(edge(node_id, target, relation, child["answer"], child_pointer))
            walk(child["node"], child_pointer + "/node", template)

    root = tree["root"]["id"]
    walk(tree["root"], "/root")
    for template_id, definition in tree["templates"].items():
        walk(definition, f"/templates/{key(template_id)}", template_id)

    children = defaultdict(list)
    for relation in edges:
        children[relation["source"]].append(relation)
    queue = deque([(root, [root])])
    while queue:
        node_id, access = queue.popleft()
        node = index[node_id]
        if "access" in node:
            continue
        node["access"] = access
        for relation in children[node_id]:
            next_id = relation["target"]
            if next_id not in access:
                queue.append((next_id, [*access, next_id]))
    assert all("access" in node for node in nodes)

    rules = []
    for rule_id, record in rule_data.items():
        row, criterion = criterion_by_rule[rule_id]
        rules.append(located({
            **record,
            "definition_nodes": criterion["definition_nodes"],
            "criterion_locator": {"file": CRITERION_FILE, "pointer": f"/{row}"},
        }, RULES_FILE, f"/{key(rule_id)}"))

    entries = []
    for row, skill in enumerate(inventory["skills"]):
        review = contracts["source_reviews"].get(skill["id"])
        info = located(skill, INVENTORY_FILE, f"/skills/{row}")
        if review:
            info["source_review"] = located(review, CONTRACTS_FILE, "/source_reviews/" + key(skill["id"]))
        entries.append(info)

    plan_sources = [
        (TREE_FILE, "baseline", "Definiciones compartidas, preguntas, ramas, prerrequisitos y gate humano por defecto."),
        (RULES_FILE, "baseline", "Criterios fijados, origen y adaptaciones. Incluye reglas de política local conservadas en el baseline."),
        (CRITERION_FILE, "baseline", "Correspondencia entre criterios fuente y IDs de definición."),
        (INVENTORY_FILE, "baseline", "Inventario fijado, asignaciones y disposiciones propuestas."),
        (f"{BASELINE}/index.html", "baseline", "Visor archivado del árbol fijado."),
        (f"{BASELINE}/README.md", "baseline", "Guía de lectura y límites del árbol fijado."),
        (f"{BASELINE}/AUDIT.md", "baseline", "Auditoría histórica del árbol fijado."),
        (LOCK_FILE, "fijación", "Huellas SHA-256 para los siete archivos fijados."),
        (CONTRACTS_FILE, "política suplementaria", "Relaciones tipadas, recursos, revisión de fuentes y requisitos declarados de verificación."),
        (f"{SKILL}/SKILL.md", "protocolo", "Entradas para diseño y mantenimiento, asistencia, decisiones y gates."),
        (f"{REFERENCE}/PILOT.md", "protocolo", "Alcance del piloto supervisado."),
        (f"{REFERENCE}/ASSISTANCE.md", "protocolo", "Mandatos y niveles de asistencia."),
        (f"{REFERENCE}/PROTOCOL.md", "protocolo", "Contratos de la sesión y decisión."),
        (f"{REFERENCE}/CLI.md", "protocolo", "Comandos y contratos del helper."),
        (f"{REFERENCE}/MAINTENANCE.md", "protocolo", "Entrada de mantenimiento y diagnóstico, fuera de Q00."),
        (EXPANDER_FILE, "helper", "Expansión de referencias con prefijo, contexto y candidato."),
        (f"{SKILL}/scripts/contracts.py", "helper", "Evalúa relaciones y condiciones con evidencia."),
        (f"{SKILL}/scripts/runner.py", "helper", "Helper de expediente y transiciones supervisadas."),
    ]
    sources = [dict(file=file, layer=layer, summary=summary, sha256=digest(file),
                    locked=layer == "baseline")
               for file, layer, summary in plan_sources]
    for name, expected in lock.items():
        assert digest(f"{BASELINE}/{name}") == expected, name
    assert contracts["baseline"]["tree_hash"] == lock["tree.json"]

    instantiated = list(flatten(expand_model(tree)["root"]))
    return dict(
        schema="design-tree-declaration-map/1",
        plugin_version=plugin["version"],
        tree_version=tree["version"],
        root=root,
        nodes=nodes,
        edges=edges,
        prerequisites=requirements,
        sources=sources,
        semantics=tree["semantics"],
        default_gate=located(tree["default_gate"], TREE_FILE, "/default_gate"),
        expansion=dict(
            file=EXPANDER_FILE,
            locator="expand_model",
            declarations=len(nodes),
            counts_by_kind=dict(Counter(node["kind"] for node in nodes)),
            occurrences=len(instantiated),
            occurrence_counts_by_kind=dict(Counter(node["kind"] for node in instantiated)),
            template_entries=dict(templated_by),
            summary="Una declaración instance sustituye su lugar por una copia de la definición indicada. Los prefijos se concatenan para los IDs y prerrequisitos. Cada copia conserva definition_id y hereda contexto, política de escritura y candidato cuando corresponda. El mapa muestra las definiciones y referencias una vez.",
        ),
        rules=rules,
        inventory=entries,
        contracts=dict(
            file=CONTRACTS_FILE,
            schema=contracts["schema"],
            baseline=located(contracts["baseline"], CONTRACTS_FILE, "/baseline"),
            relations=[located(record, CONTRACTS_FILE, f"/relations/{row}") for row, record in enumerate(contracts["relations"])],
            resources=[located(record, CONTRACTS_FILE, f"/resources/{row}") for row, record in enumerate(contracts["resources"])],
            verification_requirements=contracts.get("verification_requirements", []),
        ),
    )


if __name__ == "__main__":
    result = extract()
    Path(__file__).with_name("tree_data.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
