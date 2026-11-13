#!/usr/bin/env python3
"""Cambia el dominio del sitio en un solo comando.

El dominio aparece en el canonical, en las etiquetas Open Graph, en los datos
estructurados, en el sitemap y en robots.txt. Tenerlo repetido es una fuente
de errores: basta que uno quede viejo para que Google indexe la URL
equivocada. Esto los cambia todos a la vez.

    python3 scripts/set-dominio.py privatebuild.com
    python3 scripts/set-dominio.py --ver          # muestra el actual

Se le pasa el dominio sin esquema ni barra final. El script agrega https://.
"""

import io
import os
import re
import sys

ARCHIVOS = [
    'index.html',
    'diagnostico/index.html',
    'robots.txt',
    'sitemap.xml',
    'llms.txt',
    'manifest.webmanifest',
    'MIGRACION-VERCEL.md',
]

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATRON = re.compile(r'https://[a-z0-9][a-z0-9.-]*\.(?:vercel\.app|com|co|cl|app|io|net|dev)')


def actuales():
    encontrados = {}
    for rel in ARCHIVOS:
        ruta = os.path.join(RAIZ, rel)
        if not os.path.exists(ruta):
            continue
        for m in PATRON.findall(io.open(ruta, encoding='utf-8').read()):
            # los dominios de terceros no son nuestros
            if any(t in m for t in ('google', 'fonts.g', 'schema.org', 'notion',
                                    'whatsapp', 'wa.me', 'make.com', 'github',
                                    'sitemaps.org', 'jsdelivr', 'cdnjs')):
                continue
            encontrados[m] = encontrados.get(m, 0) + 1
    return encontrados


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 1

    if sys.argv[1] == '--ver':
        enc = actuales()
        if not enc:
            print('no encontré ningún dominio propio')
            return 1
        for d, n in sorted(enc.items(), key=lambda x: -x[1]):
            print('%-44s %d apariciones' % (d, n))
        return 0

    nuevo = 'https://' + sys.argv[1].strip().rstrip('/').replace('https://', '').replace('http://', '')

    enc = actuales()
    if not enc:
        print('no encontré ningún dominio propio que reemplazar')
        return 1
    viejo = max(enc.items(), key=lambda x: x[1])[0]
    if viejo == nuevo:
        print('ya está en %s, no hay nada que cambiar' % nuevo)
        return 0

    total = 0
    for rel in ARCHIVOS:
        ruta = os.path.join(RAIZ, rel)
        if not os.path.exists(ruta):
            continue
        s = io.open(ruta, encoding='utf-8').read()
        n = s.count(viejo)
        if not n:
            continue
        io.open(ruta, 'w', encoding='utf-8').write(s.replace(viejo, nuevo))
        print('  %-26s %d' % (rel, n))
        total += n

    print('\n%s  ->  %s   (%d reemplazos)' % (viejo, nuevo, total))
    print('\nFalta: en Vercel, Settings > Domains, agregar el dominio y')
    print('apuntar el DNS. Y en Search Console, volver a enviar el sitemap.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
