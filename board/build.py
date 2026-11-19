"""Reconstruye la pizarra v1.2 con la biblioteca estándar de Python."""

import argparse
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE = ROOT / "src"
RESOURCE = re.compile(r"@@BOARD:([a-z0-9-]+/[a-z0-9.-]+)@@")
ESCAPED_HTML_DATA = {"comparacion/datos.json", "revisiones-pendientes/datos.json"}
POLICY_DIGEST = "__MIN_ROUTE_POLICY_SHA256__"
SELECTION_CORE = "__MIN_ROUTE_SELECTION_CORE__"


def read(path):
    return path.read_bytes().decode("utf-8")


def compact_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def protect_script(value):
    return re.sub(r"</script(?=[\s/>])", lambda match: r"\u003c" + match[0][1:], value, flags=re.I)


def resource(source, name):
    text = read(source / name)
    if name.endswith(".drawio"):
        # El script original contiene la cadena JSON con los cierres XML escapados.
        return compact_json(text).replace("</", r"<\/")
    if name.endswith(".json"):
        data = protect_script(compact_json(json.loads(text)))
        return data.replace(">", r"\u003e") if name in ESCAPED_HTML_DATA else data
    return text


def reconstruct_template(source=DEFAULT_SOURCE):
    """Ensambla la plantilla histórica, incluidos sus marcadores del simulador."""
    skeleton = read(source / "board.template.html")
    names = RESOURCE.findall(skeleton)
    if not names or len(names) != len(set(names)) or skeleton.count("@@BOARD:") != len(names):
        raise ValueError("Marcadores de recursos ausentes, duplicados o inválidos")
    return RESOURCE.sub(lambda match: resource(source, match[1]), skeleton).encode("utf-8")


def replace_once(text, marker, content):
    if text.count(marker) != 1:
        raise ValueError(f"Marcador ausente o duplicado: {marker}")
    return text.replace(marker, content, 1)


def build(source=DEFAULT_SOURCE):
    """Devuelve el HTML autocontenido de la pizarra v1.2."""
    template = reconstruct_template(source).decode("utf-8")
    simulator = source / "simulador"
    policy = compact_json(json.loads(read(simulator / "politica.json"))).replace("<", r"\u003c")
    policy_hash = hashlib.sha256(policy.encode("utf-8")).hexdigest()
    selector = replace_once(read(simulator / "selector.js"), POLICY_DIGEST, policy_hash)
    selector = replace_once(selector, SELECTION_CORE, read(simulator / "selection-core.cjs"))
    sections = {
        "@@MIN_ROUTE_POLICY@@": policy,
        "@@MIN_ROUTE_SELECTOR@@": selector,
        "@@MIN_ROUTE_CSS@@": read(simulator / "selector.css"),
    }
    for marker, content in sections.items():
        template = replace_once(template, marker, content)
    return template.encode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    destinations = parser.add_mutually_exclusive_group()
    destinations.add_argument("--output", metavar="PATH", type=Path, help="Destino de la pizarra v1.2")
    destinations.add_argument("--template-output", metavar="PATH", type=Path, help="Reconstruye la plantilla histórica con sus tres marcadores del simulador")
    parser.add_argument("--expect-sha256", metavar="DIGEST", help="Exige este SHA-256 antes de escribir")
    args = parser.parse_args()
    if args.template_output:
        output = args.template_output
        content = reconstruct_template()
    else:
        output = args.output or ROOT / "release" / "design-router-pizarra-v1.2.html"
        content = build()
    digest = hashlib.sha256(content).hexdigest()
    if args.expect_sha256 and digest != args.expect_sha256.lower():
        parser.error(f"SHA-256 obtenido: {digest}. Se esperaba {args.expect_sha256}.")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(content)
    print(f"{digest}  {output}")


if __name__ == "__main__":
    main()
