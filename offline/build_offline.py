#!/usr/bin/env python3
"""Generate a self-contained local-view copy of the gold board from pinned UI assets."""

import argparse
import base64
from hashlib import sha256
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / 'local-ui'
CDN = 'https://cdn.jsdelivr.net/npm/@shoelace-style/shoelace@2.20.1/cdn'
FONT_URL = r'https://fonts\.gstatic\.com/s/[^)\s]+\.woff2'


def replace_once(content, old, new):
    if content.count(old) != 1:
        raise ValueError(f'Se esperaba una sola aparición de {old[:120]}')
    return content.replace(old, new, 1)


def build(board):
    manifest = json.loads((ROOT / 'ui-dependencies.json').read_text(encoding='utf-8'))
    assets = {}
    for file in manifest['local_files']:
        path = file['path']
        data = (ASSETS / path).read_bytes()
        if sha256(data).hexdigest() != file['sha256']:
            raise ValueError(f'Integridad inválida en {path}')
        assets[path] = data
    head_attached = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    html = replace_once(board, head_attached, '')
    css = assets['shoelace-2.20.1-light.css'].decode('utf-8')
    html = replace_once(html, f'<link rel="stylesheet" href="{CDN}/themes/light.css">', f'<style>\n{css}\n</style>')
    fonts = assets['google-fonts.css'].decode('utf-8')
    fonts = re.sub(FONT_URL, lambda match: 'data:font/woff2;base64,' + base64.b64encode(
        assets['fonts/' + match.group().rsplit('/', 1)[-1]]
    ).decode('ascii'), fonts)
    font_import = f"@import url('{manifest['google_fonts_stylesheet']}');"
    html = replace_once(html, font_import, fonts)
    js = assets['shoelace-2.20.1-board.js'].decode('utf-8')
    if re.search(r'</script[\s>]', js, re.IGNORECASE):
        raise ValueError('El módulo del visor contiene un cierre script incrustado')
    html = replace_once(html, f'<script type="module" src="{CDN}/shoelace.js"></script>',
                        f'<script type="module">\n{js}\n</script>')
    viewer = re.findall(r'^function fetchDrawioViewer\(\)\{.*?\}$', html, re.MULTILINE)
    if len(viewer) != 1 or 'https://viewer.diagrams.net/js/viewer-static.min.js' not in viewer[0]:
        raise ValueError('No se encontró el cargador opcional del visor draw.io')
    html = replace_once(html, viewer[0], 'function fetchDrawioViewer(){return Promise.resolve(false)}')
    notices = '\n\n'.join(f'=== {name} ===\n{data.decode("utf-8")}'
                           for name, data in sorted(assets.items()) if name.startswith('licenses/'))
    if re.search(r'</script[\s>]', notices, re.IGNORECASE):
        raise ValueError('El texto de avisos contiene un cierre script incrustado')
    return replace_once(html, '</head>',
                        f'<script type="text/plain" id="localUiLicenses">\n{notices}\n</script>\n</head>')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('golden', type=Path, help='HTML v1.3 dorado')
    parser.add_argument('output', type=Path, help='Nueva ruta para variante autónoma')
    args = parser.parse_args()
    if args.golden.resolve() == args.output.resolve():
        parser.error('elige una ruta distinta a la del HTML dorado')
    board = args.golden.read_text(encoding='utf-8')
    args.output.write_text(build(board), encoding='utf-8')


if __name__ == '__main__':
    main()
