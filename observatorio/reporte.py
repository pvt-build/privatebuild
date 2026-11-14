#!/usr/bin/env python3
"""Arma el informe comparativo con la última captura de cada lander.

    python3 observatorio/reporte.py              # a pantalla
    python3 observatorio/reporte.py --guardar    # a observatorio/INFORME.md

Lee las fichas que dejó snapshot.py. No baja nada de internet.
"""

import io
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OBS = os.path.join(RAIZ, 'observatorio')
CAPTURAS = os.path.join(OBS, 'capturas')


def ultimas():
    out = []
    if not os.path.isdir(CAPTURAS):
        return out
    for slug in sorted(os.listdir(CAPTURAS)):
        d = os.path.join(CAPTURAS, slug)
        fechas = sorted(f for f in os.listdir(d) if os.path.isdir(os.path.join(d, f)))
        if not fechas:
            continue
        f = os.path.join(d, fechas[-1], 'ficha.json')
        if os.path.exists(f):
            ficha = json.load(io.open(f, encoding='utf-8'))
            ficha['capturas'] = len(fechas)
            out.append(ficha)
    return out


def tabla(filas, cols):
    anchos = [max(len(str(r.get(c, ''))) for r in filas + [{c: c}]) for c in cols]
    L = []
    L.append('| ' + ' | '.join(c.ljust(a) for c, a in zip(cols, anchos)) + ' |')
    L.append('|' + '|'.join('-' * (a + 2) for a in anchos) + '|')
    for r in filas:
        L.append('| ' + ' | '.join(str(r.get(c, '')).ljust(a) for c, a in zip(cols, anchos)) + ' |')
    return '\n'.join(L)


def main():
    fichas = ultimas()
    if not fichas:
        print('Todavía no hay capturas. Corre: python3 observatorio/snapshot.py')
        return 1

    idx = json.load(io.open(os.path.join(OBS, 'landers.json'), encoding='utf-8'))
    meta = {l['slug']: l for l in idx['landers']}

    L = ['# Observatorio de landers', '']
    L.append('Última captura de cada una. Para refrescar: `python3 observatorio/snapshot.py`')
    L.append('')

    for cat, desc in idx['categorias'].items():
        grupo = [f for f in fichas if f.get('categoria') == cat]
        L.append('## %s' % cat)
        L.append('')
        L.append('_%s_' % desc)
        L.append('')
        if not grupo:
            L.append('Ninguna capturada todavía.')
            L.append('')
            continue
        filas = [{
            'lander': f['slug'],
            'de quién': f.get('dueno', ''),
            'fecha': f.get('fecha', ''),
            'capturas': f.get('capturas', 1),
            'stack': ', '.join(f.get('stack', [])) or '—',
        } for f in grupo]
        L.append(tabla(filas, ['lander', 'de quién', 'fecha', 'capturas', 'stack']))
        L.append('')

    # Qué palanca usa cada una: acá se ve lo que la competencia hace y tú no.
    L.append('## Palancas de conversión')
    L.append('')
    L.append('Recursos que usan para que la gente complete el formulario.')
    L.append('')
    todas = sorted({p for f in fichas for p in f.get('palancas', [])})
    if todas:
        cols = ['palanca'] + [f['slug'] for f in fichas]
        filas = []
        for p in todas:
            r = {'palanca': p}
            for f in fichas:
                r[f['slug']] = 'si' if p in f.get('palancas', []) else '·'
            filas.append(r)
        L.append(tabla(filas, cols))
        L.append('')

    L.append('## Formularios')
    L.append('')
    for f in fichas:
        campos = f.get('campos_formulario', [])
        etiquetas = [c.get('placeholder') or c.get('name') or c.get('type', '?') for c in campos]
        L.append('**%s** — %d campo(s): %s' % (f['slug'], len(campos),
                                               ', '.join(etiquetas) or 'ninguno detectado'))
        pr = f.get('preguntas', [])
        if pr:
            L.append('')
            for q in pr[:12]:
                L.append('  - %s' % q)
        L.append('')

    L.append('## Nichos en juego')
    L.append('')
    nichos = {}
    for f in fichas:
        for n in meta.get(f['slug'], {}).get('nichos', []):
            nichos.setdefault(n, []).append(f['slug'])
    for n in sorted(nichos, key=lambda x: -len(nichos[x])):
        L.append('- **%s** — %s' % (n, ', '.join(nichos[n])))
    L.append('')

    pendientes = [l for l in idx['landers'] if l.get('url', 'PENDIENTE') == 'PENDIENTE']
    if pendientes:
        L.append('## Sin URL todavía')
        L.append('')
        for l in pendientes:
            L.append('- **%s** (%s) — %s' % (l['slug'], l.get('categoria', ''),
                                             l.get('notas', '')))
        L.append('')

    txt = '\n'.join(L)
    if '--guardar' in sys.argv:
        io.open(os.path.join(OBS, 'INFORME.md'), 'w', encoding='utf-8').write(txt)
        print('escrito en observatorio/INFORME.md')
    else:
        print(txt)
    return 0


if __name__ == '__main__':
    sys.exit(main())
